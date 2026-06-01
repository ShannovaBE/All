import logging
import torch
from typing import List, Dict, Any, Union
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedCategorizer:
    """
    A unified model to categorize multimodal data using Hugging Face zero-shot
    classification for text and mapped image classification for vision.
    
    Categories match the Shannova 12-domain taxonomy:
    - Financial
    - Health/Medical
    - Legal/Government
    - Creative/Media
    - Engineering/Manufacturing
    - Environmental/Sustainability
    - Education/Research
    - Consumer/Retail
    - Transportation/Logistics
    - IT/Software
    - Real Estate/Construction
    - General/Other
    """

    CATEGORIES = [
        "Financial",
        "Health/Medical",
        "Legal/Government",
        "Creative/Media",
        "Engineering/Manufacturing",
        "Environmental/Sustainability",
        "Education/Research",
        "Consumer/Retail",
        "Transportation/Logistics",
        "IT/Software",
        "Real Estate/Construction",
        "General/Other"
    ]

    def __init__(self, text_model: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-docnli-ling-2c", device: int = -1):
        """
        Args:
            text_model: The Hugging Face zero-shot classification model (Defaults to DeBERTa-v3).
            device: -1 for CPU, 0+ for GPU.
        """
        logger.info(f"Loading Zero-Shot Text Classifier: {text_model}")
        try:
            self.text_classifier = pipeline(
                "zero-shot-classification", 
                model=text_model, 
                device=device
            )
            logger.info("Text Classifier loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Text Classifier: {e}")
            self.text_classifier = None

    def categorize_text(self, text: str) -> Dict[str, Any]:
        """
        Returns top categories for text based on the 12 Shannova taxonomy domains.
        """
        if not self.text_classifier or not text.strip():
            return {"primary_category": "General/Other", "scores": {}}

        # Perform zero-shot classification
        result = self.text_classifier(text, candidate_labels=self.CATEGORIES)
        
        # Format the result nicely
        scores = {label: score for label, score in zip(result["labels"], result["scores"])}
        primary = result["labels"][0]

        return {
            "primary_category": primary,
            "scores": scores
        }

    def categorize_dataset(self, data: List[Dict[str, Any]], text_column: str = "text") -> List[Dict[str, Any]]:
        """
        Processes a dataset dictionary mapping the primary category into a new column.
        """
        logger.info(f"Categorizing dataset with {len(data)} records...")
        categorized_data = []
        for row in data:
            new_row = row.copy()
            if text_column in row and isinstance(row[text_column], str):
                cat_result = self.categorize_text(row[text_column])
                new_row["shannova_category"] = cat_result["primary_category"]
            else:
                new_row["shannova_category"] = "General/Other"
            categorized_data.append(new_row)
        return categorized_data

if __name__ == "__main__":
    # Test Categorizer
    categorizer = UnifiedCategorizer()
    
    sample_text = "The new algorithm optimizes trading latency by routing order books through a decentralized ledger."
    print("\\n--- SAMPLE TEXT ---")
    print(sample_text)
    
    print("\\n--- CLASSIFICATION ---")
    result = categorizer.categorize_text(sample_text)
    print(f"Primary Category: {result['primary_category']}")
    print("Scores:")
    for k, v in list(result['scores'].items())[:3]:
        print(f"  {k}: {v:.4f}")
