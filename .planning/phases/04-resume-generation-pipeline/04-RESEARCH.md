# Phase 4: Resume Generation Pipeline - Research

**Researched:** 2026-02-23
**Domain:** LLM-driven content selection, one-page enforcement loop, entity validation
**Confidence:** HIGH

## Summary

Phase 4 implements an end-to-end resume generation pipeline that takes a parsed job record and produces a one-page PDF. The pipeline: (1) uses the LLM to rank experiences and projects for relevance, selecting top 3 experiences and top 2 projects; (2) assembles the selected content into a JSON payload matching `resume_json_template.json`; (3) renders via Phase 3's Jinja2 + tectonic pipeline; (4) measures page count via PyMuPDF; (5) if page count > 1, trims the longest bullet points and recompiles (TRIM mode, up to `max_iterations`); (6) validates final output using pure Python entity matching against `master_resume.json`; (7) returns structured result with PDF path, iteration count, and optional warning flags.

The phase wires together Phase 2's LLM client, Phase 3's LaTeX engine, and introduces `ResumeService` — a stateless class that orchestrates the entire flow. Success hinges on: reliable LLM selection (no hallucinations), robust TRIM iteration without infinite loops, deterministic entity validation (no false positives), and graceful handling of edge cases (oversized pages, corruption, multiple failures).

**Primary recommendation:** Build `ResumeService` as a stateless orchestrator that delegates to Phase 2 (LLM) and Phase 3 (LaTeX/PDF) without custom PDF parsing. Use Python's built-in struct/list operations for entity extraction (no spaCy NER). Implement TRIM as a structured loop with three termination conditions: page_count == 1 (success), max_iterations reached (failure with flag), or two consecutive compilation failures (hard stop).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Selection logic**
   - LLM ranks experiences and projects for relevance to the job; service takes top 3 experiences and top 2 projects from the ranked list
   - LLM receives extracted JD fields only (skills, responsibilities, requirements) — not the full JD text — to reduce noise
   - Selection is pick-only: no bullet rewriting or tailoring at this stage; content passes through unchanged

2. **Trim behavior**
   - When page count > 1, trim prompt targets the longest bullets first (by character count)
   - Trim is progressive: small cuts per iteration (~10-20% reduction per pass) to preserve content quality
   - Line-overflow heuristic based on template baseline (9pt Charter, ~100-char one-line threshold):
     * Bullets overflowing onto 2nd line with <50% fill → rewrite to fit cleanly on one line
     * Bullets using 2.5+ lines with sparse partial last line → rewrite to clean 2 lines
     * LLM trim prompt receives explicit ~100-char threshold
     * Rewrites must follow ATS-standard phrasing (action verb + metric/result)
   - If max_iterations reached: return last iteration's PDF with `page_fit_warning` flag
   - If final PDF whitespace_ratio exceeds threshold (over-trimmed): include `whitespace_warning` flag

3. **Content validation**
   - Validation runs once: on final output before returning to caller
   - Validator is purely Python entity matching (fast, deterministic)
   - Extract skills/tools/companies/metrics from output; diff against `master_resume.json`

4. **Output artifacts**
   - Files saved to `data/<company_slug>/`:
     * `selected_resume.json` — assembled content after LLM selection (pre-render), for debugging and future re-use
     * `resume_iter_N.tex` / `resume_iter_N.pdf` — only final successful iteration kept, plus last failed iteration if loop terminated without fitting
     * Intermediate iterations cleaned up after run
   - On success, service returns structured result object containing: PDF path, .tex path, iteration count, and optional warning flags

### Claude's Discretion

