---
phase: 05-jd-intake-f1-flag-and-cover-letter
plan: "02"
subsystem: api
tags: [jd-intake, llm, job-record, job-store, async, orchestrator]

# Dependency graph
requires:
  - phase: 05-01
    provides: detect_f1_sponsorship() function already in src/jd/service.py
  - phase: 04-03
    provides: ResumeService stateless async orchestrator pattern
  - phase: 01-02
    provides: JobStore.new_job_dir() collision-safe directory allocation
  - phase: 02-01
    provides: LLMClient.call() + LLMError
  - phase: 02-02
    provides: load_prompt() + extract_json() from src.llm.utils

provides:
  - JDService stateless async orchestrator (parse_and_persist, _parse_jd)
  - JDParseResult dataclass (success, job_record, error)
  - src/jd/__init__.py full public API exports

affects:
  - phase-06-api: imports JDService for /jobs/intake endpoint
  - phase-07: end-to-end integration uses JDService as entry point

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stateless async orchestrator pattern (matching ResumeService)"
    - "LLM parse with 2-attempt retry — strict prompt fallback on attempt 2"
    - "Validate raw dict before constructing Pydantic model (avoid partial JobRecord)"
    - "store.new_job_dir() always used — never manual slug construction"

key-files:
  created: []
  modified:
    - src/jd/service.py
    - src/jd/__init__.py

key-decisions:
  - "JobRecord has no skills_required/responsibilities/requirements fields — only company/role/location/jd_text/f1_sponsorship_available stored; LLM parse dict fields unused beyond required 3"
  - "parse_job_description.md has no strict_mode parameter — attempt 2 appends IMPORTANT instruction to base prompt instead"
  - "JobStore constructor takes data_dir: Path, not AppConfig — smoke test uses config.data_dir directly"

patterns-established:
  - "JDService follows identical constructor signature to ResumeService: __init__(config, llm_client)"
  - "JDParseResult mirrors ResumeGenerationResult: success flag + optional result + optional error string"
  - "Strict field validation (required fields from raw dict) before ANY Pydantic model construction or disk write"

requirements-completed: [JD-01, JD-02, JD-04]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 5 Plan 02: JDService Orchestrator Summary

**JDService stateless async orchestrator wiring F1 detection, LLM parse-with-retry, and collision-safe JobStore persistence into parse_and_persist()**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T10:04:13Z
- **Completed:** 2026-02-25T10:05:41Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added JDParseResult dataclass and JDService class to src/jd/service.py (adding to existing detect_f1_sponsorship() from Plan 01)
- parse_and_persist() validates required fields before any disk writes, uses store.new_job_dir() for collision-safe directory allocation
- _parse_jd() implements 2-attempt LLM retry pattern with strict fallback prompt on attempt 2
- Updated src/jd/__init__.py to export full public API (JDService, JDParseResult, detect_f1_sponsorship)
- All 27 Plan 01 regression tests pass after Plan 02 additions

## Task Commits

Each task was committed atomically:

1. **Task 1: JDParseResult dataclass + JDService orchestrator** - `9a00b6c` (feat)
2. **Task 2: Update src/jd/__init__.py exports + integration smoke test** - `f004447` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/jd/service.py` - Added JDParseResult dataclass, JDService class, _REQUIRED_FIELDS, _MAX_PARSE_ATTEMPTS constants
- `src/jd/__init__.py` - Updated to export JDService, JDParseResult, detect_f1_sponsorship with __all__

## Decisions Made
- JobRecord model has no skills_required/responsibilities/requirements fields — LLM-parsed extra fields from parse_job_description.md are not stored; only the 3 required fields plus jd_text and f1_sponsorship_available are placed on JobRecord
- parse_job_description.md has no strict_mode template variable — attempt 2 appends a hardcoded IMPORTANT instruction to the rendered base prompt rather than passing strict_mode=True as a Jinja2 variable
- JobStore constructor signature is `__init__(self, data_dir: Path)` not `(self, config: AppConfig)` — smoke test calls `JobStore(config.data_dir)` directly

## Deviations from Plan

None - plan executed exactly as written. The only adaptations were working around actual API signatures (JobStore takes data_dir not config, parse_job_description.md has no strict_mode parameter) which the plan explicitly anticipated with "check job_record.py for actual field names" and "IF the template supports strict_mode, otherwise repeat with appended instruction."

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- src.jd package fully exported: JDService, JDParseResult, detect_f1_sponsorship
- Phase 6 FastAPI endpoint can import JDService and call parse_and_persist(jd_text, store) directly
- All Phase 5 Plan 01 regression tests still pass (27/27)

## Self-Check: PASSED

- FOUND: src/jd/service.py
- FOUND: src/jd/__init__.py
- FOUND: .planning/phases/05-jd-intake-f1-flag-and-cover-letter/05-02-SUMMARY.md
- FOUND commit: 9a00b6c (feat(05-02): add JDParseResult dataclass and JDService orchestrator)
- FOUND commit: f004447 (feat(05-02): update src/jd/__init__.py with full Phase 5 JD public API exports)
- 27/27 tests pass in tests/test_jd_service.py

---
*Phase: 05-jd-intake-f1-flag-and-cover-letter*
*Completed: 2026-02-25*
