"""
ekf_hk_runner.py -- Phase 2c: SENTINEL + EKF validation on UrbanNav Hong Kong.

Four real urban environments from the UrbanNav HK benchmark:
  Medium Urban  -- TST (Tsim Sha Tsui), ~785 s, moderate canyon
  Deep Urban    -- Whampoa, ~1536 s, heavy canyon
  Harsh Urban   -- Mong Kok, ~2314 s (partial GT), ultra-dense canyon
  Tunnel        -- CHT cross-harbour tunnel, ~398 s, complete GNSS blockage

No IMU data is available for HK → uses a 4-state constant-velocity EKF:
  State   : [x, y, vx, vy]
  Predict : x += vx*dt, y += vy*dt at 1 Hz (GNSS rate)
  Update  : GNSS position measurement with adaptive-R (SENTINEL-driven trust)

Comparison:
  gnss_raw     -- raw u-blox F9P positions (no filtering)
  cv_kf_fixed  -- CV-EKF with constant R
  cv_kf_adapt  -- CV-EKF with SENTINEL-driven R inflation

Ground truth: SPAN-CPT post-processed in DMS lat/lon format (Q flag preserved).
GNSS: u-blox F9P dual-frequency NMEA. SENTINEL: 5-second lookahead horizon.

Output: results/urbannav_ekf_hk_<env>.json + matching _tracks.npz files
        results/urbannav_ekf_hk_summary.json  -- all-environment table
"""
from __future__ import annotations
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

HK_DATA = ROOT / "data" / "raw" / "public" / "urbannav"
RESULTS  = ROOT / "results"

# ─── environment config ───────────────────────────────────────────────────────
ENVS = {
    "medium": {
        "label":    "Medium Urban (TST)",
        "nmea":     HK_DATA / "urbanNav_Medium" / "UrbanNav-HK-Medium-Urban-1.ublox.f9p.nmea",
        "gt":       HK_DATA / "UrbanNav_TST_GT_raw.txt",
        "r_base":   4.0,   # clean GNSS std (m) — F9P dual-freq is accurate
        "r_deg":   30.0,   # degraded GNSS std (m)
    },
    "deep": {
        "label":    "Deep Urban (Whampoa)",
        "nmea":     HK_DATA / "urbanNav_Deep" / "UrbanNav-HK-Deep-Urban-1.ublox.f9p.nmea",
        "gt":       HK_DATA / "UrbanNav_whampoa_raw.txt",
        "r_base":   5.0,
        "r_deg":   40.0,
    },
    "harsh": {
        "label":    "Harsh Urban (Mong Kok)",
        "nmea":     HK_DATA / "urbanNav_Harsh" / "UrbanNav-HK-Harsh-Urban-1.ublox.f9p.nmea",
        "gt":       HK_DATA / "UrbanNav_mongkok_GT_part_raw.txt",
        "r_base":   6.0,
        "r_deg":   50.0,
    },
    "tunnel": {
        "label":    "Tunnel (CHT)",
        "nmea":     HK_DATA / "urbanNav_tunnel" / "20210518.tunnel.cht.ublox.f9p.nmea",
        "gt":       HK_DATA / "UrbanNav_tunnel_GT_raw.txt",
        "r_base":   4.0,
        "r_deg":   60.0,
    },
}


# ─── geometry helpers ─────────────────────────────────────────────────────────

def dms_to_deg(d: str, m: str, s: str) -> float:
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def latlon_to_enu(lat: np.ndarray, lon: np.ndarray, lat0: float, lon0: float):
    """Equirectangular local ENU (metres) centred on (lat0, lon0)."""
    R = 6_378_137.0
    lat_r  = np.radians(lat);  lon_r  = np.radians(lon)
    lat0_r = np.radians(lat0); lon0_r = np.radians(lon0)
    x = R * (lon_r - lon0_r) * np.cos(lat0_r)   # East
    y = R * (lat_r - lat0_r)                     # North
    return x, y


# ─── ground-truth parser ──────────────────────────────────────────────────────

