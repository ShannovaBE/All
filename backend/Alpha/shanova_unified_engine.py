from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import logging
import math
import os
import re
import string
import uuid
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from PIL import Image, ImageFile, UnidentifiedImageError

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ImageFile.LOAD_TRUNCATED_IMAGES = True


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
TABULAR_EXTENSIONS = {".csv", ".parquet", ".pq", ".json", ".xlsx", ".xls"}
TEXT_EXTENSIONS = {".txt", ".md", ".log"}

PII_NAME_HINTS = {
    "name",
    "first_name",
    "last_name",
    "full_name",
    "email",
    "phone",
    "mobile",
    "ssn",
    "social",
    "dob",
    "birth",
    "address",
    "zip",
    "postal",
    "passport",
    "license",
    "account",
    "iban",
    "credit",
    "card",
}

PII_REGEX = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
}

DIMENSIONS = [
    "Completeness",
    "Validity",
    "Consistency",
    "Uniqueness",
    "Representativeness",
    "Balance",
    "Timeliness",
]

CATEGORY_TO_DIMENSION = {
    "Data Integrity & Validation": "Consistency",
    "Missingness Analysis": "Completeness",
    "Distribution & Normality": "Validity",
    "Multivariate Tests": "Validity",
    "Outlier Detection": "Validity",
    "Two-Sample/Drift Tests": "Representativeness",
    "Multivariate Divergences": "Representativeness",
    "Coverage & Sampling": "Representativeness",
    "Time Series: Stationarity": "Timeliness",
    "Time Series: Autocorrelation": "Timeliness",
    "Time Series: Spectral & Cointegration": "Timeliness",
    "Change-Point Detection": "Timeliness",
    "Complexity & Causality": "Consistency",
    "Information Theory": "Consistency",
    "Manifold & Geometry": "Representativeness",
    "Privacy & Anonymity": "Validity",
    "Data Leakage": "Validity",
    "Label Quality": "Balance",
    "Text Quality": "Consistency",
    "Vision Quality": "Validity",
    "Geospatial Quality": "Validity",
    "Graph Quality": "Consistency",
    "Metadata & Governance": "Completeness",
}


@dataclass
class TestResult:
    name: str
    status: str
    metric: Optional[Any] = None
    interpretation: str = ""
    extra: Optional[Dict[str, Any]] = None


