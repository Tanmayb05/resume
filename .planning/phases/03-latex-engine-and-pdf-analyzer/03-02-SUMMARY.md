---
phase: 03-latex-engine-and-pdf-analyzer
plan: 02
subsystem: latex
tags: [tectonic, pymupdf, fitz, subprocess, pdf-analysis, latex-compilation]

# Dependency graph
requires:
  - phase: 03-latex-engine-and-pdf-analyzer-plan-01
    provides: src/latex/__init__.py with render_resume_tex()
provides:
  - compile_tex(tex_path, output_dir) — tectonic subprocess wrapper with structured error dict returns
  - check_ats_parsability(pdf_path) — pdftotext-based ATS text extraction check
  - analyze_pdf(pdf_path) — PyMuPDF page count, whitespace ratio, and page height metrics
  - src/latex package fully exports all three stages of render-compile-measure chain
affects: [04-resume-service, phase 4 enforcement loop, overflow detection, trim/expand decisions]

# Tech tracking
tech-stack:
  added: [tectonic (subprocess), PyMuPDF/fitz (already in requirements.txt)]
  patterns:
    - Structured error dict returns — never raise raw subprocess exceptions; error_type discriminator
    - Sentinel error values — page_count=-1, whitespace_ratio=-1.0 on failure for safe caller checks
    - Thin subprocess wrapper — iter_N naming responsibility left to caller, not compiler

key-files:
  created:
    - src/latex/compiler.py
    - src/latex/pdf_analyzer.py
  modified:
    - src/latex/__init__.py

key-decisions:
  - "compile_tex does not handle iter_N naming — caller (Phase 4) names .tex file, tectonic derives PDF name from stem"
  - "check_ats_parsability returns True when pdftotext not installed — non-blocking, assume OK"
  - "analyze_pdf page_height_inches field enables Phase 4 single-tall-page overflow detection (> 11.5in)"
  - "Generic Exception catch in analyze_pdf covers PyMuPDF's internal FileNotFoundError variant"

patterns-established:
  - "Structured error dict: all subprocess wrappers return {success, error_type, stderr, return_code} on failure"
  - "Sentinel contract: {success=False, page_count=-1, whitespace_ratio=-1.0} guarantees callers can check success key"
  - "Thin wrapper principle: compiler.py adds zero business logic — that belongs in Phase 4 ResumeService"

requirements-completed: [RES-03, RES-05]

# Metrics
duration: 1min
completed: 2026-02-22
---

# Phase 03 Plan 02: LaTeX Compiler and PDF Analyzer Summary

**tectonic subprocess compiler (compile_tex) and PyMuPDF analyzer (analyze_pdf) providing structured error dicts and sentinel returns for the Phase 4 render-compile-measure enforcement loop**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-22T21:23:08Z
- **Completed:** 2026-02-22T21:24:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- compile_tex() wraps tectonic CLI via subprocess with 60s timeout and structured error_type discriminator (compilation_failed | timeout | tectonic_not_found)
- check_ats_parsability() uses pdftotext to verify ATS-readable text extraction; returns True when tool unavailable (non-blocking)
- analyze_pdf() uses PyMuPDF (fitz) to return page_count, whitespace_ratio (clamped 0.0-1.0), and page_height_inches for overflow detection
- Validated against real PDF: templates/resume_template.pdf → page_count=1, whitespace_ratio=0.168, page_height_inches=11.0
- src/latex/__init__.py updated to export all four symbols from the render-compile-measure chain

## Task Commits

Each task was committed atomically:

1. **Task 1: Create compile_tex() tectonic subprocess wrapper** - `ea9e6cb` (feat)
2. **Task 2: Create analyze_pdf() PyMuPDF analyzer** - `b4917cf` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/latex/compiler.py` — compile_tex() and check_ats_parsability() — 100 lines
- `src/latex/pdf_analyzer.py` — analyze_pdf() using fitz.open() — 101 lines
- `src/latex/__init__.py` — updated to export compile_tex, check_ats_parsability, analyze_pdf

## Decisions Made
- compile_tex does not handle iter_N naming: caller (Phase 4 ResumeService) names the .tex file with _iter_N suffix; tectonic derives PDF name from stem, so resume_iter_0.tex → resume_iter_0.pdf. Keeps compiler as thin subprocess wrapper.
- check_ats_parsability returns True when pdftotext not installed — tool may not be present on all machines; non-blocking assumption prevents CI failures on developer machines.
- analyze_pdf page_height_inches field enables Phase 4 to detect single-tall-page overflow (tectonic Pitfall 3): page_count=1 but height > 11.5 inches signals overflow without page break.
- PyMuPDF's fitz.open() raises a different exception type than FileNotFoundError for missing files; the generic Exception catch covers both cases correctly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- PyMuPDF catches missing-file conditions internally and raises a fitz-specific exception rather than Python's FileNotFoundError. The generic Exception catch in analyze_pdf handles this correctly, returning the sentinel dict with `error: "Error analyzing PDF: no such file: '/path'"`. Sentinel contract is honored.

## User Setup Required
None - no external service configuration required. tectonic must be installed for compile_tex to produce PDFs (brew install tectonic), but compiler gracefully returns error_type="tectonic_not_found" when missing.

## Next Phase Readiness
- Phase 4 can call compile_tex() and analyze_pdf() directly with `if result["page_count"] > 1: trigger_trim()`
- All three stages of render-compile-measure chain are importable from `src.latex`
- Single-tall-page overflow detection available via page_height_inches > 11.5
- Whitespace threshold calibration (40% EXPAND trigger) deferred to Phase 4 empirical validation

---
*Phase: 03-latex-engine-and-pdf-analyzer*
*Completed: 2026-02-22*

## Self-Check: PASSED

- FOUND: src/latex/compiler.py
- FOUND: src/latex/pdf_analyzer.py
- FOUND: src/latex/__init__.py
- FOUND: .planning/phases/03-latex-engine-and-pdf-analyzer/03-02-SUMMARY.md
- FOUND: commit ea9e6cb (Task 1)
- FOUND: commit b4917cf (Task 2)
