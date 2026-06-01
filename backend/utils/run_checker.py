# backend/utils/run_checker.py

def run_data_checker(file_path: str):
    """
    Temporary stub. Later:
    - Load CSV/JSON/JSONL
    - Call Shannova's run_quality_checks(df)
    - Map its metrics into quality_score + details + subscores.
    """
    import random
    score = round(random.uniform(75, 99), 2)
    return {
        "quality_score": score,
        "status": "passed" if score > 80 else "needs_review",
        "details": ["File received and analyzed successfully."],
    }
