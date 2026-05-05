"""
Master Data Pipeline — SENTINEL-GNSS Project
=============================================
Runs the full data processing pipeline from raw files to labelled training data.

PIPELINE OVERVIEW:
─────────────────────────────────────────────────────────────────────────────────

  RAW DATA                     RTKLIB               FEATURES           LABELLED
  ─────────                    ───────              ────────           ────────
  Our collection (.sbf/.25O) ──┐
  Supervisor vehicle (.25O)  ──┼── rnx2rtkp.exe ──► .pos files ──────► features.csv
  Supervisor drone   (.24o)  ──┘                                         │
                                                                          │ labeler.py
  UrbanNav  (.obs/.nmea) ────────── parse_gnss ──► features.csv ──────►  ▼
  NCLT      (gps_rtk.csv) ───────── nclt_processor ──► features.csv    labelled.csv
  Oxford    (ins.csv/gps.csv) ───── oxford_processor ─► features.csv     │
                                                                          │
                                                                          ▼
                                                                     dataset_assembler.py
                                                                          │
                                                                          ▼
                                                                    train/val/test split
                                                                          │
                                                                          ▼
                                                                       MODEL

─────────────────────────────────────────────────────────────────────────────────
RTKLIB .pos file explained:
  RTKLIB takes RINEX observation files and outputs a .pos solution file.
  The .pos file is a plain-text CSV-like file with one row per GNSS epoch.
  Columns: GPST (date+time), lat, lon, height, Q, ns, sdn, sde, sdu, sdne, sdeu, sdun, age, ratio
  Q codes:  1 = Fixed RTK (cm accuracy, best)
            2 = Float RTK (10–30 cm)
            3 = SBAS (1–3 m)
            4 = DGPS (1–3 m)
            5 = Single (3–10 m, no correction)
            6 = PPP (cm, needs precise products)
  Q and ns (satellite count) are the most important columns for our feature extraction.
  The sdn/sde/sdu columns give the uncertainty in each axis — also key features.

USAGE:
  python src/processing/pipeline.py --all
  python src/processing/pipeline.py --dataset our_collection
  python src/processing/pipeline.py --dataset nclt
  python src/processing/pipeline.py --dataset urbannav
  python src/processing/pipeline.py --dataset oxford
  python src/processing/pipeline.py --dataset supervisor
  python src/processing/pipeline.py --features-only   # Skip RTKLIB, just extract features
  python src/processing/pipeline.py --assemble        # Only run dataset assembler
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def run_script(script_relative: str, *extra_args: str) -> bool:
    """Run a Python script relative to project root."""
    script_path = PROJECT_ROOT / script_relative
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False
    cmd = [PYTHON, str(script_path)] + list(extra_args)
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode == 0


# ─── STEP 1: RTKLIB POST-PROCESSING ──────────────────────────────────────────

def step_rtklib_our_collection() -> bool:
    logger.info("=== STEP 1a: RTKLIB — Our Collection (Septentrio) ===")
    return run_script("src/processing/our_collection_processor.py", "--all")


def step_rtklib_supervisor() -> bool:
    logger.info("=== STEP 1b: RTKLIB — Supervisor Vehicle + Drone ===")
    return run_script("src/rtklib/rtklib_pipeline.py", "--dataset", "vehicle") and \
        run_script("src/rtklib/rtklib_pipeline.py", "--dataset", "drone")


# ─── STEP 2: DATASET-SPECIFIC EXTRACTION ─────────────────────────────────────

def step_extract_nclt() -> bool:
    logger.info("=== STEP 2a: Extract NCLT GPS ===")
    return run_script("src/processing/nclt_processor.py")


def step_extract_oxford() -> bool:
    logger.info("=== STEP 2b: Extract Oxford RobotCar GPS ===")
    return run_script("src/processing/oxford_processor.py")


def step_extract_urbannav() -> bool:
    logger.info("=== STEP 2c: Extract UrbanNav RINEX+NMEA ===")
    return run_script("src/extraction/urbannav_extractor.py")


# ─── STEP 3: FEATURE EXTRACTION ──────────────────────────────────────────────

def step_extract_features(dataset: str | None = None) -> bool:
    logger.info("=== STEP 3: Feature Extraction from .pos files ===")
    processed = PROJECT_ROOT / "data" / "processed"
    pos_files = list(processed.rglob("*.pos"))

    if not pos_files:
        logger.warning("No .pos files found. Run RTKLIB step first.")
        return False

    for pos_file in pos_files:
        if dataset and dataset not in str(pos_file):
            continue
        source = pos_file.parent.name
        out_csv = pos_file.with_suffix(".features.csv")
        logger.info(f"  Extracting features: {pos_file.name} → {out_csv.name}")
        run_script("src/features/feature_extractor.py",
                   "--input", str(pos_file),
                   "--output", str(out_csv),
                   "--source", source)
    return True


# ─── STEP 4: LABELLING ───────────────────────────────────────────────────────

def step_label() -> bool:
    logger.info("=== STEP 4: Label feature CSVs ===")
    return run_script("src/labeling/labeler.py")


# ─── STEP 5: ASSEMBLE TRAIN/VAL/TEST ─────────────────────────────────────────

def step_assemble() -> bool:
    logger.info("=== STEP 5: Assemble Final Dataset ===")
    return run_script("src/features/dataset_assembler.py", "--split", "temporal")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run_dataset(dataset: str) -> None:
    dataset = dataset.lower()
    if dataset in ("our_collection", "scenarios"):
        step_rtklib_our_collection()
        step_extract_features("our_collection")
        step_label()
    elif dataset == "supervisor":
        step_rtklib_supervisor()
        step_extract_features("supervisor")
    elif dataset == "nclt":
        step_extract_nclt()
    elif dataset == "oxford":
        step_extract_oxford()
    elif dataset == "urbannav":
        step_extract_urbannav()
    else:
        logger.error(f"Unknown dataset: {dataset}")
        logger.error(
            "Valid options: our_collection, supervisor, nclt, oxford, urbannav")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SENTINEL-GNSS master data pipeline")
    parser.add_argument("--all", action="store_true",
                        help="Run full pipeline for all datasets")
    parser.add_argument("--dataset", help="Process a specific dataset only")
    parser.add_argument("--features-only", action="store_true",
                        help="Only run feature extraction")
    parser.add_argument("--assemble", action="store_true",
                        help="Only run dataset assembler")
    args = parser.parse_args()

    if args.all:
        step_rtklib_our_collection()
        step_rtklib_supervisor()
        step_extract_nclt()
        step_extract_oxford()
        step_extract_urbannav()
        step_extract_features()
        step_label()
        step_assemble()
    elif args.dataset:
        run_dataset(args.dataset)
    elif args.features_only:
        step_extract_features()
    elif args.assemble:
        step_assemble()
    else:
        parser.print_help()
