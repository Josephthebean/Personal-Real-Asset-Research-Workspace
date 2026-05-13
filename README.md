# Real Asset Investment Research Platform

A static, multi-company research platform for real-asset investment work. The homepage is a company screener, and each company has its own generated dashboard page.

Pensana is the first company entry. It now lives in a reusable company JSON file rather than a hardcoded one-off page.

## Structure

```text
data/
  company_registry.json
  companies/
    pensana.json
    example_company_template.json
```

`company_registry.json` powers the homepage screener. Each file in `data/companies/` powers one company dashboard.

Generated pages:

```text
public/index.html
public/company/pensana.html
```

## Company JSON

Each company JSON can include company summary, commodity exposure, industry primer, projects, valuation, catalysts, risks, sources, and user assumptions.

Use `data/companies/example_company_template.json` when adding the next company.

## Interactivity

Each dashboard preserves editable valuation and status fields. Edits are stored in browser `localStorage` with a company-specific key:

```text
company-dashboard-<slug>-v1
```

That keeps edits for one company separate from every other company.

## Run Locally

```bash
pip install -r requirements.txt
python scripts/validate_data.py
python scripts/build_site.py
python scripts/check_site.py
```

Open `public/index.html`.

## Add A New Company

1. Copy `data/companies/example_company_template.json`.
2. Rename it to `data/companies/<company-slug>.json`.
3. Fill in the company data and source references.
4. Add a row to `data/company_registry.json`.
5. Rebuild the site.

## Deploy To GitHub Pages

1. Push changes to GitHub.
2. In repository settings, set Pages source to **GitHub Actions**.
3. Run the Action named **Build and Deploy GitHub Pages**.

## Boundaries

- No external APIs.
- No live market data.
- No LLM calls.
- No automatic recommendations.
- Calculations are illustrative research workflow outputs only.
