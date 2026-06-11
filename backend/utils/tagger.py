# backend/utils/tagger.py
from typing import Any, Dict, List, Optional

def run_tagger(file_path: str, *, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Wrapper to call the external tagging code.

    This should eventually call your teammate's implementation, which:
      - inspects `file_path`
      - uses `user_id` if needed
      - returns tags + a hash that THEY compute.

    Expected return structure (example):
    {
        "tag_hash": "abc123...",      # hash computed by tagger side
        "tags": ["medical", "uk", "csv", "2020"],
        "extra": {...}                # anything else they want
    }
    """

    # ⚠️ DEV STUB: replace this with a real implementation.
    # For now we just return something simple so the pipeline works.
    return {
        "tag_hash": "dev-placeholder-hash",
        "tags": [],        # e.g. ["demo"]
        "extra": {
            "note": "replace run_tagger with real implementation"
        },
        "user_id": user_id,
    }
