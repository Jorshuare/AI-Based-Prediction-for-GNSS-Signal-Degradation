"""
Oxford RobotCar Dataset Processor — GPS/INS Only
=================================================
Oxford RobotCar Dataset.
Website: https://robotcar-dataset.robots.ox.ac.uk/

WHAT TO DOWNLOAD (GPS signal only — do NOT download radar/lidar/camera):
─────────────────────────────────────────────────────────────────────────────────
1. Register at: https://mrgdatashare.robots.ox.ac.uk/register/
2. Choose 2–3 traversals from: https://robotcar-dataset.robots.ox.ac.uk/datasets/
   Recommended traversals (small GPS files, diverse conditions):
     2015-02-10-11-58-05   — overcast, good GPS
     2015-08-12-15-04-18   — summer, clear sky
     2014-11-18-13-20-12   — winter, lower sun angle
3. For each traversal, download ONLY the GPS/INS sensor zip:
     Sensor name in downloader: "NovAtel GPS / INS"
     Zip file size: ~10–20 MB per traversal
4. Also download the ground truth RTK solution:
     https://robotcar-dataset.robots.ox.ac.uk/ground_truth
     File: rtk.csv (single file for all traversals)

WHERE TO PLACE THE FILES:
  data/raw/public/oxford/
    2015-02-10-11-58-05/
      gps/
        gps.csv          ← from NovAtel GPS / INS zip
      ins/
        ins.csv          ← from NovAtel GPS / INS zip
    2015-08-12-15-04-18/
      gps/
        gps.csv
      ...
    rtk.csv              ← ground truth (place at top level of oxford/)

Oxford gps.csv format:
  timestamp,northing,easting,altitude,latitude,longitude,roll,pitch,yaw
  (timestamp = microseconds since UNIX epoch)
  (latitude/longitude in degrees, altitude in metres)

Oxford ins.csv format (higher-frequency, IMU-fused):
  timestamp,ins_status,latitude,longitude,altitude,
  northing,easting,down,roll,pitch,yaw,
  vn,ve,vd,ax,ay,az,wx,wy,wz

RTKLIB is NOT needed for Oxford — positions are pre-computed by NovAtel.
This script standardises the CSV for the feature pipeline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DATA_ROOT = Path("data/raw/public/oxford")
OUTPUT_DIR = Path("data/processed/oxford")


def load_gps_csv(gps_file: Path) -> pd.DataFrame:
    """
    Load Oxford gps.csv.
    Standardises to: timestamp_s, latitude, longitude, altitude, source
    """
    df = pd.read_csv(gps_file)
    # Rename columns to standard names
    rename = {
        "timestamp": "timestamp_us",
        "latitude": "latitude",
        "longitude": "longitude",
        "altitude": "altitude",
    }
    df = df.rename(columns=rename)
    df["timestamp_s"] = df["timestamp_us"] / 1e6
    df["solution_quality"] = 2     # NovAtel INS-fused = Float/DGPS equivalent
    df["source"] = "oxford_gps"
    return df[["timestamp_s", "latitude", "longitude", "altitude",
               "solution_quality", "source"]]


def load_ins_csv(ins_file: Path) -> pd.DataFrame:
    """
    Load Oxford ins.csv (higher frequency, IMU-fused solution).
    Preferred over gps.csv because it includes orientation and velocity.
    """
    df = pd.read_csv(ins_file)
    df["timestamp_s"] = df["timestamp"] / 1e6
    df["solution_quality"] = 2    # INS-fused
    df["source"] = "oxford_ins"

    # Keep only position for now (extendable with velocity/attitude)
    out = df[["timestamp_s", "latitude", "longitude", "altitude",
              "solution_quality", "source"]].copy()
    return out


def process_run(run_dir: Path) -> pd.DataFrame | None:
    """Process one Oxford traversal. Prefers INS over GPS-only."""
    # Try INS first (higher quality and frequency)
    ins_file = run_dir / "ins" / "ins.csv"
    gps_file = run_dir / "gps" / "gps.csv"

    if ins_file.exists():
        logger.info(f"  {run_dir.name}: using INS/GPS-fused solution")
        df = load_ins_csv(ins_file)
    elif gps_file.exists():
        logger.info(f"  {run_dir.name}: using GPS-only solution")
        df = load_gps_csv(gps_file)
    else:
        logger.warning(
            f"  {run_dir.name}: no GPS or INS files found — skipping")
        logger.warning(f"  Expected: {ins_file} or {gps_file}")
        return None

    df["oxford_run"] = run_dir.name
    return df


def process_all() -> pd.DataFrame | None:
    """Process all Oxford traversals available under DATA_ROOT."""
    if not DATA_ROOT.exists() or not any(
        d for d in DATA_ROOT.iterdir() if d.is_dir()
    ):
        logger.warning(
            f"No Oxford data found at {DATA_ROOT}.\n"
            "Download instructions are at the top of this file.\n"
            "Place gps/ and ins/ folders under data/raw/public/oxford/<traversal_date>/"
        )
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_dfs = []

    # Find run directories (format: YYYY-MM-DD-HH-MM-SS)
    run_dirs = sorted(
        d for d in DATA_ROOT.iterdir()
        if d.is_dir() and len(d.name) >= 10 and d.name[4] == '-'
    )

    if not run_dirs:
        logger.warning("No Oxford run directories found. "
                       "Expected format: YYYY-MM-DD-HH-MM-SS/")
        return None

    for run_dir in run_dirs:
        df = process_run(run_dir)
        if df is not None:
            all_dfs.append(df)

    if not all_dfs:
        logger.error("No data extracted from any Oxford traversal.")
        return None

    combined = pd.concat(all_dfs, ignore_index=True).sort_values("timestamp_s")
    out_file = OUTPUT_DIR / "oxford_combined.csv"
    combined.to_csv(out_file, index=False)
    logger.info(f"Oxford combined: {len(combined):,} rows → {out_file}")
    return combined


if __name__ == "__main__":
    process_all()
