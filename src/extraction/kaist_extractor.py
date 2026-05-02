"""
KAIST (Korea Advanced Institute of Science and Technology) Dataset Extraction
Data source: https://3d.skku.edu/guide/ or http://irvlab.cs.umn.edu/
Note: KAIST and NCLT are sometimes used interchangeably in literature
Format: Multiple sensors with GPS data (similar to NCLT)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KAISTExtractor:
    """
    Extract GPS data from KAIST dataset
    Similar to NCLT but from different institution
    Handles: CSV-format GPS data, RTK solutions
    """

    def __init__(self, data_root: str = "data/raw/public/kaist"):
        self.data_root = Path(data_root)
        self.output_dir = Path("data/processed/kaist")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_sequences(self):
        """Extract GPS data from all available sequences/runs"""
        all_data = []

        # KAIST typically has sequences organized by name/date
        sequence_dirs = []

        # Look for directories (sequences)
        for item in self.data_root.iterdir():
            if item.is_dir():
                sequence_dirs.append(item)

        if not sequence_dirs:
            logger.warning(f"No KAIST sequences found in {self.data_root}")
            logger.info(f"Expected structure: data_root/sequence_name/")
            logger.info(f"or data_root/YYYY-MM-DD/")
            return None

        sequence_dirs = sorted(sequence_dirs)

        for seq_dir in sequence_dirs:
            logger.info(f"Processing KAIST sequence: {seq_dir.name}...")
            seq_data = self.extract_sequence(seq_dir)
            if seq_data is not None:
                seq_data['kaist_sequence'] = seq_dir.name
                all_data.append(seq_data)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(
                'timestamp').reset_index(drop=True)
            output_file = self.output_dir / "kaist_combined.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_file}")
            return combined_df
        else:
            logger.error("No KAIST data extracted")
            return None

    def extract_sequence(self, seq_dir: Path) -> pd.DataFrame:
        """Extract GPS data from a single sequence"""

        # Priority 1: Look for GPS solution file
        gps_files = []
        for candidate in ['gps.csv', 'GPS.csv', 'gps_data.csv', 'gps_solution.csv']:
            candidates = list(seq_dir.glob(candidate))
            if candidates:
                gps_files.extend(candidates)

        # Also try wildcard
        if not gps_files:
            gps_files = list(seq_dir.glob("*gps*.csv"))

        if gps_files:
            logger.info(f"  Found {len(gps_files)} GPS file(s)")
            return self.extract_gps_csv(gps_files[0])

        # Priority 2: Look in subdirectories
        logger.info(f"  Looking in subdirectories...")
        for subdir in seq_dir.iterdir():
            if subdir.is_dir():
                for candidate in ['gps.csv', 'GPS.csv']:
                    gps_file = subdir / candidate
                    if gps_file.exists():
                        logger.info(f"  Found GPS file in {subdir.name}")
                        return self.extract_gps_csv(gps_file)

        # Priority 3: Look for any measurement file
        csv_files = list(seq_dir.glob("*.csv"))
        if csv_files:
            logger.warning(
                f"  No explicit GPS file found, trying first CSV: {csv_files[0].name}")
            data = self.extract_gps_csv(csv_files[0])
            if data is not None:
                return data

        logger.warning(f"  No GPS data found in sequence")
        return None

    def extract_gps_csv(self, gps_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from KAIST CSV file
        KAIST format varies, but typically includes:
        timestamp, latitude, longitude, altitude, accuracy, num_satellites
        """
        try:
            # Read with flexible parsing
            df = pd.read_csv(gps_file, comment='#')

            if df is None or len(df) == 0:
                logger.warning(f"GPS file is empty")
                return None

            # Standardize column names
            df.columns = [col.lower().strip() for col in df.columns]

            logger.info(f"  Columns found: {list(df.columns)}")

            # Find timestamp column
            time_col = None
            for candidate in ['timestamp', 'time', 'gps_time', 'utc_time', 'epoch', 'index']:
                if candidate in df.columns:
                    time_col = candidate
                    break

            if time_col is None:
                # Try first numeric column as index/time
                numeric_cols = df.select_dtypes(
                    include=[np.number]).columns.tolist()
                if numeric_cols:
                    time_col = numeric_cols[0]
                    logger.info(f"  Using {time_col} as timestamp")

            # Parse timestamp
            if time_col:
                if df[time_col].dtype == 'object':
                    df['timestamp'] = pd.to_datetime(
                        df[time_col], errors='coerce')
                else:
                    # Assume numeric: Unix timestamp
                    if df[time_col].max() > 1e11:  # Nanoseconds
                        df['timestamp'] = pd.to_datetime(
                            df[time_col] / 1e9, unit='s')
                    else:  # Seconds or sequence number
                        if df[time_col].max() < 1000000:  # Likely sequence number
                            df['timestamp'] = pd.date_range(
                                start='2024-01-01', periods=len(df), freq='0.01S')
                        else:
                            df['timestamp'] = pd.to_datetime(
                                df[time_col], unit='s', errors='coerce')
            else:
                # No timestamp found, create sequence
                df['timestamp'] = pd.date_range(
                    start='2024-01-01', periods=len(df), freq='0.01S')

            # Extract coordinates
            if 'latitude' in df.columns and 'longitude' in df.columns:
                keep_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
            elif 'lat' in df.columns and 'lon' in df.columns:
                df = df.rename(columns={'lat': 'latitude', 'lon': 'longitude'})
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
                logger.error(
                    f"Could not find coordinate columns in {gps_file}")
                logger.info(f"Available columns: {list(df.columns)}")
                return None

            # Keep only needed columns and remove NaN
            keep_cols = [c for c in keep_cols if c in df.columns]
            df = df[keep_cols].dropna(subset=['latitude', 'longitude'])

            if len(df) == 0:
                logger.warning(f"No valid coordinates after filtering")
                return None

            logger.info(f"Extracted {len(df)} KAIST GPS records")
            return df

        except Exception as e:
            logger.error(f"Error reading KAIST GPS file: {e}")
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
    extractor = KAISTExtractor()
    df = extractor.extract_all_sequences()
    if df is not None:
        print(f"\nExtracted {len(df)} total records")
        print(df.head())
