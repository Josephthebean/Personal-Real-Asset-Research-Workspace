from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.validators import validate_data

def main() -> int:
    errors = validate_data()
    if errors:
        print("Data validation failed:")
        for error in errors: print(f"- {error}")
        return 1
    print("Data validation passed.")
    return 0
if __name__ == "__main__": raise SystemExit(main())
