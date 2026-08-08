# Job Hunt Assistant

## What This Is

A personal web app that streamlines the entire job application workflow. Given a job description (pasted or via URL), it parses it into a structured JSON record, selects the most relevant content from a master resume JSON, generates a tailored LaTeX resume (compiled to one-page PDF), and produces a matching cover letter — all in one flow. Built for a single user on F1 visa status.

## Core Value

From job description to application-ready resume + cover letter in under 15 minutes, with zero manual formatting work.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Job description parser: paste text or URL → structured JSON (using job_description_schema.json schema)
- [ ] F1 visa signal: flag jobs immediately based on sponsorship keywords, shown prominently
- [ ] Master resume selector: AI picks relevant experiences/projects from master_resume.json for the given JD
- [ ] Resume tweaker: AI subtly adjusts tech stack mentions and functionality descriptions to better match JD (no fabricated experience)
- [ ] LaTeX resume generator: produce a .tex file from selected/tweaked content using resume_template.tex
- [ ] One-page enforcement: iterative compile → measure → trim loop until PDF fits exactly one page with minimal whitespace
- [ ] Cover letter generator: produce a 300–400 word cover letter tailored to the JD using cover_letter_prompt.md style
- [ ] Job tracker: persist job JSON files (one per application), track application status pipeline (applied, interview, offer, rejected)
- [ ] Web UI: browser-based interface to input JDs, view generated documents, manage application pipeline

### Out of Scope

- Multi-user / accounts — personal tool only
- Mobile app — web-first
- OAuth / social login — no auth needed (personal tool)
- Real-time job scraping (automated crawlers) — URL scraping is best-effort, paste is always fallback
- Fabricating experience — AI may reword/reframe but cannot invent roles or companies

## Context

- Existing repo has early Python experiments: `src/` contains resume_generator.py, cover_letter_generator.py, main.py, llm.py, pdf_analyzer.py — treat as reference/inspiration, not production code
- Templates already exist: `templates/resume_template.tex`, `templates/cover_letter_template.docx`, `templates/master_resume.json`, `templates/job_description_schema.json`
- User is on F1 visa — visa sponsorship signal is a first-class feature, not an afterthought
- Resume generation pipeline: JD → AI selects from master_resume.json → AI tweaks → render to .tex → compile to PDF → measure page count → if >1 page, AI trims bullet points iteratively → final PDF
- One-page strategy: compile PDF, detect overflow, feed character-per-line context back to AI, AI shortens over-limit bullet points, repeat until one page fits
- Cover letter approach: structured prompt (role + style + resume context + JD + company) → 300–400 word output, human reviews before sending
- Resume rules: no em-dashes, use "May 2026" for full-time applications, "Dec 2026" for internships, no lies
- ATS optimization: keywords from JD woven naturally into resume content

## Constraints

- **Tech stack**: Python backend (existing ecosystem), web frontend TBD
- **LaTeX**: Resume output must be .tex → PDF via LaTeX compiler (pdflatex or equivalent)
- **Single user**: No authentication, no multi-tenancy
- **One-page PDF**: Hard requirement — never submit a 2-page resume
- **AI honesty**: Cannot fabricate experience; can reframe, reorder, reword

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LaTeX for resume output | Precise layout control, easy to version, programmatic generation | — Pending |
| JSON as master resume format | Already exists as master_resume.json, structured for AI selection | — Pending |
| Iterative compile-and-trim for one-page | Most reliable way to enforce page count vs. character estimates alone | — Pending |
| Web app UI | User wants browser interface, not CLI | — Pending |
| Personal tool (no auth) | Single user, no need for accounts | — Pending |

---
*Last updated: 2026-02-21 after initialization*
