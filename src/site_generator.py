from __future__ import annotations

import json, os, shutil, stat
from typing import Any
from .utils import DATA_DIR, PUBLIC_DIR, copy_data_files, html_escape, write_text

NAV=[('Overview','#overview'),('Summary','#summary'),('Industry','#industry'),('Projects','#projects'),('Valuation','#valuation'),('Assumptions','#assumptions'),('Catalysts','#catalysts'),('Risks','#risks'),('Sources','#sources')]

def build_site()->None:
    data=json.loads((DATA_DIR/'pensana.json').read_text(encoding='utf-8'))
    if PUBLIC_DIR.exists(): shutil.rmtree(PUBLIC_DIR,onexc=lambda f,p,e:(os.chmod(p,stat.S_IWRITE),f(p)))
    (PUBLIC_DIR/'assets').mkdir(parents=True,exist_ok=True)
    copy_data_files(); write_assets(); write_text(PUBLIC_DIR/'index.html',page(data))

def layout(title,body):
    nav=''.join(f'<a class="nav-link" href="{h}">{l}</a>' for l,h in NAV)
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)}</title><link rel="stylesheet" href="assets/styles.css"><script defer src="assets/app.js"></script></head><body><aside class="sidebar"><div class="brand">Pensana Research</div><nav>{nav}</nav></aside><main class="main"><header class="topbar"><div><p class="eyebrow">Single-company real asset memo</p><h1>{html_escape(title)}</h1></div><div class="safety-note">Research dashboard only. Not financial advice. Source: uploaded Pensana report.</div></header>{body}</main></body></html>'

def page(d:dict[str,Any])->str:
    co=d['company']; p=d['projects'][0]; v=d['valuation']; ratio=f"{v['market_cap_usd_m']/v['project_npv_usd_m']:.2f}x"
    cards=[('Company',co['name'],co['ticker'],'extracted'),('Main Exposure',co['main_commodity'],'NdPr / rare earth magnet metals','extracted'),('Primary Project',p['name'],p['location'],'extracted'),('Development Stage',p['development_stage'],'editable below','extracted'),('Market Cap',money(v['market_cap_usd_m']),v['market_cap_note'],'extracted'),('Latest Stated NPV',money(v['project_npv_usd_m']),'NPV@8%, post-tax, unleveraged','extracted'),('P/NPV',ratio,'Market cap / Project NPV','calculated'),('Next Catalyst',d['status']['next_catalyst'],d['status']['catalyst_date'],'user-updated')]
    body=f'<section id="overview" class="metric-grid">{"".join(metric(*c) for c in cards)}</section><section class="panel"><div class="section-head"><h2>Overall Investment Thesis</h2>{chip(d["status"]["thesis_status"],"blue")}</div><p>{html_escape(co["thesis"])}</p><p>{source(co["thesis_source"])}</p></section>'
    body+=summary(co)+industry(d)+projects(d)+valuation(d)+assumptions(d)+catalysts(d)+risks(d)+sources(d)
    return layout('Pensana Investment Research Dashboard',body)

def summary(co):
    items=''.join(f'<li>{html_escape(x)} {source(s)}</li>' for x,s in co['summary_points'])
    return f'<section id="summary" class="panel"><div class="section-head"><h2>Company Summary</h2>{chip("extracted report data","green")}</div><p>{html_escape(co["description"])}</p><ul>{items}</ul></section>'

def industry(d):
    cards=''.join(f'<article class="card"><h3>{html_escape(x["label"])}</h3><p>{html_escape(x["value"])}</p><p>{source(x["source"])}</p></article>' for x in d['industryPrimer'])
    return f'<section id="industry" class="panel"><div class="section-head"><h2>Commodity And Industry Primer</h2>{chip("rare earths","blue")}</div><div class="cards">{cards}</div></section>'

def projects(d):
    out=[]
    for pr in d['projects']:
        fields=''.join(field(x['label'],x['value'],x['source'],x.get('state','extracted')) for x in pr['fields'])
        out.append(f'<article class="project-card"><div class="section-head"><h3>{html_escape(pr["name"])}</h3>{chip(pr["role"],"blue")}</div><div class="field-grid">{fields}</div></article>')
    return f'<section id="projects" class="panel"><div class="section-head"><h2>Project Details</h2><span>Dashboard fields, not prose blocks</span></div>{"".join(out)}</section>'

def valuation(d):
    rows=''.join(field(x['label'],x['value'],x['source'],x.get('state','extracted')) for x in d['valuation']['fields'])
    return f'<section id="valuation" class="panel"><div class="section-head"><h2>Financials And Valuation</h2>{chip("illustrative calculations","amber")}</div><p class="callout">P/NPV = Market Capitalisation / Project NPV. This dashboard uses only values from the uploaded report or user-edited local assumptions.</p><div class="field-grid">{rows}</div></section>'

