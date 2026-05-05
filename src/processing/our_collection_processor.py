"""
Our Collection Processor — Septentrio High-Precision Receiver
=============================================================
Processes raw data collected by the team using the Septentrio receiver
for the 5 GNSS degradation scenarios (A–E).

Septentrio output formats (what the receiver gives you):
    .sbf   — Septentrio Binary Format  (raw, proprietary)
    .nmea  — NMEA 0183 sentences       (human-readable position stream)
    .25O   — RINEX 3 Observation file  (what RTKLIB needs for PPK processing)
    .25N   — RINEX Navigation (GPS)
    .25G   — RINEX Navigation (GLONASS)
    .25P   — RINEX Navigation (mixed)
    .25L   — RINEX Navigation (Galileo)
    .25I   — RINEX Navigation (BeiDou)
    .pos   — RTKLIB post-processed solution (output after running rtkpost.exe)

RTKLIB workflow for our data:
    Step 1. Convert SBF to RINEX if needed (rtkconv.exe)
            → Input:  log_0000.sbf
            → Output: *.25O, *.25N, *.25G, *.25P  (same info, RINEX format)
            Note: If receiver already outputs RINEX (.25O), skip this step.

    Step 2. Run post-processing (rnx2rtkp.exe or rtkpost GUI)
            → Input:  rover.25O  (our moving receiver)
                      base.25O   (stationary reference, if available)
                      nav.25N / .25G / .25P
            → Config: config/rtkpost_kinematic.conf
            → Output: solution.pos

    RTKLIB .pos file format (what you get):
    ─────────────────────────────────────────────────────────────────────────
    % GPST                   latitude(deg) longitude(deg)  height(m)  Q  ns
    % Q: 1=Fixed RTK  2=Float RTK  3=SBAS  4=DGPS  5=Single  6=PPP
    2025/05/05 08:32:10.000   39.921234  116.402987  52.341  1  12
    ...
    ─────────────────────────────────────────────────────────────────────────
    Q=1 (Fixed) is the best quality. Q=5 (Single) is GPS-only, no RTK.
    ns = number of satellites used.
    Additional columns: sdn/sde/sdu (std dev north/east/up in metres),
                        age (differential age), ratio (AR ratio test).

    Step 3. Extract features from .pos file
            → Input:  solution.pos
            → Script: src/features/feature_extractor.py
            → Output: data/processed/our_collection/<scenario>_features.csv

    Step 4. Label the features
            → Script: src/labeling/labeler.py
            → Output: data/labelled/<scenario>_labelled.csv

Pipeline orchestration:
    python src/processing/our_collection_processor.py --scenario A
    python src/processing/our_collection_processor.py --all
"""

import subprocess
import logging
import argparse
from pathlib import Path
import sys
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RTKLIB_BIN = Path(r"C:\Program Files\RTKLIB\bin")
RNX2RTKP = RTKLIB_BIN / "rnx2rtkp.exe"
RTKCONV = RTKLIB_BIN / "rtkconv.exe"

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "scenarios"
RINEX_DIR = PROJECT_ROOT / "data" / "rinex" / "our_collection"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "our_collection"
CONFIG_DIR = PROJECT_ROOT / "config"

# ─── SCENARIO DEFINITIONS ─────────────────────────────────────────────────────
SCENARIOS = {
    "A": "instant_blockage",
    "B": "urban_canyon",
    "C": "partial_blockage",
    "D": "open_sky",
    "E": "approaching_blockage",
}


def check_rtklib() -> bool:
    if not RNX2RTKP.exists():
        logger.error(f"RTKLIB not found at: {RTKLIB_BIN}")
        logger.error(
            "Install RTKLIB from: https://rtkexplorer.com/downloads/rtklib-code/")
        return False
    return True


