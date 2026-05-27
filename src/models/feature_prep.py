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
  X      : (N, 30, 37)  — 30 time-steps × 37 features
             (33 signal + cnr_available + pdop_delta + hdop_delta + receiver_tier)
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
    # Delta (rate-of-change) features added in Run 6
    "pdop_delta":        (-15.0, 15.0),
    "hdop_delta":        (-15.0, 15.0),
    # Receiver tier feature added in Run 7
    "receiver_tier":     (0.0, 4.0),
}

# Features for which within-session first differences are computed.
# Gradient saliency from Run 5 confirmed pdop and hdop are the two most
# informative raw features; their rate of change is a leading degradation signal.
DELTA_FEATURE_COLS: list[str] = ["pdop", "hdop"]

# SMOTE target ratios (applied to training set only)
# Goal: CLEAN stays majority; WARNING × 2; DEGRADED × 3 (approx.)
SMOTE_STRATEGY = "auto"   # oversample all minority classes to match majority

# ─── Default source exclusions ──────────────────────────────────────────────
# Sources are excluded when they introduce label inconsistency or feature noise
# that is incompatible with the primary C/N0-based labelling scheme.
#
# Drone sessions: domain mismatch (aerial vs vehicular), 100% CLEAN, no value.
# Oxford RobotCar: 2014 GPS-only hardware (no GLONASS/Galileo). Labels derived
#   from position sigma (average ~6 m) — a hardware-limitation artefact, not a
#   signal physics label. 96% DEGRADED/WARNING; no C/N0 data. Including it
#   teaches the model "Oxford-receiver noise = DEGRADED", the wrong association.
# NCLT: 2012 GPS module with a logging bug — num_satellites is always 0, so every
#   DOP proxy value is 30/√0 = undefined → imputed as noise. No C/N0 data.
#   Labels based on RTK error vs LiDAR SLAM (different mechanism from C/N0).
# Tokyo Shinjuku / Odaiba u-blox: 31,265 + 6,205 rows, 91–100% CLEAN, with DOP
#   imputed from satellite count (no NMEA GSA sentences). These rows dominated the
#   CLEAN class (51% of dataset) and caused the model to learn "Tokyo-like imputed
#   DOP = CLEAN", suppressing WARNING recall. Retained as a SEPARATE cross-city
#   evaluation set (tokyo_odaiba_trimble stays in val to provide CLEAN val signal).
#
# To include any of these: pass --include_drones / --include_legacy / --include_tokyo
# on the CLI, or pass exclude_sources=[] to prepare().
DEFAULT_EXCLUDE_SOURCES: list[str] = [
    # Aerial / non-vehicular
    "supervisor_drone_1",         # 2,769 rows — UAV open sky, all CLEAN
    "supervisor_drone_2",         # 2,792 rows — UAV open sky, all CLEAN
    "supervisor_drone_12",        # 5,562 rows — UAV open sky, all CLEAN
    # Legacy hardware — incompatible label mechanisms
    "oxford",                     # 7,114 rows — 2014 GPS-only, position-sigma labels
    "nclt",                       # 7,493 rows — 2012 GPS, satellite count always 0 (bug)
    # Tokyo cross-city evaluation set (kept separate to preserve geographic generalization claim)
    "tokyo_shinjuku_trimble",     # 20,790 rows — train split, 94% CLEAN, DOP imputed
    "tokyo_shinjuku_ublox",       # 10,475 rows — train split, 92% CLEAN, DOP imputed
    "tokyo_odaiba_ublox",         #  6,205 rows — test split, 100% CLEAN, DOP imputed
    # tokyo_odaiba_trimble is intentionally NOT excluded: it stays in val (12,398 rows,
    # 97.7% CLEAN) and provides the CLEAN examples the balanced val early-stopping
    # subset needs.  It is a proxy for "professional receiver, open/moderate urban".
]

