"""
GNSS Quality Labeler
====================
Labels GPS feature data as CLEAN / WARNING / DEGRADED.

This is one of the most critical steps — without correct labels,
the AI model cannot learn. Labels are derived from:
  - Position accuracy (from RTKLIB standard deviation, sdn/sde)
  - Signal strength (C/N0, or proxy)
  - Satellite count
  - Solution quality flag Q from RTKLIB

Labeling Rules:
    CLEAN:    pos_error_2D < 2.0 m AND mean_cnr > 35 dB-Hz AND ns >= 6
    WARNING:  pos_error_2D 2.0-5.0 m OR mean_cnr 30-35 dB-Hz OR ns 4-5
    DEGRADED: pos_error_2D > 5.0 m OR mean_cnr < 30 dB-Hz OR ns < 4

Usage:
    python labeler.py --input data/processed/supervisor/vehicle/exp1_features.csv
                      --output data/labelled/vehicle_exp1_labelled.csv
    
    python labeler.py --all   # Label everything in data/processed/
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── LABELING THRESHOLDS ──────────────────────────────────────────────────────
# Adjust these based on your GPS receiver specifications and application needs

THRESHOLDS = {
    # Position error thresholds (meters, 2D horizontal)
    "clean_pos_error":   2.0,   # Below this → CLEAN
    "warning_pos_error": 5.0,   # Below this → WARNING (above = DEGRADED)

    # Signal strength / C/N0 thresholds (dB-Hz)
    "clean_cnr":   35.0,   # Above this → CLEAN
    "warning_cnr": 30.0,   # Above this → WARNING (below = DEGRADED)

    # Satellite count thresholds
    "clean_ns":   6,    # At least this many → CLEAN
    "warning_ns": 4,    # At least this many → WARNING (below = DEGRADED)

    # RTKLIB quality flag
    # Q=1 fix → CLEAN candidate
    # Q=2 float → WARNING candidate
    # Q=5 single → DEGRADED
    "clean_q":   1,    # Fixed solution
    "warning_q": 2,    # Float solution
}


def label_epoch(row: pd.Series) -> str:
    """
    Determine GPS quality label for a single epoch.

    Decision logic:
    1. Compute position error from RTKLIB standard deviations
    2. Apply tiered thresholds to assign CLEAN/WARNING/DEGRADED
    3. Any single DEGRADED criterion → DEGRADED label
    4. Any WARNING criterion (no DEGRADED) → WARNING
    5. All CLEAN criteria → CLEAN

    Returns: str 'CLEAN', 'WARNING', or 'DEGRADED'
    """
    # --- Compute 2D position error (horizontal) ---
    lat_std = row.get('lat_std', 0.05)
    lon_std = row.get('lon_std', 0.05)
    pos_error_2d = np.sqrt(lat_std**2 + lon_std**2)

    # --- Get signal strength ---
    mean_cnr = row.get('mean_cnr', 35.0)

    # --- Get satellite count ---
    num_sats = row.get('num_satellites', 8)

    # --- Get fix quality ---
    sol_status = row.get('solution_status', 0.5)
    # sol_status: 1.0=fix, ~0.75=float, ~0.0=single (normalized)
    fix_continuity = row.get('fix_continuity', 0.5)

    # ─── DEGRADED: ANY of these conditions ────────────────────────────────────
    degraded = (
        pos_error_2d > THRESHOLDS["warning_pos_error"] or   # > 5m error
        mean_cnr < THRESHOLDS["warning_cnr"] or             # < 30 dB-Hz signal
        num_sats < THRESHOLDS["warning_ns"] or              # < 4 satellites
        sol_status < 0.25 or                                # Mostly single solution
        fix_continuity < 0.1                                # Rarely fixed in last 30s
    )
    if degraded:
        return 'DEGRADED'

    # ─── CLEAN: ALL of these conditions ──────────────────────────────────────
    clean = (
        pos_error_2d < THRESHOLDS["clean_pos_error"] and    # < 2m error
        mean_cnr > THRESHOLDS["clean_cnr"] and              # > 35 dB-Hz signal
        num_sats >= THRESHOLDS["clean_ns"] and              # >= 6 satellites
        sol_status >= 0.75 and                              # Mostly fixed solution
        fix_continuity >= 0.7                               # Fixed > 70% of last 30s
    )
    if clean:
        return 'CLEAN'

    # ─── WARNING: Everything in between ──────────────────────────────────────
    return 'WARNING'


def label_dataset(input_csv: Path, output_csv: Path) -> pd.DataFrame:
    """
    Load feature CSV, apply labels, and save.

    Args:
        input_csv:  Path to features CSV (output from feature_extractor.py)
        output_csv: Path to save labelled CSV

    Returns:
        DataFrame with 'label' column added
    """
    logger.info(f"Labeling: {input_csv.name}")

    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        logger.error(f"Cannot read {input_csv}: {e}")
        return None

    if len(df) == 0:
        logger.warning(f"Empty file: {input_csv}")
        return None

    # Apply labels row by row
    df['label'] = df.apply(label_epoch, axis=1)

    # ─── Label statistics ─────────────────────────────────────────────────────
    label_counts = df['label'].value_counts()
    label_pct = df['label'].value_counts(normalize=True) * 100

    logger.info(f"  Labels assigned: {len(df)} epochs")
    for lbl in ['CLEAN', 'WARNING', 'DEGRADED']:
        count = label_counts.get(lbl, 0)
        pct = label_pct.get(lbl, 0.0)
        logger.info(f"    {lbl:8s}: {count:6d} ({pct:5.1f}%)")

    # Warn if DEGRADED is very rare (< 5%) — SMOTE will be needed
    if label_pct.get('DEGRADED', 0) < 5.0:
        logger.warning(f"  ⚠ DEGRADED class is rare (<5%). SMOTE will be applied during training.")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    logger.info(f"  ✓ Saved to {output_csv}")

    return df


def label_all_datasets():
    """
    Label ALL feature CSVs in data/processed/ and save to data/labelled/.
    """
    processed_dir = Path("data/processed")
    labelled_dir = Path("data/labelled")
    labelled_dir.mkdir(parents=True, exist_ok=True)

    # Find all feature CSV files
    all_feature_files = list(processed_dir.rglob("*_features.csv"))

    if not all_feature_files:
        logger.error(f"No feature files found in {processed_dir}")
        logger.info("Run feature_extractor.py first!")
        return

    logger.info(f"Found {len(all_feature_files)} feature files to label")

    all_labelled = []
    for feat_file in all_feature_files:
        # Mirror the directory structure in labelled/
        relative_path = feat_file.relative_to(processed_dir)
        output_name = str(relative_path).replace("_features.csv", "_labelled.csv")
        output_csv = labelled_dir / output_name

        labelled_df = label_dataset(feat_file, output_csv)
        if labelled_df is not None:
            all_labelled.append(labelled_df)

    # ─── Assemble master dataset ───────────────────────────────────────────────
    if all_labelled:
        master_df = pd.concat(all_labelled, ignore_index=True)
        master_df = master_df.sort_values('timestamp').reset_index(drop=True)

        master_path = labelled_dir / "master_dataset.csv"
        master_df.to_csv(master_path, index=False)

        logger.info(f"\n{'='*60}")
        logger.info(f"MASTER DATASET ASSEMBLED")
        logger.info(f"  Total epochs:   {len(master_df):,}")
        logger.info(f"  Total features: {master_df.shape[1] - 2}")  # minus timestamp + label

        label_counts = master_df['label'].value_counts()
        for lbl in ['CLEAN', 'WARNING', 'DEGRADED']:
            count = label_counts.get(lbl, 0)
            pct = 100 * count / len(master_df)
            logger.info(f"  {lbl:8s}: {count:8,} ({pct:.1f}%)")

        logger.info(f"\nSaved master dataset to: {master_path}")
        logger.info("Next step: Run train_val_test_split.py")

        return master_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label GNSS features as CLEAN/WARNING/DEGRADED")
    parser.add_argument("--input", type=str, help="Single feature CSV to label")
    parser.add_argument("--output", type=str, help="Output labelled CSV path")
    parser.add_argument("--all", action="store_true", help="Label ALL datasets and create master CSV")

    args = parser.parse_args()

    if args.all:
        label_all_datasets()
    elif args.input and args.output:
        label_dataset(Path(args.input), Path(args.output))
    else:
        print("Usage:")
        print("  Single file: python labeler.py --input data/processed/vehicle_features.csv --output data/labelled/vehicle_labelled.csv")
        print("  All files:   python labeler.py --all")
