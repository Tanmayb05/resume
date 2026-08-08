# Technology Stack

**Analysis Date:** 2026-02-21

## Languages

**Primary:**
- Python 3.13.7 - Core application logic, all business functionality

## Runtime

**Environment:**
- Python 3.13.7 (venv-based virtual environment at `.venv/`)

**Package Manager:**
- pip (Python package manager)
- Lockfile: `requirements.txt` (present, unpinned)

## Frameworks

**Core:**
- None - Standalone Python application using standard library

**Document Generation:**
- LaTeX/tectonic - Resume PDF generation via LaTeX compilation
- python-docx - Cover letter DOCX file creation
- docx2pdf - DOCX to PDF conversion

**Configuration:**
- PyYAML - Configuration file parsing (`config.yaml`)

## Key Dependencies

**Critical:**
- requests 2.x - HTTP client for Ollama API communication
- PyMuPDF (fitz) - PDF whitespace analysis for resume optimization
- python-docx - Word document creation for cover letters
- PyYAML - YAML configuration parsing
- docx2pdf - DOCX to PDF conversion

**Supporting:**
- Built-in libraries: argparse, json, os, subprocess, shutil, logging, re, sys

## External Runtime Dependencies

**Required CLI Tools:**
- tectonic - LaTeX/PDF compiler for resume generation
  - Installation: `brew install tectonic` (macOS), `cargo install tectonic` (Linux/Windows)
- pdflatex - Alternative LaTeX compiler detection (fallback)
- libreoffice - DOCX to PDF conversion fallback for Linux/macOS without Word
- ollama - LLM service for content generation
  - Must be running at configured URL: `http://localhost:11434/api/generate`

## Configuration

**Environment:**
- YAML configuration file: `config.yaml` (required)
- Configurable parameters:
  - `llm.ollama_url` - Ollama API endpoint (default: `http://localhost:11434/api/generate`)
  - `llm.model_id` - Ollama model identifier (default: `llama3.1:8b`)
  - `resume.whitespace_threshold` - Target whitespace percentage (default: 40.0)
  - `resume.max_optimization_iterations` - Resume generation iterations (default: 3)
  - `paths.templates` - Templates directory (default: `templates/`)
  - `paths.data` - Output data directory (default: `data/`)

**Build:**
- No build configuration files (`setup.py`, `pyproject.toml`, `Makefile`)

## Platform Requirements

**Development:**
- macOS, Linux, or Windows
- Python 3.13+
- pip for dependency installation
- tectonic or pdflatex for LaTeX compilation
- LibreOffice or Microsoft Word for DOCX to PDF conversion

**Production:**
- Same as development - no containerization or production-specific deployment configuration

## Dependency Details

**From requirements.txt:**
```
requests          - HTTP requests to Ollama API
python-docx       - DOCX file creation
PyMuPDF           - PDF analysis (whitespace detection)
PyYAML            - YAML configuration parsing
docx2pdf          - DOCX to PDF conversion
```

## Entry Point

- `src/main.py` - Main entry point, runs with Python: `python src/main.py --jd <job_description_file>`

---

*Stack analysis: 2026-02-21*
