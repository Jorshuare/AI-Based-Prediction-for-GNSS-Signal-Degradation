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

# Beihang blue family + cividis-friendly accents (single source of truth).
PALETTE = {
    "raw": "#7A8CA3",        # grey-blue (raw GNSS)
    "fixed": "#344E7F",      # Beihang secondary blue
    "adaptive": "#BCB245",   # Beihang mustard (the proposed method)
    "ekf": "#003360",        # Beihang primary blue
    "win": "#2E7D32",        # green (adaptive wins)
    "lose": "#C0392B",       # red (adaptive loses)
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
    methods = ["gnss_raw", "cv_kf_fixed", "cv_kf_adaptive", "ekf9_fixed", "ekf9_adaptive"]
    labels = ["GNSS\nraw", "CV-KF\nfixed", "CV-KF\nadaptive", "9-EKF\nfixed", "9-EKF\nadaptive"]
    colors = [PALETTE["raw"], PALETTE["fixed"], PALETTE["adaptive"], PALETTE["ekf"], PALETTE["adaptive"]]

    overall = [res["rmse_overall"][m] for m in methods]
    blocked = [res["rmse_blocked_segment"][m] for m in methods]

    x = np.arange(len(methods))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    b1 = ax.bar(x - w / 2, overall, w, label="Overall", color=colors, alpha=0.55, edgecolor="black", linewidth=0.8)
    b2 = ax.bar(x + w / 2, blocked, w, label="Blocked segment", color=colors, edgecolor="black", linewidth=0.8)

    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=9)

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
    ax.plot(bias, raw, "o--", color=PALETTE["raw"], linewidth=2, markersize=7, label="Raw GNSS")
    ax.plot(bias, fixed, "s-", color=PALETTE["fixed"], linewidth=2.4, markersize=7, label="Fixed-R KF")
    ax.plot(bias, adapt, "D-", color=PALETTE["adaptive"], linewidth=2.8, markersize=8, label="Adaptive-R KF (ours)")

    if cross is not None:
        ax.axvline(cross, color=PALETTE["win"], linestyle=":", linewidth=2)
        ax.annotate(f"crossover ≈ {cross} m\n(adaptive starts winning)",
                    xy=(cross, ax.get_ylim()[1] * 0.55),
                    xytext=(cross + 6, ax.get_ylim()[1] * 0.7),
                    fontsize=11, color=PALETTE["win"],
                    arrowprops=dict(arrowstyle="->", color=PALETTE["win"], lw=1.5))

    # Shade the deep-urban regime where adaptive wins.
    if cross is not None:
        ax.axvspan(cross, max(bias), color=PALETTE["win"], alpha=0.06)

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
