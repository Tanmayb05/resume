"""
Lever Postings API fetcher.
Public API: https://api.lever.co/v0/postings/{company}?mode=json
"""

from datetime import datetime, timezone
import httpx

from scraper.core.filters import matches_role, get_experience_level, matches_location, is_recent
from scraper.core.registry import Company

BASE = "https://api.lever.co/v0/postings/{slug}"


def _parse_ts(ms: int | None) -> datetime | None:
    """Lever timestamps are milliseconds since epoch."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except Exception:
        return None


def fetch(company: Company, client: httpx.Client, days: int = 7) -> tuple[list[dict], str | None]:
    url = BASE.format(slug=company.slug_or_url)
    try:
        resp = client.get(url, params={"mode": "json"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        return [], f"HTTP {e.response.status_code}"
    except Exception as e:
        return [], str(e)

    jobs = []
    for raw in data:
        title = raw.get("text", "")
        if not matches_role(title):
            continue

        level = get_experience_level(title)
        if level is None:
            continue

        categories = raw.get("categories", {})
        location = categories.get("location", "") or categories.get("office", "")
        if not matches_location(location):
            continue

        posted_at = _parse_ts(raw.get("createdAt"))
        if not is_recent(posted_at, days):
            continue

        jobs.append({
            "id": f"lv-{raw['id']}",
            "company": company.name,
            "title": title,
            "level": level,
            "location": location or "Remote",
            "posted_at": posted_at,
            "url": raw.get("hostedUrl", company.careers_url),
        })

    return jobs, None
