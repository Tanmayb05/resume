"""
Role, location, date, and experience level filtering.
"""

import re
from datetime import datetime, timezone, timedelta

# ── Role keywords ──────────────────────────────────────────────────────────────

ROLE_KEYWORDS = [
    # Generic SWE
    "software engineer", "software developer", "swe",
    # Specializations
    "backend", "back-end", "back end",
    "frontend", "front-end", "front end",
    "fullstack", "full-stack", "full stack",
    "platform engineer", "infrastructure engineer",
    "devops", "site reliability", "sre",
    # ML / AI
    "machine learning", "ml engineer",
    "ai engineer", "artificial intelligence",
    "research engineer", "research scientist",
    "deep learning", "nlp engineer",
    "data scientist", "data engineer",
    "applied scientist", "applied ml",
    # Mobile
    "mobile engineer", "ios engineer", "android engineer",
    # Security / Cloud
    "security engineer", "cloud engineer",
    "systems engineer", "embedded engineer",
    # General tech
    "engineer", "developer",  # broad catch-all — filtered further by exclude list
]

# Titles containing these are excluded (senior-only roles we don't want)
SENIOR_EXCLUDE = [
    "staff", "principal", "director", "vp ", "vice president",
    "head of", "manager", "senior staff", "distinguished",
    "fellow", "cto", "ceo", "ciso",
]

# Experience level detection
INTERN_SIGNALS = ["intern", "internship", "co-op", "coop", "co op"]
NEW_GRAD_SIGNALS = [
    "new grad", "new graduate", "entry level", "entry-level",
    "university grad", "associate engineer", "junior",
    "university recruiting", "campus",
]
# Mid-level = no seniority keyword → default bucket
SENIOR_SIGNALS = ["senior", "sr.", "sr ", "lead ", "staff", "principal"]


# ── US location keywords ───────────────────────────────────────────────────────

US_LOCATION_SIGNALS = [
    "united states", "usa", "u.s.", "us ",
    "remote", "san francisco", "new york", "seattle", "austin",
    "boston", "chicago", "los angeles", "denver", "atlanta",
    "washington", "cambridge", "palo alto", "mountain view",
    "menlo park", "santa clara", "sunnyvale", "san jose",
    "bellevue", "redmond",
    # State abbreviations
    " ca", " ny", " wa", " tx", " ma", " co", " il", " ga",
]


def _lower(text: str) -> str:
    return text.lower()


def matches_role(title: str) -> bool:
    """Return True if the job title matches target engineering/ML roles."""
    t = _lower(title)
    # Quick exclude: clearly non-technical
    for excl in SENIOR_EXCLUDE:
        if excl in t:
            return False
    for kw in ROLE_KEYWORDS:
        if kw in t:
            return True
    return False


def get_experience_level(title: str) -> str | None:
    """
    Returns 'intern', 'new_grad', 'mid', or None if senior-only.
    None means we should exclude this job.
    """
    t = _lower(title)
    # Exclude seniors
    for sig in SENIOR_SIGNALS:
        if sig in t:
            return None
    for sig in INTERN_SIGNALS:
        if sig in t:
            return "intern"
    for sig in NEW_GRAD_SIGNALS:
        if sig in t:
            return "new_grad"
    return "mid"


def matches_location(location: str) -> bool:
    """Return True if location appears to be US or remote."""
    if not location:
        return True  # unknown → include (better to over-include)
    loc = _lower(location)
    # Explicitly non-US signals
    non_us = ["london", "berlin", "paris", "toronto", "amsterdam",
               "singapore", "tokyo", "sydney", "dublin", "barcelona",
               "india", "canada", "uk", "germany", "france", "australia"]
    for x in non_us:
        if x in loc:
            return False
    for sig in US_LOCATION_SIGNALS:
        if sig in loc:
            return True
    # If location is just "Remote" or empty → include
    if "remote" in loc or loc.strip() == "":
        return True
    return False


def is_recent(posted_at: datetime | None, days: int = 7) -> bool:
    """Return True if posted within the last `days` days."""
    if posted_at is None:
        return True  # unknown date → include
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    return posted_at >= cutoff
