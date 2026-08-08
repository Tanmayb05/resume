# `/add-job` — documentation

Turns a pasted job description into a complete, tailored application package:
resume (JSON + LaTeX + PDF), cover letter (text + DOCX + PDF), a new job
folder, and a scored row in the Excel tracker. Runs entirely inside Claude
Code — no external LLM API, no Ollama.

## Usage

```
/add-job <paste the job description>
```

Or, if you'd rather not paste it inline:

```
/add-job path/to/jd.txt
/add-job https://company.com/careers/12345
```

If you give nothing, Claude falls back to `input/jd.txt` if it's non-empty.
If none of these produce a usable JD, it stops and asks — it will not invent
one. It also stops if the JD looks truncated (under ~400 characters).

**Ambiguous company / role / location**: these three fields decide the job
folder's name and the tracker's duplicate-detection key, so if the JD doesn't
state them clearly, Claude asks rather than guesses.

**Duplicate jobs**: re-running `/add-job` on a JD for a company+role already
in `data/` does not create a second folder — it reports the existing one and
asks whether to reuse it or force a variant.

### What you get

```
data/<company-slug>-<role-slug>/
  job.json                 structured job record
  jd.txt                   the JD you gave it
  extraction.json           extraction + match-score justifications
  resume_content.json       Claude's content selection (ids + bullet rewrites)
  resume_iter_N.json        the full render payload for the accepted iteration
  resume_iter_N.tex
  resume_iter_N.pdf         one page, ATS-parsable
  cover_letter.txt          canonical text — source of truth
  cover_letter.docx
  cover_letter.tex
  cover_letter.pdf
  tracker_extras.json       what got written into the spreadsheet
```

Plus one new row in `output/Tanmay_Job_Application_Tracker.xlsx`, including
match scores in columns N–R.

## How it works

Split down the middle on purpose:

- **Claude does the creative work**: reading the JD, deciding company/role/
  location/visa signals, scoring the match 0–10 on five dimensions, choosing
  which resume experiences/projects/skills to show, rewriting bullets to fit
  the JD, writing the cover letter.
- **Python does the mechanical work**: creating the job folder, assembling
  the LaTeX render payload, compiling PDFs, building the DOCX, writing into
  the spreadsheet. None of it calls an LLM.

This is a parallel path — it does not touch the existing `scripts/run.py`
Ollama pipeline. Both can coexist; nothing here changes how that one runs.

### The ten steps

1. **Acquire the JD** — argument text, file, URL, or `input/jd.txt`. Stops
   and asks if nothing usable is found.
2. **Preflight** — restores `templates/cover_letter_template.tex.j2` from git
   if missing, checks `docx`/`openpyxl`/`jsonschema` are installed.
3. **Extract + score** (Claude) — reads
   `templates/add_job_extraction_prompt.md`, writes
   `input/last_extraction.json` with company/role/location/visa/dates and
   five 0–10 match scores, each with a one-line justification.
4. **Create job folder** — `scripts/add_job.py init` allocates
   `data/<slug>/`, writes `job.json` + `jd.txt`, checks for a duplicate.
5. **Tailor resume content** (Claude) — reads
   `templates/add_job_tailoring_prompt.md` + `master_resume.json`, writes
   `resume_content.json`: which experience/project ids to show, in what
   order, with rewritten bullets, and which skills to surface.
6. **Build + fit-check** (loop, capped at 4 iterations) —
   `scripts/add_job.py build-resume` assembles the full render payload,
   validates it against the schema, renders LaTeX, compiles with `tectonic`,
   measures page count and whitespace. Claude edits `resume_content.json` and
   retries if it's too long or too sparse; reads the LaTeX error and fixes
   content (never the `.tex` directly) on a compile failure.
7. **Write cover letter** (Claude) — follows
   `templates/cover_letter_prompt.md` exactly: fixed salutation, fixed
   opening line, 3–5 numbered reasons in JD order, fixed closing, fixed
   signature block, 220–320 words, no em dashes.
