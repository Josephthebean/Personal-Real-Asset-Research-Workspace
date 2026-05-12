from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.site_generator import build_site
from src.validators import validate_data

def main() -> int:
    errors = validate_data()
    if errors:
        print("Cannot build site because data validation failed:")
        for error in errors: print(f"- {error}")
        return 1
    build_site(); print("Generated static site in public/."); return 0
if __name__ == "__main__": raise SystemExit(main())
