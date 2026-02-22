---
phase: 02-llm-client-and-prompt-registry
plan: 03
subsystem: llm
tags: [jinja2, prompt-registry, templates, file-system-loader, strict-undefined]

# Dependency graph
requires:
  - phase: 02-02
    provides: extract_json and _strip_code_fences in utils.py — load_prompt appended to same file
provides:
  - load_prompt(name, **variables) -> str function with Jinja2 FileSystemLoader and memory caching
  - Four seed prompt templates: select_resume.md, parse_job_description.md, generate_cover_letter.md, trim_resume.md
  - StrictUndefined enforcement — missing template variables raise jinja2.UndefinedError at render time
affects: [04-resume-service, 05-job-service, 05-cover-letter-service]

# Tech tracking
tech-stack:
  added: [Jinja2>=3.0]
  patterns:
    - FileSystemLoader pointed at src/llm/prompts/ — no hardcoded prompt strings in business logic
    - Module-level _JINJA_ENV cache — Environment and compiled templates initialized once per process
    - StrictUndefined — fail-fast on variable name mismatches rather than silent empty substitution
    - FileNotFoundError with available prompt names list — actionable error for callers

key-files:
  created:
    - src/llm/prompts/select_resume.md
    - src/llm/prompts/parse_job_description.md
    - src/llm/prompts/generate_cover_letter.md
    - src/llm/prompts/trim_resume.md
  modified:
    - src/llm/utils.py
    - requirements.txt

key-decisions:
  - "Jinja2 FileSystemLoader with StrictUndefined — all prompt variables must be explicitly supplied, catches mismatches at render time"
  - "Memory caching via module-level _JINJA_ENV — process restart required to pick up prompt file edits (documented behavior, acceptable for CLI tool)"
  - "FileNotFoundError lists available prompts — callers get actionable debug info without inspecting filesystem"
  - "Prompt files use .md extension — human-readable in editors, load_prompt maps name to name.md automatically"

patterns-established:
  - "Prompt loading pattern: load_prompt('name', key=value) — no hardcoded strings in service layer"
  - "Template variable pattern: {{ variable_name }} with StrictUndefined enforcement"
  - "Prompts directory convention: src/llm/prompts/{name}.md maps to load_prompt(name)"

requirements-completed: [RES-01, RES-04, RES-06, COV-01, COV-02, JD-02, JD-03]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 2 Plan 03: Prompt Registry Summary

**Jinja2 FileSystemLoader prompt registry with StrictUndefined caching and four seed templates covering all pipeline operations (resume selection, JD parsing, cover letter generation, resume trimming)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T20:56:03Z
- **Completed:** 2026-02-22T20:57:40Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added `load_prompt(name, **variables)` to `src/llm/utils.py` with lazy-initialized Jinja2 Environment using FileSystemLoader and StrictUndefined
- Created four seed prompt templates covering all core pipeline operations (select_resume, parse_job_description, generate_cover_letter, trim_resume)
- StrictUndefined enforcement verified — missing variables raise `jinja2.UndefinedError` at render time, not silently
- `FileNotFoundError` with available prompt names list verified for missing template names
- All 8 existing `test_extract_json.py` tests remain green — no regressions from adding load_prompt

## Task Commits

Each task was committed atomically:

1. **Task 1: Add load_prompt() to src/llm/utils.py with Jinja2 registry** - `7d97263` (feat)
2. **Task 2: Create four seed prompt template files in src/llm/prompts/** - `856af12` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `src/llm/utils.py` - Added `_JINJA_ENV` cache, `_get_jinja_env()` helper, and `load_prompt()` function
- `requirements.txt` - Added `Jinja2>=3.0`
- `src/llm/prompts/select_resume.md` - Selects experiences/projects/skills from master resume JSON for a job
- `src/llm/prompts/parse_job_description.md` - Extracts structured fields (company, role, skills, responsibilities) from raw JD text
- `src/llm/prompts/generate_cover_letter.md` - Writes 300-400 word tailored cover letter with strict writing rules
- `src/llm/prompts/trim_resume.md` - Shortens bullet points in overflow sections to fit resume on single page

## Decisions Made
- Jinja2 FileSystemLoader with StrictUndefined chosen so variable name mismatches fail fast at render time rather than silently producing wrong output
- Module-level `_JINJA_ENV` cache — process restart picks up prompt file edits, acceptable for a CLI/single-user tool
- `FileNotFoundError` lists available prompts — gives callers actionable debug info without needing to inspect the filesystem manually

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `load_prompt()` is ready for Phase 3 (any remaining Phase 2 plans) and Phase 4 (ResumeService) and Phase 5 (JobService, CoverLetterService)
- All four seed templates are syntactically valid Jinja2 and will be refined in Phases 4-5
- Downstream phases can import `from src.llm.utils import load_prompt` immediately

## Self-Check: PASSED

- FOUND: src/llm/utils.py
- FOUND: src/llm/prompts/select_resume.md
- FOUND: src/llm/prompts/parse_job_description.md
- FOUND: src/llm/prompts/generate_cover_letter.md
- FOUND: src/llm/prompts/trim_resume.md
- FOUND: 02-03-SUMMARY.md
- FOUND: commit 7d97263 (Task 1)
- FOUND: commit 856af12 (Task 2)

---
*Phase: 02-llm-client-and-prompt-registry*
*Completed: 2026-02-22*
