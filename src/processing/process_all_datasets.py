"""
SENTINEL-GNSS  —  Unified Dataset Processing Pipeline
======================================================
Processes ALL raw data sources to standardized 35-feature CSVs ready for
Transformer-LSTM model training.

Sources handled:
  1. Our collected scenarios (Septentrio Mosaic-X5C)
       NMEA (GGA/GNS/GSA/GST/GBS) + RINEX 3 OBS (SNR indicator for C/N0)
  2. Supervisor vehicle (exp1–exp4)
       NMEA (GGA/GSA/GSV — direct C/N0)
  3. Supervisor drone
       RINEX 3 OBS (S1C field = actual dBHz)
  4. UrbanNav HK-Medium-Urban-1 (all receivers)
       RINEX 3 OBS (S1C field = actual dBHz) + NMEA (GSV)

Feature groups (35 total, 5 per group):
  G1 Position:          lat, lon, alt, lat_std, lon_std
  G2 Signal Strength:   mean_cnr, min_cnr, max_cnr, std_cnr, cnr_trend
  G3 Satellite Count:   num_satellites, sat_mean, sat_min, sat_visibility, sat_drop_rate
  G4 DOP:               pdop, hdop, vdop, gdop, dop_ratio
  G5 Receiver Status:   solution_status, baseline_sats, solution_age, fix_continuity, fix_transitions
  G6 Temporal Patterns: position_variance, cnr_variance, elevation_violations, multipath, clock_bias
  G7 Atmospheric:       iono_delay, tropo_delay, cycle_slips, residual_mean, residual_std

Label scheme (3 classes):
  0 = CLEAN     — nominal signal, satellite count and C/N0 within healthy thresholds
  1 = WARNING   — partial degradation; signal weakening but solution maintained
  2 = DEGRADED  — significant degradation; loss of fix or very poor signal quality

Usage:
  python src/processing/process_all_datasets.py --all
  python src/processing/process_all_datasets.py --source scenarios
  python src/processing/process_all_datasets.py --source supervisor
  python src/processing/process_all_datasets.py --source urbannav
  python src/processing/process_all_datasets.py --source drone
  python src/processing/process_all_datasets.py --combine
"""

from __future__ import annotations

import argparse
import logging
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

# RINEX GPS-to-UTC leap seconds (valid 2017–2024+)
GPS_LEAP_SECONDS = 18

# Max expected tracked satellites across all constellations (GPS+GLO+GAL+BDS+QZSS+NAVIC)
# Modern multi-constellation receivers can track 50+ simultaneously
MAX_MULTI_CONST_SATS = 50

# Sliding window in seconds for temporal feature computation
WINDOW_SECONDS = 30

# ─── Label thresholds ─────────────────────────────────────────────────────────
#
#  Literature basis:
#   - C/N0 < 25 dBHz → severe degradation (below typical tracking threshold)
#   - C/N0 25–35 dBHz → marginal to moderate (multipath / partial blockage)
#   - C/N0 ≥ 35 dBHz → healthy signal
#   - HDOP > 5 → unacceptable horizontal accuracy for navigation
#   - PDOP > 8 → unacceptable 3D geometry for AV navigation
#   - Satellites < 4 → cannot maintain a solution; < 8 → geometry compromised
#
#  Note on SNR-indicator mode (Septentrio RINEX without S1C):
#   The 0-9 SNR digit gives approximate C/N0 in 6 dBHz bins. Open-sky
#   conditions produce SNR=6–7, corresponding to 36–42 dBHz. Using 35 dBHz
#   as the CLEAN lower bound accommodates this quantisation without
#   misclassifying genuinely good open-sky epochs as WARNING.
#
LABEL_THRESHOLDS = {
    # ALL conditions must be satisfied for CLEAN
    # dBHz (accommodates SNR-indicator quantisation)
    "clean_min_cnr": 35.0,
    "clean_max_hdop": 2.5,
    "clean_max_pdop": 4.0,
    "clean_min_sats": 8,
    # ANY one condition triggers DEGRADED
    "degraded_max_cnr": 25.0,    # mean C/N0 below this → DEGRADED
    "degraded_min_hdop": 5.0,    # HDOP above this → DEGRADED
    "degraded_min_pdop": 8.0,    # PDOP above this → DEGRADED
    "degraded_max_sats": 4,      # fewer sats → DEGRADED
}

# RINEX SNR indicator (0-9 digit) to approximate C/N0 dBHz
# Formula: cnr = (snr_digit - 1) * 6 + 6  (snr_digit >= 1)
# SNR=0 → unknown; SNR=1 → ~6 dBHz; SNR=7 → ~42 dBHz; SNR=9 → ~54 dBHz


def snr_to_cnr(snr_digit: int) -> float:
    if snr_digit <= 0:
        return 0.0
    return float((snr_digit - 1) * 6 + 6)


# ─── NMEA Parser ──────────────────────────────────────────────────────────────

class NmeaParser:
    """
    Parse NMEA 0183 sentences from Septentrio Mosaic-X5C and similar receivers.

    Supports two receiver output profiles:
      Profile A (our scenarios):  GGA, GNS (multi-constellation), GSA, GST, GBS
      Profile B (supervisor veh): GGA, GSA, GSV (multi-constellation)

    Returns a list of epoch dicts, one per second (or per GGA sentence).
    """

    def __init__(self, date_hint: Optional[datetime] = None):
        """
        Args:
            date_hint: Date to attach to NMEA times (NMEA GGA has time but not date).
                       If None, defaults to today.
        """
        self.date_hint = date_hint or datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def parse_file(self, nmea_path: Path) -> pd.DataFrame:
        """Parse a single NMEA file and return per-epoch DataFrame."""
        with open(nmea_path, "rb") as fh:
            raw = fh.read()
        text = raw.decode("latin-1", errors="replace")
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        epochs: list[dict] = []
        current: dict = {}
        gsv_buffer: dict[str, list[float]] = defaultdict(
            list)  # constellation → [cnr]
        gsa_dops: list[tuple] = []  # [(pdop, hdop, vdop), ...]

        for raw_line in lines:
            line = raw_line.strip()
            if not line.startswith("$"):
                continue
            # Strip checksum
            if "*" in line:
                line = line[: line.rfind("*")]
            parts = line.split(",")
            if len(parts) < 2:
                continue
            talker_sentence = parts[0][1:]  # e.g. "GPGGA", "GNGNS"
            sentence = talker_sentence[-3:]  # last 3 chars: "GGA", "GNS", etc.
            talker = talker_sentence[:-3]   # "GP", "GN", "GL", etc.

            try:
                if sentence == "GGA":
                    if current:
                        current = self._finalize_epoch(
                            current, gsv_buffer, gsa_dops)
                        epochs.append(current)
                        gsv_buffer = defaultdict(list)
                        gsa_dops = []
                    current = self._parse_gga(parts)

                elif sentence == "GNS":
                    # $GNGNS gives total multi-constellation satellite count
                    self._parse_gns(parts, current, talker)

                elif sentence == "GSA":
                    dop = self._parse_gsa(parts)
                    if dop:
                        gsa_dops.append(dop)

                elif sentence == "GST":
                    self._parse_gst(parts, current)

                elif sentence == "GBS":
                    self._parse_gbs(parts, current)

                elif sentence == "GSV":
                    self._parse_gsv(parts, talker, gsv_buffer)

                elif sentence == "RMC":
                    self._parse_rmc_date(parts)

            except Exception:
                pass  # Skip malformed sentences

        # Don't forget last epoch
        if current:
            current = self._finalize_epoch(current, gsv_buffer, gsa_dops)
            epochs.append(current)

        if not epochs:
            log.warning(f"No epochs parsed from {nmea_path}")
            return pd.DataFrame()

        df = pd.DataFrame(epochs)
        # Keep no-fix rows (lat/lon=NaN, fix_quality=0) — they represent DEGRADED periods
        # (e.g. complete blockage in Scenario A/E). Only drop rows with no timestamp.
        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        log.info(
            f"  NMEA: {len(df)} epochs  "
            f"[{df['timestamp'].iloc[0].strftime('%H:%M:%S')} – "
            f"{df['timestamp'].iloc[-1].strftime('%H:%M:%S')}]  "
            f"from {nmea_path.name}"
        )
        return df

    # ── sentence parsers ──────────────────────────────────────────────────────

    def _parse_gga(self, p: list[str]) -> dict:
        """$xxGGA,time,lat,N,lon,E,quality,nsat,hdop,alt,M,sep,M,age,ref"""
        epoch: dict = {}
        if len(p) < 10:
            return epoch
        epoch["timestamp"] = self._parse_time(p[1])
        epoch["lat"] = self._parse_lat(p[2], p[3])
        epoch["lon"] = self._parse_lon(p[4], p[5])
        epoch["fix_quality"] = int(p[6]) if p[6] else 0
        epoch["num_sats"] = int(p[7]) if p[7] else 0
        epoch["hdop"] = float(p[8]) if p[8] else np.nan
        epoch["alt"] = float(p[9]) if p[9] else np.nan
        epoch["solution_age"] = float(p[13]) if len(p) > 13 and p[13] else 0.0
        return epoch

    def _parse_gns(self, p: list[str], epoch: dict, talker: str):
        """$GxGNS gives per-constellation satellite counts; $GNGNS gives combined total."""
        if not epoch:
            return
        if len(p) < 8:
            return
        sats = int(p[7]) if p[7] else 0
        if talker == "GN":
            epoch["num_sats_total"] = sats  # combined multi-constellation
        elif talker == "GP":
            epoch["gps_sats"] = sats
        elif talker == "GL":
            epoch["glo_sats"] = sats
        elif talker == "GA":
            epoch["gal_sats"] = sats
        elif talker == "GB":
            epoch["bds_sats"] = sats

    def _parse_gsa(self, p: list[str]) -> Optional[tuple]:
        """$xxGSA,auto,fix,sv1..12,pdop,hdop,vdop  → (pdop, hdop, vdop)"""
        if len(p) < 18:
            return None
        try:
            pdop = float(p[15]) if p[15] else np.nan
            hdop = float(p[16]) if p[16] else np.nan
            vdop = float(p[17]) if p[17] else np.nan
            return (pdop, hdop, vdop)
        except (ValueError, IndexError):
            return None

    def _parse_gst(self, p: list[str], epoch: dict):
        """$GPGST,time,rms,semi_maj,semi_min,orient,lat_sig,lon_sig,alt_sig"""
        if not epoch or len(p) < 9:
            return
        try:
            epoch["rms_error"] = float(p[2]) if p[2] else np.nan
            epoch["lat_sigma"] = float(p[6]) if p[6] else np.nan
            epoch["lon_sigma"] = float(p[7]) if p[7] else np.nan
            epoch["alt_sigma"] = float(p[8]) if p[8] else np.nan
        except (ValueError, IndexError):
            pass

    def _parse_gbs(self, p: list[str], epoch: dict):
        """$GPGBS,time,lat_err,lon_err,alt_err,prn,prob,bias,rms"""
        if not epoch or len(p) < 8:
            return
        try:
            epoch["gbs_lat_err"] = float(p[2]) if p[2] else np.nan
            epoch["gbs_lon_err"] = float(p[3]) if p[3] else np.nan
            epoch["gbs_alt_err"] = float(p[4]) if p[4] else np.nan
        except (ValueError, IndexError):
            pass

    def _parse_gsv(self, p: list[str], talker: str, gsv_buffer: dict):
        """
        $xxGSV,total_msgs,msg_num,total_sats[,prn,elev,azimuth,snr]*4
        SNR is C/N0 in dBHz (0 = not tracked).
        Talker: GP=GPS, GL=GLONASS, GA=Galileo, GB=BeiDou
        """
        constellation_map = {"GP": "gps", "GL": "glo", "GA": "gal",
                             "GB": "bds", "GQ": "qzss", "GI": "irnss"}
        const = constellation_map.get(talker, talker.lower())
        # Fields: [0]=sentence, [1]=total_msgs, [2]=msg_num, [3]=total_sats,
        #         then groups of 4: prn, elev, azimuth, snr
        i = 4
        while i + 3 <= len(p):
            snr_str = p[i + 3]
            if snr_str:
                try:
                    snr = float(snr_str)
                    if snr > 0:
                        gsv_buffer[const].append(snr)
                except ValueError:
                    pass
            i += 4

    def _parse_rmc_date(self, p: list[str]):
        """$xxRMC contains date (DDMMYY) — update date_hint if available."""
        if len(p) > 9 and p[9] and len(p[9]) == 6:
            try:
                dd, mm, yy = int(p[9][:2]), int(p[9][2:4]), int(p[9][4:6])
                year = 2000 + yy if yy < 80 else 1900 + yy
                self.date_hint = datetime(year, mm, dd, tzinfo=timezone.utc)
            except (ValueError, OverflowError):
                pass

    def _finalize_epoch(
        self, epoch: dict, gsv_buffer: dict, gsa_dops: list
    ) -> dict:
        """Attach aggregated GSV C/N0 and GSA DOP values to the epoch."""
        # Aggregate GSV per-satellite C/N0 into a list
        all_cnr: list[float] = []
        for cnr_list in gsv_buffer.values():
            all_cnr.extend(cnr_list)
        epoch["cnr_list"] = all_cnr if all_cnr else []

        # Best DOP: use the last GSA if multiple (combined solution is last)
        if gsa_dops:
            last = gsa_dops[-1]
            if not math.isnan(last[0]):
                epoch.setdefault("pdop", last[0])
            if not math.isnan(last[1]):
                epoch.setdefault("hdop", last[1])
            if not math.isnan(last[2]):
                epoch.setdefault("vdop", last[2])

        # num_sats: prefer combined GNS total, fall back to GGA
        epoch["num_satellites"] = epoch.pop(
            "num_sats_total", epoch.get("num_sats", 0)
        )

        return epoch

    # ── helpers ───────────────────────────────────────────────────────────────

    def _parse_time(self, t: str) -> Optional[datetime]:
        """Parse HHMMSS.SS → datetime (using stored date_hint)."""
        if not t or len(t) < 6:
            return None
        try:
            hh = int(t[0:2])
            mm = int(t[2:4])
            ss_f = float(t[4:])
            ss = int(ss_f)
            us = int(round((ss_f - ss) * 1e6))
            return self.date_hint.replace(
                hour=hh, minute=mm, second=ss, microsecond=us
            )
        except (ValueError, OverflowError):
            return None

    @staticmethod
    def _parse_lat(val: str, hemi: str) -> Optional[float]:
        if not val:
            return None
        try:
            deg = float(val[:2])
            minutes = float(val[2:])
            lat = deg + minutes / 60.0
            return -lat if hemi.upper() == "S" else lat
        except ValueError:
            return None

    @staticmethod
    def _parse_lon(val: str, hemi: str) -> Optional[float]:
        if not val:
            return None
        try:
            deg = float(val[:3])
            minutes = float(val[3:])
            lon = deg + minutes / 60.0
            return -lon if hemi.upper() == "W" else lon
        except ValueError:
            return None


