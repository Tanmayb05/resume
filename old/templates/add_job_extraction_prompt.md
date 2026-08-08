# JD Extraction and Match Scoring

You are reading a job description to produce one JSON object. Write it to
`input/last_extraction.json`. It is the input to `scripts/add_job.py init`.

Extract only what the JD actually says. This file drives the folder name, the tracker
row, and every downstream artifact, so a confident guess is worse than a null.

## Hard rules

1. **Never invent a field.** If the JD does not state it, use `null` (or `[]` for lists).
2. **`company`, `role`, and `location` are mandatory and must not be guessed.** They
   determine the directory slug and the duplicate-detection key. If any of the three is
   absent or ambiguous in the JD, stop and ask the user instead of inferring.
3. Copy the full JD verbatim into `jd_text`. Downstream steps re-read it.
4. Dropdown fields must use one of the exact values listed below. An off-list value is
   rejected by `_sanitize_extras` and shows a validation error in Excel.

## Output shape

```json
{
  "company": "Acme Robotics",
  "role": "Software Engineer, Platform",
  "location": "Cincinnati, OH",
  "employment_type": "Full-time",
  "department": null,
  "description": "One or two sentence summary of the role.",
  "jd_text": "<the full job description, verbatim>",
  "responsibilities": ["..."],
  "requirements": ["..."],
  "qualifications": ["..."],
  "skills_technical": ["Python", "Kubernetes"],
  "skills_soft": ["..."],
  "education": ["BS in Computer Science or equivalent"],
  "experience_required": "2+ years",
  "benefits": ["..."],
  "salary_range": null,
  "date_posted": "2026-07-20",
  "application_deadline": null,
  "visa_keywords": ["we sponsor H-1B"],
  "f1_sponsorship_available": true,

  "job_url": "https://acme.example/careers/123",
  "job_id": "REQ-123",
  "source": "LinkedIn",
  "work_arrangement": "Remote",

  "scores": {
    "technical_match": {"value": 8.5, "why": "Owns 6 of 8 required skills; no Rust exposure."},
    "ats_match": {"value": 8.0, "why": "JD keywords Python/K8s/Docker/CI-CD all appear literally."},
    "experience_match": {"value": 7.5, "why": "Asks 2+ years; has 2 years production plus MS in progress."},
    "hiring_risk": {"value": 8.0, "why": "Sponsors H-1B, no clearance requirement, no senior-only wall."},
    "competition": {"value": 5.5, "why": "Remote US new-grad platform role draws a very large pool."}
  }
}
```

## Dropdown vocabularies

- `employment_type`: `Full-time` | `Internship` | `Contract` | `Part-time` | `Temporary`
- `work_arrangement`: `Remote` | `Hybrid` | `On-site` | `Flexible` | `Unknown`
- `source`: `Company Careers` | `LinkedIn` | `Referral` | `Recruiter` | `Handshake` |
  `Indeed` | `Other`

Infer `source` from the URL: a `linkedin.com` link is `LinkedIn`, a company careers
subdomain is `Company Careers`, otherwise `Other`.

## Sponsorship detection

Set `f1_sponsorship_available` with the same three-way logic the pipeline already uses
(`src/jd/service.py::detect_f1_sponsorship`), and record the phrases you matched in
`visa_keywords`.

- `true` — the JD **offers** sponsorship: "will sponsor", "visa sponsorship",
  "sponsorship available/provided/offered", "H-1B", "OPT eligible", "open to sponsoring".
- `false` — the JD **denies** it: "no sponsorship", "sponsorship is not available",
  "must be a US citizen", "citizens and permanent residents only", "cannot sponsor",
  "do not sponsor", "must already be authorized".
- `null` — no sponsorship language at all, **or positive and negative signals both
  appear**. Conflicting signals are ambiguous, not positive. "We sponsor H-1B but you
  must already be authorized to work" is `null`.

This maps to the tracker as `true` → `Sponsorship Likely`, `false` → `No Sponsorship`,
`null` → `Unknown`.

## Scoring rubric

Five independent scores, 0-10, each with a one-line `why` so the number stays auditable.
They feed the workbook's Hiring Score:
`technical*0.35 + ats*0.20 + experience*0.15 + hiring_risk*0.15 + competition*0.15`.

Score against `templates/master_resume.json`, not against an idealized candidate.

- **technical_match** — what fraction of the JD's required technical skills are evidenced
  in the master resume? 10 = every required skill appears; 5 = about half; 0 = a different
  discipline entirely.
- **ats_match** — literal keyword overlap between the JD and the resume text you are about
  to generate. Judge the exact strings a keyword filter would look for, not synonyms.
- **experience_match** — required years and seniority versus roughly 2 years of production
  engineering plus an MS in progress. A "2+ years" ask scores high; "8+ years, Staff"
  scores low; an internship asking for coursework scores high.
- **hiring_risk** — **10 means low risk.** Score high when the role sponsors visas, needs
  no security clearance, and has no senior-only requirement. Score low for "US citizens
  only", an active clearance, or a hard 5+ year minimum.
- **competition** — **10 means favorable.** Score high for a niche stack, a narrow
  location, or an unusual domain. Score low for a generic "New Grad SWE, Remote, US"
  posting that attracts thousands of applicants.

Do not round toward the middle to feel safe. A 4 that is honest is more useful than a 7
that is diplomatic.
