# Architecture

**Analysis Date:** 2026-02-21

## Pattern Overview

**Overall:** Pipeline-based sequential processing with configuration-driven behavior and external LLM integration.

**Key Characteristics:**
- Single-threaded, synchronous execution flow
- External service dependency (Ollama LLM) for intelligent content generation
- Multi-format output generation (LaTeX → PDF, DOCX → PDF)
- Iterative optimization with feedback loop for resume whitespace management
- Layered separation between configuration, core logic, and file I/O

## Layers

**Configuration Layer:**
- Purpose: Centralized configuration management for LLM endpoints, model selection, optimization parameters, and file paths
- Location: `src/config.py`
- Contains: YAML-based configuration schema with property accessors
- Depends on: External `config.yaml` file
- Used by: All other modules access configuration through singleton `config` object

**Logging Layer:**
- Purpose: Unified logging infrastructure with dual output (console and file) and configurable severity levels
- Location: `src/logger.py`
- Contains: Logger factory function with handler setup
- Depends on: Python standard library `logging` module
- Used by: All modules for operational visibility and debugging

**LLM Integration Layer:**
- Purpose: Abstraction over Ollama API for LLM-powered content generation tasks
- Location: `src/llm.py`
- Contains: `prompt_ollama()` for API communication, and specialized prompt-based functions for domain-specific tasks
- Depends on: HTTP requests to Ollama, JSON parsing, template files in `templates/`
- Used by: Main orchestration layer for all intelligent content generation

**Resume Processing Layer:**
- Purpose: LaTeX template handling and PDF compilation
- Location: `src/resume_generator.py`
- Contains: Template reading and LaTeX-to-PDF compilation logic using tectonic
- Depends on: File I/O, external `tectonic` command-line tool
- Used by: Main orchestration for resume PDF generation

**Cover Letter Processing Layer:**
- Purpose: DOCX creation and PDF conversion
- Location: `src/cover_letter_generator.py`
- Contains: Text-to-DOCX serialization and DOCX-to-PDF conversion using docx2pdf
- Depends on: `python-docx` library, `docx2pdf` library, external Office/LibreOffice tools
- Used by: Main orchestration for cover letter PDF generation

**PDF Analysis Layer:**
- Purpose: Whitespace measurement for iterative optimization feedback
- Location: `src/pdf_analyzer.py`
- Contains: PDF text extraction and whitespace percentage calculation using PyMuPDF
- Depends on: `fitz` (PyMuPDF) library for PDF parsing
- Used by: Main orchestration to drive whitespace optimization loop

**Orchestration Layer:**
- Purpose: Coordinates the entire pipeline, manages state, handles errors, and drives decision logic
- Location: `src/main.py`
- Contains: `main()` entry point, dependency checking, CLI argument parsing, pipeline sequencing
- Depends on: All other layers
- Used by: Command-line invocation

## Data Flow

**Standard Workflow (with optimization):**

1. **Initialization**: `check_dependencies()` validates external tools (ollama, pdflatex/tectonic, libreoffice) are available and accessible
2. **Input Parsing**: Read job description from file specified via `--jd` CLI argument
3. **Company Extraction**: LLM extracts company name from raw job description text
4. **JD Parsing**: LLM parses job description into structured JSON using schema from `templates/job_description_schema.json`
5. **Resume Template Loading**: Read LaTeX template from `templates/resume_template.tex`
6. **Output Directory Setup**: Create company-specific directory under `data/{company_name}/`
7. **JD JSON Persistence**: Save parsed job description to `data/{company_name}/{company_name}_jd.json`
8. **Resume Generation Loop** (if `--no-optimization` not set):
   - For each iteration (up to `config.max_optimization_iterations`):
     - Generate tailored LaTeX resume using LLM with optional section expansion hints
     - Save generated LaTeX to `data/{company_name}/{company_name}_resume_iter_{i}.tex`
     - Compile LaTeX to PDF using tectonic
     - Analyze PDF whitespace using PyMuPDF
     - If whitespace ≤ `config.whitespace_threshold`: Exit loop (optimization complete)
     - Otherwise: Continue to next iteration with `["WORK EXPERIENCE"]` marked for expansion
9. **Direct Resume Generation** (if `--no-optimization` set):
   - Generate tailored LaTeX resume once (no iteration)
   - Save to `data/{company_name}/{company_name}_resume.tex`
   - Compile to PDF
