from __future__ import annotations

import json
from pathlib import Path

from .models import JobRecord


def save_jobs_json(path: str | Path, jobs: list[JobRecord]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [job.to_dict() for job in jobs]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
