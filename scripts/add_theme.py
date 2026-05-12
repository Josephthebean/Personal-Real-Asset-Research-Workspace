from __future__ import annotations
import argparse, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import DATA_DIR, read_json, slugify, write_json

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--name',required=True); p.add_argument('--asset-class',required=True); p.add_argument('--description',default=''); a=p.parse_args(); rows=read_json(DATA_DIR/'themes.json'); tid=f'theme-{slugify(a.name).lower()}'
    if any(r['theme_id']==tid for r in rows): print(f'Theme already exists: {tid}'); return 1
    today=date.today().isoformat(); rows.append({'theme_id':tid,'name':a.name,'asset_class':a.asset_class,'description':a.description,'why_it_matters':'','current_affairs':'','key_drivers':[],'risks':[],'related_companies':[],'saved_sources':[],'thesis_notes':'','conviction_level':'low','status':'exploring','created_date':today,'last_updated':today})
    write_json(DATA_DIR/'themes.json',rows); print(f'Added theme {a.name}.'); return 0
if __name__=='__main__': raise SystemExit(main())
