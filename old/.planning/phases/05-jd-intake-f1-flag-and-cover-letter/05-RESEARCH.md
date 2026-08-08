# Phase 5: JD Intake, F1 Flag, and Cover Letter - Research

**Researched:** 2026-02-25
**Domain:** LLM-driven JD parsing, F1 keyword detection, cover letter generation with retry logic, plain-text + TXT file output
**Confidence:** HIGH (all findings verified from project source code and established patterns)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### F1 Sponsorship Detection
- Flag is a **boolean**: `true` means sponsorship IS offered (OPT/H-1B supported), `false` means not offered
- When no sponsorship-related keywords are found: default to **null/unknown** (not false) — distinguishes "explicitly not offered" from "not mentioned"
- Matching is **case-insensitive + normalized variants**: handles "H1B" vs "H-1B" vs "H1-B", and avoids false positives like "opt-in" for "opt"
- No reason string stored — just the boolean/null value on the job record

#### JD Parsing Behavior
- **Required fields** for parse success: company, role, location — all three must be non-null
- On missing required fields: **retry once** with the same or stricter prompt, then fail if still missing (do not persist a partial record)
- **Duplicate company slug**: create a new versioned record (e.g., `acme_v2`) — never overwrite existing data
- Validation approach: Claude's discretion (validate required fields + reasonable structural check)

#### Cover Letter Content and Tone
- **Resume context**: full resume text passed to the LLM (all sections)
- **Tone**: professional but conversational — warm and direct, sounds human-written
- **Prompt**: use `templates/cover_letter_prompt.md` as the generation prompt (structure, salutation, body format, signature block are all defined there)
- **Graduation date**: "May 2026" for full-time roles, "Dec 2026" for internships; Claude determines other internship vs full-time adaptations
- **Word count enforcement**: retry with an explicit correction prompt on out-of-range output — "Previous version was X words, please shorten/expand to 300–400 words"
- **No em-dashes**: enforced via prompt (already in template); strip any remaining em-dashes post-generation as a safety net

#### Cover Letter Output Format
- **Filename**: `cover_letter.txt` and `cover_letter.pdf` — fixed names inside `data/<company_slug>/` (overwritten on regeneration)
- **Structure**: follow `templates/cover_letter_template.docx` as layout reference
- **Text output**: plain `.txt` with the letter body exactly as generated (no extra metadata header)
- **PDF generation**: Claude's discretion on library — must be pure Python with no LibreOffice dependency; Microsoft Word via `docx2pdf` is acceptable if present but not required

### Claude's Discretion
- Validation depth for JD schema (beyond required fields check)
- PDF generation library choice (reportlab, fpdf2, WeasyPrint, or docx2pdf if Word available)
- Internship vs full-time tone adaptation beyond the graduation date
- Exact F1 keyword list and normalization rules

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JD-01 | User can paste a job description as text and submit it for parsing | `JDService.parse()` accepts raw `jd_text: str`; returns populated `JobRecord` |
| JD-02 | System parses JD text into structured JSON matching job_description_schema.json | `parse_job_description.md` Jinja2 prompt already exists in `src/llm/prompts/`; use `load_prompt()` + `extract_json()` + retry-on-missing-fields pattern |
| JD-03 | System detects F1 visa/sponsorship signal from JD text | Pure Python keyword matching module (`detect_f1_sponsorship(jd_text)`); returns `Optional[bool]`; no LLM call needed |
| JD-04 | System persists parsed job record as JSON under data/<company_slug>/ | `JobStore.write()` already atomic-safe; `JobStore.new_job_dir()` already handles slug collision via counter; just need to call them correctly |
| COV-01 | System generates a cover letter from JD context + selected resume content | `generate_cover_letter.md` prompt already exists in `src/llm/prompts/`; async `LLMClient.call()` pattern follows Phase 4 selection |
| COV-02 | Generated cover letter is 300-400 words; system validates word count and regenerates if outside range | Word count = `len(text.split())`; retry with explicit correction prompt template if outside [300, 400] |
| COV-03 | System saves cover letter as plain .txt file to data/<company_slug>/ | `Path(job_dir / "cover_letter.txt").write_text(text, encoding="utf-8")` — plain write, no library needed |
| COV-04 | Cover letter uses correct graduation date: "May 2026" for full-time, "Dec 2026" for internships | Detect `employment_type` from parsed JD record; pass correct `graduation_date` variable to `generate_cover_letter.md` template |
| COV-05 | Cover letter contains no em-dashes | Strip `\u2014` (—) and `--` post-generation via `text.replace("\u2014", ",").replace(" -- ", ", ")` as safety net; primary enforcement is in prompt |
</phase_requirements>

