# `resume_content.json` contract

The file you write to `<job_dir>/resume_content.json`. It is the only input
`build_resume_payload()` accepts from you; everything factual comes from
`templates/master_resume.json`.

## Full shape

```json
{
  "experience_ids": [
    "siemens-industry-software-software-developer-engineer",
    "siemens-industry-software-software-developer-intern"
  ],
  "project_ids": [
    "policypilot-medical-benefit-policy-intelligence-portal",
    "spotify-personal-analytics-platform"
  ],
  "skills": {
    "programming": ["Python", "Go", "Java", "SQL (Postgres)"],
    "developer_tools": ["AWS", "Docker", "Kubernetes", "Git", "Jenkins", "ArgoCD"],
    "frameworks": ["Flask", "React"],
    "libraries": ["Pandas", "NumPy"]
  },
  "experience_overrides": {
    "siemens-industry-software-software-developer-engineer": {
      "bullets": [
        "Executed **44 production upgrades in 4 months**, diagnosing live infrastructure issues with zero service interruption.",
        "Automated AWS workflows with Python and Boto3, replacing legacy Ruby scripts and cutting deployment time by **40%**."
      ]
    }
  },
  "project_overrides": {},
  "extracurricular_indices": [0, 1]
}
```

## Field reference

| Key | Required | Meaning |
|---|---|---|
| `experience_ids` | no | Which work experiences to show, in resume order. Omit to include all. |
| `project_ids` | no | Which projects to show, in resume order. Omit to include all (usually too long). |
| `skills` | no | Category → item list. Both must exist in master. Omit to include all skills. |
| `experience_overrides` | no | `{id: {"bullets": [...]}}`. Replaces that entry's bullets. |
| `project_overrides` | no | Same, for projects. |
| `extracurricular_indices` | no | Which extracurricular entries by 0-based index. Omit for all. |

Every key is optional, but in practice you always set `experience_ids`, `project_ids`, and
`skills` — the defaults produce a resume well over one page.

## Rules the builder enforces

An override may contain **only** `bullets`. Attempting `dates`, `company`, `role`,
`techStack`, `degree`, or `institution` raises an error naming the disallowed keys. Those
values always come from master_resume.

Ids must match exactly. The `init` step prints the valid set as `available_ids`; unknown
ids raise an error listing what is valid. Ids are full-length slugs, not truncated.

Skill categories must be one of `programming`, `frameworks`, `developer_tools`,
`libraries`, and each item must appear verbatim (case-insensitively) in that category in
master_resume. A skill mentioned only in achievement prose — Ansible, for example — is not
in the skills list and will be rejected.

`bullets` must be a non-empty list of strings. `summary` is forbidden at the root.

## Bold markers

`**text**` becomes `\textbf{text}`. The markers must balance, or LaTeX compilation fails
with an error you will then have to chase through the generated `.tex`. One or two bolded
phrases per bullet is the house style; more reads as shouting.
