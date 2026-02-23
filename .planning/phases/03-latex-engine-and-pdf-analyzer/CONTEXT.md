# Phase 3 Context: LaTeX Engine and PDF Analyzer

## Source of Truth

The reference LaTeX template is `templates/resume_template.tex`. The JSON payload schema is
`templates/resume_json_template.json`. The Jinja2 template (`resume_template.tex.j2`) must
reproduce the output of `resume_template.tex` exactly — same preamble, same environments, same
spacing — with hardcoded values replaced by template variables.

---

## Jinja2 Delimiters

Use these custom delimiters to avoid clashing with LaTeX `{}` and `%` syntax:

| Purpose   | Open  | Close |
|-----------|-------|-------|
| Variable  | `((*` | `*))` |
| Block     | `((%` | `%))` |
| Comment   | `((#` | `#))` |

`trim_blocks=True` and `lstrip_blocks=True` must be set so block tags don't inject blank lines
into the rendered `.tex`.

---

## latex_escape Filter

Register a `latex_escape` Jinja2 filter. It must escape in this order (backslash first to avoid
double-escaping):

| Character | Replacement              |
|-----------|--------------------------|
| `\`       | `\textbackslash{}`       |
| `&`       | `\&`                     |
| `%`       | `\%`                     |
| `$`       | `\$`                     |
| `#`       | `\#`                     |
| `_`       | `\_`                     |
| `{`       | `\{`                     |
| `}`       | `\}`                     |
| `~`       | `\textasciitilde{}`      |
| `^`       | `\textasciicircum{}`     |

Apply `| latex_escape` to **every user-supplied string field** in the template. Do NOT apply it
to static LaTeX strings (e.g. `\textbf{Tech Stack:}`).

---

## Template Preamble (Static — Copy Verbatim)

The entire preamble from `\documentclass` through `\end{document}` opening is static. Copy it
from `resume_template.tex` without modification. Key elements:

- `\documentclass[9pt, letterpaper]{article}`
- geometry: top/bottom `0.5cm`, left/right `0.7cm`, footskip `0.2cm`
- `\usepackage{charter}` (font)
- `\usepackage{paracol}` (two-column entries)
- `\usepackage{fontawesome5}` (icons — keep even if unused in template)
- `\titleformat{\section}` with `\needspace{4\baselineskip}\bfseries\large` and `\titlerule`
- `\titlespacing{\section}{-1pt}{0.05 cm}{0.05 cm}`
- Custom environments: `highlights`, `highlightsforbulletentries`, `onecolentry`, `twocolentry`,
  `threecolentry`, `header`
- `\AND` / `\ANDbox` commands defined inside `\begin{document}`
- `\renewcommand\labelitemi{$\vcenter{\hbox{\small$\bullet$}}$}`
- `\placelastupdatedtext` definition (keep, but do not call it in the template body)

---

## Header Section

Reference output from `resume_template.tex`:

```latex
\begin{header}
    \fontsize{16 pt}{26 pt}\selectfont Tanmay Bhuskute

    \normalsize
    \mbox{Cincinnati, OH}%
    \kern 1.0 pt%
    \AND%
    \kern 1.0 pt%
    \mbox{linkedin.com/in/tanmay-bhuskute}%
    \kern 1.0 pt%
    \AND%
    \kern 1.0 pt%
    \mbox{tanmayb05.github.io/portfolio/}%
    \kern 1.0 pt%
    \AND%
    \kern 1.0 pt%
    \mbox{tanmay.v.bhuskute@gmail.com}%
    \kern 1.0 pt%
\end{header}
```

Jinja2 version (note: `nameFontPt` and `nameLineHeightPt` are integers, no escaping needed):

```latex
\begin{header}
    \fontsize{((* header.nameFontPt *)) pt}{((* header.nameLineHeightPt *)) pt}\selectfont ((* header.name | latex_escape *))

    \normalsize
    ((% for item in header.contactLine %))
    \mbox{((* item.text | latex_escape *))}%
    \kern 1.0 pt%
    ((% if not loop.last %))
    \AND%
    \kern 1.0 pt%
    ((% endif %))
    ((% endfor %))
\end{header}
```

