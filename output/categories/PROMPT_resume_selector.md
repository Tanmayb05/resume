# Resume Category Selector — Prompt

Paste this prompt (with a JD pasted below it) to pick the best-fit resume category.

---

## Prompt

You are an expert ATS resume matcher. I have 9 pre-built resume variants, each tuned toward a different engineering identity/pitch. Given the job description I paste below, tell me which ONE category fits best, and one sentence why (keyword/domain overlap, not guesswork).

Compare against these 9 reference resumes (read the tex for exact content, PDF for visual):

| Category | Resume PDF | Resume TeX |
|---|---|---|
| Cloud/Distributed Backend Infra | output/categories/Tanmay_Bhuskute_resume_Cloud_Distributed_Backend_Infra.pdf | output/categories/Tanmay_Bhuskute_resume_Cloud_Distributed_Backend_Infra.tex |
| DevOps / Infra-as-Code | output/categories/Tanmay_Bhuskute_resume_DevOps_Infra_as_Code.pdf | output/categories/Tanmay_Bhuskute_resume_DevOps_Infra_as_Code.tex |
| AI/ML & LLM-Forward Engineering | output/categories/Tanmay_Bhuskute_resume_AI_ML_LLM_Forward.pdf | output/categories/Tanmay_Bhuskute_resume_AI_ML_LLM_Forward.tex |
| Full-Stack / Web Product | output/categories/Tanmay_Bhuskute_resume_Full_Stack_Web_Product.pdf | output/categories/Tanmay_Bhuskute_resume_Full_Stack_Web_Product.tex |
| Systems / Low-Level (C/C++) | output/categories/Tanmay_Bhuskute_resume_Systems_Low_Level_CCpp.pdf | output/categories/Tanmay_Bhuskute_resume_Systems_Low_Level_CCpp.tex |
| Data Engineering / Analytics | output/categories/Tanmay_Bhuskute_resume_Data_Engineering_Analytics.pdf | output/categories/Tanmay_Bhuskute_resume_Data_Engineering_Analytics.tex |
| Security / Compliance / Ops | output/categories/Tanmay_Bhuskute_resume_Security_Compliance_Ops.pdf | output/categories/Tanmay_Bhuskute_resume_Security_Compliance_Ops.tex |
| AI-Native Dev Tooling (Claude Code / AI-assisted workflows) | output/categories/Tanmay_Bhuskute_resume_AI_Native_Dev_Tooling.pdf | output/categories/Tanmay_Bhuskute_resume_AI_Native_Dev_Tooling.tex |
| Condensed Backend Pitch (short/terse, no M.S.-candidate framing) | output/categories/Tanmay_Bhuskute_resume_Condensed_Backend_Pitch.pdf | output/categories/Tanmay_Bhuskute_resume_Condensed_Backend_Pitch.tex |

Rules:
- Pick exactly ONE category as primary recommendation.
- If two categories tie closely, name both and say which edges out and why.
- Base decision on JD's stated required skills/keywords, not job title alone.
- Do not fabricate — if JD is ambiguous or generic, say so and pick the closest match.
- Output format: **Category:** \<name\> — **Why:** \<1 sentence\> — **Fallback:** \<second choice, if close\>

## Job Description

\<PASTE JD HERE\>
