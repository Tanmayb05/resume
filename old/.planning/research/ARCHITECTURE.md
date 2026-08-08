# Architecture Patterns

**Domain:** Personal job hunt assistant — Python web app with LLM integration and LaTeX PDF generation
**Researched:** 2026-02-21
**Confidence:** HIGH (based on direct analysis of existing codebase + established Python web patterns)

---

## Recommended Architecture

### Overview

A layered service architecture with clear separation between the web layer, business logic pipeline, and infrastructure layer (LLM, LaTeX compiler, filesystem).

```
┌─────────────────────────────────────────────────────────────┐
│                        WEB LAYER                            │
│   FastAPI app  ←→  Jinja2 templates / HTMX / static assets  │
│   Routes: /jobs, /jobs/{id}, /generate, /download           │
└──────────────────────────┬──────────────────────────────────┘
                           │ calls
┌──────────────────────────▼──────────────────────────────────┐
│                   SERVICE LAYER                              │
│  JobService  |  ResumeService  |  CoverLetterService        │
└────────┬─────────────────┬──────────────────────┬───────────┘
         │                 │                      │
┌────────▼──────┐ ┌────────▼───────┐ ┌────────────▼──────────┐
│  LLM CLIENT   │ │  LaTeX Engine  │ │   Storage Layer       │
│  (llm.py)     │ │ (tectonic CLI) │ │   data/<company>/     │
│  Anthropic    │ │ PDF Analyzer   │ │   JSON + .tex + .pdf  │
└───────────────┘ └────────────────┘ └───────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Key Files |
|-----------|---------------|-----------|
| **Web Layer** | HTTP routing, form handling, file downloads, UI rendering | `app.py`, `routes/`, `templates/` |
| **JobService** | Create job record from JD text or URL, persist to disk, track status | `services/job_service.py` |
| **ResumeService** | Orchestrate: select → tweak → render → compile → enforce one page | `services/resume_service.py` |
| **CoverLetterService** | Generate cover letter from JD + resume context, persist .txt | `services/cover_letter_service.py` |
| **LLM Client** | Stateless wrapper around Claude API; takes prompt, returns string | `llm/client.py` |
| **Prompt Registry** | Named prompt templates (not inline strings in business logic) | `llm/prompts/` |
| **LaTeX Engine** | Render .tex from structured data via Jinja2; compile via tectonic subprocess | `latex/renderer.py`, `latex/compiler.py` |
| **PDF Analyzer** | Open compiled PDF with PyMuPDF (fitz), measure page count | `latex/pdf_analyzer.py` |
| **Storage** | Read/write JSON job records, .tex, .pdf | `storage/job_store.py` |

**Boundary rules:**
- Web layer never directly calls LLM Client or LaTeX Engine — only Service Layer
- Service Layer never does raw HTTP or subprocess calls — only through dedicated wrappers
- Storage layer is the only thing that touches the filesystem for job data
- Templates are read-only at runtime

---

## Data Flow

### Flow 1: JD Input → Job Record

```
User pastes JD text (or submits URL)
  → [Web Layer] POST /jobs/new
  → [JobService] scrape URL if needed → raw text
  → [LLM Client] prompt: extract company, role, sponsorship flag, skills
  → parse JSON → validate against job_description_schema.json
  → check sponsorship keywords → set visa_flag: true/false (shown prominently)
  → [Storage] write data/<company_slug>/<date>_<company>_<role>.json
  → redirect to /jobs/<job_id>
```

**Job record schema:**
```json
{
  "id": "uuid",
  "job_title": "",
  "company": "",
  "company_slug": "",
  "location": "",
  "summary": "",
  "responsibilities": [],
  "qualifications": { "required": [], "preferred": [] },
  "skills": [],
  "visa_sponsorship_flag": true,
  "visa_keywords_found": ["sponsorship", "H1B"],
  "status": "saved | applied | interview | offer | rejected",
  "created_at": "ISO8601",
  "resume_path": null,
  "cover_letter_path": null
}
```

### Flow 2: Resume Generation Pipeline

```
User clicks "Generate Resume" for job_id
  → [ResumeService] load job JSON + master_resume.json

  ── LLM CHAIN ──
  Step A: select_content(jd_json + master_resume) → selected_resume_json
  Step B: tweak_content(jd_json + selected_resume_json) → tweaked_resume_json
          (reword/reframe for JD; no fabrication)

  ── RENDER ──
  Step C: Jinja2 render tweaked_resume_json → tailored .tex string

  ── ONE-PAGE ENFORCEMENT LOOP (max N iterations) ──
  for iteration in range(max_iterations):
    Step D: compile .tex → .pdf via tectonic subprocess
    Step E: PDF Analyzer checks page_count

    if page_count == 1:
      break  # SUCCESS
    elif page_count > 1:
      prompt trim_content(tweaked_json + overflow_context) → trimmed_json
      re-render; continue loop

  ── PERSIST ──
  save final .tex, final .pdf to data/<company_slug>/
  update job record with resume_path
```

**Critical:** The LLM only touches content (strings); LaTeX structure stays in Jinja2 template. Never ask LLM to emit raw LaTeX.

### Flow 3: Cover Letter Generation

```
User clicks "Generate Cover Letter" for job_id
  → [CoverLetterService] load job JSON + resume JSON
  → load cover_letter_prompt.md from templates/
  → prompt(template + jd_json + resume_json) → 300-400 word plain text
  → save as data/<company_slug>/<company>_cover_letter.txt
  → update job record
