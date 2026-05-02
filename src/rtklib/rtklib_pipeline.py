"""
RTKLIB Processing Pipeline for GNSS Signal Degradation Project
==============================================================
Automates RTKLIB processing for all datasets:
  1. Supervisor Vehicle (RINEX .25O observation files → .pos)
  2. Supervisor Drone (RINEX .24o files → .pos)
  3. NCLT Dataset (gps.csv → already has RTK solution, no processing needed)
  4. Your 5 Scenarios (RINEX from GPS receiver → .pos)

RTKLIB is installed at: C:\\Program Files\\RTKLIB\\bin\\

Key tools used:
    rtkconv.exe  - Convert NMEA/UBX to RINEX format
    rtkpost.exe  - Post-process RINEX with precise orbits for accuracy
    rtkplot.exe  - Visualize results (manual use)

Usage:
    python rtklib_pipeline.py --dataset vehicle   # Process supervisor vehicle
    python rtklib_pipeline.py --dataset drone     # Process supervisor drone  
    python rtklib_pipeline.py --dataset scenarios # Process your collected data
    python rtklib_pipeline.py --all               # Process everything

For RTKLIB GUI usage instructions, see: docs/RTKLIB_GUIDE.md
"""

import subprocess
import os
import shutil
from pathlib import Path
import logging
import argparse
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── RTKLIB CONFIGURATION ─────────────────────────────────────────────────────
RTKLIB_BIN = r"C:\Program Files\RTKLIB\bin"
RTKCONV = os.path.join(RTKLIB_BIN, "rtkconv.exe")
RTKPOST = os.path.join(RTKLIB_BIN, "rtkpost.exe")
RNX2RTKP = os.path.join(RTKLIB_BIN, "rnx2rtkp.exe")  # Command-line post-processor

# Base directory for the project
BASE_DIR = Path(".")
CONFIG_DIR = BASE_DIR / "config"


def check_rtklib_installed():
    """Verify RTKLIB is installed and accessible."""
    if not os.path.exists(RTKCONV):
        logger.error(f"rtkconv.exe not found at: {RTKCONV}")
        logger.error("Please verify RTKLIB is installed at C:\\Program Files\\RTKLIB\\")
        return False
    if not os.path.exists(RTKPOST):
        logger.error(f"rtkpost.exe not found at: {RTKPOST}")
        return False
    logger.info(f"✓ RTKLIB found at: {RTKLIB_BIN}")
    return True


def create_rtkpost_config(config_path: Path, mode: str = "kinematic"):
    """
    Create RTKPOST configuration file.

    mode:
        'kinematic' - for moving platforms (vehicle, drone)
        'static'    - for stationary receivers (base stations)
        'ppk'       - Post-Processed Kinematic (highest accuracy)
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config_content = f"""# RTKPOST Configuration File
# Generated for SENTINEL-GNSS Project
# Mode: {mode}

# =============================================================================
# POSITIONING OPTIONS
# =============================================================================
pos1-posmode       = {mode}     # Positioning mode: kinematic/static/fixed
pos1-frequency     = l1+2      # Use L1+L2 frequencies for better accuracy
pos1-soltype       = forward   # Forward solution (or combined for best)
pos1-elmask        = 5         # Elevation mask: ignore satellites below 5 degrees
pos1-snrmask_r     = 0         # SNR mask for rover (0=disabled)
pos1-snrmask_b     = 0         # SNR mask for base (0=disabled)
pos1-dynamics      = on        # Dynamics model on for moving platform
pos1-tidecorr      = off       # Tide correction (off for urban areas)
pos1-ionoopt       = iflc      # Ionosphere: Ionosphere-free LC (dual frequency)
pos1-tropopt       = saas      # Troposphere: Saastamoinen model
pos1-sateph        = brdc      # Satellite ephemeris: broadcast
pos1-exclsats      =           # No excluded satellites
pos1-navsys        = 7         # Navigation systems: GPS+GLONASS+Galileo (bitmask)

# =============================================================================
# FILTER OPTIONS (Kalman Filter tuning)
# =============================================================================
pos2-armode        = continuous  # Integer ambiguity resolution: continuous
pos2-gloarmode     = on          # GLONASS ambiguity resolution
pos2-bdsarmode     = on          # BeiDou ambiguity resolution
pos2-arelmask      = 15          # AR elevation mask
pos2-arthres       = 3.0         # AR threshold (ratio test)
pos2-arminfix      = 10          # Min epochs for fixed solution
pos2-armaxiter     = 1           # Max AR iterations
pos2-elmaskhold    = 0           # Hold elevation mask
pos2-aroutcnt      = 5           # AR outlier count
pos2-maxage        = 30          # Max age of differential corrections
pos2-syncsol       = off         # Synchronize solution
pos2-slipthres     = 0.05        # Cycle slip threshold
pos2-rejionno      = 30          # Reject ionosphere threshold
pos2-rejgdop       = 30          # Reject GDOP threshold
pos2-niter         = 1           # Number of iterations

