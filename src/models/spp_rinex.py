"""
spp_rinex.py — GPS-only Single Point Positioning (SPP) from RINEX, via georinex.

Turns the REAL raw pseudoranges in UrbanNav's `rover_ublox.obs` into a REAL GNSS
position track (ECEF per epoch), so the adaptive-EKF study can be run on genuinely
real GNSS errors (real urban multipath / NLOS), not synthetic noise.

Algorithm (standard, IS-GPS-200):
  • broadcast-ephemeris GPS satellite position at transmit time (Keplerian + corrections)
  • satellite clock correction (af0/af1/af2 + relativistic)
  • Sagnac (Earth-rotation) correction over signal travel time
  • Saastamoinen tropospheric delay (elevation-based); ionosphere left in (dominated by
    multipath in a canyon anyway) — can add Klobuchar later if needed
  • iterated weighted least squares for [x, y, z, c·dt_rx], elevation mask 10°

Output: results/urbannav_spp.npz with tow, ecef (N×3), nsat per epoch.

Usage:
  python -m src.models.spp_rinex            # processes Tokyo/Shinjuku rover_ublox.obs
"""
from __future__ import annotations

import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "raw" / "public" / "urbannav" / "Tokyo" / "Shinjuku"
RESULTS = ROOT / "results"

# Physical constants (WGS-84 / GPS)
MU = 3.986005e14            # earth gravitational constant (m^3/s^2)
OMEGA_E = 7.2921151467e-5   # earth rotation rate (rad/s)
C = 299792458.0            # speed of light (m/s)
F_REL = -4.442807633e-10    # relativistic correction factor
GPS_EPOCH = datetime(1980, 1, 6)


def gps_week_tow(dt: datetime) -> tuple[int, float]:
    """Datetime (GPS time) -> (week, seconds-of-week)."""
    delta = dt - GPS_EPOCH
    week = delta.days // 7
    tow = (delta.days - week * 7) * 86400 + delta.seconds + delta.microseconds * 1e-6
    return week, tow


def sat_pos_clock(eph: dict, t_tx: float) -> tuple[np.ndarray, float, float]:
    """GPS satellite ECEF position + clock bias at transmit time t_tx (seconds-of-week).

    eph: dict of broadcast ephemeris fields for one satellite.
    Returns (pos_ecef[3], dt_sv seconds, Ek) .
    """
    a = eph["sqrtA"] ** 2
    n0 = np.sqrt(MU / a ** 3)
    tk = t_tx - eph["Toe"]
    if tk > 302400:
        tk -= 604800
    elif tk < -302400:
        tk += 604800
    n = n0 + eph["DeltaN"]
    Mk = eph["M0"] + n * tk

    # Kepler
    Ek = Mk
    for _ in range(12):
        Ek = Mk + eph["Eccentricity"] * np.sin(Ek)

    e = eph["Eccentricity"]
    vk = np.arctan2(np.sqrt(1 - e ** 2) * np.sin(Ek), np.cos(Ek) - e)
    phik = vk + eph["omega"]

    s2, c2 = np.sin(2 * phik), np.cos(2 * phik)
    duk = eph["Cus"] * s2 + eph["Cuc"] * c2
    drk = eph["Crs"] * s2 + eph["Crc"] * c2
    dik = eph["Cis"] * s2 + eph["Cic"] * c2

    uk = phik + duk
    rk = a * (1 - e * np.cos(Ek)) + drk
    ik = eph["Io"] + dik + eph["IDOT"] * tk

    xkp = rk * np.cos(uk)
    ykp = rk * np.sin(uk)

    Omegak = eph["Omega0"] + (eph["OmegaDot"] - OMEGA_E) * tk - OMEGA_E * eph["Toe"]
    X = xkp * np.cos(Omegak) - ykp * np.cos(ik) * np.sin(Omegak)
    Y = xkp * np.sin(Omegak) + ykp * np.cos(ik) * np.cos(Omegak)
    Z = ykp * np.sin(ik)

    # satellite clock (relativistic + polynomial)
    dtr = F_REL * e * eph["sqrtA"] * np.sin(Ek)
    toc = eph.get("Toc", eph["Toe"])
    dt_poly = t_tx - toc
    if dt_poly > 302400:
        dt_poly -= 604800
    elif dt_poly < -302400:
        dt_poly += 604800
    dt_sv = (eph["SVclockBias"] + eph["SVclockDrift"] * dt_poly
             + eph["SVclockDriftRate"] * dt_poly ** 2 + dtr - eph.get("TGD", 0.0))
    return np.array([X, Y, Z]), dt_sv, Ek


