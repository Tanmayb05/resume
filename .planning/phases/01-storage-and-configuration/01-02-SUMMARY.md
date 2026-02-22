---
phase: 01-storage-and-configuration
plan: 02
subsystem: database
tags: [pydantic, filesystem, persistence, json, atomic-write, slug, pathlib]

# Dependency graph
requires:
  - phase: 01-storage-and-configuration
    plan: 01
    provides: "JobRecord Pydantic v2 model and AppConfig — imported by JobStore"
provides:
  - sanitize_slug() helper converting arbitrary user input to filesystem-safe lowercase slug with path traversal rejection
  - get_job_dir() helper returning collision-safe absolute Path with silent auto-increment
  - JobStore class with write() (atomic via tempfile+os.replace), read(), list_all() sorted by created_at desc
  - Package markers for src, src/utils, src/storage namespaces
  - Clean requirements.txt: anthropic, pydantic, pydantic-settings, PyMuPDF, requests only
affects: [03-llm-client, 04-resume-generation, 05-cover-letter, 06-api, 07-web-ui]

# Tech tracking
tech-stack:
  added: [anthropic>=0.40.0, pydantic>=2.7.0, pydantic-settings>=2.13.0, PyMuPDF>=1.24.0, requests>=2.31.0]
  patterns:
    - Atomic file write pattern: NamedTemporaryFile + os.fsync + os.replace — prevents partial writes on crash
    - Slug sanitization with pre-check before character stripping to catch path traversal that would otherwise normalize away
    - Collision-safe directory naming via silent counter increment (-2, -3, ...) with WARNING log above 10

key-files:
  created:
    - src/utils/__init__.py
    - src/utils/paths.py
    - src/storage/__init__.py
    - src/storage/job_store.py
    - src/__init__.py
  modified:
    - requirements.txt

key-decisions:
  - "No python-slugify dependency — slug sanitization uses stdlib re with custom rules for full control and zero extra dependency"
  - "Path traversal pre-check before re.sub stripping — catches '../../../etc' before character stripping makes it appear safe"
  - "Atomic write via tempfile+fsync+os.replace — guarantees job.json is never left in a partially-written state"
  - "list_all() silently skips invalid directories (logged at DEBUG) — robust to manually created dirs without job.json"
  - "write() rejects relative job_dir with ValueError — enforces absolute-path invariant at storage layer boundary"

patterns-established:
  - "Persistence pattern: JobRecord -> model_dump_json() -> atomic tempfile write -> job.json; reverse via model_validate_json()"
  - "Directory naming pattern: <company-slug>-<role-slug> with -2/-3 counter on collision; always resolved to absolute path"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 1 Plan 02: Path Utilities and JobStore Summary

**Atomic filesystem persistence layer with slug sanitization (path traversal rejection), collision-safe directory naming, and JobStore write/read/list_all using tempfile+os.replace**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T16:24:48Z
- **Completed:** 2026-02-22T16:26:36Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- `sanitize_slug()` converts company/role names to lowercase dash-separated slugs; pre-check rejects path traversal sequences before character stripping would make them appear safe
- `get_job_dir()` returns absolute collision-safe path with silent auto-increment (-2, -3) and WARNING log when counter exceeds 10
- `JobStore.write()` uses NamedTemporaryFile + os.fsync + os.replace for atomic, crash-safe writes to job.json
- `JobStore.read()` validates JSON via Pydantic's model_validate_json(); raises FileNotFoundError or ValueError on failure
- `JobStore.list_all()` silently skips directories without valid job.json (logged at DEBUG), returns records sorted most-recent-first
- requirements.txt cleaned: anthropic, pydantic, pydantic-settings, PyMuPDF, requests — removed python-docx, docx2pdf, PyYAML

## Task Commits

Each task was committed atomically:

1. **Task 1: Path utilities — sanitize_slug and get_job_dir** - `072eb12` (feat)
2. **Task 2: JobStore filesystem CRUD and requirements update** - `02a9b8a` (feat)

**Plan metadata:** (docs commit — created below)

## Files Created/Modified

- `src/utils/__init__.py` - Empty package marker for utils package (6 bytes)
- `src/utils/paths.py` - sanitize_slug() and get_job_dir() helpers; 104 lines
- `src/storage/__init__.py` - Empty package marker for storage package (6 bytes)
- `src/storage/job_store.py` - JobStore class with write/read/list_all; 127 lines
- `src/__init__.py` - Empty package marker for src root package (6 bytes)
- `requirements.txt` - Cleaned to 5 canonical dependencies; removed 3 obsolete packages

## Decisions Made

- **No python-slugify:** Slug sanitization implemented with stdlib `re` per RESEARCH.md recommendation — custom logic gives full control and avoids an extra dependency.
- **Pre-check before character stripping:** The traversal check (`".." in text`) runs on the raw lowercased input before `re.sub` strips non-alphanumeric characters. Without this, `../../../etc` would sanitize to `etc` and appear safe.
- **Atomic write via tempfile+fsync+os.replace:** Writes to a temporary file in the same directory (ensuring same filesystem), fsync for durability, then os.replace() which is POSIX-atomic. job.json is never partially written.
- **list_all() skips invalid dirs at DEBUG:** Non-job directories (e.g., manually created folders) don't raise — they're skipped with a DEBUG-level log. Keeps list_all() robust without hiding real failures.
- **write() enforces absolute job_dir:** ValueError raised immediately if job_dir is relative — prevents subtle bugs where records written with a relative path become unresolvable when cwd changes.

## Deviations from Plan

None — plan executed exactly as written. All code follows the exact structure specified in the plan, including the JobStore class body, error messages, and requirements.txt content.

## Issues Encountered

None. All verifications passed on first run.

## User Setup Required

None — no external service configuration required. All dependencies are available via pip install -r requirements.txt.

## Next Phase Readiness

- Full Phase 1 data layer complete: JobRecord + AppConfig (Plan 01) + JobStore + paths (Plan 02)
- Any downstream phase can `from src.storage.job_store import JobStore` and `from src.models.job_record import JobRecord`
- No blockers for Phase 2 or any other phase that depends on persistence

---
*Phase: 01-storage-and-configuration*
*Completed: 2026-02-22*