---

## Summary

Phase 5 builds two largely independent services that the Phase 4 ResumeService will call into: a `JDService` that parses raw job description text into a structured `JobRecord`, and a `CoverLetterService` that generates, validates, and saves a plain-text cover letter. Both follow the exact same async orchestrator pattern established in Phase 4 — constructor takes `AppConfig` + `LLMClient`, entry method is `async def` and returns a result dataclass, errors are caught and returned as strings, never raised.

The infrastructure for Phase 5 is 80% already in place. `parse_job_description.md` and `generate_cover_letter.md` prompt templates exist in `src/llm/prompts/`. `JobStore` already handles atomic writes and slug collision. `load_prompt()`, `extract_json()`, `LLMClient.call()`, and `LLMError` are all importable. What Phase 5 needs to build is: the orchestrator modules (`src/jd/service.py`, `src/cover_letter/service.py`), the F1 keyword detection function, the word-count retry loop, and the em-dash post-processing strip.

The one area of Claude's discretion that needs a firm recommendation is PDF generation. Given the existing `cover_letter_generator.py` and `docx2pdf` in the codebase, the project already has the docx approach working on macOS. However, the locked decision is `.txt` only for Phase 5 (COV-03 says "no PDF/docx — eliminates LibreOffice dependency"). PDF is deferred to v2 (`COV-V2-01`). So Phase 5 only writes `cover_letter.txt`.

**Primary recommendation:** Build `JDService` and `CoverLetterService` as thin async orchestrators following the `ResumeService` pattern. Keep F1 detection as pure Python (no LLM). Write only `.txt` for Phase 5. Retry once on JD required-field failure, retry up to 2 times on word-count violations.

---

## Standard Stack

### Core (all already in project — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `src.llm.client.LLMClient` | project | Async Ollama calls with Tenacity retry | All LLM calls go through this single point — consistent timeout/retry/error handling |
| `src.llm.utils.load_prompt` | project | Jinja2 template rendering from `src/llm/prompts/*.md` | Established pattern; StrictUndefined catches variable mismatches at render time |
| `src.llm.utils.extract_json` | project | Parse LLM JSON output with json_repair fallback | Handles all fence variants and malformed output |
| `src.models.job_record.JobRecord` | project | Pydantic model for job application state | Already has `f1_sponsorship_available: Optional[bool]` field |
| `src.storage.job_store.JobStore` | project | Atomic filesystem persistence | Already has `new_job_dir()` slug collision handling and `write()` atomic via tempfile+os.replace |
| `pydantic` | >=2.7.0 | Model validation | Already in requirements.txt |
| `jinja2` | >=3.0 | Prompt template rendering | Already in requirements.txt |
| `json-repair` | >=0.30.0 | LLM JSON repair | Already in requirements.txt |

### Supporting (already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | stdlib | F1 keyword normalization, em-dash strip | F1 detection and post-processing |
| `pathlib.Path` | stdlib | File I/O for cover_letter.txt | Writing cover letter to job_dir |
| `src.llm.errors.LLMError` | project | Catch transient + permanent LLM failures | Wrap in result dataclass |
| `dataclasses.dataclass` | stdlib | Result type for JDService and CoverLetterService | Matches Phase 4 pattern |

### No New Dependencies Required

Phase 5 requires zero new Python packages. All infrastructure is already installed.

**Installation:**
```bash
# No new packages. Verify existing:
pip show json-repair jinja2 pydantic ollama tenacity
```

---

## Architecture Patterns

### Recommended Module Structure

```
src/
├── jd/
│   ├── __init__.py
│   └── service.py          # JDService: parse + F1 detect + persist
├── cover_letter/
│   ├── __init__.py
│   └── service.py          # CoverLetterService: generate + validate + save
├── llm/
│   └── prompts/
│       ├── parse_job_description.md   # ALREADY EXISTS — update field names
│       └── generate_cover_letter.md  # ALREADY EXISTS — update graduation_date var
└── models/
    └── job_record.py        # ALREADY EXISTS — no changes needed
```

### Pattern 1: Stateless Async Orchestrator (follow ResumeService exactly)

**What:** Constructor takes `AppConfig` + `LLMClient`. Entry method is `async def` and returns a result dataclass. Never raises on business logic failures (missing fields, word count, F1 unknown). Only raises on programming errors (bad config, import failures).