# ─── RINEX 3 Observation Parser ───────────────────────────────────────────────

class Rinex3ObsParser:
    """
    Parse RINEX 3.xx observation files to extract per-epoch C/N0 and cycle slips.

    Two modes:
      'snr_indicator' — for Septentrio receivers that do NOT include S1C.
                        Uses the 0-9 SNR digit appended to each observation value
                        and converts to approximate dBHz via snr_to_cnr().
      'direct_s1c'   — for receivers (Unicore, u-blox, NovAtel) that include S1C.
                        Reads the S1C field as actual dBHz value.

    Returns per-epoch dict: {datetime: {'cnr_list': [...], 'cycle_slips': int, 'date': date}}
    """

    def __init__(self, mode: str = "snr_indicator"):
        assert mode in ("snr_indicator", "direct_s1c"), f"Unknown mode: {mode}"
        self.mode = mode

    def parse_file(self, obs_path: Path) -> dict[datetime, dict]:
        """
        Returns: {gps_datetime: {'cnr_list': [float, ...], 'cycle_slips': int}}
        Timestamps are in GPS time (NOT converted to UTC here).
        """
        epochs: dict[datetime, dict] = {}
        obs_types: dict[str, list[str]] = {}

        in_header = True
        cur_dt: Optional[datetime] = None
        cur_sats: list[str] = []
        cur_cnr: list[float] = []
        cur_slips: int = 0
        sat_idx: int = 0

        with open(obs_path, encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line = raw_line.rstrip("\n")

                # ── header parsing ────────────────────────────────────────────
                if in_header:
                    if "SYS / # / OBS TYPES" in line[60:]:
                        sys_char = line[0]
                        if sys_char.strip():
                            # Count obs types (may continue on next line with blank sys char)
                            n_obs = int(line[3:6].strip() or 0)
                            obs_list = line[7:60].split()
                            obs_types[sys_char] = obs_list
                        else:
                            # Continuation line
                            last_sys = list(
                                obs_types.keys())[-1] if obs_types else None
                            if last_sys:
                                obs_types[last_sys].extend(line[7:60].split())
                    if "END OF HEADER" in line:
                        in_header = False
                    continue

                # ── epoch header: starts with '>' ─────────────────────────────
                if line.startswith(">"):
                    # Save previous epoch
                    if cur_dt is not None and cur_cnr:
                        epochs[cur_dt] = {
                            "cnr_list": cur_cnr,
                            "cycle_slips": cur_slips,
                        }
                    # Parse new epoch header: > YYYY MM DD HH MM SS.SSSSSSS  flag n_sats
                    tok = line[1:].split()
                    if len(tok) < 6:
                        cur_dt = None
                        continue
                    yr, mo, dy = int(tok[0]), int(tok[1]), int(tok[2])
                    hh, mm = int(tok[3]), int(tok[4])
                    sec_f = float(tok[5])
                    isec = int(sec_f)
                    usec = int(round((sec_f - isec) * 1e6))
                    cur_dt = datetime(yr, mo, dy, hh, mm, isec, usec,
                                      tzinfo=timezone.utc)
                    n_sats_in_epoch = int(tok[7]) if len(tok) > 7 else 0
                    cur_sats = []
                    cur_cnr = []
                    cur_slips = 0
                    sat_idx = 0
                    continue

                # ── observation record (satellite line) ───────────────────────
                if cur_dt is None or len(line) < 3:
                    continue
                if line[0] in ("G", "R", "E", "C", "J", "S", "I") and len(line) >= 3:
                    sys_char = line[0]
                    sat_id = line[0:3].strip()
                    obs_data = line[3:]

                    types_for_sys = obs_types.get(sys_char, [])
                    cnr_from_sat = self._extract_cnr(obs_data, types_for_sys)
                    slips_from_sat = self._extract_cycle_slips(
                        obs_data, types_for_sys)

                    if cnr_from_sat:
                        cur_cnr.extend(cnr_from_sat)
                    cur_slips += slips_from_sat

        # Save last epoch
        if cur_dt is not None and cur_cnr:
            epochs[cur_dt] = {"cnr_list": cur_cnr, "cycle_slips": cur_slips}

        log.info(
            f"  RINEX: {len(epochs)} epochs  "
            f"mode={self.mode}  from {obs_path.name}"
        )
        return epochs

    def _extract_cnr(self, obs_data: str, obs_types: list[str]) -> list[float]:
        """
        Extract C/N0 values from a satellite observation record line.

        For mode='snr_indicator': takes the BEST (max) SNR digit across all
        observation types for this satellite (one C/N0 per satellite, not per band).
        This avoids double-counting multi-frequency pseudoranges and gives a
        representative C/N0 for the satellite.

        For mode='direct_s1c': takes the mean of all S1C values present.
        """
        field_width = 16

        if self.mode == "direct_s1c":
            # Return the BEST (max) S-type value per satellite.
            # One C/N0 entry per satellite ensures correct satellite count later.
            best_cnr: Optional[float] = None
            for i, obs_type in enumerate(obs_types):
                if not obs_type.startswith("S"):
                    continue
                start = i * field_width
                field = obs_data[start:start +
                                 field_width] if start < len(obs_data) else ""
                val_str = field[:14].strip() if len(field) >= 14 else ""
                if val_str:
                    try:
                        val = float(val_str)
                        if 0 < val < 70:
                            best_cnr = max(
                                best_cnr, val) if best_cnr is not None else val
                    except ValueError:
                        pass
            return [best_cnr] if best_cnr is not None else []

        else:  # snr_indicator
            # Collect best SNR digit across all obs for this satellite
            best_snr = 0
            for i, obs_type in enumerate(obs_types):
                start = i * field_width
                field = obs_data[start:start +
                                 field_width] if start < len(obs_data) else ""
                snr_char = field[15:16] if len(field) >= 16 else ""
                if snr_char and snr_char.isdigit():
                    best_snr = max(best_snr, int(snr_char))
            if best_snr > 0:
                return [snr_to_cnr(best_snr)]
            return []

    def _extract_cycle_slips(self, obs_data: str, obs_types: list[str]) -> int:
        """Count cycle slips (LLI bit 0 set in carrier phase observations)."""
        slips = 0
        field_width = 16
        for i, obs_type in enumerate(obs_types):
            if not obs_type.startswith("L"):
                continue
            start = i * field_width
            lli_pos = start + 14
            if lli_pos < len(obs_data):
                lli_char = obs_data[lli_pos]
                if lli_char.isdigit() and int(lli_char) & 0x01:
                    slips += 1
        return slips


# ─── Feature Computer ─────────────────────────────────────────────────────────

ALL_FEATURES = [
    # G1 - Position
    "lat", "lon", "alt", "lat_std", "lon_std",
    # G2 - Signal Strength
    "mean_cnr", "min_cnr", "max_cnr", "std_cnr", "cnr_trend",
    # G3 - Satellite Count
    "num_satellites", "sat_mean", "sat_min", "sat_visibility", "sat_drop_rate",
    # G4 - DOP
    "pdop", "hdop", "vdop", "gdop", "dop_ratio",
    # G5 - Receiver Status
    "solution_status", "baseline_sats", "solution_age", "fix_continuity", "fix_transitions",
    # G6 - Temporal Patterns
    "position_variance", "cnr_variance", "elevation_violations", "multipath", "clock_bias",
    # G7 - Atmospheric Effects
    "iono_delay", "tropo_delay", "cycle_slips", "residual_mean", "residual_std",
]


def compute_features(
    epoch_df: pd.DataFrame,
    window_sec: int = WINDOW_SECONDS,
) -> pd.DataFrame:
    """
    Apply a sliding window over the epoch DataFrame and compute all 35 features.

    Args:
        epoch_df: DataFrame with per-epoch columns (output of merge_epoch_data).
        window_sec: Window length in seconds.

    Returns:
        DataFrame with one row per epoch (after warm-up), 35 feature columns,
        plus metadata columns: timestamp, source, scenario, label.
    """
    if len(epoch_df) < 2:
        log.warning("Epoch data too short for feature computation.")
        return pd.DataFrame()

    df = epoch_df.copy().reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    results = []

    for idx in range(len(df)):
        t_now = df.loc[idx, "timestamp"]
        t_start = t_now - timedelta(seconds=window_sec)
        window = df[df["timestamp"] >= t_start].loc[:idx]

        if len(window) < 2:
            continue  # Not enough data for window features yet

        current = df.loc[idx]
        feats = _compute_single_epoch_features(window, current)
        feats["timestamp"] = t_now
        feats["source"] = current.get("source", "unknown")
        feats["scenario"] = current.get("scenario", "unknown")
        results.append(feats)

    if not results:
        return pd.DataFrame()

    feat_df = pd.DataFrame(results)

    # Reorder columns
    meta_cols = ["timestamp", "source", "scenario"]
    feat_cols = [c for c in ALL_FEATURES if c in feat_df.columns]
    feat_df = feat_df[meta_cols + feat_cols].copy()

    # Assign labels
    feat_df["label"] = feat_df.apply(_assign_label, axis=1)
    feat_df["label_name"] = feat_df["label"].map(
        {0: "CLEAN", 1: "WARNING", 2: "DEGRADED"})

    return feat_df


def _compute_single_epoch_features(window: pd.DataFrame, current: pd.Series) -> dict:
    """Compute all 35 features for one epoch given a 30s sliding window."""
    f: dict = {}

    # ── G1: Position (5) ─────────────────────────────────────────────────────
    f["lat"] = current.get("lat", np.nan)
    f["lon"] = current.get("lon", np.nan)
    f["alt"] = current.get("alt", np.nan)
    f["lat_std"] = float(window["lat_sigma"].mean(
    )) if "lat_sigma" in window.columns and window["lat_sigma"].notna().any() else np.nan
    f["lon_std"] = float(window["lon_sigma"].mean(
    )) if "lon_sigma" in window.columns and window["lon_sigma"].notna().any() else np.nan

    # ── G2: Signal Strength / C/N0 (5) ───────────────────────────────────────
    # Build per-epoch mean C/N0 series across window
    cnr_series = []
    if "mean_cnr_epoch" in window.columns:
        cnr_series = window["mean_cnr_epoch"].dropna().tolist()
    if not cnr_series:
        # Fallback: estimate from fix quality
        fix_qual = current.get("fix_quality", 0)
        cnr_estimate = {4: 48.0, 5: 35.0, 1: 40.0, 2: 42.0, 3: 38.0, 0: 20.0}
        cnr_series = [cnr_estimate.get(
            int(fix_qual) if not math.isnan(fix_qual) else 0, 30.0)]

    f["mean_cnr"] = float(np.mean(cnr_series))
    f["min_cnr"] = float(np.min(cnr_series))
    f["max_cnr"] = float(np.max(cnr_series))
    f["std_cnr"] = float(np.std(cnr_series)) if len(cnr_series) > 1 else 0.0
    # Trend: slope of mean C/N0 over window (positive = improving, negative = degrading)
    if len(cnr_series) >= 3:
        x = np.arange(len(cnr_series), dtype=float)
        try:
            slope = np.polyfit(x, cnr_series, 1)[0]
            f["cnr_trend"] = float(slope)
        except Exception:
            f["cnr_trend"] = 0.0
    else:
        f["cnr_trend"] = 0.0

    # ── G3: Satellite Count (5) ───────────────────────────────────────────────
    sat_col = "num_satellites" if "num_satellites" in window.columns else "num_sats"
    ns_series = window[sat_col].dropna(
    ) if sat_col in window.columns else pd.Series([8])
    f["num_satellites"] = float(current.get(
        sat_col, ns_series.iloc[-1] if len(ns_series) > 0 else 0))
    f["sat_mean"] = float(ns_series.mean()) if len(ns_series) > 0 else 0.0
    f["sat_min"] = float(ns_series.min()) if len(ns_series) > 0 else 0.0
    f["sat_visibility"] = min(f["num_satellites"] / MAX_MULTI_CONST_SATS, 1.0)
    # Rate of sat count decrease: negative diff events per window second
    if len(ns_series) > 1:
        diffs = ns_series.diff().dropna()
        drop_sum = float(diffs[diffs < 0].sum())
        duration_s = max((window["timestamp"].iloc[-1] -
                         window["timestamp"].iloc[0]).total_seconds(), 1.0)
        f["sat_drop_rate"] = drop_sum / duration_s
    else:
        f["sat_drop_rate"] = 0.0

    # ── G4: DOP (5) ──────────────────────────────────────────────────────────
    pdop_col = window["pdop"].dropna(
    ) if "pdop" in window.columns else pd.Series([2.5])
    hdop_col = window["hdop"].dropna(
    ) if "hdop" in window.columns else pd.Series([1.5])
    vdop_col = window["vdop"].dropna(
    ) if "vdop" in window.columns else pd.Series([1.5])
    f["pdop"] = float(current.get("pdop", pdop_col.iloc[-1]
                      if len(pdop_col) > 0 else 2.5))
    f["hdop"] = float(current.get("hdop", hdop_col.iloc[-1]
                      if len(hdop_col) > 0 else 1.5))
    f["vdop"] = float(current.get("vdop", vdop_col.iloc[-1]
                      if len(vdop_col) > 0 else 1.5))
    # GDOP ≈ sqrt(PDOP² + TDOP²). TDOP ~ PDOP / sqrt(n_sats); approximate as PDOP * 1.1
    f["gdop"] = float(math.sqrt(
        f["pdop"] ** 2 + max(f["pdop"] / max(f["num_satellites"], 1), 0.5) ** 2))
    vdop_safe = f["vdop"] if f["vdop"] > 0 else 1.0
    f["dop_ratio"] = f["hdop"] / vdop_safe

    # ── G5: Receiver / Solution Status (5) ───────────────────────────────────
    fq = int(current.get("fix_quality", 0))
    # Normalize fix quality: 1→RTK fixed (best), 2→DGPS, 3→SBAS, 4→RTK fixed, 5→RTK float, 0→no fix
    quality_score = {4: 1.0, 1: 0.8, 2: 0.85, 3: 0.7, 5: 0.5, 6: 0.4, 0: 0.0}
    f["solution_status"] = quality_score.get(fq, 0.3)
    f["baseline_sats"] = f["num_satellites"]
    f["solution_age"] = float(current.get("solution_age", 0.0))
    # Fix continuity: fraction of window epochs with fix_quality >= 1
    if "fix_quality" in window.columns:
        fq_series = window["fix_quality"].fillna(0)
        f["fix_continuity"] = float((fq_series >= 1).mean())
        f["fix_transitions"] = float((fq_series.diff().fillna(0) != 0).sum())
    else:
        f["fix_continuity"] = 1.0 if fq >= 1 else 0.0
        f["fix_transitions"] = 0.0

    # ── G6: Temporal Patterns (5) ────────────────────────────────────────────
    # Position variance: variance of lat_sigma + lon_sigma over window
    if "lat_sigma" in window.columns and window["lat_sigma"].notna().any():
        lat_var = float(window["lat_sigma"].dropna().var())
        lon_var = float(window["lon_sigma"].dropna().var()
                        ) if "lon_sigma" in window.columns else 0.0
        f["position_variance"] = lat_var + lon_var
    else:
        # Proxy from DOP: higher DOP → higher expected position variance
        f["position_variance"] = (f["hdop"] * 2.5) ** 2
    f["cnr_variance"] = f["std_cnr"] ** 2
    # Elevation violations: proxy for low-elevation tracked satellites
    # More satellites than expected for geometry → some likely near horizon
    f["elevation_violations"] = max(
        0.0, (f["num_satellites"] - 20) / 20.0) if f["num_satellites"] > 0 else 0.0
    # Multipath indicator: high position variance + low C/N0 → likely multipath
    mean_cnr_safe = max(f["mean_cnr"], 1.0)
    f["multipath"] = f["position_variance"] * (50.0 / mean_cnr_safe)
    # Clock bias proxy: rate of change of solution_age over window
    if "solution_age" in window.columns and window["solution_age"].notna().any():
        age_series = window["solution_age"].dropna()
        f["clock_bias"] = float(age_series.diff().fillna(0).abs().mean())
    else:
        f["clock_bias"] = float(f["solution_age"])

    # ── G7: Atmospheric Effects (5) ──────────────────────────────────────────
    # Ionospheric delay proxy: dual-frequency pseudorange difference
    # Without dual-frequency data, use 0 (honest: not computable from NMEA only)
    f["iono_delay"] = 0.0
    # Tropospheric delay: rough altitude-based Hopfield model proxy
    alt_m = f["alt"] if not math.isnan(f["alt"]) else 50.0
    f["tropo_delay"] = max(0.0, 2.3 - 0.0116 * max(alt_m, 0))  # simplified
    # Cycle slips: from RINEX LLI flags
    f["cycle_slips"] = float(current.get("cycle_slips_epoch", 0.0))
    # Residuals: from GPGST rms_error or GPGBS
    if "rms_error" in window.columns and window["rms_error"].notna().any():
        f["residual_mean"] = float(window["rms_error"].dropna().mean())
        f["residual_std"] = float(window["rms_error"].dropna().std(
        )) if window["rms_error"].dropna().shape[0] > 1 else 0.0
    elif "gbs_lat_err" in window.columns and window["gbs_lat_err"].notna().any():
        combined_err = np.sqrt(
            window["gbs_lat_err"].fillna(0) ** 2 +
            window["gbs_lon_err"].fillna(0) ** 2
        )
        f["residual_mean"] = float(combined_err.mean())
        f["residual_std"] = float(combined_err.std()) if len(
            combined_err) > 1 else 0.0
    else:
        # Fallback: estimate from position accuracy and DOP
        f["residual_mean"] = f["hdop"] * 2.0
        f["residual_std"] = f["std_cnr"] * 0.1

    return f


def _assign_label(row: pd.Series) -> int:
    """
    Assign CLEAN (0), WARNING (1), or DEGRADED (2) based on signal metrics.

    Priority: DEGRADED > WARNING > CLEAN (most severe condition wins).

    NaN-aware: if a feature is NaN its condition is skipped (neither helps
    CLEAN nor triggers DEGRADED).  This handles legacy datasets (NCLT, Oxford)
    that lack C/N0 or DOP data — callers may override labels separately.

    Decision logic (all thresholds in LABEL_THRESHOLDS dict):
      DEGRADED : ANY one non-NaN critical condition breached
      CLEAN    : ALL non-NaN good-signal conditions simultaneously satisfied
      WARNING  : everything else (partial degradation / transitional)
    """
    t = LABEL_THRESHOLDS

    # Retrieve raw values — keep NaN so conditions can be skipped
    cnr_raw = row.get("mean_cnr", np.nan)
    hdop_raw = row.get("hdop", np.nan)
    pdop_raw = row.get("pdop", np.nan)
    nsv_raw = row.get("num_satellites", np.nan)
    sol_raw = row.get("solution_status", np.nan)

    cnr_na = pd.isna(cnr_raw)
    hdop_na = pd.isna(hdop_raw)
    pdop_na = pd.isna(pdop_raw)
    nsv_na = pd.isna(nsv_raw)
    sol_na = pd.isna(sol_raw)

    # DEGRADED: any one non-NaN critical threshold breached
    if (
        (not cnr_na and cnr_raw < t["degraded_max_cnr"])
        or (not hdop_na and hdop_raw > t["degraded_min_hdop"])
        or (not pdop_na and pdop_raw > t["degraded_min_pdop"])
        or (not nsv_na and nsv_raw < t["degraded_max_sats"])
        or (not sol_na and sol_raw == 0.0)
    ):
        return 2

    # CLEAN: all *available* conditions satisfied (at least one must be present)
    clean_conditions = []
    if not cnr_na:
        clean_conditions.append(cnr_raw >= t["clean_min_cnr"])
    if not hdop_na:
        clean_conditions.append(hdop_raw <= t["clean_max_hdop"])
    if not pdop_na:
        clean_conditions.append(pdop_raw <= t["clean_max_pdop"])
    if not nsv_na:
        clean_conditions.append(nsv_raw >= t["clean_min_sats"])
    if not sol_na:
        clean_conditions.append(sol_raw > 0.0)

    if clean_conditions and all(clean_conditions):
        return 0

    # WARNING: everything else (transitional / marginal)
    return 1


# ─── Epoch Data Merger ────────────────────────────────────────────────────────

def merge_nmea_rinex(
    nmea_df: pd.DataFrame,
    rinex_epochs: dict,
    leap_seconds: int = GPS_LEAP_SECONDS,
) -> pd.DataFrame:
    """
    Merge NMEA epoch DataFrame with RINEX C/N0 data.

    RINEX epochs are in GPS time; we convert to UTC by subtracting leap_seconds.
    Matching is done by nearest-second timestamp.
    """
    if rinex_epochs:
        # Build RINEX DataFrame
        rinex_rows = []
        for gps_dt, data in rinex_epochs.items():
            utc_dt = gps_dt - timedelta(seconds=leap_seconds)
            cnr_list = data.get("cnr_list", [])
            rinex_rows.append({
                "timestamp_rinex": utc_dt,
                "mean_cnr_epoch": float(np.mean(cnr_list)) if cnr_list else np.nan,
                "cycle_slips_epoch": data.get("cycle_slips", 0),
            })
        rinex_df = pd.DataFrame(rinex_rows)
        rinex_df["timestamp_rinex"] = pd.to_datetime(
            rinex_df["timestamp_rinex"], utc=True)
        rinex_df = rinex_df.sort_values("timestamp_rinex")

        # Merge on nearest second
        nmea_df = nmea_df.copy()
        nmea_df["timestamp"] = pd.to_datetime(nmea_df["timestamp"], utc=True)
        nmea_df = nmea_df.sort_values("timestamp")

        merged = pd.merge_asof(
            nmea_df,
            rinex_df,
            left_on="timestamp",
            right_on="timestamp_rinex",
            tolerance=pd.Timedelta("2s"),
            direction="nearest",
        )
        merged = merged.drop(columns=["timestamp_rinex"], errors="ignore")
        return merged
    else:
        # No RINEX: compute mean_cnr from NMEA GSV cnr_list if available
        nmea_df = nmea_df.copy()
        if "cnr_list" in nmea_df.columns:
            nmea_df["mean_cnr_epoch"] = nmea_df["cnr_list"].apply(
                lambda x: float(np.mean(x)) if isinstance(
                    x, list) and x else np.nan
            )
        nmea_df["cycle_slips_epoch"] = 0
        return nmea_df


# ─── Source-Specific Processors ───────────────────────────────────────────────

def extract_rinex_date(obs_path: Path) -> Optional[datetime]:
    """Extract the date of observation from RINEX 3 header."""
    try:
        with open(obs_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "TIME OF FIRST OBS" in line[60:]:
                    parts = line[:60].split()
                    if len(parts) >= 3:
                        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                        return datetime(y, m, d, tzinfo=timezone.utc)
                if "END OF HEADER" in line:
                    break
    except Exception:
        pass
    return None


def process_scenario_folder(
    folder: Path,
    scenario_label: str,
    source_tag: str,
) -> pd.DataFrame:
    """
    Process a single scenario collection folder.
    Expected contents: log_0000.nmea [+ SEPT125x.26O RINEX obs]
    """
    nmea_file = folder / "log_0000.nmea"
    if not nmea_file.exists():
        log.warning(f"  No NMEA found in {folder}")
        return pd.DataFrame()

    # Find RINEX obs file — prefer the LAST (highest session number) .xxO file.
    # Septentrio names files SEPT125{0,1,2}.26O where 1 is the rover and 0 may
    # be the base station reference; taking the last avoids picking the base.
    rinex_obs = None
    for pattern in ["*.26O", "*.25O", "*.24O", "*.23O"]:
        candidates = sorted(folder.glob(pattern))
        if candidates:
            # Prefer the highest-numbered obs file (rover session)
            rinex_obs = candidates[-1]
            break

    # Extract date hint from RINEX header (if available)
    date_hint = None
    if rinex_obs:
        date_hint = extract_rinex_date(rinex_obs)

    log.info(f"Processing scenario folder: {folder.name}")
    log.info(
        f"  NMEA: {nmea_file.name}  RINEX: {rinex_obs.name if rinex_obs else 'None'}")

    # Parse NMEA
    parser = NmeaParser(date_hint=date_hint)
    nmea_df = parser.parse_file(nmea_file)
    if nmea_df.empty:
        return pd.DataFrame()

    # Parse RINEX for C/N0
    rinex_epochs: dict = {}
    if rinex_obs:
        rinex_parser = Rinex3ObsParser(mode="snr_indicator")
        rinex_epochs = rinex_parser.parse_file(rinex_obs)

    # Merge
    epoch_df = merge_nmea_rinex(nmea_df, rinex_epochs)
    epoch_df["source"] = source_tag
    epoch_df["scenario"] = scenario_label

    # Compute features
    feat_df = compute_features(epoch_df)
    log.info(
        f"  → {len(feat_df)} feature rows, label dist: {feat_df['label'].value_counts().to_dict()}")
    return feat_df


def process_scenarios() -> pd.DataFrame:
    """Process all scenario folders (A, B, C, D, E)."""
    base = Path("data/raw/scenarios")
    all_dfs = []

    # Mapping: (folder_path, scenario_label, source_tag)
    scenario_map = [
        # Scenario A: Instant Blockage (3 runs)
        (base / "scenario_a" / "A",  "scenario_a", "scenario_a_r1"),
        (base / "scenario_a" / "A2", "scenario_a", "scenario_a_r2"),
        (base / "scenario_a" / "A3", "scenario_a", "scenario_a_r3"),
        # Scenario B: Urban Canyon (2 runs)
        (base / "scenario_b" / "B",  "scenario_b", "scenario_b_r1"),
        (base / "scenario_b" / "B2", "scenario_b", "scenario_b_r2"),
        # Scenario C: Partial Blockage / Trees (2 runs)
        (base / "scenario_c" / "C",  "scenario_c", "scenario_c_r1"),
        (base / "scenario_c" / "C2", "scenario_c", "scenario_c_r2"),
        # Scenario D: Open Sky (1 run — largest dataset)
        (base / "scenario_d" / "D",  "scenario_d", "scenario_d_r1"),
        # Scenario E: Approaching Blockage (master run + 3 repeats)
        (base / "scenario_a_to_e",         "scenario_e", "scenario_e_master"),
        (base / "scenario_a_to_e" / "E",   "scenario_e", "scenario_e_r1"),
        (base / "scenario_a_to_e" / "E2",  "scenario_e", "scenario_e_r2"),
        (base / "scenario_a_to_e" / "E3",  "scenario_e", "scenario_e_r3"),
    ]

    for folder, scenario_label, source_tag in scenario_map:
        if not folder.exists():
            log.warning(f"Folder not found: {folder}")
            continue
        df = process_scenario_folder(folder, scenario_label, source_tag)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        log.error("No scenario data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save per-scenario CSVs
    for scenario in combined["scenario"].unique():
        subset = combined[combined["scenario"] == scenario]
        out_path = out_dir / f"{scenario}_features.csv"
        subset.to_csv(out_path, index=False)
        log.info(f"Saved {len(subset)} rows → {out_path}")

    # Save combined scenarios CSV
    combined_path = out_dir / "all_scenarios_features.csv"
    combined.to_csv(combined_path, index=False)
    log.info(f"Saved {len(combined)} total rows → {combined_path}")

    return combined


def process_supervisor_vehicle() -> pd.DataFrame:
    """Process supervisor vehicle experiments (exp1–exp4)."""
    base = Path("data/raw/supervisor/vehicle")
    all_dfs = []

    for exp_num in range(1, 5):
        exp_dir = base / f"exp{exp_num}"
        if not exp_dir.exists():
            continue

        log.info(f"Processing supervisor vehicle exp{exp_num}...")

        # exp3 and exp4 have a single top-level NMEA + RINEX OBS
        # exp1 and exp2 have multiple sub-session folders
        top_nmea = exp_dir / "log_0000.nmea"
        if top_nmea.exists():
            # Single session
            sessions = [(exp_dir, f"supervisor_vehicle_exp{exp_num}")]
        else:
            # Multiple sub-session folders
            sessions = []
            for sub in sorted(exp_dir.iterdir()):
                if sub.is_dir() and (sub / "log_0000.nmea").exists():
                    tag = f"supervisor_vehicle_exp{exp_num}_{sub.name.replace(' ', '_')}"
                    sessions.append((sub, tag))

        for sess_dir, source_tag in sessions:
            nmea_file = sess_dir / "log_0000.nmea"
            if not nmea_file.exists():
                continue

            # Find RINEX OBS for C/N0 (Septentrio RINEX — no S1C; but GSV in NMEA)
            # For supervisor vehicle, NMEA has GSV → no need for RINEX C/N0
            rinex_obs = None
            for pattern in ["*.25O", "*.26O", "*.24O"]:
                candidates = sorted(sess_dir.glob(pattern))
                if candidates:
                    # prefer highest session = rover
                    rinex_obs = candidates[-1]
                    break

            # Date hint from RINEX header
            date_hint = extract_rinex_date(rinex_obs) if rinex_obs else None

            log.info(f"  Session: {source_tag}")
            parser = NmeaParser(date_hint=date_hint)
            nmea_df = parser.parse_file(nmea_file)
            if nmea_df.empty:
                continue

            # Supervisor NMEA has GSV → cnr_list already in nmea_df
            # Compute mean_cnr_epoch from the cnr_list
            epoch_df = merge_nmea_rinex(nmea_df, {})  # No RINEX C/N0 needed
            epoch_df["source"] = source_tag
            epoch_df["scenario"] = "supervisor_vehicle"

            feat_df = compute_features(epoch_df)
            if not feat_df.empty:
                all_dfs.append(feat_df)
                log.info(
                    f"    → {len(feat_df)} rows, labels: {feat_df['label'].value_counts().to_dict()}")

    if not all_dfs:
        log.error("No supervisor vehicle data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/supervisor/vehicle")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "supervisor_vehicle_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} supervisor vehicle rows → {out_path}")
    return combined


def process_supervisor_drone() -> pd.DataFrame:
    """Process supervisor drone RINEX obs files (no NMEA — RINEX only)."""
    base = Path("data/raw/supervisor/drone")
    all_dfs = []

    # Drone files: drone1_241h.24o, drone2_241h.24o, drone12_241h.24o
    # car0241h.24o = car (vehicle, not drone) — include as extra vehicle source
    obs_map = {
        "drone1_241h.24o":  ("supervisor_drone", "supervisor_drone_1"),
        "drone2_241h.24o":  ("supervisor_drone", "supervisor_drone_2"),
        "drone12_241h.24o": ("supervisor_drone", "supervisor_drone_12"),
        "car0241h.24o":     ("supervisor_car",   "supervisor_car_ref"),
    }

    rinex_parser = Rinex3ObsParser(mode="direct_s1c")

    for fname, (scenario_label, source_tag) in obs_map.items():
        obs_path = base / fname
        if not obs_path.exists():
            log.warning(f"  Drone obs not found: {obs_path}")
            continue

        log.info(f"Processing drone obs: {fname}")
        rinex_epochs = rinex_parser.parse_file(obs_path)
        if not rinex_epochs:
            continue

        # Build epoch DataFrame from RINEX only
        rows = []
        for gps_dt, data in sorted(rinex_epochs.items()):
            utc_dt = gps_dt - timedelta(seconds=GPS_LEAP_SECONDS)
            cnr_list = data.get("cnr_list", [])
            rows.append({
                "timestamp": utc_dt,
                "mean_cnr_epoch": float(np.mean(cnr_list)) if cnr_list else np.nan,
                "cycle_slips_epoch": data.get("cycle_slips", 0),
                "lat": np.nan, "lon": np.nan, "alt": np.nan,
                "fix_quality": 1,  # RINEX data assumes acquisition
                "num_satellites": len([c for c in cnr_list if c > 0]),
                "hdop": 1.5, "pdop": 2.0, "vdop": 1.5,
                "source": source_tag,
                "scenario": scenario_label,
            })

        epoch_df = pd.DataFrame(rows)
        epoch_df["timestamp"] = pd.to_datetime(epoch_df["timestamp"], utc=True)

        feat_df = compute_features(epoch_df)
        if not feat_df.empty:
            all_dfs.append(feat_df)
            log.info(
                f"  → {len(feat_df)} rows, labels: {feat_df['label'].value_counts().to_dict()}")

    if not all_dfs:
        log.error("No drone data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/supervisor/drone")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "supervisor_drone_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} drone rows → {out_path}")
    return combined


def process_urbannav() -> pd.DataFrame:
    """
    Process UrbanNav HK-Medium-Urban-1 for all available receivers.
    Uses the existing parse_gnss.py output (features CSV) if present,
    otherwise parses RINEX OBS + NMEA directly.
    """
    base = Path("data/raw/public/urbannav/urbanNav_Medium")
    all_dfs = []

    # Receiver list (filename stems)
    receivers = [
        "UrbanNav-HK-Medium-Urban-1.google.pixel4",
        "UrbanNav-HK-Medium-Urban-1.huawei.p40pro",
        "UrbanNav-HK-Medium-Urban-1.ublox.f9p",
        "UrbanNav-HK-Medium-Urban-1.ublox.f9p.splitter",
        "UrbanNav-HK-Medium-Urban-1.ublox.m8t.GC",
        "UrbanNav-HK-Medium-Urban-1.ublox.m8t.GEJ",
        "UrbanNav-HK-Medium-Urban-1.ublox.m8t.GR",
        "UrbanNav-HK-Medium-Urban-1.samsung.note8",
        "UrbanNav-HK-Medium-Urban-1.xiaomi.mi8",
        "UrbanNav-HK-Medium-Urban-1.novatel.flexpak6",
    ]

    rinex_parser = Rinex3ObsParser(mode="direct_s1c")
    nmea_parser = NmeaParser()

    for rec in receivers:
        obs_path = base / f"{rec}.obs"
        nmea_path = base / f"{rec}.nmea"
        pre_processed = base / f"{rec}_features.csv"

        if not obs_path.exists() and not pre_processed.exists():
            log.info(f"  Skipping {rec} — no obs or pre-processed file")
            continue

        log.info(f"Processing UrbanNav receiver: {rec}")
        source_tag = f"urbannav_{rec.split('.')[-1]}"
        # Use the simplified receiver name as the source tag
        parts = rec.split(".")
        # e.g. google.pixel4 → receiver_name = "pixel4" or full "google_pixel4"
        receiver_short = "_".join(parts[1:]) if len(parts) > 1 else rec
        source_tag = f"urbannav_{receiver_short}"

        # Parse RINEX OBS
        rinex_epochs: dict = {}
        if obs_path.exists():
            rinex_epochs = rinex_parser.parse_file(obs_path)

        # Parse NMEA (for position + DOP)
        nmea_df = pd.DataFrame()
        if nmea_path.exists():
            nmea_df = nmea_parser.parse_file(nmea_path)

        if not rinex_epochs and nmea_df.empty:
            continue

        if not nmea_df.empty and rinex_epochs:
            epoch_df = merge_nmea_rinex(
                nmea_df, rinex_epochs, leap_seconds=GPS_LEAP_SECONDS)
        elif not nmea_df.empty:
            epoch_df = merge_nmea_rinex(nmea_df, {})
        else:
            # RINEX only
            rows = []
            for gps_dt, data in sorted(rinex_epochs.items()):
                utc_dt = gps_dt - timedelta(seconds=GPS_LEAP_SECONDS)
                cnr_list = data.get("cnr_list", [])
                rows.append({
                    "timestamp": utc_dt,
                    "mean_cnr_epoch": float(np.mean(cnr_list)) if cnr_list else np.nan,
                    "cycle_slips_epoch": data.get("cycle_slips", 0),
                    "lat": np.nan, "lon": np.nan, "alt": np.nan,
                    "fix_quality": 1,
                    "num_satellites": len([c for c in cnr_list if c > 0]),
                    "hdop": 2.5, "pdop": 3.5, "vdop": 2.0,
                })
            epoch_df = pd.DataFrame(rows)

        epoch_df["source"] = source_tag
        epoch_df["scenario"] = "urbannav_hk_urban"

        feat_df = compute_features(epoch_df)
        if not feat_df.empty:
            all_dfs.append(feat_df)
            log.info(
                f"  → {len(feat_df)} rows, labels: {feat_df['label'].value_counts().to_dict()}")

    if not all_dfs:
        log.error("No UrbanNav data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/urbannav")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "urbannav_hk_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} UrbanNav rows → {out_path}")
    return combined


