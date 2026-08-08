# Codebase Structure

**Analysis Date:** 2026-02-21

## Directory Layout

```
resume/
├── src/                       # Python source code for the application
│   ├── main.py                # Entry point and pipeline orchestration
│   ├── config.py              # Configuration management (YAML-based)
│   ├── logger.py              # Logging infrastructure
│   ├── llm.py                 # LLM integration and prompt functions
│   ├── resume_generator.py    # LaTeX template and PDF compilation
│   ├── cover_letter_generator.py  # DOCX creation and PDF conversion
│   └── pdf_analyzer.py        # PDF whitespace analysis
├── templates/                 # Static templates and schemas
│   ├── resume_template.tex    # LaTeX resume template (input)
│   ├── resume_template.pdf    # Compiled template (reference)
│   ├── cover_letter_prompt.md # LLM prompt template for cover letters
│   ├── cover_letter_template.docx  # DOCX template (reference)
│   ├── job_description_schema.json # Schema for JD parsing
│   ├── master_resume.json     # Structured resume data (reference)
│   ├── resume_generation_config.json # Resume generation config (reference)
│   └── .gitkeep               # Placeholder for empty directory
├── data/                      # Generated outputs (company-specific)
│   ├── {company_name}/        # Directory per company processed
│   │   ├── {company_name}_jd.json              # Parsed job description
│   │   ├── {company_name}_resume.tex           # Generated LaTeX (no optimization)
│   │   ├── {company_name}_resume.pdf           # Final resume PDF
│   │   ├── {company_name}_resume_iter_1.tex   # Iteration 1 LaTeX
│   │   ├── {company_name}_resume_iter_1.pdf   # Iteration 1 PDF
│   │   ├── {company_name}_resume_iter_2.tex   # Iteration 2 LaTeX
│   │   ├── {company_name}_resume_iter_2.pdf   # Iteration 2 PDF
│   │   ├── {company_name}_cover_letter.docx   # Generated cover letter DOCX
│   │   └── {company_name}_cover_letter.pdf    # Converted cover letter PDF
│   └── .gitkeep               # Placeholder for empty directory
├── input/                     # Source job descriptions
│   ├── jd.txt                 # Job description text file
│   └── ...                    # Additional JD files
├── logs/                      # Application logs
│   ├── app.log                # Combined application log
│   └── .gitkeep               # Placeholder for empty directory
├── config.yaml                # Application configuration (LLM, paths, thresholds)
├── requirements.txt           # Python dependencies
├── PRD.md                      # Product requirements document
├── development_plan.md        # Development plan and roadmap
└── claude-code-setup.md       # Setup instructions
```

## Directory Purposes

**src/:**
- Purpose: All Python application code
- Contains: Modular logic for configuration, logging, LLM integration, file processing, and orchestration
- Key files: `main.py` (entry point), `llm.py` (core LLM logic), `resume_generator.py` and `cover_letter_generator.py` (output generation)

**templates/:**
- Purpose: Static input templates, schemas, and prompts used by the application
- Contains: LaTeX resume template (source of truth for resume format), JSON schemas for LLM parsing, markdown prompts for LLM instruction
- Key files: `resume_template.tex` (used as base for all generated resumes), `job_description_schema.json` (constrains JD parsing), `cover_letter_prompt.md` (instructs LLM on cover letter generation)

**data/:**
- Purpose: Generated outputs organized by company
- Contains: Parsed job descriptions (JSON), generated resumes (LaTeX, PDF), generated cover letters (DOCX, PDF), and iteration artifacts
- Key files: Company-specific subdirectories contain all outputs for a single job application

**input/:**
- Purpose: Raw job descriptions before processing
- Contains: `.txt` files with job description text (one per job application)
- Key files: `jd.txt` (or custom filenames passed via `--jd` CLI argument)

**logs/:**
- Purpose: Application runtime logs for debugging and audit
- Contains: Single log file with all messages from all modules
- Key files: `app.log` (append-only, grows across runs)

## Key File Locations

**Entry Points:**
- `src/main.py`: CLI entry point and main orchestration function; contains `check_dependencies()` and `main()`

**Configuration:**
- `config.yaml`: Application configuration (LLM URL, model ID, whitespace threshold, max iterations, path settings)