10. **Cover Letter Generation**: Using parsed JD and tailored resume, generate cover letter text via LLM
11. **Cover Letter Output**: Save as DOCX, then convert DOCX to PDF
12. **Error Handling**: Catch and log `OllamaError`, file errors, and subprocess failures; exit gracefully

**State Management:**
- `tailored_latex_resume`: Persisted across iterations as reference for subsequent steps
- `expand_sections`: Array that accumulates during optimization loop, passed to LLM for context
- File outputs: Incremental saves at each major stage enable recovery and inspection
- Logs: Written to `logs/app.log` for debugging and audit trail

## Key Abstractions

**OllamaError:**
- Purpose: Custom exception type for LLM service failures
- Examples: Raised by `prompt_ollama()`, `parse_jd_to_json()`, `generate_latex_resume()`, `extract_company_name()`, `generate_cover_letter()`
- Pattern: Wraps HTTP request exceptions with context; can be caught separately from file/subprocess errors

**Config Object:**
- Purpose: Singleton configuration accessor with property-based interface
- Examples: `config.ollama_url`, `config.model_id`, `config.whitespace_threshold`, `config.templates_path`, `config.data_path`
- Pattern: Lazy-loaded from YAML on first access; properties encapsulate schema navigation

**Prompt Templates:**
- Purpose: Reusable, parameterized prompts that inject structured context into LLM calls
- Examples: `templates/job_description_schema.json`, `templates/cover_letter_prompt.md`, embedded prompts in `llm.py`
- Pattern: Prompts are formatted Python f-strings with role definition, schema injection, and output constraints

**Logger Factory:**
- Purpose: Standardized logger configuration with dual handlers
- Examples: Used via `get_logger(__name__)` in each module
- Pattern: Returns configured `logging.Logger` instance; skips handler re-registration on repeated calls

## Entry Points

**CLI Entry Point:**
- Location: `src/main.py`, `main()` function
- Triggers: `python -m src.main --jd <path_to_job_description> [--no-optimization]`
- Responsibilities: Argument parsing, dependency validation, pipeline orchestration, error handling

**Dependency Check:**
- Location: `src/main.py`, `check_dependencies()` function
- Triggers: Called first in `main()`
- Responsibilities: Verify `ollama`, `pdflatex` or `tectonic`, `libreoffice` are in PATH; verify Ollama service is running via HTTP

## Error Handling

**Strategy:** Fail-fast with detailed logging. Each layer logs errors at appropriate severity (DEBUG, INFO, WARNING, ERROR, CRITICAL) before raising or catching exceptions.

**Patterns:**

- **OllamaError (Custom)**: Raised when LLM API communication fails; caught in main() to provide user guidance
- **FileNotFoundError**: Raised when required templates or input files are missing; caught in main() with context logging
- **ValueError**: Raised when file type validation fails (e.g., non-.tex, non-.docx input)
- **subprocess.CalledProcessError**: Raised when tectonic or docx2pdf subprocess fails; logged with stdout/stderr for debugging
- **json.JSONDecodeError**: Caught in `parse_jd_to_json()` when LLM returns invalid JSON; returns empty dict as fallback
- **requests.exceptions.RequestException**: Caught in `prompt_ollama()` and wrapped as OllamaError
- **Generic Exception**: Catch-all in main() logs with traceback and exits with code 1

**Recovery:**
- Iteration tolerance: Resume generation loop continues to next iteration if PDF compilation fails
- Partial success: Cover letter generation is attempted even if resume PDF creation had issues (soft failure)
- No rollback: Generated files are not cleaned up; enables manual inspection if process halts mid-pipeline

## Cross-Cutting Concerns

**Logging:**
- Centralized via `get_logger(__name__)` in all modules
- Dual output: Console shows INFO and above; file (`logs/app.log`) captures DEBUG and above
- Format: Console uses `name - level - message`; file includes timestamps

**Validation:**
- Input: File existence checked before read operations; CLI arguments are required
- LLM Output: JSON and LaTeX responses are validated before use; markdown code block wrappers are stripped
- Format: File extensions validated (`.tex`, `.docx`); LaTeX and DOCX structure assumed correct per LLM compliance

**Configuration Management:**
- Centralized in `config.yaml`; read once at module import time
- No runtime re-configuration; all values are read-only properties
- Paths can be relative or absolute; resolved at use time

**External Tool Invocation:**
- All subprocess calls use `subprocess.run()` with `check=True` for error detection
- Output captured (`capture_output=True`) and logged on failure
- Tools checked in PATH via `shutil.which()` before use in critical paths

---

*Architecture analysis: 2026-02-21*
