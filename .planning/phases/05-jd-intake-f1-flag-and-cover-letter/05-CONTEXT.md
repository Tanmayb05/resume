# Phase 5: JD Intake, F1 Flag, and Cover Letter - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Users paste a job description → system parses it into a structured JSON record, detects F1 sponsorship signals via keyword matching, and generates a cover letter saved as both `.txt` and `.pdf` to `data/<company_slug>/`. Creating the web UI, HTTP routes, and browser-based submission are separate phases.

</domain>

<decisions>
## Implementation Decisions

### F1 Sponsorship Detection
- Flag is a **boolean**: `true` means sponsorship IS offered (OPT/H-1B supported), `false` means not offered
- When no sponsorship-related keywords are found: default to **null/unknown** (not false) — distinguishes "explicitly not offered" from "not mentioned"
- Matching is **case-insensitive + normalized variants**: handles "H1B" vs "H-1B" vs "H1-B", and avoids false positives like "opt-in" for "opt"
- No reason string stored — just the boolean/null value on the job record

### JD Parsing Behavior
- **Required fields** for parse success: company, role, location — all three must be non-null
- On missing required fields: **retry once** with the same or stricter prompt, then fail if still missing (do not persist a partial record)
- **Duplicate company slug**: create a new versioned record (e.g., `acme_v2`) — never overwrite existing data
- Validation approach: Claude's discretion (validate required fields + reasonable structural check)

### Cover Letter Content and Tone
- **Resume context**: full resume text passed to the LLM (all sections)
- **Tone**: professional but conversational — warm and direct, sounds human-written
- **Prompt**: use `templates/cover_letter_prompt.md` as the generation prompt (structure, salutation, body format, signature block are all defined there)
- **Graduation date**: "May 2026" for full-time roles, "Dec 2026" for internships; Claude determines other internship vs full-time adaptations
- **Word count enforcement**: retry with an explicit correction prompt on out-of-range output — "Previous version was X words, please shorten/expand to 300–400 words"
- **No em-dashes**: enforced via prompt (already in template); strip any remaining em-dashes post-generation as a safety net

### Cover Letter Output Format
- **Filename**: `cover_letter.txt` and `cover_letter.pdf` — fixed names inside `data/<company_slug>/` (overwritten on regeneration)
- **Structure**: follow `templates/cover_letter_template.docx` as layout reference
- **Text output**: plain `.txt` with the letter body exactly as generated (no extra metadata header)
- **PDF generation**: Claude's discretion on library — must be pure Python with no LibreOffice dependency; Microsoft Word via `docx2pdf` is acceptable if present but not required

### Claude's Discretion
- Validation depth for JD schema (beyond required fields check)
- PDF generation library choice (reportlab, fpdf2, WeasyPrint, or docx2pdf if Word available)
- Internship vs full-time tone adaptation beyond the graduation date
- Exact F1 keyword list and normalization rules

</decisions>

<specifics>
## Specific Ideas

- `templates/cover_letter_prompt.md` is the canonical prompt — use it verbatim as the system/user prompt for cover letter generation; do not paraphrase it
- `templates/cover_letter_template.docx` defines the expected layout for the PDF output
- Cover letter must feel "human-written rather than AI-generated" per the prompt template
- "I saw the job post on [Job Source]" — job source may not be known from JD text alone; handle gracefully (e.g., "your website" as fallback or leave as a placeholder)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-jd-intake-f1-flag-and-cover-letter*
*Context gathered: 2026-02-25*