**Core Logic:**
- `src/llm.py`: LLM prompt engineering and API communication; contains `prompt_ollama()`, `parse_jd_to_json()`, `generate_latex_resume()`, `extract_company_name()`, `generate_cover_letter()`
- `src/config.py`: Configuration loader with property accessors
- `src/logger.py`: Logger factory

**Resume Generation:**
- `src/resume_generator.py`: `read_latex_template()` and `compile_latex_to_pdf()` functions
- `templates/resume_template.tex`: LaTeX template source

**Cover Letter Generation:**
- `src/cover_letter_generator.py`: `save_as_docx()` and `convert_docx_to_pdf()` functions
- `templates/cover_letter_prompt.md`: LLM prompt template

**PDF Analysis:**
- `src/pdf_analyzer.py`: `analyze_whitespace()` function using PyMuPDF

**Testing & Documentation:**
- `PRD.md`: Product requirements
- `development_plan.md`: Development roadmap and technical decisions

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `resume_generator.py`, `pdf_analyzer.py`)
- Data outputs: `{company_name}_{asset_type}{_iteration}.{extension}` (e.g., `Cisco_resume_iter_1.tex`, `Cisco_cover_letter.pdf`)
- Configuration: `config.yaml` (application config), `*.json` (data schemas and reference configs)
- Templates: `*_template.*` (e.g., `resume_template.tex`, `cover_letter_template.docx`)
- Logs: `app.log` (single combined application log)

**Directories:**
- lowercase with underscores: `src/`, `templates/`, `data/`, `input/`, `logs/`
- Generated company directories: `data/{company_name}/` (exact company name as extracted and sanitized)

**Variables and Functions:**
- Functions: `snake_case` (e.g., `parse_jd_to_json()`, `compile_latex_to_pdf()`, `analyze_whitespace()`)
- Classes: `PascalCase` (e.g., `Config`, `OllamaError`)
- Module-level constants: `UPPERCASE` (e.g., `LOG_DIR`)

**Types and Schemas:**
- JSON schema files: `*_schema.json` (e.g., `job_description_schema.json`)
- Config files: `*_config.json` (e.g., `resume_generation_config.json`)

## Where to Add New Code

**New Feature (e.g., new document type beyond resume + cover letter):**
- Implementation: Create new module in `src/{document_type}_generator.py` following the pattern of `resume_generator.py` and `cover_letter_generator.py`
- Integration: Import and call in `src/main.py` within the main pipeline
- Templates: Add template file to `templates/{document_type}_template.*`
- Prompts: Add prompt template to `templates/{document_type}_prompt.md` if LLM-driven

**New LLM Task (e.g., new parsing or generation function):**
- Implementation: Add new function to `src/llm.py`
- Pattern: Follow existing functions (`parse_jd_to_json()`, `generate_latex_resume()`) - use `prompt_ollama()` for API calls, handle JSON/text parsing, implement response cleaning as needed
- Prompts: Define prompt string within function or externalize to `templates/` if complex
- Error Handling: Raise `OllamaError` on API failures; return empty dict/string on LLM parsing failures

**New Configuration Parameter:**
- Add to `config.yaml` under appropriate section (e.g., `resume`, `llm`, `paths`)
- Add property accessor to `Config` class in `src/config.py` (e.g., `@property def new_param(self): return self.config['section']['param']`)

**New Logging Point:**
- Use existing logger from module: `logger = get_logger(__name__)`
- No new logger initialization needed; factory ensures consistent configuration

**New External Dependency:**
- Add to `requirements.txt`
- Add validation to `check_dependencies()` in `src/main.py` if system-level tool (e.g., new CLI dependency like tectonic)

## Special Directories

**.planning/codebase/:**
- Purpose: GSD (Get Shit Done) codebase analysis documents
- Generated: Yes (by GSD mappers)
- Committed: Yes
- Contents: `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `TESTING.md`, `CONCERNS.md`, `STACK.md`, `INTEGRATIONS.md`

**src/__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (listed in `.gitignore`)

**data/{company_name}/:**
- Purpose: Outputs for a specific job application
- Generated: Yes (at runtime by main pipeline)
- Committed: Typically no; data is application-specific output
- Structure: All files for one company application are grouped together for easy inspection and sharing

---

*Structure analysis: 2026-02-21*
