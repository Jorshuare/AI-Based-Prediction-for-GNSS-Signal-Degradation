"""
Dataset Assembler: Train / Validation / Test Split
===================================================
Combines all labelled feature CSVs into one master dataset,
then splits by TIME (not randomly) into 70/15/15.

Why time-based split?
    GPS data is sequential. If you randomly shuffle, you end up with
    "future" data in training and "past" data in testing — the AI cheats!
    Time-based split means: train on past, validate/test on future.
    This is the ONLY correct way to evaluate a time series model.

Split Strategy:
    By SOURCE:
        - Your scenarios (A-E): labelled training data (foundation)
        - Supervisor vehicle/drone: training + validation
        - UrbanNav (3 cities): hold-out validation test
        - NCLT: long-term stability test
        - Oxford: global generalization test
        - KAIST: temporal stability test (if available)

Usage:
    python dataset_assembler.py --split temporal  # Time-based split (default)
    python dataset_assembler.py --split source    # Split by dataset source
    python dataset_assembler.py --split both      # Both strategies
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging
import pickle
from sklearn.preprocessing import StandardScaler, LabelEncoder
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ─── FEATURE COLUMNS (35 features) ────────────────────────────────────────────
FEATURE_COLS = [
    # Position
    'lat', 'lon', 'alt', 'lat_std', 'lon_std',
    # Signal strength
    'mean_cnr', 'min_cnr', 'max_cnr', 'std_cnr', 'cnr_trend',
    # Satellite count
    'num_satellites', 'sat_mean', 'sat_min', 'sat_visibility', 'sat_drop_rate',
    # DOP
    'pdop', 'hdop', 'vdop', 'gdop', 'dop_ratio',
    # Receiver status
    'solution_status', 'baseline_sats', 'solution_age', 'fix_continuity', 'fix_transitions',
    # Temporal patterns
    'position_variance', 'cnr_variance', 'elevation_violations', 'multipath', 'clock_bias',
    # Atmospheric
    'iono_delay', 'tropo_delay', 'cycle_slips', 'residual_mean', 'residual_std',
]

# Datasets that are TRAINING data (not validation/test)
TRAINING_SOURCES = [
    'scenario_a', 'scenario_b', 'scenario_c', 'scenario_d', 'scenario_e',
    'supervisor_vehicle', 'supervisor_drone',
]

# Datasets reserved for generalization testing (not in training)
VALIDATION_SOURCES = ['nclt']
TEST_SOURCES = ['urbannav', 'oxford', 'kaist']


def load_master_dataset(master_csv: Path = Path("data/labelled/master_dataset.csv")) -> pd.DataFrame:
    """Load the master labelled dataset."""
    if not master_csv.exists():
        logger.error(f"Master dataset not found: {master_csv}")
        logger.info("Run labeler.py --all first!")
        return None

    df = pd.read_csv(master_csv)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.sort_values('timestamp').reset_index(drop=True)

    logger.info(f"Loaded master dataset: {len(df):,} rows")
    logger.info(f"Sources: {df['source'].value_counts().to_dict()}")
    logger.info(f"Labels:  {df['label'].value_counts().to_dict()}")

    return df


def temporal_split(df: pd.DataFrame, train_ratio=0.70, val_ratio=0.15) -> tuple:
    """
    Split dataset by TIME:
        First 70% → Training
        Next  15% → Validation
        Last  15% → Test

    The data is sorted by timestamp first, so this respects chronological order.
    """
    df = df.sort_values('timestamp').reset_index(drop=True)
    n = len(df)

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()

    logger.info("\n--- Temporal Split ---")
    for name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        pct = 100 * len(split_df) / n
        labels = split_df['label'].value_counts().to_dict()
        logger.info(f"  {name:5s}: {len(split_df):7,} rows ({pct:.1f}%) | Labels: {labels}")

    return train_df, val_df, test_df


def source_based_split(df: pd.DataFrame) -> tuple:
    """
    Split by DATASET SOURCE (geography-based generalization test):
        Training:   Your scenarios + Supervisor data
        Validation: NCLT
        Test:       UrbanNav + Oxford + KAIST
    """
    def source_group(source_str):
        src = str(source_str).lower()
        if any(s in src for s in TRAINING_SOURCES):
            return 'train'
        elif any(s in src for s in VALIDATION_SOURCES):
            return 'val'
        elif any(s in src for s in TEST_SOURCES):
            return 'test'
        else:
            return 'train'  # Default: use for training

    df['split_group'] = df['source'].apply(source_group)

    train_df = df[df['split_group'] == 'train'].copy()
    val_df = df[df['split_group'] == 'val'].copy()
    test_df = df[df['split_group'] == 'test'].copy()

    logger.info("\n--- Source-Based Split ---")
    for name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        sources = split_df['source'].value_counts().to_dict()
        labels = split_df['label'].value_counts().to_dict()
        logger.info(f"  {name:5s}: {len(split_df):7,} rows")
        logger.info(f"    Sources: {sources}")
        logger.info(f"    Labels:  {labels}")

    return train_df, val_df, test_df


def normalize_features(train_df: pd.DataFrame, val_df: pd.DataFrame,
                        test_df: pd.DataFrame, output_dir: Path) -> tuple:
    """
    Normalize features to zero mean, unit variance.

    CRITICAL: Fit the scaler ONLY on training data.
    Apply the same scaler to validation and test data.
    Never fit on validation or test — that would be data leakage!

    Saves scaler to results/scaler.pkl for use in real-time inference.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Only use columns that actually exist in the data
    available_features = [c for c in FEATURE_COLS if c in train_df.columns]
    logger.info(f"Normalizing {len(available_features)} features...")

    scaler = StandardScaler()

    # Fit on training ONLY
    train_df[available_features] = scaler.fit_transform(train_df[available_features].fillna(0))

    # Apply to val and test
    val_df[available_features] = scaler.transform(val_df[available_features].fillna(0))
    test_df[available_features] = scaler.transform(test_df[available_features].fillna(0))

    # Save scaler for inference
    scaler_path = output_dir / "scaler.pkl"
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    logger.info(f"  Scaler saved to {scaler_path}")

    # Also save feature column order (critical for inference)
    feature_info = {
        'feature_cols': available_features,
        'n_features': len(available_features),
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_std': scaler.scale_.tolist(),
    }
    import json
    with open(output_dir / "feature_info.json", 'w') as f:
        json.dump(feature_info, f, indent=2)

    return train_df, val_df, test_df, scaler


