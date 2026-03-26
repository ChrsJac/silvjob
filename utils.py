from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

USER_AGENT = "SilvDocJobs/0.1 (academic job monitoring; replace-with-your-email@example.com)"


def absolutize(base_url: str, maybe_relative: str | None) -> str:
    if not maybe_relative:
        return ""
    return urljoin(base_url, maybe_relative)


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    value = html.unescape(value)
    value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_description(text: str) -> str:
    text = clean_text(text)
    noise_patterns = [
        r"\bopen in new window\b",
        r"\bour sponsors and partners\b",
        r"\ba member of\b.*$",
        r"\bshare this\b.*$",
        r"\bapply now\b",
        r"\bbookmark\b",
        r"\bsearch job board database\b.*?\bresults:\b",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_first_heading_text(soup: BeautifulSoup) -> str:
    for tag in ["h1", "h2", "h3", "title"]:
        node = soup.find(tag)
        if node:
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                return text
    return ""


def extract_field(text: str, label: str, stop_labels: list[str]) -> str:
    stop_pattern = "|".join(re.escape(label_) for label_ in stop_labels)
    pattern = rf"{re.escape(label)}\s*:?\s*(.+?)(?=(?:{stop_pattern})\s*:|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return clean_text(match.group(1))


def parse_mmddyyyy_to_iso(value: str) -> str:
    value = clean_text(value)
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value or "--"


def is_recent_enough(date_posted: str, days_back: int) -> bool:
    if not date_posted or date_posted == "--":
        return True
    try:
        posted = datetime.fromisoformat(date_posted).date()
    except ValueError:
        return True
    cutoff = datetime.utcnow().date() - timedelta(days=days_back)
    return posted >= cutoff


def compact_json(data: list[dict]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