---

## Section Dispatch Loop

The `sections` array has exactly 5 entries in fixed order:
`education`, `technical_skills`, `work_experience`, `projects_and_research`, `extracurricular`.

```latex
((% for section in sections %))
((% if section.type == 'education' %))
...
((% elif section.type == 'technical_skills' %))
...
((% elif section.type == 'work_experience' %))
...
((% elif section.type == 'projects_and_research' %))
...
((% elif section.type == 'extracurricular' %))
...
((% endif %))
((% endfor %))
```

---

## Education Section

Reference:
```latex
\section{EDUCATION}
    \begin{twocolentry}{
        Aug 2024 - Aug 2026}
        \textbf{Master of Science in Computer Science} - University of Cincinnati \end{twocolentry}
    \begin{onecolentry}
    Relevant Coursework: Advanced Algorithms, Deep Learning, Intelligent Data Analysis, Database Theory.
    \end{onecolentry}
\vspace{0.10 cm}
```

Jinja2 version:
```latex
\section{((* section.title | latex_escape *))}
    ((% for entry in section.entries %))
    \begin{twocolentry}{
        ((* entry.dates | latex_escape *))}
        \textbf{((* entry.degree | latex_escape *))} - ((* entry.institution | latex_escape *)) \end{twocolentry}
    \begin{onecolentry}
    ((* entry.courseworkLine | latex_escape *))
    \end{onecolentry}
    ((% if not loop.last %))
    \vspace{0.10 cm}
    ((% endif %))
    ((% endfor %))
```

---

## Technical Skills Section

Reference:
```latex
\section{TECHNICAL SKILLS}
    \begin{onecolentry}
    \textbf{Programming \& Scripting:} Java, Python, C/C++, SQL (Postgres), ...
    \end{onecolentry}
```

Jinja2 version (join items into a comma-separated string, then escape the whole string):
```latex
\section{((* section.title | latex_escape *))}
    ((% for line in section.lines %))
    \begin{onecolentry}
    \textbf{((* line.label | latex_escape *)):} ((* line.items | join(', ') | latex_escape *)).
    \end{onecolentry}
    ((% endfor %))
```

Note: `join(', ')` first, then `latex_escape` — this matches how the reference template renders
skill lines as a single string.

---

## Work Experience Section

Reference:
```latex
\section{WORK EXPERIENCE}
    \begin{twocolentry}{Jul 2022 - Jun 2024}\textbf{Siemens Industry Software} (Software Developer Engineer)\end{twocolentry}
    \begin{onecolentry}\textbf{Tech Stack:} AWS, Python, Boto, REST APIs, ...\end{onecolentry}
    \begin{onecolentry}
        \begin{highlights}
            \item Automated AWS workflows...
        \end{highlights}
    \end{onecolentry}
```

Jinja2 version:
```latex
\section{((* section.title | latex_escape *))}
    ((% for entry in section.entries %))
    \begin{twocolentry}{((* entry.dates | latex_escape *))}\textbf{((* entry.company | latex_escape *))} (((* entry.role | latex_escape *)))\end{twocolentry}
    \begin{onecolentry}\textbf{Tech Stack:} ((* entry.techStack | join(', ') | latex_escape *)) \end{onecolentry}
    \begin{onecolentry}
        \begin{highlights}
            ((% for bullet in entry.bullets %))
            \item ((* bullet | latex_escape *))
            ((% endfor %))
        \end{highlights}
    \end{onecolentry}
    ((% if not loop.last %))

    ((% endif %))
    ((% endfor %))
```

---

## Projects and Research Section

Reference:
```latex
\section{PROJECTS AND RESEARCH}
    \begin{twocolentry}
        {Jun 2025}\textbf{Spendora - Conversational AI for Expense Insights} [ HuggingFace, LangChain, Mistral, Gemma ]
    \end{twocolentry}
    \begin{onecolentry}
        \begin{highlights}
            \item{Developed LLM-powered finance assistant...}
        \end{highlights}
    \end{onecolentry}

    \begin{twocolentry}
        {Mar 2022}\textbf{Media Recommender | Published Paper ID - IJRASET42927} [ React, Flask, Python, Spotify API ]
    \end{twocolentry}
```