def assumptions(d):
    a=d['userAssumptions']; opts=['Not started','Pending','In progress','Completed','Delayed','Unknown']
    nums=[('Market cap (USD m)','marketCapUsdM',a['market_cap_usd_m']),('Project NPV (USD m)','projectNpvUsdM',a['project_npv_usd_m']),('Discount rate (%)','discountRatePct',a['discount_rate_pct']),('Capex (USD m)','capexUsdM',a['capex_usd_m']),('Opex','opex',a['opex']),('Commodity price assumption','commodityPrice',a['commodity_price']),('Production volume','productionVolume',a['production_volume'])]
    inputs=''.join(f'<label>{html_escape(l)}<input data-assumption="{k}" value="{html_escape(v)}"></label>' for l,k,v in nums)
    for label,key in [('Project status','projectStatus'),('Financing status','financingStatus'),('Permitting status','permittingStatus'),('Offtake status','offtakeStatus'),('Government support status','governmentSupportStatus')]:
        inputs+=f'<label>{label}<select data-assumption="{key}">'+''.join(f'<option {"selected" if o==a[key] else ""}>{o}</option>' for o in opts)+'</select></label>'
    inputs+=f'<label>Next catalyst<input data-assumption="nextCatalyst" value="{html_escape(a["next_catalyst"])}"></label><label>Catalyst date<input data-assumption="catalystDate" value="{html_escape(a["catalyst_date"])}"></label><label class="wide">Notes<textarea data-assumption="notes">{html_escape(a["notes"])}</textarea></label>'
    return f'<section id="assumptions" class="panel"><div class="section-head"><h2>Interactive Assumptions Panel</h2><button class="button secondary" data-reset-dashboard>Reset to report values</button></div><div class="assumption-grid">{inputs}</div><div class="calc-strip"><strong>Updated P/NPV: <span data-output="pnpv"></span></strong><span data-output="calcNote"></span></div></section>'

def catalysts(d):
    rows=[[x['catalyst'],x['type'],x['expected_timing'],select(x['status']),x['importance'],edit(x['notes']),source(x['source'])] for x in d['catalysts']]
    return f'<section id="catalysts" class="panel"><div class="section-head"><h2>Catalyst Tracker</h2>{chip("editable local state","blue")}</div>{table(["Catalyst","Type","Expected Timing","Current Status","Importance","Notes","Source"],rows)}</section>'

def risks(d):
    rows=[[x['risk'],x['category'],select(x['severity'],['Low','Medium','High','Critical']),select(x['status']),x['why_it_matters'],edit(x['mitigation']),source(x['source'])] for x in d['risks']]
    return f'<section id="risks" class="panel"><div class="section-head"><h2>Risk Register</h2>{chip("editable local state","amber")}</div>{table(["Risk","Category","Severity","Current Status","Why It Matters","Mitigation / Watch Item","Source"],rows)}</section>'

def sources(d):
    rows=[[x['id'],x['title'],x['page'],x['note']] for x in d['sources']]
    return f'<section id="sources" class="panel"><div class="section-head"><h2>Source Traceability</h2><span>Original uploaded report</span></div>{table(["Ref","Source","Page","Note"],rows)}</section>'

def metric(l,v,n,s): return f'<article class="metric-card {s}"><span>{html_escape(l)}</span><strong data-card="{html_escape(l)}">{html_escape(v)}</strong><small>{html_escape(n)}</small></article>'
def field(l,v,src,state): return f'<div class="field {state}"><span>{html_escape(l)}</span><strong>{html_escape(v or "Not disclosed in uploaded report")}</strong><small>{source(src)}</small></div>'
def table(h,rows): return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{html_escape(x)}</th>' for x in h)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{cell}</td>' for cell in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def select(v,opts=None):
    opts=opts or ['Not started','Pending','In progress','Completed','Delayed','Unknown']
    return '<select data-editable-cell>'+''.join(f'<option {"selected" if o==v else ""}>{o}</option>' for o in opts)+'</select>'
def edit(v): return f'<textarea data-editable-cell>{html_escape(v)}</textarea>'
def chip(v,t): return f'<span class="chip chip-{t}">{html_escape(v)}</span>'
def source(v): return f'<span class="source-ref">Source: {html_escape(v)}</span>'
def money(v): return f'US${v:,.2f}m' if v<1000 else f'US${v:,.0f}m'

def write_assets():
    write_text(PUBLIC_DIR/'assets'/'styles.css',CSS); write_text(PUBLIC_DIR/'assets'/'app.js',APP_JS); write_text(PUBLIC_DIR/'assets'/'charts.js','')

