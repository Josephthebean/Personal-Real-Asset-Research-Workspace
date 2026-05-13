# Pensana Investment Research Dashboard

A static, single-company investment research dashboard for reviewing Pensana PLC using one uploaded source: `data/report_drop/processed/Pensana Project Valuation Analysis_.pdf`.

This version removes the earlier multi-company sample workspace. It is a focused research memo and assumptions dashboard, not a stock-picking bot, trading system, investment adviser, live data feed, or FactSet replacement.

## What The Site Shows

- Pensana company summary
- Rare earth / NdPr industry primer
- Longonjo and Coola project details
- Report-derived valuation fields
- P/NPV calculation
- Editable assumptions panel
- Editable catalyst tracker
- Editable risk register
- Source references back to the uploaded Pensana report

Missing figures are shown as `Not disclosed in uploaded report` or `To be updated`.

## Data Source

The structured dashboard data lives in `data/pensana.json`. Compatibility JSON files are reduced to Pensana-only records so older sample companies are not generated.

## Run Locally

```bash
pip install -r requirements.txt
python scripts/validate_data.py
python scripts/build_site.py
python scripts/check_site.py
```

Open `public/index.html`.

## Edit Assumptions On The Page

The dashboard supports local edits for market cap, project NPV, discount rate, capex, opex, commodity price assumption, production volume, project status, financing status, permitting status, offtake status, government support status, next catalyst, catalyst date, and notes.

Edits are stored in browser `localStorage`. Use **Reset to report values** to restore the extracted baseline.

## P/NPV

```text
P/NPV = Market Capitalisation / Project NPV
```

Both inputs can be updated in the assumptions panel. If either value is missing, the dashboard marks the calculation incomplete.

## Deploy To GitHub Pages

1. Push changes to GitHub.
2. In repository settings, set Pages source to **GitHub Actions**.
3. Run the Action named **Build and Deploy GitHub Pages**.

## Limitations

- No external APIs or live market data.
- No LLM summarization.
- No automatic fact invention.
- No persistent in-browser editing beyond localStorage.
- Only Pensana is active in this version.

## Safety Note

This is a personal research workflow tool for organizing evidence, assumptions, and follow-up work. It does not make investment recommendations.