def parse_hk_gt(txt_path: Path) -> pd.DataFrame:
    """
    Parse UrbanNav HK SPAN-CPT ground truth.

    Format (after two header lines):
      col 0  UTCTime   Unix seconds (1 Hz)
      col 1  Week      GPS week
      col 2  GPSTime   GPS TOW (s)
      col 3-5          Latitude  D M S
      col 6-8          Longitude D M S
      col 9  H-Ell     ellipsoidal height (m)
      …
      col -1 Q         quality flag (1=best, 2=degraded)
    """
    rows = []
    skip = 2  # two header lines
    with open(txt_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i < skip or not line.strip():
                continue
            p = line.split()
            if len(p) < 10:
                continue
            try:
                rows.append({
                    "unix":  float(p[0]),
                    "lat":   dms_to_deg(p[3], p[4], p[5]),
                    "lon":   dms_to_deg(p[6], p[7], p[8]),
                    "q":     int(p[-1]),
                })
            except (ValueError, IndexError):
                pass
    return pd.DataFrame(rows)


# ─── simple GGA NMEA parser ───────────────────────────────────────────────────

def _parse_gga_latlon(ddmm: str, hemi: str) -> float:
    """Convert NMEA DDMM.MMMM + hemisphere to signed decimal degrees."""
    if not ddmm:
        return np.nan
    dot = ddmm.index(".")
    deg = int(ddmm[: dot - 2])
    mins = float(ddmm[dot - 2 :])
    val = deg + mins / 60.0
    return -val if hemi in ("S", "W") else val


def parse_nmea_positions(nmea_path: Path, date_str: str | None = None) -> pd.DataFrame:
    """
    Lightweight GGA parser — returns one row per GGA sentence with:
      unix_time, lat, lon, n_sats, hdop, fix_quality.

    date_str : 'YYYY-MM-DD' UTC date for RMC-less files.
               If None, the RMC sentence in the file sets the date.
    """
    from datetime import timezone as tz

    cur_date = None
    if date_str:
        cur_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz.utc)

    rows = []
    with open(nmea_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            # RMC carries the date (DDMMYY in field 9)
            if line.startswith("$") and "RMC," in line:
                p = line.split(",")
                if len(p) > 9 and p[9] and len(p[9]) == 6:
                    try:
                        dd, mm, yy = int(p[9][:2]), int(p[9][2:4]), int(p[9][4:6])
                        yr = 2000 + yy if yy < 80 else 1900 + yy
                        cur_date = datetime(yr, mm, dd, tzinfo=tz.utc)
                    except ValueError:
                        pass
            # GGA carries time + position
            if line.startswith("$") and "GGA," in line:
                p = line.split(",")
                if len(p) < 10 or not p[1]:
                    continue
                try:
                    t = p[1]
                    hh, mi, ss_f = int(t[0:2]), int(t[2:4]), float(t[4:])
                    lat = _parse_gga_latlon(p[2], p[3])
                    lon = _parse_gga_latlon(p[4], p[5])
                    fq  = int(p[6]) if p[6] else 0
                    ns  = int(p[7]) if p[7] else 0
                    hdop = float(p[8]) if p[8] else np.nan
                    if cur_date is None:
                        continue
                    dt = cur_date.replace(hour=hh, minute=mi,
                                          second=int(ss_f),
                                          microsecond=int(round((ss_f % 1) * 1e6)))
                    rows.append({
                        "unix": dt.timestamp(),
                        "lat":  lat,
                        "lon":  lon,
                        "fix_quality": fq,
                        "n_sats": ns,
                        "hdop": hdop,
                    })
                except (ValueError, IndexError):
                    pass
    df = pd.DataFrame(rows).drop_duplicates("unix").sort_values("unix").reset_index(drop=True)
    return df


# ─── SENTINEL inference on NMEA file ─────────────────────────────────────────

def run_sentinel_on_nmea(nmea_path: Path) -> pd.DataFrame | None:
    """
    Run SENTINEL ML inference on an NMEA file.
    Returns a DataFrame indexed by feature epoch with p_degraded_5s,
    or None if inference fails (falls back to nsat proxy in caller).
    """
    try:
        from src.models.inference import SentinelInference
        si = SentinelInference(receiver_tier=0)  # F9P = professional tier
        feat, _pos = si.features_from_nmea(nmea_path)
        Xw, end_idx = si.windows(feat)
        if Xw is None:
            return None
        probs = si.predict(Xw)
        # Expand window predictions to per-epoch series (interpolate)
        p_windows = probs["5s"][:, 2]   # P(DEGRADED at +5 s)
        n_feat = len(feat)
        p_epoch = np.zeros(n_feat)
        if len(end_idx) >= 2:
            # Linearly interpolate between window endpoints
            xi = np.arange(n_feat)
            xp = np.array(end_idx, dtype=float)
            fp_ = p_windows
            p_epoch = np.interp(xi, xp, fp_, left=fp_[0], right=fp_[-1])
        elif len(end_idx) == 1:
            p_epoch[end_idx[0]:] = p_windows[0]
        # Attach p_degraded_5s to feat timestamps
        result = feat[["timestamp"] if "timestamp" in feat.columns else []].copy()
        result = result.reset_index(drop=True)
        result["p_degraded_5s"] = p_epoch
        result["n_windows"] = len(end_idx)
        return result
    except Exception as e:
        print(f"  [warn] SENTINEL inference failed: {e}; using nsat proxy")
        return None


# ─── 4-state CV EKF (1 Hz) ───────────────────────────────────────────────────

def run_cv_ekf(gnss_xy: np.ndarray, r_var, dt: float = 1.0,
               gnss_mask: np.ndarray | None = None, q: float = 0.3) -> np.ndarray:
    """
    Constant-velocity EKF for GNSS-only (no IMU).

    State: [x, y, vx, vy]. Predicts at dt; updates on GNSS fixes.

    r_var : scalar (fixed-R) or (N,) array (adaptive-R per epoch)
    """
    n = len(gnss_xy)
    F = np.array([[1, 0, dt, 0], [0, 1, 0, dt],
                  [0, 0,  1, 0], [0, 0,  0,  1]], float)
    H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], float)
    Q = q * np.array([
        [dt**4/4, 0, dt**3/2, 0],
        [0, dt**4/4, 0, dt**3/2],
        [dt**3/2, 0, dt**2, 0],
        [0, dt**3/2, 0, dt**2],
    ])
    r_arr = np.full(n, float(r_var)) if np.ndim(r_var) == 0 else np.asarray(r_var, float)

    # Seed velocity from first 5-second displacement
    valid = np.where(gnss_mask if gnss_mask is not None else np.ones(n, bool))[0]
    if len(valid) >= 2:
        v0 = (gnss_xy[valid[min(5, len(valid)-1)]] - gnss_xy[valid[0]]) / \
             (max(1, (valid[min(5, len(valid)-1)] - valid[0])) * dt)
    else:
        v0 = np.zeros(2)

    x = np.r_[gnss_xy[valid[0]], v0]
    P = np.diag([10.0, 10.0, 5.0, 5.0])
    out = np.zeros((n, 2))
    out[valid[0]] = x[:2]

    for k in range(valid[0] + 1, n):
        x = F @ x
        P = F @ P @ F.T + Q
        has_fix = gnss_mask is None or gnss_mask[k]
        if has_fix:
            R = np.eye(2) * r_arr[k]
            S = H @ P @ H.T + R
            K = P @ H.T @ np.linalg.inv(S)
            inn = gnss_xy[k] - H @ x
            x = x + K @ inn
            P = (np.eye(4) - K @ H) @ P @ (np.eye(4) - K @ H).T + K @ R @ K.T
        out[k] = x[:2]

    return out