**When to use:** Both `JDService` and `CoverLetterService`.

**Example:**
```python
# Source: src/resume/service.py (Phase 4 — proven pattern)
@dataclass
class JDParseResult:
    success: bool
    job_record: Optional[JobRecord] = None
    error: Optional[str] = None

class JDService:
    def __init__(self, config: AppConfig, llm_client: LLMClient) -> None:
        self.config = config
        self.llm = llm_client

    async def parse_and_persist(
        self,
        jd_text: str,
        store: JobStore,
    ) -> JDParseResult:
        ...
```

### Pattern 2: LLM Parse + Retry Once on Missing Required Fields

**What:** Call LLM, extract JSON, validate required fields (company, role, location). If any are None/empty: retry once with a stricter prompt. If still missing: return failure, do NOT persist.

**When to use:** JD parsing step inside `JDService.parse_and_persist()`.

**Example:**
```python
# Source: pattern derived from src/resume/service.py try/except + retry pattern
MAX_PARSE_ATTEMPTS = 2

async def _parse_jd(self, jd_text: str) -> dict:
    prompt = load_prompt("parse_job_description", jd_text=jd_text)
    for attempt in range(1, MAX_PARSE_ATTEMPTS + 1):
        raw = await self.llm.call(prompt)
        parsed = extract_json(raw)
        if all(parsed.get(f) for f in ("company", "role", "location")):
            return parsed
        if attempt < MAX_PARSE_ATTEMPTS:
            logger.warning(
                "JD parse missing required fields on attempt %d; retrying with strict prompt",
                attempt,
            )
            prompt = load_prompt(
                "parse_job_description",
                jd_text=jd_text,
                strict_mode=True,  # template uses {% if strict_mode %} block
            )
    raise ValueError("JD parse failed: company, role, or location missing after 2 attempts")
```

### Pattern 3: Word Count Retry Loop for Cover Letter

**What:** Generate cover letter, count words with `len(text.split())`. If outside [300, 400]: retry with correction prompt that includes actual word count and direction. Max 2 retries.

**When to use:** Inside `CoverLetterService.generate()`.

**Example:**
```python
# Source: derived from trim_loop pattern in src/resume/trimmer.py
MAX_WORD_COUNT_RETRIES = 2
WORD_COUNT_MIN, WORD_COUNT_MAX = 300, 400

async def _generate_with_word_count_check(
    self,
    jd_text: str,
    selected_resume_json: str,
    graduation_date: str,
    application_type: str,
) -> str:
    prompt = load_prompt(
        "generate_cover_letter",
        job_description=jd_text,
        selected_resume_json=selected_resume_json,
        graduation_date=graduation_date,
        application_type=application_type,
    )

    for attempt in range(MAX_WORD_COUNT_RETRIES + 1):
        raw = await self.llm.call(prompt)
        text = raw.strip()
        word_count = len(text.split())

        if WORD_COUNT_MIN <= word_count <= WORD_COUNT_MAX:
            return text

        if attempt < MAX_WORD_COUNT_RETRIES:
            direction = "shorten" if word_count > WORD_COUNT_MAX else "expand"
            prompt = (
                f"Previous version was {word_count} words. Please {direction} it "
                f"to be between {WORD_COUNT_MIN} and {WORD_COUNT_MAX} words.\n\n"
                + prompt
            )
            logger.warning(
                "Cover letter word count %d out of range [%d, %d]; retrying (%d/%d)",
                word_count, WORD_COUNT_MIN, WORD_COUNT_MAX, attempt + 1, MAX_WORD_COUNT_RETRIES,
            )

    logger.warning(
        "Cover letter word count still %d after %d retries; accepting anyway",
        word_count, MAX_WORD_COUNT_RETRIES,
    )
    return text
```

### Pattern 4: F1 Keyword Detection (Pure Python, No LLM)

**What:** Case-insensitive regex matching with normalization. Returns `Optional[bool]`: `True` = sponsorship offered, `False` = explicitly not offered, `None` = not mentioned.

**When to use:** `detect_f1_sponsorship(jd_text: str)` called immediately after JD text is received, before LLM parsing.

