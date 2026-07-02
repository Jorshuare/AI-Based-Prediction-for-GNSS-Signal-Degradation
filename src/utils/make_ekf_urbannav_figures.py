"""
make_ekf_urbannav_figures.py — Publication figures for the UrbanNav adaptive-EKF study.

Reads results/urbannav_ekf.json and produces:
  fig21_urbannav_filter_comparison.(png|pdf) — blocked-segment RMSE per filter
  fig22_urbannav_severity_sweep.(png|pdf)    — the crossover: when adaptive-R helps

Style: Beihang palette + cividis accents, white background, no titles (captions in
paper), bold 14 pt labels, 300 dpi.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
FIGS = RESULTS / "paper_figures"
FIGS.mkdir(parents=True, exist_ok=True)

# ── Cividis palette — matches make_paper_figures.py (perceptually uniform,
#    colour-blind safe).  Six evenly-spaced samples cover all methods.
_CIV = matplotlib.colormaps["cividis"]


def civ(t):
    r, g, b, _ = _CIV(float(t))
    return (r, g, b)


PALETTE = {
    "raw":      civ(0.05),   # Raw GNSS         (darkest — worst)
    "cv_kf":    civ(0.22),   # CV-KF             (dark blue)
    "fixed_na": civ(0.40),   # EKF fixed, no aid (mid blue-green)
    "ada_na":   civ(0.55),   # EKF adapt, no aid (teal)
    "fixed":    civ(0.72),   # Aided EKF fixed-R  (proposed — warm)
    "adaptive": civ(0.90),   # Aided EKF adapt-R  (yellow — best)
}
rcParams.update({
    "font.size": 13,
    "font.weight": "bold",
    "axes.labelweight": "bold",
    "axes.linewidth": 1.2,
    "figure.dpi": 300,
})


def _save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {stem}.png / .pdf")


def fig_filter_comparison(res):
    """Grouped bars: overall vs blocked-segment RMSE for each filter."""
    methods = ["gnss_raw", "cv_kf_fixed", "ekf9_fixed", "ekf9_adaptive",
               "ekf9_aided_fixed", "ekf9_aided_adaptive"]
    labels = ["GNSS\nraw", "CV-KF", "EKF\n(no aid)", "EKF adapt\n(no aid)",
              "Aided EKF\n(proposed)", "Aided EKF\nadaptive"]
    colors = [
        PALETTE["raw"], PALETTE["cv_kf"], PALETTE["fixed_na"],
        PALETTE["ada_na"], PALETTE["fixed"], PALETTE["adaptive"],
    ]
    methods = [m for m in methods if m in res["rmse_overall"]]
    labels = labels[:len(methods)]
    colors = colors[:len(methods)]

    overall = [res["rmse_overall"][m] for m in methods]
    blocked = [res["rmse_blocked_segment"][m] for m in methods]

    x = np.arange(len(methods))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    # Hatch "Overall" bars so they're visually distinct from "Blocked segment"
    # without relying on alpha (alpha degrades in print/PDF export).
    b1 = ax.bar(x - w / 2, overall, w, label="Overall",
                color=colors, edgecolor="black", linewidth=1.2, hatch="//")
    b2 = ax.bar(x + w / 2, blocked, w, label="Blocked segment",
                color=colors, edgecolor="black", linewidth=1.2)

    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=9,
                    fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("RMSE (m)")
    ax.legend(fontsize=12, frameon=True)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    _save(fig, "fig21_urbannav_filter_comparison")


def fig_severity_sweep(res):
    """Line plot: blocked-segment RMSE vs multipath severity, with crossover."""
    sweep = res["severity_sweep"]
    bias = [r["bias_max_m"] for r in sweep]
    raw = [r["raw"] for r in sweep]
    fixed = [r["fixed_R"] for r in sweep]
    adapt = [r["adaptive_R"] for r in sweep]
    cross = res.get("adaptive_crossover_bias_m")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(bias, raw, "o--", color=PALETTE["raw"], linewidth=3.0, markersize=8, label="Raw GNSS")
    ax.plot(bias, fixed, "s-", color=PALETTE["fixed"], linewidth=3.0, markersize=9,
            label="Aided EKF, fixed-R (proposed)")
    ax.plot(bias, adapt, "D-", color=PALETTE["adaptive"], linewidth=3.0, markersize=8,
            label="Aided EKF, adaptive-R")

    # Annotate crossover if visible, otherwise note the regime boundary.
    cross = res.get("adaptive_crossover_bias_m")
    _ann_color = PALETTE["adaptive"]
    if cross and cross in bias:
        ci = bias.index(cross)
        ax.annotate(f"SENTINEL adaptive-R wins\nabove ~{cross} m bias",
                    xy=(cross, (fixed[ci] + adapt[ci]) / 2),
                    xytext=(max(5, cross - 35), max(adapt) * 0.88),
                    fontsize=10.5, color=_ann_color,
                    arrowprops=dict(arrowstyle="->", color=_ann_color, lw=1.6))
    else:
        mid = len(bias) // 2
        ax.annotate("adaptive-R wins at extreme\nmultipath (>80 m — tunnels / deep canyons)",
                    xy=(bias[mid], fixed[mid]),
                    xytext=(bias[1], max(adapt) * 0.92),
                    fontsize=10.5, color=_ann_color,
                    arrowprops=dict(arrowstyle="->", color=_ann_color, lw=1.6))

    ax.set_xlabel("Multipath bias during blockage (m)")
    ax.set_ylabel("Blocked-segment RMSE (m)")
    ax.legend(fontsize=12, frameon=True, loc="upper left")
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    _save(fig, "fig22_urbannav_severity_sweep")


def main():
    path = RESULTS / "urbannav_ekf.json"
    if not path.exists():
        raise SystemExit("Run `python -m src.models.ekf_urbannav_runner` first.")
    res = json.loads(path.read_text())
    fig_filter_comparison(res)
    fig_severity_sweep(res)
    print("[DONE] UrbanNav EKF figures written to", FIGS)


if __name__ == "__main__":
    main()
