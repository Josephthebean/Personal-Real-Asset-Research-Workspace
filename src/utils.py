from __future__ import annotations

import json, re, shutil
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"
FORBIDDEN_ADVICE_LANGUAGE = ["you should buy", "sell now", "guaranteed return", "risk-free", "definitely invest", "sure winner"]

def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().replace("/", "-")).strip("-")

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")

def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

def copy_data_files() -> None:
    target = PUBLIC_DIR / "data"
    target.mkdir(parents=True, exist_ok=True)
    for path in DATA_DIR.glob("*.json"):
        shutil.copy2(path, target / path.name)
    if (DATA_DIR / "local").exists():
        shutil.copytree(DATA_DIR / "local", target / "local", dirs_exist_ok=True)
    processed = DATA_DIR / "report_drop" / "processed"
    if processed.exists():
        report_target = target / "report_drop" / "processed"
        report_target.mkdir(parents=True, exist_ok=True)
        for path in processed.iterdir():
            if path.is_file() and path.name != ".gitkeep" and path.stat().st_size <= 5_000_000:
                shutil.copy2(path, report_target / path.name)

def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")

def html_escape(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)

def badge(value: str, kind: str = "neutral") -> str:
    return f'<span class="badge badge-{kind}">{html_escape(value)}</span>'

def comma(values):
    return ", ".join(values) if isinstance(values, list) else values

def contains_forbidden_language(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in FORBIDDEN_ADVICE_LANGUAGE if phrase in lowered]
