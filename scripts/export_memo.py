from __future__ import annotations

import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_loader import load_all
from src.memo_renderer import memo_to_html, memo_to_markdown
from src.utils import PUBLIC_DIR, write_text

def main()->int:
    parser=argparse.ArgumentParser(description='Export a memo to Markdown and HTML.'); parser.add_argument('memo_id'); args=parser.parse_args()
    memo=next((m for m in load_all()['memos'] if m['memo_id']==args.memo_id),None)
    if not memo: print(f'Memo not found: {args.memo_id}'); return 1
    md=memo_to_markdown(memo); write_text(PUBLIC_DIR/'memos'/f"{memo['memo_id']}.md",md); write_text(PUBLIC_DIR/'memos'/f"{memo['memo_id']}.html",memo_to_html(memo,md)); print(f"Exported memo {memo['memo_id']} to public/memos/."); return 0
if __name__=='__main__': raise SystemExit(main())
