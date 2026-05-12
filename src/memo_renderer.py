from __future__ import annotations

from .utils import html_escape


def memo_to_markdown(memo: dict) -> str:
    lines = [
        f"# {memo['memo_title']}",
        "",
        f"Type: {memo['memo_type']}",
        f"Status: {memo['status']}",
        f"Updated: {memo['updated_date']}",
        "",
        "> Research workflow memo only. This is not financial advice.",
        "",
        "## Summary",
        memo.get("summary", ""),
        "",
    ]
    for section in memo.get("sections", []):
        lines.extend([f"## {section.get('heading', 'Section')}", section.get("body", ""), ""])
    return "\n".join(lines)


def memo_to_html(memo: dict, markdown_text: str) -> str:
    body = simple_markdown(markdown_text)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(memo['memo_title'])}</title>
  <link rel="stylesheet" href="../assets/styles.css">
</head>
<body class="print-page">
  <main class="memo-print">
    {body}
    <button class="button print-hidden" onclick="window.print()">Print or Save PDF</button>
  </main>
</body>
</html>
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
