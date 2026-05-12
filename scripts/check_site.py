from __future__ import annotations

import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_loader import DATA_FILES, load_all
from src.utils import FORBIDDEN_ADVICE_LANGUAGE, PUBLIC_DIR, slugify
MAIN_PAGES=["index.html","themes.html","companies.html","inbox.html","sources.html","valuations.html","theses.html","memos.html","weekly-review.html"]

def main()->int:
    errors=[]; data=load_all()
    for p in MAIN_PAGES: exists(errors,PUBLIC_DIR/p)
    for f in DATA_FILES.values(): exists(errors,PUBLIC_DIR/'data'/f)
    for c in data['companies']: exists(errors,PUBLIC_DIR/'companies'/f"{slugify(c['ticker'])}.html")
    if (PUBLIC_DIR/'index.html').exists() and 'Next Best Actions' not in (PUBLIC_DIR/'index.html').read_text(encoding='utf-8'): errors.append('Dashboard is missing Next Best Actions.')
    for c in data['companies']:
        p=PUBLIC_DIR/'companies'/f"{slugify(c['ticker'])}.html"
        if p.exists():
            txt=p.read_text(encoding='utf-8')
            for marker in ['Download company JSON','Download valuation CSV','Print/save memo as PDF']:
                if marker not in txt: errors.append(f'{p} missing {marker}')
    for html in PUBLIC_DIR.rglob('*.html'):
        txt=html.read_text(encoding='utf-8')
        for href in re.findall(r'href="([^"]+)"',txt):
            if href.startswith(('http://','https://','mailto:','#')): continue
            if not (html.parent/href.split('#')[0]).resolve().exists(): errors.append(f'Broken internal link in {html}: {href}')
        low=txt.lower()
        for phrase in FORBIDDEN_ADVICE_LANGUAGE:
            if phrase in low: errors.append(f'Forbidden advice language in {html}: {phrase}')
    if errors:
        print('Site check failed:'); [print(f'- {e}') for e in errors]; return 1
    print('Site check passed.'); return 0

def exists(errors,path):
    if not path.exists(): errors.append(f'Missing generated file: {path}')
if __name__=='__main__': raise SystemExit(main())
