"""
feature_prep.py — Feature engineering, imputation, windowing, and SMOTE
                  for the SENTINEL-GNSS Transformer-LSTM model.

Pipeline
--------
  1. Load  data/labelled/sentinel_gnss_labelled.csv  (66,128 rows × 41 cols)
  2. Drop  lat / lon                (geographic overfitting; see NOTE below)
  3. Impute NaNs                   (see NaN handling table in NEXT_STEPS.md)
  4. Add   cnr_available flag       (lets model know when C/N0 is absent)
  5. Min-max scale [0, 1]          (fit on TRAINING set ONLY)
  6. Build sliding-window tensors  (T=30 steps; no overlap across sessions)
  7. SMOTE on TRAINING windows     (minority class oversampling)
  8. Save  data/processed/windows/ + data/processed/scaler.pkl

Model input
-----------
  X      : (N, 30, 34)  — 30 time-steps × 34 features (33 signal + cnr_available)
  y_5s   : (N,)          — label 5 s after window end
  y_15s  : (N,)          — label 15 s after window end
  y_30s  : (N,)          — label 30 s after window end

NOTE: lat/lon are excluded because including raw geographic coordinates
introduces positional bias — the model would learn "Beijing ≈ CLEAN" instead
of the underlying signal physics.  Altitude is kept because it proxies
tropospheric delay (Saastamoinen, 1972).

References
----------
Chawla, N. V., Bowyer, K. W., Hall, L. O., & Kegelmeyer, W. P. (2002).
    SMOTE: Synthetic Minority Over-sampling TEchnique. JAIR, 16, 321–357.
    https://doi.org/10.1613/jair.953

Saastamoinen, J. (1972). Atmospheric correction for the troposphere and
    stratosphere in radio ranging satellites. Geophysical Monograph Series, 15,
    247–251. https://doi.org/10.1029/GM015p0247

Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. JMLR.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import MinMaxScaler

log = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "labelled" / "sentinel_gnss_labelled.csv"
OUT_DIR = ROOT / "data" / "processed" / "windows"
SCALER_PATH = ROOT / "data" / "processed" / "scaler.pkl"

# ─── Window / horizon parameters ─────────────────────────────────────────────
WINDOW_SIZE = 30   # seconds (1 Hz → 30 time steps)
HORIZONS = {"5s": 5, "15s": 15, "30s": 30}   # look-ahead after window end

# ─── Feature columns (33 signal features + 1 added flag = 34 total) ──────────
METADATA_COLS = ["timestamp", "source", "scenario",
                 "lat", "lon",          # excluded: geographic overfitting
                 "label", "label_name", "split"]

# Features where NaN is meaningful (NCLT/Oxford have no C/N0 hardware)
CNR_FEATURES = ["mean_cnr", "min_cnr", "max_cnr", "std_cnr", "cnr_trend"]

# Features to impute with session median (high NaN because RINEX-only sources)
MEDIAN_IMPUTE = ["alt"]

# Features to impute as hdop × scale factor (no GST/GSA for many sources)
DOP_PROXY_MAP = {
    "lat_std": ("hdop", 2.5),    # horizontal error proxy
    "lon_std": ("hdop", 2.5),
}

# Features to estimate from satellite count when DOP unavailable
SAT_DOP_APPROX = ["pdop", "hdop", "vdop", "gdop", "dop_ratio"]

# Clipping bounds [low, high] applied BEFORE scaling to remove extreme outliers
# Values are physical upper limits (not data-driven) based on GNSS signal ranges.
CLIP_BOUNDS: dict[str, tuple[float, float]] = {
    "mean_cnr":          (0,  60),
    "min_cnr":           (0,  60),
    "max_cnr":           (0,  60),
    "std_cnr":           (0,  30),
    "cnr_trend":         (-10, 10),
    "num_satellites":    (0,  50),
    "sat_mean":          (0,  50),
    "sat_min":           (0,  50),
    "sat_visibility":    (0,  1),
    "sat_drop_rate":     (-5,  5),
    "pdop":              (0,  30),
    "hdop":              (0,  30),
    "vdop":              (0,  30),
    "gdop":              (0,  50),
    "dop_ratio":         (0,  10),
    "solution_status":   (0,  1),
    "baseline_sats":     (0,  50),
    "solution_age":      (0,  60),
    "fix_continuity":    (0,  1),
    "fix_transitions":   (0,  30),
    "position_variance": (0,  1e6),
    "cnr_variance":      (0,  900),
    "elevation_violations": (0, 1),
    "multipath":         (0,  1e6),
    "clock_bias":        (0,  60),
    "iono_delay":        (0,  1),
    "tropo_delay":       (0,  50),
    "cycle_slips":       (0,  50),
    "residual_mean":     (0,  1e4),
    "residual_std":      (0,  1e4),
    "alt":               (-100, 9000),
    "lat_std":           (0,  200),
    "lon_std":           (0,  200),
}

# SMOTE target ratios (applied to training set only)
# Goal: CLEAN stays majority; WARNING × 2; DEGRADED × 3 (approx.)
SMOTE_STRATEGY = "auto"   # oversample all minority classes to match majority


# ─────────────────────────────────────────────────────────────────────────────
def load_and_validate(path: Path = DATA_FILE) -> pd.DataFrame:
    """Load the labelled dataset and run basic sanity checks."""
    log.info(f"Loading {path} …")
    df = pd.read_csv(path, low_memory=False)
    assert "label" in df.columns,   "Missing 'label' column"
    assert "split" in df.columns,   "Missing 'split' column — run process_all_datasets.py first"
    assert "source" in df.columns,  "Missing 'source' column"
    # Normalise split names: 'validation' → 'val' (process_all_datasets.py may
    # write either form; downstream code always expects 'val').
    df["split"] = df["split"].replace("validation", "val")
    log.info(f"  {len(df):,} rows × {len(df.columns)} columns")
    log.info(f"  label dist: {df['label'].value_counts().to_dict()}")
    log.info(f"  split dist: {df['split'].value_counts().to_dict()}")
    return df


def _get_feature_cols(df: pd.DataFrame) -> list[str]:
    """Return the ordered list of feature columns (after adding cnr_available)."""
    all_cols = set(df.columns)
    meta_cols = set(METADATA_COLS) | {"cnr_available"}
    feat_cols = sorted(all_cols - meta_cols)
    # Ensure cnr_available is at the END (convention)
    feat_cols.append("cnr_available")
    return feat_cols


def impute(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all imputation rules in-place and add cnr_available flag.

    Imputation strategy
    -------------------
    1. C/N0 features (5 cols)  → zero-fill  +  cnr_available = 0 flag
       Rationale: the model receives an explicit binary indicator telling it
       "no C/N0 hardware present" so it can weight the signal features
       appropriately.  Ref: Sechidis et al. (2017) on missing-data indicators.

    2. alt (54% NaN)           → session median imputation
       Rationale: altitude changes slowly within a session; median is robust
       to outliers and avoids temporal leakage from global mean.

    3. lat_std / lon_std (85%) → hdop × 2.5
       Rationale: for a single-frequency receiver the 1-sigma horizontal
       accuracy ≈ 2.5 × HDOP in moderate conditions (IS-GPS-200N, 2022, §3.3).

    4. DOP cols (~45% NaN)     → estimated from satellite count
       Rationale: PDOP ≈ 30 / sqrt(N) is a rough but physically valid
       approximation when GSA sentences are absent
       (Langley, R.B., 1999. GPS World, 10(5), 56-61).

    5. Remaining < 5% NaN      → forward-fill within session, then zero-fill.
    """
    df = df.copy()

    # ── 1. C/N0 flag ────────────────────────────────────────────────────────
    df["cnr_available"] = (~df[CNR_FEATURES[0]].isna()).astype(np.float32)
    for col in CNR_FEATURES:
        df[col] = df[col].fillna(0.0)

    # ── 2. Altitude — session-median imputation ───────────────────────────
    for col in MEDIAN_IMPUTE:
        if col not in df.columns:
            continue
        session_median = df.groupby("source")[col].transform(
            lambda s: s.fillna(s.median())
        )
        df[col] = df[col].fillna(session_median).fillna(0.0)

    # ── 3. lat_std / lon_std — DOP proxy ────────────────────────────────
    for col, (ref_col, factor) in DOP_PROXY_MAP.items():
        if col not in df.columns or ref_col not in df.columns:
            continue
        proxy = df[ref_col] * factor
        df[col] = df[col].fillna(proxy).fillna(proxy.median())

    # ── 4. DOP columns — satellite-count approximation ───────────────────
    if "num_satellites" in df.columns:
        n_sats = df["num_satellites"].replace(0, np.nan)
        pdop_est = (30.0 / np.sqrt(n_sats)).clip(1.0, 30.0)
        hdop_est = (20.0 / np.sqrt(n_sats)).clip(0.5, 20.0)
        vdop_est = (25.0 / np.sqrt(n_sats)).clip(0.5, 25.0)
        gdop_est = (35.0 / np.sqrt(n_sats)).clip(1.0, 50.0)
        dop_ratio_est = (hdop_est / vdop_est.replace(0, np.nan)).fillna(1.0)

        for col, est in zip(
            SAT_DOP_APPROX,
            [pdop_est, hdop_est, vdop_est, gdop_est, dop_ratio_est],
        ):
            if col in df.columns:
                df[col] = df[col].fillna(est).fillna(df[col].median())

    # ── 5. Remaining NaN — forward-fill within session then zero-fill ────
    # groupby().transform() is the pandas 2.x-safe pattern for within-group
    # operations: it never promotes the group key to an index (unlike apply).
    # We only operate on numeric columns so string columns (source, split, etc.)
    # are left untouched.
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df[num_cols] = df.groupby(
        "source")[num_cols].transform(lambda x: x.ffill())
    df = df.fillna(0.0)

    return df


