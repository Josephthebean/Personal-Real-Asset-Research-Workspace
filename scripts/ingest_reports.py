from __future__ import annotations

import argparse, hashlib, json, re, shutil, sys
from datetime import date
from pathlib import Path
from typing import Any
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_loader import load_all
from src.utils import DATA_DIR, ROOT, slugify, write_json

REPORT_DROP = DATA_DIR / "report_drop"
NEW_DIR = REPORT_DROP / "new"
PROCESSED_DIR = REPORT_DROP / "processed"
FAILED_DIR = REPORT_DROP / "failed"
OUTPUTS_DIR = ROOT / "outputs"
SUPPORTED = {".md", ".txt", ".pdf", ".json"}
SECTION_ALIASES = {
    "executive_summary": {"executive summary", "summary"},
    "company_overview": {"company overview", "introduction", "market data", "market perception"},
    "current_valuation": {"current valuation", "valuation snapshot"},
    "key_value_drivers": {"key value drivers", "value drivers"},
    "primary_project": {"primary project", "primary project asset", "primary project / asset", "main project"},
    "secondary_project": {"secondary project", "secondary project upside", "secondary project / upside", "exploration project"},
    "valuation_analysis": {"valuation", "valuation approach", "valuation analysis", "risk reward", "risk/reward"},
    "thesis": {"investment thesis", "thesis"},
    "catalysts": {"catalysts", "key catalysts"},
    "risks": {"risks", "risk factors"},
    "follow_up_tasks": {"follow up tasks", "follow-up tasks", "open questions", "manual review", "next steps", "what to verify"},
    "sources_or_references": {"works cited", "sources", "references"},
    "what_would_change_my_mind": {"what would change my mind"},
}
SECTION_KEYS = list(SECTION_ALIASES) + ["raw_unclassified_sections"]
THEME_RULES = [(('rare earths','ndpr','magnet metals'),'rare earths supply chain','Rare earths'),(('copper','electrification'),'copper electrification','Copper'),(('uranium','nuclear'),'uranium nuclear restart','Uranium'),(('gold','safe haven','safe-haven'),'gold safe-haven demand','Gold'),(('oil','gas','lng'),'energy security','Energy')]

def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest dropped research reports without an LLM or API.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input-dir", type=Path, default=NEW_DIR)
    args = parser.parse_args()
    result = ingest_reports(args.input_dir, args.dry_run)
    print(f"Processed {result['processed_count']} report(s), failed {result['failed_count']}.")
    print(f"Log written to {OUTPUTS_DIR / 'report_ingestion_log.json'}")
    return 1 if result['failed_count'] and not result['processed_count'] else 0

def ingest_reports(input_dir: Path = NEW_DIR, dry_run: bool = False) -> dict[str, Any]:
    ensure_folders(); OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_all(); seen = {m.get('checksum') for m in data['memos'] if m.get('checksum')}
    log = {"dry_run": dry_run, "processed": [], "failed": []}
    for path in sorted(input_dir.iterdir() if input_dir.exists() else []):
        if path.is_dir() or path.name == '.gitkeep': continue
        try:
            doc = read_document(path)
            if doc['checksum'] in seen: raise ValueError('Duplicate report checksum already ingested.')
            parsed = parse_report(doc, data); log['processed'].append(parsed['log'])
            if not dry_run:
                apply_ingestion(data, parsed)
                dest = unique_path(PROCESSED_DIR / path.name); shutil.move(str(path), dest)
                parsed['memo']['source_file'] = rel(dest); write_all(data)
        except Exception as exc:
            log['failed'].append({'file': str(path), 'error': str(exc)})
            if not dry_run and path.exists(): shutil.move(str(path), unique_path(FAILED_DIR / path.name))
    log['processed_count'] = len(log['processed']); log['failed_count'] = len(log['failed'])
    write_json(OUTPUTS_DIR / 'report_ingestion_log.json', log); return log

def ensure_folders() -> None:
    for folder in [NEW_DIR, PROCESSED_DIR, FAILED_DIR, DATA_DIR/'inbox_drop'/'new', DATA_DIR/'inbox_drop'/'processed', DATA_DIR/'inbox_drop'/'failed']:
        folder.mkdir(parents=True, exist_ok=True); (folder/'.gitkeep').touch(exist_ok=True)

