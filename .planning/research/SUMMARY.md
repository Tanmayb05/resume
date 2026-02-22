# Project Research Summary

**Project:** Job Hunt Assistant Web App
**Domain:** AI-powered resume tailoring, cover letter generation, and job application tracking
**Researched:** 2026-02-21
**Confidence:** HIGH (stack, architecture, pitfalls from direct codebase analysis) / MEDIUM (competitive landscape)

## Executive Summary

This is a personal-use, single-user Python web application that wraps a working CLI prototype with a browser UI. The existing codebase (`src/main.py`, `src/llm.py`, `src/pdf_analyzer.py`) contains a functional but monolithic pipeline: parse JD → select from master resume → tweak content → render LaTeX → compile to PDF via tectonic. The recommended approach is to decompose this monolith into a layered service architecture (FastAPI + HTMX + Jinja2) with clearly separated components: web routing, service orchestration, LLM client, LaTeX engine, and filesystem storage. No database, no auth, no build toolchain — this is a personal tool and complexity is the enemy.

The most critical architectural decision is confirmed by multiple research threads: the LLM must never emit raw LaTeX. Instead, LLM calls produce structured JSON (content only); Jinja2 templates handle LaTeX structure. This eliminates the largest class of bugs documented in the current code. The second most important decision is replacing the current whitespace-percentage overflow detection with direct PDF page count (`fitz.open(pdf).page_count > 1`), and implementing a bidirectional enforcement loop that both trims overflow AND expands sparse output — the current loop only expands, making an overflowing resume progressively worse.

The key risks are well-understood and preventable: LLM content fabrication (addressed by strict allowlist enforcement in every prompt), LaTeX injection via LLM output (addressed by command scanning before compilation), path traversal via LLM-extracted company names (sanitize immediately), and cover letter generation hanging due to the `docx2pdf`/LibreOffice dependency (eliminate it — serve plain `.txt`). Four features are missing that the stated requirements demand: F1 visa/sponsorship flag, bidirectional one-page enforcement, job tracker status system, and the web UI itself. All are well-scoped and buildable.

---

## Key Findings

### Recommended Stack

The stack is nearly fully determined by the existing codebase and the constraints of a single-user personal tool. FastAPI + Uvicorn provides async handling needed for 5-30s LLM calls and 5-10s tectonic compilation without blocking. HTMX replaces a React/Vue frontend with zero build toolchain overhead — HTML partials from FastAPI endpoints plus Server-Sent Events for streaming progress. tectonic is already validated and self-contained. Anthropic Claude API (via `anthropic` SDK) replaces Ollama as the primary LLM: documented bugs with llama3.1:8b (inconsistent JSON formatting, markdown fence variations, empty responses) are eliminated by Claude's deterministic structured output.

**Core technologies:**
- **FastAPI ^0.115:** HTTP API backend — async support for LLM + LaTeX pipeline operations
- **HTMX ^2.0:** Frontend interactivity — zero build toolchain, SSE for progress streaming
- **Jinja2 ^3.1:** Server-side HTML templating AND LaTeX template rendering
- **Anthropic Claude SDK ^0.40:** LLM API — reliable structured JSON output, no Ollama format bugs
- **tectonic (CLI):** LaTeX → PDF — already validated, self-contained
- **PyMuPDF (fitz) ^1.25:** PDF page count detection — binary overflow signal
- **pydantic-settings ^2.6:** Config via .env — startup validation with clear errors
- **httpx ^0.28:** Async HTTP for URL scraping and LLM API calls
- **beautifulsoup4 + lxml:** HTML parsing for URL-scraped job descriptions

**Do not use:** React/Vue/Svelte (build toolchain), SQLAlchemy (no relational DB needed), Celery/Redis (FastAPI BackgroundTasks sufficient), python-docx + LibreOffice for cover letters (fragile, hangs), Ollama in production (documented JSON/LaTeX output bugs).

### Expected Features

The existing codebase covers the core pipeline (JD parsing, content selection, LaTeX rendering, PDF compilation) but is missing four features that are critical to the stated product requirements.

**Must have (table stakes):**
- JD paste input → structured JSON parsing (port CLI to web API)
- F1 visa / sponsorship signal — parse sponsorship keywords, display prominently BEFORE generation (not implemented; low effort, critical value)
- Master resume selector + content tweaker (refactor monolith into discrete pipeline stages)
- One-page enforcement in BOTH directions — current loop only expands; must also trim when page_count > 1 (most critical functional gap)
- Cover letter generation — cleanup fragile `docx2pdf` dependency; serve plain `.txt`
- Artifact download via web UI (PDF resume, cover letter text)
- Job tracker status field per application (not implemented)
- Application list view — index of all `data/*/` with status badges (not implemented)

