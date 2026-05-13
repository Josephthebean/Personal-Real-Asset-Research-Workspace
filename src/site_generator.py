from __future__ import annotations

import json, os, shutil, stat
from typing import Any
from .utils import DATA_DIR, PUBLIC_DIR, copy_data_files, html_escape, write_text

DASHBOARD_NAV=[('Overview','#overview'),('Summary','#summary'),('Industry','#industry'),('Projects','#projects'),('Valuation','#valuation'),('Assumptions','#assumptions'),('Catalysts','#catalysts'),('Risks','#risks'),('Sources','#sources')]

def build_site()->None:
    registry=load_registry(); companies=[load_company(row['slug']) for row in registry]
    if PUBLIC_DIR.exists(): shutil.rmtree(PUBLIC_DIR,onexc=lambda f,p,e:(os.chmod(p,stat.S_IWRITE),f(p)))
    (PUBLIC_DIR/'assets').mkdir(parents=True,exist_ok=True); (PUBLIC_DIR/'company').mkdir(parents=True,exist_ok=True)
    copy_data_files(); write_assets(); write_text(PUBLIC_DIR/'index.html',company_screener_page(registry))
    for company in companies: write_text(PUBLIC_DIR/'company'/f"{company['slug']}.html",company_dashboard_page(company))

def load_registry(): return json.loads((DATA_DIR/'company_registry.json').read_text(encoding='utf-8'))
def load_company(slug): return json.loads((DATA_DIR/'companies'/f'{slug}.json').read_text(encoding='utf-8'))

def layout(title,body,nav,subtitle='Multi-company real asset research platform'):
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)}</title><link rel="stylesheet" href="assets/styles.css"><script defer src="assets/app.js"></script></head><body><aside class="sidebar"><div class="brand">Real Asset Research</div><nav>{nav}</nav></aside><main class="main"><header class="topbar"><div><p class="eyebrow">{html_escape(subtitle)}</p><h1>{html_escape(title)}</h1></div><div class="safety-note">Research dashboard only. Not financial advice. No external APIs or live data.</div></header>{body}</main></body></html>'

def company_screener_page(registry):
    nav='<a class="nav-link active" href="index.html">Company Screener</a>'; rows=[]
    for row in registry:
        rows.append([f'<a href="company/{html_escape(row["slug"])}.html"><strong>{html_escape(row["company_name"])}</strong></a><small>{html_escape(row["ticker"])}</small>',html_escape(row['commodity']),html_escape(row['project']),chip(row['stage'],'blue'),money(row.get('market_cap_usd_m')),money(row.get('project_npv_usd_m')),pnpv_ratio(row.get('market_cap_usd_m'),row.get('project_npv_usd_m')) or 'Incomplete',html_escape(row['next_catalyst']),chip(row['risk_level'],risk_tone(row['risk_level']))])
    body=f'<section class="panel"><div class="section-head"><h2>Company Screener</h2><span>{len(registry)} active company</span></div><div class="toolbar"><input data-table-search type="search" placeholder="Search company, commodity, stage, catalyst"></div>{table(["Company","Commodity","Project","Stage","Market Cap","Project NPV","P/NPV","Next Catalyst","Risk"],rows)}</section><section class="panel"><h2>Add The Next Company</h2><p>Copy <code>data/companies/example_company_template.json</code>, rename it to the new company slug, then add one row to <code>data/company_registry.json</code>.</p></section>'
    return layout('Investment Research Screener',body,nav)

def company_dashboard_page(data):
    nav='<a class="nav-link" href="../index.html">Company Screener</a>'+''.join(f'<a class="nav-link" href="{h}">{html_escape(l)}</a>' for l,h in DASHBOARD_NAV)
    return layout(f"{data['company']['name']} Research Dashboard",company_dashboard(data),nav,'Reusable company dashboard').replace('href="assets/','href="../assets/').replace('src="assets/','src="../assets/')

