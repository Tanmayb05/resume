"""JD intake service — F1 sponsorship keyword detector and JDService orchestrator.

This module provides:
  - detect_f1_sponsorship(): pure Python function that scans JD text for
    visa sponsorship signals and returns Optional[bool].
  - JDParseResult: dataclass returned by JDService.parse_and_persist().
  - JDService: stateless async orchestrator that parses raw JD text via LLM,
    detects F1 sponsorship, and persists a JobRecord to disk atomically.

detect_f1_sponsorship() returns:
    True   — JD contains positive sponsorship indicators (H-1B, OPT, will sponsor)
    False  — JD explicitly denies sponsorship (no sponsorship, must be citizen)
    None   — No sponsorship keywords found, or signals conflict (ambiguous)

No LLM call is made for F1 detection; matching is deterministic via regex.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from src.config import AppConfig
from src.llm.client import LLMClient
from src.llm.errors import LLMError
from src.llm.utils import extract_json, load_prompt
from src.models.job_record import JobRecord, JobStatus
from src.storage.job_store import JobStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Positive indicators: sponsorship IS offered / supported
# ---------------------------------------------------------------------------
# Pattern notes:
#   - r"\bopt\b(?!\s*-?\s*(?:in|out|ional))": matches "OPT" (Optional Practical
#     Training) but NOT "opt-in", "opt-out", "optional".
#   - r"\bh1b\b": matches after H-1B/H1-B/H 1 B have been normalized to "h1b".
#     Uses (?<!not sponsor ) lookbehind so "do not sponsor H-1B" is not a false positive.
#   - r"(?<!no )(?<!no visa )\bsponsorship\s+...": double lookbehind excludes
#     "no sponsorship available" and "no visa sponsorship available" substrings.
#   - r"(?<!no )\bvisa\s+sponsorship\b": excludes "no visa sponsorship" substring.
#   - authorize[ds]? to work: negative lookahead excludes "authorized to work ...
#     without sponsorship" (catches the "must already be authorized" phrasing).
_POSITIVE_PATTERNS: list[str] = [
    r"\bwill\s+sponsor\b",
    # Double lookbehind: exclude "no sponsorship available" and "no visa sponsorship available"
    r"(?<!no )(?<!no visa )\bsponsorship\s+(?:is\s+)?(?:available|provided|offered)\b",
    r"(?<!no )\bvisa\s+sponsorship\b",  # exclude "no visa sponsorship"
    r"\bopt\b(?!\s*-?\s*(?:in|out|ional))",  # OPT but NOT opt-in / opt-out / optional
    r"(?<!not sponsor )\bh1b\b",  # after normalization; exclude "do not sponsor h1b"
    r"\bopt\s+(?:eligible|authorized)\b",
    # Exclude "authorized to work ... without sponsorship" via lookahead
    r"\bauthorize[ds]?\s+to\s+work(?!\s+(?:(?:\w+\s+){0,5})?without\s+sponsorship)\b",
    r"\bwork\s+authorization\s+(?:supported|provided)\b",
    r"\bopen\s+to\s+sponsor(?:ing)?\b",
]

# ---------------------------------------------------------------------------
# Negative indicators: sponsorship NOT offered / must already be authorized
# ---------------------------------------------------------------------------
_NEGATIVE_PATTERNS: list[str] = [
    r"\bno\s+(?:visa\s+)?sponsorship\b",
    r"\bsponsorship\s+(?:is\s+)?not\s+(?:available|offered|provided)\b",
    r"\bmust\s+be\s+(?:a\s+)?(?:us\s+)?(?:citizen|permanent\s+resident|pr)\b",
    r"\bcitizens?\s+(?:and\s+)?(?:permanent\s+residents?\s+)?only\b",
    r"\bno\s+work\s+(?:visa|authorization)\s+sponsorship\b",
    r"\bauthorized\s+to\s+work\s+(?:in\s+the\s+us|without\s+sponsorship)\b",
    r"\bcannot\s+sponsor\b",
    r"\bdo\s+not\s+sponsor\b",
    # Catches "We sponsor H-1B but must already be authorized" — the applicant
    # must already have work authorization, so sponsorship is not actually offered.
    r"\bmust\s+already\s+be\s+(?:authorized|eligible|work\s+authorized)\b",
]


def detect_f1_sponsorship(jd_text: str) -> Optional[bool]:
    """Detect F1 visa / sponsorship signals in a job description.

    Args:
        jd_text: Raw job description text (any case; normalization applied internally).

    Returns:
        True   — JD explicitly offers sponsorship (H-1B, OPT, will sponsor …).
        False  — JD explicitly denies sponsorship (no sponsorship, must be citizen …).
        None   — No sponsorship keywords found OR signals conflict (ambiguous).
    """
    if not jd_text:
        return None

    # Step 1: Normalize to lowercase.
    normalized = jd_text.lower()

    # Step 2: Collapse H-1B / H1-B / H 1 B variants to the canonical token "h1b"
    #         so that \bh1b\b in _POSITIVE_PATTERNS matches all variants uniformly.
    normalized = re.sub(r"h[\-\s]?1[\-\s]?b", "h1b", normalized)

    # Step 3: Test against pattern lists.
    has_positive = any(
        re.search(p, normalized, re.IGNORECASE) for p in _POSITIVE_PATTERNS
    )
    has_negative = any(
        re.search(p, normalized, re.IGNORECASE) for p in _NEGATIVE_PATTERNS
    )

    # Step 4: Apply XOR logic; both present = ambiguous.
    if has_positive and not has_negative:
        logger.debug("F1 detection: positive signal found")
        return True
    if has_negative and not has_positive:
        logger.debug("F1 detection: negative signal found")
        return False
    if has_positive and has_negative:
        logger.debug("F1 detection: conflicting signals — returning None (ambiguous)")
        return None

    logger.debug("F1 detection: no sponsorship keywords found")
    return None


# ---------------------------------------------------------------------------
# JDParseResult dataclass
# ---------------------------------------------------------------------------


@dataclass
class JDParseResult:
    """Structured result from JDService.parse_and_persist().

    Attributes:
        success:    True when JD was parsed and persisted successfully.
        job_record: Populated JobRecord on success; None on failure.
        error:      Human-readable error description on failure; None on success.
    """

    success: bool
    job_record: Optional[JobRecord] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# JDService orchestrator
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ("company", "role", "location")
_MAX_PARSE_ATTEMPTS = 2


class JDService:
    """Stateless async orchestrator for JD intake pipeline.

    Wires together:
      1. detect_f1_sponsorship() — pure Python, no LLM
      2. LLM parse with retry (_parse_jd) — 2 attempts with strict fallback
      3. JobStore persistence — collision-safe via new_job_dir()

    Stateless design: safe to share across concurrent requests. Each call
    receives its own job_dir via JobStore.new_job_dir().

    Usage:
        service = JDService(config, llm_client)
        result = await service.parse_and_persist(jd_text, store)
    """

    def __init__(self, config: AppConfig, llm_client: LLMClient) -> None:
        self.config = config
        self.llm = llm_client

    async def parse_and_persist(
        self, jd_text: str, store: JobStore
    ) -> JDParseResult:
        """Parse raw JD text into a structured JobRecord and persist to disk.

        Pipeline:
          1. F1 detection (pure Python, no LLM)
          2. LLM parse with retry (2 attempts; strict fallback on attempt 2)
          3. Validate required fields from raw dict BEFORE constructing JobRecord
          4. Allocate job directory via store.new_job_dir() (collision-safe)
          5. Construct JobRecord
          6. Persist via store.write()

        Returns JDParseResult — never raises on business logic failures.
        success=False is returned with a descriptive error on any failure.

        Args:
            jd_text: Raw job description text (any format).
            store:   JobStore instance for directory allocation and persistence.

        Returns:
            JDParseResult with success flag, optional job_record, optional error.
        """
        # Step 1 — F1 detection (pure Python, no LLM)
        f1_flag = detect_f1_sponsorship(jd_text)
        logger.debug("F1 detection result: %s", f1_flag)

        # Step 2 — LLM parse with retry
        try:
            parsed = await self._parse_jd(jd_text)
        except ValueError as exc:
            logger.warning("JD parse failed (ValueError): %s", exc)
            return JDParseResult(success=False, error=str(exc))
        except LLMError as exc:
            logger.warning("JD parse failed (LLMError): %s", exc)
            return JDParseResult(success=False, error=f"LLM error: {exc}")
        except Exception as exc:
            logger.warning("JD parse failed (unexpected): %s", exc)
            return JDParseResult(success=False, error=f"JD parse failed: {exc}")

        # Step 3 — Validate required fields BEFORE constructing JobRecord
        if not all(parsed.get(f) for f in _REQUIRED_FIELDS):
            missing = [f for f in _REQUIRED_FIELDS if not parsed.get(f)]
            logger.warning("Missing required JD fields: %s", missing)
            return JDParseResult(
                success=False,
                error="Missing required fields after parse",
            )

        # Step 4 — Allocate job directory (collision-safe via JobStore)
        job_dir = store.new_job_dir(parsed["company"], parsed["role"])
        job_dir.mkdir(parents=True, exist_ok=True)

        # Step 5 — Construct JobRecord (only fields that exist on the model)
        record = JobRecord(
            company=parsed["company"],
            role=parsed["role"],
            location=parsed["location"],
            job_dir=str(job_dir),
            jd_text=jd_text,
            f1_sponsorship_available=f1_flag,
            status=JobStatus.DISCOVERED,
        )

        # Step 6 — Persist
        store.write(record)
        logger.info(
            "JD persisted: %s @ %s -> %s",
            record.role,
            record.company,
            job_dir,
        )
        return JDParseResult(success=True, job_record=record)

    async def _parse_jd(self, jd_text: str) -> dict:
        """Parse JD text into a structured dict via LLM with retry.

        Attempt 1: Standard parse_job_description prompt.
        Attempt 2: Same prompt with appended instruction requiring company/role/location.

        Raises:
            ValueError: After MAX_PARSE_ATTEMPTS if required fields still missing.
            LLMError:   On LLM transport/timeout failure (propagated to caller).
        """
        last_parsed: dict = {}

        for attempt in range(1, _MAX_PARSE_ATTEMPTS + 1):
            if attempt == 1:
                prompt = load_prompt("parse_job_description", jd_text=jd_text)
            else:
                # Attempt 2: append a strict instruction to the standard prompt
                base_prompt = load_prompt(
                    "parse_job_description", jd_text=jd_text
                )
                prompt = (
                    base_prompt
                    + "\n\nIMPORTANT: company, role, and location are required. "
                    "If any are unclear from the JD, make your best inference. "
                    "Do not return null for these fields."
                )

            raw = await self.llm.call(prompt)
            try:
                last_parsed = extract_json(raw)
            except (ValueError, Exception) as exc:
                logger.warning(
                    "JD parse attempt %d: JSON extraction failed: %s", attempt, exc
                )
                last_parsed = {}
                continue

            if all(last_parsed.get(f) for f in _REQUIRED_FIELDS):
                logger.debug("JD parse succeeded on attempt %d", attempt)
                return last_parsed

            logger.warning(
                "JD parse attempt %d: missing required fields %s",
                attempt,
                [f for f in _REQUIRED_FIELDS if not last_parsed.get(f)],
            )

        raise ValueError(
            "JD parse failed: company, role, or location missing after "
            f"{_MAX_PARSE_ATTEMPTS} attempts"
        )
