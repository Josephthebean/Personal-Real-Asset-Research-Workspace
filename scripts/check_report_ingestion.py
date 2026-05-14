from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = """---
title: Sample Rare Earths Report
company: Sample Minerals PLC
ticker: SMP
exchange: LSE
theme: rare earths supply chain
source_type: GPT/Gemini deep research
source_tier: Tier 2
confidence: medium
status: thesis drafting
date_added: 2026-05-13
---

## Executive Summary
Sample report.

## Current Valuation
| Metric | Value |
| --- | --- |
| Market cap | Placeholder |

## Primary Project
Primary project text.

## Investment Thesis
Thesis text.

## Follow-up Tasks
- Verify cited sources
- Check latest company filings

## Works Cited
- Company announcement https://example.com/company-announcement
"""


def main() -> int:
    log_path = ROOT / "outputs" / "report_ingestion_log.json"
    previous = log_path.read_text(encoding="utf-8") if log_path.exists() else None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "new"
            input_dir.mkdir()
            (input_dir / "sample.md").write_text(SAMPLE, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "scripts/ingest_reports.py", "--dry-run", "--input-dir", str(input_dir)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            return result.returncode
        log = json.loads(log_path.read_text(encoding="utf-8"))
        if log.get("processed_count") != 1:
            print("Expected one processed dry-run report.")
            return 1
        entry = log["processed"][0]
        required = {"executive_summary", "current_valuation", "primary_project", "thesis", "follow_up_tasks", "sources_or_references"}
        missing = required - set(entry.get("sections_detected", []))
        if missing:
            print(f"Missing detected sections: {sorted(missing)}")
            return 1
        if not entry.get("memo_id"):
            print("Dry-run did not produce a memo id.")
            return 1
        if not entry.get("company_slug") or not entry.get("company_json"):
            print("Dry-run did not produce a company dashboard target.")
            return 1
        print("Report ingestion check passed.")
        return 0
    finally:
        if previous is not None:
            log_path.write_text(previous, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
