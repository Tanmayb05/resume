---
created: 2026-02-25T22:44:15.817Z
title: Build end-to-end pipeline runner script
area: tooling
files:
  - scripts/test_pipeline.py
  - src/jd/service.py
  - src/resume/service.py
  - src/cover_letter/service.py
  - input/jd.txt
---

## Problem

No script wires the three services together end-to-end. The user wants to:
1. Paste a JD into `input/jd.txt`
2. Run a single script
3. Get resume PDF + cover letter TXT in `data/<company_slug>/`

`scripts/test_pipeline.py` only runs `ResumeService` with a hardcoded JobRecord (company="Test Corp"). It skips `JDService` (no LLM parse, no F1 detection, no real company slug) and never calls `CoverLetterService`.

All three services are fully built and tested individually. What's missing is a `scripts/run.py` orchestrator that calls them in sequence:
  JDService.parse_and_persist() → JobRecord with real company/role/slug
  ResumeService.generate()      → resume.pdf in data/<company_slug>/
  CoverLetterService.generate() → cover_letter.txt in data/<company_slug>/

## Solution

Create `scripts/run.py` that:
- Loads `input/jd.txt` (error if missing/empty)
- Loads `templates/master_resume.json`
- Loads `AppConfig` (reads from `.env`)
- Creates `LLMClient`, `JobStore`, `JDService`, `ResumeService`, `CoverLetterService`
- Calls the three services in sequence
- Prints clear progress and final output paths
- Exits with code 1 on any hard failure
