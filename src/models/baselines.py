"""
Baseline models for SENTINEL-GNSS comparison.

Baseline strategy
-----------------
A rigorous ML paper requires three tiers of baselines:

  Tier 1 — Trivial (set the floor):
    MajorityClass   Always predicts the most common class (CLEAN).
                    Sets a lower bound; any model must beat this.

  Tier 2 — Domain-rule (expert heuristic):
    CNR_Threshold   Uses C/N₀ thresholds from GNSS literature
                    (< 30 dB-Hz → DEGRADED, 30–37 → WARNING, > 37 → CLEAN).
                    Represents what a domain expert would hard-code.
                    Justification: Standard GNSS quality masks use exactly
                    this criterion (IS-GPS-200, RTCM SC-104).

  Tier 3 — Classical ML (strong baselines):
    RandomForest    Ensemble of decision trees on flattened windows.
                    Gold standard for tabular time-series (Fernández-Delgado
                    et al., 2014; Breiman 2001).
    XGBoost         Gradient boosting; typically best among classical methods
                    on structured data (Chen & Guestrin, 2016).

  Tier 4 — Ablations (justify the architecture):
    Run via train.py --model_type lstm_only / transformer_only.
    Results are loaded from their checkpoint dirs and printed in the table.

All baselines use the SAME train/val/test windows as SENTINEL-GNSS.
The 30-step (T×F) window is flattened to a 1-D feature vector for Tier 3.

References
----------
Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32.
Chen, T. & Guestrin, C. (2016). XGBoost. KDD.
Fernández-Delgado, M. et al. (2014). Do we need hundreds of classifiers?
  JMLR 15(1), 3133–3181.
RTCM SC-104 (2021). Signal quality indicator thresholds, RTCM 10403.3.

Run:
    python -m src.models.baselines
    python -m src.models.baselines --include_ablations   # also reads DL ckpts
"""
import argparse
import json
import logging
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score, accuracy_score, matthews_corrcoef, cohen_kappa_score,
    classification_report,
)

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)-5s  %(message)s")

ROOT = Path(__file__).resolve().parents[2]
WINDOW_DIR = ROOT / "data" / "processed" / "windows"
RESULTS_DIR = ROOT / "results" / "baselines"
CKPT_ROOT = ROOT / "results" / "models"
HORIZONS = ["5s", "15s", "30s"]
CLASS_LABELS = ["CLEAN", "WARNING", "DEGRADED"]

# Feature names in the order they appear in the saved windows (alphabetically
# sorted by feature_prep._get_feature_cols).  Used to derive MEAN_CNR_IDX.
_FEATURE_NAMES_SORTED = [
    "alt", "baseline_sats", "clock_bias", "cnr_trend", "cnr_variance",
    "cycle_slips", "dop_ratio", "elevation_violations", "fix_continuity",
    "fix_transitions", "gdop", "hdop", "iono_delay", "lat_std", "lon_std",
    "max_cnr", "mean_cnr", "min_cnr", "multipath", "num_satellites",
    "pdop", "position_variance", "residual_mean", "residual_std",
    "sat_drop_rate", "sat_mean", "sat_min", "sat_visibility",
    "solution_age", "solution_status", "std_cnr", "tropo_delay",
    "vdop", "cnr_available",
]
MEAN_CNR_IDX = _FEATURE_NAMES_SORTED.index("mean_cnr")  # 16

# C/N₀ thresholds (dB-Hz) from GNSS signal quality literature
CNR_DEGRADED_THRESHOLD = 30.0   # < 30  → DEGRADED
CNR_WARNING_THRESHOLD = 37.0   # 30–37 → WARNING, > 37 → CLEAN


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_split(windows_dir: Path, split: str) -> dict:
    path = windows_dir / f"{split}.npz"
    if not path.exists():
        raise FileNotFoundError(
            f"Windows not found at {path}. Run feature_prep first.")
    d = np.load(path)
    return {
        # (N, T, F) — for threshold rule
        "X_raw": d["X"],
        # (N, T*F)  — for classical ML
        "X":     d["X"].reshape(len(d["X"]), -1),
        "y_5s":  d["y_5s"],
        "y_15s": d["y_15s"],
        "y_30s": d["y_30s"],
    }


# ─── Metric helper ────────────────────────────────────────────────────────────

