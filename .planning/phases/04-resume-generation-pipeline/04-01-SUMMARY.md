---
phase: 04-resume-generation-pipeline
plan: "01"
subsystem: resume
tags: [llm, jinja2, selection, master-resume, keyword-filter, json]

# Dependency graph
requires:
  - phase: 02-llm-client-and-prompt-registry
    provides: load_prompt, extract_json, LLMClient
  - phase: 01-storage-and-configuration
    provides: JobRecord, AppConfig, job_dir
provides:
  - LLM-driven content selection module (src/resume/selection.py)
  - Updated select_resume.md prompt accepting jd_fields + master_resume_json
  - selected_resume.json written to job_dir on each call
  - resume_json_template.json-compatible payload assembly
affects:
  - 04-02 (validation and schema checking)
  - 04-03 (ResumeService orchestration)
  - 03 (render_resume_tex receives selected_content payload)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LLM ranking pattern: ask LLM to score and rank all candidates; pick top N by score; keyword filter applied separately"
    - "Sparse jd_payload in Phase 4: intentionally minimal — Phase 5 enriches from full JD text"
    - "Fallback-to-master pattern: if LLM ranking fails to match IDs, fall back to first N entries from master resume"
    - "Category-preserving skill filter: skills dict preserves category structure for skills section rendering"

key-files:
  created:
    - src/resume/__init__.py
    - src/resume/selection.py
  modified:
    - src/llm/prompts/select_resume.md

key-decisions:
  - "jd_payload is intentionally sparse in Phase 4 (only job_title, company, skills from keyword pass) — Phase 5 enriches responsibilities and qualifications via LLM JD parsing"
  - "LLM ranks experiences and projects; selection.py picks top 3 and top 2 — skills filtered via keyword matching only (LLM not trusted for skill selection)"
  - "Experience id in LLM response uses title|company concatenation to enable matching back to master_resume entries"
  - "Fallback to first-N-from-master if LLM ranking returns IDs that don't match any entry — ensures caller never gets empty sections"
  - "select_resume.md updated to use jd_fields variable (not job_description) — LLM receives structured fields, not raw JD text"
  - "Skills keyword filter preserves category structure (programming, frameworks, etc.) — renderer needs category grouping for TECHNICAL SKILLS section"

patterns-established:
  - "Async selection function: select_resume_content is async, follows LLM call pattern from Phase 2"
  - "Prompt receives structured JSON fields, not raw text — reduces hallucination surface area"

requirements-completed:
  - RES-01

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 4 Plan 01: Resume Content Selection Module Summary

**LLM-driven content selector that ranks master resume entries against structured JD fields, picks top 3 experiences + top 2 projects, and assembles a resume_json_template.json-compatible payload with keyword-filtered skills**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T14:53:53Z
- **Completed:** 2026-02-23T14:55:53Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Updated `select_resume.md` prompt to accept structured `jd_fields` (job_title, company, skills, responsibilities, qualifications) instead of raw `job_description` text, with explicit master-only constraint
- Created `src/resume/selection.py` with async `select_resume_content` function that LLM-ranks all experiences and projects, selects top 3 and top 2, filters skills via keyword matching, and assembles full `resume_json_template.json`-compatible payload
- Created `src/resume/__init__.py` exporting `select_resume_content` with proper `__all__`
- Function writes `selected_resume.json` to `job_dir` on each call and returns the assembled payload for immediate use by renderer

## Task Commits

Each task was committed atomically:

1. **Task 1: Update select_resume.md prompt and create selection.py module** - `ac11f65` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `src/resume/__init__.py` - Package marker, exports select_resume_content
- `src/resume/selection.py` - LLM-driven ranking + skills keyword filter + payload assembly (250+ lines)
- `src/llm/prompts/select_resume.md` - Updated prompt: jd_fields input, ONLY-from-master constraint, ranked_experiences/ranked_projects output

## Decisions Made

- **Sparse jd_payload in Phase 4:** The jd_payload sent to the LLM contains only basic fields (job_title, company, skills via keyword pass from jd_text). Phase 5 will enrich responsibilities and qualifications from full JD text via dedicated LLM parsing — Phase 4 must work before Phase 5 exists.
- **Experience id format:** LLM response uses `title|company` concatenation as the experience id. Matching logic checks both title and company substrings in the id string (case-insensitive), with fallback to title-only match.
- **Fallback to master order:** If LLM ranking produces no matchable IDs, function falls back to first N entries from master resume to ensure non-empty sections — caller always gets valid output.
- **Skill filter preserves category structure:** The filtered skills dict maintains `{programming: [...], frameworks: [...], ...}` structure rather than flattening, so the renderer can produce grouped skill lines.
- **Skills not ranked by LLM:** Plan specified keyword matching for skills (not LLM selection) to avoid hallucination — LLM only ranks experiences and projects.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Content selection module complete and importable at `src.resume.select_resume_content`
- `selected_resume.json` written to job_dir matches `resume_json_template.json` schema structure
- Ready for Plan 02: validation layer to verify selected_content matches schema before rendering
- Ready for Plan 03: ResumeService orchestration calling select_resume_content as first pipeline stage

---
*Phase: 04-resume-generation-pipeline*
*Completed: 2026-02-23*

## Self-Check: PASSED

- src/resume/__init__.py: FOUND
- src/resume/selection.py: FOUND
- src/llm/prompts/select_resume.md: FOUND
- 04-01-SUMMARY.md: FOUND
- Commit ac11f65: FOUND