# ─── Split reassignment ──────────────────────────────────────────────────────
# Resolves two classes of problem:
#
# CLASS 1 — Test-only WARNING/DEGRADED (runs 2-4 root cause):
#   84% of test WARNING rows came from sources with ZERO training rows.
#   Fix: move those sources to training, keep one per-type in test.
#
# CLASS 2 — Instant-blockage gap (new, run 7):
#   Scenario A (3 runs, all in 'validation') was NEVER in training, so the
#   model had no examples of the sudden complete-blockage pattern.  Moving
#   r1+r2 to train while keeping r3 in val gives training coverage AND
#   preserves a DEGRADED signal for the balanced-val early-stopping subset.
#
# CLASS 3 — Useless all-CLEAN test sessions (run 7):
#   supervisor_vehicle_exp1_4b, exp2_1b, exp2_2_b, exp2_3b are all 100%
#   CLEAN.  Having them in test only inflates CLEAN test accuracy without
#   improving minority-class evaluation.  Move to training; keep exp1_3_b,
#   exp1_4b, and exp3 in test for a balanced hold-out (37% CLEAN / 57% WARN
#   / 6% DEG).
#
# Resulting test set (Beijing campus hold-out):
#   supervisor_vehicle_exp1_3_b  665 rows: 607 WARN,  58 DEG,   0 CLEAN
#   supervisor_vehicle_exp1_4b   397 rows:   0 WARN,   0 DEG, 397 CLEAN
#   supervisor_vehicle_exp3      392 rows:   0 WARN,   0 DEG, 392 CLEAN
#   ────────────────────────────────────────────────────────────────────
#   TOTAL                      1,454 rows: 607 WARN,  58 DEG, 789 CLEAN
#
SPLIT_REASSIGN: dict[str, str] = {
    # ── CLASS 1: WARNING/DEGRADED sources moved from test → train ───────────
    "supervisor_vehicle_exp1_1_base": "train",  # 664 rows: 654 WARN,  10 DEG
    "supervisor_vehicle_exp1_2_base": "train",  # 357 rows: 221 WARN, 136 DEG
    "supervisor_vehicle_exp4":        "train",  # 480 rows: 280 CLEAN, 182 WARN, 18 DEG
    "scenario_b_r1":                  "train",  # 535 rows: 260 CLEAN, 206 WARN, 69 DEG
    "scenario_b_r2":                  "train",  # 391 rows: 118 CLEAN, 260 WARN, 13 DEG
    "urbannav_tunnel_google_pixel4":  "train",  # 263 rows: 232 WARN,  31 DEG
    "urbannav_tunnel_huawei_p40pro":  "train",  # 400 rows: 216 WARN, 184 DEG
    # supervisor_vehicle_exp1_3_b intentionally kept in test (607 WARN, 58 DEG).
    # supervisor_vehicle_exp1_4b intentionally kept in test (397 CLEAN) for balance.
    # supervisor_vehicle_exp3    intentionally kept in test (392 CLEAN) for balance.

    # ── UrbanNav HK-Deep-Urban-1 (Whampoa) consumer phones → train ──────────
    # Consumer phones have the most DEGRADED and WARNING epochs in Deep.
    # Professional (NovAtel) and high-precision (F9P) kept in val for
    # cross-receiver generalisation experiment (Paper 2).
    "urbannav_deep_google_pixel4":   "train",
    "urbannav_deep_huawei_p40pro":   "train",
    "urbannav_deep_xiaomi_mi8":      "train",
    "urbannav_deep_samsung_note8":   "train",

    # ── UrbanNav HK-Harsh-Urban-1 (Mong Kok) — all non-professional → train ─
    # Mong Kok provides the most severe urban-canyon signal degradation in the
    # dataset. Moving all consumer phones and M8T (prosumer) to training gives
    # the model the most challenging WARNING/DEGRADED examples.
    # Keep NovAtel FlexPak6 in val for cross-receiver eval.
    "urbannav_harsh_google_pixel4":  "train",
    "urbannav_harsh_huawei_p40pro":  "train",
    "urbannav_harsh_xiaomi_mi8":     "train",
    "urbannav_harsh_samsung_note8":  "train",
    "urbannav_harsh_ublox_m8t_GC":   "train",
    "urbannav_harsh_ublox_m8t_GEJ":  "train",
    "urbannav_harsh_ublox_m8t_GRJ":  "train",

    # ── CLASS 2: Scenario A moved from val → train ───────────────────────────
    # Instant-blockage pattern was completely absent from training.  r3 stays
    # in val so the balanced early-stopping subset retains DEGRADED signal.
    "scenario_a_r1":                  "train",  #  47 rows: 33 DEG, 11 CLEAN, 3 WARN
    "scenario_a_r2":                  "train",  #  53 rows: 41 DEG,  9 CLEAN, 3 WARN

    # ── CLASS 3: All-CLEAN test sessions moved to train ──────────────────────
    "supervisor_vehicle_exp2_1b":     "train",  # 174 rows: all CLEAN
    "supervisor_vehicle_exp2_2_b":    "train",  # 132 rows: all CLEAN
    "supervisor_vehicle_exp2_3b":     "train",  # 140 rows: all CLEAN
}


