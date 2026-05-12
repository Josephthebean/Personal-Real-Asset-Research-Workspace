# Personal Real Asset Research Workspace

A static personal productivity workspace for organizing real-asset investment research. It is designed for themes, companies, research notes, source links, valuation assumptions, thesis drafts, memo exports, and weekly follow-up actions.

This project is a research workflow tool. It is not a stock-picking bot, trading system, automated investment adviser, FactSet replacement, scraper, or live backend application.

## What It Does

- Turns JSON research files into a GitHub Pages-ready static site in `public/`
- Tracks real-asset themes, companies, sources, inbox notes, valuation cases, thesis drafts, memos, and weekly reviews
- Provides search and filters with vanilla JavaScript
- Calculates simple illustrative valuation outputs from manually entered assumptions
- Exports company data, valuation CSVs, and memo Markdown/HTML
- Keeps all data in files so the project works on GitHub Pages without a server

## Run Locally

```bash
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
requirements.txt
README.md
```

## Limitations

- No live backend or database in v1
- No in-browser saving to GitHub without a backend or authenticated GitHub flow
- No paid data scraping
- No API keys in frontend JavaScript
- Sample valuation data is illustrative placeholder data and should be replaced with your own evidence-backed assumptions

## Suggested Next Features

- Import CSV helper for source libraries and valuation cases
- Local-only editor mode that writes JSON when run from a small development server
- More memo templates for one-page briefs, theme notes, and valuation notes
- Optional Chart.js valuation charts
- GitHub issue templates for weekly research actions
- Stronger source-evidence linking between thesis claims and source excerpts

## Safety Note

This is a personal research workflow tool for organizing evidence, assumptions, and follow-up work. It does not make investment recommendations.