class ShanovaUnifiedEngine:
    """
    Unified multimodal data quality engine:
    - tabular: 208-test battery dynamically loaded from TesterV1i.ipynb
    - image: visual health checks
    - text: nlp health checks
    """

    def __init__(
        self,
        tester_notebook: Union[str, Path] = "TesterV1i.ipynb",
        output_root: Union[str, Path] = "outputs",
        max_rows: int = 200_000,
        seed: int = 42,
        dimension_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self.tester_notebook = Path(tester_notebook)
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

        self.config: Dict[str, Any] = {
            "max_rows": int(max_rows),
            "max_cols": 500,
            "seed": int(seed),
            "sampling_ratio": 1.0,
            "run_outlier_tests": True,
            "run_drift_tests": True,
            "run_ts_tests": True,
            "run_privacy_tests": True,
            "warn_missing_pct": 5.0,
            "fail_missing_pct": 20.0,
            "warn_outlier_pct": 10.0,
            "fail_outlier_pct": 30.0,
            "warn_vif": 10.0,
            "fail_vif": 50.0,
            "warn_condition_number": 1e5,
            "fail_condition_number": 1e8,
            "output_dir": None,
        }

        self.status_to_score = {
            "PASS": 100.0,
            "WARN": 70.0,
            "FAIL": 20.0,
            "SKIP": 70.0,
            "NA": 70.0,
        }

        self.dimension_weights = dimension_weights or {
            "Completeness": 0.16,
            "Validity": 0.16,
            "Consistency": 0.14,
            "Uniqueness": 0.14,
            "Representativeness": 0.14,
            "Balance": 0.13,
            "Timeliness": 0.13,
        }

        self._dep_namespace, self._deps = self._load_dependency_namespace()
        self._tester_namespace: Dict[str, Any] = {}
        self._test_names: List[str] = []
        self._test_registry: Dict[str, Callable[..., Any]] = {}
        self._test_categories: Dict[str, List[int]] = {}
        self._test_to_dimension: Dict[str, str] = {}

        self._load_tester_assets()

    # ------------------------- public api -------------------------

    def run_assessment(
        self,
        data: Any,
        modality: str = "auto",
        compare_data: Any = None,
        target_col: Optional[str] = None,
        id_col: Optional[str] = None,
        time_col: Optional[str] = None,
        datetime_cols: Optional[List[str]] = None,
        labels: Optional[Dict[str, Any]] = None,
        min_image_resolution: Tuple[int, int] = (224, 224),
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        selected_modality = self._detect_modality(data, modality)
        run_dir = self._prepare_run_dir(selected_modality, data, output_dir=output_dir)
        logger = self._build_run_logger(run_dir)

        start_ts = datetime.now(timezone.utc)
        logger.info("Starting assessment (modality=%s)", selected_modality)

        input_hash = self._hash_input(data)
        compare_hash = self._hash_input(compare_data) if compare_data is not None else None

        try:
            if selected_modality == "tabular":
                report = self._evaluate_tabular(
                    data=data,
                    compare_data=compare_data,
                    target_col=target_col,
                    id_col=id_col,
                    time_col=time_col,
                    datetime_cols=datetime_cols,
                    input_hash=input_hash,
                    compare_hash=compare_hash,
                    logger=logger,
                )
            elif selected_modality == "image":
                report = self._evaluate_images(
                    data=data,
                    labels=labels,
                    min_resolution=min_image_resolution,
                )
            elif selected_modality == "text":
                report = self._evaluate_text(data=data)
            else:
                raise ValueError(f"Unsupported modality: {selected_modality}")

            report["modality"] = selected_modality
            report["input_hash_sha256"] = input_hash
            if compare_hash:
                report["compare_hash_sha256"] = compare_hash
            report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
            report["run_id"] = run_dir.name

            chart_paths, encoded = self._generate_dashboard_assets(report, run_dir)
            html = self._build_html_report(report, encoded)

            reports_dir = run_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            json_path = reports_dir / "assessment_report.json"
            html_path = reports_dir / "assessment_report.html"

            json_path.write_text(json.dumps(report, indent=2, default=self._json_default), encoding="utf-8")
            html_path.write_text(html, encoding="utf-8")

            report["artifacts"] = {
                "json_report": str(json_path),
                "html_report": str(html_path),
                "charts": {k: str(v) for k, v in chart_paths.items()},
                "log": str(run_dir / "logs" / "assessment.log"),
            }

            elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
            report["runtime_seconds"] = round(elapsed, 3)
            logger.info("Assessment complete in %.3fs", elapsed)
            return report
        finally:
            self._close_logger(logger)

    # ------------------------- loader / setup -------------------------

    def _load_dependency_namespace(self) -> Tuple[Dict[str, Any], Dict[str, Tuple[str, bool]]]:
        ns: Dict[str, Any] = {}
        deps: Dict[str, Tuple[str, bool]] = {
            "scipy": ("scipy", False),
            "sklearn": ("sklearn", False),
            "statsmodels": ("statsmodels", False),
            "pingouin": ("pingouin", False),
            "pyod": ("pyod", False),
            "torch": ("torch", False),
        }

        try:
            from scipy import linalg, spatial, stats

            ns.update({"stats": stats, "spatial": spatial, "linalg": linalg})
            deps["scipy"] = ("scipy", True)
        except Exception:
            pass

        try:
            from sklearn.decomposition import PCA
            from sklearn.ensemble import IsolationForest
            from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
            from sklearn.preprocessing import StandardScaler

            ns.update(
                {
                    "PCA": PCA,
                    "IsolationForest": IsolationForest,
                    "NearestNeighbors": NearestNeighbors,
                    "LocalOutlierFactor": LocalOutlierFactor,
                    "StandardScaler": StandardScaler,
                }
            )
            deps["sklearn"] = ("sklearn", True)
        except Exception:
            pass

        try:
            import statsmodels.api as sm
            import statsmodels.tsa.stattools as tsat
            from statsmodels.stats.outliers_influence import (
                variance_inflation_factor as sm_vif,
            )

            ns.update({"sm": sm, "tsat": tsat, "sm_vif": sm_vif})
            deps["statsmodels"] = ("statsmodels", True)
        except Exception:
            pass

        try:
            import pingouin as pg

            ns["pg"] = pg
            deps["pingouin"] = ("pingouin", True)
        except Exception:
            pass

        try:
            from pyod.models.copod import COPOD
            from pyod.models.hbos import HBOS
            from pyod.models.knn import KNN as PYODKNN

            ns.update({"HBOS": HBOS, "COPOD": COPOD, "PYODKNN": PYODKNN})
            deps["pyod"] = ("pyod", True)
        except Exception:
            pass

        try:
            import torch
            import torch.nn as nn

            ns.update({"torch": torch, "nn": nn})
            deps["torch"] = ("torch", True)
        except Exception:
            pass

        return ns, deps

    def _load_tester_assets(self) -> None:
        if not self.tester_notebook.exists():
            raise FileNotFoundError(
                f"Tester notebook not found: {self.tester_notebook}. "
                "ShanovaUnifiedEngine requires TesterV1i.ipynb for the 208-test battery."
            )

        namespace: Dict[str, Any] = {
            "np": np,
            "pd": pd,
            "math": math,
            "re": re,
            "hashlib": hashlib,
            "Path": Path,
            "logging": logging,
            "Counter": Counter,
            "defaultdict": defaultdict,
            "TestResult": TestResult,
            "CONFIG": dict(self.config),
            "DEPS": dict(self._deps),
            "is_datetime": self._is_datetime,
            "safe_num": self._safe_num,
            "safe_cat": self._safe_cat,
            "sha256_file": self._sha256_file,
        }
        namespace.update(self._dep_namespace)

        nb = json.loads(self.tester_notebook.read_text(encoding="utf-8"))
        selected_nodes: List[ast.AST] = []

        for cell in nb.get("cells", []):
            if cell.get("cell_type") != "code":
                continue

            src = "".join(cell.get("source", []))
            if not src.strip():
                continue

            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue

            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    if (
                        node.name.startswith("test_")
                        or node.name.startswith("get_test_registry")
                        or node.name in {"skip", "compute_dqa_score", "compute_category_scores"}
                    ):
                        selected_nodes.append(node)
                elif isinstance(node, ast.Assign):
                    targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                    if any(t.startswith("TEST_NAMES_") or t == "TEST_CATEGORIES" for t in targets):
                        selected_nodes.append(node)

        module = ast.Module(body=selected_nodes, type_ignores=[])
        compiled = compile(module, filename=str(self.tester_notebook), mode="exec")
        exec(compiled, namespace, namespace)

        ordered_test_lists = [
            "TEST_NAMES_FIRST_25",
            "TEST_NAMES_26_TO_50",
            "TEST_NAMES_51_TO_75",
            "TEST_NAMES_76_TO_100",
            "TEST_NAMES_101_TO_125",
            "TEST_NAMES_126_TO_208",
        ]

        test_names: List[str] = []
        for name in ordered_test_lists:
            chunk = namespace.get(name, [])
            if isinstance(chunk, list):
                test_names.extend(chunk)

        if len(test_names) != 208:
            raise RuntimeError(
                f"Unable to recover full 208-test list from {self.tester_notebook}; found {len(test_names)} tests."
            )

        registry_fn_names = [
            "get_test_registry",
            "get_test_registry_26_50",
            "get_test_registry_51_75",
            "get_test_registry_76_100",
            "get_test_registry_101_125",
            "get_test_registry_126_208",
        ]

        registry: Dict[str, Callable[..., Any]] = {}
        for fn_name in registry_fn_names:
            fn = namespace.get(fn_name)
            if callable(fn):
                registry.update(fn())

        self._tester_namespace = namespace
        self._test_names = test_names
        self._test_registry = registry
        self._test_categories = namespace.get("TEST_CATEGORIES", {})
        self._test_to_dimension = self._build_test_dimension_map(test_names, self._test_categories)

    # ------------------------- helpers -------------------------

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return float(max(low, min(high, value)))

    @staticmethod
    def _safe_mean(values: Sequence[float]) -> float:
        vals = [float(v) for v in values if v is not None and not pd.isna(v)]
        return float(np.mean(vals)) if vals else 0.0

    @staticmethod
    def _quality_tier(score: float) -> str:
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Good"
        if score >= 55:
            return "Fair"
        return "Poor"

    @staticmethod
    def _json_default(obj: Any) -> Any:
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return str(obj)

    @staticmethod
    def _is_datetime(series: pd.Series) -> bool:
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        non_na = series.dropna()
        if non_na.empty:
            return False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pd.to_datetime(non_na.sample(min(50, len(non_na))), errors="raise")
            return True
        except Exception:
            return False

    def _safe_num(self, df: pd.DataFrame) -> List[str]:
        return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def _safe_cat(self, df: pd.DataFrame, max_card: int = 100) -> List[str]:
        cats: List[str] = []
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]) and not self._is_datetime(df[col]):
                uniq = df[col].nunique(dropna=True)
                if 2 <= uniq <= max_card:
                    cats.append(col)
        return cats

    @staticmethod
    def _sha256_file(path: Path) -> str:
        hsh = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                hsh.update(chunk)
        return hsh.hexdigest()

    def _hash_input(self, data: Any) -> str:
        if data is None:
            return ""

        if isinstance(data, pd.DataFrame):
            hashed = pd.util.hash_pandas_object(data, index=True).values
            return hashlib.sha256(hashed.tobytes()).hexdigest()

        if isinstance(data, np.ndarray):
            return hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()

        if isinstance(data, (str, Path)):
            path = Path(data)
            if path.exists() and path.is_file():
                return self._sha256_file(path)
            if path.exists() and path.is_dir():
                hsh = hashlib.sha256()
                for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
                    hsh.update(str(file_path.relative_to(path)).encode("utf-8"))
                    hsh.update(self._sha256_file(file_path).encode("utf-8"))
                return hsh.hexdigest()
            return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

        if isinstance(data, (list, tuple)):
            hsh = hashlib.sha256()
            for item in data:
                hsh.update(self._hash_input(item).encode("utf-8"))
            return hsh.hexdigest()

        return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

    def _prepare_run_dir(
        self,
        modality: str,
        data: Any,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        if output_dir is not None:
            run_dir = Path(output_dir)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            input_hash = self._hash_input(data)[:10] if data is not None else "noinput"
            run_dir = self.output_root / f"{modality}_run_{ts}_{input_hash}"

        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        (run_dir / "charts").mkdir(parents=True, exist_ok=True)
        return run_dir

    def _build_run_logger(self, run_dir: Path) -> logging.Logger:
        logger_name = f"ShanovaUnifiedEngine.{uuid.uuid4().hex[:10]}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        file_handler = logging.FileHandler(run_dir / "logs" / "assessment.log", encoding="utf-8")
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        return logger

    @staticmethod
    def _close_logger(logger: logging.Logger) -> None:
        handlers = list(logger.handlers)
        for handler in handlers:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)

    # ------------------------- modality loaders -------------------------

    def _detect_modality(self, data: Any, modality: str = "auto") -> str:
        if modality and modality.lower() != "auto":
            return modality.lower()

        if isinstance(data, pd.DataFrame):
            return "tabular"

        if isinstance(data, np.ndarray) and data.ndim in (2, 3):
            return "image"

        if isinstance(data, (list, tuple)) and data:
            if all(isinstance(x, np.ndarray) for x in data):
                return "image"
            if all(isinstance(x, str) for x in data):
                path_count = sum(Path(x).exists() for x in data)
                if path_count == 0:
                    return "text"
                paths = [Path(x) for x in data if Path(x).exists()]
                if paths and all(p.suffix.lower() in IMAGE_EXTENSIONS for p in paths):
                    return "image"
                if paths and all(p.suffix.lower() in TABULAR_EXTENSIONS for p in paths):
                    return "tabular"
                if paths and all(p.suffix.lower() in TEXT_EXTENSIONS for p in paths):
                    return "text"

        if isinstance(data, (str, Path)):
            p = Path(data)
            if p.exists() and p.is_file():
                ext = p.suffix.lower()
                if ext in IMAGE_EXTENSIONS:
                    return "image"
                if ext in TABULAR_EXTENSIONS:
                    return "tabular"
                if ext in TEXT_EXTENSIONS:
                    return "text"
            if p.exists() and p.is_dir():
                files = [f for f in p.iterdir() if f.is_file()]
                img_n = sum(f.suffix.lower() in IMAGE_EXTENSIONS for f in files)
                tab_n = sum(f.suffix.lower() in TABULAR_EXTENSIONS for f in files)
                txt_n = sum(f.suffix.lower() in TEXT_EXTENSIONS for f in files)
                if img_n >= max(tab_n, txt_n) and img_n > 0:
                    return "image"
                if tab_n >= max(img_n, txt_n) and tab_n > 0:
                    return "tabular"
                if txt_n > 0:
                    return "text"

        return "tabular"

    @staticmethod
    def _load_tabular(data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data.copy()

        if isinstance(data, (str, Path)):
            path = Path(data)
            if not path.exists() or not path.is_file():
                raise ValueError(f"Tabular path not found: {path}")

            ext = path.suffix.lower()
            if ext == ".csv":
                return pd.read_csv(path)
            if ext in {".parquet", ".pq"}:
                return pd.read_parquet(path)
            if ext in {".xlsx", ".xls"}:
                return pd.read_excel(path)
            if ext == ".json":
                return pd.read_json(path)

        raise ValueError("Unsupported tabular input. Provide DataFrame or csv/json/parquet/xlsx path.")

    def _collect_image_candidates(self, data: Any) -> List[Tuple[str, Any]]:
        candidates: List[Tuple[str, Any]] = []

        if isinstance(data, np.ndarray):
            return [("array_0", data)]

        if isinstance(data, (str, Path)):
            p = Path(data)
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                return [(str(p), p)]
            if p.is_dir():
                for file_path in sorted(p.rglob("*")):
                    if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
                        candidates.append((str(file_path), file_path))
                return candidates

        if isinstance(data, (list, tuple)):
            for idx, item in enumerate(data):
                if isinstance(item, np.ndarray):
                    candidates.append((f"array_{idx}", item))
                else:
                    p = Path(item)
                    if p.exists() and p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                        candidates.append((str(p), p))
            return candidates

        raise ValueError("Unsupported image input. Use array, image file path, directory, or list of paths.")

    def _load_text_items(self, data: Any) -> List[str]:
        texts: List[str] = []

        if isinstance(data, pd.Series):
            return [str(x) for x in data.tolist()]

        if isinstance(data, str) and not Path(data).exists():
            return [data]

        if isinstance(data, (str, Path)):
            p = Path(data)
            if p.is_file():
                return [p.read_text(errors="ignore")]
            if p.is_dir():
                for file_path in sorted(p.rglob("*")):
                    if file_path.is_file() and file_path.suffix.lower() in TEXT_EXTENSIONS:
                        texts.append(file_path.read_text(errors="ignore"))
                return texts

        if isinstance(data, (list, tuple)):
            for item in data:
                if isinstance(item, (str, Path)) and Path(item).exists() and Path(item).is_file():
                    texts.append(Path(item).read_text(errors="ignore"))
                else:
                    texts.append(str(item))
            return texts

        raise ValueError("Unsupported text input. Use text string, file, dir, or list of these.")

    # ------------------------- tabular pipeline -------------------------

    def _evaluate_tabular(
        self,
        data: Any,
        compare_data: Any,
        target_col: Optional[str],
        id_col: Optional[str],
        time_col: Optional[str],
        datetime_cols: Optional[List[str]],
        input_hash: str,
        compare_hash: Optional[str],
        logger: logging.Logger,
    ) -> Dict[str, Any]:
        df = self._load_tabular(data)
        if df.empty:
            raise ValueError("Tabular dataset is empty.")

        if len(df) > int(self.config["max_rows"]):
            logger.warning(
                "Input has %s rows > max_rows=%s. Sampling with seed=%s.",
                len(df),
                self.config["max_rows"],
                self.config["seed"],
            )
            df = df.sample(n=int(self.config["max_rows"]), random_state=int(self.config["seed"]), replace=False)

        # standardize columns
        df.columns = [str(c).strip() for c in df.columns]

        compare_df = None
        if compare_data is not None:
            compare_df = self._load_tabular(compare_data)
            compare_df.columns = [str(c).strip() for c in compare_df.columns]
            shared_cols = sorted(set(df.columns) & set(compare_df.columns))
            if shared_cols:
                compare_df = compare_df[shared_cols]
                df = df[shared_cols]
            else:
                compare_df = None
                logger.warning("compare_data provided but no shared columns; drift tests will SKIP.")

        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]) and self._is_datetime(df[col]):
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass

        num_cols = self._safe_num(df)
        cat_cols = self._safe_cat(df)
        dt_cols: List[str] = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

        if datetime_cols:
            dt_cols = sorted(set(dt_cols) | {c for c in datetime_cols if c in df.columns})

        text_cols: List[str] = []
        for c in df.columns:
            if c in cat_cols or c in dt_cols:
                continue
            if pd.api.types.is_object_dtype(df[c]):
                non_na = df[c].dropna().astype(str)
                if len(non_na) == 0:
                    continue
                avg_len = float(non_na.str.len().mean())
                uniq_ratio = float(non_na.nunique() / max(1, len(non_na)))
                if avg_len > 5 and uniq_ratio > 0.6:
                    text_cols.append(c)

        if id_col and id_col not in df.columns:
            logger.warning("id_col=%s not found; uniqueness tests will degrade.", id_col)
            id_col = None

        if time_col and time_col not in df.columns:
            logger.warning("time_col=%s not found; time-series tests will SKIP.", time_col)
            time_col = None

        if target_col and target_col not in df.columns:
            logger.warning("target_col=%s not found; label-quality tests will SKIP.", target_col)
            target_col = None

        if time_col and time_col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
            if time_col not in dt_cols:
                dt_cols.append(time_col)

        schema = {}
        for col in df.columns:
            series = df[col]
            schema[col] = {
                "dtype": str(series.dtype),
                "inferred": pd.api.types.infer_dtype(series, skipna=True),
                "missing_pct": float(series.isna().mean() * 100.0),
                "cardinality": int(series.nunique(dropna=True)),
            }

        data_path = Path(data) if isinstance(data, (str, Path)) else Path("<in_memory_dataframe>")
        compare_path = Path(compare_data) if isinstance(compare_data, (str, Path)) else None

        context = {
            "df": df,
            "compare_df": compare_df,
            "id_col": id_col,
            "time_col": time_col,
            "target_col": target_col,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "dt_cols": dt_cols,
            "text_cols": text_cols,
            "schema": schema,
            "data_path": data_path,
            "compare_path": compare_path,
            "data_hash": input_hash,
            "compare_hash": compare_hash,
            "run_drift_tests": compare_df is not None,
            "run_ts_tests": bool(time_col),
            "run_outlier_tests": True,
            "run_privacy_tests": True,
            "metadata": {
                "n_rows": int(len(df)),
                "n_cols": int(len(df.columns)),
            },
        }

        self._tester_namespace["CONFIG"] = dict(self.config)
        self._tester_namespace["DEPS"] = dict(self._deps)

        test_results = self._run_208_tests(context, logger)
        status_summary = Counter([result["status"] for result in test_results])

        dimension_scores = self._compute_dimension_scores(test_results)
        overall_score = self._weighted_dimension_score(dimension_scores)
        quality_tier = self._quality_tier(overall_score)

        recommendations, cautions = self._recommend_use_cases("tabular", dimension_scores, overall_score)
        remediation = self._build_tabular_remediation(test_results)

        top_failures = [r for r in test_results if r["status"] == "FAIL"][:25]
        top_warnings = [r for r in test_results if r["status"] == "WARN"][:25]

        return {
            "overall_score": round(overall_score, 2),
            "quality_tier": quality_tier,
            "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
            "best_use_recommendation": recommendations[0] if recommendations else "Manual review required",
            "recommended_use_cases": recommendations,
            "cautions": cautions,
            "fix_actions": remediation,
            "summary": {
                "n_rows": int(len(df)),
                "n_cols": int(len(df.columns)),
                "total_tests": len(test_results),
                "pass": int(status_summary.get("PASS", 0)),
                "warn": int(status_summary.get("WARN", 0)),
                "fail": int(status_summary.get("FAIL", 0)),
                "skip": int(status_summary.get("SKIP", 0)),
            },
            "tabular_context": {
                "id_col": id_col,
                "time_col": time_col,
                "target_col": target_col,
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "dt_cols": dt_cols,
                "text_cols": text_cols,
                "input_hash_sha256": input_hash,
                "compare_hash_sha256": compare_hash,
            },
            "test_results": test_results,
            "failed_tests": top_failures,
            "warning_tests": top_warnings,
        }

    def _run_208_tests(self, context: Dict[str, Any], logger: logging.Logger) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for idx, test_name in enumerate(self._test_names, start=1):
            test_func = self._test_registry.get(test_name)
            if test_func is None:
                tr = self._fallback_test_result(test_name, context)
            else:
                try:
                    output = test_func(context)
                    tr = self._normalize_test_result(test_name, output)
                except Exception as exc:  # pragma: no cover - defensive
                    tr = TestResult(
                        name=test_name,
                        status="FAIL",
                        metric={"error": str(exc)},
                        interpretation=f"Exception during execution: {exc}",
                    )

            dimension = self._test_to_dimension.get(test_name) or self._infer_dimension_for_test_name(test_name)
            status = tr.status if tr.status in self.status_to_score else "WARN"

            payload = {
                "index": idx,
                "test": test_name,
                "status": status,
                "dimension": dimension,
                "interpretation": tr.interpretation or "",
                "metric": self._compact_metric(tr.metric),
            }
            results.append(payload)

            if idx % 25 == 0:
                logger.info("Executed %s / 208 tests", idx)

            if status == "FAIL":
                logger.warning("FAIL [%03d] %s", idx, test_name)
            elif status == "WARN":
                logger.info("WARN [%03d] %s", idx, test_name)

        if len(results) != 208:
            logger.warning("Expected 208 test outputs but got %s", len(results))

        return results

    def _normalize_test_result(self, test_name: str, output: Any) -> TestResult:
        if isinstance(output, TestResult):
            return output

        if hasattr(output, "status") and hasattr(output, "name"):
            return TestResult(
                name=getattr(output, "name", test_name),
                status=getattr(output, "status", "WARN"),
                metric=getattr(output, "metric", None),
                interpretation=getattr(output, "interpretation", ""),
                extra=getattr(output, "extra", None),
            )

        if isinstance(output, dict):
            return TestResult(
                name=test_name,
                status=str(output.get("status", "WARN")),
                metric=output.get("metric", output),
                interpretation=str(output.get("interpretation", "")),
            )

        return TestResult(name=test_name, status="WARN", metric=output, interpretation="Non-standard test output")

    def _fallback_test_result(self, test_name: str, context: Dict[str, Any]) -> TestResult:
        if "fairness coverage" in test_name.lower():
            target = context.get("target_col")
            if not target or target not in context["df"].columns:
                return TestResult(test_name, "SKIP", interpretation="No target column for fairness coverage test")
            vc = context["df"][target].dropna().value_counts(normalize=True)
            if vc.empty:
                return TestResult(test_name, "SKIP", interpretation="No non-null labels")
            parity = float(vc.min() / max(vc.max(), 1e-9))
            status = "PASS" if parity >= 0.5 else "WARN"
            return TestResult(
                test_name,
                status,
                metric={"prevalence_parity": parity, "class_distribution": vc.to_dict()},
                interpretation=f"Label prevalence parity={parity:.3f}",
            )

        return TestResult(test_name, "SKIP", interpretation="No implementation mapped for this test.")

    def _build_test_dimension_map(
        self,
        test_names: List[str],
        categories: Dict[str, List[int]],
    ) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for category, indices in categories.items():
            dimension = CATEGORY_TO_DIMENSION.get(category, "Validity")
            for idx in indices:
                if 1 <= idx <= len(test_names):
                    test_name = test_names[idx - 1]
                    mapping[test_name] = dimension

        for test_name in test_names:
            mapping[test_name] = self._keyword_dimension_override(test_name, mapping.get(test_name, "Validity"))
        return mapping

    def _keyword_dimension_override(self, test_name: str, default_dimension: str) -> str:
        name = test_name.lower()

        if any(k in name for k in ["missing", "null", "completeness"]):
            return "Completeness"

        if any(k in name for k in ["duplicate", "unique", "primary-key", "composite-key"]):
            return "Uniqueness"

        if any(k in name for k in ["timeliness", "stationarity", "autocorrelation", "change-point", "chow", "adf", "kpss", "cointegration", "granger"]):
            return "Timeliness"

        if any(k in name for k in ["drift", "shift", "coverage", "sampling", "representative", "wasserstein", "psi", "mmd", "divergence", "hellinger", "tv distance", "energy distance"]):
            return "Representativeness"

        if any(k in name for k in ["label", "class", "parity", "imbalance", "balance"]):
            return "Balance"

        if any(k in name for k in ["schema", "format", "regex", "datatype", "consistency", "metadata", "governance"]):
            return "Consistency"

        return default_dimension

    def _infer_dimension_for_test_name(self, test_name: str) -> str:
        return self._keyword_dimension_override(test_name, "Validity")

    def _compute_dimension_scores(self, test_results: List[Dict[str, Any]]) -> Dict[str, float]:
        grouped: Dict[str, List[float]] = {dim: [] for dim in DIMENSIONS}

        for row in test_results:
            dim = row["dimension"]
            if dim not in grouped:
                grouped[dim] = []
            grouped[dim].append(self.status_to_score.get(row["status"], 70.0))

        scores: Dict[str, float] = {}
        for dim in DIMENSIONS:
            vals = grouped.get(dim, [])
            scores[dim] = float(np.mean(vals)) if vals else 70.0
        return scores

    def _weighted_dimension_score(self, dimension_scores: Dict[str, float]) -> float:
        numerator = 0.0
        denominator = 0.0
        for dim, score in dimension_scores.items():
            weight = float(self.dimension_weights.get(dim, 1.0))
            numerator += score * weight
            denominator += weight
        if denominator <= 0:
            return self._safe_mean(list(dimension_scores.values()))
        return numerator / denominator

    def _build_tabular_remediation(self, test_results: List[Dict[str, Any]]) -> List[str]:
        actions: List[str] = []

        keyword_action_pairs = [
            (["missing", "null"], "Backfill missing values and enforce required-field checks at ingestion."),
            (["outlier", "hbos", "isolation", "lof", "mahalanobis"], "Review outlier policy: cap, winsorize, or remove extreme records by column."),
            (["duplicate", "unique", "primary-key"], "Deduplicate records and enforce stable unique identifiers in source systems."),
            (["drift", "shift", "psi", "wasserstein", "mmd"], "Address training-serving drift with recent data refresh and segment-aware monitoring."),
            (["timeliness", "stationarity", "change-point", "autocorrelation"], "Improve freshness and temporal ordering; update late-arrival handling windows."),
            (["pii", "privacy", "leakage"], "Mask or tokenize sensitive fields and enforce leakage controls before model use."),
            (["schema", "format", "regex", "encoding"], "Harden schema contracts (types/ranges/formats) and block malformed records."),
            (["label", "class", "balance"], "Mitigate label imbalance with stratified sampling or class weighting."),
        ]

        for row in test_results:
            if row["status"] not in {"FAIL", "WARN"}:
                continue
            lname = row["test"].lower()
            for keywords, action in keyword_action_pairs:
                if any(k in lname for k in keywords):
                    actions.append(action)
                    break

        if not actions:
            actions.append("No critical failures detected; maintain data quality monitoring cadence.")

        unique_actions: List[str] = []
        seen = set()
        for action in actions:
            if action not in seen:
                unique_actions.append(action)
                seen.add(action)
        return unique_actions[:8]

    # ------------------------- image pipeline -------------------------

    @staticmethod
    def _average_hash(image: Image.Image, hash_size: int = 8) -> str:
        gray = image.convert("L").resize((hash_size, hash_size), Image.Resampling.BILINEAR)
        arr = np.asarray(gray, dtype=np.float32)
        bits = arr > arr.mean()
        return "".join("1" if b else "0" for b in bits.flatten())

    @staticmethod
    def _image_sharpness_score(gray: np.ndarray) -> float:
        gy, gx = np.gradient(gray)
        sharpness = float(np.var(np.hypot(gx, gy)))
        return max(0.0, min(100.0, 100.0 * (sharpness / (sharpness + 80.0))))

    def _evaluate_images(
        self,
        data: Any,
        labels: Optional[Dict[str, Any]],
        min_resolution: Tuple[int, int],
    ) -> Dict[str, Any]:
        candidates = self._collect_image_candidates(data)
        if not candidates:
            raise ValueError("No image candidates found.")

        records: List[Dict[str, Any]] = []
        corrupted: List[str] = []

        for name, item in candidates:
            try:
                if isinstance(item, np.ndarray):
                    arr = np.asarray(item)
                    if arr.ndim == 2:
                        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="L").convert("RGB")
                    elif arr.ndim == 3:
                        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGB")
                    else:
                        raise ValueError("Unsupported ndarray shape for image")
                else:
                    with Image.open(item) as im:
                        img = im.convert("RGB")

                rgb = np.asarray(img, dtype=np.uint8)
                gray = np.asarray(img.convert("L"), dtype=np.float32)
                h, w = gray.shape
                brightness = float(gray.mean())
                contrast = float(gray.std())
                blur = self._image_sharpness_score(gray)

                records.append(
                    {
                        "id": name,
                        "width": int(w),
                        "height": int(h),
                        "resolution": int(w * h),
                        "brightness": brightness,
                        "contrast": contrast,
                        "sharpness_score": blur,
                        "aspect_ratio": float(w / max(1, h)),
                        "hash": self._average_hash(img),
                        "channels": int(rgb.shape[2]) if rgb.ndim == 3 else 1,
                    }
                )
            except (UnidentifiedImageError, OSError, ValueError):
                corrupted.append(name)

        total_n = len(candidates)
        valid_n = len(records)
        if valid_n == 0:
            raise ValueError("All image assets were corrupted or unreadable.")

        integrity = 100.0 * (valid_n / total_n)
        completeness = integrity

        resolutions = np.array([r["resolution"] for r in records], dtype=float)
        target_pixels = float(min_resolution[0] * min_resolution[1])
        resolution_score = float(np.mean(np.clip(resolutions / max(1.0, target_pixels), 0.0, 1.0)) * 100.0)

        sharpness_score = self._safe_mean([r["sharpness_score"] for r in records])
        brightness_vals = np.array([r["brightness"] for r in records], dtype=float)
        contrast_vals = np.array([r["contrast"] for r in records], dtype=float)

        exposure_score = float(np.mean(np.clip(1.0 - (np.abs(brightness_vals - 128.0) / 128.0), 0.0, 1.0)) * 100.0)
        contrast_score = float(np.mean(np.clip((contrast_vals - 10.0) / 50.0, 0.0, 1.0)) * 100.0)

        validity = self._safe_mean([resolution_score, sharpness_score, exposure_score, contrast_score])

        hashes = [r["hash"] for r in records]
        unique_ratio = len(set(hashes)) / max(1, len(hashes))
        uniqueness = 100.0 * unique_ratio

        aspect = np.array([r["aspect_ratio"] for r in records], dtype=float)
        if len(aspect) >= 4:
            q1, q3 = np.percentile(aspect, [25, 75])
            iqr = q3 - q1
            if iqr > 0:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outlier_ratio = float(((aspect < lower) | (aspect > upper)).mean())
            else:
                outlier_ratio = 0.0
        else:
            outlier_ratio = 0.0
        consistency = 100.0 * (1.0 - outlier_ratio)

        sample_size_score = min(100.0, math.log10(valid_n + 1) / math.log10(5000 + 1) * 100.0)
        representativeness = self._safe_mean([sample_size_score, uniqueness, consistency])

        balance_score = 70.0
        balance_details: Dict[str, Any] = {}
        if labels:
            label_values = [labels.get(r["id"]) for r in records if labels.get(r["id"]) is not None]
            if label_values:
                vc = pd.Series(label_values).value_counts()
                if len(vc) > 1:
                    ratio = float(vc.min() / vc.max())
                    probs = (vc / vc.sum()).to_numpy(dtype=float)
                    entropy = float(-(probs * np.log2(probs + 1e-12)).sum() / np.log2(len(probs)))
                    balance_score = 100.0 * self._safe_mean([ratio, entropy])
                    balance_details = {
                        "class_counts": vc.to_dict(),
                        "minority_majority_ratio": ratio,
                        "normalized_entropy": entropy,
                    }

        timeliness = 70.0
        if all(isinstance(item, Path) for _, item in candidates):
            now = datetime.now().timestamp()
            ages_days: List[float] = []
            for _, item in candidates:
                try:
                    mtime = Path(item).stat().st_mtime
                    ages_days.append(max(0.0, (now - mtime) / 86400.0))
                except Exception:
                    continue
            if ages_days:
                timeliness = max(0.0, 100.0 * (1.0 - min(1.0, float(np.mean(ages_days)) / 365.0)))

        dimension_scores = {
            "Completeness": self._clamp(completeness),
            "Validity": self._clamp(validity),
            "Consistency": self._clamp(consistency),
            "Uniqueness": self._clamp(uniqueness),
            "Representativeness": self._clamp(representativeness),
            "Balance": self._clamp(balance_score),
            "Timeliness": self._clamp(timeliness),
        }

        overall = self._weighted_dimension_score(dimension_scores)
        recommendations, cautions = self._recommend_use_cases("image", dimension_scores, overall)

        remediation = self._improvement_actions(
            "image",
            self._bottom_dimensions(dimension_scores, n=4),
        )

        pseudo_status = self._dimension_to_status_summary(dimension_scores)

        return {
            "overall_score": round(overall, 2),
            "quality_tier": self._quality_tier(overall),
            "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
            "best_use_recommendation": recommendations[0] if recommendations else "Manual review required",
            "recommended_use_cases": recommendations,
            "cautions": cautions,
            "fix_actions": remediation,
            "summary": {
                "n_images": total_n,
                "n_valid_images": valid_n,
                **pseudo_status,
            },
            "details": {
                "corrupted_images": corrupted,
                "resolution_target": {"width": min_resolution[0], "height": min_resolution[1]},
                "duplicate_ratio": round(1.0 - unique_ratio, 4),
                "balance": balance_details,
                "sample_image_stats": records[:20],
            },
            "test_results": self._synthetic_dimension_tests(dimension_scores),
        }

    # ------------------------- text pipeline -------------------------

    def _detect_language_hint(self, text: str) -> Tuple[str, float]:
        tokens = re.findall(r"[A-Za-z']+", text.lower())
        if not tokens:
            return "unknown", 0.0

        common_en = {
            "the",
            "and",
            "is",
            "are",
            "to",
            "of",
            "for",
            "with",
            "in",
            "on",
            "this",
            "that",
        }
        hits = sum(1 for t in tokens[:400] if t in common_en)
        ratio = hits / max(1, min(400, len(tokens)))
        if ratio >= 0.02:
            return "en", min(1.0, ratio * 15)
        return "unknown", max(0.05, ratio)

    def _evaluate_text(self, data: Any) -> Dict[str, Any]:
        texts = self._load_text_items(data)
        if not texts:
            raise ValueError("No text content found.")

        n_docs = len(texts)
        stripped = [t.strip() for t in texts]
        non_empty = [t for t in stripped if t]

        completeness = 100.0 * (len(non_empty) / max(1, n_docs))

        normalized = [re.sub(r"\s+", " ", t.lower()) for t in non_empty]
        uniqueness = 100.0 * (len(set(normalized)) / max(1, len(normalized)))

        token_counts = [len(re.findall(r"\w+", t)) for t in non_empty]
        token_arr = np.array(token_counts, dtype=float) if token_counts else np.array([0.0])

        short_ratio = float((token_arr < 5).mean()) if token_counts else 1.0
        long_ratio = float((token_arr > 1500).mean()) if token_counts else 1.0
        length_quality = 100.0 * (1.0 - self._safe_mean([short_ratio, long_ratio]))

        symbol_word_ratios: List[float] = []
        alpha_ratios: List[float] = []
        pii_hits = {"email": 0, "phone": 0, "ssn": 0, "credit_card": 0}

        language_votes: Counter[str] = Counter()
        language_conf: List[float] = []

        for text in non_empty:
            words = max(1, len(re.findall(r"\w+", text)))
            symbols = len(re.findall(r"[^\w\s]", text))
            symbol_word_ratios.append(symbols / words)

            total = max(1, len(text))
            alpha_ratios.append(sum(ch.isalpha() for ch in text) / total)

            lang, conf = self._detect_language_hint(text)
            language_votes[lang] += 1
            language_conf.append(conf)

            for label, pattern in PII_REGEX.items():
                try:
                    if re.search(pattern, text):
                        pii_hits[label] += 1
                except re.error:
                    continue

        symbol_ratio = self._safe_mean(symbol_word_ratios)
        language_confidence = 100.0 * self._safe_mean(language_conf)
        dominant_language = language_votes.most_common(1)[0][0] if language_votes else "unknown"

        validity = 100.0 * (1.0 - min(1.0, symbol_ratio / 0.5))
        consistency = 100.0 * self._safe_mean(alpha_ratios)

        all_tokens: List[str] = []
        for text in non_empty:
            all_tokens.extend(re.findall(r"[A-Za-z']+", text.lower()))
        vocab_diversity = len(set(all_tokens)) / max(1, len(all_tokens))

        sample_size_score = min(100.0, math.log10(len(non_empty) + 1) / math.log10(2000 + 1) * 100.0)
        representativeness = self._safe_mean([sample_size_score, min(100.0, vocab_diversity * 400.0), uniqueness])

        balance_score = 70.0
        timeliness = 70.0

        if isinstance(data, (str, Path)) and Path(data).exists():
            p = Path(data)
            files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in TEXT_EXTENSIONS]
            if files:
                now = datetime.now().timestamp()
                ages = [max(0.0, (now - f.stat().st_mtime) / 86400.0) for f in files]
                timeliness = max(0.0, 100.0 * (1.0 - min(1.0, float(np.mean(ages)) / 365.0)))

        dimension_scores = {
            "Completeness": self._clamp(completeness),
            "Validity": self._clamp(validity),
            "Consistency": self._clamp(self._safe_mean([consistency, length_quality, language_confidence])),
            "Uniqueness": self._clamp(uniqueness),
            "Representativeness": self._clamp(representativeness),
            "Balance": self._clamp(balance_score),
            "Timeliness": self._clamp(timeliness),
        }

        overall = self._weighted_dimension_score(dimension_scores)
        recommendations, cautions = self._recommend_use_cases("text", dimension_scores, overall)
        remediation = self._improvement_actions("text", self._bottom_dimensions(dimension_scores, n=4))

        pseudo_status = self._dimension_to_status_summary(dimension_scores)

        return {
            "overall_score": round(overall, 2),
            "quality_tier": self._quality_tier(overall),
            "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
            "best_use_recommendation": recommendations[0] if recommendations else "Manual review required",
            "recommended_use_cases": recommendations,
            "cautions": cautions,
            "fix_actions": remediation,
            "summary": {
                "n_documents": int(n_docs),
                **pseudo_status,
            },
            "details": {
                "token_count_summary": {
                    "min": int(np.min(token_arr)) if token_counts else 0,
                    "median": float(np.median(token_arr)) if token_counts else 0.0,
                    "max": int(np.max(token_arr)) if token_counts else 0,
                },
                "vocab_diversity": round(vocab_diversity, 4),
                "symbol_to_word_ratio": round(symbol_ratio, 4),
                "language_detection": {
                    "dominant_language": dominant_language,
                    "mean_confidence": round(language_confidence, 2),
                    "votes": dict(language_votes),
                },
                "pii_pattern_hits": pii_hits,
            },
            "test_results": self._synthetic_dimension_tests(dimension_scores),
        }

    # ------------------------- recommendations -------------------------

    def _recommend_use_cases(
        self,
        modality: str,
        scores: Dict[str, float],
        overall: float,
    ) -> Tuple[List[str], List[str]]:
        recommendations: List[str] = []
        cautions: List[str] = []

        weakest_dim = min(scores.items(), key=lambda kv: kv[1])
        weakest_name, weakest_score = weakest_dim[0], weakest_dim[1]

        if modality == "tabular":
            if overall >= 85:
                recommendations.append("Excellent for production ML training, feature stores, and KPI dashboards.")
                recommendations.append("Strong candidate for LLM/RAG structured fine-tuning datasets.")
                recommendations.append("Suitable for high-confidence forecasting with monitoring.")
            elif overall >= 70:
                recommendations.append("Good for model development and analytics with targeted cleanup.")
                recommendations.append("Suitable for segmentation, anomaly detection, and BI iterations.")
            elif overall >= 55:
                recommendations.append("Fair for exploratory analysis and preprocessing pipelines.")
                recommendations.append("Use for prototyping before promotion to training data.")
            else:
                recommendations.append("Poor for direct model training; use only for profiling and remediation.")

            if weakest_score < 65:
                cautions.append(
                    f"Weakest dimension is {weakest_name} ({weakest_score:.1f}); avoid high-stakes use cases dependent on it."
                )

            if scores.get("Timeliness", 100) < 55:
                cautions.append("Low timeliness: avoid near-real-time forecasting and rapid-response decision systems.")
            if scores.get("Balance", 100) < 60:
                cautions.append("Low balance: supervised tasks require class reweighting or resampling.")
            if scores.get("Representativeness", 100) < 60:
                cautions.append("Low representativeness: generalization risk is high for production deployments.")

        elif modality == "image":
            if overall >= 85:
                recommendations.append("Excellent for computer vision training and benchmark-grade validation sets.")
                recommendations.append("Strong candidate for high-quality fine-tuning pipelines.")
            elif overall >= 70:
                recommendations.append("Good for transfer learning and prototype vision models.")
                recommendations.append("Usable for visual search with preprocessing.")
            elif overall >= 55:
                recommendations.append("Fair for labeling workflow development and coarse visual tasks.")
            else:
                recommendations.append("Poor for direct training; use for cleaning and recapture planning.")

            if scores.get("Validity", 100) < 60:
                cautions.append("Image quality issues (resolution/blur/exposure) can degrade OCR and detection accuracy.")
            if scores.get("Uniqueness", 100) < 70:
                cautions.append("High duplicate likelihood: deduplicate before train/validation split.")

        elif modality == "text":
            if overall >= 85:
                recommendations.append("Excellent for LLM fine-tuning, RAG ingestion, and semantic search.")
                recommendations.append("Suitable for production NLP training corpora.")
            elif overall >= 70:
                recommendations.append("Good for classification, topic modeling, and summarization workflows.")
            elif overall >= 55:
                recommendations.append("Fair for exploratory NLP and prototype search/QA systems.")
            else:
                recommendations.append("Poor for model training; prioritize curation and normalization first.")

            if scores.get("Validity", 100) < 60:
                cautions.append("High symbol/noise ratio reduces downstream NLP quality.")
            if scores.get("Consistency", 100) < 60:
                cautions.append("Low text consistency; normalize casing, encoding, and formatting.")

        caveat = (
            f"Best fit now, but weaker for scenarios requiring strong {weakest_name.lower()} "
            f"(current {weakest_score:.1f})."
        )
        if recommendations:
            recommendations[0] = f"{recommendations[0]} {caveat}"

        return recommendations, cautions

    def _improvement_actions(self, modality: str, weakest_dimensions: List[Tuple[str, float]]) -> List[str]:
        action_map = {
            "Completeness": "Backfill nulls and enforce mandatory fields at data ingestion boundaries.",
            "Validity": "Apply schema/type/range validation and reject malformed records early.",
            "Consistency": "Normalize formats (dates, booleans, casing) and standardize feature engineering logic.",
            "Uniqueness": "Deduplicate assets/rows and enforce stable primary keys or perceptual hashes.",
            "Representativeness": "Expand data coverage and monitor segment drift to improve generalization.",
            "Balance": "Use class reweighting, stratified sampling, or targeted data collection for minority classes.",
            "Timeliness": "Increase refresh cadence and enforce freshness SLAs for time-sensitive use cases.",
        }

        actions: List[str] = []
        for dim, _ in weakest_dimensions:
            if dim in action_map:
                actions.append(action_map[dim])

        if modality == "image":
            actions.append("Increase image sharpness and resolution quality gates during data capture.")
        if modality == "text":
            actions.append("Reduce symbol noise and normalize document formatting before tokenization.")

        unique_actions: List[str] = []
        seen = set()
        for action in actions:
            if action not in seen:
                unique_actions.append(action)
                seen.add(action)
        return unique_actions[:8]

    @staticmethod
    def _bottom_dimensions(scores: Dict[str, float], n: int = 3) -> List[Tuple[str, float]]:
        return sorted(scores.items(), key=lambda kv: kv[1])[:n]

    @staticmethod
    def _dimension_to_status_summary(scores: Dict[str, float]) -> Dict[str, int]:
        status = {"pass": 0, "warn": 0, "fail": 0, "skip": 0, "total_tests": len(scores)}
        for score in scores.values():
            if score >= 85:
                status["pass"] += 1
            elif score >= 60:
                status["warn"] += 1
            else:
                status["fail"] += 1
        return status

    def _synthetic_dimension_tests(self, scores: Dict[str, float]) -> List[Dict[str, Any]]:
        tests = []
        for idx, dim in enumerate(DIMENSIONS, start=1):
            score = float(scores.get(dim, 70.0))
            if score >= 85:
                status = "PASS"
            elif score >= 60:
                status = "WARN"
            else:
                status = "FAIL"
            tests.append(
                {
                    "index": idx,
                    "test": f"Dimension aggregate: {dim}",
                    "status": status,
                    "dimension": dim,
                    "interpretation": f"Aggregated {dim} score",
                    "metric": {"score": round(score, 2)},
                }
            )
        return tests

    # ------------------------- visualization + html -------------------------

    def _generate_dashboard_assets(
        self,
        report: Dict[str, Any],
        run_dir: Path,
    ) -> Tuple[Dict[str, Path], Dict[str, str]]:
        chart_dir = run_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)

        chart_paths: Dict[str, Path] = {}
        encoded: Dict[str, str] = {}

        overall = float(report.get("overall_score", 0.0))
        dims = report.get("dimension_scores", {})

        # Gauge
        fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={"projection": "polar"})
        theta = np.linspace(0, np.pi, 200)
        colors = ["#d73027", "#fc8d59", "#fee08b", "#91cf60", "#1a9850"]
        bounds = [0, 50, 70, 85, 95, 100]
        for i, color in enumerate(colors):
            start = np.pi * (1 - bounds[i + 1] / 100)
            end = np.pi * (1 - bounds[i] / 100)
            zone = np.linspace(start, end, 30)
            ax.fill_between(zone, 0.8, 1.0, color=color, alpha=0.35)
        needle = np.pi * (1 - overall / 100)
        ax.plot([needle, needle], [0, 0.92], color="black", linewidth=3)
        ax.scatter([needle], [0.92], color="black", s=60)
        ax.set_ylim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["polar"].set_visible(False)
        ax.text(np.pi / 2, 0.28, f"{overall:.1f}", ha="center", va="center", fontsize=40, fontweight="bold")
        ax.text(np.pi / 2, 0.08, "Overall Score", ha="center", va="center", fontsize=12, color="#4b5563")
        ax.set_title("Shanova Unified Quality Gauge", fontsize=14, pad=20)

        gauge_path = chart_dir / "01_gauge.png"
        fig.tight_layout()
        fig.savefig(gauge_path, dpi=180, bbox_inches="tight")
        encoded["gauge"] = self._encode_image(gauge_path)
        chart_paths["gauge"] = gauge_path
        plt.close(fig)

        # Dimension heatmap
        dim_labels = list(dims.keys())
        dim_values = [float(v) for v in dims.values()]
        fig, ax = plt.subplots(figsize=(max(8, len(dim_labels) * 1.2), 2.8))
        sns.heatmap(
            np.array([dim_values]),
            annot=True,
            fmt=".1f",
            cmap="RdYlGn",
            vmin=0,
            vmax=100,
            xticklabels=dim_labels,
            yticklabels=["Score"],
            cbar_kws={"label": "0-100"},
            ax=ax,
        )
        ax.set_title("Dimension Heatmap")
        fig.tight_layout()
        heatmap_path = chart_dir / "02_dimension_heatmap.png"
        fig.savefig(heatmap_path, dpi=180, bbox_inches="tight")
        encoded["dimension_heatmap"] = self._encode_image(heatmap_path)
        chart_paths["dimension_heatmap"] = heatmap_path
        plt.close(fig)

        # Status pie
        summary = report.get("summary", {})
        pass_n = int(summary.get("pass", 0))
        warn_n = int(summary.get("warn", 0))
        fail_n = int(summary.get("fail", 0))
        skip_n = int(summary.get("skip", 0))
        total = pass_n + warn_n + fail_n + skip_n

        if total > 0:
            fig, ax = plt.subplots(figsize=(6.5, 6.5))
            sizes = [pass_n, warn_n, fail_n, skip_n]
            labels = [f"PASS ({pass_n})", f"WARN ({warn_n})", f"FAIL ({fail_n})", f"SKIP ({skip_n})"]
            colors = ["#22c55e", "#f59e0b", "#ef4444", "#94a3b8"]
            ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=100)
            ax.set_title("Test Status Distribution")
            fig.tight_layout()
            pie_path = chart_dir / "03_status_pie.png"
            fig.savefig(pie_path, dpi=180, bbox_inches="tight")
            encoded["status_pie"] = self._encode_image(pie_path)
            chart_paths["status_pie"] = pie_path
            plt.close(fig)

        return chart_paths, encoded

    @staticmethod
    def _encode_image(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("ascii")

    def _build_html_report(self, report: Dict[str, Any], charts: Dict[str, str]) -> str:
        dim_rows = "\n".join(
            f"<tr><td>{dim}</td><td>{score:.2f}</td></tr>"
            for dim, score in report.get("dimension_scores", {}).items()
        )

        fail_rows = ""
        for row in report.get("failed_tests", [])[:15]:
            fail_rows += (
                f"<tr><td>{row.get('index')}</td><td>{row.get('test')}</td><td>{row.get('dimension')}</td>"
                f"<td>{row.get('interpretation','')}</td></tr>"
            )

        warn_rows = ""
        for row in report.get("warning_tests", [])[:15]:
            warn_rows += (
                f"<tr><td>{row.get('index')}</td><td>{row.get('test')}</td><td>{row.get('dimension')}</td>"
                f"<td>{row.get('interpretation','')}</td></tr>"
            )

        recommendations = "".join(f"<li>{item}</li>" for item in report.get("recommended_use_cases", []))
        cautions = "".join(f"<li>{item}</li>" for item in report.get("cautions", []))
        actions = "".join(f"<li>{item}</li>" for item in report.get("fix_actions", []))

        summary = report.get("summary", {})

        status_cards = ""
        if summary:
            status_cards = f"""
            <div class="card-grid">
              <div class="card"><h3>{summary.get('pass', 0)}</h3><p>PASS</p></div>
              <div class="card"><h3>{summary.get('warn', 0)}</h3><p>WARN</p></div>
              <div class="card"><h3>{summary.get('fail', 0)}</h3><p>FAIL</p></div>
              <div class="card"><h3>{summary.get('skip', 0)}</h3><p>SKIP</p></div>
            </div>
            """

        gauge_html = (
            f'<img alt="Gauge" src="data:image/png;base64,{charts["gauge"]}" />' if "gauge" in charts else ""
        )
        heatmap_html = (
            f'<img alt="Dimension heatmap" src="data:image/png;base64,{charts["dimension_heatmap"]}" />'
            if "dimension_heatmap" in charts
            else ""
        )
        pie_html = (
            f'<img alt="Status pie" src="data:image/png;base64,{charts["status_pie"]}" />'
            if "status_pie" in charts
            else ""
        )

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Shanova Unified Assessment Report</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 28px; background: #f4f7fb; color: #1f2937; }}
    .container {{ max-width: 1300px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 28px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08); }}
    h1 {{ margin-top: 0; border-bottom: 2px solid #dbeafe; padding-bottom: 10px; }}
    h2 {{ margin-top: 30px; color: #111827; }}
    .kpi {{ display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 10px; margin: 18px 0 22px 0; }}
    .kpi div {{ background: linear-gradient(135deg, #e0f2fe 0%, #f8fafc 100%); border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; }}
    .kpi h3 {{ margin: 0; font-size: 28px; }}
    .kpi p {{ margin: 6px 0 0 0; font-size: 13px; color: #374151; }}
    .charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin: 10px 0 20px 0; }}
    .charts img {{ width: 100%; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; text-align: left; padding: 8px; font-size: 14px; }}
    th {{ background: #eff6ff; }}
    ul {{ margin-top: 8px; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 8px; margin: 10px 0 16px 0; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; text-align: center; background: #f8fafc; }}
    .card h3 {{ margin: 0; font-size: 24px; }}
    .muted {{ color: #6b7280; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Shanova Unified Data Quality Report</h1>
    <p class="muted"><strong>Generated:</strong> {report.get('generated_at_utc','')} | <strong>Run ID:</strong> {report.get('run_id','')} | <strong>Modality:</strong> {report.get('modality','')}</p>

    <div class="kpi">
      <div><h3>{report.get('overall_score', 0):.2f}</h3><p>Overall Score</p></div>
      <div><h3>{report.get('quality_tier','')}</h3><p>Quality Tier</p></div>
      <div><h3>{summary.get('total_tests', summary.get('n_images', summary.get('n_documents', 0)))}</h3><p>Tests / Items</p></div>
      <div><h3>{report.get('modality','').upper()}</h3><p>Modality</p></div>
    </div>

    <h2>Executive Summary</h2>
    <p><strong>Best Use Recommendation:</strong> {report.get('best_use_recommendation','')}</p>
    {status_cards}

    <div class="charts">
      {gauge_html}
      {heatmap_html}
      {pie_html}
    </div>

    <h2>Dimension Scores</h2>
    <table>
      <tr><th>Dimension</th><th>Score</th></tr>
      {dim_rows}
    </table>

    <h2>Strategic Recommendations</h2>
    <h3>Recommended Uses</h3>
    <ul>{recommendations}</ul>

    <h3>Cautions</h3>
    <ul>{cautions}</ul>

    <h3>Priority Fix Actions</h3>
    <ul>{actions}</ul>

    <h2>Failure Highlights</h2>
    <table>
      <tr><th>#</th><th>Test</th><th>Dimension</th><th>Interpretation</th></tr>
      {fail_rows or '<tr><td colspan="4">No failed tests recorded.</td></tr>'}
    </table>

    <h2>Warning Highlights</h2>
    <table>
      <tr><th>#</th><th>Test</th><th>Dimension</th><th>Interpretation</th></tr>
      {warn_rows or '<tr><td colspan="4">No warning tests recorded.</td></tr>'}
    </table>
  </div>
</body>
</html>
"""
        return html

    # ------------------------- reporting utils -------------------------

    def _compact_metric(self, value: Any, depth: int = 0, max_items: int = 12) -> Any:
        if depth > 3:
            return "..."

        if isinstance(value, dict):
            out = {}
            for idx, (k, v) in enumerate(value.items()):
                if idx >= max_items:
                    out["..."] = f"truncated ({len(value)} keys)"
                    break
                out[str(k)] = self._compact_metric(v, depth=depth + 1, max_items=max_items)
            return out

        if isinstance(value, (list, tuple, set)):
            seq = list(value)
            compact = [self._compact_metric(v, depth=depth + 1, max_items=max_items) for v in seq[:max_items]]
            if len(seq) > max_items:
                compact.append(f"... truncated ({len(seq)} items)")
            return compact

        if isinstance(value, np.ndarray):
            flat = value.flatten()
            head = flat[:max_items].tolist()
            if flat.size > max_items:
                head.append(f"... truncated ({flat.size} values)")
            return head

        if isinstance(value, (np.integer, np.floating)):
            return value.item()

        if isinstance(value, (pd.Timestamp, datetime)):
            return value.isoformat()

        return value
