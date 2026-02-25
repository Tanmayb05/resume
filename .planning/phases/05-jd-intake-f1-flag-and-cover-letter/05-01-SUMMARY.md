---
phase: 05-jd-intake-f1-flag-and-cover-letter
plan: "01"
subsystem: jd-intake
tags: [regex, f1-detection, sponsorship, keyword-matching, tdd, pytest]

# Dependency graph
requires: []
provides:
  - "detect_f1_sponsorship(jd_text: str) -> Optional[bool] pure Python function"
  - "src/jd/__init__.py package init"
  - "tests/test_jd_service.py TestF1Detection test suite (27 tests)"
affects:
  - "05-02 (JDService orchestrator imports detect_f1_sponsorship)"
  - "05-03 (CoverLetterService — same phase)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD: RED (failing import) -> GREEN (27/27 pass) -> implementation done"
    - "Double lookbehind (?<!no )(?<!no visa ) to exclude negative-context substrings from positive regex"
    - "Negative lookahead on authorize[ds] to work prevents false positive on 'authorized to work without sponsorship'"
    - "H-1B/H1-B/H 1 B normalization via re.sub before pattern matching"

key-files:
  created:
    - src/jd/__init__.py
    - src/jd/service.py
    - tests/test_jd_service.py
  modified: []

key-decisions:
  - "detect_f1_sponsorship() lives in src/jd/service.py as a module-level function — matches Phase 4 pattern where helper functions live alongside orchestrators"
  - "Added 'must already be authorized' as a negative signal — handles the conflicting-signals test case from plan spec"
  - "Double lookbehind on sponsorship patterns rather than a pre-filter approach — keeps patterns self-contained"
  - "Lookahead on authorize[ds] to work excludes the 'authorized to work without sponsorship' negative case"

patterns-established:
  - "Pattern: H-1B variant normalization via re.sub(r'h[\\-\\s]?1[\\-\\s]?b', 'h1b', text) before regex matching"
  - "Pattern: Double lookbehind for positive patterns that appear as substrings in negative phrases"

requirements-completed: [JD-03]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 05 Plan 01: F1 Sponsorship Keyword Detector Summary

**Pure Python regex detector for F1/H-1B sponsorship signals with normalized H-1B variants, OPT false-positive guard, and XOR logic for ambiguous cases — 27 tests, 0 failures.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-25T09:56:50Z
- **Completed:** 2026-02-25T10:02:00Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 3

## Accomplishments

- Wrote 27 tests covering all plan behavior cases (positive/negative/None/false-positive guards) before implementation
- Implemented `detect_f1_sponsorship()` with H-1B/H1-B/H 1 B normalization, OPT lookahead guard, and XOR positive/negative logic
- Fixed 4 regex edge cases discovered during GREEN phase: `visa sponsorship` substring in "no visa sponsorship", `sponsorship available` substring, `h1b` in "do not sponsor h1b", and `authorized to work` in "authorized to work without sponsorship"
- All 27 tests pass; all plan verification spot-checks confirmed correct

## Task Commits

Each task was committed atomically:

1. **RED — Failing tests** - `cf44bca` (test)
2. **GREEN — Implementation** - `51c6380` (feat)

_Note: TDD plan — separate RED and GREEN commits per TDD protocol_

## Files Created/Modified

- `/Users/tanmaybhuskute/Documents/resume/src/jd/__init__.py` — Package init for jd module
- `/Users/tanmaybhuskute/Documents/resume/src/jd/service.py` — `detect_f1_sponsorship()` pure Python function with `_POSITIVE_PATTERNS` and `_NEGATIVE_PATTERNS` lists
- `/Users/tanmaybhuskute/Documents/resume/tests/test_jd_service.py` — `TestF1Detection` class with 27 tests

## Decisions Made

- **`detect_f1_sponsorship()` in `src/jd/service.py` as module-level function** — plan spec says "Do NOT create JDService class yet — that is Plan 02". Function co-located with its module; can be split to `f1_detector.py` if keyword list grows past ~30 patterns.
- **Added `must already be authorized` as negative signal** — The plan spec case "We sponsor H-1B but must already be authorized" -> None required a negative signal that implied "applicant must already have work auth". Adding this pattern produces the conflicting-signals (both positive h1b + negative must-already-authorized) -> None result correctly.
- **Double lookbehind on `sponsorship available` and `visa sponsorship` patterns** — The substrings "visa sponsorship" and "sponsorship available" appear inside "no visa sponsorship available", causing false positive if only positive patterns were checked. Fixed with `(?<!no )(?<!no visa )` compound lookbehinds.
- **Negative lookahead on `authorize[ds]? to work`** — "authorized to work in the US without sponsorship" contains "authorized to work" as a substring. Added `(?!\s+(?:(?:\w+\s+){0,5})?without\s+sponsorship)` lookahead to exclude this case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 4 regex edge cases discovered during GREEN phase**
- **Found during:** GREEN phase (running tests after initial implementation)
- **Issue:** Initial `_POSITIVE_PATTERNS` matched substrings inside negative phrases:
  1. `\bvisa\s+sponsorship\b` matched inside "no visa sponsorship available"
  2. `\bsponsorship\s+(?:is\s+)?(?:available|provided|offered)\b` matched inside "no visa sponsorship available"
  3. `\bh1b\b` matched inside "do not sponsor h1b" after normalization
  4. `\bauthorize[ds]?\s+to\s+work\b` matched inside "authorized to work in the US without sponsorship"
- **Fix:** Added targeted lookbehinds and lookaheads to each affected pattern; added `must already be authorized` negative pattern for the conflicting-signals case
- **Files modified:** `src/jd/service.py`
- **Verification:** All 27 tests pass including all 4 previously failing cases
- **Committed in:** `51c6380` (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Required to achieve plan success criteria. Pattern refinement is expected in TDD — the RED→GREEN iteration surfaced the edge cases the tests were designed to catch. No scope creep.

## Issues Encountered

None beyond the regex edge cases documented above (which are the expected output of TDD).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `detect_f1_sponsorship()` is importable from `src.jd.service` and ready for Plan 02 (`JDService` orchestrator)
- Plan 02 will add `JDService` class alongside `detect_f1_sponsorship()` in the same `src/jd/service.py` file
- All 27 tests will continue to run as part of the test suite

---
*Phase: 05-jd-intake-f1-flag-and-cover-letter*
*Completed: 2026-02-25*
