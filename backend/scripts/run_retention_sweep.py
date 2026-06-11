from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from retention import run_retention_sweep


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Shannova dataset retention sweep.")
    parser.add_argument("--execute", action="store_true", help="Apply retention restrictions. Defaults to dry-run.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of records to process.")
    args = parser.parse_args()

    result = run_retention_sweep(dry_run=not args.execute, limit=args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