# ─── Receiver tier mapping ───────────────────────────────────────────────────
# A single integer (0–4) that encodes hardware quality class.  Added as a
# constant feature per session so the model can distinguish "C/N0 = 38 dBHz on
# a Septentrio" (= CLEAN) from "C/N0 = 38 dBHz on a u-blox M8T" (= WARNING).
# Without this context the model cannot reconcile contradictory CLEAN/WARNING
# labels that arise purely from receiver hardware differences.
#
#   0 = professional multi-constellation  (Septentrio, NovAtel, Trimble survey)
#   1 = high-precision dual-frequency     (u-blox F9P)
#   2 = prosumer single-frequency         (u-blox M8T)
#   3 = consumer phone                    (Pixel 4, Huawei P40 Pro, Mi8, Note8)
#   4 = legacy GPS-only                   (NCLT 2012, Oxford 2014 — excluded from
#                                          primary training but kept for reference)
#
RECEIVER_TIER_MAP: dict[str, int] = {
    # ── Professional (tier 0) — Septentrio Mosaic-X5C, Beijing ──────────────
    "scenario_a_r1": 0, "scenario_a_r2": 0, "scenario_a_r3": 0,
    "scenario_b_r1": 0, "scenario_b_r2": 0,
    "scenario_c_r1": 0, "scenario_c_r2": 0,
    "scenario_d_r1": 0,
    "scenario_e_r1": 0, "scenario_e_r2": 0, "scenario_e_r3": 0,
    "scenario_e_master": 0,
    "supervisor_car_ref":           0,
    "supervisor_vehicle_exp1_1_base": 0, "supervisor_vehicle_exp1_2_base": 0,
    "supervisor_vehicle_exp1_3_b":  0,   "supervisor_vehicle_exp1_4b":    0,
    "supervisor_vehicle_exp2_1b":   0,   "supervisor_vehicle_exp2_2_b":   0,
    "supervisor_vehicle_exp2_3b":   0,   "supervisor_vehicle_exp3":       0,
    "supervisor_vehicle_exp4":      0,
    # Unicore UB4B0 drone (military-grade, aerial) — excluded from primary training
    "supervisor_drone_1": 0, "supervisor_drone_2": 0, "supervisor_drone_12": 0,
    # Professional — NovAtel FlexPak6, UrbanNav HK
    "urbannav_novatel_flexpak6":        0,
    "urbannav_tunnel_novatel_flexpak6": 0,
    "urbannav_deep_novatel_flexpak6":   0,   # Whampoa (Deep)
    "urbannav_harsh_novatel_flexpak6":  0,   # Mong Kok (Harsh)
    # Professional — Trimble survey grade, Tokyo
    "tokyo_odaiba_trimble":   0,
    "tokyo_shinjuku_trimble": 0,
    # ── High-precision dual-frequency (tier 1) — u-blox F9P ─────────────────
    "urbannav_ublox_f9p":              1, "urbannav_ublox_f9p_splitter":         1,
    "urbannav_tunnel_ublox_f9p":       1, "urbannav_tunnel_ublox_f9p_splitter":  1,
    "urbannav_deep_ublox_f9p":         1, "urbannav_deep_ublox_f9p_splitter":    1,
    "urbannav_harsh_ublox_f9p":        1, "urbannav_harsh_ublox_f9p_splitter":   1,
    "tokyo_odaiba_ublox":              1, "tokyo_shinjuku_ublox":                1,
    # ── Prosumer single-frequency (tier 2) — u-blox M8T ─────────────────────
    # Note: Medium uses "GR" (GPS+GLONASS); Tunnel/Deep/Harsh use "GRJ" (+QZSS)
    "urbannav_ublox_m8t_GC":           2, "urbannav_ublox_m8t_GEJ":             2,
    "urbannav_ublox_m8t_GR":           2,
    "urbannav_tunnel_ublox_m8t_GC":    2, "urbannav_tunnel_ublox_m8t_GEJ":      2,
    "urbannav_tunnel_ublox_m8t_GRJ":   2,
    "urbannav_deep_ublox_m8t_GC":      2, "urbannav_deep_ublox_m8t_GEJ":        2,
    "urbannav_deep_ublox_m8t_GRJ":     2,
    "urbannav_harsh_ublox_m8t_GC":     2, "urbannav_harsh_ublox_m8t_GEJ":       2,
    "urbannav_harsh_ublox_m8t_GRJ":    2,
    # ── Consumer phone (tier 3) ──────────────────────────────────────────────
    "urbannav_google_pixel4":          3, "urbannav_huawei_p40pro":              3,
    "urbannav_xiaomi_mi8":             3, "urbannav_samsung_note8":              3,
    "urbannav_tunnel_google_pixel4":   3, "urbannav_tunnel_huawei_p40pro":       3,
    "urbannav_tunnel_xiaomi_mi8":      3, "urbannav_tunnel_samsung_note8":       3,
    "urbannav_deep_google_pixel4":     3, "urbannav_deep_huawei_p40pro":         3,
    "urbannav_deep_xiaomi_mi8":        3, "urbannav_deep_samsung_note8":         3,
    "urbannav_harsh_google_pixel4":    3, "urbannav_harsh_huawei_p40pro":        3,
    "urbannav_harsh_xiaomi_mi8":       3, "urbannav_harsh_samsung_note8":        3,
    # ── Legacy GPS-only (tier 4) — excluded from primary training ────────────
    "nclt":   4,
    "oxford": 4,
}


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


