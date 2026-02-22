# Codebase Concerns

**Analysis Date:** 2026-02-21

## Tech Debt

**Hard-coded relative file paths:**
- Issue: Critical path resolution failures when running from different directories. Code uses relative paths like `"templates/job_description_schema.json"` instead of resolving relative to package root.
- Files: `src/llm.py` (lines 50, 208)
- Impact: Application fails with `FileNotFoundError` when invoked from any directory other than project root. Cover letter prompt and job description schema cannot be found.
- Fix approach: Use `os.path.dirname(__file__)` to resolve paths relative to module location, or use `os.path.abspath()` with proper path construction using `config.templates_path`.

**String replacement for file type conversion:**
- Issue: Naive string replacement to generate output filenames. Using `.replace(".tex", ".pdf")` and `.replace(".docx", ".pdf")` fails if company names contain these substrings.
- Files: `src/main.py` (lines 107, 134, 171), `src/cover_letter_generator.py` (line 48)
- Impact: If company name is "LaTex Corp" or "Tex-based Systems", resume file paths become corrupted (e.g., `LaPDF Corp_resume.PD` instead of correct path). Generated PDFs cannot be created.
- Fix approach: Use `os.path.splitext()` to safely replace only file extensions, or construct output paths explicitly using `os.path.join()` and filename variables.

**No timeout on external API calls:**
- Issue: `requests.post()` and `requests.get()` calls have no timeout parameter, can hang indefinitely if Ollama service is slow or unresponsive.
- Files: `src/llm.py` (line 28), `src/main.py` (line 37)
- Impact: User cannot interrupt the program without force-killing. Long-running optimization loops with no timeout create unbounded wait times, blocking other applications.
- Fix approach: Add explicit `timeout` parameter to all requests (e.g., `timeout=30`). Add configurable timeout in `config.yaml` for customization.

**Config file load timing issue:**
- Issue: `config.py` creates a module-level `Config()` instance which fails immediately if `config.yaml` is missing or invalid.
- Files: `src/config.py` (line 33), imported by `src/main.py` (line 12)
- Impact: Any import of modules using config (llm.py, logger.py, main.py) raises exception before user code can run. Cannot provide helpful error message about missing config to the user.
- Fix approach: Lazy-load config or wrap initialization in try/except at module level with helpful error message.

**No input validation on company name:**
- Issue: `company_name` extracted from LLM is used directly in `os.path.join()` to create output directory without sanitization.
- Files: `src/main.py` (lines 58-61, 79)
- Impact: LLM could return malicious input like `"../../etc/passwd"` or `"/tmp/evil"` causing directory creation outside intended location. Directory traversal vulnerability.
- Fix approach: Validate company name against whitelist of safe characters (alphanumeric, spaces, hyphens, underscores). Reject names with path separators or special characters.

## Known Bugs

**JSON parsing markdown formatting edge case:**
- Symptoms: If LLM returns JSON wrapped in ` ```json\n` (with newline) instead of `\`\`\`json`, string slicing fails. Off-by-one error in substring extraction.
- Files: `src/llm.py` (line 83)
- Trigger: Run with LLM that adds newline after opening fence: `\`\`\`json\n{...}\n\`\`\``
- Workaround: None - application silently returns empty dict and continues, losing job description data.

**LaTeX markdown formatting edge case:**
- Symptoms: Same issue as JSON parsing. If LLM returns ` ```latex\n` instead of `\`\`\`latex`, line 163 slice `llm_response.strip()[8:-4]` produces malformed LaTeX.
- Files: `src/llm.py` (line 163)
- Trigger: LLM adds newline after opening fence
- Workaround: None - malformed LaTeX fails PDF compilation with cryptic tectonic error messages.

**PDF analysis returns worst-case on error:**
- Symptoms: If PDF file is corrupted or cannot be opened, function returns hardcoded `100.0%` whitespace (worst case).
- Files: `src/pdf_analyzer.py` (lines 20-22)
- Trigger: Corrupted PDF file from LaTeX compilation failure
- Workaround: None - optimization loop interprets as "too much whitespace" and infinitely retries.

