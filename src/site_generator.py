from __future__ import annotations

import os, shutil, stat
from typing import Any
from .data_loader import load_all
from .memo_renderer import memo_to_html, memo_to_markdown
from .utils import PUBLIC_DIR, badge, comma, copy_data_files, html_escape, slugify, write_text
from .valuation import enrich_valuation

NAV=[('Dashboard','index.html'),('Themes','themes.html'),('Companies','companies.html'),('Research Inbox','inbox.html'),('Sources','sources.html'),('Valuations','valuations.html'),('Theses','theses.html'),('Memos','memos.html'),('Weekly Review','weekly-review.html')]

def build_site() -> None:
    data=load_all()
    if PUBLIC_DIR.exists(): shutil.rmtree(PUBLIC_DIR,onexc=lambda f,p,e:(os.chmod(p,stat.S_IWRITE),f(p)))
    (PUBLIC_DIR/'companies').mkdir(parents=True,exist_ok=True); (PUBLIC_DIR/'assets').mkdir(parents=True,exist_ok=True); (PUBLIC_DIR/'memos').mkdir(parents=True,exist_ok=True)
    copy_data_files(); assets()
    pages={'index.html':dashboard(data),'themes.html':listing('Themes',data['themes'],['name','asset_class','status','conviction_level','last_updated']),'companies.html':companies(data),'inbox.html':listing('Research Inbox',data['inbox'],['title','source_type','related_company','status','confidence_level','date_added']),'sources.html':listing('Source Library',data['sources'],['title','source_type','source_tier','related_company','confidence_level','status']),'valuations.html':valuations(data),'theses.html':listing('Thesis Builder',data['theses'],['thesis_title','status','confidence_level','last_updated']),'memos.html':memos(data),'weekly-review.html':weekly(data)}
    for path,html in pages.items(): write_text(PUBLIC_DIR/path,html)
    for c in data['companies']: write_text(PUBLIC_DIR/'companies'/f"{slugify(c['ticker'])}.html",company_detail(data,c))
    for m in data['memos']:
        md=memo_to_markdown(m); write_text(PUBLIC_DIR/'memos'/f"{m['memo_id']}.md",md); write_text(PUBLIC_DIR/'memos'/f"{m['memo_id']}.html",memo_to_html(m,md))

def layout(title:str,body:str,active='index.html',depth=0)->str:
    pre='../'*depth; nav=''.join(f'<a class="nav-link {"active" if h==active else ""}" href="{pre}{h}">{l}</a>' for l,h in NAV)
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html_escape(title)}</title><link rel="stylesheet" href="{pre}assets/styles.css"><script defer src="{pre}assets/app.js"></script></head><body><aside class="sidebar"><div class="brand">Real Asset Research</div><nav>{nav}</nav></aside><main class="main"><header class="topbar"><div><p class="eyebrow">Personal research operating system</p><h1>{html_escape(title)}</h1></div><div class="safety-note">Illustrative research workflow only. Not financial advice.</div></header>{body}</main></body></html>'

def dashboard(data):
    cards=[('Active Themes',len(data['themes'])),('Companies in Research',len(data['companies'])),('Thesis Drafts',len(data['theses'])),('Open Follow-ups',len(data['tasks'])),('Recently Added Sources',len(data['sources'])),('Valuation Notes',len(data['valuations'])),('Memos Ready for Export',len([m for m in data['memos'] if m['status']=='ready for export']))]
    stats=''.join(f'<article class="stat-card"><span>{l}</span><strong>{v}</strong></article>' for l,v in cards)
    tasks=''.join(task(t) for t in sorted(data['tasks'],key=lambda x:x['priority'])[:6])
    return layout('Dashboard',f'<section class="grid stats">{stats}</section><section class="two-col"><div class="panel"><h2>Next Best Actions</h2>{tasks}</div><div class="panel"><h2>Weekly Review Summary</h2><p>{html_escape(data["weekly_reviews"][-1]["what_i_learned"])}</p></div></section>')

def listing(title,rows,fields):
    trs=''.join('<tr>'+''.join(f'<td>{html_escape(comma(r.get(f,"")))}</td>' for f in fields)+'</tr>' for r in rows)
    th=''.join(f'<th>{f.replace("_"," ").title()}</th>' for f in fields)
    return layout(title,f'<section class="panel"><div class="toolbar"><input class="search-input" placeholder="Search"></div><div class="table-wrap"><table class="filter-table"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div></section>',title.lower().split()[0]+'.html')

def companies(data):
    rows=[]
    for c in data['companies']:
        rows.append([f'<a href="companies/{slugify(c["ticker"])}.html"><strong>{c["ticker"]}</strong></a><small>{html_escape(c["name"])}</small>',c['company_type'],comma(c['commodities']),badge(c['research_status'],'blue'),badge(c['priority'],'priority'),c['last_updated']])
    return layout('Companies',table(['Company','Type','Commodities','Status','Priority','Updated'],rows),'companies.html')

def valuations(data):
    cos={c['company_id']:c for c in data['companies']}; rows=[]
    for v in data['valuations']:
        e=enrich_valuation(v); rows.append([cos[v['company_id']]['ticker'],v['case_name'],badge(v['case_type'],'blue'),f"${e['implied_enterprise_value']:,.1f}m",f"${e['implied_share_price']:,.2f}",f"{e['upside_downside_pct']}%",f"{e['ev_ebitda']}x"])
    return layout('Valuation Notebook','<p class="callout">All outputs are illustrative calculations, not financial advice.</p>'+table(['Company','Case','Type','Implied EV','Implied Share','Upside/Downside','EV/EBITDA'],rows),'valuations.html')

