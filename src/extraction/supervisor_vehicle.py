"""
Supervisor Vehicle Dataset Extraction
Handles: NMEA (.nmea), Septentrio Binary (.sbf), and Rinex formats
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import struct
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupervisorVehicleExtractor:
    """
    Extract GPS data from supervisor vehicle dataset
    Raw formats: NMEA, Septentrio Binary (.sbf), Rinex
    """

    def __init__(self, data_root: str = "data/raw/supervisor/vehicle"):
        self.data_root = Path(data_root)
        self.output_dir = Path("data/processed/supervisor/vehicle")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_experiments(self):
        """Extract GPS data from all vehicle experiments (exp1-exp4)"""
        all_data = []

        for exp_num in range(1, 5):
            exp_dir = self.data_root / f"exp{exp_num}"
            if not exp_dir.exists():
                logger.warning(f"Experiment directory {exp_dir} not found")
                continue

            logger.info(f"Processing Experiment {exp_num}...")
            exp_data = self.extract_experiment(exp_dir)
            if exp_data is not None:
                all_data.append(exp_data)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(
                'timestamp').reset_index(drop=True)
            output_file = self.output_dir / "vehicle_combined.csv"
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_file}")
            return combined_df
        else:
            logger.error("No experiment data extracted")
            return None

    def extract_experiment(self, exp_dir: Path) -> pd.DataFrame:
        """Extract single experiment with multiple base stations"""
        exp_data = []

        # Process each base station folder (1 base, 2 base, 3 b, 4b)
        for base_dir in exp_dir.iterdir():
            if not base_dir.is_dir():
                continue

            logger.info(f"  Processing {base_dir.name}...")
            base_data = self.extract_base_station(base_dir)
            if base_data is not None:
                base_data['base_station'] = base_dir.name
                exp_data.append(base_data)

        if exp_data:
            return pd.concat(exp_data, ignore_index=True)
        return None

    def extract_base_station(self, base_dir: Path) -> pd.DataFrame:
        """
        Extract GPS data from a single base station directory
        Handles: .nmea, .sbf, Rinex files
        """
        data = None

        # Try NMEA format first (most common)
        nmea_file = list(base_dir.glob("*.nmea"))
        if nmea_file:
            logger.info(f"    Found NMEA: {nmea_file[0].name}")
            data = self.extract_nmea(nmea_file[0])

        # Try Septentrio Binary format
        sbf_file = list(base_dir.glob("*.sbf"))
        if sbf_file and data is None:
            logger.info(f"    Found SBF: {sbf_file[0].name}")
            data = self.extract_septentrio_binary(sbf_file[0])

        # Try Rinex format
        rinex_files = list(base_dir.glob("*.[0-9][0-9]o"))  # .21o, .22o, etc.
        if rinex_files and data is None:
            logger.info(f"    Found Rinex: {rinex_files[0].name}")
            data = self.extract_rinex(rinex_files[0])

        return data

    def extract_nmea(self, nmea_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from NMEA format
        Focus on GGA and GSA sentences
        """
        records = []

        try:
            with open(nmea_file, 'r', encoding='utf-8', errors='ignore') as f:
                current_fix = {}

                for line in f:
                    line = line.strip()
                    if not line or not line.startswith('$'):
                        continue

                    parts = line.split(',')
                    sentence_type = parts[0][3:6]  # Extract GGA, GSA, etc.

                    # Parse GGA sentence (position + time)
                    if sentence_type == 'GGA':
                        current_fix = self.parse_gga_sentence(parts)

                    # Parse GSA sentence (satellite info + DOP)
                    elif sentence_type == 'GSA':
                        if current_fix:
                            gsa_data = self.parse_gsa_sentence(parts)
                            current_fix.update(gsa_data)
                            records.append(current_fix)
                            current_fix = {}

                    # Parse GGA only if we won't get GSA
                    elif sentence_type == 'RMC' and current_fix:
                        rmc_data = self.parse_rmc_sentence(parts)
                        current_fix.update(rmc_data)

            if records:
                df = pd.DataFrame(records)
                df = df.dropna(subset=['latitude', 'longitude'])
                logger.info(f"Extracted {len(df)} records from NMEA")
                return df
        except Exception as e:
            logger.error(f"Error reading NMEA: {e}")

        return None

    def parse_gga_sentence(self, parts):
        """Parse NMEA GGA sentence"""
        try:
            timestamp_str = parts[1]  # HHMMSS.SS
            lat_str = parts[2]
            lat_dir = parts[3]
            lon_str = parts[4]
            lon_dir = parts[5]
            fix_quality = int(parts[6]) if len(parts) > 6 else 0
            num_sat = int(parts[7]) if len(parts) > 7 else 0
            altitude = float(parts[9]) if len(parts) > 9 else np.nan

            # Convert latitude/longitude
            lat = self.dms_to_decimal(lat_str)
            lon = self.dms_to_decimal(lon_str)

            if lat_dir == 'S':
                lat = -lat
            if lon_dir == 'W':
                lon = -lon

            return {
                'timestamp': timestamp_str,
                'latitude': lat,
                'longitude': lon,
                'altitude': altitude,
                'fix_quality': fix_quality,
                'num_satellites': num_sat,
            }
        except Exception as e:
            logger.debug(f"Error parsing GGA: {e}")
            return {}

    def parse_gsa_sentence(self, parts):
        """Parse NMEA GSA sentence"""
        try:
            pdop = float(parts[15]) if len(parts) > 15 else np.nan
            hdop = float(parts[16]) if len(parts) > 16 else np.nan
            vdop = float(parts[17].split('*')[0]
                         ) if len(parts) > 17 else np.nan

            return {
                'pdop': pdop,
                'hdop': hdop,
                'vdop': vdop,
            }
        except Exception as e:
            logger.debug(f"Error parsing GSA: {e}")
            return {}

    def parse_rmc_sentence(self, parts):
        """Parse NMEA RMC sentence"""
        try:
            status = parts[2]  # A=active, V=void
            return {'gps_valid': (status == 'A')}
        except Exception as e:
            logger.debug(f"Error parsing RMC: {e}")
            return {}

    def extract_septentrio_binary(self, sbf_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from Septentrio Binary Format (.sbf)
        This is a complex binary format - we'll extract key messages
        """
        logger.warning(
            f"SBF format extraction not fully implemented. Recommend converting to NMEA first.")
        logger.info(
            f"To convert SBF to NMEA, use Septentrio's tools or RtkLib's conv feature")
        return None

    def extract_rinex(self, rinex_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from Rinex format
        Note: Rinex is observational data, not positions
        For positions, you need the corresponding navigation file
        """
        logger.warning(f"Rinex extraction requires RTKLIB processing first")
        logger.info(f"After RTKLIB processing, use the .pos file instead")
        return None

    @staticmethod
    def dms_to_decimal(dms_str):
        """Convert DMS string to decimal degrees"""
        if len(dms_str) < 4:
            return np.nan
        # Format: DDMM.MMMM or DDDMM.MMMM
        degrees = int(dms_str[:-7])
        minutes = float(dms_str[-7:])
        return degrees + minutes / 60

    def extract_rtklib_solution(self, pos_file: Path) -> pd.DataFrame:
        """
        Extract GPS data from RTKLIB .pos solution file (high accuracy)
        Format: Latitude Longitude Altitude Q ns sd sn se su cv ge sn cv we exStatus Age Ratio un
        """
        try:
            df = pd.read_csv(
                pos_file,
                delim_whitespace=True,
                comment='%',
                header=None,
                names=[
                    'date', 'time', 'latitude', 'longitude', 'altitude',
                    'q', 'ns', 'sd', 'sn', 'se', 'su', 'cv', 'ge', 'sn2', 'cv2',
                    'we', 'exStatus', 'age', 'ratio', 'un'
                ],
                dtype={'date': str, 'time': str}
            )

            # Combine date and time
            df['timestamp'] = pd.to_datetime(
                df['date'] + ' ' + df['time'],
                format='%Y/%m/%d %H:%M:%S.%f',
                errors='coerce'
            )

            # Keep relevant columns
            df = df[[
                'timestamp', 'latitude', 'longitude', 'altitude',
                'q', 'ns', 'sd', 'sn', 'se', 'su'
            ]]

            logger.info(f"Extracted {len(df)} records from RTKLIB solution")
            return df
        except Exception as e:
            logger.error(f"Error reading RTKLIB .pos file: {e}")
            return None


if __name__ == "__main__":
    extractor = SupervisorVehicleExtractor()
    df = extractor.extract_all_experiments()
    if df is not None:
        print(f"\nExtracted {len(df)} total records")
        print(df.head())