def ecef_to_geodetic(p: np.ndarray) -> tuple[float, float, float]:
    """ECEF -> (lat, lon, h) WGS-84 (Bowring)."""
    a = 6378137.0
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = f * (2 - f)
    ep2 = (a ** 2 - b ** 2) / b ** 2
    x, y, z = p
    lon = np.arctan2(y, x)
    p_xy = np.hypot(x, y)
    th = np.arctan2(z * a, p_xy * b)
    lat = np.arctan2(z + ep2 * b * np.sin(th) ** 3, p_xy - e2 * a * np.cos(th) ** 3)
    N = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    h = p_xy / np.cos(lat) - N
    return lat, lon, h


def tropo_saastamoinen(elev: float, h: float) -> float:
    """Simple Saastamoinen tropospheric delay (m) for elevation `elev` (rad)."""
    if elev < np.deg2rad(3):
        elev = np.deg2rad(3)
    # standard atmosphere
    P = 1013.25 * (1 - 2.2557e-5 * max(h, 0)) ** 5.2568
    T = 15.0 - 6.5e-3 * max(h, 0) + 273.15
    e = 6.108 * np.exp((17.15 * T - 4684.0) / (T - 38.45)) * 0.5  # 50% humidity
    z = np.pi / 2 - elev
    trop = 0.002277 / np.cos(z) * (P + (1255.0 / T + 0.05) * e - np.tan(z) ** 2)
    return trop


def enu_rotation(lat: float, lon: float) -> np.ndarray:
    sl, cl = np.sin(lat), np.cos(lat)
    so, co = np.sin(lon), np.cos(lon)
    return np.array([
        [-so, co, 0],
        [-sl * co, -sl * so, cl],
        [cl * co, cl * so, sl],
    ])


def spp_epoch(prns, pranges, nav_by_sv, tow, rx0, elev_mask_deg=10.0):
    """Solve one epoch. Returns (rx_ecef[3], clock_b, n_used) or (None, None, 0)."""
    rx = np.array(rx0, dtype=float)
    b = 0.0
    lat0, lon0, h0 = ecef_to_geodetic(rx)
    R = enu_rotation(lat0, lon0)

    for _ in range(8):
        rows, res, used = [], [], 0
        for prn, P in zip(prns, pranges):
            if not np.isfinite(P) or P <= 0:
                continue
            eph = nav_by_sv.get(prn)
            if eph is None:
                continue
            travel = P / C
            t_tx = tow - travel
            sat, dt_sv, _ = sat_pos_clock(eph, t_tx)
            # Sagnac: rotate sat ECEF by earth rotation during travel
            ang = OMEGA_E * travel
            ca, sa = np.cos(ang), np.sin(ang)
            sat = np.array([ca * sat[0] + sa * sat[1], -sa * sat[0] + ca * sat[1], sat[2]])

            los = sat - rx
            rho = np.linalg.norm(los)
            enu = R @ los
            elev = np.arcsin(np.clip(enu[2] / rho, -1, 1))
            if np.rad2deg(elev) < elev_mask_deg:
                continue
            trop = tropo_saastamoinen(elev, h0)
            # corrected pseudorange = P + c*dt_sv - tropo
            Pc = P + C * dt_sv - trop
            pred = rho + b
            res.append(Pc - pred)
            rows.append([-los[0] / rho, -los[1] / rho, -los[2] / rho, 1.0])
            used += 1
        if used < 4:
            return None, None, used
        Hm = np.array(rows)
        r = np.array(res)
        try:
            dx = np.linalg.lstsq(Hm, r, rcond=None)[0]
        except np.linalg.LinAlgError:
            return None, None, used
        rx = rx + dx[:3]
        b = b + dx[3]
        lat0, lon0, h0 = ecef_to_geodetic(rx)
        R = enu_rotation(lat0, lon0)
        if np.linalg.norm(dx[:3]) < 1e-3:
            break
    return rx, b, used


