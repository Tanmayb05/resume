---
name: add-job
description: >
  Take a pasted job description and produce a complete tailored application
  package in the resume repo: a job folder under data/<company>-<role>/, an
  ATS-friendly one-page resume (JSON + LaTeX + PDF), a cover letter (text +
  DOCX + PDF), and a new row in output/Tanmay_Job_Application_Tracker.xlsx
  with match scores. Claude does the JD extraction, resume tailoring, cover
  letter writing, and scoring; Python helpers do slugging, rendering, LaTeX
  compilation, and spreadsheet writing. Triggers on /add-job.
allowed-tools: Read, Write, Bash(.venv/bin/python scripts/add_job.py:*), Bash(.venv/bin/python -c *), Bash(git checkout -- templates/*), Bash(test -f templates/*)
---

# Add Job

## What this does

Turns a job description into a complete application package without touching the
existing Ollama-driven pipeline (`scripts/run.py`). Claude does every creative step —
extracting the JD, scoring the match, choosing which resume content to show, writing the
cover letter. `scripts/add_job.py` does every mechanical step — creating the job
directory, rendering LaTeX, compiling PDFs, building the DOCX, and writing the tracker
row. Neither side does the other's job: Python never calls an LLM, and Claude never hand-
edits a `.tex` file.

Output lands in `data/<company-slug>-<role-slug>/`: `job.json`, `jd.txt`,
`extraction.json`, `resume_content.json`, `resume_iter_N.{json,tex,pdf}`,
`cover_letter.{txt,docx,tex,pdf}`, `tracker_extras.json`.

## Steps

### 1. Acquire the job description

In priority order:
1. Text passed directly as the `/add-job` argument.
2. A file path or URL argument — `Read` the file, or fetch the URL if it's a link (keep
   the URL, it becomes the tracker's `Job URL`).
3. `input/jd.txt`, if it exists and is non-empty.

If none of these produce a JD, **stop and ask the user to paste one.** Never invent or
guess at a job description.

If the JD is under ~400 characters, stop and say it looks truncated — ask for the full
text before continuing. A bad extraction downstream produces a plausible-looking but wrong
application package, which is worse than stopping here.

### 2. Preflight

```bash
test -f templates/cover_letter_template.tex.j2 || git checkout -- templates/cover_letter_template.tex.j2
.venv/bin/python -c "import docx, openpyxl, jsonschema"
```

If the import fails, tell the user to run `.venv/bin/pip install -r requirements.txt` and
stop.

### 3. Extract and score

Read `templates/add_job_extraction_prompt.md`, apply it to the JD, `Write` the result to
`input/last_extraction.json`.

`company`, `role`, and `location` drive the folder slug and the tracker dedup key — if any
is ambiguous in the JD, ask the user rather than guess. Every other field can be `null` or
`[]` if the JD doesn't say.

### 4. Create the job directory

```bash
.venv/bin/python scripts/add_job.py init --extraction input/last_extraction.json
```

If the response has `duplicate_of` set, report the existing directory to the user and ask
whether to reuse it or create a variant with `--allow-duplicate`. Do not proceed silently
either way.

The response includes `available_ids` — the exact experience/project ids and skill
categories valid for step 5.

### 5. Tailor resume content

Read `templates/master_resume.json`, `templates/add_job_tailoring_prompt.md`,
`templates/resume_generation_prompt.md`, `templates/resume_generation_config.json`, and
`.claude/skills/add-job/reference/resume_content_contract.md`. `Write`
`<job_dir>/resume_content.json` per that contract.

### 6. Build the resume and enforce one page

```bash
.venv/bin/python scripts/add_job.py build-resume --job-dir <job_dir> --content <job_dir>/resume_content.json --iter 1
```

Branch on `verdict`, incrementing `--iter` on every retry, capped at **4 iterations**:

- `accept` — proceed. If `ats_parsable` is false, warn the user loudly; a PDF with no
  extractable text defeats the purpose of an ATS-friendly resume.
- `too_long` — edit `resume_content.json`: drop the weakest project first, then trim the
  longest bullets, then reduce skills items. Never remove a section — all five are
  required by the schema. Re-run with the next `--iter`.
- `too_sparse` — follow `templates/resume_expansion_prompt.md`: restore a project, restore
  trimmed bullet detail, widen a skills line. Re-run.
- `ok: false`, `error_type: compilation_failed` — `Read` the returned `.tex` and `stderr`,
  find the LaTeX error (almost always an unbalanced `**bold**` marker), and fix the
  *content* in `resume_content.json`. Never hand-edit the generated `.tex`.

If 4 iterations pass without `accept`, keep the closest artifact, tell the user which
iteration and why, and continue — partial output beats none.

Report any `violations` from the response verbatim; a violation means fabricated content.
Fix `resume_content.json` and re-run. Never waive a violation.

### 7. Write the cover letter

Read `templates/cover_letter_prompt.md` and the accepted `resume_iter_N.json`. Follow the
prompt exactly — salutation, opening sentence, numbered reasons in JD-requirement order,
availability paragraph, closing, signature block, word count, no em dashes. `Write` to
`<job_dir>/cover_letter.txt`.

### 8. Build the DOCX and PDF

```bash
.venv/bin/python scripts/add_job.py build-cover-letter --job-dir <job_dir> --text <job_dir>/cover_letter.txt
```

Failures here (word count, em dash, leftover placeholder, stale "May 2026") are mechanical
— fix `cover_letter.txt` and re-run.

### 9. Update the tracker

`Write` `<job_dir>/tracker_extras.json` from the step-3 extraction — the scores, the
dropdown values, the job URL/ID.

```bash
.venv/bin/python scripts/add_job.py track --job-dir <job_dir> --extras <job_dir>/tracker_extras.json
```

### 10. Report

Summarize for the user: job directory, all six artifact paths, resume page count and
whitespace percent, cover letter word count, the five scores plus the computed Hiring
Score (`technical*.35 + ats*.20 + experience*.15 + risk*.15 + competition*.15`) so they
can sanity-check it against the workbook's column S, the tracker row number, and any
warnings carried over from earlier steps.

## Notes

- The Ollama pipeline (`scripts/run.py`, `src/llm/*`, `src/jd/service.py`,
  `src/resume/service.py`, `src/cover_letter/service.py`) is untouched and unrelated —
  this skill never calls it.
- `src/cover_letter/service.py::_resolve_graduation_date` returns "May 2026" for
  full-time roles, which is wrong. `templates/cover_letter_prompt.md` and
  `master_resume.json` both say December 2026 — that's the value this skill uses.
  `build-cover-letter` hard-rejects "May 2026" if it slips into the text.
- `data/` is gitignored — everything this skill writes is local-only.
- Close the tracker workbook in Excel before running step 9, or the write fails with a
  clear `tracker_locked` error and nothing else is lost — every other artifact is already
  on disk and every step is safe to re-run.
- The workbook's `ApplicationsTable` covers rows 5-304. Past 300 applications, new rows
  fall outside the table and lose the App ID and Hiring Score formulas — not handled here,
  just flagged if it comes up.