Note: `linkText` appears inline after the tech bracket, separated by ` | `. The `|` is a LaTeX
special character only in tabular contexts — it is safe in normal text, so do NOT escape it.

Jinja2 version:
```latex
\section{((* section.title | latex_escape *))}
    ((% for entry in section.entries %))
    \begin{twocolentry}
        {((* entry.date | latex_escape *))}\textbf{((* entry.title | latex_escape *))}((% if entry.linkText is defined and entry.linkText %)) | ((* entry.linkText | latex_escape *))((% endif %)) [ ((* entry.techBracket | join(', ') | latex_escape *)) ]
    \end{twocolentry}
    \begin{onecolentry}
        \begin{highlights}
            ((% for bullet in entry.bullets %))
            \item ((* bullet | latex_escape *))
            ((% endfor %))
        \end{highlights}
    \end{onecolentry}
    ((% endfor %))
```

---

## Extracurricular Section

Reference:
```latex
\section{EXTRACURRICULAR ACTIVITIES}
    \begin{onecolentry}
        \begin{highlights}
            \item Finalist at \textbf{RevolutionUC 2025}...
            \item Earned \textbf{SAFe\textsuperscript{\textregistered} Practitioner 5.1 Certification}...
        \end{highlights}
    \end{onecolentry}
```

Jinja2 version:
```latex
\section{((* section.title | latex_escape *))}
    \begin{onecolentry}
        \begin{highlights}
            ((% for bullet in section.bullets %))
            \item ((* bullet | latex_escape *))
            ((% endfor %))
        \end{highlights}
    \end{onecolentry}
```

---

## Artifact Naming (RES-05)

The renderer saves `.tex` files atomically to `data/<company_slug>/` with `_iter_N` suffix:

```
data/<company_slug>/resume_iter_0.tex
data/<company_slug>/resume_iter_1.tex
...
```

The compiler saves `.pdf` files with the same naming convention:

```
data/<company_slug>/resume_iter_0.pdf
```

The caller (Phase 4 enforcement loop) is responsible for constructing the output path and
passing it to `render_resume_tex(payload, output_path)`. The renderer does not infer
`company_slug` or iteration number — it only writes to whatever `output_path` it receives.

---

## tectonic Invocation

```python
import subprocess
result = subprocess.run(
    ["tectonic", "-X", "compile", "--outdir", str(output_dir), str(tex_path)],
    capture_output=True,
    text=True,
    timeout=60,  # first-run package download can take 60+ seconds
)
```

On failure (`returncode != 0`), return a structured dict — do not raise:
```python
{"success": False, "error": result.stderr, "tex_path": str(tex_path)}
```

On success:
```python
{"success": True, "pdf_path": str(pdf_path), "tex_path": str(tex_path)}
```

---

## PDF Analyzer

Use PyMuPDF (`import fitz`). Return a structured dict for both success and failure (never raise
on corrupt/missing input):

```python
def analyze_pdf(pdf_path: Path) -> dict:
    # Returns: {"success": bool, "page_count": int, "whitespace_ratio": float,
    #           "page_height_inches": float, "error": str | None}
```

`whitespace_ratio` = fraction of page area with no text bounding boxes (0.0–1.0). Target: below
0.40 for a well-filled single-page resume.

`page_height_inches` is included to detect the edge case where a single oversized page is
returned (height > 11.5 inches = overflow even though `page_count == 1`).

---

## What NOT to Change

- Do not modify the LaTeX preamble (packages, environment definitions, spacing constants).
- Do not add `\placelastupdatedtext` to the template body — omit the call.
- Do not add `\vspace` between entries in work experience or projects (the reference template
  uses a blank line pattern, handled by `((% if not loop.last %))` with a blank line).
- The `\AND` / `\ANDbox` commands are defined inside `\begin{document}` — keep them there.
