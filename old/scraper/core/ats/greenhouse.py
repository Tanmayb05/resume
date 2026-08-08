"""
Greenhouse Jobs Board API fetcher.
Public API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
"""

from datetime import datetime, timezone
import httpx

from scraper.core.filters import matches_role, get_experience_level, matches_location, is_recent
from scraper.core.registry import Company

BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def fetch(company: Company, client: httpx.Client, days: int = 7) -> tuple[list[dict], str | None]:
    """
    Returns (jobs, error_message).
    jobs is a list of normalized job dicts.
    error_message is set if the company should be flagged as blocked/unavailable.
    """
    url = BASE.format(slug=company.slug_or_url)
    try:
        resp = client.get(url, params={"content": "true"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            return [], f"HTTP {e.response.status_code}"
        return [], f"HTTP error {e.response.status_code}"
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

        # Location: greenhouse returns a list of offices
        offices = raw.get("offices", []) or raw.get("location", {})
        if isinstance(offices, list):
            location = ", ".join(o.get("name", "") for o in offices if o.get("name"))
        elif isinstance(offices, dict):
            location = offices.get("name", "")
        else:
            location = ""

        if not matches_location(location):
            continue

        posted_at = _parse_date(raw.get("updated_at") or raw.get("created_at"))
        if not is_recent(posted_at, days):
            continue

        jobs.append({
            "id": f"gh-{raw['id']}",
            "company": company.name,
            "title": title,
            "level": level,
            "location": location or "Remote",
            "posted_at": posted_at,
            "url": raw.get("absolute_url", company.careers_url),
        })

    return jobs, None
