"""
UrbanNav Dataset Extraction
Data source: https://github.com/IPNL-POLYU/UrbanNavDataset
Locations: Hong Kong, Beijing, Taipei
Format: GNSS raw measurements (need RTKLIB conversion) + ground truth
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UrbanNavExtractor:
    """
    Extract GPS data from UrbanNav dataset
    Requires RTKLIB processing first to get positions from raw measurements
    """

    def __init__(self, data_root: str = "data/raw/public/urbannav"):
        self.data_root = Path(data_root)
        self.output_dir = Path("data/processed/urbannav")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Define location subdirectories
        self.locations = {
            'hong_kong': 'hong_kong',
            'beijing': 'beijing',
            'taipei': 'taipei'
        }

    def extract_all_locations(self):
        """Extract GPS data from all three cities"""
        all_data = []

        for location_name, folder_name in self.locations.items():
            location_dir = self.data_root / folder_name

            # Also try common naming variants
            if not location_dir.exists():
                # Try Hong Kong variants
                if location_name == 'hong_kong':
                    variants = ['Hong_Kong', 'HongKong', 'HK', 'hong_kong']
                elif location_name == 'beijing':
                    variants = ['Beijing', 'BEIJING', 'beijing']
                else:  # taipei
                    variants = ['Taipei', 'TAIPEI', 'taipei']

                for variant in variants:
                    alt_dir = self.data_root / variant
                    if alt_dir.exists():
                        location_dir = alt_dir
                        break

            if not location_dir.exists():
                logger.warning(
                    f"Location directory for {location_name} not found")
                continue

            logger.info(
                f"Processing UrbanNav {location_name.replace('_', ' ').title()}...")
            location_data = self.extract_location(location_dir, location_name)
            if location_data is not None:
                location_data['urbannav_location'] = location_name
                all_data.append(location_data)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(
                'timestamp').reset_index(drop=True)
            output_file = self.output_dir / "urbannav_combined.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_file}")
            return combined_df
        else:
            logger.error("No UrbanNav data extracted")
            return None

    def extract_location(self, location_dir: Path, location_name: str) -> pd.DataFrame:
        """Extract data from a single location"""

        # Look for ground truth file (reference solution)
        gt_files = list(location_dir.rglob("*ground*truth*")) + \
            list(location_dir.rglob("*groundtruth*")) + \
            list(location_dir.rglob("*reference*")) + \
            list(location_dir.rglob("*gt.csv"))

        if gt_files:
            logger.info(f"  Found ground truth: {gt_files[0].name}")
            return self.extract_ground_truth(gt_files[0])

        # Look for GNSS measurements that need RTKLIB processing
        logger.warning(f"  No ground truth file found for {location_name}")
        logger.info(
            f"  Looking for raw GNSS measurements that need RTKLIB processing...")

        # Find RINEX or raw GNSS files
        rinex_files = list(location_dir.rglob("*.??o"))  # RINEX observation
        if rinex_files:
            logger.info(f"  Found {len(rinex_files)} RINEX observation files")
            logger.warning(
                f"  These require RTKLIB processing (RTKCONV + RTKPOST) to extract positions")
            logger.info(
                f"  Run RTKLIB processing first, then use extract_location with solution files")
            return None

        return None

    def extract_ground_truth(self, gt_file: Path) -> pd.DataFrame:
        """
        Extract ground truth reference solution
        UrbanNav typically provides this in CSV format with positions
        Format varies: may be lat/lon/alt or x/y/z (ECEF)
        """
        try:
            # Try different possible formats
            df = None

            # Try standard CSV
            try:
                df = pd.read_csv(gt_file)
            except:
                # Try with different delimiters
                df = pd.read_csv(gt_file, sep='\s+')

            if df is None or len(df) == 0:
                logger.error(f"Could not read ground truth file")
                return None

            # Standardize column names
            df.columns = [col.lower().strip() for col in df.columns]

            # Find timestamp column
            time_col = None
            for candidate in ['timestamp', 'time', 'gps_time', 'utc_time', 'epoch', 'date']:
                if candidate in df.columns:
                    time_col = candidate
                    break

            if time_col is None:
                # If no time column, assume index is timestamp
                df['timestamp'] = pd.date_range(
                    start='2024-01-01', periods=len(df), freq='1S')
            else:
                # Parse timestamp
                if df[time_col].dtype == 'object':
                    df['timestamp'] = pd.to_datetime(
                        df[time_col], errors='coerce')
                else:
                    # Assume Unix timestamp
                    if df[time_col].max() > 1e11:  # Nanoseconds
                        df['timestamp'] = pd.to_datetime(
                            df[time_col] / 1e9, unit='s')
                    else:  # Seconds
                        df['timestamp'] = pd.to_datetime(
                            df[time_col], unit='s')

            # Extract coordinates
            if 'latitude' in df.columns and 'longitude' in df.columns:
                # Geodetic coordinates
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            elif 'lat' in df.columns and 'lon' in df.columns:
                df = df.rename(columns={'lat': 'latitude', 'lon': 'longitude'})
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            elif 'x' in df.columns and 'y' in df.columns and 'z' in df.columns:
                # ECEF coordinates
                logger.info(f"  Converting ECEF to geodetic coordinates...")
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

            keep_cols = [c for c in keep_cols if c in df.columns]
            df = df[keep_cols].dropna(subset=['latitude', 'longitude'])

            logger.info(f"Extracted {len(df)} ground truth records")
            return df

        except Exception as e:
            logger.error(f"Error reading ground truth file: {e}")
            return None

    def extract_rtklib_solution(self, solution_dir: Path) -> pd.DataFrame:
        """
        Extract RTKLIB-processed solution files
        If user has already processed UrbanNav with RTKLIB
        """
        pos_files = list(solution_dir.glob("*.pos"))

        if not pos_files:
            logger.warning(f"No RTKLIB solution files (.pos) found")
            return None

        all_data = []
        for pos_file in pos_files:
            logger.info(f"  Processing {pos_file.name}")
            try:
                df = pd.read_csv(
                    pos_file,
                    delim_whitespace=True,
                    comment='%',
                    header=None
                )

                if len(df.columns) >= 5:
                    df.columns = ['date', 'time', 'latitude', 'longitude', 'altitude'] + \
                        [f'col_{i}' for i in range(5, len(df.columns))]

                    df['timestamp'] = pd.to_datetime(
                        df['date'].astype(str) + ' ' + df['time'].astype(str),
                        format='%Y/%m/%d %H:%M:%S.%f',
                        errors='coerce'
                    )

                    df = df[['timestamp', 'latitude',
                             'longitude', 'altitude']].dropna()
                    all_data.append(df)
            except Exception as e:
                logger.error(f"Error reading {pos_file.name}: {e}")

        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            logger.info(f"Extracted {len(combined)} RTKLIB solution records")
            return combined

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
            # Fallback
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
    extractor = UrbanNavExtractor()
    df = extractor.extract_all_locations()
    if df is not None:
        print(f"\nExtracted {len(df)} total records")
        print(df.head())