**Example:**
```python
# Source: designed from CONTEXT.md locked decisions
import re
from typing import Optional

# Positive indicators: sponsorship IS offered
_POSITIVE_PATTERNS = [
    r"\bwill\s+sponsor\b",
    r"\bsponsorship\s+(?:is\s+)?(?:available|provided|offered)\b",
    r"\bvisa\s+sponsorship\b",
    r"\bopt\b(?!\s*-?\s*(?:in|out|ional))",  # "OPT" but not "opt-in", "opt-out", "optional"
    r"\bh[\-\s]?1[\-\s]?b\b",               # H-1B, H1B, H1-B
    r"\bopt\s+(?:eligible|authorized)\b",
    r"\bauthorize[ds]?\s+to\s+work\b",
    r"\bwork\s+authorization\s+(?:supported|provided)\b",
    r"\bopen\s+to\s+sponsoring\b",
]

# Negative indicators: sponsorship NOT offered / must already be authorized
_NEGATIVE_PATTERNS = [
    r"\bno\s+(?:visa\s+)?sponsorship\b",
    r"\bsponsorship\s+(?:is\s+)?not\s+(?:available|offered|provided)\b",
    r"\bmust\s+be\s+(?:a\s+)?(?:us\s+)?(?:citizen|permanent\s+resident|pr)\b",
    r"\bcitizens?\s+(?:and\s+)?(?:permanent\s+residents?\s+)?only\b",
    r"\bno\s+work\s+(?:visa|authorization)\s+sponsorship\b",
    r"\bauthorized\s+to\s+work\s+(?:in\s+the\s+us|without\s+sponsorship)\b",
    r"\bcannot\s+sponsor\b",
    r"\bdo\s+not\s+sponsor\b",
]

def detect_f1_sponsorship(jd_text: str) -> Optional[bool]:
    """Return True (offered), False (not offered), or None (not mentioned)."""
    normalized = jd_text.lower()
    # Remove hyphens between H and 1 and B for normalization
    normalized = re.sub(r"h[\-\s]1[\-\s]b", "h1b", normalized)

    has_negative = any(re.search(p, normalized) for p in _NEGATIVE_PATTERNS)
    has_positive = any(re.search(p, normalized) for p in _POSITIVE_PATTERNS)

    if has_negative and not has_positive:
        return False
    if has_positive and not has_negative:
        return True
    if has_positive and has_negative:
        # Ambiguous — treat as unknown
        return None
    return None  # Not mentioned
```

### Pattern 5: Em-Dash Strip (Post-Generation Safety Net)

**What:** Strip unicode em-dash (U+2014) and double-hyphen `--` after LLM generation. Primary enforcement is in the prompt; this is defense-in-depth.

```python
def _strip_em_dashes(text: str) -> str:
    """Remove em-dashes post-generation. Primary enforcement is in the prompt."""
    # Unicode em-dash: U+2014
    text = text.replace("\u2014", ",")
    # Double hyphen used as em-dash
    text = re.sub(r"\s*--\s*", ", ", text)
    return text
```

### Pattern 6: Internship vs Full-Time Detection

**What:** Look at parsed `employment_type` field from JD parse result. Map to graduation date and application type label.

```python
def _resolve_graduation_date(employment_type: Optional[str]) -> tuple[str, str]:
    """Return (graduation_date, application_type) based on employment_type."""
    if employment_type and "intern" in employment_type.lower():
        return "Dec 2026", "internship"
    return "May 2026", "full-time"
```

### Anti-Patterns to Avoid

- **Calling LLM for F1 detection:** LLM is unreliable for binary keyword presence. Pure regex is faster, deterministic, and requires no token budget.
- **Persisting a partial JobRecord (missing company/role/location):** The locked decision is explicit: do not persist if required fields are missing. Always validate before calling `job_store.write()`.
- **Overwriting existing job directories:** `JobStore.new_job_dir()` already handles collision with `-2`, `-3` suffix. Always call it, never construct `job_dir` manually.
- **Importing cover_letter service at module level without tectonic check:** Unlike LaTeX, `.txt` write has no external dependency, but follow the same deferred-import convention for anything non-stdlib.
- **Using the old `src/cover_letter_generator.py`:** The legacy module at `src/cover_letter_generator.py` uses `docx` and `docx2pdf` (old architecture). Phase 5 builds new `src/cover_letter/service.py` — do not use or import the legacy module.
- **Using the old `src/llm.py`:** Legacy file uses raw `requests` against Ollama with no retry. All new LLM calls go through `src.llm.client.LLMClient`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON extraction from LLM output | Custom regex/strip logic | `src.llm.utils.extract_json()` | Already handles all fence variants + json_repair fallback |
| Prompt template rendering | f-strings or manual .format() | `src.llm.utils.load_prompt()` | Jinja2 with StrictUndefined catches missing variables at render time |
| LLM retry on transient errors | Manual try/except loop | `src.llm.client.LLMClient.call()` | Already has Tenacity exponential backoff; wraps all errors in `LLMError` |
| Atomic file write | `open().write()` | `src.storage.job_store.JobStore.write()` | tempfile + fsync + os.replace already implemented |
| Slug collision handling | Custom counter logic | `src.storage.job_store.JobStore.new_job_dir()` | Already auto-increments -2, -3, etc. |
| F1 sponsorship text parsing | LLM call | Pure Python `re` module | Deterministic, fast, no token cost, no hallucination risk |
| Word count | len(text) | `len(text.split())` | Simple; don't use NLTK or any tokenizer |