8. **Build DOCX + PDF** — `scripts/add_job.py build-cover-letter` checks the
   text (word count, em dash, leftover placeholders, wrong graduation date),
   then renders both formats from the same `cover_letter.txt` so they can't
   drift apart.
9. **Update tracker** — `scripts/add_job.py track` writes company, role,
   scores, dropdowns, and status into the Applications sheet.
10. **Report** — folder path, all artifact paths, page/whitespace stats,
    word count, the five scores plus the computed Hiring Score, tracker row
    number, and any warnings.

## The anti-fabrication guarantee

The one part of this skill worth understanding even if you never read the
code: Claude **cannot** put a wrong fact on the resume, structurally.

`resume_content.json` — the only file Claude writes for resume content — may
only say *which* master-resume entries to include and *what the bullet text
should say*. It cannot set a date, company name, job title, degree,
institution, or tech stack; `src/resume/ir_builder.py` pulls all of those
straight from `templates/master_resume.json` and raises an error if the
content file tries to override any of them. Skills work the same way — every
item must already exist in `master_resume.json`'s skill lists, verbatim.

Concretely: if Claude's `resume_content.json` says
`{"dates": "Jan 2030 - Now"}` inside an experience override, or lists a skill
that isn't in the master resume, `build-resume` fails immediately with an
error naming exactly what was rejected. This can't reach a rendered PDF.

## Known conflicts this skill resolves

- **Graduation date**: `src/cover_letter/service.py` (the old Ollama path)
  says May 2026; `master_resume.json` and `templates/cover_letter_prompt.md`
  both say December 2026. This skill uses December 2026 and will hard-reject
  a cover letter that contains "May 2026".
- **Cover letter DOCX + PDF, no converter installed**: there's no
  LibreOffice/pandoc on this machine, so DOCX and PDF are built
  independently from the same `cover_letter.txt`, both via the same
  paragraph split, so they can't diverge in content — only in formatting.

## Requirements

- `tectonic` on PATH (LaTeX compilation) — already required by the existing
  pipeline.
- `python-docx`, `openpyxl`, `jsonschema` — added to `requirements.txt`,
  install with `.venv/bin/pip install -r requirements.txt`.
- The tracker workbook must be closed in Excel before step 9 runs, or the
  write fails cleanly with a `tracker_locked` error (nothing else is lost —
  every other artifact is already on disk, and every step is safe to
  re-run).

## Files this skill introduces

| File | Role |
|---|---|
| `.claude/skills/add-job/SKILL.md` | The orchestration Claude follows |
| `.claude/skills/add-job/reference/resume_content_contract.md` | Exact shape of `resume_content.json` |
| `scripts/add_job.py` | CLI: `init`, `build-resume`, `build-cover-letter`, `track` |
| `src/resume/ir_builder.py` | Pure master_resume → render-payload assembly, fabrication guards |
| `src/cover_letter/docx_writer.py` | DOCX rendering, shared paragraph splitting |
| `templates/add_job_extraction_prompt.md` | JD extraction + scoring rubric |
| `templates/add_job_tailoring_prompt.md` | Resume content selection rules |

Modified: `src/resume/selection.py` (now re-exports from `ir_builder.py`,
behavior unchanged — see the golden-output regression test),
`src/storage/tracker_store.py` (adds numeric score writing, formula-column
guard, `extras` parameter — old two-argument calls are unaffected).

## Tests

```
.venv/bin/python -m pytest tests/ -q
```

`tests/test_ir_builder.py` — schema compliance, fabrication guards, golden
regression against the pre-refactor payload.
`tests/test_tracker_extras.py` — numeric writes don't corrupt formulas,
dropdown/score validation, real-workbook integration.
`tests/test_cover_letter_docx.py` — paragraph splitting, DOCX rendering,
text-quality gates.