def company_dashboard(data):
    company=data['company']; project=data.get('projects',[{}])[0]; valuation=data['valuation']
    cards=[('Company',company['name'],company['ticker'],'extracted'),('Main Exposure',company['main_commodity'],company.get('commodity_detail',''),'extracted'),('Primary Project',project.get('name','To be updated'),project.get('location',''),'extracted'),('Development Stage',project.get('development_stage','To be updated'),'editable below','extracted'),('Market Cap',money(valuation.get('market_cap_usd_m')),valuation.get('market_cap_note',''),'extracted'),('Latest Stated NPV',money(valuation.get('project_npv_usd_m')),valuation.get('npv_note',''),'extracted'),('P/NPV',pnpv_ratio(valuation.get('market_cap_usd_m'),valuation.get('project_npv_usd_m')) or 'Incomplete','Market cap / Project NPV','calculated'),('Next Catalyst',data['status'].get('next_catalyst','To be updated'),data['status'].get('catalyst_date',''),'user-updated')]
    return f'<section id="overview" class="metric-grid" data-company-slug="{html_escape(data["slug"])}">{"".join(metric_card(*c) for c in cards)}</section><section class="panel thesis-panel"><div class="section-head"><h2>Overall Research Thesis</h2>{chip(data["status"].get("thesis_status","To be updated"),"blue")}</div><p>{html_escape(company.get("thesis","To be updated"))}</p><p class="source-line">{source(company.get("thesis_source","To be updated"))}</p></section>{summary_section(data)}{industry_section(data)}{projects_section(data)}{valuation_section(data)}{assumptions_section(data)}{catalyst_section(data)}{risk_section(data)}{sources_section(data)}'

def summary_section(data):
    company=data['company']; bullets=''.join(f'<li>{html_escape(item)} {source(src)}</li>' for item,src in company.get('summary_points',[]))
    return f'<section id="summary" class="panel"><div class="section-head"><h2>Company Summary</h2>{chip("extracted report data","green")}</div><p>{html_escape(company.get("description","To be updated"))}</p><ul class="memo-list">{bullets}</ul></section>'

def industry_section(data):
    cards=''.join(f'<article class="card"><h3>{html_escape(x["label"])}</h3><p>{html_escape(x["value"])}</p><p class="source-line">{source(x["source"])}</p></article>' for x in data.get('industryPrimer',[]))
    return f'<section id="industry" class="panel"><div class="section-head"><h2>Commodity And Industry Primer</h2>{chip(data["company"]["main_commodity"],"blue")}</div><div class="cards">{cards}</div></section>'

def projects_section(data):
    out=[]
    for p in data.get('projects',[]):
        rows=''.join(field_row(f['label'],f['value'],f['source'],f.get('state','extracted')) for f in p.get('fields',[]))
        out.append(f'<article class="project-card"><div class="section-head"><h3>{html_escape(p["name"])}</h3>{chip(p["role"],"blue")}</div><div class="field-grid">{rows}</div></article>')
    return f'<section id="projects" class="panel"><div class="section-head"><h2>Project Details</h2><span>Reusable structured project fields</span></div>{"".join(out)}</section>'

def valuation_section(data):
    rows=''.join(field_row(x['label'],x['value'],x['source'],x.get('state','extracted')) for x in data['valuation'].get('fields',[]))
    return f'<section id="valuation" class="panel"><div class="section-head"><h2>Financials And Valuation</h2>{chip("illustrative calculations","amber")}</div><p class="callout">P/NPV = Market Capitalisation / Project NPV. Outputs use company JSON values or user-edited local assumptions.</p><div class="field-grid">{rows}</div></section>'

