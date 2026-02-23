# Roadmap: Job Hunt Assistant

## Overview

Seven phases build the application in strict dependency order: infrastructure first, then LLM integration, then the LaTeX engine, then the resume pipeline that combines all three, then JD intake and cover letter generation (which share the LLM client), then the web layer that wraps everything in a browser UI, and finally the job tracker that surfaces the application pipeline. Each phase produces independently verifiable output; no phase depends on untested work from a parallel track.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Storage and Configuration** - Pydantic job record model, JSON filesystem store, pydantic-settings config (completed 2026-02-22)
- [x] **Phase 2: LLM Client and Prompt Registry** - Async Ollama LLM client, prompt-as-file pattern, JSON extraction utility (completed 2026-02-22)
- [ ] **Phase 3: LaTeX Engine and PDF Analyzer** - Jinja2 LaTeX renderer, tectonic compiler, PyMuPDF page count detection
- [ ] **Phase 4: Resume Generation Pipeline** - Full select → tweak → render → compile → TRIM loop with one-page enforcement
- [ ] **Phase 5: JD Intake, F1 Flag, and Cover Letter** - JobService, F1 keyword detection, CoverLetterService producing plain .txt
- [ ] **Phase 6: FastAPI Web Layer** - HTTP routes, BackgroundTasks, HTMX, PDF and cover letter download endpoints
- [ ] **Phase 7: Job Tracker UI** - Application list view with status badges

## Phase Details

### Phase 1: Storage and Configuration
**Goal**: The data layer and config system exist so every subsequent phase can read/write job records and resolve paths without KeyError or JSON corruption
**Depends on**: Nothing (first phase)
**Requirements**: None directly (pure infrastructure enabling all v1 requirements)
**Success Criteria** (what must be TRUE):
  1. A `JobRecord` Pydantic model can be instantiated with company, role, location, status, and file paths, and round-trips to/from JSON without data loss
  2. `job_store.py` can write a job record to `data/<company_slug>/job.json`, read it back, and list all existing records
  3. App config (API key, data directory, max iterations) loads from `.env` via pydantic-settings and raises a clear startup error if required fields are missing
  4. All file paths in the codebase resolve to absolute paths — no relative path bugs on different working directories
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — JobRecord Pydantic model + AppConfig via pydantic-settings
- [x] 01-02-PLAN.md — Path utilities (slug sanitization, collision detection) + JobStore filesystem CRUD + package wiring

### Phase 2: LLM Client and Prompt Registry
**Goal**: A single, reliable async LLM client and a file-based prompt registry exist so all pipeline stages share one integration point with consistent error handling
**Depends on**: Phase 1
**Requirements**: None directly (shared infrastructure enabling RES-01, RES-04, RES-06, COV-01, COV-02, JD-02, JD-03)
**Success Criteria** (what must be TRUE):
  1. `llm/client.py` can call Ollama asynchronously and return raw response text without hanging — requests time out after a configurable limit
  2. Markdown code fences are stripped from LLM responses before JSON parsing, regardless of fence variant (` ```json `, ` ``` `, bare backticks)
  3. Each pipeline prompt lives as a named `.md` file in `llm/prompts/`; no prompt strings are hardcoded inside business logic files
  4. The client retries on transient API errors (connection, timeout, 5xx, 429) without surfacing exceptions to callers
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — AppConfig Ollama fields + LLMClient with Tenacity retry + LLMError exception
- [ ] 02-02-PLAN.md — extract_json() TDD: fence stripping + fix-busted-json repair (RED-GREEN-REFACTOR)
- [ ] 02-03-PLAN.md — load_prompt() Jinja2 registry + four seed prompt templates (select_resume, parse_job_description, generate_cover_letter, trim_resume)

### Phase 3: LaTeX Engine and PDF Analyzer
**Goal**: The LaTeX render-compile-measure chain works correctly in isolation so the enforcement loop in Phase 4 is built on validated components
**Depends on**: Phase 2
**Requirements**: RES-02, RES-03, RES-05
**Success Criteria** (what must be TRUE):
  1. `latex/renderer.py` renders a fixture JSON payload through `resume_template.tex.j2` using Jinja2 custom delimiters and produces a valid `.tex` file (no unresolved template variables, no LaTeX syntax errors from the renderer)
  2. `latex/compiler.py` compiles the rendered `.tex` file via tectonic and produces a PDF; compilation failures return a structured error (not a raw subprocess exception)
  3. `latex/pdf_analyzer.py` returns `page_count` (integer) and `whitespace_ratio` (float) for a given PDF path; a missing or corrupt PDF returns a sentinel error value, not a crash
  4. Final `.tex` and `.pdf` artifacts are saved to `data/<company_slug>/` with `_iter_N` naming as specified in RES-05
  5. The generated PDF passes `pdftotext` extraction (non-empty output), confirming ATS parsability of the template
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Jinja2 LaTeX renderer (renderer.py) + resume_template.tex.j2 with custom delimiters and latex_escape (RES-02, RES-05)
- [ ] 03-02-PLAN.md — tectonic compiler (compiler.py) + PyMuPDF PDF analyzer (pdf_analyzer.py) with structured error returns (RES-03, RES-05)

