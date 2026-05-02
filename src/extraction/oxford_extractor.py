"""
Oxford RobotCar Dataset Extraction
Data source: http://ori.ox.ac.uk/datasets/radar-robotcar-dataset/
Format: Multiple sensors (Radar, GPS, LiDAR) in proprietary formats
We extract only GPS data for this project
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OxfordRobotCarExtractor:
    """
    Extract GPS data from Oxford RobotCar dataset
    Note: Radar and LiDAR data are ignored for this GPS prediction task
    """

    def __init__(self, data_root: str = "data/raw/public/oxford"):
        self.data_root = Path(data_root)
        self.output_dir = Path("data/processed/oxford")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_runs(self):
        """Extract GPS data from all available runs"""
        all_data = []

        # Oxford RobotCar has runs organized by date/time
        # Look for typical Oxford dataset structure
        run_dirs = []

        # Try to find run directories (format: YYYY-MM-DD-HH-MM-SS)
        for item in self.data_root.iterdir():
            if item.is_dir() and len(item.name) >= 19 and item.name[4] == '-':
                run_dirs.append(item)

        if not run_dirs:
            logger.warning(f"No Oxford runs found in {self.data_root}")
            logger.info(f"Expected format: data_root/YYYY-MM-DD-HH-MM-SS/")
            return None

        run_dirs = sorted(run_dirs)

        for run_dir in run_dirs:
            logger.info(f"Processing Oxford run: {run_dir.name}...")
            run_data = self.extract_run(run_dir)
            if run_data is not None:
                run_data['oxford_run'] = run_dir.name
                all_data.append(run_data)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(
                'timestamp').reset_index(drop=True)
            output_file = self.output_dir / "oxford_combined.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_file}")
            return combined_df
        else:
            logger.error("No Oxford RobotCar data extracted")
            return None

    def extract_run(self, run_dir: Path) -> pd.DataFrame:
        """Extract GPS data from a single run"""

        # Look for GPS data files
        # Oxford RobotCar typically stores GPS in CSV or specific format
        gps_file = None

        # Try common GPS file names
        for candidate in ['gps.csv', 'GPS.csv', 'gps_data.csv', 'INS.csv', 'ins.csv']:
            candidate_path = run_dir / candidate
            if candidate_path.exists():
                gps_file = candidate_path
                break

        # Also try to find any file with 'gps' in the name
        if not gps_file:
            gps_files = list(run_dir.glob("*gps*"))
            if gps_files:
                gps_file = gps_files[0]

        if gps_file:
            logger.info(f"  Found GPS file: {gps_file.name}")
            return self.extract_gps_csv(gps_file)

        # Try looking in subdirectories
        logger.warning(f"  No GPS file in root, checking subdirectories...")
        for subdir in run_dir.iterdir():
            if subdir.is_dir():
                gps_file = subdir / "gps.csv"
                if gps_file.exists():
                    logger.info(
                        f"  Found GPS file in {subdir.name}: {gps_file.name}")
                    return self.extract_gps_csv(gps_file)

        logger.warning(f"  No GPS data found in run")
        return None

    def extract_gps_csv(self, gps_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from CSV file
        Oxford RobotCar GPS format (typical):
        timestamp, latitude, longitude, altitude, accuracy, num_satellites
        """
        try:
            df = pd.read_csv(gps_file)

            # Standardize column names
            df.columns = [col.lower().strip() for col in df.columns]

            # Find timestamp column
            time_col = None
            for candidate in ['timestamp', 'time', 'gps_time', 'utc_time']:
                if candidate in df.columns:
                    time_col = candidate
                    break

            if time_col is None:
                logger.error(f"Could not find timestamp column")
                return None

            # Parse timestamp
            if df[time_col].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df[time_col], errors='coerce')
            else:
                # Assume Unix timestamp or similar
                if df[time_col].max() > 1e11:  # Nanoseconds
                    df['timestamp'] = pd.to_datetime(
                        df[time_col] / 1e9, unit='s')
                else:  # Seconds
                    df['timestamp'] = pd.to_datetime(df[time_col], unit='s')

            # Extract coordinates
            if 'latitude' in df.columns and 'longitude' in df.columns:
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            elif 'lat' in df.columns and 'lon' in df.columns:
                df = df.rename(
                    columns={'lat': 'latitude', 'lon': 'longitude', 'alt': 'altitude'})
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            elif 'x' in df.columns and 'y' in df.columns and 'z' in df.columns:
                # ECEF coordinates
                logger.info(f"  Converting ECEF to geodetic...")
                df[['latitude', 'longitude', 'altitude']] = df[['x', 'y', 'z']].apply(
                    lambda row: self.ecef_to_geodetic(
                        row['x'], row['y'], row['z']),
                    axis=1,
                    result_type='expand'
                )
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            else:
                logger.error(f"Could not find coordinate columns")
                logger.info(f"Available columns: {list(df.columns)}")
                return None

            # Keep only needed columns
            keep_cols = [c for c in keep_cols if c in df.columns]
            df = df[keep_cols].dropna(subset=['latitude', 'longitude'])

            logger.info(f"Extracted {len(df)} GPS records from Oxford")
            return df

        except Exception as e:
            logger.error(f"Error reading GPS file: {e}")
            return None

    def extract_ins_solution(self, ins_file: Path) -> pd.DataFrame:
        """
        Extract INS (Inertial Navigation System) solution if available
        More accurate than raw GPS
        """
        try:
            df = pd.read_csv(ins_file)
            df.columns = [col.lower().strip() for col in df.columns]

            # INS typically has timestamp and position
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(
                    df['timestamp'], errors='coerce')

            if 'latitude' in df.columns and 'longitude' in df.columns:
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
                keep_cols = [c for c in keep_cols if c in df.columns]
                df = df[keep_cols].dropna(subset=['latitude', 'longitude'])
                logger.info(f"Extracted {len(df)} INS records")
                return df
        except Exception as e:
            logger.error(f"Error reading INS file: {e}")

        return None

    @staticmethod
    def ecef_to_geodetic(x, y, z):
        """Convert ECEF to geodetic coordinates"""
        try:
            import pyproj
            transformer = pyproj.Transformer.from_crs(
                {"proj": 'geocent', "ellps": 'WGS84', "datum": 'WGS84'},
                {"ellps": 'WGS84', "datum": 'WGS84'}
            )
            lon, lat, alt = transformer.transform(x, y, z)
            return pd.Series([lat, lon, alt])
        except:
            # Fallback iterative algorithm
            a = 6378137.0
            f = 1.0 / 298.257223563
            e2 = 2 * f - f ** 2

            lon = np.arctan2(y, x)
            p = np.sqrt(x ** 2 + y ** 2)
            lat = np.arctan2(z, p * (1 - e2))

            for _ in range(5):
                N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
                alt = p / np.cos(lat) - N
                lat = np.arctan2(z, p * (1 - e2 * N / (N + alt)))

            lat, lon = np.degrees(lat), np.degrees(lon)
            return pd.Series([lat, lon, alt])


if __name__ == "__main__":
    extractor = OxfordRobotCarExtractor()
    df = extractor.extract_all_runs()
    if df is not None:
        print(f"\nExtracted {len(df)} total records")
        print(df.head())
