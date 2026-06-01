import sys
import os
from typing import List, Dict, Any

# Ensure Alpha, Beta, Gamma can be imported
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "Alpha"))
sys.path.insert(0, os.path.join(base_dir, "Beta"))
sys.path.insert(0, os.path.join(base_dir, "Gamma"))

from gamma_pii_eraser import PIIEraser
from beta_categorizer import UnifiedCategorizer
from shanova_unified_engine import ShanovaUnifiedEngine

# Initialize engines cleanly (singletons to avoid reloading large HF models on every request)
eraser = PIIEraser()
categorizer = UnifiedCategorizer()
engine = ShanovaUnifiedEngine(output_root="outputs")

def scrub_pii(data: List[Dict]) -> List[Dict]:
    """
    Uses the Gamma Hugging Face Eraser to scrub PII from the dataset.
    """
    return eraser.process_dataset(data)

def categorize_data(data: List[Dict]) -> List[str]:
    """
    Uses the Beta Hugging Face Categorizer to label the data.
    Since MVP takes random user rows, we'll categorize the first row's JSON string representation
    as a proxy for the entire set to save compute, or just default.
    """
    if not data:
        return ["General/Other"]
    
    # We serialize the first row to string for zero-shot categorization as a test
    sample_text = str(data[0])
    result = categorizer.categorize_text(sample_text)
    primary_category = result.get("primary_category", "General/Other")
    return [primary_category]

def compute_quality_score(data: List[Dict]) -> Dict[str, Any]:
    """
    Uses the Alpha Unified Engine to compute quality score for the upload.
    For this MVP, we mock the required file conversion if it's strictly in-memory testing.
    Since Alpha engine usually takes a CSV file, we can save data to temp, run engine, return score.
    """
    import tempfile
    import csv
    
    if not data:
        return {}
        
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        temp_path = f.name
        
    try:
        report = engine.run_assessment(
            data=temp_path,
            modality="tabular",
        )
        # Extract the highest-level score data
        return {
            "overall_score": report.get("overall_score", 0),
            "quality_tier": report.get("quality_tier", "Unknown"),
            "dimensions": report.get("dimension_scores", {})
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