def _apply_position_sigma_labels(
    feat_df: pd.DataFrame,
    clean_sigma_m: float = 3.0,
    degraded_sigma_m: float = 10.0,
    clean_min_sats: int = 5,
    degraded_max_sats: int = 3,
) -> pd.DataFrame:
    """
    Override label column using position sigma (lat_std / lon_std) and
    satellite count.  Used for datasets that lack C/N0 (NCLT, Oxford).

    CLEAN:    lat_std < clean_sigma_m AND lon_std < clean_sigma_m AND sats >= clean_min_sats
    DEGRADED: lat_std > degraded_sigma_m OR lon_std > degraded_sigma_m OR sats < degraded_max_sats
    WARNING:  everything else
    """
    feat_df = feat_df.copy()

    def _sigma_label(row):
        ls = row.get("lat_std", np.nan)
        lo = row.get("lon_std", np.nan)
        ns = row.get("num_satellites", np.nan)
        sol = row.get("solution_status", 0.8)

        if sol == 0.0:
            return 2  # no fix → DEGRADED

        # Any sigma exceeds degraded threshold
        if (not pd.isna(ls) and ls > degraded_sigma_m) or \
           (not pd.isna(lo) and lo > degraded_sigma_m):
            return 2
        if not pd.isna(ns) and ns < degraded_max_sats:
            return 2

        # All available conditions satisfy CLEAN
        clean_ok = []
        if not pd.isna(ls):
            clean_ok.append(ls < clean_sigma_m)
        if not pd.isna(lo):
            clean_ok.append(lo < clean_sigma_m)
        if not pd.isna(ns):
            clean_ok.append(ns >= clean_min_sats)
        if clean_ok and all(clean_ok):
            return 0

        return 1

    feat_df["label"] = feat_df.apply(_sigma_label, axis=1)
    feat_df["label_name"] = feat_df["label"].map(
        {0: "CLEAN", 1: "WARNING", 2: "DEGRADED"})
    return feat_df