def assumptions_section(data):
    a=data['userAssumptions']; opts=['Not started','Pending','In progress','Completed','Delayed','Unknown']; inputs=[]
    fields=[('Market cap (USD m)','marketCapUsdM',a.get('market_cap_usd_m','')),('Project NPV (USD m)','projectNpvUsdM',a.get('project_npv_usd_m','')),('Discount rate (%)','discountRatePct',a.get('discount_rate_pct','')),('Capex (USD m)','capexUsdM',a.get('capex_usd_m','')),('Opex','opex',a.get('opex','')),('Commodity price assumption','commodityPrice',a.get('commodity_price','')),('Production volume','productionVolume',a.get('production_volume',''))]
    for label,key,value in fields:
        typ='number' if isinstance(value,(int,float)) else 'text'; step=' step="0.01"' if typ=='number' else ''
        inputs.append(f'<label>{html_escape(label)}<input data-assumption="{key}" type="{typ}"{step} value="{html_escape(value)}"></label>')
    for label,key in [('Project status','projectStatus'),('Financing status','financingStatus'),('Permitting status','permittingStatus'),('Offtake status','offtakeStatus'),('Government support status','governmentSupportStatus')]:
        current=a.get(key,'Unknown'); option_html=''.join(f'<option {"selected" if o==current else ""}>{html_escape(o)}</option>' for o in opts)
        inputs.append(f'<label>{html_escape(label)}<select data-assumption="{key}">{option_html}</select></label>')
    inputs.append(f'<label>Next catalyst<input data-assumption="nextCatalyst" value="{html_escape(a.get("next_catalyst",""))}"></label>')
    inputs.append(f'<label>Catalyst date<input data-assumption="catalystDate" value="{html_escape(a.get("catalyst_date",""))}"></label>')
    inputs.append(f'<label class="wide">Notes<textarea data-assumption="notes">{html_escape(a.get("notes",""))}</textarea></label>')
    defaults=html_escape(json.dumps(js_defaults(a)))
    return f'<section id="assumptions" class="panel" data-dashboard-root data-company-slug="{html_escape(data["slug"])}" data-storage-key="company-dashboard-{html_escape(data["slug"])}-v1" data-default-assumptions="{defaults}"><div class="section-head"><h2>Interactive Assumptions Panel</h2><button class="button secondary" data-reset-dashboard>Reset to report values</button></div><div class="assumption-grid">{"".join(inputs)}</div><div class="calc-strip"><strong>Updated P/NPV: <span data-output="pnpv"></span></strong><span data-output="calcNote"></span></div></section>'

def catalyst_section(data):
    rows=[[html_escape(x['catalyst']),html_escape(x['type']),html_escape(x['expected_timing']),select_cell(x['status']),html_escape(x['importance']),editable_text(x['notes']),source(x['source'])] for x in data.get('catalysts',[])]
    return f'<section id="catalysts" class="panel"><div class="section-head"><h2>Catalyst Tracker</h2>{chip("editable local state","blue")}</div>{table(["Catalyst","Type","Expected Timing","Current Status","Importance","Notes","Source"],rows)}</section>'

def risk_section(data):
    rows=[[html_escape(x['risk']),html_escape(x['category']),select_cell(x['severity'],['Low','Medium','High','Critical']),select_cell(x['status']),html_escape(x['why_it_matters']),editable_text(x['mitigation']),source(x['source'])] for x in data.get('risks',[])]
    return f'<section id="risks" class="panel"><div class="section-head"><h2>Risk Register</h2>{chip("editable local state","amber")}</div>{table(["Risk","Category","Severity","Current Status","Why It Matters","Mitigation / Watch Item","Source"],rows)}</section>'

def sources_section(data):
    rows=[[html_escape(s['id']),html_escape(s['title']),html_escape(s['page']),html_escape(s['note'])] for s in data.get('sources',[])]
    return f'<section id="sources" class="panel"><div class="section-head"><h2>Source Traceability</h2><span>{html_escape(data.get("source_file","Company JSON sources"))}</span></div>{table(["Ref","Source","Page","Note"],rows)}</section>'

def js_defaults(a):
    return {'marketCapUsdM':a.get('market_cap_usd_m',''),'projectNpvUsdM':a.get('project_npv_usd_m',''),'discountRatePct':a.get('discount_rate_pct',''),'capexUsdM':a.get('capex_usd_m',''),'opex':a.get('opex',''),'commodityPrice':a.get('commodity_price',''),'productionVolume':a.get('production_volume',''),'projectStatus':a.get('projectStatus','Unknown'),'financingStatus':a.get('financingStatus','Unknown'),'permittingStatus':a.get('permittingStatus','Unknown'),'offtakeStatus':a.get('offtakeStatus','Unknown'),'governmentSupportStatus':a.get('governmentSupportStatus','Unknown'),'nextCatalyst':a.get('next_catalyst',''),'catalystDate':a.get('catalyst_date',''),'notes':a.get('notes','')}