**Should have (competitive differentiators):**
- Application detail view — artifacts, status, iteration count per application
- Submission checklist — post-generation reminder (no em-dashes, correct dates, signature)
- Per-iteration artifact history (`_iter_N` files) for debugging regression
- Graduation date context switching (May 2026 full-time vs Dec 2026 internships)

**Defer to v2+:**
- URL-based JD scraping (paste is reliable; URL adds error surface)
- Multi-LLM support UI (abstract in code, but expose only if Ollama proves useful)
- Application notes / journal
- ATS match percentage score (gameable — show keyword list instead)
- Chrome extension, mobile app, resume template marketplace

### Architecture Approach

The recommended architecture is a layered service pattern with strict component boundaries. The web layer (FastAPI routes + Jinja2 + HTMX) only calls service classes; services orchestrate LLM calls, LaTeX rendering/compilation, and storage; no layer bypasses its abstraction. Long-running operations (generation takes 30-120s) use FastAPI `BackgroundTasks` with the UI polling `GET /jobs/{id}/status` until complete. Filesystem JSON is the correct storage backend at single-user scale — no database needed for MVP.

**Major components:**
1. **Web Layer** (`app.py`, `routes/`, `templates/`) — HTTP routing, form handling, file downloads, UI rendering
2. **JobService** (`services/job_service.py`) — Create job record from JD text/URL, persist to disk, track status
3. **ResumeService** (`services/resume_service.py`) — Orchestrate: select → tweak → render → compile → one-page enforce loop
4. **CoverLetterService** (`services/cover_letter_service.py`) — Generate cover letter from JD + resume context, persist as `.txt`
5. **LLM Client** (`llm/client.py`) — Stateless async wrapper around Claude API
6. **Prompt Registry** (`llm/prompts/`) — Named `.md` prompt templates; never inline prompts in business logic
7. **LaTeX Engine** (`latex/renderer.py`, `latex/compiler.py`) — Jinja2 render to `.tex`; tectonic subprocess compile
8. **PDF Analyzer** (`latex/pdf_analyzer.py`) — PyMuPDF page count check (primary signal); whitespace (secondary)
9. **Storage** (`storage/job_store.py`) — Read/write JSON job records, `.tex`, `.pdf`

**Key patterns:**
- LLM → JSON only; Jinja2 → LaTeX structure (never ask LLM to emit raw LaTeX)
- Thin routes, fat services — all business logic in service classes
- Prompt-as-file — each LLM prompt is a named `.md` file in `llm/prompts/`
- BackgroundTasks for all generation operations; UI polls for status

### Critical Pitfalls