def add_delta_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add within-session first-difference features for key DOP signals.

    delta_col[t] = col[t] - col[t-1]   (first row per session = 0.0)

    Rationale: the rate of change of PDOP/HDOP is a leading indicator of
    imminent GNSS geometry deterioration — a rapid positive spike signals
    satellites are being obscured.  Gradient-based saliency from Run 5
    confirmed pdop and hdop are the two highest-importance raw features;
    adding their deltas gives the model an explicit trend signal.

    Must be called AFTER clip_features() and BEFORE fit_and_scale() so the
    delta values are properly clipped and scaled.
    """
    df = df.copy()
    for col in DELTA_FEATURE_COLS:
        if col not in df.columns:
            continue
        delta = df.groupby("source")[col].diff().fillna(0.0)
        df[f"{col}_delta"] = delta.astype(np.float32)
    return df


def add_receiver_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Add a constant-per-session receiver_tier integer feature (0–4).

    Maps each source to a hardware quality class so the model can distinguish
    "C/N0 = 38 dBHz on Septentrio (CLEAN)" from "C/N0 = 38 dBHz on u-blox M8T
    (WARNING)".  Without this the model cannot reconcile contradictory labels
    that arise from receiver hardware differences across the multi-source dataset.

    Tier assignment:
        0 — professional multi-constellation (Septentrio, NovAtel, Trimble)
        1 — high-precision dual-frequency    (u-blox F9P)
        2 — prosumer single-frequency        (u-blox M8T)
        3 — consumer phone                   (Pixel 4, Huawei P40, Mi8, Note8)
        4 — legacy GPS-only                  (NCLT 2012, Oxford 2014)

    Unknown sources default to tier 2 (prosumer mid-point) rather than 0 or 4
    to avoid erroneously anchoring new sources at the extremes.
    """
    df = df.copy()
    df["receiver_tier"] = (
        df["source"].map(RECEIVER_TIER_MAP).fillna(2).astype(np.float32)
    )
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
    ys = {"0s": [], **{k: [] for k in horizons}}

    for i in range(max_start + 1):
        xs.append(rows[i: i + window_size])
        # Current state: label of the last time-step in the window
        ys["0s"].append(labels[i + window_size - 1])
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
      'train': {'X': ndarray (N,30,37), 'y_5s': ndarray, 'y_15s': ..., 'y_30s': ...},
      'val':   {...},
      'test':  {...},
    }
    """
    split_data: dict[str, dict] = {
        "train": {"X": [], "y_0s": [], "y_5s": [], "y_15s": [], "y_30s": []},
        "val":   {"X": [], "y_0s": [], "y_5s": [], "y_15s": [], "y_30s": []},
        "test":  {"X": [], "y_0s": [], "y_5s": [], "y_15s": [], "y_30s": []},
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
        for k in ("0s", *HORIZONS):
            split_data[split][f"y_{k}"].append(y_arr[k])

    # Concatenate along axis 0
    for spl in split_data:
        if not split_data[spl]["X"]:
            continue
        split_data[spl]["X"] = np.concatenate(split_data[spl]["X"], axis=0)
        for k in ("0s", *HORIZONS):
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
    for k in ("y_0s", "y_15s", "y_30s"):
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
    exclude_sources: list[str] | None = None,
    reassign_splits: bool = True,
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
    exclude_sources    : Source names to remove before windowing.
                         e.g. ['nclt'] drops the RTK-labelled NCLT data.
    reassign_splits    : If True, apply SPLIT_REASSIGN to move all-CLEAN
                         val-only drone sessions to train (default: True).

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

    # ── Source exclusion ──────────────────────────────────────────────────────
    if exclude_sources:
        for src in list(exclude_sources):
            n_before = len(df)
            df = df[df["source"] != src].reset_index(drop=True)
            log.info(
                f"  Excluded '{src}': {n_before - len(df):,} rows removed")

    # ── Split reassignment ────────────────────────────────────────────────────
    if reassign_splits:
        for src, new_split in SPLIT_REASSIGN.items():
            src_mask = df["source"] == src
            if src_mask.any():
                old_split = df.loc[src_mask, "split"].iloc[0]
                df.loc[src_mask, "split"] = new_split
                log.info(
                    f"  Split reassign: '{src}'  {old_split} \u2192 {new_split}"
                    f"  ({src_mask.sum():,} rows)"
                )

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
    df = add_delta_features(df)   # adds pdop_delta, hdop_delta (Run 6)
    df = add_receiver_tier(df)    # adds receiver_tier 0–4 constant per session (Run 7)

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
    parser.add_argument("--exclude_sources", type=str, nargs="*", default=None,
                        metavar="SOURCE",
                        help="Additional source names to drop before windowing "
                             "(drone sessions are always excluded by default). "
                             "e.g. --exclude_sources nclt oxford")
    parser.add_argument("--include_drones", action="store_true",
                        help="Include supervisor_drone_* sessions (excluded by default). "
                             "Not recommended: drone data is non-vehicular open-sky only.")
    parser.add_argument("--include_legacy", action="store_true",
                        help="Include NCLT and Oxford in all splits (excluded by default). "
                             "Not recommended for primary training: 2012-2015 GPS-only "
                             "hardware with position-error labels incompatible with C/N0-based "
                             "labelling. Use --include_legacy for cross-era generalization eval.")
    parser.add_argument("--include_tokyo", action="store_true",
                        help="Include Tokyo Shinjuku and Odaiba u-blox in all splits "
                             "(excluded by default from primary training). Use for cross-city "
                             "generalization evaluation. tokyo_odaiba_trimble remains in "
                             "validation regardless of this flag.")
    parser.add_argument("--no_reassign", action="store_true",
                        help="Disable SPLIT_REASSIGN (moves 7 test-only WARNING/DEGRADED "
                             "sources to train to fix source-domain mismatch).")
    args = parser.parse_args()

    # Build the effective exclude list starting from DEFAULT_EXCLUDE_SOURCES,
    # then selectively remove groups that the user wants to include back.
    effective_exclude = list(DEFAULT_EXCLUDE_SOURCES)

    if args.include_drones:
        for src in ["supervisor_drone_1", "supervisor_drone_2", "supervisor_drone_12"]:
            effective_exclude = [s for s in effective_exclude if s != src]

    if args.include_legacy:
        for src in ["nclt", "oxford"]:
            effective_exclude = [s for s in effective_exclude if s != src]

    if args.include_tokyo:
        for src in ["tokyo_shinjuku_trimble", "tokyo_shinjuku_ublox", "tokyo_odaiba_ublox"]:
            effective_exclude = [s for s in effective_exclude if s != src]

    if args.exclude_sources:
        for s in args.exclude_sources:
            if s not in effective_exclude:
                effective_exclude.append(s)

    effective_exclude = effective_exclude or None   # None = no exclusion

    if effective_exclude:
        log.info(f"Excluding sources: {effective_exclude}")

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
            exclude_sources=effective_exclude,
            reassign_splits=not args.no_reassign,
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
                exclude_sources=effective_exclude,
                reassign_splits=not args.no_reassign,
            )
        else:
            data = prepare(
                force_rebuild=args.force,
                exclude_sources=effective_exclude,
                reassign_splits=not args.no_reassign,
            )

    print("\n=== Window summary ===")
    for spl, d in data.items():
        if isinstance(d.get("X"), np.ndarray):
            print(
                f"  {spl:5s}  X={d['X'].shape}  y_5s={np.bincount(d['y_5s'])}")