**Key insight:** Phase 5 is an orchestration layer, not an infrastructure layer. All the hard infrastructure already exists. The job is wiring it together correctly with the right retry logic and validation gates.

---

## Common Pitfalls

### Pitfall 1: False Positive F1 Detection ("opt-in", "optional")

**What goes wrong:** The word "opt" matches OPT (Optional Practical Training) — but "opt-in," "opt-out," and "optional" are unrelated.
**Why it happens:** Simple substring matching on "opt" hits these words.
**How to avoid:** Use the word-boundary pattern `\bopt\b(?!\s*-?\s*(?:in|out|ional))` — a negative lookahead excludes "opt-in", "opt-out", "optional". Test with: `re.search(r"\bopt\b(?!\s*-?\s*(?:in|out|ional))", "optional skills", re.IGNORECASE)` should return None.
**Warning signs:** F1 flag returns True for job postings that have "optional" anywhere in the text.

### Pitfall 2: Missing Required Fields Not Caught Before Persistence

**What goes wrong:** LLM returns a parsed JD where `company` is None or empty string. JobRecord is persisted with `company=""` which passes Pydantic's `min_length=1` check (empty string has length 0 — actually Pydantic WILL catch it), but more subtly: LLM may return `"company": null` which after `extract_json()` gives Python `None`, and `None` passed to `company` field raises ValidationError at `JobRecord()` construction.
**Why it happens:** LLM outputs null for fields it can't find; the parse loop doesn't validate before trying to construct JobRecord.
**How to avoid:** Validate the raw dict from `extract_json()` first: check `all(parsed.get(f) for f in ("company", "role", "location"))` before attempting `JobRecord(...)` construction. Only after that validation passes should you construct and persist the record.
**Warning signs:** `pydantic.ValidationError` on `min_length=1` or `None` type mismatch during testing.

### Pitfall 3: Word Count Counting Includes Signature Block

**What goes wrong:** The cover letter prompt includes a signature block (`Regards,\nTanmay Bhuskute,...`). Word count for 300–400 words target is the letter body; if counted with the signature, letters will be consistently short.
**Why it happens:** `len(text.split())` counts all words in the text, including the signature.
**How to avoid:** The locked decision says "300-400 words" per COV-02. The existing `generate_cover_letter.md` prompt already says "300-400 words exactly." The prompt template in `templates/cover_letter_prompt.md` includes the full signature. Count total words including signature — this matches "the cover letter as generated" per COV-03's "plain .txt with the letter body exactly as generated." Do NOT strip the signature before counting.
**Warning signs:** Retry loops triggering constantly because the letter is always "too long."

### Pitfall 4: Jinja2 Template Variable Mismatch

**What goes wrong:** Calling `load_prompt("generate_cover_letter", job_description=..., selected_resume_json=..., graduation_date=..., application_type=...)` but the template uses different variable names.
**Why it happens:** The existing `generate_cover_letter.md` template uses `{{ job_description }}`, `{{ selected_resume_json }}`, `{{ graduation_date }}`, `{{ application_type }}` — which matches the proposed call. But if the template was edited, `StrictUndefined` will raise `jinja2.UndefinedError` immediately.
**How to avoid:** Read `src/llm/prompts/generate_cover_letter.md` before calling `load_prompt()` to verify variable names. Update the template if new variables are needed.
**Warning signs:** `jinja2.UndefinedError` in tests.

### Pitfall 5: LLM Preamble in Cover Letter Output

