---
phase: 01-storage-and-configuration
plan: 01
subsystem: database
tags: [pydantic, pydantic-settings, python-dotenv, models, config, environment]

# Dependency graph
requires: []
provides:
  - JobRecord Pydantic v2 model with UUID id, company, role, location, status, timestamps, job_dir, and optional artifact path fields
  - JobStatus enum with DISCOVERED, PROCESSING, READY, APPLIED values (str enum, use_enum_values=True)
  - AppConfig pydantic-settings class with APP_ env prefix, fail-fast on missing anthropic_api_key, absolute data_dir resolution
affects: [02-job-store, 03-llm-client, 04-resume-generation, 05-cover-letter, 06-api, 07-web-ui]

# Tech tracking
tech-stack:
  added: [pydantic>=2.0, pydantic-settings>=2.0, python-dotenv>=0.21.0]
  patterns:
    - Pydantic v2 API (model_dump_json, model_validate_json, ConfigDict) — no v1 shims
    - pydantic-settings BaseSettings with env_prefix for namespaced env vars
    - field_validator with mode="after" for path resolution at config load time

key-files:
  created:
    - src/models/__init__.py
    - src/models/job_record.py
    - src/config.py
    - .env.example
  modified:
    - requirements.txt

key-decisions:
  - "use_enum_values=True in JobRecord.model_config so JSON output contains string values not enum objects"
  - "APP_ env prefix on AppConfig prevents collisions with system env vars"
  - "data_dir resolved to absolute path via field_validator — no relative-path bugs when cwd differs"
  - "anthropic_api_key has no default — fails immediately at instantiation if missing, never silently continues"
  - "mark_updated() is a simple helper; no custom to_json/from_json wrappers — call sites use model_dump_json() directly"

patterns-established:
  - "Data model pattern: Pydantic v2 BaseModel with ConfigDict, Optional fields default None, datetimes auto-set via default_factory"
  - "Config pattern: pydantic-settings BaseSettings with .env file, APP_ prefix, required fields raise ValidationError on startup"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 1 Plan 01: JobRecord Model and AppConfig Summary

**JobRecord Pydantic v2 model with UUID id and lifecycle status enum, plus AppConfig pydantic-settings class with fail-fast API key validation and absolute path resolution**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T16:20:59Z
- **Completed:** 2026-02-22T16:22:40Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- JobRecord Pydantic v2 model with all required fields (id, company, role, location, status, timestamps, job_dir) and optional artifact fields (jd_text, f1_sponsorship_available, resume_pdf_path, cover_letter_path, generation_iterations)
- JobStatus str enum with four lifecycle values: DISCOVERED, PROCESSING, READY, APPLIED
- AppConfig pydantic-settings class replacing legacy PyYAML loader; raises ValidationError at instantiation if APP_ANTHROPIC_API_KEY is missing
- data_dir field always resolved to absolute path via field_validator — safe regardless of working directory at runtime
- .env.example template at project root with all configurable fields documented

## Task Commits

Each task was committed atomically:

1. **Task 1: JobRecord Pydantic model and JobStatus enum** - `89105c8` (feat)
2. **Task 2: AppConfig via pydantic-settings** - `c0c6bb3` (feat)

**Plan metadata:** (docs commit — created below)

## Files Created/Modified

- `src/models/__init__.py` - Empty package marker for models package
- `src/models/job_record.py` - JobRecord BaseModel + JobStatus enum; pure data class with mark_updated() helper
- `src/config.py` - AppConfig BaseSettings replacing legacy PyYAML Config class; APP_ prefixed env vars
- `.env.example` - Template documenting all configurable environment variables
- `requirements.txt` - Added pydantic>=2.0, pydantic-settings>=2.0, python-dotenv>=0.21.0

## Decisions Made

- **Pydantic v2 API only:** Used model_dump_json(), model_validate_json(), ConfigDict — no v1 shims. Keeps the codebase forward-compatible.
- **use_enum_values=True:** Ensures JobStatus values serialize as plain strings ("discovered") in JSON, not enum objects. Matches the must_have truth that `r.status == 'discovered'`.
- **APP_ env prefix:** Avoids collisions with common system env vars (e.g., plain `DATA_DIR` could shadow something else). All app config is namespaced.
- **No custom serialization wrappers:** model_dump_json() / model_validate_json() called at use sites — keeps JobRecord a pure data class with no behavior duplication.
- **pydantic and pydantic-settings added to requirements.txt:** These were missing from requirements.txt before this plan — added as Rule 2 fix since they are critical dependencies.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed pydantic and pydantic-settings into project venv**
- **Found during:** Task 1 (JobRecord model creation)
- **Issue:** pydantic and pydantic-settings not installed in project .venv; import would fail
- **Fix:** Ran `pip install "pydantic>=2.0" "pydantic-settings>=2.0"` in project venv
- **Files modified:** .venv (virtual environment packages), requirements.txt
- **Verification:** `python -c "import pydantic; import pydantic_settings"` succeeds
- **Committed in:** c0c6bb3 (Task 2 commit, requirements.txt update included)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing dependency)
**Impact on plan:** Required installation; no scope creep. Both tasks completed as specified.

## Issues Encountered

None beyond the missing pydantic installation (handled as Rule 3 deviation above).

## User Setup Required

To run the application, create a `.env` file at the project root based on `.env.example`:

```
APP_ANTHROPIC_API_KEY=sk-ant-your-key-here
APP_DATA_DIR=data
APP_MAX_ITERATIONS=5
```

The APP_ANTHROPIC_API_KEY is required — the app will refuse to start without it.

## Next Phase Readiness

- JobRecord and AppConfig are ready for Plan 02 (JobStore filesystem layer)
- Plan 02 can import from `src.models.job_record` and `src.config` without any changes to this plan's output
- No blockers

---
*Phase: 01-storage-and-configuration*
*Completed: 2026-02-22*
