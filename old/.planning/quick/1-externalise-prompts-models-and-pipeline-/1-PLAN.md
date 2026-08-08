---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - templates/resume_generation_prompt.md
  - templates/jd_parser_prompt.md
  - templates/company_name_extractor_prompt.md
  - templates/resume_expansion_prompt.md
  - src/config.py
  - src/llm.py
  - src/main.py
  - .env.example
  - config.yaml
autonomous: true
requirements: []

must_haves:
  truths:
    - "All four prompts live in templates/*.md files and are loaded at runtime from disk"
    - "resume_generation_config.json rules are injected into the resume generation prompt"
    - "expand_sections_default is read from config, not hardcoded in main.py"
    - "Cover letter cleaning rules (bullet_char, preamble_patterns) come from config fields"
    - "config.yaml is deleted; all its values are represented in src/config.py pydantic fields"
    - ".env.example documents all new APP_ variables"
  artifacts:
    - path: "templates/resume_generation_prompt.md"
      provides: "Resume generation system prompt"
    - path: "templates/jd_parser_prompt.md"
      provides: "JD parsing system prompt"
    - path: "templates/company_name_extractor_prompt.md"
      provides: "Company name extraction prompt"
    - path: "templates/resume_expansion_prompt.md"
      provides: "Whitespace expansion sub-prompt"
    - path: "src/config.py"
      provides: "All runtime config including new fields"
      contains: "expand_sections_default"
  key_links:
    - from: "src/llm.py:generate_latex_resume"
      to: "templates/resume_generation_prompt.md"
      via: "open() at call time, same pattern as generate_cover_letter"
    - from: "src/llm.py:generate_latex_resume"
      to: "templates/resume_generation_config.json"
      via: "open() + json.load(), rules JSON injected into prompt"
    - from: "src/main.py"
      to: "src/config.py:expand_sections_default"
      via: "config.expand_sections_default replaces hardcoded list"
---

