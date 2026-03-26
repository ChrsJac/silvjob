from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable

import requests
from bs4 import BeautifulSoup

from .config import SourceConfig
from .filters import classify_job, infer_job_type, TOPIC_PATTERNS, ROLE_PATTERNS, EXCLUDE_PATTERNS
from .models import JobRecord
from .utils import (
    USER_AGENT,
    absolutize,
    clean_text,
    extract_field,
    extract_first_heading_text,
    is_recent_enough,
    normalize_description,
    parse_mmddyyyy_to_iso,
)

LOGGER = logging.getLogger(__name__)
TIMEOUT = 45
# Cap detail-page requests per source to balance coverage vs. scraping time and server load
_MAX_DETAIL_PAGES = 40
# Polite delay between detail-page requests within a single source
_DETAIL_PAGE_DELAY = 0.3

# Compiled regexes for the fast candidate pre-filter
_TOPIC_RE = re.compile("|".join(TOPIC_PATTERNS.values()), re.IGNORECASE)
_ROLE_RE = re.compile("|".join(ROLE_PATTERNS.values()), re.IGNORECASE)
_EXCLUDE_RE = re.compile("|".join(EXCLUDE_PATTERNS.values()), re.IGNORECASE)


class ScraperError(RuntimeError):
    pass


def fetch_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def scrape_all_sources(sources: Iterable[SourceConfig], max_pages: int = 3, days_back: int = 120) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    seen: set[str] = set()

    for source in sources:
        if not source.enabled:
            continue
        try:
            source_jobs = scrape_source(source, max_pages=max_pages, days_back=days_back)
        except Exception as exc:
            LOGGER.exception("Source failed: %s | %s", source.name, exc)
            continue
        for job in source_jobs:
            if job.listing_url in seen:
                continue
            seen.add(job.listing_url)
            jobs.append(job)
        time.sleep(1.0)

    jobs.sort(key=lambda j: (j.date_posted == "--", j.date_posted, j.organization.lower(), j.title.lower()))
    return jobs


def scrape_source(source: SourceConfig, max_pages: int = 3, days_back: int = 120) -> list[JobRecord]:
    if source.engine == "tamu_job_board":
        return scrape_tamu_job_board(source, max_pages=max_pages, days_back=days_back)
    if source.engine == "warnell_board":
        return scrape_warnell_board(source, max_pages=max_pages, days_back=days_back)
    if source.engine == "generic_board":
        return scrape_generic_board(source, max_pages=max_pages, days_back=days_back)
    raise ScraperError(f"Unsupported engine: {source.engine}")


def scrape_tamu_job_board(source: SourceConfig, max_pages: int = 3, days_back: int = 120) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    detail_urls: set[str] = set()

    for page_num in range(1, max_pages + 1):
        page_url = re.sub(r"PageNum=\d+", f"PageNum={page_num}", source.url)
        html = fetch_html(page_url)
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "/view-job/" in href:
                detail_urls.add(absolutize(page_url, href))

    for detail_url in sorted(detail_urls):
        job = parse_tamu_detail(detail_url, source)
        if not job:
            continue
        if not is_recent_enough(job.date_posted, days_back):
            continue
        jobs.append(job)
    return jobs