def clip_features(df: pd.DataFrame) -> pd.DataFrame:
    """Clip physical outliers to sensor/signal maximum bounds."""
    df = df.copy()
    for col, (lo, hi) in CLIP_BOUNDS.items():
        if col in df.columns:
            df[col] = df[col].clip(lo, hi)
    return df


def fit_and_scale(
    df: pd.DataFrame,
    feature_cols: list[str],
    scaler_path: Path = SCALER_PATH,
) -> tuple[pd.DataFrame, MinMaxScaler]:
    """Fit MinMaxScaler on TRAINING rows only; transform the full dataset.

    Fitting on training data only is critical to prevent data leakage —
    the scaler must not 'see' validation or test statistics.
    Ref: Hastie, T., Tibshirani, R., & Friedman, J. (2009). The Elements of
         Statistical Learning (2nd ed.). Section 7.3.
    """
    train_mask = df["split"] == "train"
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(df.loc[train_mask, feature_cols].values)

    scaled = scaler.transform(df[feature_cols].values)
    df = df.copy()
    df[feature_cols] = scaled

    scaler_path.parent.mkdir(parents=True, exist_ok=True)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    log.info(f"  Scaler saved → {scaler_path}")
    return df, scaler


def _build_windows_for_session(
    rows: np.ndarray,         # shape (T_session, n_features)
    labels: np.ndarray,       # shape (T_session,)
    window_size: int = WINDOW_SIZE,
    horizons: dict[str, int] = HORIZONS,
) -> tuple[np.ndarray, dict[str, np.ndarray]] | None:
    """Build sliding windows for a single session.

    For each start index i the window is rows[i : i+window_size].
    The target labels are taken from:
        y_5s  → labels[i + window_size + 5  - 1]
        y_15s → labels[i + window_size + 15 - 1]
        y_30s → labels[i + window_size + 30 - 1]

    Windows that would require labels BEYOND the session boundary are dropped.

    No overlap is ever created across session boundaries because this function
    is called per-session (prevents temporal data leakage across recordings).
    Ref: Bergmeir, C. & Benitez, J. M. (2012). Neural Networks, 32, 182–192.
         https://doi.org/10.1016/j.neunet.2012.02.021
    """
    max_horizon = max(horizons.values())
    n = len(rows)
    max_start = n - window_size - max_horizon

    if max_start <= 0:
        return None   # session too short

    xs = []
    ys = {k: [] for k in horizons}

    for i in range(max_start + 1):
        xs.append(rows[i: i + window_size])
        for key, h in horizons.items():
            ys[key].append(labels[i + window_size + h - 1])

    x_arr = np.array(xs, dtype=np.float32)                # (N, T, F)
    y_arr = {k: np.array(v, dtype=np.int64) for k, v in ys.items()}
    return x_arr, y_arr


