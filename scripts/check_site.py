from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import FORBIDDEN_ADVICE_LANGUAGE, PUBLIC_DIR

REQUIRED_MARKERS = [
    "Pensana Investment Research Dashboard",
    "Interactive Assumptions Panel",
    "Catalyst Tracker",
    "Risk Register",
    "Source Traceability",
]


def main() -> int:
    errors: list[str] = []
    index = PUBLIC_DIR / "index.html"
    if not index.exists():
        errors.append("Missing generated file: public/index.html")
    else:
        content = index.read_text(encoding="utf-8")
        lowered = content.lower()
        for marker in REQUIRED_MARKERS:
            if marker not in content:
                errors.append(f"Dashboard missing marker: {marker}")
        for forbidden in ["free" + "port", "f" + "cx", "came" + "co", "c" + "cj", "whe" + "aton", "w" + "pm", "ag" + "nico", "a" + "em"]:
            if forbidden in lowered:
                errors.append(f"Old sample company reference still present: {forbidden}")
    for required in [
        PUBLIC_DIR / "assets" / "styles.css",
        PUBLIC_DIR / "assets" / "app.js",
        PUBLIC_DIR / "data" / "pensana.json",
    ]:
        if not required.exists():
            errors.append(f"Missing generated file: {required}")
    _check_internal_links(errors)
    _check_forbidden_language(errors)
    if errors:
        print("Site check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Site check passed.")
    return 0


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
