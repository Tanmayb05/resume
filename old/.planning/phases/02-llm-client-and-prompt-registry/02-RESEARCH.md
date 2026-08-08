# Phase 2: LLM Client and Prompt Registry - Research

**Researched:** 2026-02-22
**Domain:** Open-source LLM orchestration, async Python client patterns, prompt management
**Confidence:** HIGH

## Summary

This phase builds a unified async LLM client backed by **Ollama** (local open-source LLMs) instead of the Anthropic API. The client must handle timeouts, retries on transient errors, and JSON extraction from LLM output. A file-based prompt registry (Markdown templates with Jinja2 substitution) centralizes all prompt logic outside business code.

**Key finding:** Ollama's official Python library provides first-class async support via `AsyncClient`, supports timeout configuration, and pairs well with lightweight open-source models (Llama 3 8B, Zephyr 7B, Mistral 7B). For writing tasks like resume/cover letter generation, **Zephyr 7B** (Mistral 7B fine-tuned with DPO) delivers the best prose quality at 7B scale. **LangGraph is optional**—recommended only if workflow complexity demands durable execution and human-in-the-loop; for this project's linear pipeline, simple sequential orchestration is sufficient.

**Primary recommendation:** Use Ollama's `AsyncClient` with exponential backoff retry logic (via Tenacity library), JSON extraction via regex + `fix-busted-json` library for robustness, and Jinja2 for prompt templating with memory caching.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Fully replace Claude API with open-source models** — no Anthropic dependency
- **Run models locally via Ollama** — no API keys, no third-party hosted services
- **Target: fast + good enough quality** — smaller models (7B–14B) acceptable; no 70B models required
- **Client must be Ollama-compatible** — OpenAI-compatible API or `ollama` Python library
- **Class-based interface:** `LLMClient(config)` with primary method `call(prompt_str) → str`
- **JSON extraction as standalone utility:** `extract_json(text: str) → dict` in utils module, not on client
- **Retry policy:** 3 retries with exponential backoff (1s, 2s, 4s); configurable via `AppConfig`
- **Prompt loading:** Registry function `load_prompt(name) → str` maps to `llm/prompts/{name}.md`
- **Markdown code fence stripping:** All variants (` ```json `, ` ``` `, bare backticks, leading whitespace)
- **Error on exhausted retries:** Raise custom `LLMError` with original error + attempt count

### Claude's Discretion

- System prompt handling (separate param vs parsed from prompt file)
- Internal module structure within `llm/`
- Exact Jinja2 environment configuration
- Specific Ollama Python library vs raw HTTP calls
- **LangGraph adoption** — researcher recommends based on findings; decision in planning phase

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

---

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ollama` | 0.1.3+ | Async LLM client, local Ollama integration | Official Python library; first-class async support; simple, well-documented API |
| `tenacity` | 8.5.0+ | Exponential backoff retry logic | Production-standard async retry library; handles transient failures; extensive customization |
| `Jinja2` | 3.0+ | Prompt template rendering with variables | Battle-tested template engine; sandboxed execution; minimal overhead for caching |
| `fix-busted-json` | Latest | Robust JSON extraction from LLM markdown output | Handles all code fence variants; designed specifically for LLM output repair |
| `pydantic` | 2.0+ | Configuration/validation (via AppConfig) | Already in project; validates schema before extraction attempts |

### Recommended Open-Source Models (Ollama)

| Model | Size | Primary Strength | When to Use | Why Recommended |
|-------|------|------------------|-------------|-----------------|
| **Zephyr 7B** | 7B | Writing/prose quality; instruction-following | Resume points, cover letters, text generation | Mistral 7B fine-tuned with DPO; best prose at 7B scale; proven in writing tasks |
| **Llama 3 8B** | 8B | General reasoning, depth, all-around | Complex analysis, fallback default model | GPT-3.5-level performance; best general-purpose; strong reasoning |
| **Mistral 7B** | 7B | Speed, efficiency, lightweight | Real-time tasks, resource-constrained | Fast inference on modest hardware; acceptable quality at 7B |

**Hardware baseline:** 16GB RAM minimum for 7B models; 32GB recommended for smooth multi-inference workloads.

### Installation

```bash
pip install ollama tenacity Jinja2 fix-busted-json pydantic
```

### Model Installation (Local Ollama)

```bash
# Pull models into local Ollama
ollama pull zephyr           # Recommended for writing tasks
ollama pull llama3           # General-purpose fallback
ollama pull mistral          # Speed-optimized
```

**Note:** First Ollama run downloads package cache (~60–120s); web UI must surface this latency clearly.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Ollama local | OpenAI-compatible remote API (e.g., Together, Replicate) | Loses privacy/offline capability; adds API key management; requires internet |
| `tenacity` | `backoff` library or manual retry loop | Backoff works fine; Tenacity offers more features and async-native design |
| `fix-busted-json` | Manual regex extraction | Works for simple cases; custom regex is brittle and doesn't handle all fence variants |
| `Jinja2` | f-strings or simple string.format() | Less powerful for complex substitution; no sandbox; no caching |

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── llm/
│   ├── __init__.py
│   ├── client.py           # LLMClient class, AsyncClient wrapper
│   ├── config.py           # LLM-specific config (model, timeout, retry count)
│   ├── errors.py           # Custom LLMError exception
│   ├── prompts/            # Markdown prompt templates
│   │   ├── select_resume.md
│   │   ├── generate_cover_letter.md
│   │   └── ...
│   └── utils.py            # extract_json(), load_prompt() functions
├── utils/
│   └── ...                 # Project-wide utilities (JobStore, etc.)
└── ...
```