# ─── per-environment runner ───────────────────────────────────────────────────

def run_hk_env(env_name: str) -> dict:
    cfg = ENVS[env_name]
    print(f"\n{'='*72}")
    print(f"HK Phase 2c: {cfg['label']} [{env_name}]")
    print(f"{'='*72}")

    nmea_path = Path(cfg["nmea"])
    gt_path   = Path(cfg["gt"])

    # ── 1. Parse NMEA positions ───────────────────────────────────────────────
    print("[1/5] Parsing NMEA positions...")
    if not nmea_path.exists():
        print(f"  ERROR: {nmea_path} not found")
        return {"env": env_name, "status": "missing_nmea"}

    nmea_df = parse_nmea_positions(nmea_path)
    # Keep only valid fixes (fix_quality >= 1)
    valid_fix = nmea_df["fix_quality"] >= 1
    print(f"  [OK] {valid_fix.sum()} valid GNSS fixes / {len(nmea_df)} total NMEA epochs")

    # Establish ENU origin at first valid fix
    first_valid = nmea_df.loc[valid_fix].iloc[0]
    lat0, lon0 = float(first_valid["lat"]), float(first_valid["lon"])

    nmea_df["x"], nmea_df["y"] = latlon_to_enu(
        nmea_df["lat"].values, nmea_df["lon"].values, lat0, lon0)

    # ── 2. Parse ground truth ─────────────────────────────────────────────────
    print("[2/5] Parsing ground truth...")
    if not gt_path.exists():
        print(f"  ERROR: {gt_path} not found")
        return {"env": env_name, "status": "missing_gt"}

    gt_df = parse_hk_gt(gt_path)
    gt_df["x"], gt_df["y"] = latlon_to_enu(
        gt_df["lat"].values, gt_df["lon"].values, lat0, lon0)
    print(f"  [OK] {len(gt_df)} GT epochs  "
          f"(q=1: {(gt_df['q']==1).sum()}, q=2: {(gt_df['q']==2).sum()})")

    # ── 3. Time-align NMEA <-> GT (1Hz grids) ─────────────────────────────────
    print("[3/5] Aligning NMEA <-> ground truth by Unix timestamp...")
    gt_unix  = gt_df["unix"].values
    gnss_unix = nmea_df["unix"].values

    # For each GT epoch, find nearest NMEA epoch within 0.6 s
    n = len(gt_df)
    gnss_xy   = np.zeros((n, 2))
    gnss_mask = np.zeros(n, bool)
    nsat_arr  = np.zeros(n, float)

    hdop_arr  = np.full(n, np.nan)
    last_xy   = np.array([0.0, 0.0])
    last_nsat = 0.0
    last_hdop = np.nan
    for i, tu in enumerate(gt_unix):
        diff = np.abs(gnss_unix - tu)
        j = int(np.argmin(diff))
        if diff[j] <= 0.6 and valid_fix.iloc[j]:
            xy = np.array([nmea_df["x"].iloc[j], nmea_df["y"].iloc[j]])
            if not np.isnan(xy).any():
                last_xy   = xy
                last_nsat = nmea_df["n_sats"].iloc[j]
                last_hdop = nmea_df["hdop"].iloc[j]
                gnss_xy[i]  = xy
                gnss_mask[i] = True
                nsat_arr[i]  = last_nsat
                hdop_arr[i]  = last_hdop
        # No-fix / unmatched epochs: hold-last position (gnss_mask stays False)
        if not gnss_mask[i]:
            gnss_xy[i] = last_xy

    truth_xy = gt_df[["x", "y"]].values
    n_aligned = gnss_mask.sum()
    print(f"  [OK] {n_aligned} aligned epochs with GNSS fix ({100*n_aligned/n:.0f}% of GT)")

    # ── 4. SENTINEL inference + P(DEGRADED) ──────────────────────────────────
    print("[4/5] Running SENTINEL inference...")
    sentinel_df = run_sentinel_on_nmea(nmea_path)

    if sentinel_df is not None and "timestamp" in sentinel_df.columns:
        # Convert feature timestamps to Unix and align to GT grid
        sent_ts = pd.to_datetime(sentinel_df["timestamp"], utc=True)
        sent_unix = sent_ts.astype(np.int64) / 1e9
        p_sent_src = sentinel_df["p_degraded_5s"].values
        # Interpolate to GT time grid
        p_sentinel = np.interp(gt_unix, sent_unix.values,
                               p_sent_src, left=p_sent_src[0], right=p_sent_src[-1])
        p_sentinel = np.clip(p_sentinel, 0.0, 1.0)
        n_windows = int(sentinel_df["n_windows"].iloc[0])
        p_src_label = f"SENTINEL-5s ({n_windows} windows, mean P={p_sentinel.mean():.3f})"
    else:
        # Fallback: nsat proxy (reactive, no lookahead)
        nsf = pd.Series(nsat_arr).replace(0, np.nan).interpolate().bfill().ffill().values
        nsf = pd.Series(nsf).rolling(5, center=True, min_periods=1).mean().values
        p_sentinel = np.clip((5.0 - nsf) / 3.0, 0.0, 1.0)
        p_src_label = f"nsat proxy (fallback, mean P={p_sentinel.mean():.3f})"

    print(f"  [OK] P(DEGRADED) source: {p_src_label}")

    # nsat-proxy P(DEGRADED) for baseline comparison
    nsf2 = pd.Series(nsat_arr).replace(0, np.nan).interpolate().bfill().ffill().values
    nsf2 = pd.Series(nsf2).rolling(5, center=True, min_periods=1).mean().values
    p_nsat = np.clip((5.0 - nsf2) / 3.0, 0.0, 1.0)

    # ── 5. Run EKF variants ───────────────────────────────────────────────────
    r_base, r_deg = cfg["r_base"], cfg["r_deg"]
    r_fixed  = np.full(n, r_base ** 2)
    r_adapt  = (r_base + (r_deg - r_base) * p_sentinel) ** 2
    r_nsat   = (r_base + (r_deg - r_base) * p_nsat) ** 2

    cv_fixed  = run_cv_ekf(gnss_xy, r_fixed,  gnss_mask=gnss_mask)
    cv_adapt  = run_cv_ekf(gnss_xy, r_adapt,  gnss_mask=gnss_mask)
    cv_nsat   = run_cv_ekf(gnss_xy, r_nsat,   gnss_mask=gnss_mask)

    # ── 6. RMSE metrics ───────────────────────────────────────────────────────
    eval_mask = gnss_mask  # evaluate where we have a real fix
    # "Degraded" = epochs with NO GNSS fix (complete signal loss).
    # F9P dual-frequency always sees 10+ sats when locked, so nsat<=5 never fires.
    # Outage epochs are the true test of EKF dead-reckoning (CV-model).
    is_degraded = ~gnss_mask
    # Also flag high-HDOP epochs (F9P uses 99.99 sentinel for invalid DOP)
    is_degraded = is_degraded | (gnss_mask & (hdop_arr > 5.0))

    def rmse(traj, mask):
        if not mask.any():
            return np.nan
        return float(np.sqrt(np.mean(np.sum((traj[mask] - truth_xy[mask])**2, axis=1))))

    def gain(ref, val):
        if ref == 0 or np.isnan(ref) or np.isnan(val):
            return np.nan
        return round(100.0 * (ref - val) / ref, 1)

    methods = {
        "gnss_raw":        gnss_xy,
        "cv_kf_fixed":     cv_fixed,
        "cv_kf_nsat":      cv_nsat,
        "cv_kf_sentinel":  cv_adapt,
    }

    overall  = {k: round(rmse(v, eval_mask), 2) for k, v in methods.items()}
    deg_rmse = {k: round(rmse(v, is_degraded), 2) if is_degraded.any() else np.nan
                for k, v in methods.items()}
    deg_gain = {k: gain(deg_rmse["gnss_raw"], deg_rmse[k]) for k in methods}

    print(f"\n  {'Method':<22}{'Overall RMSE':>14}{'Degraded RMSE':>15}{'Deg. gain':>12}")
    print(f"  {'-'*63}")
    for k in methods:
        g = "-" if k == "gnss_raw" else (f"{deg_gain[k]:+.1f}%" if not np.isnan(deg_gain[k]) else "N/A")
        o = overall[k] if not np.isnan(overall[k]) else float("nan")
        d = deg_rmse[k] if not np.isnan(deg_rmse[k]) else float("nan")
        print(f"  {k:<22}{o:>11.2f} m{d:>12.2f} m{g:>12}")
    print()

    # ── 7. Save results ───────────────────────────────────────────────────────
    result = {
        "env": env_name,
        "label": cfg["label"],
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "n_gt_epochs": int(n),
        "n_gnss_fixes": int(n_aligned),
        "n_degraded_epochs": int(is_degraded.sum()),
        "gnss_coverage_pct": round(100 * n_aligned / n, 1),
        "mean_nsat": round(float(np.nanmean(nsat_arr[gnss_mask])), 2) if gnss_mask.any() else 0.0,
        "p_degraded_source": p_src_label,
        "mean_p_degraded": round(float(p_sentinel[gnss_mask].mean()), 3) if gnss_mask.any() else 0.0,
        "r_base_m": r_base,
        "r_degraded_m": r_deg,
        "rmse_overall": overall,
        "rmse_degraded_segment": {k: (v if not np.isnan(v) else None)
                                  for k, v in deg_rmse.items()},
        "degraded_gain_vs_raw": {k: (v if not np.isnan(v) else None)
                                 for k, v in deg_gain.items()},
    }

    out_json = RESULTS / f"urbannav_ekf_hk_{env_name}.json"
    with open(out_json, "w") as fh:
        json.dump(result, fh, indent=2)

    out_npz = RESULTS / f"urbannav_ekf_hk_{env_name}_tracks.npz"
    np.savez(out_npz,
             truth=truth_xy, gnss=gnss_xy, gnss_mask=gnss_mask,
             cv_fixed=cv_fixed, cv_nsat=cv_nsat, cv_adapt=cv_adapt,
             is_degraded=is_degraded, nsat=nsat_arr, hdop=hdop_arr,
             p_sentinel=p_sentinel, p_nsat=p_nsat)

    print(f"  Saved: {out_json.name}  {out_npz.name}")
    return result