**Logger handlers accumulate on repeated imports:**
- Symptoms: `get_logger()` adds handlers every time called (though check at line 32 prevents duplication). If check fails, console and file logging duplicates.
- Files: `src/logger.py` (lines 32-34)
- Trigger: Concurrent imports of modules using logger
- Workaround: Check appears to prevent issue but is fragile.

## Security Considerations

**Local LLM API communication assumed secure:**
- Risk: Application communicates with Ollama on `http://localhost:11434` (HTTP, not HTTPS). If Ollama is exposed to network or compromised, all job descriptions and generated resumes can be intercepted.
- Files: `src/config.py` (line 11), `src/main.py` (line 37)
- Current mitigation: URL is hardcoded to localhost, preventing remote access. But no validation that URL is actually local.
- Recommendations: Add validation that ollama_url is localhost-only. Document that Ollama must not be exposed to untrusted networks. Consider adding HTTPS support if needed.

**Job description content passed to untrusted LLM:**
- Risk: Entire job description (potentially containing confidential info, company internal details, salary ranges) is sent to Ollama service. If service is compromised or logs are exposed, sensitive information leaks.
- Files: `src/llm.py` (lines 59-69)
- Current mitigation: LLM is local. No persistent logs of requests mentioned.
- Recommendations: Document that users should not include confidential information in job descriptions. Consider adding data masking or redaction options.

**No output sanitization for file saving:**
- Risk: LLM-generated LaTeX and cover letter content is saved directly to files without sanitization. Malicious LLM could inject system commands or file paths.
- Files: `src/main.py` (lines 100-101, 165), `src/cover_letter_generator.py` (lines 19-22)
- Current mitigation: None
- Recommendations: Validate LaTeX syntax before saving (prevent command injection). Sanitize DOCX content before saving. Add file permission checks.

**No authentication on Ollama endpoint:**
- Risk: Any local process can call the Ollama API. If Ollama is misconfigured, malicious local application could trigger expensive operations.
- Files: `src/llm.py` (lines 28-32)
- Current mitigation: Ollama is assumed to be trustworthy
- Recommendations: Document deployment security model. Recommend running Ollama in container with restricted access.

## Performance Bottlenecks

**Full PDF re-analysis on each iteration:**
- Problem: Entire PDF is re-analyzed for whitespace using `fitz.open()` and block-by-block text area calculation, even if only minor changes made.
- Files: `src/pdf_analyzer.py` (lines 7-43), called from `src/main.py` (line 141)
- Cause: No caching of PDF analysis results. Optimization loop (up to 3 iterations) re-analyzes the same PDFs multiple times.
- Improvement path: Cache PDF analysis results keyed by file hash. Reuse analysis if PDF hasn't changed since last analysis.

**Unbounded LLM prompt size:**
- Problem: Full resume template and job description JSON are included in every LLM request (lines 120-122 in llm.py). For large templates, this creates unnecessary token consumption.
- Files: `src/llm.py` (lines 111-125)
- Cause: No prompt optimization or summarization of large inputs
- Improvement path: Summarize job description to key requirements. Compress template to essential structure. Use template ID instead of full content if possible.

**Sequential resume generation in optimization loop:**
- Problem: Each optimization iteration generates, compiles, and analyzes PDF sequentially. Could be parallelized.
- Files: `src/main.py` (lines 114-151)
- Cause: Linear loop structure with no async/parallel execution
- Improvement path: Generate multiple resume variations in parallel, then select best one based on whitespace analysis.

**Synchronous LaTeX compilation:**
- Problem: `subprocess.run()` blocks until tectonic completes. Large documents can take 5-10 seconds per iteration.
- Files: `src/resume_generator.py` (line 55)
- Cause: Blocking subprocess call
- Improvement path: Use asyncio or thread pool for concurrent compilations across iterations.

## Fragile Areas

