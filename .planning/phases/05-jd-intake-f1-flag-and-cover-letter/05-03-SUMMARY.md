---
phase: 05-jd-intake-f1-flag-and-cover-letter
plan: "03"
subsystem: cover-letter
tags: [cover-letter, llm, async, word-count-retry, em-dash, preamble-strip, atomic-write]

# Dependency graph
requires:
  - phase: 04-resume-generation-pipeline
    provides: ResumeService stateless orchestrator pattern (config+llm constructor, async generate, dataclass result)
  - phase: 02-llm-client-and-prompt-registry
    provides: load_prompt() with Jinja2 rendering, LLMClient.call(), LLMError
  - phase: 01-storage-and-configuration
    provides: JobStore.write(), JobRecord model, AppConfig
provides:
  - CoverLetterService: async orchestrator that generates 300-400 word cover letters from JD + selected resume
  - CoverLetterResult: dataclass with success/txt_path/word_count/error fields
  - _clean_cover_letter_output(): strips LLM preamble, U+2014 em-dashes, double-hyphens, [Job Source] placeholder
  - _resolve_graduation_date(): returns (graduation_date, application_type) based on employment_type
  - _save_cover_letter_txt(): atomic tempfile+os.replace write for cover_letter.txt
  - Word-count retry loop: up to MAX_WORD_COUNT_RETRIES=2 retries when output outside [300, 400] words
  - 22 unit tests for all pure synchronous helper functions
affects:
  - 05-01 (JDService — employment_type field drives graduation date)
  - 06-fastapi-backend (wires CoverLetterService into POST /generate endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Stateless async orchestrator: config+llm at construction, call-specific state per generate() call
    - Word-count retry loop: prepend correction message to prompt, retry up to N times, accept last result
    - Atomic file write: tempfile + fsync + os.replace (same pattern as JobStore.write())
    - getattr with default for optional model fields (employment_type not yet in JobRecord)
    - Pure helper function extraction: deterministic, no I/O, unit-testable without mocks

key-files:
  created:
    - src/cover_letter/__init__.py
    - src/cover_letter/service.py
    - tests/test_cover_letter_service.py
  modified: []

key-decisions:
  - "getattr(job_record, 'employment_type', None) used as safe fallback since employment_type not yet on JobRecord (added in 05-01); service degrades gracefully to full-time default"
  - "Word count retry loop accepts last result after MAX_WORD_COUNT_RETRIES with a warning — never fails on word count; caller always gets a result"
  - "Post-processing (_clean_cover_letter_output) runs after retry loop on final output only — avoids word count drift from cleaning during retry"
  - "cover_letter_path updated on job_record and re-persisted after file is written — file existence is precondition for record update"
  - "store.write() failure on cover_letter_path update is non-fatal (warning log only) — cover_letter.txt on disk is the source of truth"

patterns-established:
  - "Word-count retry: prepend '{N} words. Please shorten/expand to [{MIN}, {MAX}].' + original prompt"
  - "Atomic cover letter write: tempfile(dir=job_dir, suffix='.tmp') + fsync + tmp_path.replace(txt_path)"
  - "Graduation date resolution: 'intern' substring (case-insensitive) -> Dec 2026; else May 2026"

requirements-completed: [COV-01, COV-02, COV-03, COV-04, COV-05]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 05 Plan 03: CoverLetterService Summary

**Stateless async CoverLetterService with 300-400 word retry loop, em-dash/preamble strip, and atomic cover_letter.txt write — 22 unit tests, 0 failures**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T09:57:25Z
- **Completed:** 2026-02-25T09:59:28Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- CoverLetterService orchestrator with async generate() following ResumeService stateless pattern
- Word-count retry loop (up to 2 retries) that prepends correction message and accepts last result gracefully
- Pure helper functions for preamble strip, em-dash normalization, graduation date resolution, atomic file write
- 22 pytest unit tests covering all deterministic helpers with 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: CoverLetterService with word-count retry loop and em-dash strip** - `6ecc4c0` (feat)
2. **Task 2: Unit tests for CoverLetterService pure logic functions** - `45629df` (test)

**Plan metadata:** `544225c` (docs: complete plan)

## Files Created/Modified
- `src/cover_letter/__init__.py` - Package exports: CoverLetterService, CoverLetterResult
- `src/cover_letter/service.py` - CoverLetterService orchestrator with generate(), CoverLetterResult dataclass, and pure helper functions
- `tests/test_cover_letter_service.py` - 22 unit tests for _clean_cover_letter_output, _resolve_graduation_date, WORD_COUNT constants

## Decisions Made
- `getattr(job_record, 'employment_type', None)` used as safe fallback since `employment_type` not yet on JobRecord (added in plan 05-01); service degrades gracefully to full-time/May 2026 default
- Word count retry loop accepts last result after MAX_WORD_COUNT_RETRIES with a warning log — never fails on word count; caller always gets a CoverLetterResult
- Post-processing (`_clean_cover_letter_output`) runs after the retry loop on final output only — avoids word count drift from cleaning during retry iterations
- `cover_letter_path` updated on job_record and re-persisted after file is written — file existence is precondition for record update (never update record before file exists)
- `store.write()` failure on cover_letter_path update is non-fatal (warning log only) — cover_letter.txt on disk is the source of truth

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `tests/test_jd_service.py` had 4 pre-existing failures (`detect_f1_sponsorship` edge cases from plan 05-01 which has not yet been executed). These are out of scope — not caused by this plan's changes. All 22 cover letter tests and all 8 extract_json tests pass with 0 failures.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CoverLetterService is complete and importable as `from src.cover_letter import CoverLetterService, CoverLetterResult`
- Requires Phase 05-01 and 05-02 to be executed for employment_type field and JDService integration
- Phase 06 (FastAPI backend) can wire CoverLetterService into POST /generate endpoint using the same pattern as ResumeService

---
*Phase: 05-jd-intake-f1-flag-and-cover-letter*
*Completed: 2026-02-25*