def parse_tamu_detail(detail_url: str, source: SourceConfig) -> JobRecord | None:
    html = fetch_html(detail_url)
    soup = BeautifulSoup(html, "html.parser")
    full_text = clean_text(soup.get_text("\n", strip=True))

    title = extract_first_heading_text(soup)
    if title.lower().startswith("natural resources job board"):
        alt = extract_field(full_text, "View Job", ["Application Deadline", "Published", "Location", "Description"])
        if alt:
            title = alt

    organization = extract_field(full_text, title or "Details", [
        "Posting", "Application Deadline", "Published", "Starting Date", "Ending Date", "Hours per Week", "Salary",
        "Education Required", "Experience Required", "Location", "Description"
    ])
    organization = organization or source.organization

    external_posting_url = ""
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if href.startswith("http") and "jobs.rwfm.tamu.edu" not in href:
            external_posting_url = href
            break

    published = extract_field(full_text, "Published", [
        "Starting Date", "Ending Date", "Hours per Week", "Salary", "Education Required", "Experience Required",
        "Location", "Description", "Contact"
    ])
    salary = extract_field(full_text, "Salary", [
        "Education Required", "Experience Required", "Location", "Description", "Contact"
    ]) or "$--.--"
    education_required = extract_field(full_text, "Education Required", [
        "Experience Required", "Location", "Description", "Contact"
    ])
    location = extract_field(full_text, "Location", ["Description", "Contact"]) or ""
    description = extract_field(full_text, "Description", ["Contact", "A member of", "Texas A&M AgriLife"]) or full_text
    description = normalize_description(description)

    keep = classify_job(title, description, education_required)
    if not keep.keep:
        return None

    return JobRecord(
        title=title,
        organization=organization,
        source=source.name,
        listing_url=detail_url,
        external_posting_url=external_posting_url or detail_url,
        location=location,
        salary=salary,
        date_posted=parse_mmddyyyy_to_iso(published) if published else "--",
        description=description,
        job_type=infer_job_type(title, description),
        education_required=education_required,
        matched_terms=keep.matched_terms,
        matched_roles=keep.matched_roles,
    )


def scrape_warnell_board(source: SourceConfig, max_pages: int = 3, days_back: int = 120) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    detail_urls: set[str] = set()

    for page_num in range(1, max_pages + 1):
        page_url = source.url if page_num == 1 else f"{source.url}?page={page_num}"
        html = fetch_html(page_url)
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            url = absolutize(page_url, href)
            if "warnell.uga.edu/jobs" in url:
                continue
            if "warnell.uga.edu/" not in url:
                continue
            text = clean_text(link.get_text(" ", strip=True))
            if not text:
                continue
            detail_urls.add(url)

    for detail_url in sorted(detail_urls):
        job = parse_warnell_detail(detail_url, source)
        if not job:
            continue
        if not is_recent_enough(job.date_posted, days_back):
            continue
        jobs.append(job)
    return jobs


def parse_warnell_detail(detail_url: str, source: SourceConfig) -> JobRecord | None:
    html = fetch_html(detail_url)
    soup = BeautifulSoup(html, "html.parser")
    full_text = clean_text(soup.get_text("\n", strip=True))

    title = extract_first_heading_text(soup)
    if not title or title.lower() in {"jobs", "warnell school of forestry and natural resources"}:
        return None

    organization = extract_field(full_text, "Employer", [
        "Job Field", "Job Type", "Location", "Location Detail", "Salary", "Job Benefits", "Job Description", "Qualifications"
    ]) or source.organization
    date_posted = "--"
    for pattern in [r"([A-Z][a-z]{2,8} \d{1,2}, \d{4})", r"(\d{4}-\d{2}-\d{2})"]:
        m = re.search(pattern, full_text)
        if m:
            date_posted = parse_mmddyyyy_to_iso(m.group(1))
            break

    salary = extract_field(full_text, "Salary", [
        "Job Benefits", "Job Description", "Qualifications", "Preferred Qualifications", "How to Apply"
    ]) or "$--.--"
    location = extract_field(full_text, "Location Detail", [
        "Salary", "Job Benefits", "Job Description", "Qualifications", "Preferred Qualifications"
    ]) or extract_field(full_text, "Location", [
        "Location Detail", "Salary", "Job Benefits", "Job Description", "Qualifications"
    ])
    description = extract_field(full_text, "Job Description", [
        "Qualifications", "Preferred Qualifications", "How to Apply", "Deadline", "Contact"
    ]) or full_text
    description = normalize_description(description)

    external_posting_url = detail_url
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if href.startswith("http") and "warnell.uga.edu" not in href:
            external_posting_url = href
            break

    keep = classify_job(title, description, "")
    if not keep.keep:
        return None

    return JobRecord(
        title=title,
        organization=organization,
        source=source.name,
        listing_url=detail_url,
        external_posting_url=external_posting_url,
        location=location or "",
        salary=salary,
        date_posted=date_posted,
        description=description,
        job_type=infer_job_type(title, description),
        education_required="",
        matched_terms=keep.matched_terms,
        matched_roles=keep.matched_roles,
    )


