# Feature Landscape

**Domain:** AI-powered job hunt assistant — resume tailoring + cover letter generation + job application tracker
**Researched:** 2026-02-21
**Confidence:** HIGH (direct code inspection) + MEDIUM (competitive landscape)

---

## Table Stakes

Features users expect from any tool in this category. Missing = tool feels incomplete.

| Feature | Why Expected | Complexity | Already Exists? | Notes |
|---------|--------------|------------|-----------------|-------|
| JD ingestion (paste text) | Every tool requires a JD as input | Low | YES (CLI) | Needs upgrade: paste in UI vs. file path on CLI |
| JD structured parsing to JSON | AI must understand job before tailoring | Medium | YES (`parse_jd_to_json`) | Uses `job_description_schema.json` schema |
| Resume content selection from master | Core of "tailoring" — pick relevant experiences | Medium | YES (in monolithic LLM call) | Needs refactoring into discrete pipeline stages |
| Resume keyword alignment with JD | ATS scoring; users expect this | Medium | YES (implicit in prompt) | Not explicit extraction — implicit |
| One-page PDF output | Industry norm; hard requirement | High | PARTIAL | Expand loop exists; **trim loop is missing** |
| PDF download of generated resume | Users must submit the artifact | Low | YES (file saved) | Web UI needs download endpoint |
| Cover letter generation | Expected companion in this category | High | YES (`generate_cover_letter`) | Uses detailed `cover_letter_prompt.md` |
| Company-scoped artifact storage | Users need files by application | Low | YES (`data/<company>/`) | CLI-only; web UI needs to expose this |
| Status tracking per application | Core of "job tracker" | Medium | **NO** | Not implemented; data dir exists but no status field |
| View list of past applications | Manage 10-50 concurrent applications | Low | **NO** | No index/list view |
| F1 visa / sponsorship signal | Prevents wasted effort on ineligible roles | Medium | **NO** | JD schema has no sponsorship field; parser doesn't flag it |

---

## Differentiators

Features that set this tool apart.

| Feature | Value Proposition | Complexity | Already Exists? |
|---------|-------------------|------------|-----------------|
| Iterative compile-and-measure one-page enforcement | More reliable than character estimates | High | PARTIAL (expand only, not trim) |
| LaTeX-based resume | Precise typographic control, no formatting drift | High | YES (tectonic compiler) |
| AI reframing WITHOUT fabrication | Reword/reframe but no invented experience | Medium | YES (prompt enforces) |
| Structured cover letter with enforced format | Strict tone + structure (300-400 words) | Medium | YES (`cover_letter_prompt.md`) |
| Per-JD artifact history with iteration tracking | Multiple iterations stored per company | Low | PARTIAL (files named _iter_N) |
| Local LLM option (Ollama) | Privacy: resume data never leaves machine | Medium | YES (Ollama + llama3.1:8b) |
| Graduation date context switching | "May 2026" full-time, "Dec 2026" internships | Low | PARTIAL (text rule only, not enforced) |
| Sponsorship / F1 visa flag at ingestion | Surfaces deal-breakers before generation | Low | **NO** — high value, low effort |
| Application submission checklist | Remind: no em-dashes, correct date, verify signature | Low | **NO** |

---

## Anti-Features

Deliberately NOT build these.

| Anti-Feature | Why Avoid | Instead |
|--------------|-----------|---------|
| Multi-user / authentication | Solo tool; auth adds weeks for zero personal benefit | No auth — single user |
| Real-time job board scraping / crawlers | Unreliable, legally grey, high maintenance | URL best-effort fetch; paste is reliable fallback |
| Mobile app | Job applications happen at a desk | Responsive web UI sufficient |
| Resume template marketplace | Template switching creates layout regression surface | Perfect one canonical LaTeX template |
| ATS match percentage score | Gameable, misleading, false confidence | Show matched keyword list instead |
| Automated application submission | Legal/ethical risk; ToS violations | Generate materials only; user submits manually |
| Interview prep or coaching | Separate problem domain | Maintain focus on application materials |
| Word / Google Docs resume output | Splits template maintenance | If needed, convert PDF; don't maintain two templates |
| Chrome extension | Significant effort; APIs change frequently | Web UI with paste input is simpler |
| Rich text resume editor | Building an editor is a product unto itself | Generate, review PDF, re-generate with adjusted prompt |

---

## Feature Dependencies