def memos(data):
    rows=[[m['memo_title'],m['memo_type'],badge(m['status'],'blue'),m['updated_date'],f'<a href="memos/{m["memo_id"]}.md">Markdown</a> <a href="memos/{m["memo_id"]}.html">HTML</a>'] for m in data['memos']]
    return layout('Memo Library',table(['Memo','Type','Status','Updated','Exports'],rows),'memos.html')

def weekly(data):
    r=data['weekly_reviews'][-1]
    return layout('Weekly Review',f'<section class="panel"><h2>Weekly Research Reflection</h2><dl class="detail-list"><dt>What I learned this week</dt><dd>{html_escape(r["what_i_learned"])}</dd><dt>Best idea found</dt><dd>{html_escape(r["best_idea_found"])}</dd><dt>Riskiest idea</dt><dd>{html_escape(r["riskiest_idea"])}</dd><dt>Source/document to review</dt><dd>{html_escape(r["source_to_review"])}</dd><dt>Company to revisit next week</dt><dd>{html_escape(r["company_to_revisit_next_week"])}</dd></dl></section>','weekly-review.html')

def company_detail(data,c):
    vals=[enrich_valuation(v) for v in data['valuations'] if v['company_id']==c['company_id']]; tasks=[t for t in data['tasks'] if t.get('related_company')==c['ticker']]
    return layout(f"{c['ticker']} Research",f'<section class="summary-card"><div><h2>{c["ticker"]} - {html_escape(c["name"])}</h2><p>{html_escape(c["current_thesis_summary"])}</p></div><div>{badge(c["research_status"],"blue")} {badge(c["priority"],"priority")}</div></section><section class="panel"><h2>Research Status</h2><p>Next action: {html_escape(tasks[0]["task"] if tasks else "Review sources")}</p></section><section class="panel"><h2>Document Checklist</h2><ul class="checklist"><li>Annual report reviewed</li><li>Valuation assumptions entered</li><li>Thesis drafted</li></ul></section><section class="panel"><h2>Valuation Notebook</h2><p class="callout">Illustrative calculations only.</p></section><section class="panel"><h2>Thesis Builder</h2><p>Structured thesis template rendered from data files.</p></section><section class="panel"><h2>Risk Register</h2><p>Track severity, evidence, and monitoring notes.</p></section><section class="panel"><h2>Follow-up Actions</h2>{''.join(task(t) for t in tasks)}</section><section class="panel"><h2>Exports</h2><div class="actions"><button class="button" data-download-company="{c["ticker"]}">Download company JSON</button><button class="button secondary" data-download-valuation="{c["ticker"]}">Download valuation CSV</button><button class="button secondary" onclick="window.print()">Print/save memo as PDF</button></div></section>','companies.html',1)

def table(headers,rows):
    return '<section class="panel"><div class="toolbar"><input placeholder="Search"></div><div class="table-wrap"><table class="filter-table"><thead><tr>'+''.join(f'<th>{h}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{x}</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div></section>'

def task(t): return f'<article class="task"><strong>{html_escape(t["task"])}</strong>{badge(t["priority"],"priority")}<span>{html_escape(t["due_date"])}</span></article>'

def assets():
    write_text(PUBLIC_DIR/'assets'/'app.js',"document.querySelectorAll('.filter-table').forEach(t=>{const i=t.closest('.panel').querySelector('input');if(i)i.oninput=()=>{const q=i.value.toLowerCase();t.querySelectorAll('tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')}});\n")
    write_text(PUBLIC_DIR/'assets'/'charts.js','')
    write_text(PUBLIC_DIR/'assets'/'styles.css',":root{--navy:#003366;--bg:#F7F9FC;--card:#FFFFFF;--border:#D8E0EA;--muted:#667085;--blue:#2563EB;--amber:#F59E0B;--green:#16A34A;--red:#DC2626;--text:#172033}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif}.sidebar{position:fixed;inset:0 auto 0 0;width:248px;background:var(--navy);padding:22px 16px}.brand{color:#fff;font-weight:800;margin-bottom:20px}.nav-link{display:block;color:#dbeafe;padding:10px;border-radius:8px;text-decoration:none}.nav-link.active,.nav-link:hover{background:rgba(255,255,255,.14);color:#fff}.main{margin-left:248px;padding:28px}.topbar,.summary-card{display:flex;justify-content:space-between;gap:18px;margin-bottom:24px}.eyebrow{color:var(--muted);text-transform:uppercase;font-size:12px}.safety-note,.callout{border:1px solid var(--border);background:#fff7ed;color:#7c2d12;padding:10px;border-radius:8px}.grid{display:grid;gap:14px}.stats{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:18px}.stat-card,.panel,.summary-card{background:#fff;border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:18px}.stat-card strong{font-size:30px}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:18px}.toolbar{margin-bottom:12px}input{border:1px solid var(--border);border-radius:8px;padding:10px;width:100%}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase;background:#f2f5f9}.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:700;background:#f8fafc;border:1px solid var(--border)}.badge-blue{background:#dbeafe;color:#1d4ed8}.badge-priority{background:#fff7ed;color:#b45309}.task{display:grid;grid-template-columns:1fr auto auto;gap:10px;padding:10px 0;border-bottom:1px solid var(--border)}.button{border:0;border-radius:8px;background:var(--blue);color:white;padding:10px 14px;font-weight:700}.button.secondary{background:#eef2ff;color:#1e3a8a}.detail-list{display:grid;grid-template-columns:220px 1fr;gap:8px 12px}@media(max-width:900px){.sidebar{position:static;width:auto}.main{margin-left:0}.two-col,.detail-list{grid-template-columns:1fr}}")