def process_urbannav_tunnel() -> pd.DataFrame:
    """
    Process UrbanNav HK Tunnel dataset (20210518, Cross-Harbour Tunnel, HK).

    Same 10-receiver setup as UrbanNav-HK-Medium-Urban-1.
    Format: RINEX 3 OBS (S1C direct dBHz) + NMEA (GSV for most receivers).
    Scenario: complete tunnel traversal — signal lost inside, recovers on exit.
    """
    base = Path("data/raw/public/urbannav/urbanNav_tunnel")
    if not base.exists():
        log.warning(f"UrbanNav Tunnel directory not found: {base}")
        return pd.DataFrame()

    # Discover receiver stems from filenames
    stems: set[str] = set()
    for f in base.iterdir():
        if f.suffix in (".nmea", ".obs"):
            stems.add(f.stem)

    all_dfs = []
    rinex_parser = Rinex3ObsParser(mode="direct_s1c")
    nmea_parser = NmeaParser()

    for stem in sorted(stems):
        obs_path = base / f"{stem}.obs"
        nmea_path = base / f"{stem}.nmea"

        if not obs_path.exists():
            log.info(f"  Skipping {stem} — no .obs file")
            continue

        log.info(f"  UrbanNav Tunnel: {stem}")

        # Extract receiver name from filename: 20210518.tunnel.cht.<receiver>
        parts = stem.split(".")
        receiver_name = "_".join(parts[3:]) if len(parts) > 3 else stem
        source_tag = f"urbannav_tunnel_{receiver_name}"
        scenario_tag = f"urbannav_tunnel_{receiver_name}"

        # Parse RINEX
        rinex_epochs = rinex_parser.parse_file(obs_path)

        # Parse NMEA if available
        nmea_df = pd.DataFrame()
        if nmea_path.exists():
            nmea_df = nmea_parser.parse_file(nmea_path)

        if not rinex_epochs and nmea_df.empty:
            continue

        if not nmea_df.empty and rinex_epochs:
            epoch_df = merge_nmea_rinex(
                nmea_df, rinex_epochs, leap_seconds=GPS_LEAP_SECONDS)
        elif not nmea_df.empty:
            epoch_df = merge_nmea_rinex(nmea_df, {})
        else:
            rows = []
            for gps_dt, data in sorted(rinex_epochs.items()):
                utc_dt = gps_dt - timedelta(seconds=GPS_LEAP_SECONDS)
                cnr_list = data.get("cnr_list", [])
                rows.append({
                    "timestamp": utc_dt,
                    "mean_cnr_epoch": float(np.mean(cnr_list)) if cnr_list else np.nan,
                    "cycle_slips_epoch": data.get("cycle_slips", 0),
                    "lat": np.nan, "lon": np.nan, "alt": np.nan,
                    "fix_quality": 1,
                    "num_satellites": len([c for c in cnr_list if c > 0]),
                })
            epoch_df = pd.DataFrame(rows)

        epoch_df["source"] = source_tag
        epoch_df["scenario"] = scenario_tag

        feat_df = compute_features(epoch_df)
        if not feat_df.empty:
            all_dfs.append(feat_df)
            log.info(
                f"    -> {len(feat_df)} rows, labels: {feat_df['label'].value_counts().to_dict()}")

    if not all_dfs:
        log.warning("No UrbanNav Tunnel data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/urbannav")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "urbannav_tunnel_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} UrbanNav Tunnel rows -> {out_path}")
    return combined