**PDF analysis whitespace calculation:**
- Files: `src/pdf_analyzer.py` (lines 24-43)
- Why fragile: Text block detection via `page.get_text("blocks")` is heuristic-based and may misidentify whitespace. Different PDF structures (two-column layouts, overlapping elements) produce incorrect results. Hard to test without comprehensive PDF corpus.
- Safe modification: Only modify block boundary calculations with PDF samples of known layout. Add unit tests with sample PDFs. Consider alternative detection methods (image-based analysis).
- Test coverage: No unit tests exist for this function.

**LaTeX string slicing for markdown fence removal:**
- Files: `src/llm.py` (lines 82-84, 162-163)
- Why fragile: Uses hardcoded slice indices `[7:-4]` and `[8:-4]` based on markdown fence length. Any variation in fence format (newlines, spaces) breaks parsing. Regex would be more robust.
- Safe modification: Replace with regex-based fence removal: `re.sub(r'^```\w+\n?|\n?```$', '', text)`. Add test cases for fence variations.
- Test coverage: No unit tests for JSON/LaTeX parsing.

**Company name extraction and path creation:**
- Files: `src/main.py` (lines 58-61, 79)
- Why fragile: No validation of company name format before using in path. LLM output varies widely. Path creation can fail silently if `os.makedirs()` encounters permission errors.
- Safe modification: Add explicit company name validation (whitelist characters). Check `os.makedirs()` return code and log failures explicitly.
- Test coverage: No unit tests for company name extraction/validation.

**Configuration property access:**
- Files: `src/config.py` (lines 9-31)
- Why fragile: No checks for missing keys in config YAML. If config is incomplete, accessing `config.model_id` raises `KeyError` with cryptic message about missing key, not about missing config section.
- Safe modification: Add try/except around YAML access with custom error messages. Validate all required keys exist at Config initialization.
- Test coverage: No validation of config schema. No tests for missing keys.

**Cover letter PDF conversion dependency:**
- Files: `src/cover_letter_generator.py` (lines 27-61)
- Why fragile: Requires LibreOffice or Word to be installed. Error messages don't distinguish between missing tool and conversion failure. `convert()` function can hang indefinitely on large documents.
- Safe modification: Check for LibreOffice/Word availability at startup (similar to `check_dependencies()`). Add timeout to conversion. Provide clearer error messages.
- Test coverage: No tests for docx2pdf conversion.

## Scaling Limits

**No limit on LLM API calls:**
- Current capacity: Each run makes 3-4 API calls (company name, JD parsing, resume generation, cover letter). Optimization loop multiplies by `max_optimization_iterations` (default 3).
- Limit: Total up to 16+ API calls per run. If Ollama instance handles 10 requests/second, 4 parallel runs would exceed capacity. No request queuing or rate limiting.
- Scaling path: Implement request queue with configurable rate limit. Add cost/token tracking. Consider batch processing. Implement caching of previous extractions.

**Output directory per company:**
- Current capacity: Each company gets its own directory in `data/`. With no cleanup, directories accumulate indefinitely.
- Limit: Filesystem limits (typically millions of files per partition). If 100 companies run 3 iterations each, creates 300+ directories.
- Scaling path: Implement archive/cleanup of old runs. Add configurable retention policy. Use database instead of filesystem for metadata.

**PDF memory usage in whitespace analysis:**
- Current capacity: `fitz.open()` loads entire PDF into memory. PDFs up to 100MB can be handled on typical systems.
- Limit: Large resumes with embedded images could exceed available memory. No streaming PDF analysis available.
- Scaling path: Use streaming PDF analysis or page-by-page processing. Implement memory limits with fallback to alternative analysis methods.

## Dependencies at Risk

**Ollama service availability:**
- Risk: Entire application is blocked if Ollama crashes or stops responding. No fallback or alternative LLM available.
- Impact: Cannot generate resumes or cover letters without Ollama. Application fails completely.
- Migration plan: Consider supporting multiple LLM backends (OpenAI API, Anthropic, Hugging Face). Implement LLM abstraction layer to switch providers.

