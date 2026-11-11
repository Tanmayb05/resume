

I read your LinkedIn PDF, the 5 condensed JDs, and `master_resume.json` so I could cross-check the facts. One caveat: the keyword counts use the condensed JD text, not the original postings.

---

## 0. Fix this before anything else: your profile contradicts itself and your resume

A recruiter who has your resume open next to LinkedIn will see these. Mismatched numbers make people doubt every other number on the page.

| Topic            | LinkedIn says                                                                                     | Resume / master says                                                               |
| ---------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Downtime cut     | "reducing upgrade downtime by **75%**"                                                      | 50%                                                                                |
| Code coverage    | Experience: "a **200%** increase in code coverage". About: "from 35% to 78%"                | 35%→78%. That is +123%, not 200%. **Your profile contradicts itself here.** |
| Mentoring        | "Mentored and coached **4** new team members, leading to a 35% decrease in onboarding time" | 5 engineers. The "35%" figure appears nowhere in master.                           |
| Environments     | "over **45** customer environments"                                                         | 44 upgrades, 40+ migrated                                                          |
| Research start   | "July 2025 - Present"                                                                             | Feb 2026                                                                           |
| Internship title | "Software Engineer, March 2022 - June 2022"                                                       | Software Developer **Intern**                                                |

The internship one is the most serious. Calling the internship "Software Engineer" makes LinkedIn add it up as "2 years 4 months" at Siemens. That is a background-check problem, and it misstates your experience.

---

## 1. Identity gap

- **What you project today:** a former Siemens DevOps/ops engineer, now a grad student researching LLM agents, who says he is interested in everything. Your own line: *"I'm interested in building scalable software across: • Backend Engineering • Cloud Infrastructure & Platform Engineering • Distributed Systems • AI/ML & LLM Applications"*. Four lanes reads as no lane.
- **What the JDs hire for:** people who build product code. Feature owners who write services, APIs, pipelines and tests, then run them in production.
- **The mismatch:** your verbs describe operating and learning, not building:

  - *"Provided ongoing support and hotfixes"*
  - *"Managed data migration"*
  - *"Gained proficiency in AWS basics"*
  - *"Studied Ansible"*
  - *"Learned importance of test cases in software development"*

  The intern lines read like a course syllabus. The second mismatch is your target list itself. It covers 5 different jobs (new-grad generalist, Go platform, full-stack AI, data engineer, Java backend). No single profile ranks top 10 for all five.

## 2. Keyword gap (terms in 3+ JDs that your profile never uses)

| Term                                                              | JDs                               | Your profile                                                                                                                                |
| ----------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **code review**                                             | Stripe, MSFT, Amazon, Salesforce  | missing                                                                                                                                     |
| **AI-assisted development / AI tools**                      | Stripe, MSFT, Amazon, Salesforce  | missing. "AI-assisted software testing" is your research topic, not how you work. Add it only if you really use Copilot/Claude Code/Cursor. |
| **unit / integration / end-to-end testing**                 | Siemens, MSFT, Salesforce, Amazon | missing. You only have "code coverage" and "Learned importance of test cases".                                                              |
| **monitoring / observability / telemetry**                  | MSFT, Amazon, Salesforce          | missing                                                                                                                                     |
| **incident response / live-site / safe production updates** | Stripe, MSFT, Salesforce          | missing. "hotfixes" reads as ticket work.                                                                                                   |
| **product/program managers, cross-functional partners**     | MSFT, Amazon, Salesforce          | missing. The only collaborator you name is "a faculty advisor".                                                                             |

Missing terms that appear in only 2 JDs but carry heavy weight: **microservices, event-driven / message queue, REST APIs, ETL / data pipelines, Spark, JavaScript / TypeScript, Linux, shell scripting, NoSQL, full-stack, documentation.**

Two of these are absurd to be missing. **Linux** is in your master resume and you ran production Linux. **JavaScript** is your React/Node stack, and the word appears nowhere on your profile.

## 3. Credibility gap (proof you have but don't show)

- **Microsoft Fullstack AI:** PolicyPilot is not on your profile at all, and it is a near-perfect match:

  - "evidence-grounded RAG" covers grounding and RAG
  - the "17-tool MCP server" covers tool calling
  - "benchmarking hallucination rates" plus confidence scoring covers model evaluation
  - React/TypeScript/Node covers full-stack
  - Vitest plus **axe-core WCAG AA** covers their accessibility testing

  Your research's provider-agnostic abstraction (Gemini, GPT-4o, Llama, Qwen) is also missing. That is your best AI evidence, and it's invisible.