def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "accuracy":    float(accuracy_score(y_true, y_pred)),
        "macro_f1":    float(f1_score(y_true, y_pred, average="macro",    zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "kappa":       float(cohen_kappa_score(y_true, y_pred)),
        "mcc":         float(matthews_corrcoef(y_true, y_pred)),
    }


def per_class_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    report = classification_report(
        y_true, y_pred, target_names=CLASS_LABELS,
        output_dict=True, zero_division=0,
    )
    return {
        cls: {
            "precision": report[cls]["precision"],
            "recall":    report[cls]["recall"],
            "f1":        report[cls]["f1-score"],
            "support":   int(report[cls]["support"]),
        }
        for cls in CLASS_LABELS
    }


# ─── Tier 1: Majority-class classifier ───────────────────────────────────────

def run_majority_class(train: dict, test: dict) -> dict:
    """Always predicts the most frequent training class (CLEAN).

    Sets the absolute floor.  Macro-F1 = 0.22 for a 3-class problem where
    one class dominates (CLEAN ≈ 67 %).  Any model that cannot beat this
    is useless.
    """
    results = {}
    for h in HORIZONS:
        clf = DummyClassifier(strategy="most_frequent", random_state=42)
        clf.fit(train["X"], train[f"y_{h}"])
        y_pred = clf.predict(test["X"])
        results[h] = {
            "overall":   score(test[f"y_{h}"], y_pred),
            "per_class": per_class_metrics(test[f"y_{h}"], y_pred),
        }
    return results


# ─── Tier 2: C/N₀ threshold rule ─────────────────────────────────────────────

def run_cnr_threshold(test: dict) -> dict:
    """Rule-based classifier using mean C/N₀ averaged over the 30-step window.

    Thresholds(dB-Hz):
      mean_cnr < 30.0          → DEGRADED(class 2)
      30.0 ≤ mean_cnr < 37.0   → WARNING(class 1)
      mean_cnr ≥ 37.0          → CLEAN(class 0)

    Justification: These thresholds are the standard GNSS signal quality masks
    used in IS-GPS-200 and RTCM SC-104.  They represent the best a domain
    expert without ML can do.  If SENTINEL-GNSS cannot beat this on all three
    horizons, the ML approach is not justified.
    """
    X_raw = test["X_raw"]                   # (N, T, F)
    # Mean C/N₀ over the 30-step window for each sample
    mean_cnr = X_raw[:, :, MEAN_CNR_IDX].mean(axis=1)  # (N,)

    y_pred = np.where(
        mean_cnr < CNR_DEGRADED_THRESHOLD, 2,
        np.where(mean_cnr < CNR_WARNING_THRESHOLD, 1, 0)
    ).astype(int)

    # Threshold rule makes the same prediction for all horizons
    results = {}
    for h in HORIZONS:
        results[h] = {
            "overall":   score(test[f"y_{h}"], y_pred),
            "per_class": per_class_metrics(test[f"y_{h}"], y_pred),
        }
    return results


# ─── Tier 3: Random Forest ────────────────────────────────────────────────────

def run_random_forest(train: dict, test: dict) -> dict:
    """Random Forest on flattened(T×F) windows.

    Hyper-parameters follow the recommendations of Probst & Boulesteix(2017):
    500 trees, balanced class weights, unlimited depth.
    """
    results = {}
    for h in HORIZONS:
        clf = RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_leaf=5,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        )
        clf.fit(train["X"], train[f"y_{h}"])
        y_pred = clf.predict(test["X"])
        results[h] = {
            "overall":   score(test[f"y_{h}"], y_pred),
            "per_class": per_class_metrics(test[f"y_{h}"], y_pred),
        }
        log.info(
            f"  RandomForest  +{h}  "
            f"MacroF1={results[h]['overall']['macro_f1']:.4f}  "
            f"MCC={results[h]['overall']['mcc']:.4f}"
        )
    return results


# ─── Tier 3: XGBoost ──────────────────────────────────────────────────────────

