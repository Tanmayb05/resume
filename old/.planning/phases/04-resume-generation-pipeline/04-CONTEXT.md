# Phase 4: Resume Generation Pipeline - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

`ResumeService` takes a job record and produces a one-page PDF resume via the full loop: select relevant content from `master_resume.json` → LLM-rank and assemble → render via Jinja2 → compile via tectonic → measure via PyMuPDF → trim if needed → repeat until one page or max_iterations hit.

JD intake (parsing the job description), cover letter generation, and the web layer are separate phases. This phase wires together the Phase 2 LLM client and Phase 3 LaTeX engine into a working end-to-end pipeline.

</domain>

<decisions>
## Implementation Decisions

### Selection logic
- LLM ranks experiences and projects for relevance to the job; the service takes the top 3 experiences and top 2 projects from the ranked list
- LLM receives extracted JD fields only (skills, responsibilities, requirements from the parsed job record) — not the full JD text — to reduce noise
- Selection is pick-only: no bullet rewriting or tailoring at this stage; content passes through unchanged
- Skills selection strategy: Claude's Discretion (see below)

### Trim behavior
- When page count > 1, the trim prompt targets the longest bullets first (by character count)
- Trim is progressive: small cuts per iteration (~10-20% reduction per pass) to preserve content quality
- **Line-overflow heuristic** (based on the actual template baseline — 9pt Charter, ~100-char one-line threshold):
  - Bullets that overflow onto a 2nd line with less than ~50% of that line filled → rewrite to fit cleanly on one line
  - Bullets that use 2.5+ lines but leave the partial last line sparse → rewrite to clean 2 lines
  - The LLM trim prompt receives the explicit ~100-char threshold so it can evaluate each bullet before deciding
  - Rewrites must follow ATS-standard phrasing (action verb + metric/result)
- If max_iterations is reached without achieving one page: return the last iteration's PDF with a `page_fit_warning` flag in the result object
- If the final PDF whitespace_ratio is above a threshold (too much empty space — over-trimmed): include a `whitespace_warning` flag in the result object

### Content validation
- Validation runs once: on the final output before returning to the caller
- Validator is purely Python entity matching (fast, deterministic): extract skills/tools/companies/metrics from the output and diff against `master_resume.json`; Claude's Discretion on exact matching implementation and failure handling (see below)

### Output artifacts
- Files saved to `data/<company_slug>/`:
  - `selected_resume.json` — the assembled content after LLM selection (pre-render), for debugging and future re-use
  - `resume_iter_N.tex` / `resume_iter_N.pdf` — only the **final** successful iteration is kept, plus the **last failed iteration** if the loop terminated without fitting
  - Intermediate iterations are cleaned up after the run
- On success, service returns a structured result object containing: PDF path, .tex path, iteration count, and any warning flags (`page_fit_warning`, `whitespace_warning`, `validation_warning`)

### Claude's Discretion
- Skills selection: Claude picks the most practical approach (e.g., keyword filter against JD fields, or a quick LLM pass — whatever is most reliable given Phase 2 tooling)
- Whitespace ratio threshold: Claude calibrates the "over-trimmed" threshold by referencing `templates/resume_template.pdf` as the baseline (the reference template is a well-filled one-page resume)
- Entity validation implementation details: how entities are extracted (spaCy NER vs regex vs structured field diff), exact matching tolerance, and whether a validation violation causes a hard error, a single retry, or a warn-and-return
- Hallucination handling policy: Claude picks whatever is safest for a job-hunt tool (hard fail or warn-and-return)

</decisions>

<specifics>
## Specific Ideas

- Template baseline: `templates/resume_template.tex` and `templates/resume_template.pdf` are the reference for line-length calibration. The template uses 9pt Charter, 0.7cm side margins, letterpaper — approximately 100 characters per bullet line. The trim heuristic is grounded in this actual template, not a generic estimate.
- Trim prompt should pass the explicit `~100 char` line threshold to the LLM so it can evaluate overflow before rewriting
- ATS phrasing standard for rewritten bullets: start with strong action verb, include quantified metric or result where present in original

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-resume-generation-pipeline*
*Context gathered: 2026-02-23*
