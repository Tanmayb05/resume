---
created: 2026-02-26T00:48:32.233Z
title: Externalise prompts, models, and pipeline configuration
area: tooling
files:
  - src/llm.py:59-69
  - src/llm.py:111-150
  - src/llm.py:177-185
  - src/llm.py:208-237
  - src/config.py:1-79
  - config.yaml:1-13
  - templates/resume_generation_config.json:1-22
  - templates/cover_letter_prompt.md
---

## Problem

Several prompts, config knobs, and behavioural settings are hardcoded inside Python source files, making them hard to tweak without touching code.

**Already externalised (good baseline):**
- `config.yaml` — Ollama URL, model_id, whitespace_threshold, max_optimization_iterations, template/data paths
- `src/config.py` (pydantic-settings) — llm_host, llm_default_model, llm_timeout_seconds, llm_max_retries (env / .env overridable)
- `templates/cover_letter_prompt.md` — cover letter system instructions (loaded at runtime in `generate_cover_letter`)
- `templates/job_description_schema.json` — JD extraction schema (loaded at runtime in `parse_jd_to_json`)
- `templates/resume_generation_config.json` — resume tailoring rules (exists but **not wired** into `generate_latex_resume`)

**Still hardcoded (needs externalising):**

1. **Resume generation prompt** (`src/llm.py:111-150`) — the full f-string prompt including CRITICAL REQUIREMENTS 1-6 and TAILORING GUIDELINES is inline Python. Should move to `templates/resume_generation_prompt.md` (same pattern as `cover_letter_prompt.md`).

2. **JD parser prompt** (`src/llm.py:59-69`) — the "You are an expert JSON parsing agent..." instruction is hardcoded in `parse_jd_to_json`. Should move to `templates/jd_parser_prompt.md`.

3. **Company name extraction prompt** (`src/llm.py:177-185`) — the "You are an expert at extracting information..." prompt is hardcoded in `extract_company_name`. Should move to `templates/company_name_extractor_prompt.md`.

4. **Expansion / section-fill prompt** (`src/llm.py:103-109`) — the whitespace expansion sub-prompt ("The previous version had too much whitespace...") is hardcoded. Should be a template variable or separate prompt file.

5. **Hardcoded section names** (`src/main.py:149`) — `expand_sections = ["WORK EXPERIENCE"]` is hardcoded. Should come from config or the resume generation config JSON.

6. **Post-processing / cleaning rules** (`src/llm.py:266-278`) — preamble regex patterns and bullet normalisation rules in `_clean_cover_letter` are hardcoded. These could live in config so they're adjustable without code changes.

7. **`resume_generation_config.json` is not actually used** — it exists in `templates/` but `generate_latex_resume` never reads it. Either wire it in or remove to avoid confusion.

8. **`config.yaml` vs `src/config.py` split** — there are two separate config systems. `config.yaml` is read by something (unclear), while `src/config.py` uses pydantic-settings for .env. These should be unified or clearly separated to avoid drift.

## Decisions

| # | Item | Decision |
|---|------|----------|
| 1-4 | Resume, JD parser, company extractor, expansion prompts | Separate `.md` file per prompt in `templates/` — same pattern as `cover_letter_prompt.md` |
| 5 | `expand_sections = ["WORK EXPERIENCE"]` in `main.py` | Add `expand_sections_default` to `config.yaml` under `resume:` |
| 6 | Cover letter cleaning rules (preamble regex, bullet char) | Move to `src/config.py` as pydantic fields |
| 7 | `resume_generation_config.json` (exists but unused) | Wire into `generate_latex_resume` — inject rules into prompt |
| 8 | Dual config systems (`config.yaml` + `src/config.py`) | Consolidate into `src/config.py` only — delete `config.yaml` |
| + | Per-task model | One global `llm_default_model` — no per-task model split |

## Solution

1. **Prompt files** — create `templates/resume_generation_prompt.md`, `templates/jd_parser_prompt.md`, `templates/company_name_extractor_prompt.md`, `templates/resume_expansion_prompt.md`. Load at runtime the same way `generate_cover_letter` loads `cover_letter_prompt.md`.
2. **Wire `resume_generation_config.json`** — read it in `generate_latex_resume` and inject the rules JSON block into the resume generation prompt.
3. **`src/config.py`** — add `expand_sections_default: list[str]`, `cover_letter_bullet_char: str`, `cover_letter_preamble_patterns: list[str]` fields. Remove `_clean_cover_letter` hardcoded constants.
4. **Delete `config.yaml`** — migrate all remaining values (Ollama URL, model_id, whitespace_threshold, max_optimization_iterations, template/data paths, expand_sections_default) into `src/config.py` pydantic fields with `APP_` env prefix. Update `.env.example`.