def read_document(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower(); raw = path.read_bytes(); checksum = hashlib.sha256(raw).hexdigest()
    if suffix == '.docx': raise ValueError('.docx is unsupported in v1. Convert to Markdown, text, PDF, or JSON.')
    if suffix not in SUPPORTED: raise ValueError(f'Unsupported report type: {suffix}')
    if suffix == '.pdf': text, fm = extract_pdf(path), {}
    elif suffix == '.json':
        payload = json.loads(raw.decode('utf-8')); fm = payload.get('frontmatter', payload.get('metadata', {})); text = payload.get('content', payload.get('text', json.dumps(payload, indent=2)))
    else:
        fm, text = split_frontmatter(raw.decode('utf-8-sig'))
    return {'path': path, 'text': text, 'frontmatter': fm, 'checksum': checksum, 'format': suffix.lstrip('.')}

def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError('PDF ingestion requires pypdf. Run `pip install -r requirements.txt`, then retry.') from exc
    reader = PdfReader(str(path)); pages = []
    for index, page in enumerate(reader.pages, 1): pages.append(f"\n\n{page.extract_text() or ''}\n\n[Page {index}]\n")
    return '\n'.join(pages).strip()

def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith('---\n'): return {}, text
    end = text.find('\n---', 4)
    if end == -1: return {}, text
    return parse_yaml(text[4:end]), text[end+4:].lstrip()

def parse_yaml(block: str) -> dict[str, Any]:
    out = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or ':' not in line: continue
        key, value = line.split(':', 1); value = value.strip()
        out[key.strip()] = [x.strip().strip('"\'') for x in value[1:-1].split(',') if x.strip()] if value.startswith('[') and value.endswith(']') else value.strip('"\'')
    return out

def parse_report(doc: dict[str, Any], data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    meta = infer_meta(doc, data); sections = parse_sections(doc['text'])
    company = ensure_company(meta, data); theme = ensure_theme(meta, data)
    memo_id = sid('memo', meta['title'], meta.get('ticker') or meta.get('company') or doc['checksum'][:8])
    source_file = rel(PROCESSED_DIR / doc['path'].name)
    manual_review = not doc['frontmatter'] or not meta.get('ticker') or bool(sections.get('raw_unclassified_sections'))
    memo = {'memo_id': memo_id, 'related_company': company.get('ticker',''), 'related_theme': theme.get('theme_id',''), 'memo_title': meta['title'], 'memo_type': 'deep research report', 'source_file': source_file, 'source_type': meta['source_type'], 'status': meta['status'], 'date_added': meta['date_added'], 'updated_date': meta['date_added'], 'last_updated': meta['date_added'], 'sections': sections, 'export_paths': {'markdown': f'memos/{memo_id}.md', 'html': f'memos/{memo_id}.html'}, 'confidence_level': meta['confidence'], 'manual_review_required': manual_review, 'checksum': doc['checksum'], 'summary': first_text(sections)}
    source = {'source_id': sid('src', meta['title'], doc['checksum'][:8]), 'title': meta['title'], 'url': source_file, 'source_type': meta['source_type'], 'source_tier': meta['source_tier'], 'related_company': company.get('ticker',''), 'related_theme': theme.get('theme_id',''), 'date_published': meta['date_added'], 'date_added': meta['date_added'], 'confidence_level': meta['confidence'], 'key_notes': 'Ingested report source file.', 'status': 'needs review' if manual_review else 'reviewed'}
    inbox = {'item_id': sid('inbox', meta['title'], doc['checksum'][:8]), 'title': meta['title'], 'content': memo['summary'] or 'Structured report ingested for review.', 'source_url': source_file, 'source_type': meta['source_type'], 'related_company': company.get('ticker',''), 'related_theme': theme.get('theme_id',''), 'tags': meta['tags'], 'confidence_level': meta['confidence'], 'status': 'linked to thesis', 'date_added': meta['date_added'], 'notes': 'Created by deterministic report ingestion.', 'important': False, 'linked_thesis_section': 'deep research report'}
    tasks = extract_tasks(sections, company.get('ticker',''), theme.get('theme_id',''), memo_id, meta['date_added'])
    cited = extract_sources(sections.get('sources_or_references',''), company.get('ticker',''), theme.get('theme_id',''), meta)
    return {'company': company, 'theme': theme, 'memo': memo, 'source': source, 'inbox': inbox, 'tasks': tasks, 'cited_sources': cited, 'log': {'file': str(doc['path']), 'memo_id': memo_id, 'title': meta['title'], 'company': company.get('ticker',''), 'theme': theme.get('theme_id',''), 'sections_detected': [k for k,v in sections.items() if v and k!='raw_unclassified_sections'], 'manual_review_required': manual_review, 'checksum': doc['checksum']}}

def infer_meta(doc: dict[str, Any], data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    fm = doc['frontmatter']; head = '\n'.join(doc['text'].splitlines()[:60]); filename_title = doc['path'].stem.replace('_',' ').replace('-',' ').strip()
    title = fm.get('title') or (filename_title if doc['format']=='pdf' and filename_title else first_heading(doc['text'])) or filename_title
    known = find_known(filename_title+'\n'+head, data); ticker, exchange = infer_ticker(filename_title+'\n'+head)
    company = fm.get('company') or (known or {}).get('name') or infer_company(head) or filename_title
    source_type = fm.get('source_type') or infer_source_type(title, doc['text']); theme_name, asset = infer_theme(fm.get('theme') or '', doc['text']+'\n'+title)
    return {'title': title, 'company': company, 'ticker': fm.get('ticker') or (known or {}).get('ticker') or ticker, 'exchange': fm.get('exchange') or (known or {}).get('exchange','') or exchange, 'theme': fm.get('theme') or theme_name, 'asset_class': asset, 'source_type': source_type, 'source_tier': fm.get('source_tier') or ('Tier 2' if source_type in {'AI research output','GPT/Gemini deep research','research report'} else 'Tier 3'), 'confidence': fm.get('confidence') or ('medium' if source_type in {'AI research output','GPT/Gemini deep research'} else 'unreviewed'), 'status': fm.get('status') or 'thesis drafting', 'tags': fm.get('tags') if isinstance(fm.get('tags'), list) else [], 'date_added': fm.get('date_added') or date.today().isoformat()}

def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith('[Page '): continue
        m = re.match(r'^\s{0,3}#{1,3}\s+(.+?)\s*$', line)
        if m: return m.group(1).strip()
    for line in text.splitlines()[:8]:
        clean = line.strip()
        if 8 <= len(clean) <= 120 and not clean.startswith('[Page '): return clean
    return ''

def find_known(text: str, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    low = text.lower()
    return next((c for c in data['companies'] if c['ticker'].lower() in low or c['name'].lower() in low), None)

def infer_ticker(text: str) -> tuple[str,str]:
    m = re.search(r'\b([A-Z]{2,6}(?:\.[A-Z]{1,3})?):([A-Z]{2,6})\b', text)
    if m: return m.group(1), m.group(2)
    m = re.search(r'\b(LSE|NYSE|NASDAQ|TSX|ASX|AIM|HKEX|SGX)\s*:\s*([A-Z]{1,6})\b', text)
    return (m.group(2), m.group(1)) if m else ('','')

def infer_company(text: str) -> str:
    m = re.search(r'\b([A-Z][A-Za-z&.-]+(?:\s+[A-Z][A-Za-z&.-]+){0,4}\s+(?:PLC|Inc\.?|Corporation|Corp\.?|Ltd\.?|Limited))\b', text)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''

def infer_source_type(title: str, text: str) -> str:
    hay = (title+'\n'+text[:1000]).lower()
    if any(x in hay for x in ['gpt','gemini','deep research']): return 'AI research output'
    if 'annual report' in hay: return 'annual report'
    if 'investor presentation' in hay: return 'investor presentation'
    return 'research report'

def infer_theme(front: str, text: str) -> tuple[str,str]:
    if front: return front, front.title()
    low = text.lower()
    for keys, theme, asset in THEME_RULES:
        if any(k in low for k in keys): return theme, asset
    return '', 'Other'

def parse_sections(text: str) -> dict[str,str]:
    sections = {k: [] for k in SECTION_KEYS}; current = 'raw_unclassified_sections'
    for line in text.splitlines():
        heading = detect_heading(line)
        if heading:
            current = map_heading(heading) or 'raw_unclassified_sections'
            if current == 'raw_unclassified_sections': sections[current].append(f'\n## {heading}\n')
            continue
        sections[current].append(line)
    return {k: '\n'.join(v).strip() for k,v in sections.items()}

def detect_heading(line: str) -> str:
    s = line.strip().strip(':')
    if not s or s.startswith('[Page '): return ''
    m = re.match(r'^\s{0,3}#{1,4}\s+(.+?)\s*$', line)
    if m: return m.group(1).strip().strip(':')
    return s if len(s) <= 80 and not s.endswith('.') and re.match(r'^[A-Z][A-Za-z0-9 /&()\'-]+$', s) else ''

def map_heading(h: str) -> str:
    n = re.sub(r'[^a-z0-9]+',' ',h.lower()).strip()
    return next((k for k,a in SECTION_ALIASES.items() if n in a), '')

def ensure_company(meta: dict[str,Any], data: dict[str,list[dict[str,Any]]]) -> dict[str,Any]:
    for c in data['companies']:
        if meta.get('ticker') and c['ticker'].lower()==meta['ticker'].lower(): return c
        if meta.get('company') and c['name'].lower()==meta['company'].lower(): return c
    return {'company_id': sid('co', meta.get('ticker') or meta.get('company') or 'unknown'), 'ticker': meta.get('ticker',''), 'name': meta.get('company') or meta.get('ticker') or 'Unknown company', 'exchange': meta.get('exchange',''), 'country': '', 'company_type': 'other', 'commodities': [meta['asset_class']] if meta.get('asset_class') and meta['asset_class']!='Other' else [], 'related_themes': [], 'research_status': 'thesis drafting', 'priority': 'medium', 'current_thesis_summary': 'Created from ingested research report. Requires manual review.', 'valuation_status': 'needs review', 'document_checklist_status': 'report ingested', 'memo_status': 'drafting', 'created_date': meta['date_added'], 'last_updated': meta['date_added']}

def ensure_theme(meta: dict[str,Any], data: dict[str,list[dict[str,Any]]]) -> dict[str,Any]:
    name = meta.get('theme','')
    if not name: return {}
    for t in data['themes']:
        if t['name'].lower()==name.lower() or t['theme_id']==sid('theme', name): return t
    return {'theme_id': sid('theme', name), 'name': name, 'asset_class': meta.get('asset_class','Other'), 'description': 'Created from deterministic report ingestion.', 'why_it_matters': '', 'current_affairs': '', 'key_drivers': [], 'risks': [], 'related_companies': [], 'saved_sources': [], 'thesis_notes': '', 'conviction_level': meta.get('confidence','medium'), 'status': 'active research', 'created_date': meta['date_added'], 'last_updated': meta['date_added']}

def extract_tasks(sections: dict[str,str], ticker: str, theme: str, memo_id: str, added: str) -> list[dict[str,Any]]:
    lines = [clean(x) for x in sections.get('follow_up_tasks','').splitlines() if clean(x)]
    if not lines: lines = ['Review valuation assumptions','Verify cited sources','Check latest company filings','Confirm current market cap and share price']
    return [{'task_id': sid('task', memo_id, str(i), t), 'task': t, 'related_company': ticker, 'related_theme': theme, 'priority': 'medium', 'due_date': added, 'status': 'open', 'notes': 'Created by deterministic report ingestion.', 'source': 'report_ingestion_rule', 'source_memo': memo_id} for i,t in enumerate(lines,1)]

def extract_sources(content: str, ticker: str, theme: str, meta: dict[str,Any]) -> list[dict[str,Any]]:
    out=[]
    for line in content.splitlines():
        c = clean(line)
        if not c: continue
        m = re.search(r'https?://\S+', c); url = m.group(0).rstrip(').,') if m else ''; title = c.replace(url,'').strip(' -') or url or 'Untitled cited source'
        out.append({'source_id': sid('src', title, url or 'needs-url'), 'title': title, 'url': url, 'source_type': 'cited source', 'source_tier': meta['source_tier'], 'related_company': ticker, 'related_theme': theme, 'date_published': meta['date_added'], 'date_added': meta['date_added'], 'confidence_level': meta['confidence'], 'key_notes': 'Parsed from report works cited.' if url else 'Parsed from report works cited. Needs URL verification.', 'status': 'needs review'})
    return out

def apply_ingestion(data: dict[str,list[dict[str,Any]]], parsed: dict[str,Any]) -> None:
    for bucket,row,key in [('companies',parsed['company'],'company_id'),('themes',parsed['theme'],'theme_id'),('memos',parsed['memo'],'memo_id'),('sources',parsed['source'],'source_id'),('inbox',parsed['inbox'],'item_id')]: upsert(data[bucket], row, key)
    for s in parsed['cited_sources']: upsert(data['sources'], s, 'source_id')
    for t in parsed['tasks']: upsert(data['tasks'], t, 'task_id')

def upsert(rows: list[dict[str,Any]], row: dict[str,Any], key: str) -> None:
    if not row: return
    for i, old in enumerate(rows):
        if old.get(key)==row.get(key): rows[i]=row; return
    rows.append(row)

def write_all(data: dict[str,list[dict[str,Any]]]) -> None:
    for key, rows in data.items(): write_json(DATA_DIR / ('weekly_reviews.json' if key=='weekly_reviews' else f'{key}.json'), rows)

def first_text(sections: dict[str,str]) -> str:
    for k in ['executive_summary','thesis','company_overview']:
        if sections.get(k): return sections[k][:800]
    return ''

def clean(line: str) -> str: return re.sub(r'^\s*(?:[-*]|\d+[.)])\s*','',line).strip()
def sid(prefix: str, *parts: str) -> str: return (prefix+'-'+'-'.join(slugify(str(p).lower()) for p in parts if p))[:96].rstrip('-')
def rel(path: Path) -> str: return str(path.resolve().relative_to(ROOT)).replace('\\','/')
def unique_path(path: Path) -> Path:
    if not path.exists(): return path
    for i in range(2,1000):
        candidate = path.with_name(f'{path.stem}-{i}{path.suffix}')
        if not candidate.exists(): return candidate
    raise ValueError('Could not allocate unique processed filename.')

if __name__ == '__main__': raise SystemExit(main())
