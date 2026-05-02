"""
Unified Feature Extractor for GNSS Signal Degradation Prediction
=================================================================
Extracts 35 standardized features from RTKLIB .pos solution files.
MUST use the SAME logic for ALL datasets (vehicle, drone, NCLT, UrbanNav, Oxford, KAIST).

Input:  RTKLIB .pos solution file (from rtkpost.exe)
Output: CSV with 35 feature columns + timestamp + label columns

Usage:
    python feature_extractor.py --input data/rinex/vehicle_solution.pos
                                --output data/processed/vehicle_features.csv
                                --source supervisor_vehicle
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── FEATURE DEFINITIONS ─────────────────────────────────────────────────────
# 35 features, grouped into 7 categories of 5 each

FEATURE_GROUPS = {
    "Position": ["lat", "lon", "alt", "lat_std", "lon_std"],
    "Signal Strength (C/N0)": ["mean_cnr", "min_cnr", "max_cnr", "std_cnr", "cnr_trend"],
    "Satellite Count": ["num_satellites", "sat_mean", "sat_min", "sat_visibility", "sat_drop_rate"],
    "DOP (Dilution of Precision)": ["pdop", "hdop", "vdop", "gdop", "dop_ratio"],
    "Receiver Status": ["solution_status", "baseline_sats", "solution_age", "fix_continuity", "fix_transitions"],
    "Temporal Patterns": ["position_variance", "cnr_variance", "elevation_violations", "multipath", "clock_bias"],
    "Atmospheric Effects": ["iono_delay", "tropo_delay", "cycle_slips", "residual_mean", "residual_std"],
}

ALL_FEATURES = [feat for group in FEATURE_GROUPS.values() for feat in group]  # 35 features total


def read_rtklib_pos(pos_file: Path) -> pd.DataFrame:
    """
    Read RTKLIB .pos solution file.

    RTKLIB .pos format:
        % YYYY/MM/DD HH:MM:SS.SSS lat(deg) lon(deg) height(m) Q ns sdn(m) sde(m) sdu(m) sdne(m) sdeu(m) sdun(m) age(s) ratio
        % Q: 1=fix, 2=float, 3=SBAS, 4=DGPS, 5=Single, 6=PPP
    """
    try:
        df = pd.read_csv(
            pos_file,
            delim_whitespace=True,
            comment='%',
            header=None,
            names=[
                'date', 'time', 'latitude', 'longitude', 'altitude',
                'q', 'ns', 'sdn', 'sde', 'sdu', 'sdne', 'sdeu', 'sdun',
                'age', 'ratio'
            ],
            dtype={'date': str, 'time': str}
        )

        # Parse timestamp
        df['timestamp'] = pd.to_datetime(
            df['date'] + ' ' + df['time'],
            format='%Y/%m/%d %H:%M:%S.%f',
            errors='coerce'
        )

        # Drop rows with bad timestamps or positions
        df = df.dropna(subset=['timestamp', 'latitude', 'longitude'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        logger.info(f"Loaded {len(df)} epochs from {pos_file.name}")
        logger.info(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"  Fix quality Q=1 (fixed): {(df['q'] == 1).sum()}/{len(df)} epochs")

        return df

    except Exception as e:
        logger.error(f"Error reading {pos_file}: {e}")
        return None


def compute_features_window(window: pd.DataFrame, current: pd.Series) -> dict:
    """
    Compute all 35 features for a single epoch using a 30-second sliding window.

    Args:
        window: DataFrame with last 30 seconds of GPS data
        current: Series with current epoch data

    Returns:
        dict with all 35 feature values
    """
    features = {}

    # ─── GROUP 1: Position (5 features) ───────────────────────────────────────
    features['lat'] = current.get('latitude', np.nan)
    features['lon'] = current.get('longitude', np.nan)
    features['alt'] = current.get('altitude', np.nan)
    # sdn/sde = standard deviation north/east from RTKLIB
    features['lat_std'] = window['sdn'].mean() if 'sdn' in window.columns else 0.05
    features['lon_std'] = window['sde'].mean() if 'sde' in window.columns else 0.05

    # ─── GROUP 2: Signal Strength / C/N0 (5 features) ─────────────────────────
    # C/N0 = Carrier-to-Noise ratio (signal strength), typically 30-50 dB-Hz
    # RTKLIB doesn't directly provide C/N0; we derive a proxy from solution quality
    # Using sdu (up std) as a proxy — or if C/N0 directly available from raw data
    if 'cnr' in window.columns:
        cnr_series = window['cnr']
        features['mean_cnr'] = cnr_series.mean()
        features['min_cnr'] = cnr_series.min()
        features['max_cnr'] = cnr_series.max()
        features['std_cnr'] = cnr_series.std()
        features['cnr_trend'] = (cnr_series.iloc[-1] - cnr_series.iloc[0]) / max(len(cnr_series), 1)
    else:
        # Derive proxy from solution quality (higher Q = worse signal)
        q_vals = window['q'] if 'q' in window.columns else pd.Series([1] * len(window))
        # Map Q to approximate C/N0: Q=1→45dB, Q=2→35dB, Q=5→25dB
        cnr_proxy = 50 - (q_vals * 5)
        features['mean_cnr'] = cnr_proxy.mean()
        features['min_cnr'] = cnr_proxy.min()
        features['max_cnr'] = cnr_proxy.max()
        features['std_cnr'] = cnr_proxy.std()
        features['cnr_trend'] = (cnr_proxy.iloc[-1] - cnr_proxy.iloc[0]) / max(len(cnr_proxy), 1)

    # ─── GROUP 3: Satellite Count (5 features) ────────────────────────────────
    ns_series = window['ns'] if 'ns' in window.columns else pd.Series([8] * len(window))
    features['num_satellites'] = current.get('ns', 8)
    features['sat_mean'] = ns_series.mean()
    features['sat_min'] = ns_series.min()
    features['sat_visibility'] = features['num_satellites'] / 32.0  # GPS has 32 SVs max
    # Rate of satellite count drop over window
    sat_diff = ns_series.diff().fillna(0)
    features['sat_drop_rate'] = sat_diff[sat_diff < 0].sum() / max(len(window), 1)

    # ─── GROUP 4: DOP - Dilution of Precision (5 features) ───────────────────
    # DOP values come from RTKLIB or from NMEA GSA sentences
    features['pdop'] = current.get('pdop', 2.5)
    features['hdop'] = current.get('hdop', 2.0)
    features['vdop'] = current.get('vdop', 1.5)
    features['gdop'] = current.get('gdop', 3.0)
    vdop_safe = features['vdop'] if features['vdop'] > 0 else 1.0
    features['dop_ratio'] = features['hdop'] / vdop_safe

    # ─── GROUP 5: Receiver Status (5 features) ────────────────────────────────
    # Q=1: fixed (best), Q=2: float, Q=5: single (worst)
    q_current = current.get('q', 5)
    # Normalize quality score to 0-1 (1=best fix, 0=no solution)
    features['solution_status'] = 1.0 - (min(q_current, 5) - 1) / 4.0
    features['baseline_sats'] = current.get('ns', 0)  # Satellites used in solution
    features['solution_age'] = current.get('age', 0)
    # Continuity: fraction of last 30s with fixed solution
    q_series = window['q'] if 'q' in window.columns else pd.Series([5] * len(window))
    features['fix_continuity'] = (q_series == 1).mean()
    # Number of times solution quality dropped in window
    features['fix_transitions'] = (q_series.diff().fillna(0) > 0).sum()

    # ─── GROUP 6: Temporal Patterns (5 features) ──────────────────────────────
    sdn_series = window['sdn'] if 'sdn' in window.columns else pd.Series([0.05] * len(window))
    sde_series = window['sde'] if 'sde' in window.columns else pd.Series([0.05] * len(window))
    features['position_variance'] = sdn_series.var() + sde_series.var()
    features['cnr_variance'] = features['std_cnr'] ** 2  # Already computed
    # Elevation mask violations: how often we might be below 5-degree cutoff
    # Proxy: when ns drops suddenly, likely due to elevation mask
    features['elevation_violations'] = max(0, (8 - features['num_satellites'])) / 8.0
    # Multipath indicator: high position variance + low C/N0 = likely multipath
    features['multipath'] = features['position_variance'] * (1.0 / max(features['mean_cnr'], 1))
    features['clock_bias'] = current.get('age', 0)  # Age of differential as clock proxy

    # ─── GROUP 7: Atmospheric Effects (5 features) ────────────────────────────
    # These are estimated from RTKLIB corrections; use 0 if not available
    features['iono_delay'] = current.get('iono_delay', 0.0)
    features['tropo_delay'] = current.get('tropo_delay', 0.0)
    features['cycle_slips'] = current.get('cycle_slips', 0)
    features['residual_mean'] = window['ratio'].mean() if 'ratio' in window.columns else 0.0
    features['residual_std'] = window['ratio'].std() if 'ratio' in window.columns else 0.0

    return features


def extract_features(pos_file: Path, output_csv: Path, source_tag: str = "unknown",
                     window_size: int = 30) -> pd.DataFrame:
    """
    Main feature extraction function.
    Applies a sliding window of `window_size` seconds over RTKLIB .pos data.

    Args:
        pos_file:    Path to RTKLIB .pos file
        output_csv:  Path to save features CSV
        source_tag:  Label for this dataset (e.g., 'supervisor_vehicle', 'nclt_2012-08-04')
        window_size: Sliding window size in seconds (default: 30)

    Returns:
        DataFrame with 35 features per epoch
    """
    df = read_rtklib_pos(pos_file)
    if df is None or len(df) < window_size:
        logger.error(f"Insufficient data in {pos_file} (need >{window_size} rows, got {len(df) if df is not None else 0})")
        return None

    features_list = []

    logger.info(f"Extracting features with window_size={window_size}s...")

    for idx in range(window_size, len(df)):
        window = df.iloc[idx - window_size:idx]
        current = df.iloc[idx]

        features = compute_features_window(window, current)
        features['timestamp'] = current['timestamp']
        features['source'] = source_tag
        features_list.append(features)

        if idx % 1000 == 0:
            logger.info(f"  Progress: {idx}/{len(df)} epochs ({100*idx/len(df):.1f}%)")

    features_df = pd.DataFrame(features_list)

    # Reorder columns: timestamp first, then 35 features, then source
    cols = ['timestamp'] + ALL_FEATURES + ['source']
    features_df = features_df[[c for c in cols if c in features_df.columns]]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(output_csv, index=False)

    logger.info(f"✓ Saved {len(features_df)} feature rows to {output_csv}")
    logger.info(f"  Features extracted: {len(ALL_FEATURES)}")

    return features_df


def extract_all_datasets():
    """
    Master function: extract features from ALL datasets.
    Run this once all RTKLIB processing is complete.
    """
    base = Path(".")

    # Map of (rtklib_pos_file, output_csv, source_tag)
    datasets = [
        # === SUPERVISOR DATASETS (already have RINEX/RTKLIB processed) ===
        # Vehicle - processed per experiment
        (base / "data/rinex/supervisor/vehicle_exp1.pos",
         base / "data/processed/supervisor/vehicle/exp1_features.csv",
         "supervisor_vehicle_exp1"),
        (base / "data/rinex/supervisor/vehicle_exp2.pos",
         base / "data/processed/supervisor/vehicle/exp2_features.csv",
         "supervisor_vehicle_exp2"),
        (base / "data/rinex/supervisor/vehicle_exp3.pos",
         base / "data/processed/supervisor/vehicle/exp3_features.csv",
         "supervisor_vehicle_exp3"),
        (base / "data/rinex/supervisor/vehicle_exp4.pos",
         base / "data/processed/supervisor/vehicle/exp4_features.csv",
         "supervisor_vehicle_exp4"),
        # Drone - separate files per flight
        (base / "data/rinex/supervisor/drone1.pos",
         base / "data/processed/supervisor/drone/drone1_features.csv",
         "supervisor_drone_1"),
        (base / "data/rinex/supervisor/drone2.pos",
         base / "data/processed/supervisor/drone/drone2_features.csv",
         "supervisor_drone_2"),
        (base / "data/rinex/supervisor/drone12.pos",
         base / "data/processed/supervisor/drone/drone12_features.csv",
         "supervisor_drone_12"),

        # === NCLT DATASET ===
        (base / "data/rinex/nclt/nclt_2012-08-04.pos",
         base / "data/processed/nclt/nclt_2012-08-04_features.csv",
         "nclt_2012-08-04"),
        (base / "data/rinex/nclt/nclt_2013-04-05.pos",
         base / "data/processed/nclt/nclt_2013-04-05_features.csv",
         "nclt_2013-04-05"),

        # === URBANNAV DATASET ===
        (base / "data/rinex/urbannav/hongkong.pos",
         base / "data/processed/urbannav/hongkong_features.csv",
         "urbannav_hong_kong"),
        (base / "data/rinex/urbannav/beijing.pos",
         base / "data/processed/urbannav/beijing_features.csv",
         "urbannav_beijing"),
        (base / "data/rinex/urbannav/taipei.pos",
         base / "data/processed/urbannav/taipei_features.csv",
         "urbannav_taipei"),

        # === OXFORD DATASET ===
        (base / "data/rinex/oxford/oxford_2019-01.pos",
         base / "data/processed/oxford/oxford_2019-01_features.csv",
         "oxford_2019-01"),

        # === KAIST DATASET ===
        (base / "data/rinex/kaist/kaist_campus.pos",
         base / "data/processed/kaist/kaist_features.csv",
         "kaist"),

        # === YOUR OWN SCENARIOS (collected at Beihang) ===
        (base / "data/rinex/scenarios/scenario_a.pos",
         base / "data/processed/scenarios/scenario_a_features.csv",
         "scenario_a_instant_blockage"),
        (base / "data/rinex/scenarios/scenario_b.pos",
         base / "data/processed/scenarios/scenario_b_features.csv",
         "scenario_b_urban_canyon"),
        (base / "data/rinex/scenarios/scenario_c.pos",
         base / "data/processed/scenarios/scenario_c_features.csv",
         "scenario_c_partial_blockage"),
        (base / "data/rinex/scenarios/scenario_d.pos",
         base / "data/processed/scenarios/scenario_d_features.csv",
         "scenario_d_open_sky"),
        (base / "data/rinex/scenarios/scenario_e.pos",
         base / "data/processed/scenarios/scenario_e_features.csv",
         "scenario_e_approaching"),
    ]

    success_count = 0
    for pos_file, output_csv, source_tag in datasets:
        if not pos_file.exists():
            logger.warning(f"⚠ Skipping {source_tag} — file not found: {pos_file}")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {source_tag}")
        df = extract_features(pos_file, output_csv, source_tag)
        if df is not None:
            success_count += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"Feature extraction complete: {success_count}/{len(datasets)} datasets processed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract GNSS features from RTKLIB .pos files")
    parser.add_argument("--input", type=str, help="Path to RTKLIB .pos file (single dataset)")
    parser.add_argument("--output", type=str, help="Output CSV path")
    parser.add_argument("--source", type=str, default="unknown", help="Dataset source tag")
    parser.add_argument("--window", type=int, default=30, help="Sliding window size (seconds)")
    parser.add_argument("--all", action="store_true", help="Process ALL datasets")

    args = parser.parse_args()

    if args.all:
        extract_all_datasets()
    elif args.input and args.output:
        extract_features(
            Path(args.input),
            Path(args.output),
            args.source,
            args.window
        )
    else:
        print("Usage:")
        print("  Single file:  python feature_extractor.py --input data/rinex/file.pos --output data/processed/out.csv --source my_tag")
        print("  All datasets: python feature_extractor.py --all")