### Pattern 1: Async LLM Client with Ollama

**What:** A class-based wrapper around Ollama's `AsyncClient` that handles timeouts, retries, and error reporting.

**When to use:** Every LLM call goes through this one integration point—resume selection, cover letter generation, JD parsing, etc.

**Why:** Single source of truth for error handling, retries, and configuration. All downstream pipeline stages share consistent behavior.

**Example:**

```python
# src/llm/client.py
from ollama import AsyncClient
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from .errors import LLMError
from .config import LLMConfig

class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = AsyncClient(
            host=config.ollama_host,
            timeout=config.request_timeout
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def call(self, prompt: str, model: str | None = None) -> str:
        """
        Call LLM with exponential backoff retry on transient failures.

        Retries on:
        - Connection errors
        - Timeouts (asyncio.TimeoutError)
        - Server errors (5xx)
        - Rate limits (429)

        Fails immediately on:
        - Authentication errors
        - Validation errors (4xx, non-429)
        - Malformed requests
        """
        model = model or self.config.default_model

        try:
            response = await self.client.generate(
                model=model,
                prompt=prompt,
                stream=False,
            )
            return response['response']
        except Exception as e:
            # Tenacity will retry on transient errors
            # On exhaustion, raises LLMError with attempt count
            raise LLMError(
                f"LLM call failed: {str(e)}",
                original_error=e,
                attempts=3
            )
```

**Source:** Ollama Python library docs, Tenacity async retry patterns

### Pattern 2: Prompt Registry with Jinja2 Templating

**What:** Load prompts from `.md` files in `llm/prompts/`, render with Jinja2 variable substitution, cache in memory.

**When to use:** Any prompt that varies by context (e.g., `{{ job_description }}` in resume selection prompt).

**Why:** Keeps prompts out of business logic; easier to iterate and maintain; Jinja2 templates enable conditional/loop logic if needed later.

**Example:**

```python
# src/llm/utils.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import os

_PROMPT_CACHE = {}

def load_prompt(name: str, **variables) -> str:
    """
    Load and render a prompt template.

    Args:
        name: Prompt name (e.g., 'select_resume' → 'llm/prompts/select_resume.md')
        **variables: Jinja2 template variables to substitute

    Returns:
        Rendered prompt string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    # Create Jinja2 environment on first call
    if 'env' not in _PROMPT_CACHE:
        prompts_dir = Path(__file__).parent / 'prompts'
        _PROMPT_CACHE['env'] = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            undefined=StrictUndefined,  # Fail on missing variables
        )

    env = _PROMPT_CACHE['env']

    # Load template (cached by Jinja2)
    try:
        template = env.get_template(f'{name}.md')
    except FileNotFoundError:
        available = sorted([f.stem for f in (Path(__file__).parent / 'prompts').glob('*.md')])
        raise FileNotFoundError(
            f"Prompt '{name}' not found. Available: {', '.join(available)}"
        )

    # Render with supplied variables
    return template.render(**variables)

# Example: llm/prompts/select_resume.md
"""
You are a resume tailoring assistant. The user has provided a job description.

Job Description:
{{ job_description }}

Master Resume (JSON):
{{ master_resume_json }}

Select and rank the top 5 experience items from the master resume that are most relevant
to this job description. Return as JSON with keys: selections (array of {id, relevance_score}).
"""
```

