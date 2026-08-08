# Job Scraper Roadmap

Standalone scraper package: fetches job listings from target employers, filters by
role type and experience level, deduplicates across runs, and outputs a Markdown
report with links. Supports two company lists via `--company-list {tech,cap_exempt}`,
sharing one engine (ATS fetchers, filters, dedup, report generator).

## Scope

- **Source**: Each employer's careers page (Greenhouse/Lever/Ashby/Workday JSON APIs
  where available, requests+BS4 for others)
- **Filter**: Last N days (default 7 for `tech`, 30 for `cap_exempt`), US/remote only,
  Internship + New Grad + Mid-level
- **Role match**: Broad semantic — title keywords + equivalents (Research Engineer,
  Platform Engineer, etc.)
- **Dedup**: Seen job IDs tracked per-variant in `scraper/output/<list>/seen_jobs.json`
- **Scoring**: Resume-skill keyword overlap against `templates/master_resume.json` →
  optional "Match %" column, on by default for `cap_exempt`, off for `tech`
  (`--match-score` / `--no-match-score` to override)
- **Output**: `scraper/output/<list>/jobs_report.md` — grouped by employer, title +
  link + location + date (+ match % and visa note when applicable)
- **Blocked employers**: Listed at bottom with careers URL for manual check

## Registry status

`scraper/core/registry.py` defines a `verified: bool` field on `Company`: `True`
means the ATS type/slug has been confirmed against a live API, `False` means it's a
best guess still defaulted to `ats="blocked"` pending manual verification.

- `scraper/companies/tech.py` — all entries verified as of 2026-03-08.
- `scraper/companies/cap_exempt.py` — most entries unverified as of 2026-07-15
  (Stanford, CMU, Cornell, ASU, Mayo, Cleveland Clinic, St. Jude, Fred Hutch,
  Wikimedia, Mozilla, Khan Academy, CZI, Allen Institute, AI2 have ATS type guesses;
  everything else defaults to `blocked`).

To verify a Workday slug, hit:

```
https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
```

To verify Greenhouse/Lever, hit the public APIs directly:

```
https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
https://api.lever.co/v0/postings/{slug}?mode=json
```

Flip verified entries from `ats="blocked"` to their real ATS type and set
`verified=True` in the relevant `scraper/companies/*.py` file as confirmed.

## Role keywords (semantic match)

```python
ROLE_KEYWORDS = [
    # Engineering
    "software engineer", "software developer", "swe",
    "backend", "back-end", "back end",
    "frontend", "front-end", "front end",
    "fullstack", "full-stack", "full stack",
    "platform engineer", "infrastructure engineer",
    "devops", "site reliability", "sre",
    # ML / AI
    "machine learning", "ml engineer",
    "ai engineer", "artificial intelligence",
    "research engineer", "research scientist",
    "deep learning", "nlp engineer",
    "data scientist", "data engineer",
    "applied scientist",
    # Other technical
    "mobile engineer", "ios engineer", "android engineer",
    "security engineer", "cloud engineer",
    "systems engineer", "embedded engineer",
]

EXPERIENCE_KEYWORDS = {
    "intern": ["intern", "internship", "co-op", "coop"],
    "new_grad": ["new grad", "entry level", "university grad", "associate", "junior"],
    "mid": [],  # default if no seniority keyword — most roles
}

EXCLUDE_KEYWORDS = ["staff", "principal", "director", "vp ", "vice president", "head of", "manager", "senior staff"]
```

## Files

```
scraper/
├── ROADMAP.md               ← this file
├── requirements.txt         ← httpx, beautifulsoup4, rich
├── run.py                   ← entry point: python scraper/run.py --company-list {tech,cap_exempt}
├── companies/
│   ├── tech.py               ← COMPANIES list, top tech companies (verified)
│   └── cap_exempt.py         ← COMPANIES list, H-1B cap-exempt orgs (mostly unverified)
├── core/
│   ├── registry.py           ← Company dataclass + load_companies()
│   ├── filters.py            ← role/location/date/level filtering
│   ├── dedup.py               ← seen_jobs.json read/write, path passed in per-variant
│   ├── report.py              ← markdown report generator, match-score/visa-note opt-in
│   └── ats/
│       ├── greenhouse.py
│       ├── lever.py
│       ├── ashby.py
│       ├── workday.py
│       └── custom.py
└── output/                   ← gitignored, auto-generated per company-list
    ├── tech/
    │   ├── seen_jobs.json
    │   └── jobs_report.md
    └── cap_exempt/
        ├── seen_jobs.json
        └── jobs_report.md
```

## History

- **2026-03** — Initial tech-company scraper (`companies_jobs_search/`): 50 target
  tech companies, Greenhouse/Lever/Workday/custom fetchers, keyword filtering, dedup,
  markdown report.
- **2026-07** — Cap-exempt variant added (`companies_job_search_cap_exempt/`):
  targets H-1B cap-exempt-eligible orgs, adds resume match-scoring and visa-note
  metadata. Shared 100% of the ATS/filter/dedup engine via copy-paste.
- **2026-08** — Consolidated both into this single `scraper/` package: one engine,
  two data-driven company lists, match-score/visa-note behavior derived from company
  metadata instead of duplicated code paths.
