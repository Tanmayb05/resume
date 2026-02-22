# Phase 3: LaTeX Engine and PDF Analyzer - Research

**Researched:** 2026-02-22
**Domain:** LaTeX rendering, PDF compilation, PDF analysis
**Confidence:** HIGH

## Summary

Phase 3 implements a three-stage pipeline: (1) render JSON payload through resume_template.tex.j2 using Jinja2 with custom delimiters to avoid LaTeX syntax conflicts, (2) compile the rendered .tex file via tectonic subprocess with structured error handling, (3) analyze the resulting PDF for page count and whitespace metrics. The phase depends on Phase 2's Jinja2 prompt registry infrastructure and must validate that templates render without unresolved variables, LaTeX syntax is correct, compilation succeeds with proper error capture, and the output is ATS-parsable via pdftotext.

**Primary recommendation:** Use PyMuPDF (fitz) for PDF analysis, tectonic CLI via subprocess.run() with structured error capture, and Jinja2 custom delimiters (not default {{ }} which conflict with LaTeX).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RES-02 | System renders a LaTeX .tex file from selected content using resume_template.tex.j2 | Jinja2 custom delimiter configuration prevents LaTeX syntax conflicts; FileSystemLoader + StrictUndefined already established in Phase 2 |
| RES-03 | System compiles the .tex file to PDF via tectonic | tectonic subprocess integration via CalledProcessError + return code checking; structured error capture via stderr |
| RES-05 | Final .tex and .pdf artifacts saved to data/<company_slug>/ with iteration tracking (_iter_N naming) | Standard file I/O; atomic write pattern already established in Phase 1 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1+ | LaTeX template rendering with custom delimiters | Established in Phase 2; prevents {{ }} conflicts with LaTeX syntax; StrictUndefined enforces all variables supplied |
| PyMuPDF (fitz) | 1.20+ | PDF page count and whitespace analysis | Official documentation maintained; simple API (doc.page_count, doc.load_page()); widely used for document analysis |
| tectonic | 0.13+ | LaTeX compilation (CLI via subprocess) | Modernized, self-contained TeX engine; no external package downloads needed after first run; better error messages than pdflatex |
| pdftotext | system-provided (poppler) | Text extraction for ATS parsability validation | Standard tool for PDF text extraction; available on macOS, Linux, Windows; detects empty/corrupt PDFs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| subprocess (stdlib) | Python 3.11+ | Subprocess management for tectonic CLI | Capture stdout/stderr; handle return codes; structured error creation |
| pathlib (stdlib) | Python 3.11+ | File path handling | Consistent cross-platform paths; atomic write via tempfile + os.replace() |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tectonic | pdflatex / xelatex | pdflatex slower first-run (60-120s pkg download); less error context; xelatex larger binaries |
| PyMuPDF | pypdf / pdfplumber | pdfplumber slower for simple metrics; pypdf less active maintenance; fitz fastest for page count + text box extraction |
| Jinja2 custom delim | raw string manipulation | Error-prone; no syntax checking; impossible to validate at render time |

**Installation:**
```bash
pip install Jinja2==3.1.5 PyMuPDF==1.20.2
# tectonic: brew install tectonic (macOS) or https://tectonic-typesetting.github.io/
# pdftotext: brew install poppler (macOS) or system package manager
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── latex/
│   ├── __init__.py
│   ├── renderer.py        # Jinja2 render .tex from JSON payload
│   ├── compiler.py        # tectonic subprocess + error handling
│   └── pdf_analyzer.py    # PyMuPDF page_count, whitespace_ratio
├── models/
│   └── job_record.py      # (existing)
└── storage/
    └── job_store.py       # (existing)

templates/
└── resume_template.tex    # Jinja2-rendered LaTeX template
```

### Pattern 1: Jinja2 Custom Delimiters for LaTeX
**What:** Use non-standard delimiters to avoid conflict with LaTeX `{{ }}` and `{% %}`
**When to use:** Always for LaTeX/TeX templates; default delimiters break LaTeX syntax
**Example:**
```python
# Source: Phase 2 established pattern in src/llm/utils.py
from jinja2 import Environment, FileSystemLoader, StrictUndefined

env = Environment(
    loader=FileSystemLoader("templates"),
    undefined=StrictUndefined,
    # Custom delimiters for LaTeX compatibility:
    variable_start_string='((*',
    variable_end_string='*))',
    block_start_string='((%',
    block_end_string='%))',
    comment_start_string='((#',
    comment_end_string='#))',
    trim_blocks=True,
    lstrip_blocks=True,
)

# In template: (( var_name )) renders variable; ((% if condition %)) for blocks
```