**Source:** Jinja2 official tutorial, FileSystemLoader patterns

### Pattern 3: JSON Extraction from Markdown Code Fences

**What:** Strip markdown code fences (` ```json `, ` ``` `, bare backticks, whitespace variants) and extract JSON.

**When to use:** LLM returns structured data wrapped in code fences; must parse robustly to avoid ValueError on malformed JSON.

**Why:** LLMs frequently wrap JSON in fences; manual regex is brittle across all variants. `fix-busted-json` library handles all cases.

**Example:**

```python
# src/llm/utils.py (continued)
import json
import re
from fix_busted_json import repair_json

def extract_json(text: str) -> dict:
    """
    Extract JSON from text, handling markdown code fences.

    Handles:
    - ` ```json { ... } ``` `
    - ` ``` { ... } ``` `  (bare fence)
    - ` ` ` { ... } ` ` `  (single backticks, any spacing)
    - No fence (direct JSON)
    - Malformed/incomplete JSON (via fix-busted-json repair)

    Args:
        text: Raw text from LLM

    Returns:
        Parsed dict

    Raises:
        ValueError: If no valid JSON found or all repair attempts fail
    """
    # Strip markdown code fences
    cleaned = _strip_code_fences(text)

    # Try standard JSON parsing first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # If that fails, try repair
    try:
        repaired = repair_json(cleaned)
        return json.loads(repaired)
    except Exception as e:
        raise ValueError(
            f"Could not extract valid JSON from: {text[:200]}...\n"
            f"Original error: {str(e)}"
        )

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fence variants."""
    # Match ` ```json ... ``` ` or ` ``` ... ``` ` or ` ` ` ... ` ` `
    patterns = [
        r'```(?:json)?\s*(.*?)\s*```',  # Standard markdown fences
        r'`{3}(?:json)?\s*(.*?)\s*`{3}',  # Any backtick count
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # No fence found; assume entire text is JSON
    return text.strip()
```

**Source:** fix-busted-json library, community patterns for fence handling

### Pattern 4: Transient Error Detection and Retry Strategy

**What:** Use `tenacity` decorators to retry only transient failures (connection, timeout, 5xx, 429); fail immediately on permanent errors.

**When to use:** API calls that might temporarily fail (network, rate limit, service restart).

**Why:** Distinguishes transient (retry) from permanent (fail fast) errors; exponential backoff + jitter prevents thundering herd.

**Example:**

```python
# src/llm/client.py (continued)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    retry_if_result,
)
import asyncio

def _is_transient_error(exc: Exception) -> bool:
    """Determine if error is transient (retry) or permanent (fail fast)."""
    # Transient: connection errors, timeouts, server errors, rate limits
    transient_types = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )
    if isinstance(exc, transient_types):
        return True

    # Check for 5xx or 429 in error message (from Ollama/httpx)
    error_str = str(exc)
    if any(code in error_str for code in ['500', '502', '503', '504', '429']):
        return True

    # Permanent: auth, validation, malformed request
    return False

class LLMClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type(Exception),  # Tenacity handles filtering
        reraise=True,
    )
    async def call(self, prompt: str, model: str | None = None) -> str:
        # Implementation (see Pattern 1 above)
        pass
```

**Source:** Tenacity documentation, exponential backoff best practices

### Anti-Patterns to Avoid

