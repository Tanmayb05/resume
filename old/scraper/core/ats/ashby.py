"""
Ashby Jobs Board API fetcher.
Public API: https://api.ashbyhq.com/posting-api/job-board/{slug}
"""

from datetime import datetime, timezone
import httpx

from scraper.core.filters import matches_role, get_experience_level, matches_location, is_recent
from scraper.core.registry import Company

BASE = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def fetch(company: Company, client: httpx.Client, days: int = 7) -> tuple[list[dict], str | None]:
    url = BASE.format(slug=company.slug_or_url)
    try:
        resp = client.get(url, params={"includeCompensation": "true"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        return [], f"HTTP {e.response.status_code}"
    except Exception as e:
        return [], str(e)

    jobs = []
    for raw in data.get("jobPostings", []):
        title = raw.get("title", "")
        if not matches_role(title):
            continue

        level = get_experience_level(title)
        if level is None:
            continue

        location = raw.get("locationName", raw.get("location", ""))
        if not matches_location(location):
            continue

        posted_at = _parse_date(raw.get("publishedDate") or raw.get("updatedAt"))
        if not is_recent(posted_at, days):
            continue

        job_id = raw.get("id", "")
        job_url = raw.get("jobUrl") or raw.get("applyUrl") or company.careers_url

        jobs.append({
            "id": f"ash-{job_id}",
            "company": company.name,
            "title": title,
            "level": level,
            "location": location or "Remote",
            "posted_at": posted_at,
            "url": job_url,
        })

    return jobs, None
