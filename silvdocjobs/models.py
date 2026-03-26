from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class JobRecord:
    title: str
    organization: str
    source: str
    listing_url: str
    external_posting_url: str = ""
    location: str = ""
    salary: str = "$--.--"
    date_posted: str = "--"
    description: str = ""
    job_type: str = ""
    education_required: str = ""
    matched_terms: list[str] = field(default_factory=list)
    matched_roles: list[str] = field(default_factory=list)
    date_scraped: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
