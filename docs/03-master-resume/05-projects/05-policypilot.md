### **PolicyPilot | Medical Benefit Policy Intelligence Portal**
**May 2026**

**Tech Stack:** React, TypeScript, Node.js, Express, Google Gemini, MCP, Docker, Zod, FHIR, Railway

**Context:** Medical Benefit Policy Intelligence Portal solving the fragmented insurance payer policy problem — clinicians manually dig through 50-500 page PDFs to answer drug coverage/prior-authorization (PA) eligibility questions. Ingests, normalizes, and unifies multi-payer policies into a queryable structured system, matches patient documents against coverage criteria, and generates evidence-backed next steps. Built for the Prompt Opinion hackathon (May 2026).

**Core Features:** Unified drug coverage search across payers, cross-payer side-by-side comparison, real-time policy-change tracking, AI-powered natural-language chat for coverage/PA/eligibility questions, and an Evidence Explorer for verifying coverage details against source policy documents.

- Architected evidence-grounded RAG pipeline over Google Gemini 2.5-flash, forcing citation-backed answers to eliminate hallucination in high-stakes healthcare eligibility decisions
- Designed 17-tool MCP (Model Context Protocol) server exposing structured LLM tool-calling for PA extraction, patient-readiness evaluation, and cross-payer comparison, consumable by external AI agents
- Engineered confidence-scoring system (evidence count, negation detection, subjectivity flags) driving human-review triage, migrating from Ollama to Gemini after benchmarking hallucination rates
- Built citation/version tracing into every LLM answer so retrieval mismatches (e.g. an outdated policy version) surface immediately instead of silently misleading a provider

**AI/ML Engineer:**
- Architected evidence-grounded RAG pipeline over Google Gemini 2.5-flash, forcing citation-backed answers to eliminate hallucination in high-stakes healthcare eligibility decisions
- Designed 17-tool MCP server exposing structured LLM tool-calling for PA extraction, patient-readiness evaluation, and cross-payer comparison, letting external AI agents replace manual multi-payer PDF lookups with direct queries
- Engineered confidence-scoring system (evidence count, negation detection, subjectivity flags) driving human-review triage, migrating from Ollama to Gemini after benchmarking hallucination rates

**Software Engineer:**
- Built full-stack TypeScript healthcare app (React SPA + Express 5 REST API + MCP server) unifying insurance PA workflows on single Node.js process
- Designed 17 MCP tool APIs (get_drug_coverage, check_patient_readiness, diff_policy_versions) with Zod schema validation at every data boundary, eliminating a class of runtime type-mismatch bugs across all external tool calls
- Implemented PDF-to-structured-data pipeline (parse → clean → chunk → validate) with Vitest unit/integration tests and axe-core accessibility (WCAG AA) coverage

**Key Learnings:**
- Retrieval and document structure mattered more than the model — policy PDFs vary widely in layout, and the same rule can appear under different sections, headings, or tables
- Policy versioning is a correctness risk, not just a UX detail — an unversioned system can silently surface criteria from an outdated policy; citing source + version in every answer makes that class of error catchable
- Standards like HL7's Da Vinci FHIR guides (pushed by CMS) only cover transmitting coverage details — the harder problem was keeping underlying multi-payer data correct and versioned, not raw speed
