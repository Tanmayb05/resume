# Testing Patterns

**Analysis Date:** 2026-02-21

## Test Framework

**Status:** Not detected

**Finding:** No test files, test configuration files, or testing framework detected in the codebase.

- No `pytest.ini`, `tox.ini`, `setup.cfg`, or `pyproject.toml` configuration
- No test files in directory structure (no `test_*.py` or `*_test.py` files)
- No testing dependencies in `requirements.txt` (only: requests, python-docx, PyMuPDF, PyYAML, docx2pdf)

**Implication:** All validation occurs through manual testing and integration testing only. No automated test suite exists.

## Test Organization (Not Applicable)

**Current State:**
- Codebase currently has zero automated tests
- All quality assurance is manual or through end-to-end execution

## Error Handling for Testing

**Challenge Areas Without Tests:**
- `src/llm.py`: LLM API integration with external Ollama service requires mocking
- `src/resume_generator.py`: LaTeX compilation through external subprocess
- `src/cover_letter_generator.py`: Document conversion using external tools (LibreOffice/Word)
- `src/pdf_analyzer.py`: PDF parsing using PyMuPDF library
- `src/config.py`: YAML file loading and configuration access

## Recommended Testing Strategy

**Framework Recommendation:** `pytest`

**Suggested Installation:**
```bash
pip install pytest pytest-cov pytest-mock
```

### Unit Testing Pattern (Suggested)

**Where to Place Tests:**
- Co-located with source files: Create `tests/` directory parallel to `src/`
- File structure:
  ```
  tests/
  ├── test_llm.py
  ├── test_config.py
  ├── test_logger.py
  ├── test_resume_generator.py
  ├── test_cover_letter_generator.py
  ├── test_pdf_analyzer.py
  └── test_main.py
  ```

**Naming Convention:**
- Test functions: `test_<function_name>` (e.g., `test_parse_jd_to_json`)
- Test classes: `Test<ClassName>` (e.g., `TestOllamaError`)

### Mocking Patterns (Recommended)

**LLM API Mocking (for `src/llm.py`):**
```python
import pytest
from unittest.mock import patch, MagicMock
from llm import prompt_ollama, parse_jd_to_json, OllamaError

@patch('requests.post')
def test_prompt_ollama_success(mock_post):
    """Mock successful Ollama API response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "test response"}
    mock_post.return_value = mock_response

    result = prompt_ollama("test prompt")
    assert result == "test response"
    mock_post.assert_called_once()

@patch('requests.post')
def test_prompt_ollama_connection_error(mock_post):
    """Mock connection error to Ollama API."""
    import requests
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

    with pytest.raises(OllamaError):
        prompt_ollama("test prompt")
```

**External Command Mocking (for `src/resume_generator.py`):**
```python
from unittest.mock import patch
from resume_generator import compile_latex_to_pdf

@patch('subprocess.run')
def test_compile_latex_to_pdf_success(mock_run):
    """Mock successful LaTeX compilation."""
    mock_run.return_value = MagicMock(returncode=0)

    # Should not raise exception
    compile_latex_to_pdf("/path/to/test.tex")
    mock_run.assert_called_once()

@patch('subprocess.run')
def test_compile_latex_to_pdf_command_not_found(mock_run):
    """Mock missing tectonic command."""
    mock_run.side_effect = FileNotFoundError("tectonic not found")

    with pytest.raises(FileNotFoundError):
        compile_latex_to_pdf("/path/to/test.tex")
```

**File I/O Mocking (for `src/config.py`):**
```python
from unittest.mock import mock_open, patch
from config import Config

@patch('builtins.open', new_callable=mock_open, read_data="llm:\n  ollama_url: http://localhost:11434\n")
@patch('yaml.safe_load')
def test_config_loads_yaml(mock_yaml_load, mock_file):
    """Mock YAML configuration loading."""
    mock_yaml_load.return_value = {
        'llm': {'ollama_url': 'http://localhost:11434', 'model_id': 'llama3.1:8b'}
    }

    config = Config()
    assert config.ollama_url == 'http://localhost:11434'
```

