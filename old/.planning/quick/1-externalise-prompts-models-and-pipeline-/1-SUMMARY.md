---
phase: quick
plan: 1
subsystem: configuration
tags: [prompts, config, refactor, llm, templates]
dependency_graph:
  requires: []
  provides:
    - templates/resume_generation_prompt.md
    - templates/jd_parser_prompt.md
    - templates/company_name_extractor_prompt.md
    - templates/resume_expansion_prompt.md
    - src/config.py (extended with pipeline knobs)
  affects:
    - src/llm.py
    - src/main.py
tech_stack:
  added: []
  patterns:
    - Prompt templates loaded via open() at call time (same as generate_cover_letter pattern)
    - AppConfig pydantic-settings as single config system replacing config.yaml + .env dual split
    - All behavioural knobs configurable via APP_ env prefix without touching Python source
key_files:
  created:
    - templates/resume_generation_prompt.md
    - templates/jd_parser_prompt.md
    - templates/company_name_extractor_prompt.md
    - templates/resume_expansion_prompt.md
  modified:
    - src/config.py
    - src/llm.py
    - src/main.py
    - .env.example
  deleted:
    - config.yaml
decisions:
  - config.yaml deleted entirely — all values now in AppConfig with APP_ env prefix (no dual config system)
  - Prompts loaded fresh on each invocation via open() — no caching, consistent with cover_letter_prompt pattern
  - expand_sections_default in AppConfig replaces hardcoded list in main.py
  - cover_letter_bullet_char and cover_letter_preamble_patterns in AppConfig replace hardcoded values in _clean_cover_letter
  - templates_dir field added to AppConfig replacing config.yaml paths.templates
metrics:
  duration: 3 min
  completed: "2026-02-25"
  tasks_completed: 3
  files_changed: 9
---

# Quick Task 1: Externalise Prompts, Models, and Pipeline Configuration — Summary

All hardcoded prompt strings extracted from src/llm.py into templates/*.md files, resume_generation_config.json rules wired into the generation prompt, pipeline knobs moved into pydantic-settings AppConfig, and config.yaml deleted in favour of a single APP_-prefixed environment variable config system.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create four prompt template files | 6c95faf | templates/resume_generation_prompt.md, jd_parser_prompt.md, company_name_extractor_prompt.md, resume_expansion_prompt.md |
| 2 | Extend AppConfig with new fields and delete config.yaml | 80e40ab | src/config.py, .env.example, config.yaml (deleted) |
| 3 | Rewrite src/llm.py prompt loading and fix src/main.py | 74d6eaf | src/llm.py, src/main.py |

## What Was Built

**Task 1 — Four prompt template files:**
- `templates/resume_generation_prompt.md` — resume writer instructions (CRITICAL REQUIREMENTS block + tailoring guidelines)
- `templates/jd_parser_prompt.md` — JD parsing agent instructions (static prefix before schema injection)
- `templates/company_name_extractor_prompt.md` — company name extraction instructions
- `templates/resume_expansion_prompt.md` — whitespace expansion sub-prompt with `{{SECTIONS}}` placeholder

**Task 2 — AppConfig extended:**
- `whitespace_threshold: float = 40.0` — migrated from config.yaml resume.whitespace_threshold
- `expand_sections_default: list[str] = ["WORK EXPERIENCE"]` — was hardcoded in main.py
- `cover_letter_bullet_char: str = "•"` — was hardcoded in _clean_cover_letter
- `cover_letter_preamble_patterns: list[str]` — was hardcoded in _clean_cover_letter
- `templates_dir: str = "templates"` — migrated from config.yaml paths.templates
- config.yaml deleted, .env.example updated with all new APP_ variables

**Task 3 — Prompt loading rewritten:**
- `parse_jd_to_json` — loads jd_parser_prompt.md at call time
- `generate_latex_resume` — loads resume_generation_config.json rules, resume_generation_prompt.md, and resume_expansion_prompt.md at call time
- `extract_company_name` — loads company_name_extractor_prompt.md at call time
- `_clean_cover_letter` — reads preamble_patterns and bullet_char from config (no hardcoded values)
- `main.py` — expand_sections uses config.expand_sections_default; all old config attribute names updated to AppConfig equivalents

## Verification Results

1. Template files: 5 .md files in templates/ (cover_letter + 4 new)
2. Config loads: `from src.config import AppConfig; AppConfig()` exits 0
3. config.yaml absent: confirmed deleted
4. Syntax clean: `python -m py_compile src/llm.py src/main.py` exits 0
5. No hardcoded prompts: `grep "You are an expert" src/llm.py` returns nothing
6. Config injection: `grep "resume_generation_config" src/llm.py` shows open() path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated legacy config attribute references in main.py**
- **Found during:** Task 3
- **Issue:** src/main.py used old config attribute names (config.ollama_url, config.templates_path, config.data_path, config.max_optimization_iterations) that no longer exist after config.yaml deletion — these were from the old YAML-based config object, not AppConfig
- **Fix:** Replaced all old attribute names with their AppConfig equivalents (config.llm_host for URL, config.templates_dir, config.data_dir, config.max_iterations)
- **Files modified:** src/main.py
- **Commit:** 74d6eaf

**2. [Rule 1 - Bug] Updated import in llm.py from old config module to AppConfig**
- **Found during:** Task 3
- **Issue:** src/llm.py imported `from config import config` which assumed a module-level config singleton — AppConfig is a class, not an instance
- **Fix:** Changed import to `from config import AppConfig` and added `config = AppConfig()` module-level instantiation; updated attribute names (model_id -> llm_default_model, ollama_url -> constructed from llm_host)
- **Files modified:** src/llm.py
- **Commit:** 74d6eaf

## Self-Check: PASSED

All created files verified:
- templates/resume_generation_prompt.md: FOUND
- templates/jd_parser_prompt.md: FOUND
- templates/company_name_extractor_prompt.md: FOUND
- templates/resume_expansion_prompt.md: FOUND
- src/config.py (extended): FOUND

All commits verified:
- 6c95faf: FOUND (feat(quick-1): create four prompt template files)
- 80e40ab: FOUND (feat(quick-1): extend AppConfig with pipeline knobs and delete config.yaml)
- 74d6eaf: FOUND (feat(quick-1): rewrite llm.py prompt loading and fix main.py config references)