```
JD ingestion (paste text or URL)
  └── JD parser → structured JSON
        ├── F1 visa / sponsorship flag (extracted immediately, shown prominently)
        ├── Master resume selector (JD JSON + master_resume.json)
        │     └── Resume content tweaker (selected content + JD JSON)
        │           └── LaTeX renderer → .tex
        │                 └── LaTeX compiler → PDF
        │                       └── One-page enforcement loop
        │                             ├── page_count > 1 → AI trims → recompile
        │                             ├── whitespace high → AI expands → recompile
        │                             └── pass → Final PDF ✓
        └── Cover letter generator (JD JSON + resume content)

Job tracker (persists per application)
  ├── Status pipeline (generated / applied / interviewing / offer / rejected)
  ├── Application list view (index of data/*)
  └── Per-application artifact links

Web UI
  ├── JD input form (paste or URL)
  ├── F1 flag display (immediate, prominent, before generation)
  ├── Generation progress view
  ├── Artifact download (resume PDF, cover letter)
  ├── Application pipeline board (kanban or table)
  └── Application detail view
```

---

## MVP Priority Order

### Must Have
1. JD paste input → structured JSON (port CLI to web API)
2. **F1 visa signal** — parse sponsorship keywords, display prominently before generation (LOW effort, HIGH value)
3. Master resume selector + content tweaker (refactor into discrete pipeline stages)
4. **One-page enforcement in BOTH directions** — current loop only expands; must also trim when overflow (most critical gap)
5. Cover letter generation (cleanup fragile docx2pdf dependency)
6. Artifact download via web UI
7. Job tracker: status field per application

### Should Have
8. Application list view (index of all data/*/ with status badges)
9. Application detail view (artifacts, status, iteration count)
10. Submission checklist (post-generation reminder)

### Defer
- URL-based JD scraping (paste is reliable; URL adds error surface)
- Multi-LLM support (add only if Ollama proves insufficient)
- Application notes / journal

---

## Implementation Notes for Critical Features

### F1 Visa Flag (LOW complexity, critical)

Add to `job_description_schema.json`:
```json
{
  "visa_sponsorship": "yes | no | not_mentioned",
  "visa_keywords_found": []
}
```

Keywords to detect: "sponsorship", "authorize to work", "require sponsorship", "H-1B", "OPT", "CPT",
"citizen only", "permanent resident", "US persons only", "no visa support", "must be authorized"

Display immediately after JD parsing. If "no" → show hard warning block. User must explicitly proceed.

### One-Page Enforcement — Missing Trim Direction (HIGH priority)

Current `main.py` loop only expands content when whitespace exceeds threshold. If initial render > 1 page, there is NO trim mechanism.

Fix:
1. After compile: `fitz.open(pdf).page_count > 1` → overflow
2. If overflow: re-prompt LLM to shorten longest bullet points → recompile
3. If underflow (whitespace > threshold): re-prompt to expand (existing behavior)
4. Max N iterations (configurable in config.yaml)

PyMuPDF already imported in `pdf_analyzer.py` — page count is one line.

### Job Tracker Status (LOW complexity)

Add `status.json` per `data/<company>/` directory. No database needed.

```json
{
  "status": "generated",
  "company": "Cisco",
  "role": "Software Engineer Intern",
  "applied_date": null,
  "last_updated": "2026-02-21",
  "artifacts": {
    "resume_pdf": "Cisco_resume_iter_2.pdf",
    "cover_letter": "Cisco_cover_letter.txt",
    "jd_json": "Cisco_jd.json"
  }
}
```

Status values: `generated → applied → phone_screen → interviewing → offer → rejected → withdrawn`

### Cover Letter PDF Dependency (fragile)

`docx2pdf` requires Microsoft Word or LibreOffice. Breaks on clean deployments.

Options ranked by simplicity:
1. Serve plain text `.txt` for download — skip PDF conversion for cover letter (MVP)
2. Generate cover letter as PDF via WeasyPrint (HTML template → PDF)
3. Keep docx2pdf but document LibreOffice requirement clearly

---

## Key Gaps vs. Stated Requirements

| Gap | Severity | Effort |
|-----|----------|--------|
| No F1 visa signal | Critical (first-class requirement) | Low |
| One-page trim direction missing | Critical (hard requirement) | Medium |
| No job tracker status system | High ("tracker" is in the product name) | Low |
| No web UI | High (stated requirement) | High |
| Cover letter PDF dependency fragile | Medium | Low–Medium |