def _could_be_job_candidate(title: str, context: str) -> bool:
    """Lenient pre-filter: needs at least one topic OR role keyword, and no hard exclusions."""
    text = f"{title} {context}".lower()
    if _EXCLUDE_RE.search(text):
        return False
    return bool(_TOPIC_RE.search(text) or _ROLE_RE.search(text))


def _scrape_generic_detail(url: str, link_text: str, source: SourceConfig) -> JobRecord | None:
    """Fetch a detail page and build a JobRecord if it passes full classification."""
    try:
        html = fetch_html(url)
    except Exception as exc:
        LOGGER.debug("Detail page fetch failed %s: %s", url, exc)
        return None

    soup = BeautifulSoup(html, "html.parser")
    full_text = clean_text(soup.get_text("\n", strip=True))

    title = extract_first_heading_text(soup) or link_text
    description = normalize_description(full_text)

    date_posted = extract_date_guess(full_text)

    # Try to extract a location line
    location = ""
    loc_m = re.search(r"(?:location|city|campus)\s*:?\s*([^\n,;|]{3,80})", full_text, re.IGNORECASE)
    if loc_m:
        location = clean_text(loc_m.group(1))

    keep = classify_job(title, description, "")
    if not keep.keep:
        return None

    return JobRecord(
        title=title,
        organization=source.organization,
        source=source.name,
        listing_url=url,
        external_posting_url=url,
        location=location,
        salary="$--.--",
        date_posted=date_posted,
        description=description,
        job_type=infer_job_type(title, description),
        education_required="",
        matched_terms=keep.matched_terms,
        matched_roles=keep.matched_roles,
    )


def scrape_generic_board(source: SourceConfig, max_pages: int = 2, days_back: int = 120) -> list[JobRecord]:
    """Scrape a generic job board: collect candidate links across listing pages, then
    follow each to a detail page for full classification."""
    candidate_links: list[tuple[str, str]] = []  # (absolute_url, link_text)
    seen_urls: set[str] = set()

    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            page_url = source.url
        else:
            sep = "&" if "?" in source.url else "?"
            page_url = f"{source.url}{sep}page={page_num}"

        try:
            html = fetch_html(page_url)
        except Exception as exc:
            LOGGER.debug("Listing page failed %s: %s", page_url, exc)
            break

        soup = BeautifulSoup(html, "html.parser")
        found_new = False

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = clean_text(link.get_text(" ", strip=True))
            if not href or href.startswith("#") or not text or len(text) < 6:
                continue
            url = absolutize(page_url, href)
            if not url or url in seen_urls or url == page_url or url == source.url:
                continue

            # Use surrounding paragraph/container text as extra context
            context = text
            if link.parent:
                context = clean_text(link.parent.get_text(" ", strip=True))

            if not _could_be_job_candidate(text, context):
                continue

            seen_urls.add(url)
            found_new = True
            candidate_links.append((url, text))

            if len(candidate_links) >= _MAX_DETAIL_PAGES:
                break

        if not found_new or len(candidate_links) >= _MAX_DETAIL_PAGES:
            break

    jobs: list[JobRecord] = []
    for url, link_text in candidate_links:
        job = _scrape_generic_detail(url, link_text, source)
        if not job:
            continue
        if not is_recent_enough(job.date_posted, days_back):
            continue
        jobs.append(job)
        time.sleep(_DETAIL_PAGE_DELAY)  # be polite between detail-page requests

    return jobs


def extract_date_guess(text: str) -> str:
    text = clean_text(text)
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"([A-Z][a-z]{2,8} \d{1,2}, \d{4})",
        r"(\d{2}/\d{2}/\d{4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return parse_mmddyyyy_to_iso(m.group(1))
    return "--"
