from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import DATA_DIR, read_json


DATA_FILES = {
    "themes": "themes.json",
    "companies": "companies.json",
    "inbox": "inbox.json",
    "sources": "sources.json",
    "valuations": "valuations.json",
    "theses": "theses.json",
    "memos": "memos.json",
    "tasks": "tasks.json",
    "weekly_reviews": "weekly_reviews.json",
}


def load_all(data_dir: Path = DATA_DIR) -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {}
    for key, filename in DATA_FILES.items():
        data[key] = read_json(data_dir / filename)
    return data