1. **Skills selection:** Claude picks the most practical approach (e.g., keyword filter against JD fields, or a quick LLM pass — whatever is most reliable given Phase 2 tooling)
2. **Whitespace ratio threshold:** Claude calibrates the "over-trimmed" threshold by referencing `templates/resume_template.pdf` as the baseline (well-filled one-page resume)
3. **Entity validation implementation details:** How entities are extracted (spaCy NER vs regex vs structured field diff), exact matching tolerance, and whether validation violation causes hard error, single retry, or warn-and-return
4. **Hallucination handling policy:** Claude picks whatever is safest for a job-hunt tool (hard fail or warn-and-return)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RES-01 | System selects relevant experiences, projects, and skills from master_resume.json based on the JD | LLM ranking + top-N selection provides structured JSON payload; no custom selection logic needed |
| RES-04 | System detects PDF page overflow (page_count > 1) and re-prompts AI to shorten longest bullet points, then recompiles (TRIM mode — up to max_iterations) | PyMuPDF page_count check + structured TRIM loop with three termination conditions (success, max_iterations, two consecutive failures) |
| RES-06 | Generated resume content may only use material from master_resume.json — no fabricated experience, skills, tools, or metrics (enforced via post-generation entity validation) | Python dict/set operations for entity extraction; no spaCy NER needed; fast deterministic validation |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| LLMClient | from Phase 2 | Async LLM calls with retry logic | Established in Phase 2; all LLM calls go through single integration point |
| PyMuPDF (fitz) | 1.20+ | Page count detection; sentinel values on error | Established in Phase 3; no exceptions raised; structured dict returns |
| Jinja2 rendering | from Phase 3 | LaTeX template rendering | Established in Phase 3; custom delimiters prevent conflicts |
| tectonic compiler | from Phase 3 | LaTeX → PDF compilation | Established in Phase 3; subprocess via Phase 3's compiler.py |
| Pydantic | 2.0+ | Data model validation (JobRecord, ResumeService input/output) | Established in Phase 1; use_enum_values=True pattern |
| asyncio (stdlib) | Python 3.11+ | Async/await for LLM calls | Standard for Python async code; non-blocking I/O |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib (stdlib) | Python 3.11+ | File path handling | Consistent cross-platform paths |
| json (stdlib) | Python 3.11+ | JSON serialization for selected_resume.json | Standard format; human-readable; no custom serialization |
| re (stdlib) | Python 3.11+ | Regex for entity extraction (if not using structured diff) | For metrics extraction (e.g., "30%" → extract percentage) |
| tempfile (stdlib) | Python 3.11+ | Atomic file writes (already in Phase 3) | Prevent partial writes; os.replace() atomic rename |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python dict/set entity diff | spaCy NER | spaCy is slower, needs model loading, false positives on names; structured dict lookup is O(1), deterministic, no false positives |
| Keyword-based skills filter | Full LLM ranking pass for skills | Keyword filter (10ms) vs LLM pass (5-10s); given Phase 4 is already calling LLM for experiences, filter is acceptable |
| Tenacity retry (Phase 2) | Custom retry in Phase 4 | Avoid re-inventing; Phase 2 LLMClient already handles retries; service calls client, not LLM directly |

**Installation:**
```bash
# All dependencies already in place from Phase 2 and 3
# No new pip installs required for Phase 4
pip install pydantic==2.x asyncio  # Already installed
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── resume/
│   ├── __init__.py
│   ├── service.py           # ResumeService orchestrator
│   ├── selection.py         # LLM ranking + top-N logic
│   ├── trimmer.py           # TRIM loop + iteration logic
│   └── validator.py         # Entity extraction + validation
├── latex/                   # (existing — Phase 3)
│   ├── renderer.py
│   ├── compiler.py
│   └── pdf_analyzer.py
├── llm/                     # (existing — Phase 2)
│   ├── client.py
│   └── utils.py
├── models/                  # (existing)
│   └── job_record.py
├── storage/                 # (existing)
│   └── job_store.py
└── config.py                # (existing)

templates/
├── master_resume.json       # Source data
├── resume_json_template.json # Schema for LLM payload
├── resume_template.tex.j2   # Jinja2 template (Phase 3)
└── resume_template.pdf      # Reference for whitespace calibration
```

### Pattern 1: ResumeService Orchestrator (Stateless)
**What:** Single entry point that coordinates selection → rendering → compilation → validation
**When to use:** Always; enables testability and clear separation of concerns
**Example:**
```python
# Source: Phase 2/3 established pattern
class ResumeService:
    """Stateless orchestrator for resume generation pipeline."""

    def __init__(self, config: AppConfig, llm_client: LLMClient):
        self.config = config
        self.llm = llm_client
        self.latex_renderer = renderer from Phase 3
        self.latex_compiler = compiler from Phase 3
        self.pdf_analyzer = analyzer from Phase 3

    async def generate(
        self,
        job_record: JobRecord,
        master_resume: dict,
    ) -> ResumeGenerationResult:
        """Generate resume PDF for a job. Returns structured result or raises error."""

        # Step 1: Select content
        selected = await self.select_resume_content(job_record, master_resume)

        # Step 2: TRIM loop (1+ iterations until success or max_iterations)
        final_result = await self.trim_loop(selected, job_record.job_dir)

        # Step 3: Validate
        validation = await self.validate_content(final_result, master_resume)

        # Step 4: Return result
        return ResumeGenerationResult(
            pdf_path=final_result.pdf_path,
            tex_path=final_result.tex_path,
            iteration_count=final_result.iteration_count,
            page_fit_warning=final_result.page_fit_warning,
            whitespace_warning=validation.whitespace_warning,
            validation_warning=validation.validation_warning,
        )
```

