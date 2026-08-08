"""
Custom scrapers for companies with non-standard career sites.
Each function returns (jobs, error_message).
"""

from datetime import datetime, timezone
import hashlib
import httpx
from bs4 import BeautifulSoup

from scraper.core.filters import matches_role, get_experience_level, matches_location, is_recent
from scraper.core.registry import Company


def _job_id(company: str, title: str, url: str) -> str:
    key = f"{company}:{title}:{url}"
    return "cx-" + hashlib.md5(key.encode()).hexdigest()[:12]


# ── Microsoft ──────────────────────────────────────────────────────────────────

def fetch_microsoft(company: Company, client: httpx.Client, days: int) -> tuple[list[dict], str | None]:
    """Microsoft uses a JSON search API."""
    url = "https://jobs.careers.microsoft.com/global/en/search"
    params = {
        "q": "",
        "l": "en_us",
        "pg": 1,
        "pgSz": 100,
        "o": "Recent",
        "flt": True,
    }
    try:
        resp = client.get(url, params=params, timeout=20,
                          headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [], str(e)

    jobs = []
    for raw in data.get("operationResult", {}).get("result", {}).get("jobs", []):
        title = raw.get("title", "")
        if not matches_role(title):
            continue
        level = get_experience_level(title)
        if level is None:
            continue
        location = raw.get("location", "")
        if not matches_location(location):
            continue
        job_url = f"https://jobs.careers.microsoft.com/global/en/job/{raw.get('jobId', '')}/"
        jobs.append({
            "id": f"ms-{raw.get('jobId', _job_id('microsoft', title, job_url))}",
            "company": company.name,
            "title": title,
            "level": level,
            "location": location or "Remote",
            "posted_at": None,
            "url": job_url,
        })
    return jobs, None


# ── Google ─────────────────────────────────────────────────────────────────────

def fetch_google(company: Company, client: httpx.Client, days: int) -> tuple[list[dict], str | None]:
    """Google careers JSON API."""
    url = "https://careers.google.com/api/v3/search/"
    params = {
        "q": "",
        "sort_by": "date",
        "page_size": 100,
    }
    try:
        resp = client.get(url, params=params, timeout=20,
                          headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [], str(e)

    jobs = []
    for raw in data.get("jobs", []):
        title = raw.get("title", "")
        if not matches_role(title):
            continue
        level = get_experience_level(title)
        if level is None:
            continue
        locations = raw.get("locations", [])
        location = ", ".join(locations) if locations else ""
        if not matches_location(location):
            continue
        job_id = raw.get("id", "")
        job_url = f"https://careers.google.com/jobs/results/{job_id}"
        jobs.append({
            "id": f"goog-{job_id}",
            "company": company.name,
            "title": title,
            "level": level,
            "location": location or "Remote",
            "posted_at": None,
            "url": job_url,
        })
    return jobs, None


# ── Meta ───────────────────────────────────────────────────────────────────────

def fetch_meta(company: Company, client: httpx.Client, days: int) -> tuple[list[dict], str | None]:
    """Meta careers GraphQL-ish endpoint."""
    url = "https://www.metacareers.com/jobs"
    params = {"q": "", "sort_by_new": "true"}
    try:
        resp = client.get(url, params=params, timeout=20,
                          headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        # Meta renders client-side — try to extract from page JSON
        soup = BeautifulSoup(resp.text, "html.parser")
        # Look for __INITIAL_STATE__ or similar embedded JSON
        scripts = soup.find_all("script", {"type": "application/json"})
        if not scripts:
            return [], "Meta site is client-rendered — JS required"
    except Exception as e:
        return [], str(e)
    return [], "Meta site requires JS rendering"


# ── Tesla ──────────────────────────────────────────────────────────────────────

def fetch_tesla(company: Company, client: httpx.Client, days: int) -> tuple[list[dict], str | None]:
    """Tesla uses a simple JSON API."""
    url = "https://www.tesla.com/cua-api/tesla-jobs/search"
    payload = {"query": "", "region": "us", "limit": 100, "offset": 0}
    try:
        resp = client.post(url, json=payload, timeout=20,
                           headers={"User-Agent": "Mozilla/5.0",
                                    "Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [], str(e)

    jobs = []
    for raw in data.get("results", []):
        title = raw.get("title", "")
        if not matches_role(title):
            continue
        level = get_experience_level(title)
        if level is None:
            continue
        location = raw.get("location", {}).get("city", "") + ", " + raw.get("location", {}).get("state", "")
        if not matches_location(location):
            continue
        job_id = str(raw.get("id", ""))
        jobs.append({
            "id": f"ts-{job_id}",
            "company": company.name,
            "title": title,
            "level": level,
            "location": location.strip(", ") or "Remote",
            "posted_at": None,
            "url": f"https://www.tesla.com/careers/search/job/{job_id}",
        })
    return jobs, None


# ── SpaceX ─────────────────────────────────────────────────────────────────────

def fetch_spacex(company: Company, client: httpx.Client, days: int) -> tuple[list[dict], str | None]:
    """SpaceX careers page — HTML scrape."""
    url = "https://www.spacex.com/careers/jobs/"
    try:
        resp = client.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        return [], str(e)

    jobs = []
    # SpaceX lists jobs in anchor tags or table rows — structure varies
    for a in soup.select("a[href*='/careers/jobs/']"):
        title = a.get_text(strip=True)
        if not title or not matches_role(title):
            continue
        level = get_experience_level(title)
        if level is None:
            continue
        href = a.get("href", "")
        job_url = href if href.startswith("http") else f"https://www.spacex.com{href}"
        jobs.append({
            "id": _job_id("spacex", title, job_url),
            "company": company.name,
            "title": title,
            "level": level,
            "location": "United States",
            "posted_at": None,
            "url": job_url,
        })
    if not jobs:
        return [], "SpaceX page structure changed or blocked"
    return jobs, None


# ── Dispatcher ─────────────────────────────────────────────────────────────────

_HANDLERS = {
    "microsoft": fetch_microsoft,
    "google":    fetch_google,
    "meta":      fetch_meta,
    "tesla":     fetch_tesla,
    "spacex":    fetch_spacex,
}


def fetch(company: Company, client: httpx.Client, days: int = 7) -> tuple[list[dict], str | None]:
    handler = _HANDLERS.get(company.slug_or_url)
    if handler is None:
        return [], f"No custom handler for {company.name}"
    return handler(company, client, days)
