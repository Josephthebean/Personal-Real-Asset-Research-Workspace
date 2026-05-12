from __future__ import annotations
import argparse, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import DATA_DIR, read_json, slugify, write_json

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--title',required=True); p.add_argument('--url',required=True); p.add_argument('--source-type',default='other'); p.add_argument('--source-tier',default='Tier 2'); p.add_argument('--company',default=''); p.add_argument('--theme',default=''); p.add_argument('--notes',default=''); a=p.parse_args(); rows=read_json(DATA_DIR/'sources.json'); sid=f'src-{slugify(a.title).lower()}'
    if any(r['source_id']==sid for r in rows): print(f'Source already exists: {sid}'); return 1
    today=date.today().isoformat(); rows.append({'source_id':sid,'title':a.title,'url':a.url,'source_type':a.source_type,'source_tier':a.source_tier,'related_company':a.company,'related_theme':a.theme,'date_published':today,'date_added':today,'confidence_level':'medium','key_notes':a.notes,'status':'new'})
    write_json(DATA_DIR/'sources.json',rows); print(f'Added source {a.title}.'); return 0
if __name__=='__main__': raise SystemExit(main())
