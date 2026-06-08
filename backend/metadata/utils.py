import json
from datetime import datetime, timezone
from typing import Any

def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 with 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def write_json(path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

def read_json(path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