def metric_card(label,value,note,state): return f'<article class="metric-card {html_escape(state)}"><span>{html_escape(label)}</span><strong data-card="{html_escape(label)}">{html_escape(value)}</strong><small>{html_escape(note)}</small></article>'
def field_row(label,value,src,state): return f'<div class="field {html_escape(state)}"><span>{html_escape(label)}</span><strong>{html_escape(value if value not in ("",None) else "Not disclosed in uploaded report")}</strong><small>{source(src)}</small></div>'
def table(headers,rows): return f'<div class="table-wrap"><table data-search-table><thead><tr>{"".join(f"<th>{html_escape(h)}</th>" for h in headers)}</tr></thead><tbody>{"".join("<tr>"+"".join(f"<td>{c}</td>" for c in row)+"</tr>" for row in rows)}</tbody></table></div>'
def select_cell(value,options=None):
    options=options or ['Not started','Pending','In progress','Completed','Delayed','Unknown']; return '<select data-editable-cell>'+''.join(f'<option {"selected" if o==value else ""}>{html_escape(o)}</option>' for o in options)+'</select>'
def editable_text(value): return f'<textarea data-editable-cell>{html_escape(value)}</textarea>'
def chip(value,tone): return f'<span class="chip chip-{tone}">{html_escape(value)}</span>'
def risk_tone(value): return {'Low':'green','Medium':'amber','High':'red','Critical':'red'}.get(value,'blue')
def source(ref): return f'<span class="source-ref">Source: {html_escape(ref)}</span>'
def money(value):
    if value is None or value=='': return 'To be updated'
    return f'US${value:,.2f}m' if value<1000 else f'US${value:,.0f}m'
def pnpv_ratio(market_cap,npv): return f'{market_cap/npv:.2f}x' if market_cap and npv else ''

def write_assets(): write_text(PUBLIC_DIR/'assets'/'styles.css',CSS); write_text(PUBLIC_DIR/'assets'/'app.js',APP_JS); write_text(PUBLIC_DIR/'assets'/'charts.js','/* Reserved for future charts. */\n')