def process_tokyo_odaiba() -> pd.DataFrame:
    """
    Process UrbanNav Tokyo Odaiba RINEX observation files.

    Two receivers: rover_trimble (Trimble) and rover_ublox (u-blox).
    RINEX 3 OBS with S1C direct C/N0.  No NMEA — position will be NaN.

    Shinjuku is NOT processed (only base station OBS available; no rover file).
    """
    base = Path("data/raw/public/urbannav/Tokyo/Odaiba")
    if not base.exists():
        log.warning(f"Tokyo Odaiba directory not found: {base}")
        return pd.DataFrame()

    obs_files = {
        "trimble": base / "rover_trimble.obs",
        "ublox": base / "rover_ublox.obs",
    }

    rinex_parser = Rinex3ObsParser(mode="direct_s1c")
    all_dfs = []

    for receiver_name, obs_path in obs_files.items():
        if not obs_path.exists():
            log.warning(f"  Tokyo Odaiba: {obs_path.name} not found")
            continue

        log.info(f"  Tokyo Odaiba: {obs_path.name}")
        rinex_epochs = rinex_parser.parse_file(obs_path)
        if not rinex_epochs:
            continue

        rows = []
        for gps_dt, data in sorted(rinex_epochs.items()):
            utc_dt = gps_dt - timedelta(seconds=GPS_LEAP_SECONDS)
            cnr_list = data.get("cnr_list", [])
            rows.append({
                "timestamp": utc_dt,
                "mean_cnr_epoch": float(np.mean(cnr_list)) if cnr_list else np.nan,
                "cycle_slips_epoch": data.get("cycle_slips", 0),
                "lat": np.nan, "lon": np.nan, "alt": np.nan,
                "fix_quality": 1,
                "num_satellites": len([c for c in cnr_list if c > 0]),
                "source": f"tokyo_odaiba_{receiver_name}",
                "scenario": f"tokyo_odaiba_{receiver_name}",
            })
        epoch_df = pd.DataFrame(rows)
        feat_df = compute_features(epoch_df)
        if not feat_df.empty:
            all_dfs.append(feat_df)
            log.info(
                f"    -> {len(feat_df)} rows, labels: {feat_df['label'].value_counts().to_dict()}")

    if not all_dfs:
        log.warning("No Tokyo Odaiba data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/tokyo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tokyo_odaiba_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} Tokyo Odaiba rows -> {out_path}")
    return combined