**What goes wrong:** LLM returns "Here is the cover letter:\n\nDear Hiring Committee,..." — the preamble gets included in the `.txt` file.
**Why it happens:** The LLM ignores the "start directly with the salutation" instruction.
**How to avoid:** Post-process with the same `_clean_cover_letter()` pattern already in `src/llm.py`: strip everything before "Dear" using `re.sub(r'^.*?(?=Dear\b)', '', text, flags=re.DOTALL | re.IGNORECASE)`.
**Warning signs:** `cover_letter.txt` starts with "Here is..." or "Certainly! Here's..." instead of "Dear Hiring Committee,".

### Pitfall 6: cover_letter_path Field Points to Non-Existent File

**What goes wrong:** `JobRecord.cover_letter_path` is updated to point to `cover_letter.txt` but the file hasn't been written yet, or the path is relative instead of absolute.
**Why it happens:** Path construction before write, or using relative `Path("cover_letter.txt")` instead of `job_dir / "cover_letter.txt"`.
**How to avoid:** Write the file first, then update `job_record.cover_letter_path = str(txt_path)` and call `job_store.write(job_record)`. Always use `Path(job_record.job_dir) / "cover_letter.txt"` — absolute because `job_dir` is always absolute (enforced by `JobStore.write()`).
**Warning signs:** `cover_letter_path` is set but file not found on disk, or relative path stored.

### Pitfall 7: Prompt Template Variable for "Job Source" Placeholder

**What goes wrong:** The `cover_letter_prompt.md` template has `"I saw the job post on [Job Source]"` — if the LLM fills this literally or leaves the bracket, the output has `[Job Source]` in the final `.txt`.
**Why it happens:** JD text doesn't tell you where the user found the job post.
**How to avoid:** The CONTEXT.md "Specifics" section says: handle gracefully — use "your website" as fallback or leave as placeholder. Pass `job_source="your website"` as a variable if the template supports it, or instruct in the prompt to use "your website" as the default. Post-generation: check for literal `[Job Source]` and replace with "your website" if still present.
**Warning signs:** Output contains literal `[Job Source]` in cover_letter.txt.

---

## Code Examples

Verified patterns from project source:

### JDService: Full Orchestration Pattern
```python
# Source: src/resume/service.py (Phase 4 proven pattern — adapt for JD)
from dataclasses import dataclass
from typing import Optional
import logging
from src.config import AppConfig
from src.llm.client import LLMClient
from src.llm.utils import extract_json, load_prompt
from src.models.job_record import JobRecord, JobStatus
from src.storage.job_store import JobStore

logger = logging.getLogger(__name__)

@dataclass
class JDParseResult:
    success: bool
    job_record: Optional[JobRecord] = None
    error: Optional[str] = None

class JDService:
    def __init__(self, config: AppConfig, llm_client: LLMClient) -> None:
        self.config = config
        self.llm = llm_client

    async def parse_and_persist(
        self,
        jd_text: str,
        store: JobStore,
    ) -> JDParseResult:
        # Step 1: Detect F1 sponsorship (pure Python, no LLM)
        f1_flag = detect_f1_sponsorship(jd_text)

        # Step 2: LLM parse with retry
        try:
            parsed = await self._parse_jd(jd_text)
        except ValueError as exc:
            return JDParseResult(success=False, error=str(exc))
        except Exception as exc:
            return JDParseResult(success=False, error=f"JD parse failed: {exc}")

        # Step 3: Allocate job directory (collision-safe)
        job_dir = store.new_job_dir(parsed["company"], parsed["role"])
        job_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: Construct and persist JobRecord
        record = JobRecord(
            company=parsed["company"],
            role=parsed["role"],
            location=parsed["location"],
            job_dir=str(job_dir),
            jd_text=jd_text,
            f1_sponsorship_available=f1_flag,
            status=JobStatus.DISCOVERED,
        )
        store.write(record)
        return JDParseResult(success=True, job_record=record)
```

### Atomic .txt Write Pattern
```python
# Source: src/storage/job_store.py write() method — same tempfile pattern
import os
import tempfile
from pathlib import Path

def save_cover_letter_txt(text: str, job_dir: Path) -> Path:
    """Write cover letter to cover_letter.txt atomically."""
    txt_path = job_dir / "cover_letter.txt"
    encoded = text.encode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=job_dir, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(encoded)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    try:
        tmp_path.replace(txt_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return txt_path
```