CSS=r''':root{--navy:#003366;--bg:#F7F9FC;--card:#fff;--border:#D8E0EA;--muted:#667085;--blue:#2563EB;--amber:#F59E0B;--green:#16A34A;--red:#DC2626;--text:#172033}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.5}a{color:var(--blue);text-decoration:none}code{background:#eef2ff;border:1px solid var(--border);border-radius:6px;padding:2px 5px}h1,h2,h3{margin:0;letter-spacing:0;color:#10203b}.sidebar{position:fixed;inset:0 auto 0 0;width:250px;background:var(--navy);color:#fff;padding:22px 16px;overflow:auto}.brand{font-size:18px;font-weight:800;margin-bottom:22px}.nav-link{display:block;color:#dbeafe;padding:10px 12px;border-radius:6px;margin:3px 0}.nav-link.active,.nav-link:hover{background:rgba(255,255,255,.14);color:#fff}.main{margin-left:250px;padding:28px;min-height:100vh}.topbar{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:22px}.eyebrow{margin:0 0 4px;color:var(--muted);font-size:12px;font-weight:800;text-transform:uppercase}.safety-note,.callout{border:1px solid var(--border);border-radius:8px;background:#fff7ed;color:#7c2d12;padding:10px 12px;font-size:13px}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-bottom:18px}.metric-card,.panel,.card,.project-card{background:var(--card);border:1px solid var(--border);border-radius:8px}.metric-card{padding:16px;border-left:4px solid var(--border)}.metric-card.extracted,.field.extracted{border-left-color:var(--green)}.metric-card.calculated,.field.calculated{border-left-color:var(--blue)}.metric-card.user-updated,.field.user-updated{border-left-color:var(--amber)}.metric-card span,.field span{display:block;color:var(--muted);font-size:12px;font-weight:800;text-transform:uppercase}.metric-card strong{display:block;font-size:24px;margin:6px 0}.metric-card small,.field small,.source-line,td small{color:var(--muted)}td small{display:block}.panel{padding:18px;margin-bottom:18px}.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}.toolbar{margin-bottom:14px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.card,.project-card{padding:16px}.field-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.field{border:1px solid var(--border);border-left:4px solid var(--border);border-radius:8px;padding:12px;background:#fff}.field strong{display:block;margin:6px 0}.assumption-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.wide{grid-column:1/-1}input,select,textarea{width:100%;border:1px solid var(--border);border-radius:8px;background:#fff;color:var(--text);padding:10px}textarea{min-height:72px;resize:vertical}.calc-strip{display:flex;justify-content:space-between;gap:14px;margin-top:14px;padding:14px;border:1px solid #bfdbfe;border-radius:8px;background:#eff6ff}.button{border:0;border-radius:8px;background:var(--blue);color:#fff;padding:10px 14px;font-weight:800;cursor:pointer}.button.secondary{background:#eef2ff;color:#1e3a8a}.chip{display:inline-block;border:1px solid var(--border);border-radius:999px;padding:4px 8px;font-size:12px;font-weight:800}.chip-blue{background:#dbeafe;color:#1d4ed8}.chip-green{background:#ecfdf5;color:#047857}.chip-amber{background:#fffbeb;color:#92400e}.chip-red{background:#fee2e2;color:#b91c1c}.memo-list{margin:0;padding-left:20px}.memo-list li{margin:8px 0}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:11px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}th{font-size:12px;color:var(--muted);text-transform:uppercase;background:#f2f5f9}.source-ref{color:var(--muted);font-size:12px;white-space:nowrap}@media(max-width:900px){.sidebar{position:static;width:auto}.main{margin-left:0;padding:18px}.topbar,.section-head,.calc-strip{display:block}.metric-card strong{font-size:21px}.source-ref{white-space:normal}}@media print{.sidebar,.topbar,.button,.toolbar{display:none}.main{margin:0;padding:0}.panel,.metric-card,.card,.project-card{break-inside:avoid}}'''
APP_JS=r'''function tableSearch(){document.querySelectorAll("[data-table-search]").forEach(input=>{const table=input.closest(".panel")?.querySelector("[data-search-table]");if(!table)return;input.addEventListener("input",()=>{const q=input.value.trim().toLowerCase();table.querySelectorAll("tbody tr").forEach(row=>row.style.display=row.innerText.toLowerCase().includes(q)?"":"none")})})}function dashboard(){const root=document.querySelector("[data-dashboard-root]");if(!root)return;const slug=root.dataset.companySlug;const storageKey=`company-dashboard-${slug}-v1`;const defaults=JSON.parse(root.dataset.defaultAssumptions||"{}");const state=()=>({...defaults,...JSON.parse(localStorage.getItem(storageKey)||"{}")});const save=s=>localStorage.setItem(storageKey,JSON.stringify(s));const render=()=>{const s=state();document.querySelectorAll("[data-assumption]").forEach(el=>{const key=el.dataset.assumption;if(document.activeElement!==el)el.value=s[key]??""});const m=parseFloat(s.marketCapUsdM);const n=parseFloat(s.projectNpvUsdM);const ratio=Number.isFinite(m)&&Number.isFinite(n)&&n>0?`${(m/n).toFixed(2)}x`:"Incomplete";const note=ratio==="Incomplete"?"Enter both market cap and project NPV to calculate.":`Formula: ${m.toLocaleString()} / ${n.toLocaleString()}`;document.querySelector('[data-output="pnpv"]').textContent=ratio;document.querySelector('[data-output="calcNote"]').textContent=note;const cards={"Market Cap":Number.isFinite(m)?`US$${m.toLocaleString(undefined,{maximumFractionDigits:2})}m`:"To be updated","Latest Stated NPV":Number.isFinite(n)?`US$${n.toLocaleString(undefined,{maximumFractionDigits:0})}m`:"To be updated","P/NPV":ratio,"Development Stage":s.projectStatus,"Next Catalyst":s.nextCatalyst};Object.entries(cards).forEach(([label,value])=>{const node=document.querySelector(`[data-card="${label}"]`);if(node)node.textContent=value})};document.querySelectorAll("[data-assumption]").forEach(el=>el.addEventListener("input",()=>{const s=state();s[el.dataset.assumption]=el.value;save(s);render()}));document.querySelectorAll("[data-editable-cell]").forEach((el,i)=>{const key=`${storageKey}-cell-${i}`;const stored=localStorage.getItem(key);if(stored!==null)el.value=stored;el.addEventListener("input",()=>localStorage.setItem(key,el.value))});document.querySelector("[data-reset-dashboard]")?.addEventListener("click",()=>{localStorage.removeItem(storageKey);document.querySelectorAll("[data-editable-cell]").forEach((_,i)=>localStorage.removeItem(`${storageKey}-cell-${i}`));render()});render()}tableSearch();dashboard();'''