**Python-docx library limitations:**
- Risk: `python-docx` has limited formatting capabilities. Complex cover letter designs may not be supported.
- Impact: Cover letters may lose formatting when generated (no colors, limited fonts, no tables). DOCX to PDF conversion via LibreOffice/Word adds platform dependencies.
- Migration plan: Consider using REPORTLAB or native PDF generation for cover letters. Reduce dependency on DOCX format.

**PyMuPDF (fitz) security concerns:**
- Risk: fitz is known to have had security vulnerabilities in PDF parsing. No automatic security updates mechanism.
- Impact: Malicious PDF input could cause crashes or memory corruption.
- Migration plan: Consider migration to pdf.js or pypdf library with more active security patches. Validate PDFs before opening.

**LaTeX compilation via tectonic:**
- Risk: tectonic is a Rust tool with small community. Limited support compared to TeX Live.
- Impact: Complex LaTeX features may not work. Tectonic updates could break compatibility.
- Migration plan: Consider supporting multiple LaTeX engines (pdflatex, xelatex). Validate LaTeX output before compilation.

## Missing Critical Features

**No error recovery or retry logic:**
- Problem: Any single failure (Ollama timeout, LaTeX compilation error, PDF conversion failure) stops entire pipeline. No automatic retry or partial success handling.
- Blocks: Cannot resume interrupted runs. User must restart from beginning.
- Impact: Large job descriptions with many pages timeout on first run, requiring manual retry multiple times.

**No result validation before saving:**
- Problem: Generated LaTeX and cover letter content is not validated before being saved to disk.
- Blocks: Corrupted resumes are saved without warning. Users may submit invalid documents.
- Impact: PDF compilation errors are only discovered after file is saved. Need to manually delete broken files.

**No progress reporting for long operations:**
- Problem: Optimization loop (up to 3 iterations × multiple compilations) can take 2-5 minutes with no progress indication.
- Blocks: User cannot estimate time remaining. No ability to cancel specific iterations.
- Impact: Appears frozen. Users may force-kill process thinking it's hung.

**No configuration for LLM model selection:**
- Problem: Model is hardcoded to `"llama3.1:8b"` in config.yaml. No way to switch models without editing config file.
- Blocks: Cannot experiment with better models. Cannot use smaller model for faster iteration.
- Impact: Suboptimal model selection forced on all users.

**No support for updating existing resume:**
- Problem: Each company requires a new resume from scratch. Cannot incrementally improve tailoring.
- Blocks: Cannot refine previous attempts. No history of what was changed.
- Impact: Manual editing required to reuse good content across variants.

## Test Coverage Gaps

**No unit tests:**
- What's not tested: LLM response parsing, file I/O, path resolution, company name extraction, PDF analysis
- Files: All files in `src/` directory
- Risk: Regressions in string parsing (markdown fences, file extensions) go undetected. Config loading failures are discovered at runtime only.
- Priority: High - Core functions like JSON parsing and LaTeX generation have complex logic with no test coverage.

**No integration tests:**
- What's not tested: Full pipeline from job description to final PDF. Config file loading. Dependency availability checks.
- Files: `src/main.py` and all modules it imports
- Risk: Breaking changes in dependency APIs are not caught. Config validation failures are only discovered when user runs application.
- Priority: High - End-to-end pipeline is untested.

**No edge case coverage:**
- What's not tested: Empty responses from LLM, malformed JSON from LLM, company names with special characters, missing template files, corrupted PDF files
- Files: All modules
- Risk: Edge cases cause silent failures or cryptic errors. Poor error messages make debugging difficult.
- Priority: Medium - Most likely to occur in production use.

**No performance tests:**
- What's not tested: PDF analysis speed with large documents, LLM response time, compilation time
- Files: `src/pdf_analyzer.py`, `src/llm.py`, `src/resume_generator.py`
- Risk: Performance regressions go unnoticed. Optimization loop could take hours on large resumes.
- Priority: Low - Performance issues are observable but not critical.

---

*Concerns audit: 2026-02-21*
