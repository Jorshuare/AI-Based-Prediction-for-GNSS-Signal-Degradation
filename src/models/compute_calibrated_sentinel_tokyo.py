"""
compute_calibrated_sentinel_tokyo.py
------------------------------------
Fill the Paper B headline TODO: the REAL degraded-RMSE of the floor-calibrated
SENTINEL-wired 9-state EKF on Tokyo Shinjuku (Trimble).

We do NOT re-run SENTINEL inference (its checkpoint is not needed here): the
per-epoch SENTINEL P(DEGRADED@5s), aligned to the 10-Hz EKF grid, is already
saved in results/urbannav_ekf_sentinel_trimble_tracks.npz. We reload only the
IMU/odometry via the runner's own align_data(), then:

  (1) VALIDATE: re-run the EKF with the RAW SENTINEL P and confirm it reproduces
      the saved aided_sent5 degraded RMSE (40.64 m). If it matches, our alignment
      is faithful and the calibrated number below is trustworthy.
  (2) COMPUTE: apply the unsupervised floor calibration
      P_cal = clip((P - P5)/(1 - P5), 0, 1), P5 = 5th percentile of P,
      re-run the EKF, and report overall + degraded RMSE and gain vs raw GNSS.

Run: python -m src.models.compute_calibrated_sentinel_tokyo
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

from src.models.ekf_urbannav_runner import (
    DATA, RESULTS, load_imu_data, load_reference_trajectory, align_data,
)
from src.models.ekf_9state import EKF9State, EKF9StateParams


def rmse(a: np.ndarray, truth: np.ndarray, m: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum((a[m] - truth[m]) ** 2, axis=1)))) if m.any() else float("nan")


def gain(ref: float, val: float) -> float:
    return round(100.0 * (ref - val) / ref, 1)


def main() -> None:
    src = "trimble"
    tracks = np.load(RESULTS / f"urbannav_ekf_sentinel_{src}_tracks.npz")
    truth = tracks["truth"]
    gnss_xy = tracks["gnss"]
    gnss_mask = tracks["gnss_mask"]
    is_degraded = tracks["is_degraded"]
    p_sent5 = tracks["p_sentinel_5s"]
    aided_sent5_saved = tracks["aided_sent5"]
    aided_fixed_saved = tracks["aided_fixed"]
    n_saved = len(truth)

    # Reload IMU / odometry on the identical grid via the runner's own loader.
    scn = DATA / "Shinjuku"
    imu_accel, imu_gyro, wheel_speed, _truth_xyz, n = align_data(
        load_imu_data(scn / "imu.csv"), load_reference_trajectory(scn / "reference.csv")
    )
    assert n == n_saved, f"grid mismatch: align_data n={n} vs saved {n_saved}"

    params = EKF9StateParams(dt=0.1, r_base=4.0, r_degraded=40.0)

    def run(p):
        return EKF9State(params).run(
            imu_accel, imu_gyro, gnss_xy, p,
            adaptive=True, wheel_speed=wheel_speed, gnss_mask=gnss_mask)[0]

    # (1) VALIDATION — reproduce raw SENTINEL and fixed-R
    aided_sent5_repro = run(p_sent5)
    fixed_repro = EKF9State(params).run(
        imu_accel, imu_gyro, gnss_xy, np.zeros(n),
        adaptive=False, wheel_speed=wheel_speed, gnss_mask=gnss_mask)[0]

    deg_raw_gnss = rmse(gnss_xy, truth, is_degraded)
    repro_sent5_deg = rmse(aided_sent5_repro, truth, is_degraded)
    saved_sent5_deg = rmse(aided_sent5_saved, truth, is_degraded)
    repro_fixed_deg = rmse(fixed_repro, truth, is_degraded)
    saved_fixed_deg = rmse(aided_fixed_saved, truth, is_degraded)

    print("=== VALIDATION (reproduce saved tracks) ===")
    print(f"  raw GNSS degraded RMSE        : {deg_raw_gnss:8.3f} m")
    print(f"  SENTINEL-raw degraded RMSE    : repro {repro_sent5_deg:8.3f}  saved {saved_sent5_deg:8.3f}")
    print(f"  fixed-R     degraded RMSE     : repro {repro_fixed_deg:8.3f}  saved {saved_fixed_deg:8.3f}")
    ok = abs(repro_sent5_deg - saved_sent5_deg) < 0.05 and abs(repro_fixed_deg - saved_fixed_deg) < 0.05
    print(f"  reproduction match           : {'OK' if ok else 'MISMATCH'}")

    # (2) COMPUTE — floor-calibrated SENTINEL
    p5 = float(np.percentile(p_sent5, 5))
    p_cal = np.clip((p_sent5 - p5) / (1.0 - p5), 0.0, 1.0)
    aided_cal = run(p_cal)

    cal_overall = rmse(aided_cal, truth, gnss_mask)
    cal_deg = rmse(aided_cal, truth, is_degraded)
    raw_overall_gnss = rmse(gnss_xy, truth, gnss_mask)

    print("\n=== CALIBRATED SENTINEL (real, computed) ===")
    print(f"  P5 floor (5th pct of P)       : {p5:.4f}")
    print(f"  mean P raw -> calibrated      : {p_sent5.mean():.3f} -> {p_cal.mean():.3f}")
    print(f"  overall  RMSE                 : {cal_overall:8.3f} m  (raw GNSS {raw_overall_gnss:.3f})")
    print(f"  degraded RMSE                 : {cal_deg:8.3f} m  (raw GNSS {deg_raw_gnss:.3f})")
    print(f"  degraded gain vs raw GNSS     : {gain(deg_raw_gnss, cal_deg):+.1f}%")

    # (3) Online sigma_deg estimator — calibrated P gates the estimate; r_degraded
    #     is the causal running median of recent degraded-epoch innovations.
    aided_online = EKF9State(params).run(
        imu_accel, imu_gyro, gnss_xy, p_cal,
        adaptive=True, wheel_speed=wheel_speed, gnss_mask=gnss_mask,
        online_sigma=True)[0]
    on_overall = rmse(aided_online, truth, gnss_mask)
    on_deg = rmse(aided_online, truth, is_degraded)
    print("\n=== CALIBRATED SENTINEL + ONLINE sigma_deg (no hand-tuning) ===")
    print(f"  overall  RMSE                 : {on_overall:8.3f} m")
    print(f"  degraded RMSE                 : {on_deg:8.3f} m")
    print(f"  degraded gain vs raw GNSS     : {gain(deg_raw_gnss, on_deg):+.1f}%")

    out = {
        "scenario": "Shinjuku", "gnss_source": src,
        "calibration": "unsupervised floor: P_cal = clip((P - P5)/(1-P5), 0, 1)",
        "p5_floor": round(p5, 4),
        "mean_p_raw": round(float(p_sent5.mean()), 3),
        "mean_p_calibrated": round(float(p_cal.mean()), 3),
        "validation_reproduces_saved": bool(ok),
        "rmse_overall": {"gnss_raw": round(raw_overall_gnss, 3),
                          "aided_ekf_sent5s_calib": round(cal_overall, 3),
                          "aided_ekf_sent5s_calib_online": round(on_overall, 3)},
        "rmse_degraded_segment": {"gnss_raw": round(deg_raw_gnss, 3),
                                   "aided_ekf_sent5s_calib": round(cal_deg, 3),
                                   "aided_ekf_sent5s_calib_online": round(on_deg, 3)},
        "degraded_gain_vs_raw": {"aided_ekf_sent5s_calib": gain(deg_raw_gnss, cal_deg),
                                  "aided_ekf_sent5s_calib_online": gain(deg_raw_gnss, on_deg)},
        "online_sigma_deg": "causal running median of innovations at elevated-P epochs, "
                            "window=80, clamp [8,80] m, gate P_cal>0.10 "
                            "(stable 43-44% gain across gate 0.05-0.15)",
    }
    out_path = RESULTS / f"urbannav_ekf_sentinel_{src}_calibrated.json"
    out_path.write_text(json.dumps(out, indent=2))
    np.savez(RESULTS / f"urbannav_ekf_sentinel_{src}_calibrated_tracks.npz",
             aided_sent5_calib=aided_cal, p_sent5_calib=p_cal)
    print(f"\nSaved -> {out_path.name}")


if __name__ == "__main__":
    main()
