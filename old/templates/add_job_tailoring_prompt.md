# Resume Tailoring for /add-job

You are choosing which parts of `templates/master_resume.json` appear on a one-page resume
for a specific job, and rewriting bullet text to foreground what that job asks for.

Output is a single file, `<job_dir>/resume_content.json`. Its exact shape is in
`.claude/skills/add-job/reference/resume_content_contract.md`. The `init` step already
printed the valid ids under `available_ids` — use those strings verbatim.

Read `templates/resume_generation_prompt.md` and
`templates/resume_generation_config.json` first. The rules there apply in full. This file
covers only what is specific to the id-based selection format.

## What you control, and what you cannot

You choose **which** entries appear, in **what order**, and **how bullets read**.

You cannot change any fact. Dates, company names, role titles, degrees, institutions,
tech stacks, and project dates are read straight from `master_resume.json` by
`build_resume_payload()`. An override that tries to set anything other than `bullets` is
rejected with an error. This is deliberate: it makes
`resume_generation_prompt.md` rule 6 structurally impossible to violate.

Skills are likewise constrained. Every category key and every skill string must already
exist in `master_resume.technical_skills`. If the JD wants Terraform and the master resume
does not list it, the honest answer is to omit it, not to add it.

## Selection strategy

1. **Experiences** — include all three unless the page is overfull. Order them so the most
   relevant role is first. The Siemens SDE role is the strongest signal for most
   engineering positions.
2. **Projects** — pick 2, occasionally 3. Choose the ones whose tech stack overlaps the JD.
   A backend/infra JD favors PolicyPilot and the Spotify analytics platform; an AI/ML JD
   favors the memory-augmented LLM research and the news classification work.
3. **Skills** — keep every category that has a relevant entry, and order the items inside
   each category so JD keywords come first. An ATS filter often reads only the first few
   items on a line. Drop items that are irrelevant to this JD to make room, but never drop
   a whole category to zero items. The render schema requires **at least 2 skill
   categories** and **at least 2 items per category** — a single-category or single-item
   selection fails schema validation in `build-resume`.
4. **Extracurricular** — keep both entries by default; drop one only to fix an overflow.

## Rewriting bullets

Bullet rewrites are where tailoring actually happens. For each experience or project you
override:

- Keep the same **number** of bullets as the master entry unless you are fixing page fit.
- Lead each bullet with the action and the technology the JD names.
- Preserve every metric. "reduced deployment time by 40%" must stay 40%.
- Use `**double asterisks**` for the one or two phrases per bullet that should be bold —
  the renderer converts them to `\textbf{}`. Unbalanced markers break LaTeX compilation.
- No first person, no em dashes, no invented scope.
- Do not restate a bullet the reader already saw in another entry.

Every claim must trace back to text already in `master_resume.json`. Rephrasing is
expected; new facts are fabrication. `validate_content` and the schema check will catch
most violations, but they cannot catch an invented metric, so hold that line yourself.

## Page fit

`scripts/add_job.py build-resume` reports a `verdict`. React to it rather than guessing:

- `too_long` — drop the weakest project first, then trim the longest bullets, then reduce
  skills items. Never delete a section; all five are mandatory.
- `too_sparse` — follow `templates/resume_expansion_prompt.md`: add a project back, restore
  bullet detail you trimmed, widen the skills lines.
- `accept` — stop. Do not keep polishing a resume that already fits.

## Do not set `summary`

The render schema forbids a root `summary` key and
`resume_generation_prompt.md` rule 6 bans adding a Summary section. The template's
`PROFESSIONAL SUMMARY` block is unreachable by design. Fold any framing you wanted there
into the first experience bullet instead.