CSS=''' :root{--navy:#003366;--bg:#F7F9FC;--card:#fff;--border:#D8E0EA;--muted:#667085;--blue:#2563EB;--amber:#F59E0B;--green:#16A34A;--text:#172033}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif;line-height:1.5}a{color:var(--blue)}h1,h2,h3{margin:0}.sidebar{position:fixed;inset:0 auto 0 0;width:250px;background:var(--navy);color:#fff;padding:22px 16px}.brand{font-weight:800;margin-bottom:22px}.nav-link{display:block;color:#dbeafe;text-decoration:none;padding:10px;border-radius:6px}.nav-link:hover{background:rgba(255,255,255,.14)}.main{margin-left:250px;padding:28px}.topbar,.section-head{display:flex;justify-content:space-between;gap:14px;margin-bottom:18px}.eyebrow,.source-ref,.metric-card small,.field small{color:var(--muted);font-size:12px}.safety-note,.callout{border:1px solid var(--border);background:#fff7ed;color:#7c2d12;padding:10px;border-radius:8px}.metric-grid,.cards,.field-grid,.assumption-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:18px}.metric-card,.panel,.card,.project-card,.field{background:#fff;border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:18px}.metric-card,.field{border-left:4px solid var(--border)}.extracted{border-left-color:var(--green)}.calculated{border-left-color:var(--blue)}.user-updated{border-left-color:var(--amber)}.metric-card span,.field span{display:block;color:var(--muted);font-size:12px;font-weight:800;text-transform:uppercase}.metric-card strong{display:block;font-size:24px;margin:6px 0}.wide{grid-column:1/-1}input,select,textarea{width:100%;border:1px solid var(--border);border-radius:8px;background:#fff;padding:10px}textarea{min-height:70px}.calc-strip{display:flex;justify-content:space-between;padding:14px;border:1px solid #bfdbfe;border-radius:8px;background:#eff6ff}.button{border:0;border-radius:8px;background:var(--blue);color:#fff;padding:10px 14px;font-weight:800}.button.secondary{background:#eef2ff;color:#1e3a8a}.chip{border:1px solid var(--border);border-radius:999px;padding:4px 8px;font-size:12px;font-weight:800}.chip-blue{background:#dbeafe;color:#1d4ed8}.chip-green{background:#ecfdf5;color:#047857}.chip-amber{background:#fffbeb;color:#92400e}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:11px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}th{font-size:12px;color:var(--muted);text-transform:uppercase;background:#f2f5f9}@media(max-width:900px){.sidebar{position:static;width:auto}.main{margin-left:0;padding:18px}.topbar,.section-head,.calc-strip{display:block}} '''
APP_JS='''const defaults={marketCapUsdM:282.14,projectNpvUsdM:1116,discountRatePct:8,capexUsdM:217,projectStatus:"In progress",nextCatalyst:"Initial production / commissioning at Longonjo"};const k="pensana-dashboard-state-v1";const state=()=>({...defaults,...JSON.parse(localStorage.getItem(k)||"{}")});function save(s){localStorage.setItem(k,JSON.stringify(s))}function render(){const s=state();document.querySelectorAll("[data-assumption]").forEach(e=>{if(document.activeElement!==e)e.value=s[e.dataset.assumption]??e.value});const m=parseFloat(s.marketCapUsdM),n=parseFloat(s.projectNpvUsdM);const r=Number.isFinite(m)&&Number.isFinite(n)&&n>0?`${(m/n).toFixed(2)}x`:"Incomplete";document.querySelector('[data-output="pnpv"]').textContent=r;document.querySelector('[data-output="calcNote"]').textContent=r==="Incomplete"?"Enter both values.":`Formula: ${m.toLocaleString()} / ${n.toLocaleString()}`;[["Market Cap",`US$${m.toLocaleString()}m`],["Latest Stated NPV",`US$${n.toLocaleString()}m`],["P/NPV",r],["Development Stage",s.projectStatus],["Next Catalyst",s.nextCatalyst]].forEach(([a,b])=>{const el=document.querySelector(`[data-card="${a}"]`);if(el)el.textContent=b})}document.querySelectorAll("[data-assumption]").forEach(e=>e.addEventListener("input",()=>{const s=state();s[e.dataset.assumption]=e.value;save(s);render()}));document.querySelectorAll("[data-editable-cell]").forEach((e,i)=>{const ck=`${k}-cell-${i}`;const v=localStorage.getItem(ck);if(v!==null)e.value=v;e.addEventListener("input",()=>localStorage.setItem(ck,e.value))});document.querySelector("[data-reset-dashboard]")?.addEventListener("click",()=>{localStorage.removeItem(k);render()});render();'''
