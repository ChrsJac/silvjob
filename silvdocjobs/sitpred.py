"""
silvdocjobs/sitpred.py
======================
Scraper for https://www.silvicultureinstructors.com

Collects three data sources from the public site:
  1. Tours index  – a page listing every annual tour from 1965–present
  2. Tour pages   – each year page exposes attendee names via image-tile
                    filenames (e.g. "Adam Polinko.jpg")
  3. Directory    – the public 2021 Directory, structured as <h3> person
                    headings followed by institution text

Names are normalised and matched between the tour pages and the directory.
Retired / Emeritus entries (identified by "Retired" prefix or "Emeritus"
keyword in the institution string) are kept as a separate status bucket.

Output is a JSON file whose schema is documented in sitpred.json.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import USER_AGENT, clean_text

LOGGER = logging.getLogger(__name__)
TIMEOUT = 45

SITE_BASE = "https://www.silvicultureinstructors.com"
SITE_INDEX = f"{SITE_BASE}/index.php"

DIRECTORY_VERSION_NOTE = (
    "Institutions matched from the public 2021 Directory. "
    "Affiliation may not reflect the attendee's exact institution "
    "in every tour year. Historical tour data may be incomplete "
    "per the site's own leaderboard note."
)

# Minimum SequenceMatcher.ratio() accepted as a fuzzy name match
FUZZY_THRESHOLD = 0.82

# Image file extensions whose filenames encode person names
_IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Years the SIT has been running (guard against future-year false positives)
_YEAR_RE = re.compile(r"\b(19[6-9]\d|20[0-3]\d)\b")

# Non-US country indicators present in the 2021 Directory
_NON_US_RE = re.compile(
    r"\b(canada|ontario|british columbia|alberta|quebec|\bbc\b|"
    r"australia|new zealand|new south wales|queensland|"
    r"uk|england|scotland)\b",
    re.IGNORECASE,
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DirectoryPerson:
    name_raw: str
    name_normalized: str
    institution_raw: str
    institution: str
    institution_last_known: str | None
    status_bucket: str   # "active_institution" | "retired_or_emeritus"
    country: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SitPredRecord:
    year: int
    tour: str
    person_name_raw: str
    person_name_normalized: str
    matched_directory_name: str
    institution: str
    institution_last_known: str | None
    status_bucket: str   # "active_institution" | "retired_or_emeritus" | "unmatched"
    country: str
    source_url: str

    def to_dict(self) -> dict:
        return asdict(self)


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _fetch(url: str) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text


# ── Name normalisation ────────────────────────────────────────────────────────

def normalize_name(raw: str) -> str:
    """Return a canonical lower-case form of a person name for matching."""
    name = raw.strip()
    # Strip common titles
    name = re.sub(
        r"^(Dr\.?|Prof\.?|Mr\.?|Ms\.?|Mrs\.?|Jr\.?|Sr\.?)\s+",
        "",
        name,
        flags=re.IGNORECASE,
    )
    # "Last, First" → "First Last"
    if "," in name:
        parts = name.split(",", 1)
        name = f"{parts[1].strip()} {parts[0].strip()}"
    # Replace underscores / remaining punctuation (except hyphens in names)
    name = re.sub(r"[^\w\s\-]", " ", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _match_to_directory(
    norm: str,
    directory: list[DirectoryPerson],
    exact_lookup: dict[str, DirectoryPerson],
) -> DirectoryPerson | None:
    """Exact → fuzzy → last-name+initial fallback matching."""
    # 1. Exact
    if norm in exact_lookup:
        return exact_lookup[norm]

    # 2. Fuzzy
    best: DirectoryPerson | None = None
    best_score = FUZZY_THRESHOLD - 0.001
    for person in directory:
        score = _similarity(norm, person.name_normalized)
        if score > best_score:
            best_score = score
            best = person
    if best is not None:
        return best

    # 3. Last-name + first-initial (only when unambiguous)
    parts = norm.split()
    if len(parts) >= 2:
        last = parts[-1]
        fi = parts[0][0] if parts[0] else ""
        candidates = [
            p for p in directory
            if p.name_normalized.split()
            and p.name_normalized.split()[-1] == last
            and p.name_normalized.split()[0].startswith(fi)
        ]
        if len(candidates) == 1:
            return candidates[0]

    return None


# ── Institution / status detection ───────────────────────────────────────────

def _parse_institution(raw: str) -> tuple[str, str, str | None]:
    """
    Returns (status_bucket, institution_display, institution_last_known).

    Rules (per the requirement):
      - Starts with "Retired" → retired_or_emeritus; rest of string is last_known
      - Contains "Emeritus"   → retired_or_emeritus; full string kept as last_known
    """
    raw = raw.strip()
    if re.match(r"retired\b", raw, re.IGNORECASE):
        last_known = re.sub(r"^retired[,.\s]*", "", raw, flags=re.IGNORECASE).strip()
        return "retired_or_emeritus", last_known, last_known
    if re.search(r"\bemerit", raw, re.IGNORECASE):
        return "retired_or_emeritus", raw, raw
    return "active_institution", raw, None


def _detect_country(institution: str) -> str:
    m = _NON_US_RE.search(institution)
    if not m:
        return "USA"
    tok = m.group(0).lower()
    if tok in {"canada", "ontario", "british columbia", "alberta", "quebec", "bc"}:
        return "Canada"
    if tok in {"australia", "new south wales", "queensland"}:
        return "Australia"
    if tok == "new zealand":
        return "New Zealand"
    if tok in {"uk", "england", "scotland"}:
        return "UK"
    return "Other"


# ── Directory scraping ────────────────────────────────────────────────────────

def _scrape_directory(soup: BeautifulSoup) -> list[DirectoryPerson]:
    """
    Parse the Directory page.

    Primary strategy: find all <h3> tags (person names) and collect
    the text of following siblings until the next <h3> as the institution.

    Fallback: look for <strong> or <b> tags that look like names.
    """
    people: list[DirectoryPerson] = []

    headings = soup.find_all("h3")
    for h in headings:
        name_raw = clean_text(h.get_text(" ", strip=True))
        if not name_raw or len(name_raw) < 3:
            continue
        # Skip headings that look like page section titles rather than names
        if re.search(r"\b(directory|silviculturist|roster|index|member)\b", name_raw, re.IGNORECASE):
            continue

        # Gather institution text from next siblings until next <h3>
        inst_parts: list[str] = []
        for sib in h.find_next_siblings():
            if sib.name in ("h1", "h2", "h3"):
                break
            txt = clean_text(sib.get_text(" ", strip=True))
            if txt:
                inst_parts.append(txt)
            if len(inst_parts) >= 3:
                break

        institution_raw = " ".join(inst_parts[:2]).strip()
        if not institution_raw:
            continue

        status_bucket, institution, institution_last_known = _parse_institution(institution_raw)
        country = _detect_country(institution or institution_raw)

        people.append(DirectoryPerson(
            name_raw=name_raw,
            name_normalized=normalize_name(name_raw),
            institution_raw=institution_raw,
            institution=institution,
            institution_last_known=institution_last_known,
            status_bucket=status_bucket,
            country=country,
        ))

    LOGGER.debug("Directory h3 strategy: %d entries", len(people))

    # Fallback: <strong>/<b> tags whose text looks like a person name
    if not people:
        LOGGER.info("Directory: h3 strategy empty, trying bold/strong fallback")
        for tag in soup.find_all(["strong", "b"]):
            txt = clean_text(tag.get_text(" ", strip=True))
            if not txt or len(txt) < 4 or len(txt) > 60:
                continue
            words = txt.split()
            if len(words) < 2 or not all(re.match(r"[A-Za-z'\-]", w) for w in words):
                continue
            # Institution: next sibling text
            inst_raw = ""
            nxt = tag.find_next_sibling()
            if nxt:
                inst_raw = clean_text(nxt.get_text(" ", strip=True))
            if not inst_raw and tag.parent:
                nxt = tag.parent.find_next_sibling()
                if nxt:
                    inst_raw = clean_text(nxt.get_text(" ", strip=True))
            if not inst_raw:
                continue
            status_bucket, institution, institution_last_known = _parse_institution(inst_raw)
            country = _detect_country(institution or inst_raw)
            people.append(DirectoryPerson(
                name_raw=txt,
                name_normalized=normalize_name(txt),
                institution_raw=inst_raw,
                institution=institution,
                institution_last_known=institution_last_known,
                status_bucket=status_bucket,
                country=country,
            ))

    return people


# ── Tour-page attendee scraping ───────────────────────────────────────────────

def _parse_name_from_image_path(path: str) -> str | None:
    """
    Extract a person name from an image path like "/photos/Adam Polinko.jpg"
    or "/photos/Adam%20Polinko.jpg" or "/photos/Adam_Polinko.jpg".

    Returns None when the path does not look like a person name.
    """
    decoded = urllib.parse.unquote(path)
    # Isolate the filename stem
    stem = re.split(r"[/\\]", decoded)[-1]
    stem = re.sub(
        r"\.(jpg|jpeg|png|gif|webp)$",
        "",
        stem,
        flags=re.IGNORECASE,
    )
    # Normalise separators
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()

    parts = stem.split()
    if len(parts) < 2:
        return None
    # Each part must start with a letter
    if not all(re.match(r"[A-Za-z]", p) for p in parts):
        return None
    # Reject very short segments (likely not a name)
    if any(len(p) < 2 for p in parts):
        return None
    # Reject if the stem looks like a generic filename (numbers, common words)
    generic = {"photo", "image", "img", "pic", "headshot", "portrait", "avatar"}
    if all(p.lower() in generic for p in parts):
        return None
    return stem


def _scrape_tour_page(url: str) -> list[str]:
    """
    Scrape one tour year page and return raw attendee names derived from
    image-tile filenames (the primary data source for attendees).
    """
    try:
        html = _fetch(url)
    except Exception as exc:
        LOGGER.warning("Tour page fetch failed %s: %s", url, exc)
        return []

    soup = BeautifulSoup(html, "html.parser")
    names: set[str] = set()

    # <img src="...Person Name.jpg">
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not any(src.lower().endswith(ext) for ext in _IMG_EXTS):
            continue
        name = _parse_name_from_image_path(src)
        if name:
            names.add(name)

    # <a href="...Person Name.jpg"> (image link tiles)
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not any(href.lower().endswith(ext) for ext in _IMG_EXTS):
            continue
        name = _parse_name_from_image_path(href)
        if name:
            names.add(name)

    LOGGER.debug("Tour page %s: %d names", url, len(names))
    return sorted(names)


# ── Tours index scraping ──────────────────────────────────────────────────────

def _scrape_tours_index(soup: BeautifulSoup, base_url: str) -> list[tuple[int, str, str]]:
    """
    Collect links to individual tour year pages from the Tours index.
    Returns a sorted list of (year, label, absolute_url).
    """
    tours: list[tuple[int, str, str]] = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = clean_text(a.get_text(" ", strip=True))
        url = urljoin(base_url, href)

        if url in seen_urls:
            continue

        # Must contain a valid year in text or URL
        m_text = _YEAR_RE.search(text)
        m_url = _YEAR_RE.search(href)
        if not m_text and not m_url:
            continue

        year = int((m_text or m_url).group(0))  # type: ignore[union-attr]
        now_year = datetime.now().year
        if year < 1960 or year > now_year + 1:
            continue

        # Skip pagination / boilerplate
        if len(text) < 4 or text.lower() in {
            "home", "tours", "back", "next", "previous", "index", "top",
        }:
            continue

        label = text or str(year)
        tours.append((year, label, url))
        seen_urls.add(url)

    tours.sort(key=lambda t: t[0])
    return tours


# ── Navigation discovery ──────────────────────────────────────────────────────

def _find_nav_url(soup: BeautifulSoup, base_url: str, keywords: list[str]) -> str | None:
    """Return the URL of the first nav link whose href or text matches any keyword."""
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True).lower()
        combined = f"{href.lower()} {text}"
        if any(kw in combined for kw in keywords):
            return urljoin(base_url, href)
    return None


# ── Main orchestrator ─────────────────────────────────────────────────────────

def scrape_sit_data() -> dict:
    """
    Scrape silvicultureinstructors.com and return a data dict suitable
    for serialising as docs/data/sitpred.json.

    Steps
    -----
    1. Fetch main page and discover nav URLs for Tours and Directory.
    2. Scrape the Directory to build a normalised name→institution lookup.
    3. Scrape the Tours index to enumerate all tour-year page URLs.
    4. For each tour page, collect attendee names from image filenames.
    5. Match each name to the directory; assign status_bucket.
    6. Return structured dict.
    """
    LOGGER.info("SitPred: fetching main page %s", SITE_INDEX)
    main_html = _fetch(SITE_INDEX)
    main_soup = BeautifulSoup(main_html, "html.parser")

    # ── Directory ─────────────────────────────────────────────────────────────
    dir_url = (
        _find_nav_url(main_soup, SITE_INDEX, ["directory"])
        or f"{SITE_BASE}/directory.php"
    )
    LOGGER.info("SitPred: directory URL = %s", dir_url)
    dir_html = _fetch(dir_url) if dir_url != SITE_INDEX else main_html
    dir_soup = BeautifulSoup(dir_html, "html.parser")
    directory = _scrape_directory(dir_soup)
    exact_lookup: dict[str, DirectoryPerson] = {p.name_normalized: p for p in directory}
    LOGGER.info("SitPred: %d directory entries parsed", len(directory))

    # ── Tours index ───────────────────────────────────────────────────────────
    tours_url = (
        _find_nav_url(main_soup, SITE_INDEX, ["tours", "tour index"])
        or f"{SITE_BASE}/tours.php"
    )
    LOGGER.info("SitPred: tours index URL = %s", tours_url)
    if tours_url != SITE_INDEX:
        tours_html = _fetch(tours_url)
        tours_soup = BeautifulSoup(tours_html, "html.parser")
    else:
        tours_soup = main_soup

    tour_index = _scrape_tours_index(tours_soup, tours_url)
    LOGGER.info("SitPred: %d tour year pages found", len(tour_index))

    # ── Per-tour-page scraping ────────────────────────────────────────────────
    records: list[SitPredRecord] = []
    for year, tour_label, tour_url in tour_index:
        LOGGER.info("SitPred: scraping %s (%d)", tour_label, year)
        raw_names = _scrape_tour_page(tour_url)
        for name_raw in raw_names:
            name_norm = normalize_name(name_raw)
            person = _match_to_directory(name_norm, directory, exact_lookup)
            if person:
                records.append(SitPredRecord(
                    year=year,
                    tour=tour_label,
                    person_name_raw=name_raw,
                    person_name_normalized=name_norm,
                    matched_directory_name=person.name_raw,
                    institution=person.institution,
                    institution_last_known=person.institution_last_known,
                    status_bucket=person.status_bucket,
                    country=person.country,
                    source_url=tour_url,
                ))
            else:
                records.append(SitPredRecord(
                    year=year,
                    tour=tour_label,
                    person_name_raw=name_raw,
                    person_name_normalized=name_norm,
                    matched_directory_name="",
                    institution="",
                    institution_last_known=None,
                    status_bucket="unmatched",
                    country="",
                    source_url=tour_url,
                ))
        time.sleep(0.5)  # polite delay between tour pages

    LOGGER.info(
        "SitPred: complete — %d records from %d tour pages",
        len(records),
        len(tour_index),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "directory_version_note": DIRECTORY_VERSION_NOTE,
        "tours_scraped": len(tour_index),
        "directory_entries": len(directory),
        "records": [r.to_dict() for r in records],
        "directory": [p.to_dict() for p in directory],
    }


def save_sitpred_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
