from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_loader import load_all
from src.utils import DATA_DIR, ROOT, slugify, write_json

REPORT_DROP = DATA_DIR / "report_drop"
NEW_DIR = REPORT_DROP / "new"
PROCESSED_DIR = REPORT_DROP / "processed"
FAILED_DIR = REPORT_DROP / "failed"
OUTPUTS_DIR = ROOT / "outputs"
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".json"}

SECTION_ALIASES = {
    "executive_summary": {"executive summary", "summary"},
    "company_overview": {"company overview", "introduction", "market data", "market perception"},
    "current_valuation": {"current valuation", "valuation snapshot"},
    "key_value_drivers": {"key value drivers", "value drivers"},
    "primary_project": {"primary project", "primary project / asset", "primary asset", "main project"},
    "secondary_project": {"secondary project", "secondary project / upside", "exploration project", "upside"},
    "valuation_analysis": {"valuation", "valuation approach", "valuation analysis", "risk/reward"},
    "thesis": {"investment thesis", "thesis"},
    "catalysts": {"catalysts", "key catalysts"},
    "risks": {"risks", "risk factors"},
    "follow_up_tasks": {"follow-up tasks", "follow up tasks", "open questions", "manual review", "next steps", "what to verify"},
    "sources_or_references": {"works cited", "sources", "references"},
    "what_would_change_my_mind": {"what would change my mind"},
}
SECTION_KEYS = list(SECTION_ALIASES) + ["raw_unclassified_sections"]
THEME_RULES = [
    (("rare earths", "ndpr", "magnet metals"), "rare earths supply chain", "Rare earths"),
    (("copper", "electrification"), "copper electrification", "Copper"),
    (("uranium", "nuclear"), "uranium nuclear restart", "Uranium"),
    (("gold", "safe haven", "safe-haven"), "gold safe-haven demand", "Gold"),
    (("oil", "gas", "lng"), "energy security", "Energy"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest dropped research reports into structured company dashboard data.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input-dir", type=Path, default=NEW_DIR)
    args = parser.parse_args()
    result = ingest_reports(args.input_dir, dry_run=args.dry_run)
    print(f"Processed {result['processed_count']} report(s), failed {result['failed_count']}.")
    print(f"Log written to {OUTPUTS_DIR / 'report_ingestion_log.json'}")
    return 1 if result["failed_count"] and not result["processed_count"] else 0


def ingest_reports(input_dir: Path = NEW_DIR, dry_run: bool = False) -> dict[str, Any]:
    ensure_drop_folders()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_all()
    existing_checksums = {memo.get("checksum") for memo in data["memos"] if memo.get("checksum")}
    log: dict[str, Any] = {"dry_run": dry_run, "processed": [], "failed": []}
    for path in sorted(input_dir.iterdir() if input_dir.exists() else []):
        if path.is_dir() or path.name == ".gitkeep":
            continue
        try:
            document = read_document(path)
            if document["checksum"] in existing_checksums:
                raise ValueError("Duplicate report checksum already exists in data/memos.json.")
            parsed = parse_report(document, data)
            log["processed"].append(parsed["log"])
            if not dry_run:
                destination = unique_path(PROCESSED_DIR / path.name)
                source_file = rel_repo_path(destination)
                update_source_file(parsed, source_file)
                apply_ingestion(data, parsed)
                shutil.move(str(path), destination)
                write_all_data(data)
                write_company_dashboard_data(parsed["company_dashboard"], parsed["registry_row"])
        except Exception as exc:
            log["failed"].append({"file": str(path), "error": str(exc)})
            if not dry_run and path.exists():
                shutil.move(str(path), unique_path(FAILED_DIR / path.name))
    log["processed_count"] = len(log["processed"])
    log["failed_count"] = len(log["failed"])
    write_json(OUTPUTS_DIR / "report_ingestion_log.json", log)
    return log


def ensure_drop_folders() -> None:
    folders = [NEW_DIR, PROCESSED_DIR, FAILED_DIR, DATA_DIR / "inbox_drop" / "new", DATA_DIR / "inbox_drop" / "processed", DATA_DIR / "inbox_drop" / "failed"]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        keep = folder / ".gitkeep"
        if not keep.exists():
            keep.write_text("\n", encoding="utf-8")


def read_document(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        raise ValueError(".docx ingestion is unsupported in v1. Convert to Markdown, text, PDF, or structured JSON.")
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported report type: {suffix}")
    raw = path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    if suffix == ".pdf":
        return {"path": path, "text": extract_pdf_text(path), "frontmatter": {}, "checksum": checksum, "format": "pdf"}
    if suffix == ".json":
        payload = json.loads(raw.decode("utf-8"))
        return {
            "path": path,
            "text": payload.get("content", payload.get("text", json.dumps(payload, indent=2))),
            "frontmatter": payload.get("frontmatter", payload.get("metadata", {})),
            "checksum": checksum,
            "format": "json",
        }
    frontmatter, text = split_frontmatter(raw.decode("utf-8-sig"))
    return {"path": path, "text": text, "frontmatter": frontmatter, "checksum": checksum, "format": suffix.lstrip(".")}


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF ingestion requires pypdf. Run `pip install -r requirements.txt`, then retry.") from exc
    pages = []
    for index, page in enumerate(PdfReader(str(path)).pages, start=1):
        pages.append(f"\n\n{page.extract_text() or ''}\n\n[Page {index}]\n")
    return "\n".join(pages).strip()


def split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---", 4)
    if end == -1:
        return {}, content
    return parse_simple_yaml(content[4:end]), content[end + 4 :].lstrip()


def parse_simple_yaml(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key.strip()] = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
        else:
            data[key.strip()] = value.strip("'\"")
    return data


def parse_report(document: dict[str, Any], data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    meta = infer_metadata(document, data)
    sections = parse_sections(document["text"])
    company = ensure_company_record(meta, data)
    theme = ensure_theme_record(meta, data)
    dashboard = build_company_dashboard(meta, sections, company, document)
    registry_row = build_registry_row(dashboard)
    memo_id = stable_id("memo", meta["title"], meta.get("ticker") or meta.get("company") or document["checksum"][:8])
    source_file = rel_repo_path(PROCESSED_DIR / document["path"].name)
    manual_review = not document["frontmatter"] or not meta.get("ticker") or bool(sections.get("raw_unclassified_sections"))
    memo = {
        "memo_id": memo_id,
        "related_company": company.get("ticker", ""),
        "related_theme": theme.get("theme_id", ""),
        "memo_title": meta["title"],
        "memo_type": "deep research report",
        "source_file": source_file,
        "source_type": meta["source_type"],
        "status": meta["status"],
        "date_added": meta["date_added"],
        "updated_date": meta["date_added"],
        "last_updated": meta["date_added"],
        "sections": sections,
        "export_paths": {"markdown": f"memos/{memo_id}.md", "html": f"memos/{memo_id}.html"},
        "confidence_level": meta["confidence"],
        "manual_review_required": manual_review,
        "checksum": document["checksum"],
        "summary": first_nonempty(sections, ["executive_summary", "thesis", "company_overview"]),
    }
    source = {
        "source_id": stable_id("src", meta["title"], document["checksum"][:8]),
        "title": meta["title"],
        "url": source_file,
        "source_type": meta["source_type"],
        "source_tier": meta["source_tier"],
        "related_company": company.get("ticker", ""),
        "related_theme": theme.get("theme_id", ""),
        "date_published": meta["date_added"],
        "date_added": meta["date_added"],
        "confidence_level": meta["confidence"],
        "key_notes": "Ingested report source file.",
        "status": "needs review" if manual_review else "reviewed",
    }
    inbox_item = {
        "item_id": stable_id("inbox", meta["title"], document["checksum"][:8]),
        "title": meta["title"],
        "content": memo["summary"] or "Structured report ingested for review.",
        "source_url": source_file,
        "source_type": meta["source_type"],
        "related_company": company.get("ticker", ""),
        "related_theme": theme.get("theme_id", ""),
        "tags": meta["tags"],
        "confidence_level": meta["confidence"],
        "status": "linked to thesis",
        "date_added": meta["date_added"],
        "notes": "Created by deterministic report ingestion.",
        "important": False,
        "linked_thesis_section": "deep research report",
    }
    tasks = extract_tasks(sections, company.get("ticker", ""), theme.get("theme_id", ""), memo_id, meta["date_added"])
    cited_sources = extract_cited_sources(sections.get("sources_or_references", ""), company.get("ticker", ""), theme.get("theme_id", ""), meta)
    return {
        "company": company,
        "theme": theme,
        "memo": memo,
        "source": source,
        "inbox": inbox_item,
        "tasks": tasks,
        "cited_sources": cited_sources,
        "company_dashboard": dashboard,
        "registry_row": registry_row,
        "log": {
            "file": str(document["path"]),
            "memo_id": memo_id,
            "title": meta["title"],
            "company": company.get("ticker", ""),
            "company_slug": dashboard["slug"],
            "company_json": f"data/companies/{dashboard['slug']}.json",
            "theme": theme.get("theme_id", ""),
            "sections_detected": [key for key, value in sections.items() if value and key != "raw_unclassified_sections"],
            "manual_review_required": manual_review,
            "checksum": document["checksum"],
        },
    }


def infer_metadata(document: dict[str, Any], data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    fm = document["frontmatter"]
    text_head = "\n".join(document["text"].splitlines()[:60])
    filename_title = document["path"].stem.replace("_", " ").replace("-", " ").strip()
    title = fm.get("title") or (filename_title if document["format"] == "pdf" and filename_title else first_heading(document["text"])) or filename_title
    known = find_known_company(document["path"].name + "\n" + text_head, data)
    ticker, exchange = infer_ticker_exchange(document["path"].name + "\n" + text_head)
    source_type = fm.get("source_type") or infer_source_type(title, document["text"])
    theme_name, asset_class = infer_theme(fm.get("theme") or "", document["text"] + "\n" + title)
    return {
        "title": title,
        "company": fm.get("company") or (known or {}).get("name") or infer_company_from_text(text_head) or infer_company_from_filename(document["path"].stem),
        "ticker": fm.get("ticker") or (known or {}).get("ticker") or ticker,
        "exchange": fm.get("exchange") or (known or {}).get("exchange", "") or exchange,
        "theme": fm.get("theme") or theme_name,
        "asset_class": asset_class,
        "source_type": source_type,
        "source_tier": fm.get("source_tier") or ("Tier 2" if source_type in {"AI research output", "GPT/Gemini deep research", "research report"} else "Tier 3"),
        "confidence": fm.get("confidence") or ("medium" if source_type in {"AI research output", "GPT/Gemini deep research"} else "unreviewed"),
        "status": fm.get("status") or "thesis drafting",
        "tags": fm.get("tags") if isinstance(fm.get("tags"), list) else [],
        "date_added": fm.get("date_added") or date.today().isoformat(),
        "slug": fm.get("slug") or "",
    }


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith("[Page "):
            continue
        match = re.match(r"^\s{0,3}#{1,3}\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    for line in text.splitlines()[:8]:
        clean = line.strip()
        if 8 <= len(clean) <= 120 and not clean.startswith("[Page "):
            return clean
    return ""


def find_known_company(text: str, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    lowered = text.lower()
    return next((company for company in data["companies"] if company["ticker"].lower() in lowered or company["name"].lower() in lowered), None)


def infer_ticker_exchange(text: str) -> tuple[str, str]:
    match = re.search(r"\b([A-Z]{2,6}(?:\.[A-Z]{1,3})?):([A-Z]{2,6})\b", text)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"\b(LSE|NYSE|NASDAQ|TSX|ASX|AIM|HKEX|SGX)\s*:\s*([A-Z]{1,6})\b", text)
    if match:
        return match.group(2), match.group(1)
    match = re.search(r"\b([A-Z]{1,5}\.(?:TO|L|AX|HK))\b", text)
    return (match.group(1), "") if match else ("", "")


def infer_company_from_text(text: str) -> str:
    match = re.search(r"\b([A-Z][A-Za-z&.-]+(?:\s+[A-Z][A-Za-z&.-]+){0,4}\s+(?:PLC|Inc\.?|Corporation|Corp\.?|Ltd\.?|Limited))\b", text)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def infer_company_from_filename(stem: str) -> str:
    cleaned = re.sub(r"[_-]+", " ", stem)
    cleaned = re.sub(r"\b(valuation|analysis|research|report|project|deep)\b", "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()).strip()


def infer_source_type(title: str, text: str) -> str:
    haystack = f"{title}\n{text[:1000]}".lower()
    if any(token in haystack for token in ["gpt", "gemini", "deep research"]):
        return "AI research output"
    if "annual report" in haystack:
        return "annual report"
    if "investor presentation" in haystack:
        return "investor presentation"
    return "research report"


def infer_theme(frontmatter_theme: str, text: str) -> tuple[str, str]:
    if frontmatter_theme:
        return frontmatter_theme, frontmatter_theme.title()
    lowered = text.lower()
    for keywords, theme, asset_class in THEME_RULES:
        if any(keyword in lowered for keyword in keywords):
            return theme, asset_class
    return "", "Other"


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {key: [] for key in SECTION_KEYS}
    current = "raw_unclassified_sections"
    for line in text.splitlines():
        heading = detect_heading(line)
        if heading:
            current = map_heading(heading) or "raw_unclassified_sections"
            if current == "raw_unclassified_sections":
                sections[current].append(f"\n## {heading}\n")
            continue
        sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def detect_heading(line: str) -> str:
    stripped = line.strip().strip(":")
    if not stripped or stripped.startswith("[Page "):
        return ""
    md = re.match(r"^\s{0,3}#{1,4}\s+(.+?)\s*$", line)
    if md:
        return md.group(1).strip().strip(":")
    if len(stripped) <= 80 and not stripped.endswith(".") and re.match(r"^[A-Z][A-Za-z0-9 /&()'-]+$", stripped):
        return stripped
    return ""


def map_heading(heading: str) -> str:
    normalized = normalize_heading(heading)
    for key, aliases in SECTION_ALIASES.items():
        if normalized in {normalize_heading(alias) for alias in aliases}:
            return key
    return ""


def normalize_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def ensure_company_record(meta: dict[str, Any], data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ticker = meta.get("ticker", "")
    company_name = meta.get("company", "")
    for company in data["companies"]:
        if ticker and company["ticker"].lower() == ticker.lower():
            return company
        if company_name and company["name"].lower() == company_name.lower():
            return company
    return {
        "company_id": stable_id("co", ticker or company_name or "unknown"),
        "ticker": ticker,
        "name": company_name or ticker or "Unknown company",
        "exchange": meta.get("exchange", ""),
        "country": "",
        "company_type": "other",
        "commodities": [meta["asset_class"]] if meta.get("asset_class") and meta["asset_class"] != "Other" else [],
        "related_themes": [],
        "research_status": "thesis drafting" if ticker or company_name else "needs documents",
        "priority": "medium",
        "current_thesis_summary": "Created from ingested research report. Requires manual review.",
        "valuation_status": "needs review",
        "document_checklist_status": "report ingested",
        "memo_status": "drafting",
        "created_date": meta["date_added"],
        "last_updated": meta["date_added"],
    }


def ensure_theme_record(meta: dict[str, Any], data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    theme_name = meta.get("theme", "")
    if not theme_name:
        return {}
    for theme in data["themes"]:
        if theme["name"].lower() == theme_name.lower() or theme["theme_id"] == stable_id("theme", theme_name):
            return theme
    return {
        "theme_id": stable_id("theme", theme_name),
        "name": theme_name,
        "asset_class": meta.get("asset_class", "Other"),
        "description": "Created from deterministic report ingestion.",
        "why_it_matters": "",
        "current_affairs": "",
        "key_drivers": [],
        "risks": [],
        "related_companies": [],
        "saved_sources": [],
        "thesis_notes": "",
        "conviction_level": meta.get("confidence", "medium"),
        "status": "active research",
        "created_date": meta["date_added"],
        "last_updated": meta["date_added"],
    }


def build_company_dashboard(meta: dict[str, Any], sections: dict[str, str], company: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    source_title = meta["title"]
    project_text = sections.get("primary_project", "")
    valuation_text = sections.get("current_valuation", "") + "\n" + sections.get("valuation_analysis", "")
    market_cap = extract_money_usd_m(valuation_text, ["market cap", "market capitalisation", "market capitalization"])
    npv = extract_money_usd_m(valuation_text, ["npv", "net present value"])
    capex = extract_money_usd_m(project_text + "\n" + valuation_text, ["capex", "capital cost", "capital expenditure"])
    discount_rate = extract_percent(valuation_text, ["discount rate", "npv@"])
    commodity_price = extract_inline_value(valuation_text, ["commodity price", "price assumption"])
    production = extract_inline_value(project_text + "\n" + valuation_text, ["production", "tpa", "volume"])
    project_name = infer_project_name(project_text) or "Primary Project"
    project_stage = infer_stage(sections) or "To be updated"
    return {
        "slug": infer_company_slug(meta, company),
        "source_file": rel_repo_path(PROCESSED_DIR / document["path"].name),
        "company": {
            "name": company.get("name") or meta.get("company") or "Unknown company",
            "ticker": display_ticker(meta),
            "main_commodity": meta.get("asset_class") if meta.get("asset_class") != "Other" else "To be updated",
            "commodity_detail": meta.get("theme") or meta.get("asset_class") or "To be updated",
            "description": clean_snippet(sections.get("company_overview") or sections.get("executive_summary") or "To be updated"),
            "thesis": clean_snippet(sections.get("thesis") or sections.get("executive_summary") or "To be updated"),
            "thesis_status": meta.get("status", "thesis drafting"),
            "thesis_source": f"{source_title}, uploaded report",
            "summary_points": summary_points_from_sections(sections, source_title),
        },
        "status": {"thesis_status": meta.get("status", "thesis drafting"), "next_catalyst": first_task_or_default(sections, "To be updated"), "catalyst_date": "To be updated"},
        "industryPrimer": industry_primer(meta, sections, source_title),
        "projects": [{
            "name": project_name,
            "role": "Primary project",
            "location": infer_location(project_text),
            "development_stage": project_stage,
            "fields": [
                dashboard_field("Project name", project_name, source_title),
                dashboard_field("Location", infer_location(project_text), source_title),
                dashboard_field("Ownership", extract_inline_value(project_text, ["ownership"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Development stage", project_stage, source_title),
                dashboard_field("Resource / reserve information", extract_inline_value(project_text, ["resource", "reserve"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Expected production", production or "Not disclosed in uploaded report", source_title),
                dashboard_field("Mine life / project life", extract_inline_value(project_text, ["mine life", "project life"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Capex", money_text(capex), source_title),
                dashboard_field("Opex", extract_inline_value(valuation_text, ["opex", "operating cost"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Processing / refining details", extract_inline_value(project_text, ["processing", "refining"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Infrastructure requirements", extract_inline_value(project_text, ["infrastructure", "power", "rail", "port"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Permitting status", extract_inline_value(project_text, ["permit", "permitting"]) or "To be updated", source_title),
                dashboard_field("Financing status", extract_inline_value(project_text + "\n" + sections.get("catalysts", ""), ["financing", "funding"]) or "To be updated", source_title),
                dashboard_field("Offtake agreements", extract_inline_value(project_text + "\n" + sections.get("catalysts", ""), ["offtake"]) or "To be updated", source_title),
                dashboard_field("Government support", extract_inline_value(project_text + "\n" + sections.get("catalysts", ""), ["government support", "government"]) or "To be updated", source_title),
                dashboard_field("Next milestones", first_task_or_default(sections, "To be updated"), source_title),
            ],
        }],
        "valuation": {
            "market_cap_usd_m": market_cap,
            "market_cap_note": "Extracted from uploaded report where detected." if market_cap is not None else "To be updated",
            "project_npv_usd_m": npv,
            "npv_note": "Extracted from uploaded report where detected." if npv is not None else "To be updated",
            "fields": [
                dashboard_field("Market capitalisation", money_text(market_cap), source_title),
                dashboard_field("Latest stated NPV", money_text(npv), source_title),
                dashboard_field("Discount rate used", percent_text(discount_rate), source_title),
                dashboard_field("Commodity price assumption", commodity_price or "Not disclosed in uploaded report", source_title),
                dashboard_field("Initial capex", money_text(capex), source_title),
                dashboard_field("Sustaining capex", extract_inline_value(valuation_text, ["sustaining capex"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Operating cost assumptions", extract_inline_value(valuation_text, ["operating cost", "opex"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Projected revenue", extract_inline_value(valuation_text, ["revenue"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("EBITDA", extract_inline_value(valuation_text, ["ebitda"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Cash balance / debt", extract_inline_value(valuation_text, ["cash", "debt"]) or "Not disclosed in uploaded report", source_title),
                dashboard_field("Funding gap", extract_inline_value(valuation_text, ["funding gap"]) or "To be updated", source_title),
                dashboard_field("Estimated P/NPV", pnpv_text(market_cap, npv), source_title, "calculated"),
            ],
        },
        "userAssumptions": {
            "market_cap_usd_m": market_cap if market_cap is not None else "",
            "project_npv_usd_m": npv if npv is not None else "",
            "discount_rate_pct": discount_rate if discount_rate is not None else "",
            "capex_usd_m": capex if capex is not None else "",
            "opex": extract_inline_value(valuation_text, ["opex", "operating cost"]) or "To be updated",
            "commodity_price": commodity_price or "To be updated",
            "production_volume": production or "To be updated",
            "projectStatus": status_from_text(project_stage),
            "financingStatus": "Unknown",
            "permittingStatus": "Unknown",
            "offtakeStatus": "Unknown",
            "governmentSupportStatus": "Unknown",
            "next_catalyst": first_task_or_default(sections, "To be updated"),
            "catalyst_date": "To be updated",
            "notes": "Local edits are stored in this browser only.",
        },
        "catalysts": catalyst_rows(sections, source_title),
        "risks": risk_rows(sections, source_title),
        "sources": source_rows(sections, source_title),
    }


def build_registry_row(dashboard: dict[str, Any]) -> dict[str, Any]:
    project = (dashboard.get("projects") or [{}])[0]
    valuation = dashboard.get("valuation", {})
    risks = dashboard.get("risks") or []
    return {
        "slug": dashboard["slug"],
        "company_name": dashboard["company"]["name"],
        "ticker": dashboard["company"].get("ticker", ""),
        "commodity": dashboard["company"].get("main_commodity", "To be updated"),
        "project": project.get("name", "To be updated"),
        "stage": project.get("development_stage", "To be updated"),
        "market_cap_usd_m": valuation.get("market_cap_usd_m"),
        "project_npv_usd_m": valuation.get("project_npv_usd_m"),
        "next_catalyst": dashboard.get("status", {}).get("next_catalyst", "To be updated"),
        "risk_level": risks[0].get("severity", "Medium") if risks else "Medium",
    }


def apply_ingestion(data: dict[str, list[dict[str, Any]]], parsed: dict[str, Any]) -> None:
    upsert(data["companies"], parsed["company"], "company_id")
    if parsed["theme"]:
        upsert(data["themes"], parsed["theme"], "theme_id")
    upsert(data["memos"], parsed["memo"], "memo_id")
    upsert(data["sources"], parsed["source"], "source_id")
    upsert(data["inbox"], parsed["inbox"], "item_id")
    for source in parsed["cited_sources"]:
        upsert(data["sources"], source, "source_id")
    for task in parsed["tasks"]:
        upsert(data["tasks"], task, "task_id")


def update_source_file(parsed: dict[str, Any], source_file: str) -> None:
    parsed["memo"]["source_file"] = source_file
    parsed["source"]["url"] = source_file
    parsed["inbox"]["source_url"] = source_file
    parsed["company_dashboard"]["source_file"] = source_file


def write_company_dashboard_data(dashboard: dict[str, Any], registry_row: dict[str, Any]) -> None:
    company_dir = DATA_DIR / "companies"
    company_dir.mkdir(parents=True, exist_ok=True)
    write_json(company_dir / f"{dashboard['slug']}.json", dashboard)
    registry_path = DATA_DIR / "company_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
    upsert(registry, registry_row, "slug")
    registry.sort(key=lambda row: row.get("company_name", "").lower())
    write_json(registry_path, registry)


def write_all_data(data: dict[str, list[dict[str, Any]]]) -> None:
    for key, rows in data.items():
        filename = "weekly_reviews.json" if key == "weekly_reviews" else f"{key}.json"
        write_json(DATA_DIR / filename, rows)


def extract_tasks(sections: dict[str, str], ticker: str, theme_id: str, memo_id: str, added: str) -> list[dict[str, Any]]:
    lines = rows_from_lines(sections.get("follow_up_tasks", ""))
    if not lines:
        lines = ["Review valuation assumptions", "Verify cited sources", "Check latest company filings", "Confirm current market cap and share price"]
    return [{"task_id": stable_id("task", memo_id, str(index), task), "task": task, "related_company": ticker, "related_theme": theme_id, "priority": "medium", "due_date": added, "status": "open", "notes": "Created by deterministic report ingestion.", "source": "report_ingestion_rule", "source_memo": memo_id} for index, task in enumerate(lines, start=1)]


def extract_cited_sources(content: str, ticker: str, theme_id: str, meta: dict[str, Any]) -> list[dict[str, Any]]:
    sources = []
    for line in content.splitlines():
        clean = clean_list_line(line)
        if not clean:
            continue
        url_match = re.search(r"https?://\S+", clean)
        url = url_match.group(0).rstrip(").,") if url_match else ""
        title = clean.replace(url, "").strip(" -") or url or "Untitled cited source"
        sources.append({"source_id": stable_id("src", title, url or "needs-url"), "title": title, "url": url, "source_type": "cited source", "source_tier": meta["source_tier"], "related_company": ticker, "related_theme": theme_id, "date_published": meta["date_added"], "date_added": meta["date_added"], "confidence_level": meta["confidence"], "key_notes": "Parsed from report works cited." if url else "Parsed from report works cited. Needs URL verification.", "status": "needs review"})
    return sources


def summary_points_from_sections(sections: dict[str, str], source_title: str) -> list[list[str]]:
    points: list[list[str]] = []
    for key in ["executive_summary", "company_overview", "key_value_drivers", "thesis"]:
        for sentence in split_sentences(sections.get(key, ""))[:2]:
            points.append([sentence, f"{source_title}, uploaded report"])
            if len(points) >= 5:
                return points
    return points or [["Needs manual review after report ingestion.", f"{source_title}, uploaded report"]]


def industry_primer(meta: dict[str, Any], sections: dict[str, str], source_title: str) -> list[dict[str, str]]:
    commodity = meta.get("asset_class") if meta.get("asset_class") != "Other" else "To be updated"
    overview = clean_snippet(sections.get("company_overview", "")) or clean_snippet(sections.get("executive_summary", ""))
    return [
        {"label": "Commodity Exposure", "value": commodity, "source": f"{source_title}, uploaded report"},
        {"label": "Main Uses", "value": meta.get("theme") or "To be updated", "source": f"{source_title}, uploaded report"},
        {"label": "Demand Drivers", "value": clean_snippet(sections.get("key_value_drivers", "")) or "To be updated", "source": f"{source_title}, uploaded report"},
        {"label": "Supply Chain Relevance", "value": overview or "To be updated", "source": f"{source_title}, uploaded report"},
        {"label": "Why Investors Care", "value": "Review the extracted thesis, valuation, catalyst, and risk sections.", "source": f"{source_title}, uploaded report"},
        {"label": "How The Sector Is Valued", "value": "Use disclosed NPV, capex, production, cash flow, and P/NPV fields where provided.", "source": f"{source_title}, uploaded report"},
    ]


def catalyst_rows(sections: dict[str, str], source_title: str) -> list[dict[str, str]]:
    rows = rows_from_lines(sections.get("catalysts", "")) or rows_from_lines(sections.get("follow_up_tasks", "")) or ["Review uploaded report for near-term catalysts"]
    return [{"catalyst": row, "type": infer_catalyst_type(row), "expected_timing": "To be updated", "status": "Unknown", "importance": "Medium", "notes": "Parsed from uploaded report. Edit this row after review.", "source": f"{source_title}, uploaded report"} for row in rows[:8]]


def risk_rows(sections: dict[str, str], source_title: str) -> list[dict[str, str]]:
    rows = rows_from_lines(sections.get("risks", "")) or ["Validate financing, execution, commodity price, and source-document risks"]
    return [{"risk": row, "category": infer_risk_category(row), "severity": "Medium", "status": "Unknown", "why_it_matters": "Parsed from uploaded report or created as a review item.", "mitigation": "Add mitigation or monitoring notes after review.", "source": f"{source_title}, uploaded report"} for row in rows[:8]]


def source_rows(sections: dict[str, str], source_title: str) -> list[dict[str, str]]:
    rows = rows_from_lines(sections.get("sources_or_references", ""))
    if not rows:
        return [{"id": "S1", "title": source_title, "page": "Uploaded report", "note": "Original uploaded report"}]
    return [{"id": f"S{index}", "title": row, "page": "Uploaded report", "note": "Parsed from works cited"} for index, row in enumerate(rows[:12], start=1)]


def rows_from_lines(content: str) -> list[str]:
    lines = [clean_snippet(clean_list_line(line), 240) for line in content.splitlines()]
    cleaned = [line for line in lines if line and not line.startswith("|")]
    return cleaned or split_sentences(content)[:6]


def infer_company_slug(meta: dict[str, Any], company: dict[str, Any]) -> str:
    source = meta.get("slug") or company.get("name") or meta.get("company") or meta.get("ticker") or meta["title"]
    slug = slugify(str(source).lower())
    for suffix in ["-plc", "-inc", "-corp", "-corporation", "-ltd", "-limited"]:
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
    return slug or "unknown-company"


def display_ticker(meta: dict[str, Any]) -> str:
    ticker = meta.get("ticker", "")
    exchange = meta.get("exchange", "")
    return f"{ticker}:{exchange}" if ticker and exchange and ":" not in ticker else ticker


def infer_project_name(text: str) -> str:
    for line in text.splitlines()[:8]:
        clean = clean_list_line(line).strip("#: ")
        if 4 <= len(clean) <= 80 and not clean.endswith("."):
            return clean
    return ""


def infer_location(text: str) -> str:
    match = re.search(r"\b(?:located in|location[:\s]+|in)\s+([A-Z][A-Za-z ,.-]{2,40})", text, re.IGNORECASE)
    return clean_snippet(match.group(1), 80) if match else "To be updated"


def infer_stage(sections: dict[str, str]) -> str:
    text = "\n".join(sections.values()).lower()
    if "production" in text:
        return "Production / ramp-up mentioned"
    if "construction" in text:
        return "Construction / development in progress"
    if "feasibility" in text:
        return "Feasibility / development"
    if "exploration" in text:
        return "Exploration"
    return ""


def extract_money_usd_m(text: str, labels: list[str]) -> float | None:
    lowered = text.lower()
    for label in labels:
        position = lowered.find(label)
        if position == -1:
            continue
        match = re.search(r"(?:US\$|\$|USD\s*)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(bn|billion|m|mn|million)?", text[position : position + 260], re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(",", ""))
            return value * 1000 if (match.group(2) or "m").lower() in {"bn", "billion"} else value
    return None


def extract_percent(text: str, labels: list[str]) -> float | None:
    lowered = text.lower()
    for label in labels:
        position = lowered.find(label)
        if position == -1:
            continue
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", text[position : position + 160])
        if match:
            return float(match.group(1))
    return None


def extract_inline_value(text: str, labels: list[str]) -> str:
    for line in text.splitlines():
        if any(label in line.lower() for label in labels):
            return clean_snippet(clean_list_line(line), 220)
    return ""


def first_task_or_default(sections: dict[str, str], default: str) -> str:
    lines = rows_from_lines(sections.get("follow_up_tasks", "")) or rows_from_lines(sections.get("catalysts", ""))
    return lines[0] if lines else default


def dashboard_field(label: str, value: Any, source_title: str, state: str = "extracted") -> dict[str, str]:
    return {"label": label, "value": value if value not in (None, "") else "Not disclosed in uploaded report", "source": f"{source_title}, uploaded report", "state": state}


def money_text(value: float | None) -> str:
    if value is None:
        return "Not disclosed in uploaded report"
    return f"US${value:,.2f}m" if value < 1000 else f"US${value:,.0f}m"


def percent_text(value: float | None) -> str:
    return f"{value:g}%" if value is not None else "Not disclosed in uploaded report"


def pnpv_text(market_cap: float | None, npv: float | None) -> str:
    if not market_cap or not npv:
        return "Incomplete: Market Capitalisation / Project NPV"
    return f"{market_cap / npv:.2f}x based on Market Capitalisation / Project NPV"


def status_from_text(value: str) -> str:
    lowered = value.lower()
    if "construction" in lowered or "progress" in lowered:
        return "In progress"
    if "production" in lowered:
        return "Pending"
    return "Unknown"


def infer_catalyst_type(value: str) -> str:
    lowered = value.lower()
    if "financ" in lowered or "fund" in lowered:
        return "Financing"
    if "permit" in lowered:
        return "Permitting"
    if "offtake" in lowered:
        return "Offtake"
    if "construct" in lowered:
        return "Construction"
    if "production" in lowered or "commission" in lowered:
        return "Production"
    if "resource" in lowered or "reserve" in lowered or "drill" in lowered:
        return "Resource update"
    if "partner" in lowered:
        return "Strategic partnership"
    return "Other"


def infer_risk_category(value: str) -> str:
    lowered = value.lower()
    if "financ" in lowered or "fund" in lowered or "dilution" in lowered:
        return "Financing risk"
    if "permit" in lowered:
        return "Permitting risk"
    if "price" in lowered or "commodity" in lowered:
        return "Commodity price risk"
    if "jurisdiction" in lowered or "country" in lowered:
        return "Jurisdiction risk"
    if "technical" in lowered or "resource" in lowered or "metallurg" in lowered:
        return "Technical risk"
    if "offtake" in lowered:
        return "Offtake risk"
    return "Execution risk"


def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    return [clean_snippet(sentence, 260) for sentence in re.split(r"(?<=[.!?])\s+", compact) if len(sentence.strip()) > 8]


def clean_snippet(value: str, limit: int = 800) -> str:
    compact = re.sub(r"\s+", " ", str(value)).strip()
    return compact if len(compact) <= limit else compact[: limit - 3].rstrip() + "..."


def clean_list_line(line: str) -> str:
    return re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()


def first_nonempty(sections: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if sections.get(key):
            return sections[key][:800]
    return ""


def upsert(rows: list[dict[str, Any]], row: dict[str, Any], key: str) -> None:
    if not row:
        return
    for index, existing in enumerate(rows):
        if existing.get(key) == row.get(key):
            rows[index] = row
            return
    rows.append(row)


def stable_id(prefix: str, *parts: str) -> str:
    base = "-".join(slugify(str(part).lower()) for part in parts if part)
    return f"{prefix}-{base}"[:96].rstrip("-") or f"{prefix}-unknown"


def rel_repo_path(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


if __name__ == "__main__":
    raise SystemExit(main())
