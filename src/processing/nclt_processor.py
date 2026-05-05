"""
NCLT Dataset Processor — GPS-Only Extraction
=============================================
University of Michigan North Campus Long-Term (NCLT) dataset.
Website: https://robots.engin.umich.edu/nclt/

WHAT TO DOWNLOAD FROM NCLT (GPS signal only — do NOT download full sensor data):
─────────────────────────────────────────────────────────────────────────────────
For each collection date you want, download ONLY:
  File name pattern : <date>_sen.tar.gz  (sensor data archive)
  Inside the tar.gz : hms/gps.csv        ← raw GPS
                      hms/gps_rtk.csv    ← high-accuracy RTK GPS  ← USE THIS
                      hms/gps_rtk_err.csv ← RTK error estimates

We do NOT need: velodyne_hits/, lb3/, cam0-5/, etc.

Recommended dates to download (varied environments):
  2012-08-04   — good weather, open campus
  2013-04-05   — different season
  2012-11-16   — autumn conditions
  2013-01-10   — winter
  (Each <date>_sen.tar.gz is ~50–200 MB for GPS only after extraction)

WHERE TO PLACE THE FILES:
  data/raw/public/nclt/
    2012-08-04/
      gps_rtk.csv
      gps_rtk_err.csv
      gps.csv
    2013-04-05/
      gps_rtk.csv
      ...

NCLT gps_rtk.csv format:
  utime,x,y,z       (microsecond UNIX timestamp, ECEF coordinates in metres)

NCLT gps.csv format (raw, lower accuracy):
  utime,mode,num_sats,lat,lng,alt,track,speed,climb,err_horiz,err_vert
  (lat/lng in degrees × 1e-7, alt in mm)

RTKLIB is NOT needed for NCLT — the RTK solution is pre-computed.
This script just standardises the CSV format for the feature pipeline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from pyproj import Transformer   # pip install pyproj

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DATA_ROOT = Path("data/raw/public/nclt")
OUTPUT_DIR = Path("data/processed/nclt")
# ECEF → WGS-84 geodetic transformer
_ECEF_TO_LLH = None


def _get_transformer():
    global _ECEF_TO_LLH
    if _ECEF_TO_LLH is None:
        _ECEF_TO_LLH = Transformer.from_crs(
            "EPSG:4978", "EPSG:4326", always_xy=True)
    return _ECEF_TO_LLH


def ecef_to_llh(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert ECEF (m) to (longitude, latitude, altitude in m)."""
    transformer = _get_transformer()
    lon, lat, alt = transformer.transform(x, y, z)
    return lat, lon, alt


def load_gps_rtk(rtk_file: Path) -> pd.DataFrame:
    """
    Load NCLT gps_rtk.csv.
    Columns: utime, x, y, z  (ECEF metres, utime = microseconds since epoch)
    Returns standardised DataFrame with: timestamp_s, latitude, longitude, altitude, source
    """
    df = pd.read_csv(rtk_file, header=None, names=["utime", "x", "y", "z"])
    df = df.dropna()

    # Convert ECEF → geodetic
    coords = [ecef_to_llh(row.x, row.y, row.z) for _, row in df.iterrows()]
    df["latitude"] = [c[0] for c in coords]
    df["longitude"] = [c[1] for c in coords]
    df["altitude"] = [c[2] for c in coords]
    df["timestamp_s"] = df["utime"] / 1e6  # microseconds → seconds
    # RTK = highest quality (equiv. to RTKLIB Q=1)
    df["solution_quality"] = 1
    df["source"] = "nclt_rtk"
    return df[["timestamp_s", "latitude", "longitude", "altitude",
               "solution_quality", "source"]]


def load_gps_raw(gps_file: Path) -> pd.DataFrame:
    """
    Load NCLT gps.csv (fallback when RTK is not available).
    Columns: utime, mode, num_sats, lat, lng, alt, track, speed, climb, err_horiz, err_vert
    lat/lng are in degrees × 1e-7, alt in mm.
    """
    cols = ["utime", "mode", "num_sats", "lat", "lng", "alt",
            "track", "speed", "climb", "err_horiz", "err_vert"]
    df = pd.read_csv(gps_file, header=None, names=cols)
    df = df.dropna()

    df["latitude"] = df["lat"] / 1e7
    df["longitude"] = df["lng"] / 1e7
    df["altitude"] = df["alt"] / 1000.0   # mm → m
    df["timestamp_s"] = df["utime"] / 1e6
    df["solution_quality"] = 5              # Single-point equivalent
    df["source"] = "nclt_raw_gps"
    return df[["timestamp_s", "latitude", "longitude", "altitude",
               "solution_quality", "source", "num_sats"]]


def process_date(date_dir: Path) -> pd.DataFrame | None:
    """Process one NCLT collection date. Prefers RTK over raw GPS."""
    rtk_file = date_dir / "gps_rtk.csv"
    gps_file = date_dir / "gps.csv"

    if rtk_file.exists():
        logger.info(f"  {date_dir.name}: using RTK solution")
        df = load_gps_rtk(rtk_file)
    elif gps_file.exists():
        logger.warning(
            f"  {date_dir.name}: RTK not found, using raw GPS (lower accuracy)")
        df = load_gps_raw(gps_file)
    else:
        logger.warning(f"  {date_dir.name}: no GPS files found — skipping")
        return None

    df["collection_date"] = date_dir.name
    return df


def process_all() -> pd.DataFrame | None:
    """Process all NCLT dates available under DATA_ROOT."""
    if not DATA_ROOT.exists() or not any(DATA_ROOT.iterdir()):
        logger.warning(
            f"No NCLT data found at {DATA_ROOT}.\n"
            "Download instructions are at the top of this file.\n"
            "Place gps_rtk.csv files under data/raw/public/nclt/<YYYY-MM-DD>/"
        )
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_dfs = []

    date_dirs = sorted(d for d in DATA_ROOT.iterdir() if d.is_dir())
    for date_dir in date_dirs:
        df = process_date(date_dir)
        if df is not None:
            all_dfs.append(df)

    if not all_dfs:
        logger.error("No data extracted from any NCLT date.")
        return None

    combined = pd.concat(all_dfs, ignore_index=True).sort_values("timestamp_s")
    out_file = OUTPUT_DIR / "nclt_combined.csv"
    combined.to_csv(out_file, index=False)
    logger.info(f"NCLT combined: {len(combined):,} rows → {out_file}")
    return combined


if __name__ == "__main__":
    process_all()
