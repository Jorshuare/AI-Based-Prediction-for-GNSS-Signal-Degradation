"""
paperb_make_figures.py
----------------------
Regenerate the Paper B Tokyo figures from the computed JSON artifacts so the
figures match the corrected/verified numbers:

  figures/fig_tokyo_comparison.pdf : degraded-RMSE bar chart per method
  figures/fig_error_cdf.pdf        : horizontal-error CDF (degraded epochs)

Run: python -m src.models.paperb_make_figures
"""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
FIGDIR = ROOT / "papers" / "paper_b" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

BUAA_BLUE = "#005BAC"
NAVY = "#003366"
ORANGE = "#FF9800"
GREEN = "#4CAF50"

plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
                     "pdf.fonttype": 42, "figure.dpi": 150})


def main() -> None:
    nav = json.loads((RESULTS / "paperb_navigation_metrics.json").read_text())
    m = nav["degraded_segment_metrics"]

    # ---- Figure 1: degraded-RMSE bar chart (+ online sigma_deg from calibrated json) ----
    cal = json.loads((RESULTS / "urbannav_ekf_sentinel_trimble_calibrated.json").read_text())
    online_rmse = cal["rmse_degraded_segment"]["aided_ekf_sent5s_calib_online"]

    order = ["GNSS raw", "Student-t PF", "EKF Huber (robust)", "EKF SENTINEL (calib.)",
             "EKF adaptive (nsat)", "EKF fixed-R"]
    labels = ["GNSS\nraw", "Student-t\nPF", "Huber\nEKF", "SENTINEL\ncalib.",
              "nsat\nproxy", "fixed-R\nEKF"]
    vals = [m[k]["rmse"] for k in order]
    # insert online sigma_deg next to calibrated
    labels.insert(4, "SENTINEL\ncalib.+online")
    vals.insert(4, online_rmse)
    colors = [NAVY] + [BUAA_BLUE] * (len(vals) - 2) + [GREEN]
    colors[5] = ORANGE  # highlight the online variant

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bars = ax.bar(range(len(vals)), vals, color=colors, edgecolor="black", linewidth=0.6)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Degraded-epoch horizontal RMSE (m)")
    ax.set_title("Tokyo Shinjuku: degraded-epoch RMSE by fusion method")
    ax.axhline(m["GNSS raw"]["rmse"], color=NAVY, ls="--", lw=0.8, alpha=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}",
                ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(0, max(vals) * 1.15)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_tokyo_comparison.pdf")
    fig.savefig(FIGDIR / "fig_tokyo_comparison.png", dpi=200)
    plt.close(fig)

    # ---- Figure 2: horizontal-error CDF on degraded epochs ----
    grid = np.array(nav["cdf_grid_m"])
    cdf = nav["cdf"]
    show = {"GNSS raw": NAVY, "EKF fixed-R": GREEN, "EKF SENTINEL (calib.)": BUAA_BLUE,
            "EKF Huber (robust)": ORANGE, "Student-t PF": "#9C27B0"}
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for name, c in show.items():
        ax.plot(grid, cdf[name], label=name, color=c, lw=2.0)
    ax.axvline(10, color="grey", ls=":", lw=0.8)
    ax.text(10.5, 0.05, "10 m", color="grey", fontsize=8)
    ax.set_xlabel("Horizontal error (m)")
    ax.set_ylabel("Cumulative probability (degraded epochs)")
    ax.set_title("Tokyo Shinjuku: degraded-epoch horizontal-error CDF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_error_cdf.pdf")
    fig.savefig(FIGDIR / "fig_error_cdf.png", dpi=200)
    plt.close(fig)

    print(f"Saved fig_tokyo_comparison.pdf and fig_error_cdf.pdf -> {FIGDIR}")


if __name__ == "__main__":
    main()