1. **LLM Markdown Fence Variations Corrupt LaTeX** — Current code uses hardcoded string slicing to strip ` ```latex ` fences. LLMs vary this format; any variation produces malformed `.tex`. Fix: regex-based fence removal from day one (`re.sub(r'^```\w*\n?', '', text)`); validate stripped output begins with `\documentclass` before saving. Enforce by eliminating LaTeX from LLM output entirely — LLM → JSON; Jinja2 → `.tex`.

2. **One-Page Loop Infinite Retry on Compile Failure** — When tectonic fails, PDF Analyzer returns `100.0%` whitespace (missing file). Loop misreads this as "too much whitespace — retry." Exhausts all iterations with multiple LLM calls, produces nothing. Fix: use sentinel value (`-1.0`) for error state; hard exit after 2+ consecutive compilation failures.

3. **PDF Page Count Detection Misses Overflow** — Whitespace-percentage averaging across pages masks a 2-page PDF. Current code can declare "optimization complete" while delivering a 2-page resume. Fix: `len(fitz.open(pdf)) > 1` is the primary overflow signal. Whitespace is secondary for under-fill only. Implement bidirectional loop: TRIM mode (page_count > 1) and EXPAND mode (whitespace > threshold AND page_count == 1).

4. **LLM Fabricates Resume Content** — Without strongly-worded constraints in every prompt, the model invents skills, tools, and metrics not in `master_resume.json`. Fix: include explicit allowlist constraint in every content prompt; run post-generation entity validation comparing generated content against source data.

5. **LaTeX Template Injection via LLM Output** — LLM-generated content written to `.tex` and compiled without sanitization could include `\write18{}` or `\input{/etc/passwd}`. Fix: scan generated `.tex` for dangerous commands before compilation; never run tectonic with `-shell-escape`.

---

## Implications for Roadmap

Based on combined research, the build order follows strict dependency chains. Infrastructure must precede LLM integration; LLM integration must precede the LaTeX engine; the LaTeX engine must precede the enforcement loop; services must precede the web layer. The architecture research already specifies this order explicitly — follow it.

### Phase 1: Storage and Configuration Foundation

**Rationale:** Every subsequent phase depends on job records and config. Establishing Pydantic models and `pydantic-settings` config eliminates entire categories of downstream bugs (KeyError on missing config, path resolution failures, JSON corruption). Zero LLM or LaTeX work in this phase — pure setup.
**Delivers:** `JobRecord` Pydantic model, `job_store.py` (read/write/list JSON), `pydantic-settings` config replacing `config.yaml`, absolute path resolution throughout
**Addresses:** Table stakes — company-scoped artifact storage; job tracker status field schema
**Avoids:** Pitfalls 12 (relative path failures), 14 (JSON corruption without schema validation)

### Phase 2: LLM Client and Prompt Registry

**Rationale:** The LLM client is a shared dependency for JD parsing, content selection, tweaking, trimming, and cover letter generation. Building it once with proper timeout, retry, and JSON extraction isolates all LLM reliability work in one place. Prompt-as-file pattern must be established before any prompts are written.
**Delivers:** `llm/client.py` wrapping Claude API (httpx.AsyncClient, async, timeout=(10, 120)); `llm/prompts/` directory with named `.md` prompt templates for all pipeline stages; JSON extraction utility with fence-stripping
**Addresses:** LLM integration for all downstream pipeline stages
**Avoids:** Pitfalls 1 (markdown fence variations), 13 (no timeout on LLM calls), 9 (token limit truncation via separate select/tweak calls)

### Phase 3: LaTeX Engine and PDF Analyzer

**Rationale:** LaTeX rendering and PDF analysis are independent of the LLM client — they consume JSON and produce PDFs. Validating these components in isolation (with fixture JSON) confirms the template, ATS parsability, and page count detection before the enforcement loop is built.
**Delivers:** `latex/renderer.py` (Jinja2 with custom `<< >>` delimiters → `.tex`); `latex/compiler.py` (tectonic subprocess with timeout); `latex/pdf_analyzer.py` (PyMuPDF page count as primary signal); migrated `resume_template.tex.j2`; ATS parsability validation via `pdftotext`
**Addresses:** LaTeX-based resume output (table stakes); one-page PDF output foundation
**Avoids:** Pitfalls 5 (LaTeX injection — command allowlist scan before compile), 8 (ATS parsability — validate before any resume generated), 4 (page count vs whitespace — fix measurement first)

### Phase 4: Resume Generation Pipeline with One-Page Enforcement

**Rationale:** This is the core product value. With LLM client and LaTeX engine confirmed working, `ResumeService` orchestrates the full chain: select → tweak → render → compile → enforce. The bidirectional enforcement loop (TRIM and EXPAND modes) is built here, with the correct state machine designed before coding.
**Delivers:** `ResumeService` orchestrating 4-step LLM chain; bidirectional one-page enforcement loop (TRIM: page_count > 1; EXPAND: whitespace > threshold AND page_count == 1); iteration tracking (`_iter_N` artifacts); post-generation entity validation against `master_resume.json`
**Addresses:** One-page PDF output (table stakes); resume keyword alignment; AI reframing without fabrication
**Avoids:** Pitfalls 2 (infinite retry on compile failure), 3 (LLM content fabrication), 6 (expand-only loop making overflow worse)

### Phase 5: JD Intake, F1 Flag, and Cover Letter Service

**Rationale:** JD parsing and cover letter generation are independent of the resume pipeline but share the LLM client. F1 visa flag is a critical missing feature with low implementation effort — it belongs here at ingestion, displayed before generation starts. Cover letter serves `.txt` to eliminate the `docx2pdf`/LibreOffice dependency entirely.
**Delivers:** `JobService` (JD text → structured JSON → `JobRecord` persisted to disk); F1 visa/sponsorship keyword detection with prominent display before generation; `CoverLetterService` (LLM → 300-400 word plain text → `.txt`); company name sanitization; optional URL scraping (httpx + BeautifulSoup, best-effort)
**Addresses:** F1 visa signal (critical gap), JD ingestion, cover letter generation, job tracker status schema
**Avoids:** Pitfalls 7 (company name path traversal), 10 (cover letter word count drift), 11 (LibreOffice hangs)

### Phase 6: FastAPI Web Layer

**Rationale:** With all services built and tested, the web layer is a thin routing layer. FastAPI routes call service methods; `BackgroundTasks` handles generation; HTMX polls for status. This phase is deliberately last — a web layer on top of untested services is the path to untestable monoliths.
**Delivers:** FastAPI app with Jinja2 + HTMX; routes: `/jobs`, `/jobs/{id}`, `/jobs/new`, `/generate`, `/download`; `BackgroundTasks` for long operations; status polling endpoint; PDF and `.txt` download endpoints; F1 flag warning display
**Addresses:** Web UI (critical gap), artifact download, application list view
**Uses:** FastAPI BackgroundTasks (not Celery), HTMX SSE for progress, Tailwind CDN (zero build step)

### Phase 7: Job Tracker and Application Pipeline View

**Rationale:** Once the generation pipeline is working end-to-end in the web UI, the tracker UI provides the "manage 10-50 concurrent applications" surface that makes the tool a daily driver rather than a one-shot script.
**Delivers:** Application list view grouped by status; application detail view with artifact links and iteration count; status update UI (generated → applied → interviewing → offer → rejected); submission checklist displayed post-generation
**Addresses:** Status tracking per application (table stakes), view list of past applications (table stakes), submission checklist (should have)

### Phase Ordering Rationale

- Phases 1-3 establish infrastructure that all business logic depends on; building services on unvalidated infrastructure creates debugging nightmares
- The LaTeX pipeline (Phase 3) is validated with fixture data before the enforcement loop (Phase 4) adds complexity
- F1 flag is grouped with JD intake (Phase 5) because it is an ingestion-time decision, not generation-time
- Web layer (Phase 6) is last because services tested in isolation are easier to reason about than services only exercised through HTTP
- Job tracker UI (Phase 7) is the last phase because it is the lowest-dependency feature — all it needs is the filesystem records that every preceding phase produces

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (One-page enforcement loop):** The state machine for TRIM vs EXPAND vs compile failure vs max iterations is non-trivial. Design the loop diagram before writing code.
- **Phase 6 (BackgroundTasks + HTMX polling):** FastAPI BackgroundTasks has documented limitations (tasks run in the same process, killed on server restart). Confirm acceptable for single-user personal tool; flag if deployment changes.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Storage + Config):** Pydantic models + pydantic-settings are thoroughly documented; no research needed
- **Phase 2 (LLM Client):** Anthropic SDK async patterns are well-documented
- **Phase 3 (LaTeX Engine):** tectonic already validated; Jinja2 custom delimiters are documented
- **Phase 5 (JD Intake + Cover Letter):** Standard LLM prompt + JSON extraction patterns
- **Phase 7 (Job Tracker UI):** HTMX table/kanban patterns are standard; no novel territory

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Most technologies already validated in existing codebase (tectonic, PyMuPDF, Anthropic SDK); HTMX + FastAPI is established 2024-2026 pattern |
| Features | HIGH | Based on direct codebase inspection of what exists vs. what is missing; feature gaps are confirmed not inferred |
| Architecture | HIGH | Layered service pattern is well-established for this class of tool; build order derived from explicit dependency analysis |
| Pitfalls | HIGH | All critical pitfalls are confirmed bugs in existing code (not hypothetical); CONCERNS.md and direct code review |

**Overall confidence:** HIGH

### Gaps to Address

- **Whitespace threshold calibration:** The 40% threshold for the EXPAND trigger is not validated for the current 9pt font / 0.5cm margin template. Calibrate empirically with 5 sample resumes during Phase 4 before shipping.
- **tectonic first-run latency:** tectonic downloads LaTeX packages on first use. First compile can take 60-120s. The web UI must communicate this clearly (one-time setup message, not a hung spinner).
- **Cover letter word count validation:** Programmatic word count check + regenerate if outside 300-400 word range needs testing across different JD lengths to confirm the prompt instruction is sufficient or if regeneration is consistently needed.
- **Version pinning:** Research recommends minimum-version pins for all dependencies. Exact pinning strategy should be confirmed at implementation start to avoid dependency conflicts with existing `requirements.txt`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `src/main.py`, `src/llm.py`, `src/pdf_analyzer.py`, `src/cover_letter.py` — confirmed existing behavior and documented bugs
- `.planning/codebase/CONCERNS.md` — pre-existing concern list from codebase mapping
- Anthropic Python SDK documentation — Claude API async patterns, structured output
- FastAPI official documentation — BackgroundTasks, Jinja2 integration, async route handling
- HTMX 2.0 documentation — SSE patterns, partial HTML swaps
- PyMuPDF (fitz) documentation — page count API, `len(doc)` pattern

### Secondary (MEDIUM confidence)
- Competitive landscape analysis (Resume Worded, Teal, Rezi, Kickresume) — feature expectations for this category
- tectonic project documentation — compilation behavior, first-run package download
- Python pydantic-settings documentation — .env config validation pattern

### Tertiary (LOW confidence)
- ATS parsability behavior with `paracol` two-column layout — anecdotal reports; validate with `pdftotext` during Phase 3
- LLM fabrication rate without explicit allowlist constraints — observed in Ollama experiments; Claude behavior may differ but constraint is still required

---

*Research completed: 2026-02-21*
*Ready for roadmap: yes*
