import os
import re
from typing import Any, Dict

import pandas as pd


PII_PATTERNS = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "PHONE": re.compile(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "DATE": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
}

CATEGORY_KEYWORDS = {
    "Financial": {
        "finance",
        "financial",
        "trading",
        "stock",
        "market",
        "invoice",
        "payment",
        "revenue",
        "expense",
        "bank",
    },
    "Health/Medical": {
        "health",
        "medical",
        "patient",
        "hospital",
        "diagnosis",
        "clinical",
        "doctor",
        "drug",
        "treatment",
    },
    "Legal/Government": {
        "legal",
        "court",
        "contract",
        "law",
        "government",
        "permit",
        "regulation",
        "policy",
    },
    "Creative/Media": {
        "media",
        "creative",
        "music",
        "video",
        "image",
        "photo",
        "ad",
        "campaign",
    },
    "Engineering/Manufacturing": {
        "engineering",
        "manufacturing",
        "machine",
        "sensor",
        "factory",
        "cad",
        "production",
        "supply",
    },
    "Environmental/Sustainability": {
        "environment",
        "sustainability",
        "climate",
        "carbon",
        "emission",
        "weather",
        "energy",
    },
    "Education/Research": {
        "education",
        "research",
        "student",
        "study",
        "experiment",
        "paper",
        "survey",
    },
    "Consumer/Retail": {
        "retail",
        "consumer",
        "customer",
        "basket",
        "sku",
        "store",
        "ecommerce",
        "purchase",
    },
    "Transportation/Logistics": {
        "transport",
        "logistics",
        "shipment",
        "delivery",
        "fleet",
        "route",
        "warehouse",
    },
    "IT/Software": {
        "software",
        "it",
        "app",
        "api",
        "code",
        "server",
        "database",
        "cyber",
        "latency",
        "bug",
    },
    "Real Estate/Construction": {
        "real estate",
        "property",
        "building",
        "construction",
        "listing",
        "rent",
        "lease",
        "mortgage",
    },
}


def _scrub_text(text: str) -> str:
    scrubbed = text
    for label, pattern in PII_PATTERNS.items():
        scrubbed = pattern.sub(f"[{label}_REDACTED]", scrubbed)
    return scrubbed


def _categorize_text(text: str) -> tuple[str, float]:
    lowered = (text or "").lower()
    best_category = "General/Other"
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_category = category
            best_score = score

    if best_score <= 0:
        return best_category, 0.5
    if best_score == 1:
        return best_category, 0.72
    if best_score == 2:
        return best_category, 0.84
    return best_category, 0.93


def _score_quality(*, row_count: int, col_count: int, missing_pct: float, duplicate_rows: int) -> tuple[float, Dict[str, float], str]:
    completeness = max(0.0, 100.0 - min(missing_pct, 100.0) * 1.6)
    uniqueness = max(0.0, 100.0 - (duplicate_rows / max(row_count, 1)) * 100.0)
    structure = 100.0 if col_count >= 3 else 72.0 if col_count == 2 else 55.0
    volume = 92.0 if row_count >= 100 else 84.0 if row_count >= 10 else 76.0 if row_count >= 2 else 58.0

    dimensions = {
        "Completeness": round(completeness, 1),
        "Uniqueness": round(uniqueness, 1),
        "Consistency": round(structure, 1),
        "Representativeness": round(volume, 1),
    }
    overall = round(
        (dimensions["Completeness"] * 0.35)
        + (dimensions["Uniqueness"] * 0.25)
        + (dimensions["Consistency"] * 0.20)
        + (dimensions["Representativeness"] * 0.20),
        1,
    )

    if overall >= 90:
        best_use_case = "Production analytics and model training"
    elif overall >= 80:
        best_use_case = "Business intelligence and exploratory analysis"
    elif overall >= 70:
        best_use_case = "Exploratory Data Analysis (EDA)"
    else:
        best_use_case = "Needs cleaning before reuse"

    return overall, dimensions, best_use_case


def process_file_pipeline(file_path: str, original_filename: str) -> Dict[str, Any]:
    is_csv = original_filename.lower().endswith(".csv")

    predicted_category = "General/Other"
    confidence = 0.5
    quality_score = 75.0
    dimensions: Dict[str, float] = {}
    best_use_case = "Exploratory Data Analysis (EDA)"
    stats: Dict[str, Any] = {}
    data_sample = []
    pii_report = {"redacted_cells": 0, "status": "No sensitive PII detected."}

    if is_csv:
        try:
            df = pd.read_csv(file_path)
            original_df = df.copy(deep=True)

            row_count = len(df)
            col_count = len(df.columns)
            missing_cells = int(df.isnull().sum().sum())
            total_cells = row_count * col_count
            missing_pct = (missing_cells / total_cells) * 100 if total_cells > 0 else 0.0
            duplicate_rows = int(df.duplicated().sum()) if row_count > 0 else 0

            stats = {
                "row_count": row_count,
                "column_count": col_count,
                "missing_cells": missing_cells,
                "missing_percentage": round(missing_pct, 2),
                "duplicate_rows": duplicate_rows,
            }

            object_columns = df.select_dtypes(include=["object", "string"]).columns
            redacted_cells = 0
            for col in object_columns:
                source_series = df[col].fillna("").astype(str)
                scrubbed_series = source_series.map(_scrub_text)
                redacted_cells += int((source_series != scrubbed_series).sum())
                df[col] = scrubbed_series

            pii_report = {
                "redacted_cells": redacted_cells,
                "status": (
                    f"Scrubbed {redacted_cells} cell(s) containing sensitive PII."
                    if redacted_cells > 0
                    else "No sensitive PII detected."
                ),
            }

            df.to_csv(file_path, index=False)
            data_sample = df.head(5).fillna("").to_dict(orient="records")

            classification_text = " ".join(
                [
                    original_filename,
                    " ".join(str(col) for col in df.columns),
                    df.head(10).fillna("").astype(str).to_string(index=False),
                ]
            )
            predicted_category, confidence = _categorize_text(classification_text)
            quality_score, dimensions, best_use_case = _score_quality(
                row_count=row_count,
                col_count=col_count,
                missing_pct=missing_pct,
                duplicate_rows=duplicate_rows,
            )
        except Exception as exc:
            predicted_category, confidence = _categorize_text(original_filename)
            pii_report = {"redacted_cells": 0, "status": f"Fast pipeline fallback used: {exc}"}
    else:
        ext = os.path.splitext(original_filename.lower())[1]
        predicted_category, confidence = _categorize_text(f"{original_filename} {ext}")

    generated_tags = [predicted_category.lower().replace("/", "-")]
    if quality_score >= 90:
        generated_tags.append("production-ready")
    elif quality_score >= 75:
        generated_tags.append("high-quality")
    else:
        generated_tags.append("needs-cleaning")

    details = [
        "PII scrubbed with deterministic fast path.",
        f"Categorized as {predicted_category}.",
        f"Scored {quality_score:.1f}/100.",
        f"Best Use Case: {best_use_case}",
    ] + [f"{name}: {value:.1f}" for name, value in dimensions.items()]

    return {
        "predicted_category": predicted_category,
        "confidence": confidence,
        "quality_score": quality_score,
        "details": details,
        "generated_tags": generated_tags,
        "best_use_case": best_use_case,
        "stats": stats,
        "pii_report": pii_report,
        "data_sample": data_sample,
    }
