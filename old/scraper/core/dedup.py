"""
Deduplication: track seen job IDs across runs in seen_jobs.json.
"""

import json
from pathlib import Path


def load_seen(seen_file: Path) -> set[str]:
    if not seen_file.exists():
        return set()
    try:
        data = json.loads(seen_file.read_text())
        return set(data.get("ids", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def save_seen(seen_file: Path, ids: set[str]) -> None:
    seen_file.parent.mkdir(parents=True, exist_ok=True)
    seen_file.write_text(json.dumps({"ids": sorted(ids)}, indent=2))


def filter_new(jobs: list[dict], seen: set[str]) -> tuple[list[dict], set[str]]:
    """
    Return only jobs whose ID is not in `seen`, plus the updated seen set.
    Each job dict must have an 'id' key.
    """
    new_jobs = [j for j in jobs if j["id"] not in seen]
    new_seen = seen | {j["id"] for j in new_jobs}
    return new_jobs, new_seen