def convert_sbf_to_rinex(sbf_file: Path, out_dir: Path) -> bool:
    """
    Convert Septentrio .sbf binary to RINEX using rtkconv.exe.
    Only needed if the receiver was set to record SBF rather than RINEX directly.
    If the receiver already produced .25O files, skip this step.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_rinex = out_dir / (sbf_file.stem + ".obs")

    logger.info(f"Converting {sbf_file.name} → RINEX ...")
    cmd = [str(RTKCONV), "-r", "6", "-o", str(out_rinex), str(sbf_file)]
    # -r 6 = Septentrio SBF format code in RTKLIB

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"rtkconv failed: {result.stderr}")
        return False

    logger.info(f"  → RINEX written to {out_rinex}")
    return True


def run_rtkpost(rover_obs: Path, base_obs: Path | None,
                nav_files: list[Path], out_pos: Path,
                config_file: Path | None = None) -> bool:
    """
    Run RTKLIB post-processing (rnx2rtkp.exe) to produce a .pos solution.

    rover_obs  : RINEX observation file from the moving Septentrio receiver
    base_obs   : RINEX observation from stationary base (None = single-point only)
    nav_files  : list of navigation files (.N, .G, .P, .L, .I)
    out_pos    : output .pos file path
    config_file: optional RTKPOST .conf file; if None uses sensible defaults

    Without a base station (base_obs=None), output will be Q=5 (Single) which
    gives ~3–5 m accuracy — adequate for scenario labelling but not RTK-grade.
    With a nearby base station, output is Q=1/2 (Fixed/Float) giving cm-accuracy.
    """
    out_pos.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(RNX2RTKP)]

    # Processing mode: -p 2 = kinematic (moving receiver)
    cmd += ["-p", "2"]

    # Output format: -o lat/lon/height
    cmd += ["-o", str(out_pos)]

    # Navigation files
    for nav in nav_files:
        cmd.append(str(nav))

    # Rover observation
    cmd.append(str(rover_obs))

    # Base observation (optional)
    if base_obs is not None:
        cmd.append(str(base_obs))
        logger.info("  Mode: PPK (rover + base) → expect Q=1 Fixed solutions")
    else:
        logger.warning(
            "  Mode: Single-point (no base) → Q=5 only, ~3–5 m accuracy")

    logger.info(f"Running rnx2rtkp: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"rnx2rtkp failed:\n{result.stderr}")
        return False

    logger.info(f"  → Solution written to {out_pos}")
    return True


def process_scenario(scenario_id: str) -> bool:
    """
    Full pipeline for one scenario:
      1. Locate RINEX files under data/raw/scenarios/scenario_X/X/
      2. Run RTKLIB post-processing for each run
      3. Write .pos files to data/processed/our_collection/
    Then feature_extractor.py picks up the .pos files.

    Actual folder layout (Septentrio MOSAIC-X5C, May 2026):
      data/raw/scenarios/
        scenario_a/A/
          SEPT1250.26O    ← rover observation (Run_1)
          SEPT1250.26N    ← GPS navigation
          SEPT1250.26G    ← GLONASS navigation
          A2/SEPT1250.26O ← repeat run 2
          A3/SEPT1250.26O ← repeat run 3
        scenario_b/B/   scenario_c/C/   scenario_d/D/
        scenario_a_to_e/  ← combined A→E run (E scenario runs are E2/, E3/ here)
    """
    scenario_name = SCENARIOS.get(scenario_id.upper())
    if not scenario_name:
        logger.error(
            f"Unknown scenario: {scenario_id}. Valid: {list(SCENARIOS.keys())}")
        return False

    scen_id = scenario_id.upper()

    # Primary scenario folder: scenarios/scenario_x/X/
    primary_dir = RAW_DIR / f"scenario_{scen_id.lower()}" / scen_id

    # For scenario E, the data is in scenario_a_to_e/E2, E3
    if scen_id == "E":
        primary_dir = RAW_DIR / "scenario_a_to_e"

    if not primary_dir.exists():
        logger.warning(
            f"No folder found for scenario {scen_id}: {primary_dir}")
        return False

    logger.info(f"Processing scenario {scen_id} from: {primary_dir}")

    # Collect all runs (root .26O + sub-run directories)
    obs_extensions = ["*.26O", "*.25O", "*.obs"]
    nav_extensions = ["*.26N", "*.25N", "*.26G", "*.25G",
                      "*.26P", "*.25P", "*.26L", "*.25L", "*.26I", "*.25I"]

    # Gather run directories: root + subdirs
    run_dirs = [primary_dir]
    for sub in sorted(primary_dir.iterdir()):
        if sub.is_dir():
            # For scenario E: only E2, E3 subdirs; for others: A2, A3, B2 etc.
            if scen_id == "E":
                if sub.name.upper().startswith("E"):
                    run_dirs.append(sub)
            else:
                run_dirs.append(sub)

    all_ok = True
    for run_dir in run_dirs:
        rover_obs_candidates = []
        for pat in obs_extensions:
            rover_obs_candidates += list(run_dir.glob(pat))
        if not rover_obs_candidates:
            continue  # skip empty subdirs

        rover_obs = rover_obs_candidates[0]
        run_label = run_dir.name if run_dir != primary_dir else "Run_1"

        nav_files = []
        for pat in nav_extensions:
            nav_files += list(run_dir.glob(pat))

        if not nav_files:
            logger.warning(
                f"  No nav files in {run_dir} — skipping {run_label}")
            continue

        base_obs = None
        base_candidates = list(run_dir.glob("base*.26O")) + \
            list(run_dir.glob("base*.obs"))
        if base_candidates:
            base_obs = base_candidates[0]
            logger.info(f"  [{run_label}] Base station: {base_obs.name}")
        else:
            logger.warning(
                f"  [{run_label}] No base station — single-point mode (Q=5).")

        out_pos = PROCESSED_DIR / \
            f"scenario_{scen_id}_{run_label}_solution.pos"
        ok = run_rtkpost(rover_obs, base_obs, nav_files, out_pos)
        all_ok = all_ok and ok

    return all_ok


def process_all() -> None:
    """Process all scenarios that have data available."""
    results = {}
    for scenario_id in SCENARIOS:
        logger.info(f"\n{'='*60}")
        logger.info(f"SCENARIO {scenario_id}: {SCENARIOS[scenario_id]}")
        logger.info(f"{'='*60}")
        success = process_scenario(scenario_id)
        results[scenario_id] = "OK" if success else "SKIPPED/FAILED"

    logger.info("\n" + "="*60)
    logger.info("PROCESSING SUMMARY")
    for scenario_id, status in results.items():
        logger.info(f"  Scenario {scenario_id}: {status}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process our Septentrio receiver collection through RTKLIB."
    )
    parser.add_argument("--scenario", help="Scenario ID (A, B, C, D, or E)")
    parser.add_argument("--all", action="store_true",
                        help="Process all scenarios")
    args = parser.parse_args()

    if not check_rtklib():
        sys.exit(1)

    if args.all:
        process_all()
    elif args.scenario:
        success = process_scenario(args.scenario)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
