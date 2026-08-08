# Domain Pitfalls

**Domain:** AI-powered resume generation with LaTeX PDF output and job tracking web app
**Researched:** 2026-02-21
**Sources:** Existing codebase analysis (src/), .planning/codebase/CONCERNS.md, domain expertise

---

## Critical Pitfalls

### Pitfall 1: LLM Returns Malformed LaTeX That Silently Corrupts Output

**What goes wrong:** The LLM generates LaTeX with markdown code fences (` ```latex\n `) that the parser strips using hardcoded string slicing. Any variation in fence format produces malformed LaTeX that fails to compile with a cryptic tectonic error.

**Why it happens:** Hardcoded slicing `llm_response.strip()[8:-4]` assumes exactly ` ```latex ` at start and ` ``` ` at end. LLMs are nondeterministic about this format.

**Warning signs:**
- tectonic stderr contains "Emergency stop" or "undefined control sequence" on first line
- Generated .tex file begins with a backtick character

**Prevention:**
- Use regex: `re.sub(r'^```\w*\n?', '', text).rstrip('`').rstrip()`
- Validate stripped output begins with `\documentclass` before saving
- Log first 50 chars of stripped LLM output for debugging
- **Phase:** LaTeX generation — fix before anything builds on top of it

---

### Pitfall 2: One-Page Loop Infinite Retry on PDF Compilation Failure

**What goes wrong:** When tectonic fails, `pdf_analyzer.analyze_whitespace()` cannot open the missing PDF and returns `100.0%` whitespace. The loop interprets this as "too much whitespace — retry." Loop exhausts all iterations with multiple LLM calls, producing no usable output.

**Warning signs:**
- All iterations log "Failed to generate PDF" then "Whitespace analysis: 100.00%"
- No PDF in output directory after loop completes

**Prevention:**
- Use sentinel value (`-1.0`) for error state vs `100.0` for measured whitespace
- Skip whitespace retry if PDF compilation failed; only retry with valid PDF
- Hard exit after 2+ consecutive compilation failures
- **Phase:** One-page enforcement — design loop state machine first, code second

---

### Pitfall 3: LLM Fabricates Resume Content (The "No Fabrication" Rule)

**What goes wrong:** Without strongly-worded constraints in every prompt, the model invents skills, tools, metrics, or responsibilities not in `master_resume.json`. A weak constraint like "don't make things up" is overridden by the model's helpfulness impulse.

**Consequences:** User submits resume claiming skills they don't have — potential offer rescission, termination, legal consequences.

**Warning signs:**
- Generated resume mentions tools/languages not in `master_resume.json`
- Metrics appear (e.g., "improved by 40%") not in source data
- New "Skills" entry appears that wasn't in original data

**Prevention:**
- Include in EVERY content prompt: "You may ONLY use content from the provided master_resume.json. Do not add, invent, or extrapolate any experience, skill, tool, technology, metric, or responsibility not explicitly present in the source data."
- After generation, run validation: extract all entities (companies, technologies, metrics) from .tex and verify each appears in `master_resume.json`
- Treat master resume as strict allowlist, not suggestion
- **Phase:** Must be enforced in prompting AND validated post-generation

---

### Pitfall 4: PDF Page Count Detection Misses Overflow

**What goes wrong:** Whitespace-based measurement uses PyMuPDF text block area as percentage of total page area. A 2-page PDF doubles the denominator, making average whitespace appear within threshold even though page 2 exists. Can declare "optimization complete" while delivering a 2-page resume.

**Warning signs:**
- PDF has 2 pages but loop reported "within threshold"
- Output PDF file size >200KB for a text resume

**Prevention:**
- Check `len(doc)` directly: if page count > 1, resume is not one page regardless of whitespace
- Make page count the primary signal; use whitespace only as secondary heuristic for under-fill
- Correct loop condition: `if page_count == 1 AND whitespace <= threshold: done`
- Log `len(doc)` in every loop iteration
- **Phase:** One-page enforcement — fix measurement before building trim logic

---

### Pitfall 5: LaTeX Template Injection via LLM Output

**What goes wrong:** LLM generates LaTeX written directly to disk and compiled without sanitization. Commands like `\input{/etc/passwd}` or `\write18{rm -rf /}` execute during compilation with user permissions.

**Warning signs:**
- Generated .tex contains `\input`, `\include`, `\write`, `\openout` not in original template
- Generated .tex references absolute paths

**Prevention:**
- Scan .tex for dangerous commands after LLM generation: `\write18`, `\openout`, `\input{/`
- Reject any LaTeX command not in template's allowlist
- Never run tectonic with `-shell-escape` flag
- **Phase:** LaTeX generation — implement before any production use

---

## Moderate Pitfalls

### Pitfall 6: Optimization Loop Expands When It Should Trim

**What goes wrong:** Current loop only expands sections when whitespace is too high. The PRD's primary case is trimming when resume overflows to page 2 — opposite problem, opposite solution. Current loop makes an overflowing resume worse.

**Prevention:**
- Separate into two modes: TRIM (page_count > 1) and EXPAND (whitespace > threshold AND page_count == 1)
- Never mix expand and trim signals in the same iteration
- **Phase:** One-page enforcement

---

### Pitfall 7: Company Name Used Unsanitized in File Paths

**What goes wrong:** LLM-extracted company names used directly in `os.makedirs()`. LLM can return `/`, `..`, `\n`, or other special chars. The `.replace(".tex", ".pdf")` substitution also breaks if company name contains `.tex`.

**Prevention:**
- Sanitize immediately: `re.sub(r'[^\w\s-]', '', company_name).strip()[:50]`
- Use `os.path.splitext()` instead of string `.replace()` for extension swapping
- Validate constructed paths remain within `config.data_path`
- **Phase:** Job tracking / pipeline setup

---

### Pitfall 8: ATS Keyword Matching Fails Despite Correct LaTeX Syntax

**What goes wrong:** Font ligatures from `charter` package (fi, fl, ff → single glyphs), `paracol` two-column layout interleaving columns in PDF character stream, and custom bullet points may break ATS text extraction. "Flask" may be indexed as "F ask."

**Warning signs:**
- Copying text from generated PDF produces garbled output
- `pdftotext resume.pdf` produces column-interleaved text
- ATS job portals show 0% keyword match for words visually present

**Prevention:**
- Test: `pdftotext -layout resume.pdf -` and verify logical reading order
- Test ligatures by copying "fi", "fl", "ff" from PDF into text editor
- Avoid `paracol` for keyword-heavy sections
- **Phase:** LaTeX template — validate before any resume generated

---

### Pitfall 9: LLM Token Limit Truncation of LaTeX Output

**What goes wrong:** Full LaTeX template (~200 lines preamble) + `master_resume.json` (2–5KB) + JD JSON (1–2KB) + instructions routinely approaches llama3.1:8b's 8K context window. Model truncates output mid-document — LaTeX fails to compile with "unexpected end of file."

**Warning signs:**
- Generated .tex ends without `\end{document}`
- tectonic error: "unexpected end of input"
- LLM response is exactly at model's max token output

**Prevention:**
- Use model with larger context window, or API-based model (Claude/GPT)
- Separate selection from generation: one LLM call selects relevant items, second renders LaTeX
- Summarize JD JSON to key requirements before injecting into prompt
- Check response ends with `\end{document}` before saving; reject and retry if not
- **Phase:** LLM integration

---

### Pitfall 10: Cover Letter Word Count Drift

**What goes wrong:** Without explicit word count validation, LLMs produce cover letters that are either 200 words (too brief) or 600+ words (too long). Style drifts toward generic corporate language.

**Prevention:**
- Include in prompt: "Generate exactly 300–400 words. Count carefully."
- After generation, count words programmatically; regenerate if outside range
- Include 2–3 example sentences from user's own writing in `cover_letter_prompt.md`
- **Phase:** Cover letter generation

---

### Pitfall 11: docx2pdf Conversion Hangs Without Timeout

**What goes wrong:** `docx2pdf` on macOS falls back to LibreOffice if Word not installed. LibreOffice cold-start in headless mode takes 15–30s and occasionally hangs indefinitely. No timeout. Blocks server thread permanently.

**Prevention:**
- Replace with direct subprocess call: `subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", docx_path], timeout=30)`
- Or generate cover letters as PDF directly (reportlab or WeasyPrint) — eliminates dependency
- **Phase:** Cover letter output

---

## Minor Pitfalls

### Pitfall 12: Relative Path Resolution Fails When Not Run From Project Root
`src/llm.py` references `"templates/job_description_schema.json"` as relative path. Breaks in web app context.
**Fix:** Resolve relative to module file: `os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates', ...)`. Use absolute paths from config validated at startup.

### Pitfall 13: LLM API Has No Timeout
All `requests.post()` calls to Ollama have no `timeout` parameter. Hangs indefinitely on slow model or OOM.
**Fix:** Add `timeout=(10, 120)` to all Ollama requests. Implement retry with backoff.

### Pitfall 14: Job Tracker JSON Files Have No Schema Validation
Manually edited or corrupted job JSON files cause KeyError or silent incorrect pipeline state.
**Fix:** Define Pydantic model for job records. Validate on load. Quarantine malformed files.

### Pitfall 15: Whitespace Threshold Miscalibrated for Dense Template
Default 40% threshold may not be appropriate for the current 9pt font, 0.5cm margin template. Legitimately full resume may measure above threshold, triggering unnecessary expansion.
**Fix:** Calibrate empirically with 5 sample resumes at different fill levels. Document the calibration.

---

## Phase-Specific Warnings

| Phase Topic | Pitfall | Mitigation |
|-------------|---------|------------|
| LaTeX template setup | ATS parsability (P8) | Run `pdftotext` test before any resume generated |
| LLM integration | Token limit truncation (P9) | Test with max-size inputs first |
| LLM integration | No timeout on calls (P13) | Add `timeout=(10, 120)` from day 1 |
| LaTeX generation | Markdown fence variations (P1) | Regex-based fence removal from day 1 |
| LaTeX generation | LLM fabricating content (P3) | Entity validation pass after every generation |
| LaTeX security | `\input{}` injection (P5) | Command allowlist scan before compilation |
| One-page enforcement | Loop on failed compile (P2) | Fix sentinel value before building loop |
| One-page enforcement | Page count vs whitespace (P4) | Use `len(doc)` as primary signal |
| One-page enforcement | Expand vs trim direction (P6) | Two-mode loop: TRIM vs EXPAND |
| One-page enforcement | Threshold calibration (P15) | Calibrate empirically |
| Cover letter generation | Word count drift (P10) | Word count check + regenerate if out of range |
| Cover letter output | LibreOffice hangs (P11) | Direct subprocess with 30s timeout |
| Job tracking | Company name path traversal (P7) | Sanitize immediately after LLM extraction |
| Job tracking | JSON corruption (P14) | Pydantic model validation on load |
| Pipeline setup | Relative paths break (P12) | Absolute path resolution at module level |
