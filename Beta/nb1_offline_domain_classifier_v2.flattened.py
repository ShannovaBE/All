
# ==== cell 2 ====
import sys, platform, os
from datetime import datetime
import torch

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

print("=== Runtime ===")
print("RUN_ID:", RUN_ID)
print("Python:", sys.version.split()[0])
print("Platform:", platform.platform())
print("Torch:", torch.__version__)

# Device detection (M1 uses MPS when available)
mps_ok = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
device = "mps" if mps_ok else "cpu"
print("Device:", device)

# Note: we will enforce HF offline + local-only model loads later (Cell 6+).

# ==== cell 3 ====
from pathlib import Path

# Base directory = folder containing this notebook (works when run from the notebook directory)
BASE_DIR = Path.cwd()

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
CACHE_DIR = BASE_DIR / "cache"
MODEL_CACHE_DIR = CACHE_DIR / "hf_models"

# Create dirs
for p in [DATA_DIR, OUTPUT_DIR, CACHE_DIR, MODEL_CACHE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

print("=== Paths ===")
print("BASE_DIR:", BASE_DIR)
print("DATA_DIR:", DATA_DIR)
print("OUTPUT_DIR:", OUTPUT_DIR)
print("CACHE_DIR:", CACHE_DIR)
print("MODEL_CACHE_DIR:", MODEL_CACHE_DIR)

# ==== cell 4 ====
# === Cell 5: Imports + dependency checks (offline-safe, no hard crashes) ===

import re, json, time, hashlib
from pathlib import Path

import numpy as np
import pandas as pd

# Optional deps: we try-import and set flags, so the notebook can still run.
HAS_PIL = False
HAS_PYPDF2 = False
HAS_DOCX = False
HAS_OPENPYXL = False

# Images
try:
    from PIL import Image
    HAS_PIL = True
except Exception as e:
    Image = None
    _pil_err = repr(e)

# PDFs
try:
    import PyPDF2
    HAS_PYPDF2 = True
except Exception as e:
    PyPDF2 = None
    _pypdf2_err = repr(e)

# DOCX (python-docx)
try:
    # python-docx installs as the package name "docx"
    from docx import Document
    HAS_DOCX = True
except Exception as e:
    Document = None
    _docx_err = repr(e)

# XLSX engine
try:
    import openpyxl
    HAS_OPENPYXL = True
except Exception as e:
    openpyxl = None
    _openpyxl_err = repr(e)

# HF / ML (required for the classifier)
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoProcessor, AutoModel
from sentence_transformers import SentenceTransformer, util

print("=== Dependency check ===")
print("numpy:", np.__version__)
print("pandas:", pd.__version__)
print("torch:", torch.__version__)

print("\n--- Optional file support ---")
print("PIL (images):", "OK" if HAS_PIL else f"Missing ({_pil_err})")
print("PyPDF2 (pdf):", "OK" if HAS_PYPDF2 else f"Missing ({_pypdf2_err})")
print("python-docx (docx):", "OK" if HAS_DOCX else f"Missing ({_docx_err})")
print("openpyxl (xlsx):", "OK" if HAS_OPENPYXL else f"Missing ({_openpyxl_err})")

# Guidance without installing (offline requirement)
if not HAS_DOCX:
    print("\nNOTE: DOCX extraction will be disabled until python-docx is installed.")
    print("      Install later (when allowed): pip install python-docx")

# ==== cell 5 ====
# === Cell 6 (FIXED): Enforce offline mode WITHOUT moving your existing HF cache ===
import os
from pathlib import Path

# Offline switches (safe)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# If you already downloaded models before, they are likely in the default HF cache:
#   ~/.cache/huggingface/hub
# Do NOT override cache locations unless you intentionally want a project-local cache.

USE_PROJECT_HF_CACHE = False  # <-- set True only if you intentionally want all models in your project folder

if USE_PROJECT_HF_CACHE:
    HF_HOME_DIR = CACHE_DIR / "hf_home"
    HF_HOME_DIR.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(HF_HOME_DIR)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(MODEL_CACHE_DIR)
    os.environ["TRANSFORMERS_CACHE"] = str(MODEL_CACHE_DIR)

print("=== Offline mode enforced ===")
print("HF_HUB_OFFLINE:", os.environ.get("HF_HUB_OFFLINE"))
print("TRANSFORMERS_OFFLINE:", os.environ.get("TRANSFORMERS_OFFLINE"))
print("HF_DATASETS_OFFLINE:", os.environ.get("HF_DATASETS_OFFLINE"))
print("USE_PROJECT_HF_CACHE:", USE_PROJECT_HF_CACHE)

# Show where HF will likely look
home = Path.home()
default_hf_hub = home / ".cache" / "huggingface" / "hub"
print("Default HF hub cache:", default_hf_hub)
if USE_PROJECT_HF_CACHE:
    print("Project HF hub cache:", Path(os.environ["HUGGINGFACE_HUB_CACHE"]))

# ==== cell 6 ====
# === Cell 7: Model manifest (Hugging Face IDs) ===

MODEL_IDS = {
    # Text embeddings (multilingual + long context)
    "embed_text": "BAAI/bge-m3",

    # Language detection
    "lang_id": "papluca/xlm-roberta-base-language-detection",

    # Optional reranker (only used on ambiguous cases later)
    "reranker": "BAAI/bge-reranker-v2-m3",

    # Image zero-shot (domain prompts later)
    "image_vl": "google/siglip2-base-patch16-224",
}

# Feature switches
USE_RERANKER = True     # keeps accuracy high on close calls
USE_IMAGE_MODEL = True  # enable only if you will classify images

print("=== Model manifest ===")
for k, v in MODEL_IDS.items():
    print(f"{k:>10} -> {v}")

print("\n=== Feature flags ===")
print("USE_RERANKER:", USE_RERANKER)
print("USE_IMAGE_MODEL:", USE_IMAGE_MODEL)

# ==== cell 7 ====
# === Cell 8 (FIXED AGAIN): Verify models exist locally; return feature flags instead of mutating globals ===
import os
from pathlib import Path

STRICT_MODEL_CHECK = False  # set True to hard-stop if required models are missing

def _dedupe_existing_dirs(dirs):
    out = []
    seen = set()
    for d in dirs:
        d = Path(d).expanduser()
        if d.exists():
            key = str(d.resolve())
            if key not in seen:
                seen.add(key)
                out.append(d)
    return out

def hf_cache_candidates():
    home = Path.home()
    candidates = []

    # If user explicitly set cache env vars, include them
    env_hub = os.environ.get("HUGGINGFACE_HUB_CACHE")
    env_tf  = os.environ.get("TRANSFORMERS_CACHE")
    env_home = os.environ.get("HF_HOME")

    if env_hub:
        candidates.append(Path(env_hub))
    if env_tf:
        candidates.append(Path(env_tf))
    if env_home:
        candidates.append(Path(env_home) / "hub")

    # Common defaults on mac/linux
    candidates.append(home / ".cache" / "huggingface" / "hub")
    candidates.append(home / ".cache" / "huggingface" / "transformers")

    # Your project cache folder (if you use it)
    candidates.append(MODEL_CACHE_DIR)

    return _dedupe_existing_dirs(candidates)

def hub_repo_folder_name(repo_id: str) -> str:
    # HF hub cache uses "models--ORG--REPO"
    return "models--" + repo_id.replace("/", "--")

def find_repo_in_caches(repo_id: str, caches):
    folder = hub_repo_folder_name(repo_id)
    for c in caches:
        if (c / folder).exists():
            return c
    return None

def verify_models_local(model_ids: dict, want_reranker: bool, want_image: bool):
    caches = hf_cache_candidates()
    print("=== Searching these HF cache locations ===")
    for c in caches:
        print("-", c)

    required_keys = ["embed_text", "lang_id"]
    optional_keys = []
    if want_reranker:
        optional_keys.append("reranker")
    if want_image:
        optional_keys.append("image_vl")

    found = {}
    missing_required = []
    missing_optional = []

    print("\n=== Verifying required models ===")
    for key in required_keys:
        rid = model_ids[key]
        loc = find_repo_in_caches(rid, caches)
        if loc is None:
            print(f"[MISSING] {key}: {rid}")
            missing_required.append((key, rid))
        else:
            print(f"[OK] {key}: {rid} (found in {loc})")
            found[key] = loc

    print("\n=== Verifying optional models ===")
    for key in optional_keys:
        rid = model_ids[key]
        loc = find_repo_in_caches(rid, caches)
        if loc is None:
            print(f"[MISSING] {key}: {rid}")
            missing_optional.append((key, rid))
        else:
            print(f"[OK] {key}: {rid} (found in {loc})")
            found[key] = loc

    # Recommend feature flags based on availability (no globals mutated)
    use_reranker_ok = want_reranker and not any(k == "reranker" for k, _ in missing_optional)
    use_image_ok = want_image and not any(k == "image_vl" for k, _ in missing_optional)

    if missing_required:
        print("\n⚠️ Required models are not available locally.")
        print("Because we are offline, we cannot download them during this run.")
        print("\nMissing required:")
        for k, rid in missing_required:
            print(f"- {k}: {rid}")

        print("\nNext steps (one-time, when you have internet):")
        print("1) Temporarily set offline flags OFF (HF_HUB_OFFLINE=0, TRANSFORMERS_OFFLINE=0)")
        print("2) Load each model once so it caches locally")
        print("3) Turn offline back ON and rerun")

        if STRICT_MODEL_CHECK:
            raise RuntimeError("Missing required HF models in local cache (STRICT_MODEL_CHECK=True).")

    return {
        "found_model_caches": found,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "use_reranker_recommended": use_reranker_ok,
        "use_image_recommended": use_image_ok,
        "cache_dirs_scanned": caches,
    }

MODEL_CHECK = verify_models_local(
    MODEL_IDS,
    want_reranker=USE_RERANKER,
    want_image=USE_IMAGE_MODEL
)

FOUND_MODEL_CACHES = MODEL_CHECK["found_model_caches"]

# Apply recommendations
USE_RERANKER = MODEL_CHECK["use_reranker_recommended"]
USE_IMAGE_MODEL = MODEL_CHECK["use_image_recommended"]

print("\n=== Post-check feature flags ===")
print("USE_RERANKER:", USE_RERANKER)
print("USE_IMAGE_MODEL:", USE_IMAGE_MODEL)
print("FOUND_MODEL_CACHES keys:", list(FOUND_MODEL_CACHES.keys()))

# ==== cell 8 ====
# === Cell 9: Load language detection model (offline) ===
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

LANG_TOKENIZER = AutoTokenizer.from_pretrained(
    MODEL_IDS["lang_id"],
    cache_dir=str(MODEL_CACHE_DIR),
    local_files_only=True,
)
LANG_MODEL = AutoModelForSequenceClassification.from_pretrained(
    MODEL_IDS["lang_id"],
    cache_dir=str(MODEL_CACHE_DIR),
    local_files_only=True,
)
LANG_MODEL.to(device)
LANG_MODEL.eval()

def detect_language(text: str, max_chars: int = 2000):
    """
    Returns (lang_label, confidence_float).
    Uses model's id2label mapping.
    """
    if not text:
        return ("unknown", 0.0)

    sample = text[:max_chars]
    with torch.no_grad():
        inputs = LANG_TOKENIZER(sample, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        logits = LANG_MODEL(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        idx = int(torch.argmax(probs).item())
        conf = float(probs[idx].item())

    label = LANG_MODEL.config.id2label.get(idx, str(idx))
    return (label, conf)

print("=== Language ID model loaded ===")
print("Model:", MODEL_IDS["lang_id"])
print("Device:", device)
print("Quick test:", detect_language("This is an English sentence about healthcare and hospitals."))

# ==== cell 9 ====
# === Cell 10: Load embedding model (offline) + embedding helper ===
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Some embedding models may require trust_remote_code for custom pooling.
# Offline is safe as long as the repo is already cached.
try:
    EMBED_MODEL = SentenceTransformer(
        MODEL_IDS["embed_text"],
        cache_folder=str(MODEL_CACHE_DIR),
        device=device,
        trust_remote_code=True,
    )
except Exception as e:
    print("Warning: embedding model failed on device =", device, "->", repr(e))
    print("Falling back to CPU for embedding model.")
    EMBED_MODEL = SentenceTransformer(
        MODEL_IDS["embed_text"],
        cache_folder=str(MODEL_CACHE_DIR),
        device="cpu",
        trust_remote_code=True,
    )

def _chunk_text(text: str, chunk_chars: int):
    text = text or ""
    text = text.strip()
    if not text:
        return []
    return [text[i:i+chunk_chars] for i in range(0, len(text), chunk_chars)]

def embed_text(text: str):
    """
    Accuracy-first embedding:
    - chunk long text
    - embed each chunk
    - average embeddings
    - normalize final vector
    Returns: np.ndarray shape (dim,)
    """
    text = (text or "")[:THRESHOLDS["max_text_chars"]]
    chunks = _chunk_text(text, THRESHOLDS["chunk_chars"])
    if not chunks:
        # Return a zero vector with correct dim by embedding an empty-ish token once
        v = EMBED_MODEL.encode([" "], normalize_embeddings=True)[0]
        return np.array(v, dtype=np.float32)

    embs = EMBED_MODEL.encode(chunks, normalize_embeddings=True)
    mean_emb = np.mean(embs, axis=0)
    mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-12)
    return mean_emb.astype(np.float32)

print("=== Embedding model loaded ===")
print("Model:", MODEL_IDS["embed_text"])
print("Embedding dim:", int(EMBED_MODEL.get_sentence_embedding_dimension()))

# ==== cell 10 ====

