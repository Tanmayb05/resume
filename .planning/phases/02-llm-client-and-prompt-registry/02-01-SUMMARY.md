---
phase: 02-llm-client-and-prompt-registry
plan: 01
subsystem: api
tags: [ollama, tenacity, pydantic, async, retry, llm]

# Dependency graph
requires:
  - phase: 01-storage-and-configuration
    provides: AppConfig with APP_ prefix env loading and data_dir field
provides:
  - AppConfig with four Ollama fields (llm_host, llm_default_model, llm_timeout_seconds, llm_max_retries)
  - LLMClient async wrapper over ollama.AsyncClient with Tenacity retry
  - LLMError custom exception with original_error and attempts attributes
  - _is_transient() classifier for transient vs permanent LLM errors
affects: [03-jd-parser, 04-resume-selection, 05-cover-letter, 06-api-layer]

# Tech tracking
tech-stack:
  added: [ollama>=0.1.3, tenacity>=8.5.0]
  patterns: [single integration point for all LLM calls, exponential backoff retry, fail-fast on permanent errors]

key-files:
  created:
    - src/llm/__init__.py
    - src/llm/errors.py
    - src/llm/client.py
  modified:
    - src/config.py
    - .env.example
    - requirements.txt

key-decisions:
  - "anthropic_api_key made optional (default=None) — Ollama replaces Anthropic; old .env files still load without error"
  - "llm_model renamed to llm_default_model — aligns with Ollama multi-model usage pattern"
  - "llm_timeout_seconds default lowered from 120s to 60s — local Ollama inference is faster than remote API"
  - "_is_transient() string-match approach — avoids brittle isinstance checks against Ollama library internals"
  - "LLMError wraps RetryError from Tenacity — callers see one consistent exception type regardless of failure mode"

patterns-established:
  - "All LLM calls go through LLMClient.call() — callers never construct ollama.AsyncClient directly"
  - "Permanent errors fail immediately; transient errors retry with exponential backoff (1s min, 8s max)"
  - "LLMError.__str__() always includes attempt count and original exception for actionable error logs"

requirements-completed: [RES-01, RES-04, RES-06, COV-01, COV-02, JD-02, JD-03]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 2 Plan 1: LLM Client and Config Summary

**Async Ollama LLMClient with Tenacity exponential-backoff retry, LLMError exception wrapping, and AppConfig extended with four Ollama fields replacing the deprecated Anthropic integration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T20:47:56Z
- **Completed:** 2026-02-22T20:49:34Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Extended AppConfig with llm_host, llm_default_model, llm_timeout_seconds, llm_max_retries; made anthropic_api_key optional so startup never fails when key is absent
- Created src/llm/errors.py with LLMError carrying original_error and attempts for actionable error messages
- Created src/llm/client.py with LLMClient wrapping ollama.AsyncClient, Tenacity retry on transient errors (connection/timeout/5xx/429), and immediate fail on permanent errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend AppConfig with Ollama fields and update .env.example** - `f343674` (feat)
2. **Task 2: Create LLMClient with Ollama AsyncClient and Tenacity retry** - `d156c85` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/config.py` - AppConfig updated: anthropic_api_key optional, llm_model->llm_default_model, added llm_host and llm_max_retries
- `.env.example` - Updated with Ollama config section, deprecated Anthropic key commented out
- `requirements.txt` - Added ollama>=0.1.3 and tenacity>=8.5.0
- `src/llm/__init__.py` - Package marker
- `src/llm/errors.py` - LLMError exception with original_error and attempts attributes
- `src/llm/client.py` - LLMClient with async call(), _is_transient() classifier, Tenacity retry with exponential backoff

## Decisions Made
- anthropic_api_key made optional (default=None): Ollama replaces Anthropic as LLM backend; keeping the field means existing .env files with the key still load without EnvironmentError
- llm_model renamed to llm_default_model: better communicates that callers can override per-call via model parameter
- Default timeout lowered from 120s to 60s: local Ollama inference is typically 10-60s, making 120s unnecessarily long
- _is_transient() uses string matching on error repr: avoids brittle isinstance checks against Ollama library internals that may change between versions
- LLMError wraps both RetryError and raw exceptions: ensures callers handle one exception type regardless of which failure path fires

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required beyond running `ollama serve` locally and pulling a model with `ollama pull zephyr`.

## Next Phase Readiness
- LLMClient is ready for use by all downstream pipeline stages (JD parser, resume selector, cover letter generator)
- All imports verified clean; LLMClient instantiates without requiring Ollama to be running
- Callers must `await client.call(prompt)` — the async interface is consistent throughout

---
*Phase: 02-llm-client-and-prompt-registry*
*Completed: 2026-02-22*