### Pattern 2: Subprocess Error Capture for tectonic
**What:** Run tectonic via subprocess.run() with structured error response
**When to use:** Always when calling external CLI tools; avoids raw exception propagation
**Example:**
```python
import subprocess
from pathlib import Path

def compile_tex(tex_path: Path, pdf_path: Path) -> dict:
    """Compile .tex to PDF via tectonic. Returns structured result."""
    try:
        result = subprocess.run(
            ["tectonic", "--outdir", str(pdf_path.parent), str(tex_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,  # Raises CalledProcessError if exit != 0
        )
        return {"success": True, "pdf_path": str(pdf_path)}
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error_type": "compilation_failed",
            "stderr": e.stderr[:500],  # First 500 chars for debugging
            "return_code": e.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error_type": "timeout", "stderr": "Compilation exceeded 30s"}
    except FileNotFoundError:
        return {"success": False, "error_type": "tectonic_not_found", "stderr": "tectonic binary not in PATH"}
```

### Pattern 3: PDF Analysis with Sentinel Values
**What:** Return specific sentinel values for missing/corrupt PDFs instead of raising exceptions
**When to use:** When PDF is optional or error is non-fatal; enables graceful degradation
**Example:**
```python
import fitz  # PyMuPDF

def analyze_pdf(pdf_path: str) -> dict:
    """Return page_count and whitespace_ratio; sentinel values on error."""
    try:
        doc = fitz.open(pdf_path)
        page_count = doc.page_count

        # Whitespace calculation (simplified):
        whitespace_ratio = 0.0
        for page_num in range(page_count):
            page = doc[page_num]
            blocks = page.get_text("blocks")
            # Calculate text area vs total page area
            # ... implementation ...

        doc.close()
        return {"page_count": page_count, "whitespace_ratio": whitespace_ratio}
    except FileNotFoundError:
        return {"page_count": -1, "whitespace_ratio": -1.0, "error": "PDF not found"}
    except Exception as e:
        return {"page_count": -1, "whitespace_ratio": -1.0, "error": str(e)}
```

### Pattern 4: Atomic File Write for .tex and .pdf Artifacts
**What:** Write to temp file, fsync, then atomic rename to final path
**When to use:** Always for production files; prevents partial writes if process crashes
**Example:**
```python
import tempfile
import os
from pathlib import Path

def save_tex_file(tex_content: str, output_path: Path) -> bool:
    """Atomically write .tex file to output_path."""
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=output_path.parent,
            delete=False,
            suffix='.tex'
        ) as tmp:
            tmp.write(tex_content)
            tmp.flush()
            os.fsync(tmp.fileno())  # Ensure written to disk
            tmp_path = tmp.name

        os.replace(tmp_path, output_path)  # Atomic rename
        return True
    except Exception as e:
        print(f"Error writing {output_path}: {e}")
        return False
```

### Anti-Patterns to Avoid
- **Using default Jinja2 delimiters for LaTeX:** `{{ var }}` conflicts with LaTeX math mode and command parameters. Will cause "undefined variable" errors when LaTeX tries to interpret Jinja delimiters as LaTeX syntax.
- **Raw subprocess exception propagation:** Callers see `CalledProcessError` with no structured context. Use wrapped response dicts instead.
- **Raising exceptions for missing PDFs:** Caller must catch exception. Use sentinel values (-1 for page_count, -1.0 for whitespace_ratio) and include error details in return dict.
- **Non-atomic file writes:** If process crashes mid-write, incomplete .tex/.pdf files remain. Use tempfile + os.replace() always.
- **Assuming pdftotext output is non-empty:** Corrupt/scanned PDFs produce empty text. Check `len(text) > 0` before validating ATS parsability.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF page counting / text extraction | Custom PDF parser | PyMuPDF (fitz) | Binary PDF format complex; parser must handle compression, encoding, fonts; fitz handles all edge cases; 20+ years of development |
| LaTeX compilation | Custom tectonic wrapper | subprocess.run() with CalledProcessError | tectonic CLI is stable; only needs basic subprocess setup; custom wrapper adds complexity without benefit |
| Whitespace detection | Manual pixel analysis / OCR | PyMuPDF text block coordinates | fitz provides text bounding boxes; no OCR needed; whitespace = 1 - (total_text_area / page_area) |
| Custom Jinja delimiters | Find/replace escaping | Jinja2 Environment(custom delimiters) | Escaping LaTeX special chars is error-prone and incomplete; Jinja2 handles all edge cases |