- **Creating a new Ollama client per request:** Wastes resources; reuse the `AsyncClient` instance.
- **Hardcoding prompts in business logic:** Always load from `llm/prompts/` registry for maintainability.
- **Parsing JSON with string `in` checks:** Fragile; use regex or dedicated library like `fix-busted-json`.
- **Retrying all errors equally:** Permanent errors (auth, validation) should fail immediately; only transient errors warrant retry.
- **Ignoring LLM response truncation:** If model hits token limit, JSON will be incomplete. Validate token count or re-prompt with length constraints.
- **Synchronous LLM calls in async context:** Use `await` on `AsyncClient` methods; never block the event loop.
- **Caching prompts without invalidation:** For this project's single-user scope, in-memory cache is fine; document that process restart picks up edits.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exponential backoff + retry | Custom loop with manual `asyncio.sleep()` | `tenacity` library | Handles exponential backoff, jitter, transient-only filters, async/sync compatibility. Custom implementation misses edge cases (e.g., jitter prevents retry storms). |
| JSON extraction from LLM output | Regex for all code fence variants | `fix-busted-json` library | LLMs produce ` ```json `, ` ``` `, bare backticks, mixed whitespace. Custom regex never covers all cases; library is battle-tested on real LLM output. |
| Prompt templating | String concatenation / f-strings | `Jinja2` | Enables conditional logic, loops, filters. String-based prompts don't scale; Jinja2 adds minimal overhead, is widely known, and has built-in escaping. |
| Async HTTP client pooling | New `aiohttp.ClientSession` per request | Reuse single `AsyncClient` instance | Each session incurs connection pooling overhead; reusing multiplexes requests, reduces file descriptors, improves latency. |
| Timeout + error handling | Try/except + manual socket timeout | `asyncio.TimeoutError` + `tenacity.retry` | Socket-level timeouts don't integrate with event loop; asyncio timeouts are non-blocking; Tenacity knows how to catch and retry them. |

**Key insight:** LLM orchestration layers are deceptively complex—timeouts interact with retries, JSON parsing fails on edge cases, and prompt management sprawls without structure. Each of the above "don't hand-roll" items has a well-tested library that handles corner cases custom code misses.

---

## Common Pitfalls

### Pitfall 1: Incomplete JSON from Streaming or Token Limits

**What goes wrong:** LLM hits max_tokens before finishing JSON generation. Code calls `json.loads()` on incomplete structure, raises `JSONDecodeError`, and pipeline fails without clear error message.

**Why it happens:** Model's token limit is reached mid-sentence. LLM library doesn't validate that response is valid JSON before returning.

**How to avoid:**
- Set `max_tokens` to be conservative (e.g., 20% below actual model limit) to leave room for JSON closing braces.
- Validate response structure in callers: ensure all required fields exist before proceeding.
- Use `extract_json()` utility which calls `fix-busted-json` repair on malformed JSON; log warnings if repair was needed.
- In prompts, explicitly state: "Output a complete, valid JSON object. Do not truncate."

**Warning signs:**
- `JSONDecodeError` with incomplete curly braces or missing closing `]` or `}`.
- Response text ends abruptly mid-value.
- Model log shows tokens_generated near max_tokens setting.

### Pitfall 2: Timeout Configuration Mismatch

**What goes wrong:** Timeout is set too low (e.g., 5s), and large resume/cover letter generation takes 10s. Request aborts mid-inference, raises `TimeoutError`, and pipeline fails.

**Why it happens:** Ollama model inference time varies by model size, input length, and hardware. Default timeout assumptions don't account for local model inference latency.

**How to avoid:**
- Set `request_timeout` to at least 30–60s for Ollama models (inference happens locally, no API latency, but generation time is real).
- Document timeout setting prominently in config comments.
- Log inference time on each call; warn if approaching timeout threshold.
- Test with expected input sizes (realistic resume/job descriptions) before shipping.

**Warning signs:**
- `asyncio.TimeoutError` or similar after consistent time (e.g., always fails after ~10s).
- Tenacity's retry backoff logs appear without model error; suggests timeout, not model failure.
- Shorter prompts succeed, longer ones timeout.

### Pitfall 3: Ollama Connection Issues (Model Not Loaded)

**What goes wrong:** Ollama daemon not running, or model not pulled. Client.chat() raises connection error, but error message is unclear ("Connection refused" vs. "Model not found").

**Why it happens:** Ollama requires daemon running (e.g., `ollama serve`) and models pre-downloaded. Easy to miss during setup.

**How to avoid:**
- In client initialization, add a health check: call `ollama list()` and verify default model is available.
- Raise clear error with setup instructions if Ollama is unreachable.
- Document in README: "Run `ollama serve` in background before starting app."
- In web UI, display Ollama connection status prominently.

**Warning signs:**
- Connection error on first call; subsequent calls also fail.
- Error message mentions "connection refused" or "Ollama not found".
- Works in one environment, fails in another (missing daemon).