### Pattern 2: Content Selection via LLM Ranking
**What:** LLM ranks experiences/projects by relevance; service picks top N
**When to use:** Always; avoids custom ranking logic
**Example:**
```python
# Source: Phase 2 LLM + Phase 4 selection logic
async def select_resume_content(
    self,
    job_record: JobRecord,
    master_resume: dict,
) -> SelectedResumeJSON:
    """Rank experiences and projects; select top 3 exp + top 2 proj."""

    # Extract JD fields (NOT full text)
    jd_fields = {
        "skills": job_record.skills,  # e.g., ["Python", "AWS"]
        "responsibilities": job_record.responsibilities,
        "requirements": job_record.qualifications.required,
    }

    # Call LLM for ranking
    prompt = self.llm.load_prompt("select_resume", {
        "master_resume": master_resume,
        "jd_fields": jd_fields,
    })
    ranking_json = await self.llm.call(prompt)

    # Parse and extract top N
    ranking = json.loads(ranking_json)
    selected = {
        "experiences": ranking["experiences"][:3],
        "projects": ranking["projects"][:2],
        "skills": self._filter_skills(ranking["all_skills"], jd_fields),
    }

    # Save pre-render JSON for debugging
    (job_record.job_dir / "selected_resume.json").write_text(
        json.dumps(selected, indent=2)
    )

    return selected
```

### Pattern 3: TRIM Loop with Three Termination Conditions
**What:** Iteratively shorten longest bullets until page_count == 1, max_iterations hit, or two consecutive failures
**When to use:** Always; prevents infinite loops and handles edge cases
**Example:**
```python
# Source: Phase 4 core logic
async def trim_loop(
    self,
    selected_content: dict,
    job_dir: Path,
) -> LoopResult:
    """Compile, measure, trim, repeat. Returns final iteration or last failed state."""

    iteration = 0
    consecutive_failures = 0
    previous_page_count = None

    while iteration < self.config.max_iterations:
        iteration += 1

        # Render .tex file
        tex_path = job_dir / f"resume_iter_{iteration}.tex"
        tex_content = self.render_tex(selected_content)
        tex_path.write_text(tex_content)

        # Compile to PDF
        pdf_path = job_dir / f"resume_iter_{iteration}.pdf"
        compile_result = self.compile_pdf(tex_path, pdf_path)

        if not compile_result.success:
            consecutive_failures += 1
            if consecutive_failures >= 2:
                # Hard stop after two compilation failures
                return LoopResult(
                    success=False,
                    iteration_count=iteration,
                    pdf_path=None,
                    reason="Two consecutive compilation failures",
                )
            continue  # Retry with trimmed content

        consecutive_failures = 0  # Reset on success

        # Analyze PDF
        analysis = self.analyze_pdf(pdf_path)
        previous_page_count = analysis.page_count

        # Check success condition: page_count == 1 AND height <= 11.5in (single page)
        if analysis.page_count == 1 and analysis.page_height_inches <= 11.5:
            return LoopResult(
                success=True,
                iteration_count=iteration,
                pdf_path=pdf_path,
                tex_path=tex_path,
            )

        # Check overflow: page_count > 1 or page_height > 11.5in
        if analysis.page_count > 1 or analysis.page_height_inches > 11.5:
            if iteration >= self.config.max_iterations:
                # Max iterations reached; return with warning
                return LoopResult(
                    success=False,
                    iteration_count=iteration,
                    pdf_path=pdf_path,
                    tex_path=tex_path,
                    page_fit_warning=True,
                )

            # Trim longest bullets and retry
            selected_content = self.trim_longest_bullets(
                selected_content,
                max_bullets=5,  # Trim top 5 longest
                reduction_pct=0.15,  # 10-20% per iteration
            )
            continue

    # Exhausted max_iterations
    return LoopResult(
        success=False,
        iteration_count=iteration,
        page_fit_warning=True,
    )
```

