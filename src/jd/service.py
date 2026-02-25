"""JD intake service — F1 sponsorship keyword detector.

This module provides detect_f1_sponsorship(), a pure Python function
that scans job description text for visa sponsorship signals and returns
Optional[bool]:
    True   — JD contains positive sponsorship indicators (H-1B, OPT, will sponsor)
    False  — JD explicitly denies sponsorship (no sponsorship, must be citizen)
    None   — No sponsorship keywords found, or signals conflict (ambiguous)

No LLM call is made; matching is deterministic via regex.
"""

import logging
import re
from typing import Optional

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