# ─── run all environments ─────────────────────────────────────────────────────

def run_all_hk() -> list[dict]:
    print("\n" + "="*72)
    print("Phase 2c: SENTINEL-GNSS EKF on UrbanNav Hong Kong (4 environments)")
    print("="*72)

    all_results = []
    for env_name in ENVS:
        try:
            r = run_hk_env(env_name)
            all_results.append(r)
        except Exception as exc:
            print(f"  [ERROR] {env_name}: {exc}")
            all_results.append({"env": env_name, "status": "error", "error": str(exc)})

    # Print summary table
    print("\n" + "="*72)
    print("SUMMARY -- RMSE vs SPAN-CPT ground truth (all-epoch, metres)")
    print(f"  {'Environment':<24}{'Raw GNSS':>10}{'Fixed-R':>10}{'nsat proxy':>12}{'SENTINEL':>12}{'Gain (SENT)':>14}")
    print(f"  {'-'*82}")
    for r in all_results:
        if r.get("status") != "ok":
            print(f"  {r.get('label', r['env']):<24}  ERROR")
            continue
        ov = r["rmse_overall"]
        raw = ov.get("gnss_raw", float("nan"))
        fix = ov.get("cv_kf_fixed", float("nan"))
        nsat = ov.get("cv_kf_nsat", float("nan"))
        sent = ov.get("cv_kf_sentinel", float("nan"))
        g = r["degraded_gain_vs_raw"].get("cv_kf_sentinel")
        gs = f"{g:+.1f}%" if g is not None else "N/A"
        print(f"  {r['label']:<24}{raw:>10.2f}{fix:>10.2f}{nsat:>12.2f}{sent:>12.2f}{gs:>14}")
    print()

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "environments": all_results,
    }
    out = RESULTS / "urbannav_ekf_hk_summary.json"
    with open(out, "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"Summary saved: {out}")
    return all_results


if __name__ == "__main__":
    if "--env" in sys.argv:
        idx = sys.argv.index("--env") + 1
        run_hk_env(sys.argv[idx])
    else:
        run_all_hk()