- **Siemens Cloud Native:** they want Go. Your profile says *"Executed Terragrunt tests on Terraform code"*. Master says you built a **Go + Terratest framework that caught 95% of misconfigurations**. You buried your only Go proof under "learned". The JD also asks for microservices, event-driven work and docs-as-code, and none of that is shown.
- **Amazon DE:** your profile has no data work. Master has a PySpark/Delta Lake medallion pipeline (2.3M rows) and a 4-stage ETL (71K events, PostgreSQL materialized views, 16 SQL RPC functions). Neither appears. Even with them, you'd have no Redshift/Glue/EMR and no professional data work. This is a reach.
- **Salesforce:** they want "deep Java" and "expert RDBMS". Your Java proof is one word in a list in your About section. Nothing in master backs deep Java either. Delta Lake (which they list as preferred) is in your NYC project, which isn't on the profile.
- **Stripe:** this is a hard filter, not a gap. You have 24 months full-time and their cap is 18. Fixing the intern title won't change that. Drop it from the list.
- **Buried Siemens wins that are in master but not on LinkedIn:**

  - cut AWS spend by 40% ($15K→$9K/mo)
  - built a self-service platform adopted by 15 engineers
  - cut provisioning time by 70%
  - migrated 40+ environments to Kubernetes. LinkedIn only says *"a large-scale Teamcenter X environment"*, singular.
- **Claims with no proof:** "Distributed Systems" in your headline. Nothing on the profile shows distributed-systems work. At top companies that gets you a skeptical interview question, not credit.
- **Mess that signals carelessness:**

  - a stray `:` line in Siemens experience
  - "management,enhancing" (missing space)
  - About bullets crammed inline ("I:- Modernized … deployments.- Improved")
  - "Teamcenter X Cloud ART" with ART never explained
  - your PDF export shows a literal `&amp;`; check whether the live profile does too

## 4. Search visibility

**Top Skills** is the field recruiters filter on. Your three (from the 2022 undergrad paper) are *"Recommender Systems, k-means clustering, K-Nearest Neighbors (KNN)"*. That tells a recruiter you're a data-science student. I can only see your top 3 in the PDF, so check the full list.

Three likely searches:

1. **`"software engineer" AND (Go OR Golang) AND Kubernetes AND microservices`, Cincinnati.** You'd show up without "microservices" (small local pool, matching title and terms). With "microservices" in the AND you're filtered out completely. Top 10 is a coin flip at best. Your current title "Graduate Researcher" ranks below people currently titled Software Engineer.
2. **`("software engineer" OR "AI engineer") AND (LLM OR RAG) AND (TypeScript OR React)`, Redmond / open to relocate.** "LLM" matches, but RAG and TypeScript don't appear. React appears once in a list. **Not top 10.**
3. **`"data engineer" AND (ETL OR Spark) AND SQL AND AWS`.** No matching title, no ETL, no Spark. **You're not in the results at all.**

Also: 4 of the 5 roles are outside Ohio, and nothing on the profile says you'll relocate. I can't see your Open to Work settings, so check them. LinkedIn's ranking is opaque; this is how the filters behave, not a measured result.

## 5. The one line

- **Today:** *"Software Engineer | Ex-Siemens | M.S. Computer Science @ University of Cincinnati | Cloud • AI • Distributed Systems"*. It says: student, used to work somewhere, likes three buzzwords. A recruiter can't verify any of it and can't search for most of it.
- **What it should say:** something like *"I've already run production at scale (moved 40+ environments to Kubernetes, did 44 live upgrades) and now I build LLM systems that ship (RAG, tool calling, evals)."* That sells you as a builder who can be trusted with production.

**My take on lanes:** lead with **platform/backend engineering, with applied LLM work as the second lane**. That covers Siemens, Microsoft and Salesforce. Stripe is filtered out. Amazon DE only works if the two data projects become the headline evidence.

I haven't rewritten anything. Prompts 2–4 (headline/About, experience bullets, skills) take the rewrite from here. Before you run them, decide which figures are true for the 6 contradictions in section 0.
