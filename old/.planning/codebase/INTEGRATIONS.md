# External Integrations

**Analysis Date:** 2026-02-21

## APIs & External Services

**Large Language Models:**
- Ollama (Local LLM Service)
  - Purpose: Generate tailored resume content, parse job descriptions, extract company names, generate cover letters
  - SDK/Client: requests library
  - Endpoint: Configured via `config.yaml` - `llm.ollama_url` (default: `http://localhost:11434/api/generate`)
  - Model: Configurable via `llm.model_id` (default: `llama3.1:8b`)
  - Authentication: None (local service)
  - Used in: `src/llm.py` - `prompt_ollama()` function
  - Protocol: HTTP POST with JSON payload

## Data Storage

**Databases:**
- None - No database integration

**File Storage:**
- Local filesystem only
  - Input: Job description text files (user-provided via `--jd` CLI argument)
  - Output: Generated resumes (LaTeX .tex files, PDF files), cover letters (DOCX and PDF files)
  - Configuration: `config.yaml` paths
  - Output directory: `data/` (configurable via `paths.data`)
  - Schema files: `templates/job_description_schema.json`

**Caching:**
- None - No caching mechanism

## Document Processing

**PDF Analysis:**
- PyMuPDF (fitz library)
  - Purpose: Analyze whitespace percentage in generated resume PDFs for optimization loop
  - Used in: `src/pdf_analyzer.py` - `analyze_whitespace()` function
  - Local processing only (no external service)

**Document Conversion:**
- docx2pdf library
  - Purpose: Convert generated cover letters from DOCX to PDF format
  - Backend: macOS uses Microsoft Word or LibreOffice; Windows uses Microsoft Word; Linux uses LibreOffice
  - Used in: `src/cover_letter_generator.py` - `convert_docx_to_pdf()` function

**LaTeX Compilation:**
- tectonic (external CLI tool)
  - Purpose: Compile tailored LaTeX resume templates to PDF
  - Installation: Required, must be in system PATH
  - Used in: `src/resume_generator.py` - `compile_latex_to_pdf()` function
  - Invoked via: subprocess with command `tectonic -o <output_dir> <latex_file>`

## Authentication & Identity

**Auth Provider:**
- None - No authentication mechanism
- Ollama service is assumed to be running locally and accessible

## Monitoring & Observability

**Error Tracking:**
- None - Custom exception handling with `OllamaError` class

**Logs:**
- File-based logging
  - Framework: Python `logging` module
  - Output file: `logs/app.log` (auto-created)
  - Console output: INFO level and above
  - File output: DEBUG level and above
  - Implementation: `src/logger.py` - `get_logger()` function

## CI/CD & Deployment

**Hosting:**
- Not applicable - Command-line desktop application

**CI Pipeline:**
- None detected

**Dependency Checks:**
- Runtime dependency verification in `src/main.py` - `check_dependencies()` function
  - Checks for: ollama, pdflatex, libreoffice in system PATH
  - Validates Ollama service is running via HTTP GET to base URL

## Environment Configuration

**Required env vars:**
- None - All configuration via `config.yaml` YAML file

**Secrets location:**
- Not applicable - No API keys or secrets required
- Configuration file: `config.yaml` (checked into version control)

## Input Processing

**Job Description Input:**
- Format: Plain text file
- Source: User-provided via CLI argument `--jd <path>`
- Processing: Read from filesystem, passed to LLM for parsing

**Template Files:**
- Resume template: `templates/resume_template.tex` (LaTeX)
- Job description schema: `templates/job_description_schema.json` (JSON schema for LLM)
- Cover letter prompt: `templates/cover_letter_prompt.md` (Markdown prompt template)

## Output Generation

**Resume Output:**
- LaTeX files: `{company_name}_resume.tex` or `{company_name}_resume_iter_N.tex`
- PDF files: `{company_name}_resume.pdf` or `{company_name}_resume_iter_N.pdf`
- JSON metadata: `{company_name}_jd.json` (parsed job description)
- Location: `data/{company_name}/` (configurable)

**Cover Letter Output:**
- DOCX file: `{company_name}_cover_letter.docx`
- PDF file: `{company_name}_cover_letter.pdf`
- Location: `data/{company_name}/` (configurable)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Service Dependencies and Health Checks

**Critical Dependencies:**
1. Ollama service must be running and responding to health check
   - Health check: HTTP GET to `http://localhost:11434` (base URL without `/api/generate`)
   - Failure: Application exits with critical error
   - Checked in: `src/main.py` - `check_dependencies()` line 36-40

2. tectonic must be installed and in PATH
   - Failure: Application exits with installation instructions
   - Checked in: `src/main.py` - `check_dependencies()` line 20-33

3. pdflatex or libreoffice required for DOCX to PDF conversion
   - Fallback detection in: `src/main.py` - `check_dependencies()` line 20
   - Error handling in: `src/cover_letter_generator.py` - `convert_docx_to_pdf()` with helpful error messages

---

*Integration audit: 2026-02-21*