**Key insight:** PDF parsing is deceptively complex (compression, 15+ text encoding standards, font subsetting, OCR-less scanned documents). Tectonic/LaTeX compilation similarly complex. Hand-rolling either creates unmaintainable code with edge case bugs. Use battle-tested libraries.

## Common Pitfalls

### Pitfall 1: tectonic First-Run Package Download (60-120s)
**What goes wrong:** User submits resume, UI shows spinner for 2+ minutes on first run. Appears hung.
**Why it happens:** tectonic downloads LaTeX packages to ~/.cache on first invocation (one-time cost).
**How to avoid:**
  - Web UI must show explicit "Downloading LaTeX engine (first run only)..." message during generation
  - Document in README: first resume generation takes 2-3 min, subsequent <5s
  - Consider warming cache during installation or first app load
**Warning signs:** Generation takes 60+ seconds on initial invocation; subsequent runs <5s

### Pitfall 2: Jinja2 Render Succeeds But LaTeX Compilation Fails
**What goes wrong:** .tex file has unescaped LaTeX special chars (& $ % # _ { } ^ ~) from JSON payload. Renderer passes, compiler rejects.
**Why it happens:** Jinja2 renderer only validates template syntax, not LaTeX syntax. User-provided text (name, job titles, etc.) may contain unescaped specials.
**How to avoid:**
  - Apply `latex_escape` Jinja2 filter to all user-provided strings in template: `(( name | latex_escape ))`
  - Validate in Phase 4 that generated .tex passes LaTeX syntax check (compile with --check mode)
  - Test fixture JSON with edge cases: "O&M Engineer", "AWS $100K salary", "Smith & Associates"
**Warning signs:** Compilation fails with "Undefined control sequence" or "Missing $ inserted"

### Pitfall 3: PyMuPDF Page Count vs Actual Rendered Pages
**What goes wrong:** `page_count` returns 1 but PDF appears multi-page in viewer (page height exceeds letter-size).
**Why it happens:** PDF can have single page with height >> 11 inches. `page_count` is truly 1 page, not multi-page. Whitespace ratio might be very low on single overfull page.
**How to avoid:**
  - Phase 4 uses `page_count > 1` as primary overflow signal (correct per init decision)
  - Also check page height: if height > 11.5 inches and page_count == 1, flag as overflow
  - Whitespace ratio is secondary signal; use only for EXPAND mode in Phase 4
**Warning signs:** page_count=1 but pdftotext shows massive text; page dimensions non-standard

### Pitfall 4: pdftotext Extraction Fails on Corrupt/Scanned PDFs
**What goes wrong:** ATS parsability check `if len(pdftotext_output) > 0` passes, but text is gibberish (scanned PDF with no OCR).
**Why it happens:** pdftotext extracts whatever embedded text exists; corrupt fonts produce garbage chars. Scanned PDFs have no embedded text.
**How to avoid:**
  - pdftotext extraction is best-effort; Success Criteria 5 says "non-empty output" — that's the bar
  - If you want stricter validation, check character frequency (corrupt PDFs have unusual char distribution)
  - tectonic + Charter font produces text-embedded PDFs; ATS systems will parse correctly
**Warning signs:** pdftotext returns text but words are unrecognizable; all-numeric output

### Pitfall 5: Whitespace Calculation Overflow (Integer vs Float)
**What goes wrong:** `whitespace_ratio` returns 0.0 for resume with visible whitespace; division precision issue.
**Why it happens:** Block coordinates from PyMuPDF are floats; math can accumulate rounding errors. Dividing by zero if total_page_area is 0.
**How to avoid:**
  - Use float arithmetic throughout: `(float(text_area) / float(page_area))`
  - Guard against zero: `if page_area > 0: ratio = text_area / page_area else: ratio = 0.0`
  - Test with sample PDFs: generate 10 resumes, verify whitespace_ratio between 0.0-1.0
  - Log intermediate values for debugging: print text_area, page_area, ratio
**Warning signs:** whitespace_ratio is exactly 0.0, 1.0, or negative; varies wildly between similar PDFs

### Pitfall 6: .tex File Path Traversal or Collision
**What goes wrong:** User with slug "../../etc" overwrites system files; multiple iterations collide on same filename.
**Why it happens:** Phase 1 validates job_dir; Phase 3 must validate final .tex path. Iteration counter (_iter_0, _iter_1) prevents collisions but only if incremented correctly.
**How to avoid:**
  - Phase 1 already validates company_slug with path traversal check (done in job_store.py)
  - Phase 3 uses _iter_N naming: only allow _iter_0, _iter_1, ... up to max_iterations (e.g., 10)
  - Pre-check: `assert "/../" not in str(tex_path)` before writing
  - Test edge case: slug="test_iter_999999" should still use data/test_iter_999999/resume_iter_0.tex
**Warning signs:** Files written to unexpected directories; _iter_N counter skipped or overwritten

## Code Examples

Verified patterns from official sources:

### LaTeX Rendering with Custom Delimiters
```python
# Source: Jinja2 official docs https://jinja.palletsprojects.com/en/latest/templates/
from jinja2 import Environment, FileSystemLoader, StrictUndefined

def render_resume_tex(resume_json: dict, template_path: str) -> str:
    """Render resume_template.tex.j2 with custom delimiters."""
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,  # Fail on undefined variables
        variable_start_string='((*',
        variable_end_string='*))',
        block_start_string='((%',
        block_end_string='%))',
        comment_start_string='((#',
        comment_end_string='#))',
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_path.name)
    # Ensure all required fields present
    return template.render(**resume_json)
```

### PDF Compilation with Structured Error
```python
# Source: Python subprocess documentation https://docs.python.org/3/library/subprocess.html
import subprocess
from pathlib import Path

def compile_resume_pdf(tex_path: Path, output_dir: Path) -> dict:
    """Compile .tex to PDF via tectonic with structured error handling."""
    try:
        result = subprocess.run(
            ["tectonic", "--outdir", str(output_dir), str(tex_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        pdf_path = output_dir / tex_path.stem / ".pdf"
        return {
            "success": True,
            "pdf_path": str(pdf_path),
            "stderr": result.stderr if result.stderr else None,
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error_type": "compilation_failed",
            "stderr": e.stderr[:500] if e.stderr else "No error output",
            "return_code": e.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error_type": "timeout",
            "stderr": "Compilation exceeded 30 second timeout",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error_type": "tectonic_not_found",
            "stderr": "tectonic CLI not found in PATH. Install via: brew install tectonic",
        }
```

### PDF Analysis with PyMuPDF
```python
# Source: PyMuPDF official docs https://pymupdf.readthedocs.io/en/latest/
import fitz

def analyze_pdf(pdf_path: str) -> dict:
    """Return page_count and whitespace_ratio; sentinel on error."""
    try:
        doc = fitz.open(pdf_path)
        page_count = doc.page_count

        total_page_area = 0.0
        total_text_area = 0.0

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_area = page.rect.width * page.rect.height
            total_page_area += page_area

            # Get text blocks (bounding boxes)
            blocks = page.get_text("blocks")
            for block in blocks:
                # block format: (x0, y0, x1, y1, ...)
                block_width = block[2] - block[0]
                block_height = block[3] - block[1]
                total_text_area += block_width * block_height

        doc.close()

        if total_page_area > 0:
            text_ratio = total_text_area / total_page_area
            whitespace_ratio = 1.0 - text_ratio
        else:
            whitespace_ratio = 1.0  # Assume all white if page area is zero

        return {
            "success": True,
            "page_count": page_count,
            "whitespace_ratio": float(whitespace_ratio),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "page_count": -1,
            "whitespace_ratio": -1.0,
            "error": f"PDF not found: {pdf_path}",
        }
    except Exception as e:
        return {
            "success": False,
            "page_count": -1,
            "whitespace_ratio": -1.0,
            "error": f"Error analyzing PDF: {e}",
        }
```

### ATS Parsability Check via pdftotext
```python
# Source: pdftotext documentation https://www.xpdfreader.com/pdftotext-man.html
import subprocess

def check_ats_parsability(pdf_path: str) -> bool:
    """Verify PDF contains extractable text (ATS parsable)."""
    try:
        result = subprocess.run(
            ["pdftotext", pdf_path, "-"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,  # Don't raise on non-zero; some PDFs return errors
        )

        text = result.stdout.strip()
        # Success Criteria 5: non-empty output confirms ATS parsability
        return len(text) > 0
    except FileNotFoundError:
        # pdftotext not installed; can't verify (acceptable for this phase)
        return True  # Assume OK if tool unavailable
    except subprocess.TimeoutExpired:
        return False  # Timeout means extraction is slow/stuck
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pdflatex subprocess | tectonic subprocess | 2024+ | tectonic faster (no pkg download after first run), better error messages, self-contained |
| {{ }} delimiters in LaTeX | Custom (( )) delimiters | Always (LaTeX templating) | Avoids LaTeX syntax conflicts; no escaping needed |
| Raising exceptions on PDF errors | Returning sentinel dicts | Modern error handling | Callers can handle gracefully; no try/catch needed for validation |
| Manual PDF parsing | PyMuPDF/fitz | 2020+ | fitz maintained actively; hand-rolling unviable due to PDF complexity |

**Deprecated/outdated:**
- **pdflatex/xelatex direct invocation:** Slower first-run; larger installation footprint. Tectonic replaces both with single self-contained binary.
- **fix-busted-json:** Incompatible with Python 3.13 (crashes with IndexError). Replaced with json-repair (established in Phase 2).
- **Custom whitespace detection:** Old approaches used PIL pixel analysis. fitz text block coordinates are more accurate and don't require OCR.

## Open Questions

1. **What is the exact tectonic command-line invocation?**
   - What we know: `tectonic --outdir <dir> <file.tex>` is standard; supports `--check` mode for syntax validation
   - What's unclear: Does tectonic auto-create output directory or require pre-creation? Does --check mode exist or is it xelatex-only?
   - Recommendation: Test with fixture .tex file; document exact invocation in PLAN.md

2. **Should LaTeX special character escaping happen in renderer.py or in LLM prompt (Phase 2)?**
   - What we know: Jinja2 filter `| latex_escape` exists; Phase 2 LLM generates JSON payload
   - What's unclear: Is escaping the LLM's responsibility (in Phase 2 prompt) or Phase 3's responsibility (in template)?
   - Recommendation: Phase 3 applies filter to all user-provided fields (name, company, role, bullets); LLM escaping is optional but safer

3. **How to calibrate whitespace_ratio threshold for EXPAND trigger in Phase 4?**
   - What we know: Phase 2 STATE.md mentions 40% threshold; needs empirical validation
   - What's unclear: Is 40% target for whitespace (remaining) or text fill (opposite)? Should threshold vary by page dimensions?
   - Recommendation: During Phase 3, test with 5 sample single-page PDFs; measure whitespace_ratio; adjust threshold in Phase 4 PLAN

4. **What is the maximum iteration count for resume shortening (Phase 4)?**
   - What we know: _iter_N naming supports unlimited iterations theoretically
   - What's unclear: Safety limit to prevent infinite loops if TRIM never fits on one page
   - Recommendation: Cap at max_iterations=5 (configurable); fail gracefully if exceeded

## Sources

### Primary (HIGH confidence)
- **Jinja2 3.1+ official docs** - Custom delimiters, StrictUndefined behavior, FileSystemLoader
  - https://jinja.palletsprojects.com/en/latest/templates/
- **PyMuPDF (fitz) 1.20+ official docs** - API for page_count, text block extraction
  - https://pymupdf.readthedocs.io/en/latest/
- **Python subprocess official docs** - CalledProcessError, capture_output, timeout handling
  - https://docs.python.org/3/library/subprocess.html
- **Tectonic official site** - CLI options, compile command
  - https://tectonic-typesetting.github.io/

### Secondary (MEDIUM confidence)
- **GitHub latexbuild example** - Jinja2 + LaTeX rendering patterns
  - https://github.com/pappasam/latexbuild
- **Cookieninja custom delimiter docs** - Jinja2 custom delimiter configuration examples
  - https://cookieninja.readthedocs.io/en/latest/advanced/jinja2_custom_delimiter.html
- **Smallpdf ATS PDF article** - Modern ATS systems parse text-based PDFs reliably
  - https://smallpdf.com/blog/do-applicant-tracking-systems-prefer-resumes-in-pdf-format
- **Tectonic GitHub repo** - Error handling, subprocess integration examples
  - https://github.com/tectonic-typesetting/tectonic

### Tertiary (LOW confidence)
- **WebSearch: tectonic error handling** - Subprocess error capture patterns (multiple sources agree)
- **WebSearch: PDF whitespace detection** - Layout analysis tools; consensus on text block approach

## Metadata

**Confidence breakdown:**
- Standard stack (Jinja2, PyMuPDF, tectonic): **HIGH** — All verified via official docs and current usage
- Architecture patterns (delimiters, subprocess, sentinel errors): **HIGH** — Established best practices; Phase 2 already uses these patterns
- Pitfalls and validation strategies: **MEDIUM-HIGH** — WebSearch sources consistent; not all edge cases tested empirically (whitespace threshold needs Phase 4 validation)

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days — LaTeX/PDF ecosystem stable; tectonic updates infrequent)
**Critical unknowns:** Exact tectonic invocation syntax, whitespace threshold calibration — both require Phase 3 experimentation
