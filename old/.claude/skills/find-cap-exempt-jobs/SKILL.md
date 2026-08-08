---
name: find-cap-exempt-jobs
description: >
  Find entry-level and new-grad Software Engineer / ML / AI openings at
  H-1B cap-exempt-eligible organizations — nonprofit research orgs, FFRDCs,
  universities, teaching hospitals, and large nonprofits — instead of
  commercial tech companies. Runs the shared scraper in scraper/ (in the
  resume repo at ~/Documents/resume) with --company-list cap_exempt,
  scores results against the resume in templates/master_resume.json, and
  reports new postings. Triggers on /find-cap-exempt-jobs.
allowed-tools: Bash(python3:*), Bash(python:*), Bash(pip:*), Bash(pip3:*)
---

# Find Cap-Exempt Jobs

## What this does

Runs `scraper/run.py --company-list cap_exempt` inside the resume repo
(`~/Documents/resume`), which scrapes job boards for organizations in
four tiers — FFRDCs/nonprofit research orgs, universities, teaching
hospitals, and large nonprofits — filters for SWE/ML/AI/backend/cloud
roles at intern/new-grad/mid level, dedups against previously-seen
postings, scores each listing against the resume skills in
`templates/master_resume.json`, and writes
`scraper/output/cap_exempt/jobs_report.md`.

## Steps

1. `cd ~/Documents/resume`
2. Ensure deps are installed: `pip install -q -r scraper/requirements.txt` (only if imports fail)
3. Run the scraper: `python3 scraper/run.py --company-list cap_exempt --days 30`
   (default lookback for this list is already 30 days; add `--no-dedup` to
   see all matches regardless of prior runs)
4. Read the generated `scraper/output/cap_exempt/jobs_report.md`
5. Summarize the new postings to the user directly in chat, sorted by:
   visa/cap-exempt friendliness → resume match % → application deadline
   (if present). Flag the "Manual Check Required" section — these are
   orgs with no verified ATS integration, so surface their careers URLs
   too rather than silently dropping them.

## Notes

- The registry (`scraper/companies/cap_exempt.py`) has unverified ATS
  slugs for many orgs — they default to `blocked` until confirmed live
  (see `verified` field in `scraper/core/registry.py`). If the report
  comes back mostly "Manual Check Required," that's expected; tell the
  user which orgs still need slug verification rather than treating it
  as a failure.
- This pipeline shares one scraper engine (`scraper/core/`) with the
  tech-company list (`scraper/companies/tech.py`, `--company-list tech`).
  Don't pass `--company-list tech` when running this skill.
- Resume-generation and cover-letter steps are NOT part of this skill —
  it only finds and ranks postings. Suggest the user run the repo's
  existing resume pipeline (`src/resume_generator.py`) manually per
  listing they want to apply to.