def process_tokyo_shinjuku() -> pd.DataFrame:
    """
    Process UrbanNav Tokyo Shinjuku RINEX observation files.

    Two receivers: rover_trimble (Trimble) and rover_ublox (u-blox).
    Identical file layout to Odaiba — RINEX 3 OBS with S1C direct C/N0.
    No NMEA — position will be NaN.

    Shinjuku is a dense urban canyon environment; expect significantly more
    DEGRADED epochs than Odaiba (stronger multipath, more blockage).
    """
    base = Path("data/raw/public/urbannav/Tokyo/Shinjuku")
    if not base.exists():
        log.warning(f"Tokyo Shinjuku directory not found: {base}")
        return pd.DataFrame()

    obs_files = {
        "trimble": base / "rover_trimble.obs",
        "ublox":   base / "rover_ublox.obs",
    }

    rinex_parser = Rinex3ObsParser(mode="direct_s1c")
    all_dfs = []

    for receiver_name, obs_path in obs_files.items():
        if not obs_path.exists():
            log.warning(f"  Tokyo Shinjuku: {obs_path.name} not found")
            continue

        log.info(f"  Tokyo Shinjuku: {obs_path.name}")
        rinex_epochs = rinex_parser.parse_file(obs_path)
        if not rinex_epochs:
            continue

        rows = []
        for gps_dt, data in sorted(rinex_epochs.items()):
            utc_dt = gps_dt - timedelta(seconds=GPS_LEAP_SECONDS)
            cnr_list = data.get("cnr_list", [])
            rows.append({
                "timestamp":         utc_dt,
                "mean_cnr_epoch":    float(np.mean(cnr_list)) if cnr_list else np.nan,
                "cycle_slips_epoch": data.get("cycle_slips", 0),
                "lat": np.nan, "lon": np.nan, "alt": np.nan,
                "fix_quality":    1,
                "num_satellites": len([c for c in cnr_list if c > 0]),
                "source":   f"tokyo_shinjuku_{receiver_name}",
                "scenario": f"tokyo_shinjuku_{receiver_name}",
            })
        epoch_df = pd.DataFrame(rows)
        feat_df = compute_features(epoch_df)
        if not feat_df.empty:
            all_dfs.append(feat_df)
            log.info(
                f"    -> {len(feat_df)} rows, labels: {feat_df['label'].value_counts().to_dict()}")

    if not all_dfs:
        log.warning("No Tokyo Shinjuku data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_dir = Path("data/processed/tokyo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tokyo_shinjuku_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} Tokyo Shinjuku rows -> {out_path}")
    return combined