<objective>
Externalise all hardcoded prompts in src/llm.py to templates/*.md files, wire resume_generation_config.json into the generation prompt, move config knobs (expand_sections, cover letter cleaning rules) into pydantic-settings AppConfig, and delete config.yaml by migrating its remaining values into src/config.py.

Purpose: Prompts and behavioural knobs are tweakable without touching Python source; one unified config system (APP_ env prefix) replaces the dual config.yaml + .env split.
Output: 4 new prompt template files, updated src/config.py, rewritten src/llm.py prompt loading, updated src/main.py, deleted config.yaml, updated .env.example.
</objective>

<execution_context>
@/Users/tanmaybhuskute/.claude/get-shit-done/workflows/execute-plan.md
@/Users/tanmaybhuskute/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/tanmaybhuskute/Documents/resume/src/llm.py
@/Users/tanmaybhuskute/Documents/resume/src/config.py
@/Users/tanmaybhuskute/Documents/resume/src/main.py
@/Users/tanmaybhuskute/Documents/resume/config.yaml
@/Users/tanmaybhuskute/Documents/resume/templates/cover_letter_prompt.md
@/Users/tanmaybhuskute/Documents/resume/templates/resume_generation_config.json
@/Users/tanmaybhuskute/Documents/resume/.env.example
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create four prompt template files</name>
  <files>
    templates/resume_generation_prompt.md
    templates/jd_parser_prompt.md
    templates/company_name_extractor_prompt.md
    templates/resume_expansion_prompt.md
  </files>
  <action>
Extract the hardcoded prompt strings from src/llm.py into four separate .md files. The runtime caller will inject dynamic values (jd_json, schema, jd_text, expand_sections) around the static template text — so the template files contain only the static instruction text, using the same convention as templates/cover_letter_prompt.md (plain prose, no Jinja variables needed since interpolation happens in Python f-strings around the loaded text).

templates/resume_generation_prompt.md — extract lines 111-150 of src/llm.py (the full system instructions block). Include everything from "You are an expert resume writer..." through the DO NOT list. Do NOT include the {job_description}, {resume_template}, or {expansion_prompt} placeholders — those are injected by the Python caller around the loaded template text. Structure the file so the instructions read as standalone guidance.

templates/jd_parser_prompt.md — extract the system instructions from parse_jd_to_json (lines 59-69). The static portion is: "You are an expert JSON parsing agent. Your task is to parse the following job description and extract the information into a JSON object that strictly follows this schema:" and the trailing "Respond with ONLY the JSON object, without any additional text, comments, or explanations." The schema JSON and jd_text are injected by the caller.

templates/company_name_extractor_prompt.md — extract the static instructions from extract_company_name (lines 177-185): "You are an expert at extracting information. Your task is to extract the company name from the following job description. Respond with ONLY the company name, without any additional text, comments, or explanations." The jd_text is injected by the caller.

templates/resume_expansion_prompt.md — extract the expansion sub-prompt from generate_latex_resume (lines 103-109): "The previous version of the resume had too much whitespace. Please expand the following sections to add more content and fill the page: {sections_placeholder}. When expanding, add more details and accomplishments, but do not add new sections or change the overall structure." Use a literal placeholder like {{SECTIONS}} or leave a note that the Python caller appends the section list.
  </action>
  <verify>
    ls -la /Users/tanmaybhuskute/Documents/resume/templates/*.md
    # Expect 5 files: cover_letter_prompt.md plus the 4 new ones
  </verify>
  <done>Four .md files exist in templates/. Each contains the static prompt text extracted from src/llm.py with no Python code.</done>
</task>

<task type="auto">
  <name>Task 2: Extend AppConfig with new fields and delete config.yaml</name>
  <files>
    src/config.py
    .env.example
    config.yaml
  </files>
  <action>
Add the following new pydantic fields to AppConfig in src/config.py. Insert them in logical groups after existing fields:

```python
# Resume pipeline settings (migrate from config.yaml resume: block)
whitespace_threshold: float = Field(
    default=40.0,
    ge=0.0,
    le=100.0,
    description="Whitespace percentage above which resume expansion is triggered",
)
expand_sections_default: list[str] = Field(
    default=["WORK EXPERIENCE"],
    description="Section names passed to the LLM when whitespace expansion is needed",
)

# Cover letter post-processing (was hardcoded in _clean_cover_letter)
cover_letter_bullet_char: str = Field(
    default="•",
    description="Character to use for bullet points in cover letters (replaces asterisks)",
)
cover_letter_preamble_patterns: list[str] = Field(
    default=[r"^.*?(?=Dear\s+Hiring)"],
    description="Regex patterns to strip LLM preamble text before the salutation",
)

# Path settings (migrate from config.yaml paths: block — kept as str defaults)
templates_dir: str = Field(
    default="templates",
    description="Directory containing prompt templates and LaTeX templates",
)
```

Note: data_dir already exists in AppConfig. templates_dir is the replacement for config.yaml's paths.templates. The old config.yaml also had llm.ollama_url and llm.model_id — these are already covered by llm_host and llm_default_model in AppConfig (llm_host is the base URL; callers append /api/generate). Do NOT add a duplicate ollama_url field.

After updating src/config.py, update .env.example to document the new variables:

```
# Resume pipeline
APP_WHITESPACE_THRESHOLD=40.0
APP_EXPAND_SECTIONS_DEFAULT=["WORK EXPERIENCE"]

# Cover letter cleaning
APP_COVER_LETTER_BULLET_CHAR=•
# APP_COVER_LETTER_PREAMBLE_PATTERNS=["^.*?(?=Dear\\s+Hiring)"]

# Paths
APP_TEMPLATES_DIR=templates
```

Then delete config.yaml — it is fully superseded by src/config.py:
```bash
rm /Users/tanmaybhuskute/Documents/resume/config.yaml
```

Verify AppConfig loads cleanly after the change by running a quick import check:
```bash
cd /Users/tanmaybhuskute/Documents/resume && python -c "from src.config import AppConfig; c = AppConfig(); print(c.expand_sections_default)"
```
  </action>
  <verify>
    cd /Users/tanmaybhuskute/Documents/resume && python -c "from src.config import AppConfig; c = AppConfig(); print('whitespace_threshold:', c.whitespace_threshold); print('expand_sections_default:', c.expand_sections_default); print('cover_letter_bullet_char:', c.cover_letter_bullet_char)"
    ls /Users/tanmaybhuskute/Documents/resume/config.yaml 2>/dev/null && echo "ERROR: config.yaml still exists" || echo "OK: config.yaml deleted"
  </verify>
  <done>AppConfig imports without error, new fields return their defaults, config.yaml is absent from the repo, .env.example documents all new APP_ variables.</done>
</task>

<task type="auto">
  <name>Task 3: Rewrite src/llm.py prompt loading and fix src/main.py</name>
  <files>
    src/llm.py
    src/main.py
  </files>
  <action>
Rewrite src/llm.py to load each prompt from its template file at runtime, and wire in resume_generation_config.json. Follow the exact same open()-at-call-time pattern already used in generate_cover_letter (lines 208-215) — do NOT cache; load fresh on each invocation.

**parse_jd_to_json:** Replace the hardcoded prompt f-string with:
```python
template_path = "templates/jd_parser_prompt.md"
with open(template_path) as f:
    system_instructions = f.read()

prompt = f"""
{system_instructions}
{schema}

Job Description:
---
{jd_text}
---

Respond with ONLY the JSON object, without any additional text, comments, or explanations.
"""
```

**extract_company_name:** Replace hardcoded prompt with:
```python
template_path = "templates/company_name_extractor_prompt.md"
with open(template_path) as f:
    system_instructions = f.read()

prompt = f"""
{system_instructions}

Job Description:
---
{jd_text}
---
"""
```

**generate_latex_resume:** Replace both the expansion sub-prompt and the main prompt with file-loaded versions:
```python
# Load resume generation config rules
config_path = "templates/resume_generation_config.json"
with open(config_path) as f:
    resume_config = json.load(f)
rules_json = json.dumps(resume_config, indent=2)

# Build expansion sub-prompt if needed
expansion_prompt = ""
if expand_sections:
    exp_template_path = "templates/resume_expansion_prompt.md"
    with open(exp_template_path) as f:
        exp_template = f.read()
    # Replace placeholder with actual section list
    sections_str = ', '.join(expand_sections)
    expansion_prompt = exp_template.replace("{{SECTIONS}}", sections_str)

# Load main generation prompt
template_path = "templates/resume_generation_prompt.md"
with open(template_path) as f:
    system_instructions = f.read()

prompt = f"""
{system_instructions}

Tailoring rules to apply:
<tailoring_rules>
{rules_json}
</tailoring_rules>

Here is the structured Job Description:
<job_description>
{json.dumps(jd_json, indent=2)}
</job_description>

Here is the Resume Template:
<resume_template>
{resume_template}
</resume_template>

{expansion_prompt}

Respond with ONLY the full LaTeX code for the tailored resume, without any additional text, comments, or explanations.
"""
```

**_clean_cover_letter:** Replace hardcoded preamble_patterns and bullet char with values from config:
```python
from config import config  # already imported at top of file

def _clean_cover_letter(text: str) -> str:
    import re
    for pattern in config.cover_letter_preamble_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace('\\%', '%')
    # Replace asterisk bullets with configured bullet char
    text = re.sub(r'^\s*\*\s+', config.cover_letter_bullet_char + ' ', text, flags=re.MULTILINE)
    return text.strip()
```

Note: src/llm.py currently imports `from config import config` which references the OLD config module (the one reading config.yaml). After Task 2 deletes config.yaml, verify what `config` object src/llm.py is actually using. If it imports from the old config.py (not src/config.py), update the import to `from src.config import AppConfig; config = AppConfig()` or whichever import path is correct for this module's location.

**src/main.py line 149:** Replace `expand_sections = ["WORK EXPERIENCE"]` with:
```python
expand_sections = config.expand_sections_default
```
The `config` object is already imported at the top of main.py (`from config import config`). Apply the same import path fix if needed after config.yaml is deleted.

Also update `src/main.py` references to `config.ollama_url` (line 37) — replace with `f"{config.llm_host}/api/generate"` since ollama_url no longer exists in AppConfig.

After both files are updated, run a syntax check:
```bash
cd /Users/tanmaybhuskute/Documents/resume && python -m py_compile src/llm.py src/main.py && echo "OK: syntax clean"
```
  </action>
  <verify>
    cd /Users/tanmaybhuskute/Documents/resume && python -m py_compile src/llm.py src/main.py && echo "OK: syntax clean"
    grep -n "expand_sections = \[" /Users/tanmaybhuskute/Documents/resume/src/main.py && echo "ERROR: still hardcoded" || echo "OK: expand_sections uses config"
    grep -n "open.*resume_generation_prompt" /Users/tanmaybhuskute/Documents/resume/src/llm.py
    grep -n "open.*resume_generation_config" /Users/tanmaybhuskute/Documents/resume/src/llm.py
  </verify>
  <done>src/llm.py and src/main.py compile without errors. generate_latex_resume opens both resume_generation_prompt.md and resume_generation_config.json at runtime. main.py expand_sections reads from config.expand_sections_default. No hardcoded prompt strings remain in llm.py.</done>
</task>

</tasks>

<verification>
After all three tasks complete:

1. Template files exist: `ls templates/*.md` shows 5 files including all four new ones.
2. Config loads: `python -c "from src.config import AppConfig; AppConfig()"` exits 0.
3. config.yaml absent: `ls config.yaml` returns non-zero.
4. Syntax clean: `python -m py_compile src/llm.py src/main.py` exits 0.
5. No hardcoded prompts: `grep -n "You are an expert" src/llm.py` returns nothing (prompts are in templates).
6. Config injection: `grep "resume_generation_config" src/llm.py` shows an open() call.
</verification>

<success_criteria>
- All four prompt .md files exist in templates/ and contain the static instruction text
- resume_generation_config.json rules are injected into the generate_latex_resume prompt at runtime
- AppConfig has expand_sections_default, whitespace_threshold, cover_letter_bullet_char, cover_letter_preamble_patterns, templates_dir fields
- config.yaml is deleted from the repository
- .env.example documents all new APP_ prefixed variables
- src/llm.py has no hardcoded prompt strings; all prompts loaded via open()
- src/main.py reads expand_sections from config.expand_sections_default
- Both src/llm.py and src/main.py pass py_compile with no errors
</success_criteria>

<output>
After completion, create `.planning/quick/1-externalise-prompts-models-and-pipeline-/1-SUMMARY.md`
</output>
