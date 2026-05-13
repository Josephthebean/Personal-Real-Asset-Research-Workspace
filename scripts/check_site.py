from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import FORBIDDEN_ADVICE_LANGUAGE, PUBLIC_DIR


def main() -> int:
    errors: list[str] = []
    registry_path = PUBLIC_DIR / "data" / "company_registry.json"
    if not registry_path.exists():
        errors.append("Missing generated file: public/data/company_registry.json")
        registry = []
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    _must_contain(errors, PUBLIC_DIR / "index.html", ["Investment Research Screener", "Company Screener", "Pensana PLC"])
    for row in registry:
        slug = row["slug"]
        _must_contain(
            errors,
            PUBLIC_DIR / "company" / f"{slug}.html",
            ["Research Dashboard", "Interactive Assumptions Panel", "Catalyst Tracker", "Risk Register", "Source Traceability", f"company-dashboard-{slug}-v1"],
        )
        if not (PUBLIC_DIR / "data" / "companies" / f"{slug}.json").exists():
            errors.append(f"Missing copied company JSON for {slug}.")
    _check_internal_links(errors)
    _check_forbidden_language(errors)
    if errors:
        print("Site check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Site check passed.")
    return 0


def _must_contain(errors: list[str], path: Path, markers: list[str]) -> None:
    if not path.exists():
        errors.append(f"Missing generated file: {path}")
        return
    content = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in content:
            errors.append(f"{path} missing marker: {marker}")


def _check_internal_links(errors: list[str]) -> None:
    href_re = re.compile(r'href="([^"]+)"')
    for html in PUBLIC_DIR.rglob("*.html"):
        for href in href_re.findall(html.read_text(encoding="utf-8")):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (html.parent / href.split("#", 1)[0]).resolve()
            if not target.exists():
                errors.append(f"Broken internal link in {html}: {href}")


def _check_forbidden_language(errors: list[str]) -> None:
    for path in PUBLIC_DIR.rglob("*"):
        if path.suffix.lower() not in {".html", ".js", ".css", ".json", ".md"}:
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_ADVICE_LANGUAGE:
            if phrase in lowered:
                errors.append(f"Forbidden advice language found in {path}: {phrase}")


if __name__ == "__main__":
    raise SystemExit(main())