def save_splits(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame,
                output_dir: Path = Path("data/labelled"), prefix: str = ""):
    """Save train/val/test splits to CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    p = f"{prefix}_" if prefix else ""
    paths = {
        'train': output_dir / f"{p}train.csv",
        'val':   output_dir / f"{p}val.csv",
        'test':  output_dir / f"{p}test.csv",
    }

    for name, df, path in [("Train", train_df, paths['train']),
                             ("Val", val_df, paths['val']),
                             ("Test", test_df, paths['test'])]:
        df.to_csv(path, index=False)
        logger.info(f"  Saved {name}: {path} ({len(df):,} rows)")

    return paths


def apply_smote(train_df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """
    Apply SMOTE (Synthetic Minority Over-Sampling Technique) to balance classes.

    Problem: Typically CLEAN >> WARNING >> DEGRADED
    Solution: Generate synthetic DEGRADED/WARNING samples using SMOTE

    IMPORTANT: Apply SMOTE ONLY on training data, NEVER on val or test.
    Testing on oversampled data gives falsely optimistic results.
    """
    try:
        from imblearn.over_sampling import SMOTE
    except ImportError:
        logger.warning("imbalanced-learn not installed. Run: pip install imbalanced-learn")
        logger.warning("Skipping SMOTE — training on imbalanced data")
        return train_df

    available_features = [c for c in FEATURE_COLS if c in train_df.columns]
    X_train = train_df[available_features].fillna(0).values
    y_train = train_df['label'].values

    # Encode labels to integers
    le = LabelEncoder()
    y_encoded = le.fit_transform(y_train)

    # Save label encoder
    le_path = output_dir / "label_encoder.pkl"
    with open(le_path, 'wb') as f:
        pickle.dump(le, f)

    label_counts_before = Counter(y_train)
    logger.info(f"\nBefore SMOTE: {dict(label_counts_before)}")

    # Check if SMOTE is needed (minority class < 20% of majority)
    max_count = max(label_counts_before.values())
    min_count = min(label_counts_before.values())
    if min_count >= max_count * 0.5:
        logger.info("Classes are relatively balanced. Skipping SMOTE.")
        return train_df

    # Apply SMOTE
    smote = SMOTE(random_state=42, k_neighbors=min(5, min_count - 1))
    X_balanced, y_balanced = smote.fit_resample(X_train, y_encoded)
    y_balanced_decoded = le.inverse_transform(y_balanced)

    label_counts_after = Counter(y_balanced_decoded)
    logger.info(f"After SMOTE:  {dict(label_counts_after)}")

    train_balanced = pd.DataFrame(X_balanced, columns=available_features)
    train_balanced['label'] = y_balanced_decoded

    output_path = output_dir / "train_smote.csv"
    train_balanced.to_csv(output_path, index=False)
    logger.info(f"  SMOTE balanced training set saved to {output_path}")

    return train_balanced


def main():
    parser = argparse.ArgumentParser(description="Assemble and split the GNSS training dataset")
    parser.add_argument("--master", type=str, default="data/labelled/master_dataset.csv",
                        help="Path to master labelled dataset")
    parser.add_argument("--split", type=str, choices=["temporal", "source", "both"],
                        default="both", help="Split strategy")
    parser.add_argument("--output", type=str, default="data/labelled",
                        help="Output directory for splits")
    parser.add_argument("--smote", action="store_true",
                        help="Apply SMOTE to balance training classes")
    args = parser.parse_args()

    df = load_master_dataset(Path(args.master))
    if df is None:
        return

    output_dir = Path(args.output)
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    if args.split in ("temporal", "both"):
        logger.info("\n=== TEMPORAL SPLIT ===")
        train_df, val_df, test_df = temporal_split(df)
        train_df, val_df, test_df, scaler = normalize_features(train_df, val_df, test_df, results_dir)
        save_splits(train_df, val_df, test_df, output_dir, prefix="temporal")

        if args.smote:
            apply_smote(train_df, output_dir)

    if args.split in ("source", "both"):
        logger.info("\n=== SOURCE-BASED SPLIT ===")
        train_df2, val_df2, test_df2 = source_based_split(df)
        train_df2, val_df2, test_df2, _ = normalize_features(train_df2, val_df2, test_df2, results_dir)
        save_splits(train_df2, val_df2, test_df2, output_dir, prefix="source")

        if args.smote:
            apply_smote(train_df2, output_dir)

    logger.info("\n✓ Dataset assembly complete. Ready for model training.")
    logger.info("  Next step: Run src/models/train.py")


if __name__ == "__main__":
    main()
