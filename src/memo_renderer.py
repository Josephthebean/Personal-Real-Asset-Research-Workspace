from __future__ import annotations

from .utils import html_escape


def memo_to_markdown(memo: dict) -> str:
    title = memo.get("memo_title") or memo.get("title", "Research Memo")
    updated = memo.get("updated_date") or memo.get("last_updated") or memo.get("date_added", "")
    lines = [f"# {title}", "", f"Type: {memo.get('memo_type', 'memo')}", f"Status: {memo.get('status', '')}", f"Updated: {updated}", "", "> Research workflow memo only. This is not financial advice.", "", "## Summary", memo.get("summary", ""), ""]
    sections = memo.get("sections", [])
    if isinstance(sections, dict):
        for key, body in sections.items():
            lines.extend([f"## {key.replace('_', ' ').title()}", body or "Not included in uploaded report.", ""])
    else:
        for section in sections:
            lines.extend([f"## {section.get('heading', 'Section')}", section.get("body", ""), ""])
    return "\n".join(lines)


def memo_to_html(memo: dict, markdown_text: str) -> str:
    body = simple_markdown(markdown_text)
    title = memo.get("memo_title") or memo.get("title", "Research Memo")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)}</title><link rel="stylesheet" href="../assets/styles.css"></head>
<body class="print-page"><main class="memo-print">{body}<button class="button print-hidden" onclick="window.print()">Print or Save PDF</button></main></body></html>
"""


def simple_markdown(markdown_text: str) -> str:
    html: list[str] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            html.append(f"<h1>{html_escape(line[2:])}</h1>")
        elif line.startswith("## "):
            html.append(f"<h2>{html_escape(line[3:])}</h2>")
        elif line.startswith("> "):
            html.append(f"<blockquote>{html_escape(line[2:])}</blockquote>")
        else:
            html.append(f"<p>{html_escape(line)}</p>")
    return "\n".join(html)
