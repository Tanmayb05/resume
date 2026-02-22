# Requirements: Job Hunt Assistant

**Defined:** 2026-02-21
**Core Value:** From job description to application-ready resume + cover letter in under 15 minutes, with zero manual formatting work.

---

## v1 Requirements

### JD Intake

- [ ] **JD-01**: User can paste a job description as text and submit it for parsing
- [x] **JD-02**: System parses JD text into structured JSON matching job_description_schema.json (company, role, location, skills, responsibilities, requirements, visa fields)
- [x] **JD-03**: System detects F1 visa / sponsorship signal from JD text (keyword detection: "sponsorship", "H-1B", "OPT", "authorize to work", "citizen only", etc.) and stores result in job record
- [ ] **JD-04**: System persists parsed job record as a JSON file under data/<company_slug>/

### Resume Generation

- [x] **RES-01**: System selects relevant experiences, projects, and skills from master_resume.json based on the JD
- [ ] **RES-02**: System renders a LaTeX .tex file from the selected content using resume_template.tex.j2
- [ ] **RES-03**: System compiles the .tex file to PDF via tectonic
- [x] **RES-04**: System detects PDF page overflow (page_count > 1) and re-prompts AI to shorten the longest bullet points, then recompiles (TRIM mode — up to max_iterations)
- [ ] **RES-05**: System saves final .tex and .pdf artifacts to data/<company_slug>/ with iteration tracking (_iter_N naming)
- [x] **RES-06**: Generated resume content may only use material from master_resume.json — no fabricated experience, skills, tools, or metrics (enforced via post-generation entity validation)

### Cover Letter Generation

- [x] **COV-01**: System generates a cover letter from JD context + selected resume content, following the structure and rules in cover_letter_prompt.md
- [x] **COV-02**: Generated cover letter is 300-400 words; system validates word count and regenerates if outside range
- [ ] **COV-03**: System saves cover letter as plain .txt file to data/<company_slug>/ (no PDF/docx — eliminates LibreOffice dependency)
- [ ] **COV-04**: Cover letter uses correct graduation date: "May 2026" for full-time applications, "Dec 2026" for internships
- [ ] **COV-05**: Cover letter contains no em-dashes

### Web UI

- [ ] **UI-01**: User can access the app in a browser and paste a JD to start the pipeline
- [ ] **UI-02**: User can download the generated resume PDF from the web UI
- [ ] **UI-03**: User can download or copy the generated cover letter text from the web UI

### Job Tracker

- [ ] **TRK-01**: User can view a list of all job applications with company name, role, date, and status badge

---

## v2 Requirements

### JD Intake

- **JD-V2-01**: User can paste a job URL and system scrapes + parses it (best-effort; paste always as fallback)

### Resume Generation

- **RES-V2-01**: EXPAND mode — when whitespace > threshold on a 1-page PDF, AI expands bullet points to better fill the page

### Cover Letter

- **COV-V2-01**: PDF output for cover letter (via WeasyPrint or similar; eliminates docx entirely)

### Web UI

- **UI-V2-01**: F1 visa flag warning displayed prominently before generation starts (with explicit proceed gate)
- **UI-V2-02**: Generation progress indicator during 30-120s pipeline run
- **UI-V2-03**: Application detail view — artifacts, status, iteration count per job

### Job Tracker

- **TRK-V2-01**: Status pipeline per application (generated → applied → interviewing → offer → rejected)
- **TRK-V2-02**: Submission checklist displayed post-generation (no em-dashes, correct date, signature)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user / authentication | Solo personal tool; accounts add weeks of work for zero benefit |
| Mobile app | Job applications happen at a desk; responsive web UI sufficient |
| Automated job application submission | Legal/ToS risk; generate materials only, user submits manually |
| ATS match percentage score | Gameable, misleading; show keyword list instead |
| Resume template marketplace | One perfected template beats many mediocre ones |
| Chrome extension | High maintenance, APIs change; web UI with paste is simpler |
| Interview prep / coaching | Separate problem domain |
| Salary negotiation features | Requires Glassdoor/Levels.fyi integration; out of scope |
| AI tweak of resume content (beyond selection) | Deferred to v2 — selection + LaTeX generation first |

---

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| JD-01 | Phase 5 | Pending |
| JD-02 | Phase 5 | Complete |
| JD-03 | Phase 5 | Complete |
| JD-04 | Phase 5 | Pending |
| RES-01 | Phase 4 | Complete |
| RES-02 | Phase 3 | Pending |
| RES-03 | Phase 3 | Pending |
| RES-04 | Phase 4 | Complete |
| RES-05 | Phase 3 | Pending |
| RES-06 | Phase 4 | Complete |
| COV-01 | Phase 5 | Complete |
| COV-02 | Phase 5 | Complete |
| COV-03 | Phase 5 | Pending |
| COV-04 | Phase 5 | Pending |
| COV-05 | Phase 5 | Pending |
| UI-01 | Phase 6 | Pending |
| UI-02 | Phase 6 | Pending |
| UI-03 | Phase 6 | Pending |
| TRK-01 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---

*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation — traceability table fully populated*
