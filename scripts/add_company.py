from __future__ import annotations
import argparse, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import DATA_DIR, read_json, write_json

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--ticker',required=True); p.add_argument('--name',required=True); p.add_argument('--exchange',default=''); p.add_argument('--country',default=''); p.add_argument('--company-type',default='other'); p.add_argument('--commodities',default=''); p.add_argument('--priority',default='medium'); a=p.parse_args()
    rows=read_json(DATA_DIR/'companies.json')
    if any(r['ticker'].lower()==a.ticker.lower() for r in rows): print(f'Company already exists: {a.ticker}'); return 1
    today=date.today().isoformat(); rows.append({'company_id':f"co-{a.ticker.lower().replace('.','-')}",'ticker':a.ticker.upper(),'name':a.name,'exchange':a.exchange,'country':a.country,'company_type':a.company_type,'commodities':[x.strip() for x in a.commodities.split(',') if x.strip()],'related_themes':[],'research_status':'new idea','priority':a.priority,'current_thesis_summary':'New research candidate. Add source evidence, valuation assumptions, and thesis notes.','valuation_status':'not started','document_checklist_status':'needs documents','memo_status':'not started','created_date':today,'last_updated':today})
    write_json(DATA_DIR/'companies.json',rows); print(f'Added company {a.ticker}.'); return 0
if __name__=='__main__': raise SystemExit(main())
