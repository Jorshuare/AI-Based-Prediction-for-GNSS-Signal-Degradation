"""
Supervisor Drone Dataset Extraction
Handles: Rinex observation files (.24o, .25o) and RTKLIB solution files (.pos)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupervisorDroneExtractor:
    """
    Extract GPS data from supervisor drone dataset
    Raw formats: Rinex observation files (.24o), RTKLIB solutions (.pos)
    """

    def __init__(self, data_root: str = "data/raw/supervisor/drone"):
        self.data_root = Path(data_root)
        self.output_dir = Path("data/processed/supervisor/drone")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_flights(self):
        """Extract GPS data from all drone flights"""
        all_files = list(self.data_root.glob("*.24o")) + \
            list(self.data_root.glob("*.pos"))

        if not all_files:
            logger.error(f"No Rinex or .pos files found in {self.data_root}")
            return None

        all_data = []

        # First, check for existing .pos files (RTKLIB solutions - higher quality)
        pos_files = list(self.data_root.glob("*.pos"))
        for pos_file in pos_files:
            logger.info(f"Processing RTKLIB solution: {pos_file.name}")
            data = self.extract_rtklib_solution(pos_file)
            if data is not None:
                data['source'] = pos_file.stem  # Filename without extension
                all_data.append(data)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(
                'timestamp').reset_index(drop=True)
            output_file = self.output_dir / "drone_combined.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_file}")
            return combined_df
        else:
            logger.error("No drone data extracted")
            return None

    def extract_rtklib_solution(self, pos_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from RTKLIB .pos solution file
        Format: % Latitude Longitude Altitude Q ns sd sn se su cv ge sn cv we exStatus Age Ratio un
        Q = 1:fix, 2:float, 3:sbas, 4:dgps, 5:single, 6:ppp
        ns = number of valid satellites
        """
        try:
            df = pd.read_csv(
                pos_file,
                delim_whitespace=True,
                comment='%',
                header=None,
                skiprows=0
            )

            # Try to extract date/time if present in first columns
            if len(df.columns) >= 19:
                df.columns = [
                    'date', 'time', 'latitude', 'longitude', 'altitude',
                    'q', 'ns', 'sd', 'sn', 'se', 'su', 'cv', 'ge', 'sn2', 'cv2',
                    'we', 'exStatus', 'age', 'ratio'
                ]

                # Parse timestamp
                df['timestamp'] = pd.to_datetime(
                    df['date'].astype(str) + ' ' + df['time'].astype(str),
                    format='%Y/%m/%d %H:%M:%S.%f',
                    errors='coerce'
                )
            else:
                # If format is different, try alternative parsing
                logger.warning(
                    f"Unexpected .pos format with {len(df.columns)} columns")
                # Assume columns are: lat, lon, alt, q, ns, sd, sn, se, su, ...
                df.columns = ['latitude', 'longitude', 'altitude'] + \
                    [f'col_{i}' for i in range(3, len(df.columns))]
                df['timestamp'] = pd.date_range(
                    start='2024-01-01', periods=len(df), freq='1S')

            # Extract relevant columns
            keep_cols = [
                'timestamp', 'latitude', 'longitude', 'altitude',
                'q', 'ns'  # quality and number of satellites
            ]
            keep_cols = [c for c in keep_cols if c in df.columns]
            df = df[keep_cols]

            # Remove rows with NaN positions
            df = df.dropna(subset=['latitude', 'longitude'])

            logger.info(f"Extracted {len(df)} records from {pos_file.name}")
            return df

        except Exception as e:
            logger.error(f"Error reading RTKLIB .pos file: {e}")
            return None

    def extract_rinex_observation(self, rinex_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from Rinex observation file
        Note: Rinex contains raw observations, not positions
        Would need to process with RTKLIB first to get positions
        """
        logger.info(f"Rinex observation file detected: {rinex_file.name}")
        logger.warning(
            f"Rinex files need RTKLIB processing (RTKCONV + RTKPOST) to extract positions")
        logger.info(
            f"Run: rtkconv {rinex_file.name} → then RTKPOST with precise orbits")
        return None


if __name__ == "__main__":
    extractor = SupervisorDroneExtractor()
    df = extractor.extract_all_flights()
    if df is not None:
        print(f"\nExtracted {len(df)} total records")
        print(df.head())