def process_nclt() -> pd.DataFrame:
    """
    Process NCLT (University of Michigan North Campus Long-Term) GPS data.

    Source files per session:
      gps.csv         — 1 Hz GPS fixes (lat/lon in RADIANS, fix_mode, hdop proxy)
      gps_rtk_err.csv — per-fix RTK position error in metres (ground truth comparison)

    C/N0 (signal strength, G2 features) is NOT available — will be NaN.
    DOP (G4): only approximate hdop-like values available; pdop/vdop NaN.
    num_satellites: logging artifact (always 0 in this version) — set to NaN.

    WHAT IS GROUND TRUTH?
    The `groundtruth_YYYY-MM-DD.csv` contains the precise vehicle trajectory
    computed by LiDAR SLAM — this is the reference "true" position of the robot.
    `gps_rtk_err.csv` = |GPS_position - LiDAR_SLAM_position|, i.e. the actual
    GPS positioning error in metres.  We use this error as the LABEL SIGNAL:
      CLEAN:    RTK_err < 2.0 m  AND fix_mode == 3 (3D fix)
      WARNING:  2.0 m <= RTK_err <= 5.0 m
      DEGRADED: RTK_err > 5.0 m  OR fix_mode != 3 (2D or no fix)

    Two sessions processed: 2012-08-04 and 2013-04-05.
    """
    base = Path("data/raw/public/nclt")
    out_dir = Path("data/processed/nclt")
    out_dir.mkdir(parents=True, exist_ok=True)

    sessions = ["2012-08-04", "2013-04-05"]
    all_dfs = []

    for session in sessions:
        session_dir = base / session
        gps_path = session_dir / "gps.csv"
        rtk_err_path = session_dir / "gps_rtk_err.csv"

        if not gps_path.exists():
            log.warning(f"  NCLT: gps.csv not found: {gps_path}")
            continue

        log.info(f"  NCLT: loading session {session}")

        # NCLT gps.csv: no header, lat/lon in RADIANS
        # Columns (from paper): utime[us], fix_mode, num_sats, lat_rad, lng_rad,
        #                        alt_m, track_deg, speed_ms
        gps = pd.read_csv(
            gps_path, header=None,
            names=["utime", "fix_mode", "num_sats",
                   "lat_rad", "lng_rad", "alt_m", "track_deg", "speed_ms"],
        )
        gps["lat"] = np.degrees(gps["lat_rad"])
        gps["lon"] = np.degrees(gps["lng_rad"])
        gps["alt"] = gps["alt_m"]
        gps["timestamp"] = pd.to_datetime(
            gps["utime"] / 1e6, unit="s", utc=True)
        # solution_status: 3=3D fix, 2=2D fix, 1=no fix
        gps["fix_quality"] = gps["fix_mode"].apply(
            lambda m: 1 if m == 3 else (1 if m == 2 else 0))
        gps["solution_status_raw"] = gps["fix_mode"].map(
            {3: 1.0, 2: 0.5, 1: 0.0}).fillna(0.0)
        # num_satellites not reliably logged — NaN
        gps["num_satellites"] = np.nan

        # Load RTK position error and merge
        if rtk_err_path.exists():
            err_df = pd.read_csv(
                rtk_err_path, header=None, names=["utime", "err_m"])
            err_df["err_m"] = pd.to_numeric(
                err_df["err_m"], errors="coerce")
            err_df = err_df.sort_values("utime").dropna(subset=["err_m"])
            gps = gps.sort_values("utime")
            gps = pd.merge_asof(
                gps, err_df, on="utime",
                direction="nearest", tolerance=500_000,  # 0.5 s tolerance
            )
            log.info(
                f"    RTK error: {gps['err_m'].notna().sum()} epochs matched, "
                f"mean={gps['err_m'].dropna().mean():.2f}m, "
                f"p90={gps['err_m'].dropna().quantile(0.9):.2f}m"
            )
        else:
            gps["err_m"] = np.nan

        # Derive lat_sigma / lon_sigma from RTK error (horiz error split evenly)
        gps["lat_sigma"] = gps["err_m"] / math.sqrt(2)
        gps["lon_sigma"] = gps["err_m"] / math.sqrt(2)

        # Resample to 1 Hz (raw is ~5 Hz)
        gps = (gps.set_index("timestamp")
               .resample("1s").first()
               .reset_index())
        gps["timestamp"] = pd.to_datetime(gps["timestamp"], utc=True)
        gps = gps.dropna(subset=["lat"])

        epoch_df = gps[[
            "timestamp", "lat", "lon", "alt",
            "lat_sigma", "lon_sigma",
            "num_satellites", "fix_quality", "err_m",
        ]].copy()
        epoch_df["source"] = "nclt"
        epoch_df["scenario"] = f"nclt_{session}"

        feat_df = compute_features(epoch_df)
        if feat_df.empty:
            continue

        # Override labels: use RTK error (position accuracy) since C/N0 is unavailable
        feat_df = _apply_position_sigma_labels(
            feat_df,
            clean_sigma_m=2.0,     # < 2m RTK error → CLEAN
            degraded_sigma_m=5.0,  # > 5m RTK error → DEGRADED
            clean_min_sats=1,      # num_sats not available; ignore
            degraded_max_sats=0,   # num_sats not available; ignore
        )

        all_dfs.append(feat_df)
        log.info(
            f"    Session {session}: {len(feat_df)} epochs | "
            + " | ".join(f"{n}={c}" for n,
                         c in feat_df["label_name"].value_counts().items())
        )

    if not all_dfs:
        log.warning("No NCLT data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_path = out_dir / "nclt_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} NCLT rows -> {out_path}")
    return combined


def process_oxford() -> pd.DataFrame:
    """
    Process Oxford RobotCar GPS CSV files.

    Source file per traversal: gps/gps.csv
    Columns: timestamp[us], num_satellites, latitude[deg], longitude[deg],
             altitude[m], latitude_sigma[m], longitude_sigma[m], altitude_sigma[m],
             northing, easting, down, utm_zone

    C/N0 (signal strength, G2 features) is NOT available — will be NaN.
    DOP (G4): NOT available — will be NaN.

    The NovAtel OEM6 receiver reports position sigma directly (in metres).
    We use these sigma values as the primary label signal:
      CLEAN:    lat_sigma < 3.0 m  AND lon_sigma < 3.0 m  AND num_sats >= 5
      WARNING:  3.0–10.0 m sigma range
      DEGRADED: sigma > 10.0 m  OR num_sats < 3

    Note: Oxford traversals are from 2014–2015 urban Oxford, UK.  The NovAtel
    was GPS-only (no GLONASS/Galileo integration), so max tracked sats ~12.
    The typical lat_sigma of 5-6 m reflects genuinely poor urban GNSS quality
    for a single-frequency GPS-only receiver in 2014.

    Two traversals processed: 2014-08-11 and 2015-03-10.
    """
    base = Path("data/raw/public/oxford")
    out_dir = Path("data/processed/oxford")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_dfs = []

    for traversal_dir in sorted(base.iterdir()):
        if not traversal_dir.is_dir():
            continue
        # Only directories containing gps/gps.csv
        gps_path = traversal_dir / "gps" / "gps.csv"
        if not gps_path.exists():
            continue

        # Skip the ldmrs-only directory (has no gps folder at top level)
        traversal_name = traversal_dir.name[:10]  # YYYY-MM-DD
        log.info(f"  Oxford: processing {traversal_dir.name}")

        df = pd.read_csv(gps_path)
        df = df.rename(columns={
            "latitude": "lat",
            "longitude": "lon",
            "altitude": "alt",
            "latitude_sigma": "lat_sigma",
            "longitude_sigma": "lon_sigma",
            "altitude_sigma": "alt_sigma",
        })

        # timestamp is in microseconds (Unix epoch)
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], unit="us", utc=True)
        df["fix_quality"] = 1   # gps.csv only contains valid fixes
        df["source"] = "oxford"
        df["scenario"] = f"oxford_{traversal_name}"

        # Resample to 1 Hz (Oxford GPS is logged at 5 Hz)
        df = (df.set_index("timestamp")
              .resample("1s").first()
              .reset_index())
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.dropna(subset=["lat"])

        keep_cols = [
            "timestamp", "lat", "lon", "alt",
            "lat_sigma", "lon_sigma",
            "num_satellites", "fix_quality",
            "source", "scenario",
        ]
        epoch_df = df[[c for c in keep_cols if c in df.columns]].copy()

        feat_df = compute_features(epoch_df)
        if feat_df.empty:
            continue

        # Override labels: use position sigma since C/N0 is unavailable
        feat_df = _apply_position_sigma_labels(
            feat_df,
            clean_sigma_m=3.0,
            degraded_sigma_m=10.0,
            clean_min_sats=5,
            degraded_max_sats=3,
        )

        all_dfs.append(feat_df)
        log.info(
            f"    Traversal {traversal_dir.name}: {len(feat_df)} epochs | "
            + " | ".join(f"{n}={c}" for n,
                         c in feat_df["label_name"].value_counts().items())
        )

    if not all_dfs:
        log.warning("No Oxford data processed.")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    out_path = out_dir / "oxford_features.csv"
    combined.to_csv(out_path, index=False)
    log.info(f"Saved {len(combined)} Oxford rows -> {out_path}")
    return combined