### What to Mock vs. What to Test

**What to Mock:**
- External API calls (`requests` library calls to Ollama)
- Subprocess execution (LaTeX compilation, docx2pdf conversion)
- File system operations in unit tests
- External service availability checks
- DateTime/Time dependent logic (if added)

**What NOT to Mock:**
- Configuration loading from `config.yaml` (test with fixture config file)
- Logger output (test that logger is called, not what it logs)
- Core business logic (prompt engineering, JSON parsing)
- Error handling paths

### Fixtures and Test Data

**Suggested Fixture Pattern:**
```python
# tests/fixtures.py
import pytest

@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    Company: Acme Corp
    Position: Senior Python Developer
    Requirements: Python, FastAPI, PostgreSQL, Docker, AWS
    """

@pytest.fixture
def sample_jd_json():
    """Expected parsed structure from job description."""
    return {
        "company_name": "Acme Corp",
        "position": "Senior Python Developer",
        "requirements": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]
    }

@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test output files."""
    return tmp_path
```

**Fixture Location:** `tests/conftest.py` or `tests/fixtures.py`

## Coverage

**Target:** Not currently enforced

**Recommended Setup:**
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

**Suggested Coverage Target:** 70%+ for critical modules
- `src/llm.py`: 80%+ (core business logic)
- `src/config.py`: 90%+ (configuration validation)
- `src/logger.py`: 80%+ (logging setup)
- `src/main.py`: 60%+ (orchestration/integration)

## Test Types

**Unit Tests:**
- Scope: Individual functions in isolation
- Approach: Mock external dependencies (API calls, file I/O, subprocesses)
- Example: `test_parse_jd_to_json()` with mocked LLM response

**Integration Tests:**
- Scope: Multiple modules working together
- Approach: Real file I/O, mocked external services
- Example: Load config, parse job description, generate resume outline

**E2E Tests:**
- Status: Not automated
- Current approach: Manual testing with actual Ollama instance and PDF compilation
- Recommended tool if added: `pytest` with temporary directories

## Common Testing Patterns (Recommended)

**Async Testing:**
Not applicable - codebase uses synchronous operations

**Error Testing:**
```python
def test_parse_jd_to_json_with_invalid_json():
    """Test graceful handling of invalid LLM JSON response."""
    with patch('llm.prompt_ollama', return_value="invalid json"):
        result = parse_jd_to_json("test jd")
        assert result == {}  # Should return empty dict on failure

def test_check_dependencies_missing_ollama(monkeypatch):
    """Test dependency check when Ollama is missing."""
    monkeypatch.setattr('shutil.which', lambda x: None)

    with pytest.raises(SystemExit) as exc_info:
        check_dependencies()
    assert exc_info.value.code == 1
```

**Configuration Testing:**
```python
def test_config_property_access():
    """Test configuration property access."""
    from config import config

    # Assumes config.yaml exists
    assert config.model_id is not None
    assert config.ollama_url is not None
    assert isinstance(config.whitespace_threshold, float)
```

## Run Commands (Recommended)

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_llm.py

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/

# Run tests matching pattern
pytest tests/ -k "parse_jd"
```

## Critical Testing Gaps

**High Priority Test Areas:**
1. `src/llm.py`: Exception handling for Ollama API failures, JSON parsing edge cases
2. `src/main.py`: Dependency validation, command-line argument parsing, workflow orchestration
3. `src/config.py`: YAML loading, property access, missing configuration handling
4. `src/pdf_analyzer.py`: Whitespace calculation accuracy, PDF edge cases

**Current Risk:** Zero automated testing means all validation is manual. Any refactoring is high-risk without test coverage.

---

*Testing analysis: 2026-02-21*