def run_spp(scenario_dir=DATA, obs_name="rover_ublox.obs", nav_name="base.nav",
            max_epochs=None, out_stem="urbannav_spp"):
    """Process a RINEX pair -> SPP ECEF track. Returns dict of arrays."""
    import georinex as gr

    obs_file = scenario_dir / obs_name
    nav_file = scenario_dir / nav_name
    print(f"[SPP] loading nav {nav_file.name} (GPS) ...")
    nav = gr.load(str(nav_file), use="G")
    print(f"[SPP] loading obs {obs_file.name} (GPS C1C) ...")
    obs = gr.load(str(obs_file), use="G", meas=["C1C"])

    # APPROX POSITION from obs header (fallback init)
    approx = np.array([-3955049.85, 3355057.29, 3700097.51])

    times = obs.time.values
    svs = [s for s in obs.sv.values.tolist() if str(s).startswith("G")]
    if max_epochs:
        times = times[:max_epochs]

    # Pre-index nav per sv as list of (toe, eph-dict)
    nav_fields = ["sqrtA", "DeltaN", "M0", "Eccentricity", "omega", "Cus", "Cuc",
                  "Crs", "Crc", "Cis", "Cic", "Io", "IDOT", "Omega0", "OmegaDot",
                  "Toe", "SVclockBias", "SVclockDrift", "SVclockDriftRate"]
    nav_index = {}
    for sv in svs:
        if sv not in nav.sv.values:
            continue
        sub = nav.sel(sv=sv)
        toes = np.atleast_1d(sub["Toe"].values)
        ntime = np.atleast_1d(sub["time"].values)
        recs = []
        for i in range(len(toes)):
            if not np.isfinite(toes[i]):
                continue
            eph = {}
            ok = True
            for f in nav_fields:
                try:
                    val = sub[f].values
                    eph[f] = float(np.atleast_1d(val)[i])
                except Exception:
                    ok = False
                    break
            if not ok:
                continue
            _, toc_tow = gps_week_tow(_np_dt(ntime[i]))
            eph["Toc"] = toc_tow
            recs.append((eph["Toe"], eph))
        if recs:
            nav_index[sv] = recs

    rx_prev = approx.copy()
    out_tow, out_ecef, out_nsat = [], [], []
    c1c = obs["C1C"].values  # shape (time, sv) aligned to obs.sv
    sv_list = obs.sv.values.tolist()
    sv_cols = {sv: j for j, sv in enumerate(sv_list)}

    for ti, t in enumerate(times):
        _, tow = gps_week_tow(_np_dt(t))
        # choose ephemeris per sv nearest toe
        nav_by_sv = {}
        for sv, recs in nav_index.items():
            best = min(recs, key=lambda r: abs(r[0] - tow))
            if abs(best[0] - tow) < 7200:   # within 2h
                nav_by_sv[sv] = best[1]
        prns = [sv for sv in svs if sv in sv_cols]
        pranges = [c1c[ti, sv_cols[sv]] for sv in prns]
        rx, b, n = spp_epoch(prns, pranges, nav_by_sv, tow, rx_prev)
        if rx is not None and np.linalg.norm(rx - approx) < 1e5:
            rx_prev = rx
            out_tow.append(tow)
            out_ecef.append(rx)
            out_nsat.append(n)

    out_ecef = np.array(out_ecef)
    out_tow = np.array(out_tow)
    out_nsat = np.array(out_nsat)
    print(f"[SPP] solved {len(out_tow)}/{len(times)} epochs, mean sats={out_nsat.mean():.1f}")

    out_path = RESULTS / f"{out_stem}.npz"
    np.savez(out_path, tow=out_tow, ecef=out_ecef, nsat=out_nsat)
    print(f"[SPP] saved -> {out_path}")
    return {"tow": out_tow, "ecef": out_ecef, "nsat": out_nsat}


def _np_dt(np_datetime64) -> datetime:
    """numpy datetime64 -> python datetime (GPS time, no tz)."""
    return datetime(1970, 1, 1) + timedelta(seconds=float(np_datetime64.astype("datetime64[ns]").astype("int64")) / 1e9)


if __name__ == "__main__":
    import argparse, sys
    sys.path.insert(0, str(ROOT))
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="Shinjuku", help="Shinjuku or Odaiba")
    args = ap.parse_args()
    sc = args.scenario.capitalize()
    sc_dir = ROOT / "data" / "raw" / "public" / "urbannav" / "Tokyo" / sc
    stem = "urbannav_spp" if sc == "Shinjuku" else f"urbannav_spp_{sc.lower()}"
    run_spp(scenario_dir=sc_dir, out_stem=stem)
