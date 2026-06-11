import os
from transformers import pipeline

print("Pre-downloading Hugging Face models...")
# Download the DeBERTa Beta categorizer
pipeline("zero-shot-classification", model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-docnli-ling-2c")
print("DeBERTa downloaded.")

# Download the i2b2 Gamma NER model
pipeline("ner", model="obi/deid_roberta_i2b2")
print("i2b2 downloaded.")
print("All models successfully pre-downloaded!")