def build_windows(
    df: pd.DataFrame,
    feature_cols: list[str],
) -> dict[str, dict]:
    """Build all windows, returning a dict keyed by split.

    Returns
    -------
    {
      'train': {'X': ndarray (N,30,34), 'y_5s': ndarray, 'y_15s': ..., 'y_30s': ...},
      'val':   {...},
      'test':  {...},
    }
    """
    split_data: dict[str, dict] = {
        "train": {"X": [], "y_5s": [], "y_15s": [], "y_30s": []},
        "val":   {"X": [], "y_5s": [], "y_15s": [], "y_30s": []},
        "test":  {"X": [], "y_5s": [], "y_15s": [], "y_30s": []},
    }

    # Group by (source, scenario) to create per-session windows
    session_col = "source"
    for session_id, grp in df.groupby(session_col):
        grp = grp.sort_values(
            "timestamp") if "timestamp" in grp.columns else grp
        # all rows in a session share the same split
        split = grp["split"].iloc[0]
        rows = grp[feature_cols].values.astype(np.float32)
        labels = grp["label"].values.astype(np.int64)

        result = _build_windows_for_session(rows, labels)
        if result is None:
            log.warning(f"  Session '{session_id}' too short; skipping.")
            continue

        x_arr, y_arr = result
        if split not in split_data:
            log.warning(f"  Unknown split '{split}'; assigning to train.")
            split = "train"

        split_data[split]["X"].append(x_arr)
        for k in HORIZONS:
            split_data[split][f"y_{k}"].append(y_arr[k])

    # Concatenate along axis 0
    for spl in split_data:
        if not split_data[spl]["X"]:
            continue
        split_data[spl]["X"] = np.concatenate(split_data[spl]["X"], axis=0)
        for k in HORIZONS:
            split_data[spl][f"y_{k}"] = np.concatenate(
                split_data[spl][f"y_{k}"], axis=0
            )

    for spl, d in split_data.items():
        if isinstance(d["X"], list):
            continue
        log.info(
            f"  {spl:5s}: {d['X'].shape[0]:6,} windows  "
            f"| 5s label dist: {np.bincount(d['y_5s'], minlength=3)}"
        )

    return split_data


