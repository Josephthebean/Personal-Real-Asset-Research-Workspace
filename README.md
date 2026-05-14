# Real Asset Investment Research Platform

A static, multi-company research platform for real-asset investment work. The homepage is a company screener, and each company has its own generated dashboard page.

Pensana is the first company entry. It lives in a reusable company JSON file rather than a hardcoded one-off page.

## Structure

```text
data/
  company_registry.json
  companies/
    pensana.json
    example_company_template.json
  report_drop/
    new/
    processed/
    failed/
```

`company_registry.json` powers the homepage screener. Each file in `data/companies/` powers one company dashboard.

Generated pages:

```text
public/index.html
public/company/pensana.html
public/company/<company-slug>.html
```

## Company JSON

Each company JSON can include company summary, commodity exposure, industry primer, projects, valuation, catalysts, risks, sources, and user assumptions.

Use `data/companies/example_company_template.json` when manually adding the next company.

## Interactivity

Each dashboard preserves editable valuation and status fields. Edits are stored in browser `localStorage` with a company-specific key:

```text
company-dashboard-<slug>-v1
```

That keeps edits for one company separate from every other company.

## Run Locally

```bash
pip install -r requirements.txt
python scripts/ingest_reports.py
python scripts/validate_data.py
python scripts/build_site.py
python scripts/check_site.py
```

Open `public/index.html`.

## Add A New Company From A Report

1. Add a Markdown, text, PDF, or structured JSON report to:

```text
data/report_drop/new/
```

2. Commit the uploaded report to GitHub.
3. Run the **Build and Deploy GitHub Pages** Action.

The workflow runs `scripts/ingest_reports.py` before building the site. The ingestion step:

- extracts report text locally;
- infers basic metadata using deterministic rules;
- creates or updates `data/companies/<company-slug>.json`;
- creates or updates `data/company_registry.json`;
- moves the report into `data/report_drop/processed/` inside the build workspace;
- generates the homepage screener and company dashboard page.

No LLM or external API is used.

For cleaner results, add YAML frontmatter to Markdown or text reports:

```yaml
---
title: Company Deep Research Report
company: Example Minerals PLC
ticker: EXM
exchange: LSE
theme: rare earths supply chain
source_type: GPT/Gemini deep research
source_tier: Tier 2
confidence: medium
status: thesis drafting
tags: [rare earths, NdPr]
date_added: 2026-05-13
---
```

## Add A New Company Manually

1. Copy `data/companies/example_company_template.json`.
2. Rename it to `data/companies/<company-slug>.json`.
3. Fill in the company data and source references.
4. Add a row to `data/company_registry.json`.
5. Rebuild the site.

## Deploy To GitHub Pages

1. Push changes to GitHub.
2. In repository settings, set Pages source to **GitHub Actions**.
3. Run the Action named **Build and Deploy GitHub Pages**.

## Important Build Note

When GitHub Actions ingests a newly uploaded report, the generated company JSON is included in the deployed Pages artifact. It is not automatically committed back to the repository. If you want the generated JSON stored in GitHub, run ingestion locally and commit the generated files, or add a later write-back workflow.

## Boundaries

- No external APIs.
- No live market data.
- No LLM calls.
- No automatic recommendations.
- Calculations are illustrative research workflow outputs only.