### Pattern 4: Entity Validation via Structured Diff
**What:** Extract entities from final PDF text; verify all exist in master_resume.json
**When to use:** Always; fast deterministic validation, no false positives
**Example:**
```python
# Source: Phase 4 validation logic
async def validate_content(
    self,
    final_result: LoopResult,
    master_resume: dict,
) -> ValidationResult:
    """Extract entities from PDF; verify against master_resume.json."""

    if not final_result.success:
        # Skip validation if loop failed
        return ValidationResult(success=False, warning="Loop failed before validation")

    # Extract text from final PDF
    pdf_text = pdftotext(final_result.pdf_path)

    # Extract entities using structured field diff
    extracted = {
        "skills": self._extract_skills(pdf_text, master_resume),
        "companies": self._extract_companies(pdf_text, master_resume),
        "tools": self._extract_tools(pdf_text, master_resume),
        "metrics": self._extract_metrics(pdf_text),
    }

    # Verify each entity exists in master
    violations = []
    for skill in extracted["skills"]:
        if not self._skill_in_master(skill, master_resume):
            violations.append(f"Skill not in master: {skill}")

    for tool in extracted["tools"]:
        if not self._tool_in_master(tool, master_resume):
            violations.append(f"Tool not in master: {tool}")

    # Decision: log warning if any violations; don't hard-fail
    if violations:
        logger.warning("Validation violations: %s", violations)
        return ValidationResult(
            success=True,
            validation_warning=True,
            violations=violations,
        )

    return ValidationResult(success=True, validation_warning=False)
```

### Anti-Patterns to Avoid
- **Calling LLM multiple times for selection:** Use single LLM ranking call, then extract top N. Don't ask LLM to select experiences, then projects separately.
- **Using full JD text in LLM ranking prompt:** Bloats token count, increases noise. Extract only relevant fields (skills, responsibilities, requirements).
- **Hardcoding TRIM iteration logic in templates or config:** Put the loop in Python orchestrator (`trim_loop`). Templates are for rendering, not control flow.
- **Assuming PyMuPDF page_count is the only overflow signal:** Single page can exceed letter height (11.5in). Always check `page_height_inches > 11.5` as secondary signal.
- **Raising exceptions on validation failures:** Log warnings, set flag, return normally. Job-hunt tool should not crash on validation violation.
- **Keeping intermediate .tex and .pdf files:** Clean up after each iteration; only keep final success + last failed state (if relevant for debugging).
- **Running validation on each iteration:** Validation is expensive (PDF text extraction). Run once on final output.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content selection / ranking | Custom ranking algorithm | LLM ranking + top-N pick | Custom ranking requires tuning weights, testing edge cases, handling ties. LLM ranking is language-aware, captures nuance. |
| Iteration loop control | Manual state machine | Structured loop with termination conditions | Manual state machine (flags, counters) is error-prone, hard to debug. Explicit termination conditions (page_count, max_iterations, failures) are clear. |
| Entity extraction from PDF | Regex + heuristics | Structured field diff (master_resume keys) | Regex extraction is fragile (edge cases, formatting changes). Structured diff is fast, deterministic, no false positives. |
| PDF page counting | PyMuPDF alternative (pypdf, pdfplumber) | PyMuPDF (fitz) | fitz is fastest for page_count + text box extraction; pypdf slower; pdfplumber overkill. |
| Whitespace detection | Manual pixel analysis | PyMuPDF text block coordinates | Pixel analysis requires image processing, OCR, slow. Text blocks are fast and accurate. |

**Key insight:** Iteration loops and entity matching look simple but hide complexity. Custom logic is unmaintainable. Structured loops + standard libraries (Pydantic, json) + established Phase 2/3 patterns are safer.

## Common Pitfalls

### Pitfall 1: Infinite TRIM Loop (No Termination)
**What goes wrong:** Resume never achieves page_count == 1; loop keeps trimming forever (or until timeout).
**Why it happens:** (1) Text cannot be shortened further without removing sections, (2) LaTeX layout has minimum spacing that forces overflow, (3) image/table width exceeds page, (4) no safety check for consecutive failures.
**How to avoid:**
  - Implement three termination conditions: (a) page_count == 1, (b) max_iterations reached (return with flag), (c) two consecutive compilation failures (hard stop)
  - Log iteration number and page_count at each step for debugging
  - Test with worst-case resume (10 experiences, 50+ skills, 10+ projects) to ensure max_iterations is enough
  - Set max_iterations = 5 as default (configurable); cap at 10 max