def apply_smote(
    split_data: dict,
    random_state: int = 42,
) -> dict:
    """Apply SMOTE to TRAINING windows only.

    SMOTE is applied to the flattened (N, 30×34) representation, then
    reshaped back to (N, 30, 34).  This treats each window as a sample
    and interpolates in the high-dimensional feature space.

    IMPORTANT: SMOTE is NEVER applied to validation or test sets.  Applying
    SMOTE to held-out data would inflate reported metrics and constitutes
    data leakage.  Ref: Chawla et al. (2002), JAIR.

    We use the y_5s labels for SMOTE (the nearest horizon is most balanced
    and the oversampled windows improve representation for all three heads).
    """
    X_train = split_data["train"]["X"]
    y_train = split_data["train"]["y_5s"]

    # Guard: SMOTE requires at least 1 sample per class. Skip if any class
    # is absent (expected in --debug mode where only 500 rows/source are used).
    class_counts = np.bincount(y_train, minlength=3)
    if class_counts.min() == 0:
        log.warning(
            f"  SMOTE skipped: class(es) absent from training windows "
            f"(counts={class_counts}). Use the full dataset for SMOTE to apply."
        )
        return split_data

    n, t, f = X_train.shape
    X_flat = X_train.reshape(n, t * f)

    # Adaptive k_neighbors: SMOTE requires at least k+1 samples per class.
    # In debug/tiny-dataset mode this may be as low as 1.
    min_class_count = int(np.bincount(y_train).min())
    k_neighbors = max(1, min(5, min_class_count - 1))
    if k_neighbors < 5:
        log.warning(
            f"  SMOTE: minority class has only {min_class_count} samples; "
            f"reducing k_neighbors to {k_neighbors}."
        )

    log.info(
        f"  SMOTE input  shape: {X_flat.shape} | labels: {np.bincount(y_train)}")
    smote = SMOTE(sampling_strategy=SMOTE_STRATEGY,
                  random_state=random_state, k_neighbors=k_neighbors)
    X_res, y_res = smote.fit_resample(X_flat, y_train)
    log.info(
        f"  SMOTE output shape: {X_res.shape} | labels: {np.bincount(y_res)}")

    X_res_3d = X_res.reshape(-1, t, f)

    # Propagate the same oversampling indices to all horizon targets.
    # New synthetic samples inherit the y_5s label; y_15s/y_30s are set
    # to y_5s for synthetic rows (conservative approximation).
    n_orig = n
    split_data["train"]["X"] = X_res_3d.astype(np.float32)
    split_data["train"]["y_5s"] = y_res.astype(np.int64)
    for k in ("y_15s", "y_30s"):
        orig = split_data["train"][k]
        n_synth = len(y_res) - n_orig
        synth_labels = y_res[n_orig:]    # use y_5s of synthetic rows
        split_data["train"][k] = np.concatenate(
            [orig, synth_labels]).astype(np.int64)

    return split_data