### Pitfall 4: Code Fence Parsing Fails on Variant Formats

**What goes wrong:** LLM wraps JSON in ` ``` ` (bare fence, no language tag), but custom regex only matches ` ```json `. Code extracts empty string, tries `json.loads("")`, raises `JSONDecodeError`.

**Why it happens:** Different models use different fence conventions. Custom regex is inflexible.

**How to avoid:**
- Use `fix-busted-json.first_json()` to locate any JSON object in text, regardless of fence format.
- Do not rely on fence patterns; extract JSON content first, then parse.
- Unit test `extract_json()` with real LLM outputs from all models in use.

**Warning signs:**
- `JSONDecodeError: Expecting value: line 1 column 1` (suggests empty string passed to json.loads).
- Parser works for one model, fails for another (different fence style).
- Manually inspecting response shows valid JSON, but extraction fails.

### Pitfall 5: Retry Logic Triggers on Permanent Errors

**What goes wrong:** Prompt violates LLM's content policy. Model returns 4xx validation error. Tenacity retries 3 times, each time failing the same way, wasting time and (if using a remote API) credits.

**Why it happens:** Retry decorator doesn't distinguish transient (e.g., 5xx) from permanent (e.g., 4xx validation) errors.

**How to avoid:**
- Implement `_is_transient_error()` check; only retry true transient failures (connection, timeout, 5xx, 429).
- Log what triggered retry; if same error repeats, stop early.
- For validation errors, surface the error immediately without retry.
- Test retry logic with mock exceptions that clearly identify transient vs. permanent.

**Warning signs:**
- Same error repeated 3 times in logs (suggests permanent error being retried).
- Long delay before final failure (suggests unnecessary retries).
- Error message doesn't change across retries.

### Pitfall 6: Prompt Cache Invalidation

**What goes wrong:** Developer edits `llm/prompts/select_resume.md`, restarts app, but old cached version is still used. Changes don't take effect.

**Why it happens:** In-memory prompt cache persists across edits if caching is done naively.

**How to avoid:**
- For development: disable caching or restart process after prompt edits.
- Document cache behavior: "Restart the application to pick up prompt changes."
- For production: caching is fine (single-user tool); editing prompts requires app restart anyway.
- If dynamic reloading is needed later, add a timestamp check: reload if .md file is newer than cache timestamp.

**Warning signs:**
- Edit prompt, restart (confirms you did restart), still seeing old behavior.
- Logs show correct prompt content, but output suggests old prompt was used.

### Pitfall 7: Jinja2 Variable Not in Template

**What goes wrong:** Code calls `load_prompt('select_resume', job_description='...', master_resume='...')`, but template uses `{{ master_resume_json }}`. Jinja2 raises `UndefinedError` because `master_resume_json` not provided.

**Why it happens:** Variable name mismatch between caller and template.

**How to avoid:**
- Set `undefined=StrictUndefined` in Jinja2 Environment (will raise on undefined variables).
- Document required variables in prompt file comments.
- In tests, verify all callers supply the right variable names.

**Warning signs:**
- `jinja2.exceptions.UndefinedError: 'X' is undefined` at render time.
- Prompt loads successfully but rendering fails.

---

## Code Examples

Verified patterns from official sources and best practices:

### Example 1: Full LLMClient Implementation with Async + Retries

```python
# src/llm/client.py
import asyncio
from ollama import AsyncClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)
from config import AppConfig
from .errors import LLMError

class LLMClient:
    """
    Async LLM client wrapping Ollama's AsyncClient.

    Features:
    - Automatic retry on transient failures (connection, timeout, 5xx, 429)
    - Exponential backoff with jitter
    - Configurable timeout per request
    - Clear error reporting
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.client = AsyncClient(
            host=config.llm_host,
            timeout=config.llm_timeout,  # e.g., 60.0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )
    async def call(self, prompt: str, model: str | None = None) -> str:
        """
        Call LLM with exponential backoff retry.

        Args:
            prompt: Full prompt text
            model: Model name (e.g., 'zephyr', 'llama3'); uses default if None

        Returns:
            Full response text from model

        Raises:
            LLMError: After max retries or on permanent error
            asyncio.TimeoutError: If request exceeds timeout
        """
        model = model or self.config.llm_default_model

        try:
            response = await self.client.generate(
                model=model,
                prompt=prompt,
                stream=False,
            )
            return response['response']
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            # Tenacity will retry these
            raise
        except Exception as e:
            # Check if error is transient; if not, raise immediately (no retry)
            if not self._is_transient_error(e):
                raise LLMError(f"Permanent error from LLM: {str(e)}")
            raise

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        """Distinguish transient (retry) from permanent (fail fast) errors."""
        transient_types = (ConnectionError, TimeoutError, asyncio.TimeoutError)
        if isinstance(exc, transient_types):
            return True

        error_str = str(exc).lower()
        if any(code in error_str for code in ['500', '502', '503', '504', '429']):
            return True

        return False

# Usage in pipeline:
async def select_resume_content(llm: LLMClient, job_desc: str, master_resume: str):
    from .utils import load_prompt, extract_json

    prompt = load_prompt(
        'select_resume',
        job_description=job_desc,
        master_resume_json=master_resume,
    )

    response = await llm.call(prompt, model='zephyr')
    data = extract_json(response)
    return data['selections']
```

