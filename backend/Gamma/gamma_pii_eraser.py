import re
import json
import logging
from typing import List, Dict, Any, Union
from transformers import pipeline
from faker import Faker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PIIEraser:
    """
    A robust PII eraser that combines deterministic (Regex) and 
    probabilistic (Hugging Face NER) approaches.
    
    Identifies and redacts:
    - Names, Hospitals, Dates, and Healthcare entities (via Medical NER)
    - Emails (via Regex)
    - Phones (via Regex)
    - SSNs (via Regex)
    - Credit Cards (via Regex)
    """

    def __init__(self, model_name: str = "obi/deid_roberta_i2b2", device: int = -1):
        """
        Args:
            model_name: The Hugging Face model representing the NER pipeline.
            device: -1 for CPU, 0+ for GPU.
        """
        logger.info(f"Loading NER pipeline: {model_name}")
        try:
            self.ner_pipeline = pipeline(
                "ner", 
                model=model_name, 
                tokenizer=model_name,
                aggregation_strategy="simple",
                device=device
            )
            logger.info("NER pipeline loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load NER pipeline: {e}")
            self.ner_pipeline = None

        # --- Deterministic Patterns ---
        self.patterns = {
            "EMAIL": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "PHONE": r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}",
            "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
            "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
        }

    def process_text(self, text: str) -> str:
        """
        Redacts PII from a single text string.
        """
        if not text or not isinstance(text, str):
            return text

        scrubbed_text = text

        # 1. Deterministic Scrubbing (Regex)
        for label, pattern in self.patterns.items():
            scrubbed_text = re.sub(pattern, f"[{label}_REDACTED]", scrubbed_text)

        # 2. Probabilistic Scrubbing (NER)
        if self.ner_pipeline is not None:
            # Run NER inference
            entities = self.ner_pipeline(scrubbed_text)
            
            # Sort entities by start index in descending order to avoid index shifting during replacement
            entities = sorted(entities, key=lambda x: x["start"], reverse=True)
            
            for ent in entities:
                start = ent["start"]
                end = ent["end"]
                entity_group = ent["entity_group"] # e.g., PER, ORG, LOC
                # Replace the entity with a redacted token
                scrubbed_text = scrubbed_text[:start] + f"[{entity_group}_REDACTED]" + scrubbed_text[end:]

        return scrubbed_text

    def process_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively redacts PII from a dictionary.
        """
        scrubbed_dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                scrubbed_dict[key] = self.process_text(value)
            elif isinstance(value, dict):
                scrubbed_dict[key] = self.process_dict(value)
            elif isinstance(value, list):
                scrubbed_dict[key] = [self.process_dict(v) if isinstance(v, dict) else self.process_text(v) if isinstance(v, str) else v for v in value]
            else:
                scrubbed_dict[key] = value
        return scrubbed_dict

    def process_dataset(self, dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes an entire dataset (list of dictionaries).
        """
        logger.info(f"Processing dataset with {len(dataset)} records...")
        return [self.process_dict(row) for row in dataset]


# Example usage block (can be run directly to test)
if __name__ == "__main__":
    eraser = PIIEraser()
    
    # Let's generate a complex piece of text using Faker and manual strings
    fake = Faker()
    test_text = (
        f"Contact {fake.name()} at {fake.email()} or call {fake.phone_number() }. "
        f"Their SSN is {fake.ssn()} and they work at Apple Inc. in Cupertino, California. "
        f"Payment was made using card 4532 1234 5678 9010."
    )
    
    print("\n--- ORIGINAL TEXT ---")
    print(test_text)
    
    scrubbed = eraser.process_text(test_text)
    print("\n--- SCRUBBED TEXT ---")
    print(scrubbed)
