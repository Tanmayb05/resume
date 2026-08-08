"""
Top tech companies.

Verified slugs (2026-03-08):
  Greenhouse: anthropic, scaleai, databricks, stripe, affirm, robinhood, figma,
              hubspot, cloudflare, datadog, gitlab, twilio, okta, mongodb, elastic,
              coinbase, xai-inc, andurilindustries
  Lever:      palantir, mistral, atlassian, block
  Ashby:      notion, openai
  Workday:    salesforce, servicenow, intuit, adobe, workday, autodesk, cisco, ibm, intel
  Custom:     microsoft, google, tesla, spacex
  Blocked:    apple, amazon, nvidia, meta (JS-rendered)
  Manual:     cohere, snowflake, plaid, zendesk, hashicorp, groq, robinhood, oracle, sap
"""

from scraper.core.registry import Company

COMPANIES: list[Company] = [
    # ── Greenhouse (verified slugs) ────────────────────────────────────────────
    Company("Anthropic",   "greenhouse", "anthropic",        "https://www.anthropic.com/careers"),
    Company("Scale AI",    "greenhouse", "scaleai",          "https://scale.com/careers"),
    Company("Databricks",  "greenhouse", "databricks",       "https://www.databricks.com/company/careers"),
    Company("Stripe",      "greenhouse", "stripe",           "https://stripe.com/jobs"),
    Company("Affirm",      "greenhouse", "affirm",           "https://www.affirm.com/careers"),
    Company("Robinhood",   "greenhouse", "robinhood",        "https://careers.robinhood.com"),
    Company("Figma",       "greenhouse", "figma",            "https://www.figma.com/careers"),
    Company("HubSpot",     "greenhouse", "hubspot",          "https://www.hubspot.com/careers"),
    Company("Cloudflare",  "greenhouse", "cloudflare",       "https://www.cloudflare.com/careers"),
    Company("Datadog",     "greenhouse", "datadog",          "https://www.datadoghq.com/careers"),
    Company("GitLab",      "greenhouse", "gitlab",           "https://about.gitlab.com/jobs"),
    Company("Twilio",      "greenhouse", "twilio",           "https://www.twilio.com/en-us/company/jobs"),
    Company("Okta",        "greenhouse", "okta",             "https://www.okta.com/company/careers"),
    Company("MongoDB",     "greenhouse", "mongodb",          "https://www.mongodb.com/careers"),
    Company("Elastic",     "greenhouse", "elastic",          "https://www.elastic.co/about/careers"),
    Company("Coinbase",    "greenhouse", "coinbase",         "https://www.coinbase.com/careers"),
    Company("xAI",         "greenhouse", "xai",              "https://x.ai/careers"),
    Company("Anduril",     "greenhouse", "andurilindustries","https://www.anduril.com/open-roles"),
    Company("Block",       "greenhouse", "block",            "https://careers.block.xyz"),

    # ── Lever (verified slugs) ─────────────────────────────────────────────────
    Company("Palantir",    "lever",      "palantir",         "https://www.palantir.com/careers"),
    Company("Mistral AI",  "lever",      "mistral",          "https://mistral.ai/careers"),
    Company("Atlassian",   "lever",      "atlassian",        "https://www.atlassian.com/company/careers"),

    # ── Ashby (verified slugs) ─────────────────────────────────────────────────
    Company("Notion",      "ashby",      "notion",           "https://www.notion.so/careers"),
    Company("OpenAI",      "ashby",      "openai",           "https://openai.com/careers"),

    # ── Workday (JSON search API) ──────────────────────────────────────────────
    Company("Salesforce",  "workday",    "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site", "https://www.salesforce.com/company/careers"),
    Company("ServiceNow",  "workday",    "https://servicenow.wd1.myworkdayjobs.com/en-US/External",              "https://www.servicenow.com/company/careers"),
    Company("Intuit",      "workday",    "https://intuit.wd1.myworkdayjobs.com/en-US/Intuit_Careers",            "https://careers.intuit.com"),
    Company("Adobe",       "workday",    "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced",       "https://www.adobe.com/careers"),
    Company("Workday",     "workday",    "https://workday.wd5.myworkdayjobs.com/en-US/Workday",                  "https://www.workday.com/en-us/company/careers"),
    Company("Autodesk",    "workday",    "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext",                     "https://www.autodesk.com/careers"),
    Company("Cisco",       "workday",    "https://cisco.wd5.myworkdayjobs.com/en-US/External",                   "https://jobs.cisco.com"),
    Company("IBM",         "workday",    "https://ibm.wd12.myworkdayjobs.com/en-US/External_Global_Careers",     "https://www.ibm.com/careers"),
    Company("Intel",       "workday",    "https://intel.wd1.myworkdayjobs.com/en-US/External",                   "https://jobs.intel.com"),

    # ── Custom scrapers ────────────────────────────────────────────────────────
    Company("Tesla",       "custom",     "tesla",      "https://www.tesla.com/careers"),
    Company("SpaceX",      "custom",     "spacex",     "https://www.spacex.com/careers"),

    # ── Blocked / bot-protected or JS-rendered ─────────────────────────────────
    Company("Apple",       "blocked",    "",  "https://jobs.apple.com"),
    Company("Amazon",      "blocked",    "",  "https://www.amazon.jobs"),
    Company("Nvidia",      "blocked",    "",  "https://www.nvidia.com/en-us/about-nvidia/careers"),
    Company("Meta",        "blocked",    "",  "https://www.metacareers.com"),
    Company("Microsoft",   "blocked",    "",  "https://careers.microsoft.com"),
    Company("Google",      "blocked",    "",  "https://careers.google.com"),

    # ── Manual (unresolved ATS / private job boards) ───────────────────────────
    Company("Cohere",      "blocked",    "",  "https://cohere.com/careers"),
    Company("Snowflake",   "blocked",    "",  "https://careers.snowflake.com"),
    Company("Plaid",       "blocked",    "",  "https://plaid.com/careers"),
    Company("Zendesk",     "blocked",    "",  "https://www.zendesk.com/jobs"),
    Company("HashiCorp",   "blocked",    "",  "https://www.hashicorp.com/careers"),
    Company("Groq",        "blocked",    "",  "https://groq.com/careers"),
    Company("Oracle",      "blocked",    "",  "https://www.oracle.com/corporate/careers"),
    Company("SAP",         "blocked",    "",  "https://jobs.sap.com"),
]
