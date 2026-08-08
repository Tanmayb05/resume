"""
Cap-exempt organizations.

Targets H-1B cap-exempt-eligible employers: nonprofit research orgs,
FFRDCs, universities, teaching hospitals, and large nonprofits.
`cap_exempt` / `visa_note` are static metadata about the employer type,
not something scraped per-job — verify current policy before relying on it.

ATS slugs below are NOT verified against live boards yet (unlike
scraper/companies/tech.py, which has confirmed slugs). Everything defaults
to ats="blocked" (manual-check) until a slug is confirmed by hitting the
ATS API directly. Flip verified entries to their real ATS type as they're
confirmed — see scraper/ROADMAP.md.
"""

from scraper.core.registry import Company

COMPANIES: list[Company] = [
    # ── Tier 1: Nonprofit research orgs / FFRDCs ───────────────────────────────
    Company("MITRE",       "blocked", "", "https://careers.mitre.org", False, True, "FFRDC — often sponsors, cap-exempt affiliated"),
    Company("RAND Corporation", "blocked", "", "https://www.rand.org/jobs.html", False, True, "Nonprofit research org — sometimes sponsors"),
    Company("SRI International", "blocked", "", "https://www.sri.com/careers", False, True, "Nonprofit research institute — sponsors"),
    Company("Battelle",    "blocked", "", "https://careers.battelle.org", False, True, "Nonprofit R&D org — sponsors"),
    Company("Carnegie Mellon SEI", "blocked", "", "https://www.sei.cmu.edu/about/work-for-sei", False, True, "University-affiliated FFRDC — often cap-exempt"),
    Company("Draper Laboratory", "blocked", "", "https://www.draper.com/careers", False, True, "Nonprofit lab — sometimes sponsors"),
    Company("Noblis",      "blocked", "", "https://noblis.jobs", False, True, "Nonprofit — sometimes sponsors"),
    Company("Institute for Defense Analyses", "blocked", "", "https://www.ida.org/careers", False, True, "FFRDC — limited sponsorship, often requires clearance"),

    # ── Tier 2: Universities ────────────────────────────────────────────────────
    Company("Stanford University", "workday", "https://stanford.wd1.myworkdayjobs.com/en-US/stanford", "https://careersearch.stanford.edu", False, True, "University — cap-exempt"),
    Company("UC Berkeley",  "blocked", "", "https://jobs.berkeley.edu", False, True, "University — cap-exempt"),
    Company("UCLA",         "blocked", "", "https://jobs.ucla.edu", False, True, "University — cap-exempt"),
    Company("UC San Diego", "blocked", "", "https://jobs.ucsd.edu", False, True, "University — cap-exempt"),
    Company("Carnegie Mellon University", "workday", "https://cmu.wd5.myworkdayjobs.com/en-US/CMU", "https://www.cmu.edu/jobs", False, True, "University — cap-exempt"),
    Company("Georgia Tech", "blocked", "", "https://careers.gatech.edu", False, True, "University — cap-exempt"),
    Company("Purdue University", "blocked", "", "https://careers.purdue.edu", False, True, "University — cap-exempt"),
    Company("University of Cincinnati", "blocked", "", "https://jobs.uc.edu", False, True, "University — cap-exempt"),
    Company("Arizona State University", "workday", "https://asu.wd1.myworkdayjobs.com/ASU", "https://cfo.asu.edu/jobs", False, True, "University — cap-exempt"),
    Company("University of Michigan", "blocked", "", "https://careers.umich.edu", False, True, "University — cap-exempt"),
    Company("Cornell University", "workday", "https://cornell.wd1.myworkdayjobs.com/en-US/cornelluniversitycareerpage", "https://hr.cornell.edu/jobs", False, True, "University — cap-exempt"),

    # ── Tier 3: Medical nonprofits / teaching hospitals ────────────────────────
    Company("Mayo Clinic",  "workday", "https://mayo.wd2.myworkdayjobs.com/mayoclinic", "https://jobs.mayoclinic.org", False, True, "Nonprofit teaching hospital — cap-exempt eligible"),
    Company("Cleveland Clinic", "workday", "https://clevelandclinic.wd1.myworkdayjobs.com/CCHS", "https://jobs.clevelandclinic.org", False, True, "Nonprofit teaching hospital — cap-exempt eligible"),
    Company("Memorial Sloan Kettering", "blocked", "", "https://careers.mskcc.org", False, True, "Nonprofit — cap-exempt eligible"),
    Company("St. Jude Children's Research Hospital", "workday", "https://stjude.wd1.myworkdayjobs.com/External", "https://www.stjude.org/jobs.html", False, True, "Nonprofit research hospital — cap-exempt eligible, sponsors"),
    Company("Children's Hospital of Philadelphia", "blocked", "", "https://www.research.chop.edu/careers", False, True, "Nonprofit research hospital — cap-exempt eligible"),
    Company("Dana-Farber Cancer Institute", "blocked", "", "https://www.dana-farber.org/jobs", False, True, "Nonprofit — cap-exempt eligible"),
    Company("Fred Hutchinson Cancer Center", "workday", "https://fredhutch.wd1.myworkdayjobs.com/External", "https://www.fredhutch.org/en/about/jobs.html", False, True, "Nonprofit research center — cap-exempt eligible, sponsors"),

    # ── Tier 4: Large nonprofits ────────────────────────────────────────────────
    Company("Wikimedia Foundation", "lever", "wikimedia", "https://wikimediafoundation.org/role", False, True, "Nonprofit — sponsors, cap-exempt eligible"),
    Company("Mozilla Foundation", "greenhouse", "mozilla", "https://www.mozilla.org/en-US/careers", False, True, "Nonprofit — sponsors"),
    Company("Khan Academy",  "greenhouse", "khanacademy", "https://www.khanacademy.org/careers", False, True, "Nonprofit — sponsors"),
    Company("Code.org",      "blocked", "", "https://code.org/about/jobs", False, True, "Nonprofit — sometimes sponsors"),
    Company("Chan Zuckerberg Initiative", "greenhouse", "chanzuckerberginitiative", "https://chanzuckerberg.com/careers", False, True, "LLC/nonprofit hybrid — sponsors"),
    Company("Allen Institute", "greenhouse", "alleninstitute", "https://alleninstitute.org/careers", False, True, "Nonprofit research institute — sponsors, cap-exempt eligible"),
    Company("Allen Institute for AI", "blocked", "", "https://allenai.org/careers", False, True, "Nonprofit research institute — sponsors, cap-exempt eligible"),
    Company("Linux Foundation", "blocked", "", "https://linuxfoundation.org/careers", False, True, "Nonprofit — sometimes sponsors"),
    Company("Human Rights Watch", "blocked", "", "https://www.hrw.org/careers", False, True, "Nonprofit — limited tech roles"),
]
