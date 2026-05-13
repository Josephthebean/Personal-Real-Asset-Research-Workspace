from __future__ import annotations

import json, re
from pathlib import Path
from typing import Any
from .data_loader import DATA_FILES, load_all
from .utils import DATA_DIR, contains_forbidden_language, parse_date

THEME_STATUSES = {"exploring", "active research", "monitoring", "thesis drafted", "archived"}
RESEARCH_STATUSES = {"new idea", "researching", "needs documents", "needs valuation", "thesis drafting", "watchlist", "rejected", "archived"}
SOURCE_TIERS = {"Tier 1", "Tier 2", "Tier 3"}
MEMO_SECTION_KEYS = {"executive_summary","company_overview","current_valuation","key_value_drivers","primary_project","secondary_project","valuation_analysis","thesis","catalysts","risks","follow_up_tasks","sources_or_references","what_would_change_my_mind","raw_unclassified_sections"}

def _strings(value: Any) -> list[str]:
    if isinstance(value, str): return [value]
    if isinstance(value, list): return [s for item in value for s in _strings(item)]
    if isinstance(value, dict): return [s for item in value.values() for s in _strings(item)]
    return []

def _date(errors: list[str], label: str, value: str | None) -> None:
    try: parse_date(value or "")
    except ValueError: errors.append(f"Invalid date for {label}: {value}")

def validate_data(data_dir: Path = DATA_DIR) -> list[str]:
    errors: list[str] = []
    for filename in DATA_FILES.values():
        path = data_dir / filename
        if not path.exists(): errors.append(f"Missing required data file: {path}"); continue
        try: json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc: errors.append(f"Invalid JSON in {filename}: {exc}")
    if errors: return errors
    data = load_all(data_dir); companies = {c["company_id"]: c for c in data["companies"]}; tickers = {c["ticker"] for c in data["companies"]}; themes = {t["theme_id"]: t for t in data["themes"]}; memo_ids=set()
    for c in data["companies"]:
        if not c.get("ticker") or not c.get("name"): errors.append("Each company must have ticker and name.")
        if c.get("research_status") not in RESEARCH_STATUSES: errors.append(f"Invalid research status for {c.get('ticker')}")
        _date(errors, c.get("ticker", "company"), c.get("last_updated"))
    for t in data["themes"]:
        if t.get("status") not in THEME_STATUSES: errors.append(f"Invalid theme status for {t.get('theme_id')}")
        for ticker in t.get("related_companies", []):
            if ticker not in tickers: errors.append(f"Unknown company ticker {ticker} in theme {t.get('theme_id')}")
    for s in data["sources"]:
        if s.get("source_tier") not in SOURCE_TIERS: errors.append(f"Invalid source tier for {s.get('source_id')}")
        if s.get("related_company") and s["related_company"] not in tickers: errors.append(f"Unknown company in source {s.get('source_id')}")
        if s.get("related_theme") and s["related_theme"] not in themes: errors.append(f"Unknown theme in source {s.get('source_id')}")
        if s.get("url") and not valid_url_or_path(s["url"]): errors.append(f"Invalid source URL/path for {s.get('source_id')}: {s.get('url')}")
    for memo in data["memos"]:
        mid = memo.get("memo_id")
        if not mid: errors.append("Memo record missing memo_id."); continue
        if mid in memo_ids: errors.append(f"Duplicate memo_id: {mid}")
        memo_ids.add(mid)
        if memo.get("related_company") and memo["related_company"] not in tickers: errors.append(f"Memo {mid} links to unknown company {memo['related_company']}")
        if memo.get("related_theme") and memo["related_theme"] not in themes: errors.append(f"Memo {mid} links to unknown theme {memo['related_theme']}")
        sections = memo.get("sections", [])
        if isinstance(sections, dict):
            invalid = set(sections) - MEMO_SECTION_KEYS
            if invalid: errors.append(f"Memo {mid} has invalid section keys: {', '.join(sorted(invalid))}")
    for thesis in data["theses"]:
        if thesis.get("company_id") and thesis["company_id"] not in companies: errors.append(f"Unknown company in thesis {thesis.get('thesis_id')}")
        if thesis.get("theme_id") and thesis["theme_id"] not in themes: errors.append(f"Unknown theme in thesis {thesis.get('thesis_id')}")
    for val in data["valuations"]:
        if not val.get("valuation_id") or val.get("company_id") not in companies: errors.append(f"Invalid valuation case {val.get('valuation_id')}")
    for name, rows in data.items():
        for i, row in enumerate(rows):
            for text in _strings(row):
                found = contains_forbidden_language(text)
                if found: errors.append(f"Forbidden advice language in {name}[{i}]: {', '.join(found)}")
    return errors

def valid_url_or_path(value: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+$", value)) or value.startswith(("data/", "public/", "outputs/")) or (not value) or (" " not in value and "\n" not in value)
