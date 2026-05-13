# Personal Real Asset Research Workspace

A static personal productivity workspace for organizing real-asset investment research. It is designed for themes, companies, research notes, source links, valuation assumptions, thesis drafts, memo exports, weekly follow-up actions, and offline ingestion of long research reports.

This project is a research workflow tool. It is not a stock-picking bot, trading system, automated investment adviser, FactSet replacement, scraper, or live backend application.

## What It Does

- Turns JSON research files into a GitHub Pages-ready static site in `public/`
- Tracks real-asset themes, companies, sources, inbox notes, valuation cases, thesis drafts, memos, and weekly reviews
- Ingests Markdown, text, PDF, and structured JSON research reports without any LLM or API
- Parses headings, optional YAML frontmatter, cited sources, and follow-up sections into structured memo records
- Provides search and filters with vanilla JavaScript
- Calculates simple illustrative valuation outputs from manually entered assumptions
- Exports company data, valuation CSVs, and memo Markdown/HTML
- Keeps all data in files so the project works on GitHub Pages without a server

## Run Locally

```bash
pip install -r requirements.txt
python scripts/validate_data.py
python scripts/build_site.py
python scripts/check_site.py
```

Open `public/index.html` in your browser after the build finishes.

## Deploy To GitHub Pages

1. Push this project to GitHub.
2. In the repository, open **Settings > Pages**.
3. Set **Source** to **GitHub Actions**.
4. Open **Actions > Build and Deploy GitHub Pages**.
5. Run the workflow manually or push to `main`.

Expected project URL format:

```text
https://<github-username>.github.io/personal-real-asset-research-workspace/
```

## Ingest A Deep Research Report

Drop long research reports into:

```text
data/report_drop/new/
```

Supported v1 formats:

- `.md`
- `.txt`
- `.pdf`
- `.json`

`.docx` is intentionally marked unsupported in v1. Convert it to Markdown, text, PDF, or JSON first.

Then run locally:

```bash
python scripts/ingest_reports.py
python scripts/validate_data.py
python scripts/build_site.py
python scripts/check_site.py
```

A successful local ingestion moves the original file to `data/report_drop/processed/`, writes `outputs/report_ingestion_log.json`, updates the JSON data files, creates a memo record, and generates report pages during the next site build.

## Upload Reports Directly In GitHub

You can also upload reports directly through the GitHub web interface into:

```text
data/report_drop/new/
```

After the upload commit lands on `main`, run the Action named:

```text
Build and Deploy GitHub Pages
```

The workflow ingests uploaded reports before building the site, so the deployed Pages artifact includes the generated report pages.

Important limitation: report ingestion inside GitHub Actions does not automatically commit the updated `data/*.json` files back to the repository. The deployed site can show the generated memo, but the repo will still show the uploaded file in `data/report_drop/new/`. For permanent repository history, run ingestion locally and commit the resulting JSON changes.

Generated report pages appear in:

```text
public/reports.html
public/memos/<memo_id>.html
```

The relevant company detail page also shows the report under **Research Reports**.

## Optional Report Frontmatter

Markdown and text reports can include YAML-style frontmatter. When present, the parser uses it before falling back to deterministic inference.

```markdown
---
title: Pensana Project Valuation Analysis
company: Pensana PLC
ticker: PRE
exchange: LSE
theme: rare earths supply chain
source_type: GPT/Gemini deep research
source_tier: Tier 2
confidence: medium
status: thesis drafting
tags: [rare earths, NdPr, Angola, Longonjo, Coola]
date_added: 2026-05-13
---
```

If frontmatter is missing, the script infers title, company, ticker/exchange, source type, theme, and confidence from filenames, known companies, ticker patterns, headings, and keyword rules. Uncertain reports are flagged for manual review.

## No-LLM Parsing Rule

Report ingestion is fully offline and deterministic. It does not call OpenAI, Gemini, Claude, or any other LLM API. It does not summarize or rewrite your report. It only extracts text, maps known headings into sections, preserves source material, and flags missing structure for review.

For PDFs, text is extracted locally with `pypdf`. Complex OCR and perfect PDF table extraction are outside v1.

## Data Files

Core editable data lives in `data/`:

```text
data/
  themes.json
  companies.json
  inbox.json
  sources.json
  valuations.json
  theses.json
  memos.json
  tasks.json
  weekly_reviews.json
  report_drop/
    new/
    processed/
    failed/
  inbox_drop/
    new/
    processed/
    failed/
```

During the build, these files are copied into `public/data/` so the static site can power filters, exports, and local interactivity.

## Add A Company

```bash
python scripts/add_company.py --ticker BHP --name "BHP Group" --exchange NYSE --country Australia --company-type "producer/miner" --commodities "Copper, Iron Ore" --priority medium
```

Then run:

```bash
python scripts/validate_data.py
python scripts/build_site.py
python scripts/check_site.py
```

## Add A Theme

```bash
python scripts/add_theme.py --name "Data-center power demand" --asset-class "Energy infrastructure" --description "Research theme for power demand from AI and cloud data centers."
```

## Add A Source

```bash
python scripts/add_source.py --title "Example investor presentation" --url "https://example.com/presentation.pdf" --source-type "investor presentation" --source-tier "Tier 1" --company FCX --theme theme-copper-electrification --notes "Review production guidance and capital allocation."
```

Source tiers:

- `Tier 1`: official company, regulator, or exchange documents
- `Tier 2`: reputable financial news, analyst summaries, or industry sources
- `Tier 3`: blogs, forums, commentary, or social media

## Enter Valuation Assumptions

Edit `data/valuations.json`. Each case can include revenue, EBITDA, EBITDA margin, capex, free cash flow, discount rate, terminal multiple, enterprise value, net debt, shares outstanding, current share price, manual NPV, notes, and source evidence.

The site calculates implied enterprise value, implied equity value, implied share price, upside/downside versus current price, simple sensitivity tables, EV/EBITDA, P/NAV when manual NPV exists, and FCF yield.

All outputs are illustrative calculations only and are not financial advice.

## Build A Thesis

Edit `data/theses.json`. The thesis template includes why now, exposure, business model, valuation view, catalysts, risks, what would change my mind, evidence used, confidence, and status.

The validator screens for direct advice language and checks that company/theme links are valid.

## Export A Memo

All memos are exported during the site build. To export a single memo after editing:

```bash
python scripts/export_memo.py memo-fcx-one-page
```

Generated memo files appear in `public/memos/`. Open the HTML memo and use browser print to save as PDF.

## Project Structure

```text
.github/workflows/
data/
public/
scripts/
src/
templates/
outputs/
requirements.txt
README.md
```

## Limitations

- No live backend or database in v1
- No in-browser saving to GitHub without a backend or authenticated GitHub flow
- No paid data scraping
- No API keys in frontend JavaScript
- No LLM summarization or automatic judgment calls
- No OCR for scanned PDFs in v1
- `.docx` ingestion is unsupported in v1
- Sample valuation data is illustrative placeholder data and should be replaced with your own evidence-backed assumptions

## Suggested Next Features

- Import CSV helper for source libraries and valuation cases
- Local-only editor mode that writes JSON when run from a small development server
- More memo templates for one-page briefs, theme notes, and valuation notes
- Optional Chart.js valuation charts
- GitHub issue templates for weekly research actions
- Stronger source-evidence linking between thesis claims and source excerpts
- Optional `.docx` support through a lightweight local converter

## Safety Note

This is a personal research workflow tool for organizing evidence, assumptions, and follow-up work. It does not make investment recommendations.