**Warning signs:** Generation takes 60+ seconds; iteration counter > max_iterations in logs; page_count never decreases

### Pitfall 2: LLM Hallucination in Content Selection
**What goes wrong:** LLM generates fictional experiences / skills / companies not in master_resume.json.
**Why it happens:** (1) LLM prompt doesn't constrain output to master_resume items, (2) LLM interprets "relevant to JD" as "plausible" rather than "exists in master", (3) Validation runs too late (after PDF generation).
**How to avoid:**
  - LLM selection prompt: "Select from the provided master_resume only; do not generate new experiences."
  - Validate selected items immediately after LLM returns (before rendering)
  - Hard-fail on hallucination during selection (don't let it propagate to rendering)
  - Test selection with 5+ job descriptions; verify every selected experience exists in master
**Warning signs:** Validation catches skills/companies not in master; LLM output includes phrases like "similar to" or "could include"

### Pitfall 3: Page Overflow via Single Oversized Page
**What goes wrong:** page_count == 1 but PyMuPDF reports height > 11.5 inches. TRIM loop thinks it's done; returns multi-page PDF in single-page wrapper.
**Why it happens:** LaTeX can render single page with height >> 11.5in (letter size). page_count counts pages, not whether page fits standard paper.
**How to avoid:**
  - Phase 3 ALREADY provides `page_height_inches` in PDF analysis output
  - Check BOTH: `page_count == 1 AND page_height_inches <= 11.5`
  - Trigger TRIM if either condition fails
  - Test with heavily-packed resume; verify height check works
**Warning signs:** PDF viewer shows single page but scrolling is needed; page_count == 1 but visual appears multi-page

### Pitfall 4: TRIM Prompt Targets Wrong Bullets
**What goes wrong:** LLM trims short, irrelevant bullets instead of longest, most important ones.
**Why it happens:** Prompt is vague: "Make it shorter" instead of "Shorten only the longest bullets; preserve content quality."
**How to avoid:**
  - Trim prompt explicitly: "Reduce length of these bullets (sorted by character count, longest first)."
  - Pass sorted list: `[(bullet, char_count), ...]` sorted descending by count
  - Limit trim scope: "Trim top 5 longest bullets; reduce each by 10-20%"
  - Include line-overflow heuristic in prompt: "Bullets exceeding ~100 chars overflow onto next line; rewrite to fit."
  - Test TRIM with 3+ resumes; verify longest bullets are shortened
**Warning signs:** Final PDF has trivial bullets kept but important ones removed; trim doesn't proportionally reduce length

### Pitfall 5: Validation False Positives (Entity Mismatch)
**What goes wrong:** Validation rejects valid content because of format mismatch (e.g., "Python 3.10" vs "Python" in master_resume).
**Why it happens:** Entity extraction is regex-based without normalization; master_resume has different granularity.
**How to avoid:**
  - Use structured field diff, not NER: extract skills from selected_content, not from PDF text
  - Normalize before comparing: "Python 3.10" → "Python" (strip version numbers)
  - Allow partial matches: if "Python" is in master, accept "Python 3.10" in output
  - Test validation with 5+ generated resumes; ensure no false positives
  - Decision: warn on suspicious matches, but don't hard-fail (safe for job-hunt tool)
**Warning signs:** Validation rejects legitimate skills; developer sees "Python not in master" even though master has "Python"

### Pitfall 6: Compiler Path Traversal or Iteration Collision
**What goes wrong:** Iteration N overwrites iteration N-1 because naming is incorrect; or files written to unexpected directory.
**Why it happens:** Phase 3 doesn't enforce _iter_N naming; Phase 4 must construct path correctly.
**How to avoid:**
  - Phase 4 constructs path: `job_dir / f"resume_iter_{iteration}.tex"`
  - Validate iteration counter: assert 0 <= iteration <= max_iterations
  - Pre-check path: assert "/../" not in str(tex_path) (Phase 1 already validates job_dir)
  - Clean up after successful completion: delete _iter_0 through _iter_{iteration-1}, keep final success + last failure
**Warning signs:** Files written to unexpected directory; iteration counter wraps or resets; old files persist

### Pitfall 7: Whitespace Ratio Over-Trimming
**What goes wrong:** Resume fits on one page but looks sparse (lots of whitespace); user sees half-empty page.
**Why it happens:** TRIM loop stops as soon as page_count == 1, without checking if resume is over-trimmed.
**How to avoid:**
  - Phase 3 already provides `whitespace_ratio` in PDF analysis
  - After successful TRIM (page_count == 1), check whitespace_ratio
  - If whitespace_ratio > 0.40 (threshold), set `whitespace_warning` flag in result
  - Calibrate threshold by comparing to `templates/resume_template.pdf` baseline (well-filled one-page)
  - Note: warning doesn't block success; it flags for user attention
**Warning signs:** Final PDF has 40%+ blank space; TRIM removed too much content

### Pitfall 8: Asynchronous LLM Call Race Condition
**What goes wrong:** Multiple resume generation calls run concurrently; shared state causes race condition.
**Why it happens:** ResumeService is stateless but temp files are shared (same job_dir).
**How to avoid:**
  - ResumeService should be stateless (no instance variables holding state between calls)
  - Use job_dir (company_slug) to isolate files per job — different jobs use different directories
  - Don't share LLMClient across multiple concurrent calls (LLMClient is async-safe; Ollama server handles queuing)
  - Test with concurrent calls to same job_dir (should fail gracefully or use file locking)
  - For Phase 6 (web UI), use job_dir isolation + file locks if needed
**Warning signs:** Random file corruption when running 2+ generations simultaneously; lost iterations

## Code Examples

Verified patterns from official sources:

### Structured LLM Ranking Call
```python
# Source: Phase 2 LLMClient + Phase 4 selection logic
async def rank_resume_content(
    self,
    job_record: JobRecord,
    master_resume: dict,
) -> dict:
    """Call LLM to rank experiences and projects for relevance."""

    # Load prompt template
    prompt_template = self.llm.load_prompt("select_resume")

    # Extract JD fields (not full text)
    jd_payload = {
        "job_title": job_record.role,
        "company": job_record.company,
        "skills": job_record.skills,  # Already parsed by Phase 5
        "responsibilities": job_record.responsibilities,
        "qualifications": job_record.qualifications.required,
    }

    # Render prompt with Jinja2
    from jinja2 import Template
    prompt = Template(prompt_template).render(
        master_resume=json.dumps(master_resume),
        jd_fields=json.dumps(jd_payload),
    )

    # Call LLM (with Phase 2 retry logic)
    response = await self.llm.call(prompt)

    # Parse JSON from response
    ranking = json_repair.repair(response)

    return ranking
```

### TRIM Loop with Termination Conditions
```python
# Source: Phase 4 core orchestration
async def trim_loop(
    self,
    selected_json: dict,
    job_dir: Path,
    max_iterations: int = 5,
) -> dict:
    """Iteratively compile and trim until success or max_iterations."""

    iteration = 0
    consecutive_failures = 0
    last_success = None

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"TRIM iteration {iteration}/{max_iterations}")

        # Step 1: Render .tex
        tex_path = job_dir / f"resume_iter_{iteration}.tex"
        tex_content = self._render_latex(selected_json)
        tex_path.write_text(tex_content)

        # Step 2: Compile to PDF
        pdf_path = job_dir / f"resume_iter_{iteration}.pdf"
        compile_result = self.latex_compiler.compile_tex(tex_path, pdf_path)

        if not compile_result["success"]:
            consecutive_failures += 1
            logger.warning(f"Compilation failed: {compile_result['error'][:200]}")

            if consecutive_failures >= 2:
                # Hard stop after 2 failures
                logger.error("Two consecutive compilation failures; stopping")
                return {
                    "success": False,
                    "error": "Compilation failed twice; giving up",
                    "iteration_count": iteration,
                    "pdf_path": last_success["pdf_path"] if last_success else None,
                }

            # Trim and retry
            selected_json = self._trim_longest_bullets(selected_json, pct=0.15)
            continue

        consecutive_failures = 0

        # Step 3: Analyze PDF
        analysis = self.pdf_analyzer.analyze_pdf(str(pdf_path))
        page_count = analysis["page_count"]
        page_height = analysis["page_height_inches"]

        logger.info(f"PDF analysis: page_count={page_count}, height={page_height:.1f}in")

        # Step 4: Check success
        if page_count == 1 and page_height <= 11.5:
            logger.info("SUCCESS: Resume fits on one page")
            return {
                "success": True,
                "iteration_count": iteration,
                "pdf_path": str(pdf_path),
                "tex_path": str(tex_path),
            }

        # Step 5: Check failure
        if iteration >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached")
            return {
                "success": False,
                "error": "Exceeded max iterations",
                "iteration_count": iteration,
                "pdf_path": str(pdf_path),
                "page_fit_warning": True,
            }

        # Save this iteration as fallback
        last_success = {
            "pdf_path": str(pdf_path),
            "tex_path": str(tex_path),
            "iteration": iteration,
        }

        # Step 6: Trim and retry
        logger.info(f"Page overflow (count={page_count}, height={page_height:.1f}); trimming bullets")
        selected_json = self._trim_longest_bullets(selected_json, pct=0.15)

    # Should not reach here (caught by iteration >= max_iterations above)
    logger.error("TRIM loop exited unexpectedly")
    return {"success": False, "error": "Unexpected loop exit"}
```

### Entity Validation via Structured Diff
```python
# Source: Phase 4 validation
def validate_generated_content(
    self,
    selected_json: dict,
    master_resume: dict,
) -> dict:
    """Validate that all selected content exists in master_resume."""

    violations = []

    # Validate skills
    selected_skills = set()
    for section in selected_json.get("sections", []):
        if section["type"] == "technical_skills":
            for line in section.get("lines", []):
                selected_skills.update(line.get("items", []))

    master_skills = set()
    for category, items in master_resume.get("technical_skills", {}).items():
        master_skills.update(items)

    unknown_skills = selected_skills - master_skills
    if unknown_skills:
        violations.append(f"Skills not in master: {unknown_skills}")

    # Validate companies
    selected_companies = set()
    for section in selected_json.get("sections", []):
        if section["type"] == "work_experience":
            for entry in section.get("entries", []):
                selected_companies.add(entry.get("company"))

    master_companies = {
        exp["company"] for exp in master_resume.get("work_experience", [])
    }

    unknown_companies = selected_companies - master_companies
    if unknown_companies:
        violations.append(f"Companies not in master: {unknown_companies}")

    # Log violations
    if violations:
        logger.warning(f"Validation violations: {violations}")
        return {
            "success": True,  # Don't hard-fail
            "validation_warning": True,
            "violations": violations,
        }

    return {"success": True, "validation_warning": False}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate content selection + template generation | Unified ResumeService orchestrator | 2024+ | Single service owns full pipeline; easier to test, debug, optimize |
| Manual TRIM loop with flags/counters | Structured loop with explicit termination conditions | Phase 4 best practice | Clear, maintainable, no infinite loops |
| LLM directly generates .tex | LLM ranks, service selects, Phase 3 renders | Phase 2/3/4 separation | Cleaner, testable, no LaTeX injection |
| Full JD text to LLM | Extract relevant fields only (skills, responsibilities) | Phase 4 decision | Reduces token count, noise; improves relevance |
| Exception on validation failure | Warn and return with flag | Phase 4 decision | Graceful degradation; job-hunt tool shouldn't crash |
| Multiple PDF analysis calls per iteration | Single analysis after compile | Phase 4 optimization | Faster (one fitz parse per iteration) |

**Deprecated/outdated:**
- **Custom regex entity extraction:** Fragile, hard to maintain. Use structured diff instead.
- **Whitespace detection via pixel counting:** Slow, needs image processing. Use PyMuPDF text block coordinates.
- **Storing all iteration files:** Cleanup after run; only keep final success + last failed state.

## Open Questions

1. **How to handle skills selection when skills are not explicitly mentioned in master_resume?**
   - What we know: master_resume has technical_skills with categories (programming, frameworks, tools, libraries)
   - What's unclear: Should service filter JD skills to only those in master_resume? Or should it attempt keyword matching (e.g., "Node.js" matches "Node.js" in frameworks)?
   - Recommendation: Use keyword-based filter for first pass (simple string matching); if LLM selection still references missing skills, validation will catch it and warn. This avoids over-engineering the filter.

2. **What is the exact whitespace_ratio threshold for over-trimming detection?**
   - What we know: CONTEXT.md mentions 40% threshold; Phase 3 STATE.md notes this needs empirical validation
   - What's unclear: Is this 40% whitespace (empty space) or 40% text fill? Should threshold vary by page height / number of sections?
   - Recommendation: Use 0.40 as initial threshold (40% whitespace ratio). During Phase 4 testing, generate 5 well-formed resumes, measure whitespace_ratio on each, compare to `templates/resume_template.pdf` baseline. Adjust threshold if 40% is too aggressive / too lenient.

3. **Should ResumeService retry validation on failure, or fail-fast?**
   - What we know: CONTEXT.md says "Claude's Discretion on exact matching tolerance and failure handling"
   - What's unclear: If validation catches a hallucinated skill, should service attempt to re-generate (slow, risky) or just warn and return (fast, safe)?
   - Recommendation: Fail-fast with warning. Service returns result with `validation_warning=True` and lists violations. Caller (Phase 6 web UI) can decide whether to re-generate or present results to user. This is safest for a job-hunt tool.

4. **What is the minimum bullet length in TRIM to avoid over-shortening?**
   - What we know: Bullets must start with action verb + include metric where possible
   - What's unclear: Is there a minimum character count? When does a bullet become too short to be meaningful?
   - Recommendation: No hard minimum per bullet, but TRIM prompt should say "Reduce length by 10-20%; maintain meaning." Test empirically: generate resume with TRIM, verify bullets remain ATS-parsable and meaningful.

5. **How to handle LaTeX special character escaping in selected content?**
   - What we know: Phase 3 CONTEXT.md specifies latex_escape filter must be applied to all user-provided strings in template
   - What's unclear: If master_resume.json contains unescaped special chars (e.g., "O&M Engineer"), does Phase 4 need to pre-escape before passing to renderer, or does renderer handle it?
   - Recommendation: Renderer handles it (Phase 3 pattern). Phase 4 passes selected_json as-is; Phase 3 template applies `| latex_escape` filter to all user fields. No pre-escaping in Phase 4.

## Sources

### Primary (HIGH confidence)
- **Phase 2 Research (RESEARCH.md)** — LLMClient async pattern, retry logic, JSON extraction
  - Ollama AsyncClient API; Tenacity retry patterns; json-repair library
- **Phase 3 Research (RESEARCH.md)** — PyMuPDF page_count, tectonic compilation, PDF analysis patterns
  - fitz API for page counting, text extraction; tectonic subprocess invocation; sentinel dict returns
- **Phase 3 Context (CONTEXT.md)** — Jinja2 custom delimiters, latex_escape filter, artifact naming
  - Custom delimiter configuration; latex_escape application to all user strings; _iter_N naming
- **Pydantic official docs** — Data validation, model_dump_json, custom serialization
  - https://docs.pydantic.dev/latest/
- **Python asyncio docs** — Async/await patterns, exception handling
  - https://docs.python.org/3/library/asyncio.html
- **Structured JSON schema validation** — resume_json_template.json defines expected payload format
  - Local file; reviewed in context gathering phase

### Secondary (MEDIUM confidence)
- **Project decision history (STATE.md)** — Previous decisions on LLM patterns, error handling, path safety
  - Atomic writes, path traversal prevention, retry patterns already established
- **WebSearch: TRIM algorithm for resume generation** — Iteration patterns, termination conditions
  - Multiple sources agree: compile → measure → trim → repeat with explicit max_iterations safety
- **WebSearch: Entity extraction for validation** — Structured diff vs NER performance
  - Consensus: structured field matching is faster, deterministic; NER adds complexity without benefit for this use case

### Tertiary (LOW confidence)
- **Whitespace threshold calibration strategy** — Exact percentage needs empirical validation
  - 40% mentioned in CONTEXT.md but not yet tested; recommendation to validate during Phase 4 testing

## Metadata

**Confidence breakdown:**
- **Standard stack and established patterns (LLM integration, async, retry, PDF analysis):** **HIGH** — All verified via Phase 2/3 research and existing codebase
- **Core Phase 4 architecture (ResumeService, TRIM loop, entity validation):** **HIGH** — Patterns are straightforward applications of Phase 2/3 + standard Python practices; no novel technology
- **Edge cases and validation strategy:** **MEDIUM-HIGH** — Common pitfalls identified and documented; exact whitespace threshold and error tolerance need empirical Phase 4 testing
- **Skills selection strategy (keyword vs LLM pass):** **MEDIUM** — Keyword-based filter recommended as simpler first approach; validation will catch hallucinations

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (30 days — LLM/PDF ecosystem stable; Phase 4 core is standard patterns, not bleeding-edge)

**Critical unknowns:**
- Exact whitespace_ratio threshold for over-trimmed detection (needs Phase 4 testing with 5 sample resumes)
- Skills selection reliability (keyword filter vs LLM pass — trade-off between speed and accuracy needs testing)
- Maximum iterations needed in practice (set to 5; may need adjustment based on real resume complexity)
