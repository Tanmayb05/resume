---
phase: 02-llm-client-and-prompt-registry
plan: 02
subsystem: api
tags: [json, llm, testing, pytest, tdd, json-repair, code-fence, utility]

# Dependency graph
requires:
  - phase: 02-llm-client-and-prompt-registry
    provides: LLMClient async wrapper over ollama.AsyncClient with Tenacity retry

provides:
  - extract_json(text) utility that strips all markdown code fence variants and repairs malformed JSON
  - _strip_code_fences() helper for regex-based code fence removal
  - pytest test suite with 8 test cases covering all fence and error scenarios

affects: [03-jd-parser, 04-resume-selection, 05-cover-letter, 06-api-layer]

# Tech tracking
tech-stack:
  added: [json-repair>=0.30.0, pytest>=9.0.0]
  patterns: [TDD red-green cycle, JSON repair fallback pattern, ValueError with context for parse failures]

key-files:
  created:
    - src/llm/utils.py
    - tests/__init__.py
    - tests/test_extract_json.py
  modified:
    - requirements.txt

key-decisions:
  - "json-repair used instead of fix-busted-json — fix-busted-json 0.0.19 crashes on Python 3.13 with IndexError in eat_concatenated_strings; json-repair is maintained and Python 3.13 compatible"
  - "ValueError raised with first 300 chars of input when repair_json returns empty/null — gives callers actionable debug info"
  - "repair_json empty-string guard added — json-repair returns empty string for both empty input and plain text, so we must check before json.loads to produce correct ValueError"

patterns-established:
  - "extract_json() is the single entry point for all LLM JSON parsing — callers never call json.loads directly on LLM output"
  - "Two-phase parse: fast path (json.loads) then repair path (repair_json) — avoids dependency on repair for valid JSON"
  - "ValueError includes input context (first 300 chars) — parse failures produce logs with actionable information"

requirements-completed: [RES-01, RES-04, COV-01, JD-02]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 2 Plan 2: extract_json with TDD — fence stripping and malformed JSON repair Summary

**`extract_json()` utility using json-repair for robust code fence stripping and malformed JSON repair, with 8-case pytest suite verified in TDD red-green cycle**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T20:51:58Z
- **Completed:** 2026-02-22T20:53:44Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 4

## Accomplishments
- Wrote 8 failing tests covering all fence variants (json fence, bare fence, no fence, surrounding text+fence), malformed JSON repair, and ValueError cases — RED phase confirmed
- Implemented extract_json() with regex-based fence stripping via _strip_code_fences() and two-phase parse (fast path + repair) using json-repair — GREEN phase confirmed, all 8 tests pass
- Added pytest and json-repair to requirements.txt; created tests/ package with __init__.py for pytest discovery

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing tests for extract_json** - `05e2e99` (test)
2. **Task 2: GREEN — Implement extract_json with fence stripping and json-repair** - `6fcd524` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/llm/utils.py` - extract_json() and _strip_code_fences() utility functions
- `tests/__init__.py` - Empty package marker enabling pytest discovery
- `tests/test_extract_json.py` - 8 pytest test cases in 3 classes (Fences, Repair, Errors)
- `requirements.txt` - Added json-repair>=0.30.0 and pytest>=9.0.0

## Decisions Made
- Used json-repair instead of fix-busted-json: fix-busted-json 0.0.19 crashes with IndexError on Python 3.13 in eat_concatenated_strings(); json-repair 0.58.0 works correctly
- Added empty-string guard after repair_json: the library returns "" for both empty input and plain text, so we check before attempting json.loads to ensure correct ValueError is raised
- ValueError message includes first 300 chars of raw input: LLM output parse failures need actionable context to debug prompt/model issues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced fix-busted-json with json-repair due to Python 3.13 incompatibility**
- **Found during:** Task 2 (GREEN — implement extract_json)
- **Issue:** fix-busted-json 0.0.19 raises IndexError: string index out of range in eat_concatenated_strings() when called on Python 3.13; the library is incompatible with this Python version
- **Fix:** Installed json-repair 0.58.0 which provides an equivalent repair_json() API and is Python 3.13 compatible; updated import in src/llm/utils.py; added json-repair to requirements.txt
- **Files modified:** src/llm/utils.py, requirements.txt
- **Verification:** All 8 tests pass including malformed JSON repair tests; json_repair importable in Python 3.13
- **Committed in:** `6fcd524` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug — library incompatibility)
**Impact on plan:** Essential fix — without it the malformed JSON repair tests would fail. Equivalent API maintained; no behavioral difference for callers.

## Issues Encountered
- fix-busted-json 0.0.19 crashes on Python 3.13 with IndexError in its internal eat_concatenated_strings() method. Switched to json-repair which has identical callable interface (repair_json(str) -> str) and is actively maintained.

## User Setup Required
None - no external service configuration required. All dependencies installed via pip.

## Next Phase Readiness
- extract_json() is ready for use by JD parser (Phase 3), resume selector (Phase 4), and cover letter generator (Phase 5)
- All LLM responses producing JSON should go through extract_json() — never json.loads() directly
- test infrastructure (pytest, tests/) established and ready for future test additions

---
*Phase: 02-llm-client-and-prompt-registry*
*Completed: 2026-02-22*
