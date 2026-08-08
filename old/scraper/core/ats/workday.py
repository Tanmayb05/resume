"""
Workday scraper.
Workday exposes a JSON search API at:
  https://{host}/wday/cxs/{tenant}/{board}/jobs

URL format in registry: https://{tenant}.wd12.myworkdayjobs.com/en-US/{board}
"""

from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx

from scraper.core.filters import matches_role, get_experience_level, matches_location, is_recent
from scraper.core.registry import Company

# Workday "Posted Today/Yesterday/N Days Ago" → approximate days offset
_POSTED_MAP = {
    "posted today": 0,
    "posted yesterday": 1,
}


def _parse_posted(raw: str | None) -> datetime | None:
    """Parse Workday's human-readable posted string into a datetime."""
    if not raw:
        return None
    s = raw.lower().strip()
    if s in _POSTED_MAP:
        from datetime import timedelta
        return datetime.now(timezone.utc) - timedelta(days=_POSTED_MAP[s])
    # "posted N days ago"
    import re
    m = re.search(r"(\d+)\s+day", s)
    if m:
        from datetime import timedelta
        return datetime.now(timezone.utc) - timedelta(days=int(m.group(1)))
    return None


def _build_search_url(base_url: str) -> str:
    """
    Convert registry URL like:
      https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site
    to:
      https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/jobs
    """
    parsed = urlparse(base_url)
    host = parsed.netloc                        # salesforce.wd12.myworkdayjobs.com
    tenant = host.split(".")[0]                 # salesforce
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    # path is like ['en-US', 'External_Career_Site']
    board = path_parts[-1] if path_parts else "jobs"
    return f"https://{host}/wday/cxs/{tenant}/{board}/jobs"


def fetch(company: Company, client: httpx.Client, days: int = 7) -> tuple[list[dict], str | None]:
    base_url = company.slug_or_url.rstrip("/")
    parsed = urlparse(base_url)
    host = parsed.netloc
    tenant = host.split(".")[0]
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    board = path_parts[-1] if path_parts else "jobs"

    search_url = f"https://{host}/wday/cxs/{tenant}/{board}/jobs"

    payload = {
        "appliedFacets": {},
        "limit": 100,
        "offset": 0,
        "searchText": "",
    }

    origin = f"https://{host}"
    careers_page = f"{origin}/{'/'.join(path_parts)}"

    try:
        # Workday requires session cookies set by the careers page.
        # Use a fresh client per company to avoid cross-domain cookie pollution.
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
        }
        with httpx.Client(headers=base_headers, follow_redirects=True) as wd_client:
            wd_client.get(careers_page, headers={"Accept": "text/html"}, timeout=15)
            resp = wd_client.post(
                search_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Origin": origin,
                    "Referer": careers_page,
                },
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        return [], f"HTTP {e.response.status_code}"
    except Exception as e:
        return [], str(e)

    raw_jobs = data.get("jobPostings", [])
    jobs = []

    for raw in raw_jobs:
        title = raw.get("title", "")
        if not matches_role(title):
            continue

        level = get_experience_level(title)
        if level is None:
            continue

        location = raw.get("locationsText", raw.get("primaryLocation", ""))
        if not matches_location(location):
            continue

        posted_at = _parse_posted(raw.get("postedOn"))
        if not is_recent(posted_at, days):
            continue

        external_path = raw.get("externalPath", "")
        job_url = f"https://{host}{external_path}" if external_path else company.careers_url

        bullet = (raw.get("bulletFields") or [""])[0]
        job_id = f"wd-{tenant}-{bullet or title[:30]}"

        jobs.append({
            "id": job_id,
            "company": company.name,
            "title": title,
            "level": level,
            "location": location or "Remote",
            "posted_at": posted_at,
            "url": job_url,
        })

    return jobs, None