```

### Flow 4: Job Pipeline View

```
GET /jobs → list all job JSONs → group by status → render pipeline table
GET /jobs/<job_id> → load job JSON → show artifacts + download links
GET /jobs/<job_id>/download/resume → FileResponse (PDF attachment)
```

---

## One-Page Enforcement Loop (Detailed)

```
COMPILE → ANALYZE → DECISION
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   page_count>1   whitespace    acceptable
   (overflow)     too high           │
        │          (sparse)         DONE
        ▼             ▼
   AI TRIM        AI EXPAND
        │             │
        └─────────────┘
               │
          re-render .tex
               │
          back to COMPILE
```

**Implementation notes:**
1. `fitz.open(pdf).page_count > 1` is the reliable binary overflow signal
2. LLM trim/expand prompt must receive which sections to modify, not just "make it shorter"
3. Save each iteration as `_iter_N.tex` for debugging; only final version gets canonical filename
4. After exhausting max iterations, surface a warning in the UI — never silently deliver a multi-page resume

---

## Suggested Build Order

```
Phase 1: Storage + Config foundation
  - JobRecord schema (Pydantic model)
  - job_store.py (read/write/list JSON files)
  - pydantic-settings config (replaces config.yaml)
  - No LLM, no LaTeX

Phase 2: LLM Client + Prompt Registry
  - client.py wrapping Claude API (httpx.AsyncClient)
  - llm/prompts/ directory with named .md templates:
      jd_parser, resume_selector, resume_tweaker,
      resume_trimmer, cover_letter

Phase 3: LaTeX Engine + PDF Analyzer
  - renderer.py (Jinja2 with custom delimiters → .tex)
  - compiler.py (tectonic subprocess wrapper)
  - pdf_analyzer.py (PyMuPDF page count)
  - Migrate resume_template.tex → resume_template.tex.j2

Phase 4: Service Layer — Resume Pipeline
  - ResumeService orchestrates Phases 2 + 3
  - Full one-page enforcement loop (overflow AND sparse branches)

Phase 5: Service Layer — JD Intake + Cover Letter
  - JobService (JD parse → job record persist)
  - CoverLetterService (generate + persist as .txt)
  - URL scraping (httpx + BeautifulSoup, best-effort)

Phase 6: Web Layer
  - FastAPI app with Jinja2 + HTMX
  - Routes: /jobs, /jobs/{id}, /generate, /download
  - BackgroundTasks for generation; status polling

Phase 7: UI Polish + Pipeline View
  - Kanban/table grouped by status
  - Visa flag badge displayed prominently
  - Generation status indicators
```

---

## Key Patterns

### Pattern 1: Prompt-as-File
Store each LLM prompt as a named `.md` file in `llm/prompts/`. Never inline prompt strings in business logic.

### Pattern 2: Jinja2 for LaTeX (not LLM)
LLM produces structured JSON (content only). Jinja2 renders fixed structure. Python handles LaTeX character escaping. Use custom delimiters (`<<`, `>>`) to avoid conflict with LaTeX braces.

### Pattern 3: Thin Routes, Fat Services
FastAPI routes parse request + call one service method + return response. All business logic lives in service classes.

### Pattern 4: BackgroundTasks for Long Operations
Generation takes 30-120s. Use `FastAPI BackgroundTasks`. UI polls `GET /jobs/{id}/status` until `resume_status == "ready"`.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Instead |
|---|---|---|
| LLM-generated LaTeX structure | High error rate — mismatched environments, escaped chars | LLM → JSON; Jinja2 → .tex |
| Monolithic main.py orchestration | Untestable, no retry, no reuse | Dedicated service classes |
| Blocking HTTP handlers for LLM calls | Blocks event loop for 30-120s | httpx.AsyncClient + asyncio.run_in_executor for subprocess |
| Hardcoded relative paths | Breaks when CWD ≠ project root | `pathlib.Path(__file__).parent / ...` |

---

## File Storage Pattern

```
data/
  <company_slug>/
    <YYYYMMDD>_<company>_<role>.json   # job record (source of truth)
    <company>_resume_iter_1.tex        # intermediate (debug)
    <company>_resume.tex               # final canonical
    <company>_resume.pdf               # final canonical
    <company>_cover_letter.txt         # plain text

templates/                             # READ-ONLY at runtime
  master_resume.json
  resume_template.tex.j2               # migrated Jinja2 template
  job_description_schema.json
  cover_letter_prompt.md
```

---

## LLM Prompt Chain

```
[1] parse_jd(raw_text) → jd_json
[2] select_content(jd_json, master_resume) → selected_json
[3] tweak_content(jd_json, selected_json) → tweaked_json
        → Jinja2 render → .tex → tectonic → PyMuPDF
              ├── overflow → [4a] trim_content → re-render
              └── pass     → DONE

[parallel] cover_letter(jd_json, tweaked_json) → .txt
```

---

## Key Findings

- Existing prototype is a working CLI but monolithic — needs decomposition for web app
- Biggest risk: LLM-generated LaTeX structure (fragile). Fix: LLM → JSON; Jinja2 → .tex
- One-page loop currently only handles sparse case. Must also handle overflow (page_count > 1)
- Long operations need BackgroundTasks — never block the HTTP handler
- Filesystem JSON is correct and sufficient for single-user scale