def save_windows(split_data: dict, out_dir: Path = OUT_DIR) -> None:
    """Save windows to .npz files in data/processed/windows/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for spl, d in split_data.items():
        if not isinstance(d.get("X"), np.ndarray):
            continue
        path = out_dir / f"{spl}.npz"
        np.savez_compressed(path, **d)
        log.info(
            f"  Saved {spl:5s} windows → {path}  ({d['X'].shape[0]:,} samples)")


def load_windows(out_dir: Path = OUT_DIR) -> dict[str, dict]:
    """Load pre-built window .npz files back into memory."""
    result = {}
    for spl in ("train", "val", "test"):
        path = out_dir / f"{spl}.npz"
        if not path.exists():
            raise FileNotFoundError(
                f"Window file not found: {path}  — run prepare() first")
        data = np.load(path)
        result[spl] = {k: data[k] for k in data.files}
    return result


# ─── Top-level convenience function ──────────────────────────────────────────
def prepare(
    data_file: Path = DATA_FILE,
    out_dir: Path = OUT_DIR,
    scaler_path: Path = SCALER_PATH,
    smote: bool = True,
    random_state: int = 42,
    force_rebuild: bool = False,
    max_rows_per_source: int | None = None,
) -> dict[str, dict]:
    """Run the full feature-preparation pipeline.

    Parameters
    ----------
    data_file          : Path to sentinel_gnss_labelled.csv.
    out_dir            : Directory to save .npz window files.
    scaler_path        : Where to save the fitted MinMaxScaler.
    smote              : Apply SMOTE to training set if True.
    random_state       : RNG seed for reproducibility.
    force_rebuild      : Rebuild even if cached .npz files exist.
    max_rows_per_source: If set, subsample each source to this many rows
                         (used for quick smoke-tests via --debug).

    Returns
    -------
    split_data : dict with keys 'train', 'val', 'test', each containing
                 'X', 'y_5s', 'y_15s', 'y_30s' numpy arrays.
    """
    cache_ok = all((out_dir / f"{s}.npz").exists()
                   for s in ("train", "val", "test"))
    if cache_ok and not force_rebuild:
        log.info(
            "Cached windows found; loading (use force_rebuild=True to regenerate).")
        return load_windows(out_dir)

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s  %(message)s")

    df = load_and_validate(data_file)

    if max_rows_per_source is not None:
        log.warning(
            f"DEBUG MODE: subsampling to {max_rows_per_source} rows per source "
            f"({len(df):,} → up to {max_rows_per_source * df['source'].nunique():,} rows)."
        )
        # groupby().head() is safer than groupby().apply() in pandas 2.x —
        # the latter can promote the group key to an index under some configs,
        # causing a KeyError on the next groupby call.
        df = (
            df.groupby("source", group_keys=False)
            .head(max_rows_per_source)
            .reset_index(drop=True)
        )
        log.info(f"  After subsample: {len(df):,} rows")

    df = impute(df)
    df = clip_features(df)

    feature_cols = _get_feature_cols(df)
    log.info(f"Feature columns ({len(feature_cols)}): {feature_cols}")

    df, scaler = fit_and_scale(df, feature_cols, scaler_path)

    split_data = build_windows(df, feature_cols)

    if smote:
        log.info("Applying SMOTE to training set …")
        split_data = apply_smote(split_data, random_state=random_state)

    save_windows(split_data, out_dir)
    return split_data


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(
        description="Build SENTINEL-GNSS feature windows")
    parser.add_argument("--force", action="store_true",
                        help="Rebuild windows even if cached .npz files exist")
    parser.add_argument("--no_smote", action="store_true",
                        help="Skip SMOTE oversampling. Use when training deep models: "
                             "SMOTE interpolates in the flattened (T×F) space, creating "
                             "synthetic windows with incoherent temporal dynamics that "
                             "mislead the Transformer-LSTM. Classical ML baselines should "
                             "still use SMOTE (the default). Saves to windows_no_smote/.")
    parser.add_argument("--debug", action="store_true",
                        help="Smoke-test mode: 500 rows/source, saves to windows_debug/ "
                             "(does not overwrite real windows)")
    args = parser.parse_args()

    if args.debug:
        debug_out = ROOT / "data" / "processed" / "windows_debug"
        debug_scaler = ROOT / "data" / "processed" / "scaler_debug.pkl"
        log.warning(
            "=== DEBUG MODE — outputs go to windows_debug/, scaler_debug.pkl ===")
        data = prepare(
            out_dir=debug_out,
            scaler_path=debug_scaler,
            force_rebuild=True,
            max_rows_per_source=500,
        )
    else:
        if args.no_smote:
            no_smote_out = ROOT / "data" / "processed" / "windows_no_smote"
            log.info(
                "=== --no_smote: saving class-weight-only windows to windows_no_smote/ ===")
            data = prepare(
                out_dir=no_smote_out,
                force_rebuild=args.force,
                smote=False,
            )
        else:
            data = prepare(force_rebuild=args.force)

    print("\n=== Window summary ===")
    for spl, d in data.items():
        if isinstance(d.get("X"), np.ndarray):
            print(
                f"  {spl:5s}  X={d['X'].shape}  y_5s={np.bincount(d['y_5s'])}")