def run_xgboost(train: dict, test: dict) -> dict:
    """XGBoost gradient boosting on flattened(T×F) windows."""
    if not HAS_XGB:
        log.warning("xgboost not installed — skipping. pip install xgboost")
        return {}
    results = {}
    for h in HORIZONS:
        y_tr = train[f"y_{h}"]
        # Compute scale_pos_weight-like balance per class
        classes, counts = np.unique(y_tr, return_counts=True)
        n_total = len(y_tr)
        sample_weight = np.array(
            [n_total / (len(classes) * counts[np.where(classes == c)[0][0]])
             for c in y_tr]
        )
        clf = XGBClassifier(
            n_estimators=400,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
        clf.fit(train["X"], y_tr, sample_weight=sample_weight)
        y_pred = clf.predict(test["X"])
        results[h] = {
            "overall":   score(test[f"y_{h}"], y_pred),
            "per_class": per_class_metrics(test[f"y_{h}"], y_pred),
        }
        log.info(
            f"  XGBoost       +{h}  "
            f"MacroF1={results[h]['overall']['macro_f1']:.4f}  "
            f"MCC={results[h]['overall']['mcc']:.4f}"
        )
    return results


# ─── Tier 4: load DL ablation results from checkpoints ───────────────────────

def load_ablation_results(model_type: str) -> dict | None:
    """Read test metrics already saved by evaluate.py for an ablation run."""
    metrics_path = ROOT / "results" / "figures" / \
        f"metrics_test_{model_type}.json"
    if not metrics_path.exists():
        # Also try default path (may not be labelled by model type yet)
        metrics_path = ROOT / "results" / "figures" / "metrics_test.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            return json.load(f)
    return None


# ─── Summary table ────────────────────────────────────────────────────────────

def print_comparison_table(all_results: dict) -> None:
    """Print IEEE-style comparison table."""
    log.info("\n")
    log.info("=" * 78)
    log.info("  Comparison Table — Test Set Macro-F1  (higher is better)")
    log.info("=" * 78)
    log.info(
        f"  {'Method':<26}  {'Justification':<24}  {'  +5s':>7}  {'  +15s':>7}  {'  +30s':>7}")
    log.info("-" * 78)

    descriptions = {
        "MajorityClass":      "Trivial floor",
        "CNR_Threshold":      "Domain rule (RTCM)",
        "RandomForest":       "Classical ML baseline",
        "XGBoost":            "Classical ML baseline",
        "LSTM_only":          "Ablation: no Transformer",
        "Transformer_only":   "Ablation: no LSTM",
        "SENTINEL-GNSS":      "Proposed model",
    }

    for model_name, res in all_results.items():
        if not res:
            continue
        desc = descriptions.get(model_name, "")
        f1s = []
        for h in HORIZONS:
            if h in res:
                f1s.append(f"{res[h]['overall']['macro_f1']:.4f}")
            else:
                f1s.append("  n/a ")
        marker = " ◄" if model_name == "SENTINEL-GNSS" else ""
        log.info(
            f"  {model_name:<26}  {desc:<24}  "
            f"{f1s[0]:>7}  {f1s[1]:>7}  {f1s[2]:>7}{marker}"
        )
    log.info("=" * 78)
    log.info("  Macro-F1: equally weights CLEAN / WARNING / DEGRADED classes.")
    log.info("  Random 3-class predictor would score ≈ 0.3333.")
    log.info("=" * 78)


# ─── Entry point ──────────────────────────────────────────────────────────────

def run_all(windows_dir: Path = WINDOW_DIR,
            include_ablations: bool = False) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Loading windows …")
    train_d = load_split(windows_dir, "train")
    test_d = load_split(windows_dir, "test")
    log.info(f"  Train: {train_d['X'].shape}   Test: {test_d['X'].shape}")

    all_results: dict = {}

    log.info("\n── Tier 1: Majority-class ──────────────────────────────────")
    all_results["MajorityClass"] = run_majority_class(train_d, test_d)

    log.info("\n── Tier 2: C/N₀ threshold rule ────────────────────────────")
    all_results["CNR_Threshold"] = run_cnr_threshold(test_d)

    log.info("\n── Tier 3: Random Forest ───────────────────────────────────")
    all_results["RandomForest"] = run_random_forest(train_d, test_d)

    log.info("\n── Tier 3: XGBoost ─────────────────────────────────────────")
    all_results["XGBoost"] = run_xgboost(train_d, test_d)

    if include_ablations:
        log.info("\n── Tier 4: DL ablations (from checkpoint metrics) ──────────")
        for mt in ("lstm_only", "transformer_only"):
            res = load_ablation_results(mt)
            key = mt.replace("_", " ").title().replace(" ", "_")
            all_results[key] = res or {}
            if res:
                log.info(f"  Loaded {mt} metrics from saved JSON.")
            else:
                log.warning(
                    f"  {mt} metrics not found. "
                    f"Run: python -m src.models.train --model_type {mt} --batch_size 256 "
                    f"then: python -m src.models.evaluate --model_type {mt}")

    print_comparison_table(all_results)

    out = RESULTS_DIR / "baseline_comparison.json"
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2)
    log.info(f"\nFull metrics saved → {out}")
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run all SENTINEL-GNSS baselines")
    parser.add_argument("--windows_dir",        default=str(WINDOW_DIR))
    parser.add_argument("--include_ablations",  action="store_true",
                        help="Also load DL ablation results from their checkpoint dirs")
    args = parser.parse_args()
    run_all(windows_dir=Path(args.windows_dir),
            include_ablations=args.include_ablations)