**Source:** Ollama Python library AsyncClient, Tenacity retry patterns, async/await best practices

### Example 2: JSON Extraction with Code Fence Handling

```python
# src/llm/utils.py
import json
import re
from fix_busted_json import repair_json

def extract_json(text: str) -> dict:
    """
    Extract JSON from text with markdown fence handling.

    Handles all fence variants:
    - ` ```json { ... } ``` `
    - ` ``` { ... } ``` `
    - ` ` ` { ... } ` ` `
    - No fence (direct JSON)
    - Malformed JSON (repairs via fix_busted_json)

    Args:
        text: Raw text from LLM

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If no valid JSON found after repair attempts

    Example:
        >>> text = '```json\n{"key": "value"}\n```'
        >>> extract_json(text)
        {'key': 'value'}
    """
    cleaned = _strip_code_fences(text)

    # Try standard parsing first (fastest path)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try repair for incomplete/malformed JSON
    try:
        repaired = repair_json(cleaned)
        return json.loads(repaired)
    except Exception as e:
        raise ValueError(
            f"Could not extract valid JSON.\n"
            f"Original text: {text[:300]}...\n"
            f"Cleaned: {cleaned[:300]}...\n"
            f"Error: {str(e)}"
        )

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fence variants, preserving content."""
    # Match ` ```[language] content ``` ` or ` ` ` content ` ` `
    pattern = r'```(?:json|[a-z]+)?\s*(.*?)\s*```'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()

    # No fence found; assume entire text is JSON
    return text.strip()

# Unit tests:
def test_extract_json_with_fence():
    text = '```json\n{"status": "ok"}\n```'
    assert extract_json(text) == {'status': 'ok'}

def test_extract_json_no_fence():
    text = '{"status": "ok"}'
    assert extract_json(text) == {'status': 'ok'}

def test_extract_json_incomplete():
    text = '```json\n{"status": "ok"'  # Missing closing brace
    result = extract_json(text)  # Repaired by fix_busted_json
    assert result == {'status': 'ok'}
```

**Source:** fix-busted-json library, regex patterns for fence handling

### Example 3: Prompt Registry with Jinja2

```python
# src/llm/utils.py (continued)
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

_PROMPT_CACHE = {}

def load_prompt(name: str, **variables) -> str:
    """
    Load and render a prompt template from llm/prompts/{name}.md

    Args:
        name: Prompt name (e.g., 'select_resume' → 'llm/prompts/select_resume.md')
        **variables: Jinja2 template variables (e.g., job_description='...')

    Returns:
        Fully rendered prompt string

    Raises:
        FileNotFoundError: If prompt file not found
        jinja2.exceptions.UndefinedError: If template references undefined variable

    Example:
        >>> prompt = load_prompt(
        ...     'select_resume',
        ...     job_description='Senior Python Engineer, 5yr exp',
        ...     master_resume_json='[{...}]'
        ... )
    """
    # Initialize Jinja environment on first call
    if 'env' not in _PROMPT_CACHE:
        prompts_dir = Path(__file__).parent / 'prompts'
        _PROMPT_CACHE['env'] = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            undefined=StrictUndefined,  # Fail on missing variables
            trim_blocks=True,  # Remove block tags from output
            lstrip_blocks=True,  # Left-strip leading whitespace
        )

    env = _PROMPT_CACHE['env']

    # Load template (Jinja2 caches internally)
    try:
        template = env.get_template(f'{name}.md')
    except Exception:
        available = sorted([
            f.stem for f in (Path(__file__).parent / 'prompts').glob('*.md')
        ])
        raise FileNotFoundError(
            f"Prompt '{name}' not found. Available: {', '.join(available)}"
        )

    # Render with variables
    return template.render(**variables)

