# Coding Conventions

**Analysis Date:** 2026-02-21

## Naming Patterns

**Files:**
- Module files: `lowercase_with_underscores.py` (e.g., `llm.py`, `pdf_analyzer.py`, `cover_letter_generator.py`)
- All source files located in `src/` directory

**Functions:**
- Function names: `lowercase_with_underscores` (e.g., `check_dependencies()`, `parse_jd_to_json()`, `analyze_whitespace()`)
- Private functions: Prefixed with single underscore `_function_name()` (e.g., `_clean_cover_letter()`)

**Variables:**
- Local variables: `lowercase_with_underscores` (e.g., `missing_deps`, `jd_json`, `expand_sections`)
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `LOG_DIR`)
- Configuration objects: `config` (singleton instance from `src/config.py`)

**Types:**
- Custom exception classes: `PascalCase` ending with `Error` (e.g., `OllamaError`)
- Regular classes: `PascalCase` (e.g., `Config`)

**Module-level Variables:**
- Logger instances: `logger = get_logger(__name__)` at module level (present in all modules)

## Code Style

**Formatting:**
- No explicit formatter detected (no Black, Prettier, or similar configuration)
- Manual formatting following PEP 8 conventions

**Linting:**
- No explicit linter configuration detected (no `.pylintrc`, `.flake8`, or `pyproject.toml`)
- Code follows implicit PEP 8 style guidelines

**Line Length:**
- Observed compliance with ~100-120 character soft limit (lines in prompt definitions extend longer for clarity)

**Indentation:**
- 4 spaces per indentation level (standard Python convention)

## Import Organization

**Order:**
1. Standard library imports (e.g., `argparse`, `json`, `os`, `subprocess`, `shutil`, `re`)
2. Third-party library imports (e.g., `requests`, `yaml`, `fitz`, `docx`, `docx2pdf`)
3. Local module imports (e.g., `from llm import ...`, `from config import config`)

**Pattern Observed:**
```python
import argparse
import json
import os
import subprocess
import shutil
import requests
from llm import parse_jd_to_json, generate_latex_resume
from config import config
from logger import get_logger
```

**Path Aliases:**
- No path aliases detected; all imports use absolute/relative module paths
- Singleton pattern used: `config` imported from `src/config.py`
- Logger factory: `get_logger(__name__)` used consistently across modules

## Error Handling

**Patterns:**
- **Custom Exceptions:** `OllamaError` class in `src/llm.py` for LLM-specific errors
  ```python
  class OllamaError(Exception):
      """Custom exception for Ollama API errors."""
      pass
  ```

- **Exception Chaining:** Uses `raise ... from e` to preserve stack traces
  ```python
  except requests.exceptions.RequestException as e:
      logger.error(f"Error calling Ollama API: {e}", exc_info=True)
      raise OllamaError(f"Error calling Ollama API: {e}") from e
  ```

- **Broad Exception Catching:** Used cautiously with `Exception` base class in wrapper functions
  ```python
  except Exception as e:
      logger.error(f"Error converting .docx to .pdf: {docx_path}")
      raise
  ```

- **Graceful Degradation:** Returns empty values on non-critical failures
  - `parse_jd_to_json()` returns `{}` on JSON parse failure
  - `generate_latex_resume()` returns `""` on empty LLM response
  - `extract_company_name()` returns `""` on failure

- **Exit on Critical Errors:** `exit(1)` used in main flow for unrecoverable conditions
  ```python
  if missing_deps:
      logger.critical(f"Missing dependencies...")
      exit(1)
  ```

## Logging

**Framework:** Standard library `logging` module

**Configuration Location:** `src/logger.py`

**Logger Setup:**
- Factory function `get_logger(name: str)` creates and configures loggers per module
- Dual handlers: StreamHandler (console) and FileHandler (file-based)
- Console handler level: `INFO` and above
- File handler level: `DEBUG` and above
- Log file: `logs/app.log` (created if missing)

**Format:**
- Console: `'%(name)s - %(levelname)s - %(message)s'`
- File: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`

**Patterns Observed:**

- **Debug Logging:** Used for internal state and file paths
  ```python
  logger.debug(f"Reading LaTeX template from: {template_path}")
  ```

- **Info Logging:** Used for major operation milestones
  ```python
  logger.info("Extracting company name from job description...")
  logger.info(f"Successfully parsed job description to JSON.")
  ```

- **Warning Logging:** Used for recoverable issues and expected degradation
  ```python
  logger.warning("Whitespace is too high. Will attempt to expand sections.")
  logger.warning("LLM returned an empty response for the JD to JSON parsing.")
  ```

- **Error Logging:** Used for exceptions with `exc_info=True` for stack traces
  ```python
  logger.error(f"Error calling Ollama API: {e}", exc_info=True)
  ```

- **Critical Logging:** Used for unrecoverable errors before exit
  ```python
  logger.critical(f"The following dependencies are not installed...")
  ```

**When to Log:**
- Every function entry for `debug` level
- Successful completion of major steps at `info` level
- Errors and exceptions with full traceback
- Configuration and file paths at `debug` level
- User-facing messages at `info` or `warning` level

## Comments

**When to Comment:**
- Comments sparse but used for complex sections (e.g., LaTeX structure preservation requirements)
- Comments used to explain "why" not "what" (code is self-documenting)
- Example from `src/llm.py`:
  ```python
  # The LLM response might have markdown ```json ... ``` tags
  if llm_response.strip().startswith("```json"):
      llm_response = llm_response.strip()[7:-4]
  ```

**Docstring Convention:**
- All public functions and classes have docstrings
- Format: Google-style docstrings (Args, Returns, Raises)
- Example:
  ```python
  def parse_jd_to_json(jd_text: str) -> dict:
      """
      Parses a job description text and returns a structured JSON object.

      Args:
          jd_text: The raw job description text.

      Returns:
          A dictionary representing the structured job description, or an empty dict on failure.
      """
  ```

## Function Design

**Size:**
- Functions are concise and focused (mostly 10-50 lines)
- Single responsibility principle observed
- Longer functions like `main()` are structured with clear comment sections

**Parameters:**
- Type hints used on all function parameters
- Pattern: `param_name: Type` (e.g., `jd_text: str`, `expand_sections: list = None`)
- Default values used for optional parameters

**Return Values:**
- Type hints used on return values
- Clear return statements at end of functions
- Graceful defaults: returns empty dict `{}` or empty string `""` on failure

## Module Design

**Exports:**
- Modules export specific functions and classes (not `from X import *`)
- Example from `src/main.py`:
  ```python
  from llm import parse_jd_to_json, generate_latex_resume, generate_cover_letter, OllamaError, extract_company_name
  from resume_generator import read_latex_template, compile_latex_to_pdf
  from cover_letter_generator import save_as_docx, convert_docx_to_pdf
  ```

**Barrel Files:** Not used; imports are explicit and specific

**Module Organization:**
- `src/main.py`: Entry point and orchestration logic
- `src/llm.py`: LLM integration and prompt engineering
- `src/resume_generator.py`: LaTeX compilation utilities
- `src/cover_letter_generator.py`: DOCX conversion and saving
- `src/pdf_analyzer.py`: PDF whitespace analysis
- `src/config.py`: Configuration management (singleton pattern)
- `src/logger.py`: Logging factory

---

*Convention analysis: 2026-02-21*
