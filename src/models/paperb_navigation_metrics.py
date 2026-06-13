"""
paperb_navigation_metrics.py
-----------------------------
Post-process the saved Tokyo Shinjuku (Trimble) EKF tracks into the
navigation-grade metrics a GNSS/INS reviewer expects, plus statistical rigor:

  * Degraded-segment RMSE, CEP50, CEP95, max error
  * Availability: % of degraded epochs under 5 m / 10 m horizontal error
  * Bootstrap 95% CI on degraded RMSE (1000 resamples, paired epochs)
  * Wilcoxon signed-rank paired test of per-epoch degraded errors
        (calibrated-SENTINEL vs fixed-R, and vs raw GNSS)
  * Horizontal-error CDF arrays saved for plotting

All numbers come from the saved per-epoch trajectories — no re-run.

Run: python -m src.models.paperb_navigation_metrics
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

RESULTS = Path(__file__).resolve().parents[2] / "results"
RNG = np.random.default_rng(20260613)


def herr(a: np.ndarray, truth: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum((a - truth) ** 2, axis=1))


def summarize(err: np.ndarray) -> dict:
    return {
        "rmse": round(float(np.sqrt(np.mean(err ** 2))), 3),
        "cep50": round(float(np.percentile(err, 50)), 3),
        "cep95": round(float(np.percentile(err, 95)), 3),
        "max": round(float(err.max()), 3),
        "avail_5m_pct": round(float(100.0 * np.mean(err < 5.0)), 1),
        "avail_10m_pct": round(float(100.0 * np.mean(err < 10.0)), 1),
        "n": int(err.size),
    }


def boot_ci(err: np.ndarray, n_boot: int = 1000) -> list:
    idx = np.arange(err.size)
    stats = []
    for _ in range(n_boot):
        s = RNG.choice(idx, size=idx.size, replace=True)
        stats.append(np.sqrt(np.mean(err[s] ** 2)))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


def wilcoxon(a: np.ndarray, b: np.ndarray) -> dict:
    """Paired Wilcoxon signed-rank, normal approximation (large n). Returns z, p, median diff."""
    d = a - b
    d = d[d != 0]
    n = d.size
    r = np.argsort(np.argsort(np.abs(d))) + 1.0  # ranks of |d|
    w_plus = r[d > 0].sum()
    mu = n * (n + 1) / 4.0
    sigma = np.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    z = (w_plus - mu) / sigma
    # two-sided p via normal approx
    from math import erfc, sqrt
    p = erfc(abs(z) / sqrt(2.0))
    return {"z": round(float(z), 2), "p_value": float(f"{p:.2e}"),
            "median_error_diff_m": round(float(np.median(a - b)), 3), "n_pairs": int(n)}


def main() -> None:
    rt = np.load(RESULTS / "urbannav_ekf_real_trimble_tracks.npz")
    truth = rt["truth"]; gnss = rt["gnss"]; deg = rt["is_degraded"]; fix = rt["gnss_mask"]
    cal = np.load(RESULTS / "urbannav_ekf_sentinel_trimble_calibrated_tracks.npz")["aided_sent5_calib"]

    methods = {
        "GNSS raw":              gnss,
        "CV-KF":                 rt["cv"],
        "EKF fixed-R":           rt["aided_fixed"],
        "EKF adaptive (nsat)":   rt["aided_adapt"],
        "EKF Huber (robust)":    rt["aided_huber"],
        "Student-t PF":          rt["aided_pf"],
        "EKF SENTINEL (calib.)": cal,
    }

    # degraded-segment per-epoch errors for every method
    errs = {name: herr(traj[deg], truth[deg]) for name, traj in methods.items()}

    table = {name: summarize(e) for name, e in errs.items()}
    for name in table:
        table[name]["rmse_ci95"] = boot_ci(errs[name])

    sig = {
        "calib_vs_fixed": wilcoxon(errs["EKF fixed-R"], errs["EKF SENTINEL (calib.)"]),
        "calib_vs_raw":   wilcoxon(errs["GNSS raw"], errs["EKF SENTINEL (calib.)"]),
        "fixed_vs_raw":   wilcoxon(errs["GNSS raw"], errs["EKF fixed-R"]),
    }

    # CDF arrays (degraded) for plotting
    cdf = {}
    grid = np.linspace(0, 120, 240)
    for name, e in errs.items():
        cdf[name] = np.round([float(np.mean(e <= t)) for t in grid], 4).tolist()

    print(f"{'Method':<24}{'RMSE':>8}{'CEP50':>8}{'CEP95':>8}{'max':>9}{'<5m%':>7}{'<10m%':>7}{'  RMSE 95% CI'}")
    print("-" * 86)
    for name, s in table.items():
        print(f"{name:<24}{s['rmse']:>8.2f}{s['cep50']:>8.2f}{s['cep95']:>8.2f}"
              f"{s['max']:>9.1f}{s['avail_5m_pct']:>7.1f}{s['avail_10m_pct']:>7.1f}"
              f"  [{s['rmse_ci95'][0]:.1f}, {s['rmse_ci95'][1]:.1f}]")
    print("\nPaired Wilcoxon signed-rank (degraded epochs):")
    for k, v in sig.items():
        print(f"  {k:<16} z={v['z']:>7}  p={v['p_value']:<10}  median err-diff={v['median_error_diff_m']:>7} m  (n={v['n_pairs']})")

    out = {"degraded_segment_metrics": table, "paired_significance": sig,
           "cdf_grid_m": grid.round(3).tolist(), "cdf": cdf,
           "n_degraded_epochs": int(deg.sum())}
    (RESULTS / "paperb_navigation_metrics.json").write_text(json.dumps(out, indent=2))
    print(f"\nSaved -> paperb_navigation_metrics.json")


if __name__ == "__main__":
    main()