# ─── Dataset Combiner ─────────────────────────────────────────────────────────

def combine_all(out_path: Path = Path("data/processed/combined_dataset.csv")):
    """
    Combine all processed CSVs into a single labelled dataset for model training.

    Split strategy: SESSION-BASED STRATIFIED 70 / 15 / 15
    =======================================================
    Each unique 'scenario' value represents one session (independent recording).
    Sessions are assigned to train/validation/test at the session level — NOT the
    epoch level — to prevent temporal leakage between adjacent time steps.

    Within each source category (scenarios, supervisor, urbannav, etc.) the
    sessions are proportionally distributed so every split sees every source.

    This follows established best practice for time-series classification:
      - Random epoch-level splits MUST be avoided (adjacent epochs t and t+1
        would appear in both train and test, causing data leakage).
      - Session-level stratified splits give representative distributions.
      - "Leave-dataset-out" cross-validation is run separately as a
        generalization experiment (not the primary evaluation split).

    References:
      - Bergmeir & Benitez (2012) Neural Networks 29:58-67
      - Cerqueira et al. (2020) IEEE TKDE — temporal CV guidelines
      - Standard ML practice: any Goodfellow et al. Deep Learning, Ch. 11
    """
    source_files = [
        Path("data/processed/scenarios/all_scenarios_features.csv"),
        Path("data/processed/supervisor/vehicle/supervisor_vehicle_features.csv"),
        Path("data/processed/supervisor/drone/supervisor_drone_features.csv"),
        Path("data/processed/urbannav/urbannav_hk_features.csv"),
        Path("data/processed/urbannav/urbannav_tunnel_features.csv"),
        Path("data/processed/tokyo/tokyo_odaiba_features.csv"),
        Path("data/processed/tokyo/tokyo_shinjuku_features.csv"),
        Path("data/processed/nclt/nclt_features.csv"),
        Path("data/processed/oxford/oxford_features.csv"),
    ]

    dfs = []
    for src in source_files:
        if src.exists():
            df = pd.read_csv(src)
            dfs.append(df)
            log.info(f"  Loaded {len(df):>7,} rows from {src.name}")
        else:
            log.info(f"  Not yet processed (skipping): {src.name}")

    if not dfs:
        log.error("No processed data found for combining.")
        return

    combined = pd.concat(dfs, ignore_index=True)

    # ── Session-based stratified 70 / 15 / 15 split ──────────────────────────
    rng = np.random.default_rng(seed=42)

    # Each unique (source, scenario) pair is one session
    sessions = combined.groupby("scenario")["source"].first().reset_index()
    sessions = sessions.rename(columns={"source": "src"})

    # Group sessions by broad source category
    def _source_group(src_str: str) -> str:
        s = str(src_str)
        if "scenario" in s:
            return "scenarios"
        elif "supervisor" in s:
            return "supervisor"
        elif "drone" in s:
            return "drone"
        elif "urbannav_tunnel" in s:
            return "urbannav_tunnel"
        elif "urbannav" in s:
            return "urbannav_medium"
        elif "tokyo" in s:
            return "tokyo"
        elif "nclt" in s:
            return "nclt"
        elif "oxford" in s:
            return "oxford"
        return "other"

    sessions["group"] = sessions["src"].apply(_source_group)

    split_map: dict[str, str] = {}

    for group_name, grp in sessions.groupby("group"):
        scenario_list = grp["scenario"].tolist()
        n = len(scenario_list)
        shuffled = rng.permutation(scenario_list).tolist()

        n_test = max(1, round(n * 0.15))
        n_val = max(1, round(n * 0.15))
        n_train = n - n_test - n_val
        if n_train < 1:
            # Edge case: very few sessions — keep at least 1 train
            n_train = max(1, n - 1)
            n_val = max(0, (n - n_train) // 2)
            n_test = n - n_train - n_val

        for s in shuffled[:n_train]:
            split_map[s] = "train"
        for s in shuffled[n_train:n_train + n_val]:
            split_map[s] = "validation"
        for s in shuffled[n_train + n_val:]:
            split_map[s] = "test"

    combined["split"] = combined["scenario"].map(split_map).fillna("train")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)

    log.info(f"\n{'='*65}")
    log.info(f"Combined dataset: {len(combined):,} rows -> {out_path}")
    log.info("Label distribution:")
    for name, count in combined["label_name"].value_counts().items():
        pct = 100 * count / len(combined)
        log.info(f"  {name:<10} {count:>6,}  ({pct:.1f}%)")
    log.info("Split distribution:")
    for name, count in combined["split"].value_counts().items():
        pct = 100 * count / len(combined)
        log.info(f"  {name:<12} {count:>6,}  ({pct:.1f}%)")
    log.info("Sources:")
    for name, count in combined["source"].value_counts().items():
        log.info(f"  {name:<40} {count:>6,}")
    log.info(f"{'='*65}")

    # Save labelled copy
    labelled_dir = Path("data/labelled")
    labelled_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(labelled_dir / "sentinel_gnss_labelled.csv", index=False)
    log.info(f"Also saved to {labelled_dir / 'sentinel_gnss_labelled.csv'}")

    return combined


# ─── Summary Report ───────────────────────────────────────────────────────────

def print_dataset_summary(df: pd.DataFrame, title: str = "Dataset Summary"):
    """Print a summary of the processed dataset."""
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")
    print(f"  Total epochs   : {len(df):,}")
    if "label_name" in df.columns:
        print(f"  Label distribution:")
        for name, count in df["label_name"].value_counts().items():
            pct = 100 * count / len(df)
            bar = "#" * int(pct / 2)
            print(f"    {name:<10} {count:>6,}  ({pct:5.1f}%)  {bar}")
    if "scenario" in df.columns:
        print(f"  Scenarios:")
        for s, c in df["scenario"].value_counts().items():
            print(f"    {s:<35} {c:>6,}")
    if "source" in df.columns:
        print(f"  Sources: {df['source'].nunique()} unique")
    if "timestamp" in df.columns:
        df_t = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        print(f"  Time range: {df_t.min()} to {df_t.max()}")
    print(
        f"  Feature columns: {len([c for c in df.columns if c in ALL_FEATURES])}/35")
    print(f"{'='*65}\n")


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SENTINEL-GNSS: Process all datasets to feature CSVs"
    )
    parser.add_argument(
        "--source",
        choices=["scenarios", "supervisor", "drone", "urbannav",
                 "tunnel", "tokyo", "nclt", "oxford", "all"],
        default="all",
        help="Which data source to process (default: all)",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Only combine already-processed CSVs into final dataset",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="process_all",
        help="Process everything and combine",
    )
    args = parser.parse_args()

    results = []

    if args.combine:
        combine_all()
        return

    if args.process_all or args.source in ("scenarios", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: Our Collected Scenarios (A, B, C, D, E)")
        log.info("="*65)
        df = process_scenarios()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "Scenarios Summary")

    if args.process_all or args.source in ("supervisor", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: Supervisor Vehicle (exp1-exp4)")
        log.info("="*65)
        df = process_supervisor_vehicle()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "Supervisor Vehicle Summary")

    if args.process_all or args.source in ("drone", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: Supervisor Drone")
        log.info("="*65)
        df = process_supervisor_drone()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "Supervisor Drone Summary")

    if args.process_all or args.source in ("urbannav", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: UrbanNav HK-Medium-Urban-1")
        log.info("="*65)
        df = process_urbannav()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "UrbanNav Medium Summary")

    if args.process_all or args.source in ("tunnel", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: UrbanNav HK Tunnel (Cross-Harbour Tunnel)")
        log.info("="*65)
        df = process_urbannav_tunnel()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "UrbanNav Tunnel Summary")

    if args.process_all or args.source in ("tokyo", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: Tokyo Odaiba (Trimble + u-blox)")
        log.info("="*65)
        df = process_tokyo_odaiba()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "Tokyo Odaiba Summary")

        log.info("\n" + "="*65)
        log.info("PROCESSING: Tokyo Shinjuku (Trimble + u-blox)")
        log.info("="*65)
        df = process_tokyo_shinjuku()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "Tokyo Shinjuku Summary")

    if args.process_all or args.source in ("nclt", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: NCLT (Ann Arbor, 2012 + 2013)")
        log.info("="*65)
        df = process_nclt()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "NCLT Summary")

    if args.process_all or args.source in ("oxford", "all"):
        log.info("\n" + "="*65)
        log.info("PROCESSING: Oxford RobotCar (2014 + 2015)")
        log.info("="*65)
        df = process_oxford()
        if not df.empty:
            results.append(df)
            print_dataset_summary(df, "Oxford Summary")

    if args.process_all or len(results) > 1:
        log.info("\n" + "="*65)
        log.info("COMBINING all processed datasets (session-based 70/15/15 split)")
        log.info("="*65)
        combine_all()


if __name__ == "__main__":
    main()
