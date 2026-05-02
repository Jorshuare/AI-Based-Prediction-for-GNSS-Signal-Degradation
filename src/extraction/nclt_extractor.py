"""
NCLT Dataset Extraction (KAIST University)
Data source: http://norlab.ulaval.ca/research/nexus/nclt/
Already in CSV format - just needs standardization
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NCLTExtractor:
    """
    Extract GPS data from NCLT dataset (already in CSV format)
    Handles: gps.csv (raw), gps_rtk.csv (high accuracy)
    """

    def __init__(self, data_root: str = "data/NCLT_data"):
        self.data_root = Path(data_root)
        self.output_dir = Path("data/processed/nclt")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_dates(self):
        """Extract GPS data from all available dates (2012-08-04, 2013-04-05, etc.)"""
        all_data = []

        # Find all date folders (format: YYYY-MM-DD)
        date_dirs = sorted(
            [d for d in self.data_root.iterdir() if d.is_dir() and '-' in d.name])

        for date_dir in date_dirs:
            logger.info(f"Processing {date_dir.name}...")
            date_data = self.extract_date(date_dir)
            if date_data is not None:
                date_data['collection_date'] = date_dir.name
                all_data.append(date_data)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(
                'timestamp').reset_index(drop=True)
            output_file = self.output_dir / "nclt_combined.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_file}")
            return combined_df
        else:
            logger.error("No NCLT data extracted")
            return None

    def extract_date(self, date_dir: Path) -> pd.DataFrame:
        """Extract GPS data for a single date"""

        # Priority 1: Use high-accuracy RTK solution if available
        rtk_file = date_dir / "gps_rtk.csv"
        if rtk_file.exists():
            logger.info(f"  Using high-accuracy RTK solution: {rtk_file.name}")
            return self.extract_gps_rtk(rtk_file)

        # Priority 2: Use raw GPS if RTK not available
        gps_file = date_dir / "gps.csv"
        if gps_file.exists():
            logger.info(f"  Using raw GPS: {gps_file.name}")
            return self.extract_raw_gps(gps_file)

        logger.warning(f"No GPS files found in {date_dir}")
        return None

    def extract_gps_rtk(self, rtk_file: Path) -> pd.DataFrame:
        """
        Extract high-accuracy RTK GPS data
        NCLT RTK format (typical):
        timestamp, x, y, z (ECEF coordinates)
        or
        timestamp, latitude, longitude, altitude (geodetic)
        """
        try:
            df = pd.read_csv(rtk_file, comment='#')

            # Standardize column names (NCLT varies)
            df.columns = [col.lower().strip() for col in df.columns]

            # Handle timestamp column (can be 'timestamp', 'time', 'gps_time', etc.)
            time_col = None
            for candidate in ['timestamp', 'time', 'gps_time', 'utc_time']:
                if candidate in df.columns:
                    time_col = candidate
                    break

            if time_col is None:
                logger.error(f"Could not find timestamp column in {rtk_file}")
                return None

            # Convert timestamp to datetime (typically Unix timestamp)
            if df[time_col].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df[time_col])
            else:
                # Assume Unix timestamp (seconds or nanoseconds)
                if df[time_col].max() > 1e11:  # Likely nanoseconds
                    df['timestamp'] = pd.to_datetime(
                        df[time_col] / 1e9, unit='s')
                else:  # Likely seconds
                    df['timestamp'] = pd.to_datetime(df[time_col], unit='s')

            # Handle coordinate format
            if 'latitude' in df.columns and 'longitude' in df.columns:
                # Geodetic coordinates
                df = df.rename(columns={
                    'latitude': 'latitude',
                    'longitude': 'longitude',
                    'altitude': 'altitude',
                    'lat': 'latitude',
                    'lon': 'longitude',
                    'alt': 'altitude'
                })
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']

            elif 'x' in df.columns and 'y' in df.columns and 'z' in df.columns:
                # ECEF coordinates - convert to geodetic
                logger.info("  Converting ECEF to geodetic coordinates...")
                df[['latitude', 'longitude', 'altitude']] = df[['x', 'y', 'z']].apply(
                    lambda row: self.ecef_to_geodetic(
                        row['x'], row['y'], row['z']),
                    axis=1,
                    result_type='expand'
                )
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            else:
                logger.warning(
                    f"Could not find coordinate columns in {rtk_file}")
                return None

            # Extract relevant columns
            keep_cols = [c for c in keep_cols if c in df.columns]
            df = df[keep_cols].dropna(subset=['latitude', 'longitude'])

            logger.info(f"Extracted {len(df)} RTK records")
            return df

        except Exception as e:
            logger.error(f"Error reading RTK file: {e}")
            return None

    def extract_raw_gps(self, gps_file: Path) -> pd.DataFrame:
        """
        Extract raw GPS data (lower accuracy but fallback option)
        """
        try:
            df = pd.read_csv(gps_file, comment='#')
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
            df['timestamp'] = pd.to_datetime(
                df[time_col], unit='s', errors='coerce')

            # Find coordinates
            if 'latitude' in df.columns and 'longitude' in df.columns:
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            else:
                logger.warning("Could not find coordinate columns")
                return None

            keep_cols = [c for c in keep_cols if c in df.columns]
            df = df[keep_cols].dropna(subset=['latitude', 'longitude'])

            logger.info(f"Extracted {len(df)} raw GPS records")
            return df

        except Exception as e:
            logger.error(f"Error reading GPS file: {e}")
            return None

    @staticmethod
    def ecef_to_geodetic(x, y, z):
        """
        Convert ECEF coordinates to geodetic (lat, lon, alt)
        Using WGS84 ellipsoid
        """
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
            a = 6378137.0  # WGS84 semi-major axis
            f = 1.0 / 298.257223563  # WGS84 flattening
            e2 = 2 * f - f ** 2

            lon = np.arctan2(y, x)
            p = np.sqrt(x ** 2 + y ** 2)
            lat = np.arctan2(z, p * (1 - e2))

            for _ in range(5):  # Iterate
                N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
                alt = p / np.cos(lat) - N
                lat = np.arctan2(z, p * (1 - e2 * N / (N + alt)))

            lat, lon = np.degrees(lat), np.degrees(lon)
            return pd.Series([lat, lon, alt])


if __name__ == "__main__":
    extractor = NCLTExtractor()
    df = extractor.extract_all_dates()
    if df is not None:
        print(f"\nExtracted {len(df)} total records")
        print(df.head())
