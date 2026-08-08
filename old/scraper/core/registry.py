"""
Company/organization -> ATS mapping.
Each entry defines how to fetch jobs for that employer.

`verified` marks whether the ats/slug_or_url has been confirmed against a
live board. Unverified entries default to ats="blocked" (manual-check)
until confirmed by hitting the ATS API directly.

`cap_exempt` / `visa_note` are static metadata about the employer type,
not something scraped per-job — verify current policy before relying on it.
"""

from dataclasses import dataclass, field
from typing import Literal

ATS = Literal["greenhouse", "lever", "workday", "ashby", "custom", "blocked"]


@dataclass
class Company:
    name: str
    ats: ATS
    # For greenhouse/lever/ashby: board slug.
    # For workday/custom: careers URL or handler key.
    slug_or_url: str
    careers_url: str  # always set — shown for blocked and error companies
    verified: bool = True
    cap_exempt: bool = False
    visa_note: str = ""


def load_companies(module_name: str) -> list[Company]:
    """Load a COMPANIES list from a sibling module under scraper.companies."""
    import importlib

    mod = importlib.import_module(f"scraper.companies.{module_name}")
    return mod.COMPANIES