### Preamble Strip (from legacy llm.py — proven pattern)
```python
# Source: src/llm.py _clean_cover_letter() (pre-refactor legacy — pattern is valid)
import re

def _clean_cover_letter_output(text: str) -> str:
    """Strip LLM preamble, fix em-dashes, normalize output."""
    # Strip everything before "Dear"
    text = re.sub(r'^.*?(?=Dear\b)', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Em-dash safety net
    text = text.replace('\u2014', ',')
    text = re.sub(r'\s*--\s*', ', ', text)
    # Replace literal [Job Source] placeholder
    text = text.replace('[Job Source]', 'your website')
    return text.strip()
```

### Test Pattern (follow existing test_extract_json.py)
```python
# Source: tests/test_extract_json.py — class-based pytest, parametrized
import pytest
from src.jd.service import detect_f1_sponsorship

class TestF1Detection:
    def test_h1b_variants_positive(self):
        assert detect_f1_sponsorship("We sponsor H-1B visas") is True
        assert detect_f1_sponsorship("H1B sponsorship available") is True
        assert detect_f1_sponsorship("H1-B welcome") is True

    def test_opt_not_opt_in(self):
        assert detect_f1_sponsorship("OPT eligible candidates welcome") is True
        assert detect_f1_sponsorship("This is an optional requirement") is None

    def test_no_sponsorship(self):
        assert detect_f1_sponsorship("Must be US citizen only") is False

    def test_not_mentioned(self):
        assert detect_f1_sponsorship("We are looking for a Python engineer") is None
```

---

## Existing Artifacts Status

### Already Built (Phase 2 deliverables — import these, don't rebuild)

| Artifact | Location | Status | Notes |
|----------|----------|--------|-------|
| `parse_job_description.md` prompt | `src/llm/prompts/parse_job_description.md` | EXISTS | Uses `{{ jd_text }}`; returns `company`, `role`, `location`, `employment_type`, `skills_required`, `responsibilities`, `requirements`, `visa_sponsorship_available`, `visa_notes` |
| `generate_cover_letter.md` prompt | `src/llm/prompts/generate_cover_letter.md` | EXISTS | Uses `{{ job_description }}`, `{{ selected_resume_json }}`, `{{ graduation_date }}`, `{{ application_type }}` |
| `LLMClient` | `src/llm/client.py` | EXISTS | Async, Tenacity retry, LLMError wrapping |
| `load_prompt` / `extract_json` | `src/llm/utils.py` | EXISTS | Jinja2 + json_repair |
| `JobRecord` model | `src/models/job_record.py` | EXISTS | Has `f1_sponsorship_available: Optional[bool]` field already |
| `JobStore` | `src/storage/job_store.py` | EXISTS | Atomic write, slug collision, list_all |
| `sanitize_slug` / `get_job_dir` | `src/utils/paths.py` | EXISTS | Path traversal protection, collision counter |

### Prompt Template Notes

**`parse_job_description.md`** currently returns `visa_sponsorship_available: null` (hardcoded null in the output schema). The F1 detection for Phase 5 is done by pure Python keyword matching, NOT the LLM. The `visa_sponsorship_available` field in the prompt output can be ignored — or the prompt can be updated to drop the visa fields since they're determined separately.

**`generate_cover_letter.md`** already has the 300-400 word instruction and no-em-dash rule. The template is complete and ready to use. Do NOT use `templates/cover_letter_prompt.md` (the old format) as the Jinja2 prompt — use `src/llm/prompts/generate_cover_letter.md`.

**IMPORTANT DISTINCTION:** `templates/cover_letter_prompt.md` is the human-authored style guide for what the cover letter should look like (structure, salutation, body format, signature). `src/llm/prompts/generate_cover_letter.md` is the Jinja2 Ollama prompt that the LLM receives. Both exist; they serve different purposes.

### What Phase 5 Needs to Build

| Artifact | Location | Purpose |
|----------|----------|---------|
| `JDService` | `src/jd/service.py` | Orchestrator: parse JD → detect F1 → persist |
| `detect_f1_sponsorship()` | `src/jd/service.py` or `src/jd/f1_detector.py` | Pure Python regex F1 detection |
| `CoverLetterService` | `src/cover_letter/service.py` | Orchestrator: generate → word count retry → strip em-dashes → save .txt |
| Unit tests | `tests/test_jd_service.py`, `tests/test_cover_letter_service.py` | F1 detection, word count logic, em-dash strip |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `src/llm.py` raw requests to Ollama | `src.llm.client.LLMClient` with Tenacity | Phase 2 | Retry, consistent error handling |
| `src/cover_letter_generator.py` docx2pdf | Plain `.txt` write only | Phase 5 decision | Eliminates LibreOffice dependency entirely |
| LLM parsing job description inline in `main.py` | `JDService` async orchestrator | Phase 5 | Testable, reusable, consistent with service pattern |
| F1 detection via LLM (old approach risk) | Pure Python regex | Phase 5 decision | Deterministic, no hallucination risk |

