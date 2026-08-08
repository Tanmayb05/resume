#!/usr/bin/env python3
"""
Job scraper entry point.

Usage:
    python scraper/run.py --company-list tech
    python scraper/run.py --company-list cap_exempt --days 30
    python scraper/run.py --company-list tech --no-dedup   # ignore seen_jobs, show all
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Make sure the scraper package is importable when run from repo root or from this dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.core.registry import Company, load_companies
from scraper.core.dedup import load_seen, save_seen, filter_new
from scraper.core.report import generate

console = Console()

DEFAULT_DAYS = {"tech": 7, "cap_exempt": 30}
DEFAULT_MATCH_SCORE = {"tech": False, "cap_exempt": True}


def fetch_company(company: Company, client: httpx.Client, days: int) -> tuple[list[dict], str | None]:
    """Route to the correct ATS fetcher."""
    if company.ats == "greenhouse":
        from scraper.core.ats.greenhouse import fetch
        return fetch(company, client, days)
    elif company.ats == "lever":
        from scraper.core.ats.lever import fetch
        return fetch(company, client, days)
    elif company.ats == "ashby":
        from scraper.core.ats.ashby import fetch
        return fetch(company, client, days)
    elif company.ats == "workday":
        from scraper.core.ats.workday import fetch
        return fetch(company, client, days)
    elif company.ats == "custom":
        from scraper.core.ats.custom import fetch
        return fetch(company, client, days)
    elif company.ats == "blocked":
        return [], "__blocked__"
    return [], f"Unknown ATS: {company.ats}"


def main():
    parser = argparse.ArgumentParser(description="Scrape job listings from target companies/organizations.")
    parser.add_argument("--company-list", choices=["tech", "cap_exempt"], default="tech", help="Which company list to scrape (default: tech)")
    parser.add_argument("--days", type=int, default=None, help="Look back N days (default: 7 for tech, 30 for cap_exempt)")
    parser.add_argument("--no-dedup", action="store_true", help="Skip deduplication, show all matching jobs")
    match_group = parser.add_mutually_exclusive_group()
    match_group.add_argument("--match-score", dest="match_score", action="store_true", default=None, help="Force resume match-score column on")
    match_group.add_argument("--no-match-score", dest="match_score", action="store_false", help="Force resume match-score column off")
    args = parser.parse_args()

    days = args.days if args.days is not None else DEFAULT_DAYS[args.company_list]
    show_match_score = args.match_score if args.match_score is not None else DEFAULT_MATCH_SCORE[args.company_list]

    companies = load_companies(args.company_list)
    label = "organizations" if args.company_list == "cap_exempt" else "companies"
    title = "Cap-Exempt Job Scraper" if args.company_list == "cap_exempt" else "Job Scraper"

    output_dir = Path(__file__).parent / "output" / args.company_list
    seen_file = output_dir / "seen_jobs.json"
    report_path = output_dir / "jobs_report.md"

    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print(f"Looking back [bold]{days}[/bold] days across [bold]{len(companies)}[/bold] {label}\n")

    seen = set() if args.no_dedup else load_seen(seen_file)

    all_new_jobs: list[dict] = []
    blocked: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    with httpx.Client(headers=headers, follow_redirects=True, cookies=httpx.Cookies()) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching...", total=len(companies))

            for company in companies:
                progress.update(task, description=f"[cyan]{company.name:<30}[/cyan]")

                jobs, error = fetch_company(company, client, days)

                if error == "__blocked__":
                    blocked.append((company.name, company.careers_url))
                elif error:
                    errors.append((company.name, error))
                    console.print(f"  [yellow]⚠[/yellow]  {company.name}: {error}")
                else:
                    all_new_jobs.extend(jobs)

                progress.advance(task)

    # Dedup
    if not args.no_dedup:
        new_jobs, updated_seen = filter_new(all_new_jobs, seen)
        save_seen(seen_file, updated_seen)
    else:
        new_jobs = all_new_jobs

    # Group by company
    by_company: dict[str, list[dict]] = defaultdict(list)
    for job in new_jobs:
        by_company[job["company"]].append(job)

    # Generate report
    generate(by_company, blocked, errors, days=days, companies=companies, report_path=report_path, show_match_score=show_match_score)

    # Summary
    console.print()
    console.print(f"[bold green]Done![/bold green]")
    console.print(f"  New jobs found : [bold]{len(new_jobs)}[/bold]")
    console.print(f"  {label.capitalize()} with results : [bold]{len(by_company)}[/bold]")
    console.print(f"  Blocked (manual check) : [bold]{len(blocked)}[/bold]")
    if errors:
        console.print(f"  Errors : [bold yellow]{len(errors)}[/bold yellow]")
    console.print()
    console.print(f"Report → [bold]{report_path}[/bold]")
    console.print()


if __name__ == "__main__":
    main()
