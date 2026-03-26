from __future__ import annotations

import argparse
import logging
from pathlib import Path

from silvdocjobs.config import SOURCES
from silvdocjobs.scrapers import scrape_all_sources
from silvdocjobs.storage import save_jobs_json
from silvdocjobs.site import build_static_site
from silvdocjobs.sitpred import scrape_sit_data, save_sitpred_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SilvDocJobs data and static site.")
    parser.add_argument("--output-json", default="docs/data/jobs.json", help="Path to JSON output.")
    parser.add_argument("--max-pages", type=int, default=3, help="Maximum pages to inspect for paginated sources.")
    parser.add_argument("--days-back", type=int, default=120, help="Keep only recent postings when a date is available.")
    parser.add_argument("--source", action="append", help="Optional source names to run.")
    parser.add_argument("--skip-sitpred", action="store_true", help="Skip the SitPred (silvicultureinstructors.com) scrape.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s | %(message)s")

    selected = set(args.source or [])
    sources = [s for s in SOURCES if not selected or s.name in selected]

    jobs = scrape_all_sources(sources=sources, max_pages=args.max_pages, days_back=args.days_back)
    save_jobs_json(args.output_json, jobs)
    build_static_site(output_dir=Path("docs"), jobs=jobs)
    logging.info("Jobs: wrote %d records to %s", len(jobs), args.output_json)

    if not args.skip_sitpred:
        try:
            sitpred_data = scrape_sit_data()
            save_sitpred_json("docs/data/sitpred.json", sitpred_data)
            logging.info(
                "SitPred: %d records from %d tour pages, %d directory entries",
                len(sitpred_data["records"]),
                sitpred_data["tours_scraped"],
                sitpred_data["directory_entries"],
            )
        except Exception:
            logging.exception("SitPred scrape failed (non-fatal) — jobs data unaffected")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