# =============================================================================
# OUTPUT OPTIONS
# =============================================================================
out-solformat      = llh         # Output: lat/lon/height
out-outhead        = on          # Include header in output
out-outopt         = on          # Output solution options
out-outvel         = on          # Output velocity
out-timesys        = gpst        # Time system: GPS Time
out-timeform       = tow         # Time format: time-of-week
out-timendec       = 3           # 3 decimal places (millisecond)
out-degformat      = deg         # Degrees format
out-fieldsep       =             # Default field separator (space)
out-maxsolstd      = 0           # Max position std deviation (0=no limit)
out-maxage         = 30          # Max age for DGPS
out-maxpdop        = 100         # Max PDOP (100=no limit)
out-options        = on          # Extended options in output
"""

    with open(config_path, 'w') as f:
        f.write(config_content)

    logger.info(f"Created RTKLIB config: {config_path}")
    return config_path


def convert_nmea_to_rinex(nmea_file: Path, output_dir: Path) -> Path:
    """
    Convert NMEA file to RINEX observation format using rtkconv.exe.

    Args:
        nmea_file:  Path to .nmea file
        output_dir: Directory to save .obs RINEX file

    Returns:
        Path to generated .obs file, or None if failed
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    obs_file = output_dir / (nmea_file.stem + ".obs")

    cmd = [
        RTKCONV,
        "-format", "nmea",          # Input format: NMEA
        "-d", str(output_dir),       # Output directory
        str(nmea_file)
    ]

    logger.info(f"Converting NMEA to RINEX: {nmea_file.name}")
    logger.debug(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logger.info(f"  ✓ Converted: {obs_file.name}")
            return obs_file
        else:
            logger.error(f"  ✗ rtkconv failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        logger.error("  ✗ rtkconv timed out")
        return None
    except Exception as e:
        logger.error(f"  ✗ Error running rtkconv: {e}")
        return None


def convert_sbf_to_rinex(sbf_file: Path, output_dir: Path) -> Path:
    """
    Convert Septentrio Binary Format (.sbf) to RINEX.

    The supervisor vehicle data has .sbf files.
    RTKLIB can handle SBF format with convbin.exe.

    Note: For best results with SBF files, use Septentrio's own tool (SBF Converter)
    if available. convbin.exe in RTKLIB also supports SBF.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    convbin = os.path.join(RTKLIB_BIN, "convbin.exe")

    obs_file = output_dir / (sbf_file.stem + ".obs")

    cmd = [
        convbin,
        "-format", "sbf",      # Septentrio Binary Format
        "-d", str(output_dir),
        str(sbf_file)
    ]

    logger.info(f"Converting SBF to RINEX: {sbf_file.name}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            logger.info(f"  ✓ Converted: {obs_file.name}")
            return obs_file
        else:
            logger.error(f"  ✗ convbin failed: {result.stderr}")
            logger.info("  Tip: Try converting SBF to NMEA using Septentrio RxControl first")
            return None
    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return None


def run_rtkpost(obs_file: Path, nav_file: Path, base_obs: Path,
                output_pos: Path, config_file: Path) -> bool:
    """
    Run RTKPOST for high-accuracy post-processed positioning.

    For RTK (Real-Time Kinematic) accuracy (cm-level):
    - Need: rover observation file (.obs) + base station observation file
    - Base station: SEPT3463.25P or download from CORS network

    For PPP (Precise Point Positioning) accuracy (~dm level, no base needed):
    - Need: observation file + precise orbits (.sp3) + clock (.clk)
    - Download orbits: https://cddis.nasa.gov/archive/gnss/products/

    Args:
        obs_file:   Rover RINEX observation file
        nav_file:   Navigation file (use 'auto' to auto-download)
        base_obs:   Base station observation file (None for PPP mode)
        output_pos: Output .pos solution file
        config_file: RTKPOST configuration file

    Returns:
        bool: True if successful
    """
    output_pos.parent.mkdir(parents=True, exist_ok=True)

    cmd = [RTKPOST, "-k", str(config_file)]

    # Input files
    cmd += ["-in:obs", str(obs_file)]

    if base_obs and base_obs.exists():
        cmd += ["-in:obs", str(base_obs)]   # Second obs = base station

    if nav_file:
        if str(nav_file).lower() == 'auto':
            cmd += ["-in:nav", "auto"]       # Auto-download from CDDIS
        elif nav_file.exists():
            cmd += ["-in:nav", str(nav_file)]

    # Output
    cmd += ["-out", str(output_pos)]

    logger.info(f"Running RTKPOST: {obs_file.stem}")
    logger.debug(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0 and output_pos.exists():
            # Count lines in output (= number of solution epochs)
            with open(output_pos, 'r') as f:
                lines = [l for l in f if not l.startswith('%')]
            logger.info(f"  ✓ Solved: {len(lines)} epochs → {output_pos.name}")
            return True
        else:
            logger.error(f"  ✗ RTKPOST failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("  ✗ RTKPOST timed out (>10 min)")
        return False
    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return False


def process_supervisor_vehicle():
    """
    Process supervisor vehicle dataset.

    Data location: data/vehicle/exp1-4/
    Each experiment folder has:
        - *.nmea  : NMEA GPS data (parse directly)
        - *.sbf   : Septentrio binary (needs conversion)
        - *.25O   : RINEX observation (ready for RTKLIB)
        - *.25N, *.25G etc.: Navigation files

    Strategy: Use existing RINEX files (.25O) directly with RTKPOST
    """
    logger.info("\n=== Processing Supervisor Vehicle Dataset ===")
    vehicle_dir = BASE_DIR / "data/vehicle"
    rinex_dir = BASE_DIR / "data/rinex/supervisor/vehicle"
    rinex_dir.mkdir(parents=True, exist_ok=True)

    config_file = CONFIG_DIR / "rtkpost_vehicle.conf"
    create_rtkpost_config(config_file, mode="kinematic")

    # Base station file (shared reference for RTK)
    base_obs = None
    base_files = list(vehicle_dir.rglob("*base*.25O")) + list(vehicle_dir.rglob("*BASE*.25O"))
    if base_files:
        base_obs = base_files[0]
        logger.info(f"  Using base station: {base_obs.name}")

    for exp_num in range(1, 5):
        exp_dir = vehicle_dir / f"exp{exp_num}"
        if not exp_dir.exists():
            logger.warning(f"  Experiment {exp_num} directory not found")
            continue

        logger.info(f"\n  Processing Vehicle Experiment {exp_num}...")

        # Look through all base station folders in this experiment
        for base_dir in exp_dir.iterdir():
            if not base_dir.is_dir():
                continue

            # Find RINEX observation files (.25O, .24O, etc.)
            rinex_obs_files = (
                list(base_dir.glob("*.[0-9][0-9]O")) +
                list(base_dir.glob("*.[0-9][0-9]o"))
            )

            if not rinex_obs_files:
                # Try to convert NMEA to RINEX first
                nmea_files = list(base_dir.glob("*.nmea"))
                if nmea_files:
                    logger.info(f"    Converting NMEA: {nmea_files[0].name}")
                    obs_file = convert_nmea_to_rinex(nmea_files[0], rinex_dir)
                    if obs_file:
                        rinex_obs_files = [obs_file]
                else:
                    # Try SBF conversion
                    sbf_files = list(base_dir.glob("*.sbf"))
                    if sbf_files:
                        obs_file = convert_sbf_to_rinex(sbf_files[0], rinex_dir)
                        if obs_file:
                            rinex_obs_files = [obs_file]

            for obs_file in rinex_obs_files:
                # Find matching navigation file
                nav_patterns = ["*.25N", "*.24N", "*.25G", "*.24G"]
                nav_file = None
                for pattern in nav_patterns:
                    nav_files = list(base_dir.glob(pattern))
                    if nav_files:
                        nav_file = nav_files[0]
                        break

                output_pos = rinex_dir / f"vehicle_exp{exp_num}_{base_dir.name}.pos"

                run_rtkpost(
                    obs_file=obs_file if obs_file.exists() else Path(obs_file),
                    nav_file=nav_file if nav_file else Path("auto"),
                    base_obs=base_obs,
                    output_pos=output_pos,
                    config_file=config_file
                )


def process_supervisor_drone():
    """
    Process supervisor drone dataset.

    Data location: data/drone/
    Files:
        - drone1_241h.24o, drone2_241h.24o, drone12_241h.24o (RINEX observations)
        - base2410.24o (base station reference)

    Strategy: Use RINEX files directly, with base station for RTK accuracy.
    """
    logger.info("\n=== Processing Supervisor Drone Dataset ===")
    drone_dir = BASE_DIR / "data/drone"
    rinex_dir = BASE_DIR / "data/rinex/supervisor/drone"
    rinex_dir.mkdir(parents=True, exist_ok=True)

    config_file = CONFIG_DIR / "rtkpost_drone.conf"
    create_rtkpost_config(config_file, mode="kinematic")

    # Find base station file
    base_obs_files = list(drone_dir.glob("base*.24o")) + list(drone_dir.glob("*base*.24o"))
    base_obs = base_obs_files[0] if base_obs_files else None
    if base_obs:
        logger.info(f"  Base station: {base_obs.name}")
    else:
        logger.warning("  No base station file found — will use auto nav download")

    # Find drone observation files
    drone_obs_files = [f for f in drone_dir.glob("drone*.24o")]
    drone_obs_files.sort()

    logger.info(f"  Found {len(drone_obs_files)} drone observation files")

    for obs_file in drone_obs_files:
        output_pos = rinex_dir / (obs_file.stem + "_solution.pos")

        run_rtkpost(
            obs_file=obs_file,
            nav_file=None,        # Will use auto
            base_obs=base_obs,
            output_pos=output_pos,
            config_file=config_file
        )


def process_scenarios():
    """
    Process your 5 collected scenarios (A-E).

    Data location: data/raw/scenarios/
    Each scenario subfolder contains the RINEX files from your GPS receiver.

    Strategy: Same as vehicle — use RINEX obs + nav with RTKPOST.
    """
    logger.info("\n=== Processing Your 5 Scenarios ===")
    scenarios_dir = BASE_DIR / "data/raw/scenarios"
    rinex_dir = BASE_DIR / "data/rinex/scenarios"

    config_file = CONFIG_DIR / "rtkpost_scenarios.conf"
    create_rtkpost_config(config_file, mode="kinematic")

    scenario_labels = {
        'scenario_a': 'Instant Blockage',
        'scenario_b': 'Urban Canyon',
        'scenario_c': 'Partial Blockage',
        'scenario_d': 'Open Sky (Baseline)',
        'scenario_e': 'Approaching Blockage',
    }

    for scenario_name, scenario_label in scenario_labels.items():
        scenario_dir = scenarios_dir / scenario_name
        if not scenario_dir.exists():
            logger.warning(f"  {scenario_name} not found — collect data first!")
            continue

        logger.info(f"\n  Processing {scenario_name}: {scenario_label}")
        out_dir = rinex_dir / scenario_name
        out_dir.mkdir(parents=True, exist_ok=True)

        # Find RINEX observation files
        obs_files = list(scenario_dir.glob("*.[0-9][0-9]O")) + \
                    list(scenario_dir.glob("*.[0-9][0-9]o")) + \
                    list(scenario_dir.glob("*.obs"))

        if not obs_files:
            # Try NMEA conversion
            nmea_files = list(scenario_dir.glob("*.nmea"))
            for nmea_file in nmea_files:
                obs_file = convert_nmea_to_rinex(nmea_file, out_dir)
                if obs_file:
                    obs_files.append(obs_file)

        for i, obs_file in enumerate(obs_files):
            output_pos = out_dir / f"{scenario_name}_run{i+1}.pos"
            run_rtkpost(
                obs_file=obs_file,
                nav_file=Path("auto"),  # Auto-download navigation data
                base_obs=None,
                output_pos=output_pos,
                config_file=config_file
            )


def process_nclt():
    """
    Process NCLT dataset.

    NCLT already provides gps.csv and gps_rtk.csv — NO RTKLIB NEEDED!
    The RTK solution is already computed by the NCLT team.

    We just need to confirm the data is usable.
    """
    logger.info("\n=== NCLT Dataset — Already Processed (No RTKLIB Needed) ===")
    nclt_dir = BASE_DIR / "data/NCLT_data"

    for date_dir in sorted(nclt_dir.iterdir()):
        if not date_dir.is_dir():
            continue

        gps_rtk = date_dir / "gps_rtk.csv"
        gps_raw = date_dir / "gps.csv"

        if gps_rtk.exists():
            logger.info(f"  ✓ {date_dir.name}: RTK solution found ({gps_rtk.stat().st_size/1024/1024:.1f} MB)")
        elif gps_raw.exists():
            logger.info(f"  ℹ {date_dir.name}: Only raw GPS found (no RTK)")
        else:
            logger.warning(f"  ✗ {date_dir.name}: No GPS data found")

    logger.info("  NCLT is ready for feature extraction. Run nclt_extractor.py")


def main():
    parser = argparse.ArgumentParser(description="RTKLIB processing pipeline for all datasets")
    parser.add_argument("--dataset", type=str,
                        choices=["vehicle", "drone", "scenarios", "nclt", "all"],
                        help="Which dataset to process")
    parser.add_argument("--all", action="store_true", help="Process all datasets")

    args = parser.parse_args()

    if not check_rtklib_installed():
        return

    CONFIG_DIR.mkdir(exist_ok=True)

    if args.all or args.dataset == "vehicle":
        process_supervisor_vehicle()
    if args.all or args.dataset == "drone":
        process_supervisor_drone()
    if args.all or args.dataset == "scenarios":
        process_scenarios()
    if args.all or args.dataset == "nclt":
        process_nclt()

    if not (args.all or args.dataset):
        parser.print_help()
        print("\nQuick start:")
        print("  python rtklib_pipeline.py --dataset vehicle")
        print("  python rtklib_pipeline.py --all")


if __name__ == "__main__":
    main()
