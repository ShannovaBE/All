from __future__ import annotations

from pathlib import Path

from metadata.utils import read_json
from metadata.store_db import save_record

# LEGACY: one-time migration script from JSON metadata store to Postgres.
# Not used in production.


def migrate_store(store_dir: Path) -> int:
    migrated = 0
    for path in sorted(store_dir.glob("*.json")):
        try:
            record = read_json(path)
        except Exception:
            continue

        if not record.get("owner"):
            record["owner"] = "legacy"

        save_record(record)
        migrated += 1

    return migrated


if __name__ == "__main__":
    store_dir = Path("backend/metadata_store")
    count = migrate_store(store_dir)
    print(f"Migrated {count} records from JSON store.")
