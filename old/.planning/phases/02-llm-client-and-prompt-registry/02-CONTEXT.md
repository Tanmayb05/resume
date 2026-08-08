# Phase 2: LLM Client and Prompt Registry - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

A single async LLM client (`llm/client.py`) and a file-based prompt registry (`llm/prompts/`) that all downstream pipeline stages share. Every phase that calls the LLM goes through this one integration point. Prompt content lives in `.md` files — nothing is hardcoded in business logic.

This phase also decides whether LangGraph is the right orchestration layer (researcher evaluates and recommends).

</domain>

<decisions>
## Implementation Decisions

### LLM Provider
- **Fully replace Claude API with open-source models** — no Anthropic dependency
- Run models **locally via Ollama** — no API keys, no third-party hosted services
- Target: **fast + good enough** quality — smaller models (e.g., Llama 3 8B, Mistral 7B) are acceptable
- The client must be Ollama-compatible (OpenAI-compatible API or `ollama` Python library)

### Model Selection for Writing Tasks
- Writing tasks (resume points, cover letter generation) need models with strong prose quality
- Researcher should recommend 1-2 specific open-source models optimized for writing that run well locally
- "Fast + good enough" means: acceptable quality at 7B–14B parameter scale; no need for 70B models

### LangGraph Evaluation
- **Research it and recommend** — don't commit yet
- Researcher should evaluate: does LangGraph add value over a simple sequential pipeline for this project?
- If LangGraph fits, planner includes it; if not, planner keeps a simple client + orchestration layer
- Decision to be made in planning, based on research findings

### Caller Interface
- Class-based: `LLMClient(config)` — callers instantiate or inject for testability
- Primary method: `call(prompt_str) → str` — returns raw text; JSON extraction is the caller's responsibility
- Model: `AppConfig` provides default model; `call(prompt, model=None)` allows per-call override
- System prompt handling: Claude's discretion (kept flexible for downstream)

### JSON Extraction
- Standalone utility function: `extract_json(text: str) → dict` lives in a utils module, not on the client
- Failure behavior: raises `ValueError` with the raw text included — failure is always explicit
- No schema validation in the utility — callers (pipeline stages) validate shape themselves
- Handles all common fence variants: ` ```json `, ` ``` `, bare backticks, leading/trailing whitespace

### Error and Retry Behavior
- Exhausted retries raise a custom `LLMError` exception (includes original error + attempt count)
- 3 retries with exponential backoff: 1s, 2s, 4s delays; max retries configurable via `AppConfig`
- Transient-only retry policy: retry on connection errors and timeouts; fail immediately on auth/validation errors
- `asyncio.TimeoutError` is retryable — wraps in `LLMError` after max retries

### Prompt Loading
- Registry function: `load_prompt("select_resume") → str` — name maps to `llm/prompts/select_resume.md`
- Variable substitution: Jinja2 templating (`{{ variable }}` syntax in prompt files)
- Missing prompt: `FileNotFoundError` with helpful message listing available prompts
- Caching: prompts cached in memory after first read (dict cache); restart process to pick up edits

### Claude's Discretion
- System prompt handling (separate param vs parsed from prompt file)
- Internal module structure within `llm/`
- Exact Jinja2 environment configuration
- Specific Ollama Python library vs raw HTTP calls
- LangGraph adoption (based on researcher recommendation)

</decisions>

<specifics>
## Specific Ideas

- "I want to use open-source LLMs to do this" — Ollama locally, no external API dependency
- Writing tasks (resume points, cover letter) need a model with good prose — researcher should surface the best options at 7B–14B scale
- LangGraph interest is exploratory — let the research drive the decision

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-llm-client-and-prompt-registry*
*Context gathered: 2026-02-22*