### Phase 4: Resume Generation Pipeline
**Goal**: Users can trigger full resume generation from a job record and receive a one-page PDF that uses only content from master_resume.json
**Depends on**: Phase 3
**Requirements**: RES-01, RES-04, RES-06
**Success Criteria** (what must be TRUE):
  1. `ResumeService` selects relevant experiences, projects, and skills from `master_resume.json` based on a job record and returns a structured JSON payload (RES-01)
  2. The one-page enforcement loop compiles the resume, detects page overflow via `page_count > 1`, prompts the LLM to shorten the longest bullet points, and recompiles — repeating up to `max_iterations` (RES-04)
  3. The loop terminates cleanly on: (a) page count == 1, (b) reaching max_iterations, (c) two consecutive compilation failures — it never hangs indefinitely
  4. Generated resume content contains no skills, tools, companies, or metrics that are absent from `master_resume.json` — post-generation entity validation catches violations (RES-06)
  5. The final PDF is exactly one page with minimal whitespace when the loop exits successfully
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — Content selection module (selection.py + updated select_resume.md prompt) using LLM ranking + keyword skills filter
- [ ] 04-02-PLAN.md — TRIM loop (trimmer.py + updated trim_resume.md) + entity validator (validator.py) with structured field diff
- [ ] 04-03-PLAN.md — ResumeService orchestrator (service.py) wiring selection, trim loop, validation; end-to-end smoke test

### Phase 5: JD Intake, F1 Flag, and Cover Letter
**Goal**: Users can submit a job description and receive a parsed job record with a visible F1 sponsorship signal, and the system can generate a validated cover letter
**Depends on**: Phase 2
**Requirements**: JD-01, JD-02, JD-03, JD-04, COV-01, COV-02, COV-03, COV-04, COV-05
**Success Criteria** (what must be TRUE):
  1. A pasted JD text is parsed into a structured JSON record matching `job_description_schema.json` (company, role, location, skills, responsibilities, requirements, visa fields) and persisted to `data/<company_slug>/job.json` (JD-01, JD-02, JD-04)
  2. The F1 sponsorship signal is detected from JD text using keyword matching ("sponsorship", "H-1B", "OPT", "authorize to work", "citizen only", etc.) and the result is stored on the job record (JD-03)
  3. A cover letter is generated from the JD context plus selected resume content, is between 300 and 400 words (system regenerates if outside range), contains no em-dashes, and uses the correct graduation date ("May 2026" for full-time, "Dec 2026" for internships) (COV-01, COV-02, COV-04, COV-05)
  4. The cover letter is saved as a plain `.txt` file to `data/<company_slug>/` — no docx, no LibreOffice dependency (COV-03)
  5. The company slug used for directory naming is sanitized against path traversal (no `../`, no special characters) before any file is written
**Plans**: TBD

### Phase 6: FastAPI Web Layer
**Goal**: Users can operate the entire pipeline through a browser — submitting JDs, triggering generation, and downloading artifacts — without touching the command line
**Depends on**: Phase 4, Phase 5
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. A user can open the app in a browser, paste a job description into a form, and submit it to start the pipeline — the UI shows that generation is in progress without timing out (UI-01)
  2. A user can download the generated resume PDF from the web UI after generation completes (UI-02)
  3. A user can download or copy the generated cover letter text from the web UI after generation completes (UI-03)
  4. The F1 visa flag result is displayed prominently on the job detail page so the user sees it before sending any application
**Plans**: TBD

### Phase 7: Job Tracker UI
**Goal**: Users can see all their job applications in one view with status badges, making the tool useful for managing 10-50 concurrent applications
**Depends on**: Phase 6
**Requirements**: TRK-01
**Success Criteria** (what must be TRUE):
  1. A user can navigate to an applications list view and see all past job applications with company name, role, submission date, and a status badge (TRK-01)
  2. The list view loads even when 50+ application directories exist under `data/` — no performance cliff at scale
  3. Applications are sorted by date (most recent first) so the user's active applications appear at the top
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Storage and Configuration | 2/2 | Complete   | 2026-02-22 |
| 2. LLM Client and Prompt Registry | 3/3 | Complete   | 2026-02-22 |
| 3. LaTeX Engine and PDF Analyzer | 0/TBD | Not started | - |
| 4. Resume Generation Pipeline | 0/3 | Not started | - |
| 5. JD Intake, F1 Flag, and Cover Letter | 0/TBD | Not started | - |
| 6. FastAPI Web Layer | 0/TBD | Not started | - |
| 7. Job Tracker UI | 0/TBD | Not started | - |