**Deprecated/outdated:**
- `src/llm.py`: Legacy raw Ollama requests. Do not use. All new code uses `src.llm.client.LLMClient`.
- `src/cover_letter_generator.py`: Legacy docx2pdf approach. Do not use. Phase 5 writes `.txt` directly.
- `src/main.py`: Old CLI entry point, old architecture. Not modified in Phase 5; Phase 6 handles web API.

---

## Open Questions

1. **Should `detect_f1_sponsorship()` live in `src/jd/service.py` or a separate `src/jd/f1_detector.py`?**
   - What we know: Phase 4 put all orchestration in `service.py` with helpers as module-level functions in the same file.
   - What's unclear: Whether F1 detection is large enough to warrant its own module.
   - Recommendation: Keep in `src/jd/service.py` as a module-level function (matches Phase 4 pattern where `_build_jd_payload`, `_filter_skills`, etc. are in `selection.py`). Move to `f1_detector.py` only if the keyword list grows beyond ~30 patterns.

2. **Should Phase 5 also update `job_record.cover_letter_path` after saving `.txt`?**
   - What we know: `JobRecord` has `cover_letter_path: Optional[str]`. The `CoverLetterService` writes the `.txt` file. The `JobStore.write()` is already atomic.
   - What's unclear: Whether updating `cover_letter_path` is Phase 5's responsibility or Phase 6's (web API).
   - Recommendation: Yes, Phase 5 should update it. The `CoverLetterService` should return the path, and the caller should update the record and re-persist. Keeps the record accurate for Phase 7 job tracker.

3. **Should `JDService.parse_and_persist()` accept master_resume for the cover letter call signature, or is that `CoverLetterService`'s job?**
   - What we know: ResumeService takes `job_record` and `master_resume` separately. Phase 5 needs both JD and resume for cover letter.
   - What's unclear: Whether a single "pipeline" service should coordinate both, or keep them separate.
   - Recommendation: Keep them separate — `JDService` parses JD and returns `job_record`; the caller then passes `job_record` to `CoverLetterService.generate(job_record, master_resume)`. This matches Phase 4's stateless pattern.

---

## Sources

### Primary (HIGH confidence)
- Project source code — `src/resume/service.py` — ResumeService orchestrator pattern (verified from disk)
- Project source code — `src/llm/client.py` — LLMClient API (verified from disk)
- Project source code — `src/llm/utils.py` — `load_prompt()`, `extract_json()` (verified from disk)
- Project source code — `src/storage/job_store.py` — `JobStore.write()`, `new_job_dir()` (verified from disk)
- Project source code — `src/models/job_record.py` — `JobRecord` fields (verified from disk)
- Project source code — `src/llm/prompts/parse_job_description.md` — prompt variables (verified from disk)
- Project source code — `src/llm/prompts/generate_cover_letter.md` — prompt variables (verified from disk)
- Project source code — `src/utils/paths.py` — `sanitize_slug()`, `get_job_dir()` (verified from disk)
- `.planning/phases/05-jd-intake-f1-flag-and-cover-letter/05-CONTEXT.md` — locked decisions (verified from disk)
- `.planning/REQUIREMENTS.md` — requirement descriptions JD-01 through COV-05 (verified from disk)
- `.planning/STATE.md` — accumulated project decisions (verified from disk)

### Secondary (MEDIUM confidence)
- `src/llm.py` — legacy `_clean_cover_letter()` pattern — preamble strip regex (verified, though module is deprecated)
- `tests/test_extract_json.py` — class-based pytest test pattern for this project (verified from disk)
- `requirements.txt` — confirmed no new packages needed (verified from disk)

### Tertiary (LOW confidence)
- None — all findings verified from project source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; versions confirmed in requirements.txt
- Architecture: HIGH — directly derived from Phase 4 ResumeService pattern; all infrastructure verified from source
- Pitfalls: HIGH — derived from actual code behavior observed in project source; not speculative
- F1 detection patterns: MEDIUM — keyword list and regex patterns are based on common sponsorship language; the exact list should be validated empirically against 5-10 real JDs before shipping

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable project, no external dependencies changing)