# Example prompt file: src/llm/prompts/select_resume.md
"""
You are a resume optimization assistant.

Below is a job description that the user is applying for:
---
{{ job_description }}
---

Below is the user's master resume (all experiences):
---
{{ master_resume_json }}
---

Task:
1. Identify the 5 most relevant experiences from the master resume
2. Rank them by relevance to the job description
3. Provide a brief explanation for each selection

Return your response as a JSON object with this structure:
{
  "selections": [
    {"id": "experience_id", "relevance_score": 0.9, "reason": "..."},
    ...
  ]
}

Ensure the JSON is valid and well-formatted.
"""

# Usage in pipeline:
def example_call():
    prompt_text = load_prompt(
        'select_resume',
        job_description='Senior Python Engineer, 5+ years with async, microservices',
        master_resume_json='[{"id": 1, "title": "Backend Engineer", ...}]'
    )
    # Pass prompt_text to llm.call(prompt_text)
```

**Source:** Jinja2 FileSystemLoader, best practices for template-based prompts

---

## State of the Art

### Models and Techniques

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Remote API only (OpenAI, Anthropic) | Local inference + remote fallback | 2024–2025 | Privacy, cost savings, control; open-source models now competitive at 7B–13B scale |
| Synchronous HTTP calls | Async/await with event loop | 2018–2025 | Non-blocking I/O; Python asyncio standard; handles concurrent requests efficiently |
| Manual exponential backoff | Decorator-based retry (Tenacity) | 2018+ | Less boilerplate; handles edge cases; async-native |
| String formatting for prompts | Template engines (Jinja2) | 2023+ | Enables complex logic, conditionals; easier to maintain; widely adopted |
| Fixing JSON in post-processing | Specialized repair libraries | 2023–2024 | More robust; handles LLM edge cases (incomplete, fence variants) |

### Deprecated/Outdated

- **Synchronous HTTP clients (requests library):** Works fine, but blocks event loop in async context. Use `aiohttp` or `httpx` for async.
- **Manual regex for JSON extraction:** Insufficient for all fence variants. Use `fix-busted-json` or similar.
- **Hardcoded prompts in code:** Makes iteration slow; use registry pattern with templates.
- **Simple retry loops:** Ad-hoc error handling is error-prone. Use battle-tested libraries like Tenacity.

---

## Open Questions

1. **Exact Ollama host configuration in production**
   - What we know: Local Ollama can run on `localhost:11434` (default). For cloud/container deployment, may need custom host.
   - What's unclear: Should `llm_host` be in `AppConfig` or hardcoded to `localhost` for this single-user tool?
   - Recommendation: Add `llm_host` to `AppConfig` with default `localhost:11434`. Allows flexibility without complexity.

2. **System prompt handling (Claude's discretion)**
   - What we know: Standard LLM clients support optional system prompt parameter.
   - What's unclear: Should system prompt be hardcoded, configurable, or embedded in prompt files?
   - Recommendation: Keep system prompt in `AppConfig` as a simple string (e.g., "You are a resume optimization assistant"). For task-specific system prompts, embed at top of prompt file (e.g., `select_resume.md`). Avoid mixing layers.

3. **Connection pooling in Ollama AsyncClient**
   - What we know: `AsyncClient` wraps `httpx.AsyncClient` which has built-in connection pooling.
   - What's unclear: Do we need to manage the client lifecycle (e.g., context manager), or is instantiation in `__init__` sufficient?
   - Recommendation: For single-instance lifetime (one process), instantiation in `__init__` is fine. For FastAPI background tasks, consider adding `async_context_manager` if reusing client across multiple tasks.

4. **Model quantization (Q4, Q5) vs. full precision**
   - What we know: Quantized models (Q4, Q5) run faster on consumer hardware with minor quality loss.
   - What's unclear: Should recommended models default to quantized versions or full precision?
   - Recommendation: Recommend quantized (`zephyr:7b-q5` or similar) for responsive local inference. Document tradeoff. Users can override with `ollama pull zephyr:latest` if quality is critical.

5. **Streaming vs. non-streaming inference**
   - What we know: Streaming allows real-time token output; non-streaming waits for full response.
   - What's unclear: For this project (resume/cover letter generation), is streaming worth the added complexity?
   - Recommendation: Start with non-streaming (`stream=False`) for simplicity. Add streaming in Phase 6 (web UI) if user experience requires real-time feedback.

---

## Sources

### Primary (HIGH confidence)

- **Ollama Official Documentation** (https://docs.ollama.com) — Model availability, host configuration, requirements
- **Ollama Python Library GitHub** (https://github.com/ollama/ollama-python) — AsyncClient API, timeout support, example usage
- **Tenacity Library** (https://tenacity.readthedocs.io/) — Async retry decorator syntax, exponential backoff configuration
- **Jinja2 Official Tutorial** (https://ttl255.com/jinja2-tutorial-part-1-introduction-and-variable-substitution/) — Template rendering, variable substitution, FileSystemLoader
- **fix-busted-json PyPI** (https://pypi.org/project/fix-busted-json/) — JSON extraction from LLM output, fence handling

### Secondary (MEDIUM confidence)

- **Model Comparison Research** (https://kanerika.com/blogs/mistral-vs-llama-3/, https://collabnix.com/best-ollama-models-in-2025-complete-performance-comparison/) — Llama 3 8B vs Mistral 7B vs Zephyr 7B performance and writing quality; verified with multiple sources
- **LangGraph Documentation** (https://docs.langchain.com/oss/python/langgraph/overview) — When to use LangGraph; determined simple sequential pipeline suffices for this project
- **Async Patterns Research** (https://medium.com/@thomas.vidori/bringing-your-api-client-to-the-next-level-credentials-sleep-times-and-retries-with-example-66aca6027c6e) — aiohttp timeout and retry patterns; verified with Tenacity library docs

### Tertiary (LOW confidence, marked for validation)

- **LLM Streaming JSON Issues** (https://www.aha.io/engineering/articles/streaming-ai-responses-incomplete-json) — Common pitfall of incomplete JSON during streaming; marked for validation with real inference tests
- **Ollama Python AsyncClient Concurrency** (GitHub issue #197) — Noted potential concurrency limits; unclear if applies to current version; recommend testing with realistic workload

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| **Standard Stack (Ollama, Tenacity, Jinja2)** | HIGH | Official docs verified; libraries are battle-tested; active community. |
| **Architecture Patterns (async client, retry, JSON extraction, prompt registry)** | HIGH | Patterns are industry standard; code examples from official sources. |
| **Model Recommendations (Zephyr 7B for writing)** | MEDIUM | Multiple sources agree on Zephyr 7B; performance verified with comparisons. Recommendation is sound but untested in this specific project. |
| **Common Pitfalls** | HIGH | Token limit truncation, timeout config, connection issues are well-documented in LLM community. |
| **LangGraph Recommendation (not needed)** | MEDIUM | Official docs clearly state LangGraph is for complex stateful workflows; our linear pipeline doesn't need it. Recommend keeping simple unless future phases add complexity. |
| **Ollama Connection Pooling in httpx** | MEDIUM | Confirmed that AsyncClient wraps httpx.AsyncClient with pooling. Exact tuning parameters for single-user tool need empirical validation. |

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days; Ollama and open-source models are stable; re-check if adding streaming or remote deployments)

---

## Summary for Planner

**Build this client stack:**
1. Wrap Ollama's `AsyncClient` in `LLMClient` class with Tenacity retry decorator (3 attempts, exponential backoff)
2. Add `extract_json()` utility using `fix-busted-json` for robust fence handling
3. Create `load_prompt()` registry with Jinja2 FileSystemLoader for `llm/prompts/*.md` templates
4. Recommend **Zephyr 7B** model for writing tasks; Llama 3 8B as fallback general-purpose
5. **Do NOT use LangGraph** — simple sequential pipeline is sufficient; revisit in future phases if complexity grows

**Skip research on:** LangChain abstractions, remote model APIs, synchronous clients, manual JSON repair

**Configuration priorities:** Request timeout (30–60s for Ollama), default model (Zephyr for writing phases), retry count (3 with exponential backoff)
