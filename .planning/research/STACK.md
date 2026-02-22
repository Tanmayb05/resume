# Technology Stack

**Project:** Job Hunt Assistant Web App
**Researched:** 2026-02-21
**Overall Confidence:** MEDIUM

---

## Recommended Stack

### Core Backend Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | ^0.115 | HTTP API backend (Python) | Auto-generates OpenAPI docs, native async support for LLM streaming, type-safe request/response with Pydantic, lighter than Django for a single-user tool. Flask lacks native async. FastAPI is the de-facto standard for new Python APIs in 2025/2026. |
| Uvicorn | ^0.32 | ASGI server | FastAPI's canonical server. Single command startup, no nginx/gunicorn needed for a personal single-user tool. |
| Pydantic | ^2.9 | Data validation | FastAPI v0.100+ bundles Pydantic v2. Use for API request/response schemas. |

**Why not Flask:** Synchronous by default. Resume generation involves subprocess calls (tectonic, 5-10s) and LLM calls (2-30s). FastAPI's async keeps the server responsive.

**Why not Django:** Massively over-engineered for a single-user personal tool.

### Frontend / Web UI

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| HTMX | ^2.0 | Hypermedia-driven interactivity | Zero JS build toolchain. Browser fetches HTML partials from FastAPI endpoints. Works with SSE for streaming LLM output. |
| Jinja2 | ^3.1 | Server-side HTML templating | Native to FastAPI. Generates HTML that HTMX swaps in. |
| Tailwind CSS (CDN) | ^3.4 | Utility CSS styling | Play CDN version (one script tag) means zero build step. Sufficient for a personal tool. |

**Why not React/Vue/Svelte:** npm + bundler + CORS config for no benefit over HTMX for a single-user tool.

### LLM Integration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `anthropic` Python SDK | ^0.40 | Claude API for AI content generation | Claude produces higher quality structured JSON and LaTeX than local Ollama models. Existing experiments with llama3.1:8b have documented bugs: inconsistent JSON formatting, markdown fence variations, empty responses. Claude's structured output is deterministic. |
| `openai` Python SDK | ^1.55 | Alternative LLM provider | Document as alternative. Abstract behind an LLM interface. |

**LLM abstraction pattern:**
```python
async def generate_json(prompt: str, system: str) -> dict:
    """Swappable backend: Claude or OpenAI."""
    ...
```

### LaTeX Compilation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| tectonic | latest (CLI) | LaTeX → PDF compilation | Already validated in experiments. Self-contained, downloads packages on first use, no TeX Live needed. |
| PyMuPDF (`fitz`) | ^1.25 | PDF page count detection | Use for overflow detection: compile → check page count (`len(fitz.open(pdf)) > 1`) → shorten bullets → recompile. Page count is a binary, reliable signal. |

**Critical improvement:** Replace whitespace-percentage with page count check. `len(fitz.open(pdf_path)) > 1` is reliable. Whitespace % is a fragile heuristic.

### Data Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Filesystem (JSON files) | N/A | Job application records | Each application is a directory in `data/{company_name}/`. Correct for a single-user tool — inspectable, no database needed. |
| `pathlib` (stdlib) | Python 3.12+ | Path manipulation | Replace all `os.path.join()` with `pathlib.Path`. Cleaner API. |

**When to add SQLite:** Add when job tracker needs cross-application queries (e.g., "show all interviews"). Not before.

### Configuration Management

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pydantic-settings` | ^2.6 | Config via .env file | Validates all config at startup with clear error messages. Fixes "missing key → cryptic KeyError" issue. Standard for FastAPI apps. |

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    anthropic_api_key: str
    llm_model: str = "claude-haiku-4-5-20251001"
    tectonic_path: str = "tectonic"
    data_dir: Path = Path("data")
    templates_dir: Path = Path("templates")
    max_compile_iterations: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
```

### HTTP Client

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `httpx` | ^0.28 | Async HTTP for URL scraping and LLM API | Replaces `requests`. Identical API surface, async-native. |
| `beautifulsoup4` | ^4.12 | HTML parsing for URL-scraped job descriptions | Lightweight. Extract job description text from arbitrary HTML. |
| `lxml` | ^5.3 | HTML parsing backend for BeautifulSoup | Faster than Python's html.parser for large job pages. |

---

## What NOT to Use

| Category | Avoid | Reason |
|----------|-------|--------|
| Frontend framework | React, Vue, Svelte | npm + bundler + CORS; no benefit for single-user tool |
| ORM | SQLAlchemy | No relational DB needed for MVP |
| Background queue | Celery, Redis | FastAPI BackgroundTasks + async subprocess sufficient |
| Authentication | JWT, OAuth | Single user, no auth needed |
| Cover letter pipeline | python-docx + LibreOffice | Fragile, platform-dependent. Replace: generate cover letter as formatted text in the web UI. |
| Local LLM (production) | Ollama + llama3.1:8b | Inconsistent JSON/LaTeX output causes documented bug classes. |

---

## requirements.txt

```
# Web framework
fastapi>=0.115.0
uvicorn>=0.32.0
python-multipart>=0.0.18
jinja2>=3.1.0
aiofiles>=24.1.0

# Configuration
pydantic-settings>=2.6.0

# LLM
anthropic>=0.40.0

# HTTP client
httpx>=0.28.0
beautifulsoup4>=4.12.0
lxml>=5.3.0

# PDF analysis
PyMuPDF>=1.25.0

# Env
python-dotenv>=1.0.0
```

## External CLI Tools

```
tectonic    # brew install tectonic (macOS)
```

---

## Key Decisions

1. **FastAPI over Flask:** Async matters for 5-30s pipeline operations.
2. **HTMX over React:** Zero build toolchain. SSE handles progress streaming.
3. **Claude API over Ollama:** Documented Ollama bugs eliminated by Claude structured output.
4. **Keep tectonic:** Already validated. Self-contained.
5. **Page count over whitespace %:** Binary signal, reliable.
6. **pydantic-settings over config.yaml:** Startup validation with clear errors.
7. **Drop python-docx + LibreOffice for cover letters:** Most fragile component. Generate text in web UI instead.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| tectonic (LaTeX) | HIGH | Already validated in existing experiments |
| FastAPI + Uvicorn | HIGH | Standard Python web API stack in 2025/2026 |
| HTMX + Jinja2 | HIGH | HTMX 2.0 (2024), widely adopted pattern |
| Anthropic Claude API | HIGH | Known SDK; structured output reliability |
| PyMuPDF | HIGH | Already in use; page count approach reliable |
| pydantic-settings | HIGH | FastAPI ecosystem standard |
| Specific version numbers | LOW | Pin to minimum versions, let pip resolve latest compatible |
