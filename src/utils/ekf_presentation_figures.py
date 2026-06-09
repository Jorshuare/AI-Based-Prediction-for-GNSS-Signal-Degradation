"""
ekf_presentation_figures.py — Quick figures for presentation (Option A synthetic demo).

Reuses ekf_demo.json results from adaptive_ekf.py --demo.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT = RESULTS / "paper_figures"
OUT.mkdir(parents=True, exist_ok=True)

# Colour palette (from make_paper_figures.py)
import matplotlib as _mpl
_CIV = _mpl.colormaps["cividis"]
def civ(t):
    r, g, b, _ = _CIV(float(t))
    return (r, g, b)

C_CLEAN = civ(0.12)
C_NEU = civ(0.70)
C_OURS = civ(0.18)
C_MARK = "#000000"

FONTS = {"base": 14, "label": 14, "tick": 13, "legend": 14, "value": 12, "annot": 13, "dpi": 300}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": FONTS["base"],
    "axes.titlesize": 1,
    "axes.labelsize": FONTS["label"], "axes.labelweight": "bold",
    "xtick.labelsize": FONTS["tick"], "ytick.labelsize": FONTS["tick"],
    "axes.edgecolor": "#444444", "axes.linewidth": 1.1,
    "legend.fontsize": FONTS["legend"], "figure.dpi": 110,
    "savefig.bbox": "tight", "savefig.facecolor": "white",
})

def style(ax):
    """Bold tick labels."""
    for lab in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        lab.set_fontweight("bold")
    ax.set_axisbelow(True)

def blegend(ax, **kw):
    leg = ax.legend(prop={"weight": "bold", "size": FONTS["legend"]}, **kw)
    return leg

def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=FONTS["dpi"])
    plt.close(fig)
    print(f"  [fig] {name}")


def fig_ekf_synthetic_demo():
    """
    Option A: Synthetic blockage scenario (for presentation tomorrow).

    Subfigures:
    (a) Trajectory: truth, raw GNSS, fixed-EKF, adaptive-EKF
    (b) Zoom on blockage segment (epochs 120–180)
    (c) Per-epoch RMSE during blockage vs. clean
    """
    # Load synthetic results
    ekf_demo_file = RESULTS / "ekf_demo.json"
    if not ekf_demo_file.exists():
        print("[warn] ekf_demo.json not found; run adaptive_ekf --demo first")
        return

    with open(ekf_demo_file) as fh:
        demo_data = json.load(fh)

    # Re-generate synthetic trajectory for plotting
    from src.models.adaptive_ekf import synthetic_demo
    try:
        demo_res = synthetic_demo(save=False)  # returns trajectory + metrics
    except Exception as e:
        print(f"[error] synthetic_demo failed: {e}")
        return

    # Extract from demo_res (assumed structure from adaptive_ekf.py)
    # For now, create a minimal version using the metrics in ekf_demo.json

    print("[info] fig_ekf_synthetic_demo: minimal version (metrics-only)")
    # A full implementation would regenerate the trajectory and plot it.
    # For presentation speed, we'll create a text-based metrics table instead.


def fig_ekf_metrics_table():
    """
    Simple metrics table for presentation slide.
    Output: table showing RMSE comparison (GNSS vs Fixed vs Adaptive).
    """
    ekf_demo_file = RESULTS / "ekf_demo.json"
    if not ekf_demo_file.exists():
        print("[warn] ekf_demo.json not found")
        return

    with open(ekf_demo_file) as fh:
        data = json.load(fh)

    # Extract metrics
    overall = data.get("rmse_overall", {})
    degraded = data.get("rmse_degraded_segment", {})

    print("[metrics] EKF Synthetic Blockage Results (Option A for Presentation)")
    print("-" * 70)
    print(f"Overall RMSE:       GNSS {overall.get('gnss_only')} m | "
          f"Fixed {overall.get('fixed_ekf')} m | "
          f"Adaptive {overall.get('adaptive_ekf')} m")
    if degraded:
        print(f"Blockage RMSE:      GNSS {degraded.get('gnss_only')} m | "
              f"Fixed {degraded.get('fixed_ekf')} m | "
              f"Adaptive {degraded.get('adaptive_ekf')} m")
        print(f"Improvement (degraded): {data.get('adaptive_improvement_pct_degraded', 'N/A')}%")
    print("-" * 70)


def fig_ekf_mechanism_concept():
    """
    Conceptual diagram of EKF predict-update cycle.
    No data needed; purely schematic.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Text-based schematic
    y_pos = [0.85, 0.70, 0.55, 0.40, 0.25]

    # Boxes
    ax.text(0.5, y_pos[0], "GNSS Measurement\n(noisy position)",
            ha="center", va="top", fontsize=12, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgrey", edgecolor=C_MARK, linewidth=2))

    ax.annotate("", xy=(0.5, y_pos[0]-0.05), xytext=(0.5, y_pos[1]+0.05),
                arrowprops=dict(arrowstyle="-|>", lw=2, color=C_MARK))

    ax.text(0.5, y_pos[1], "UPDATE (Kalman)\nR inflated if P(DEGRADED) high",
            ha="center", va="top", fontsize=12, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=civ(0.50), edgecolor=C_MARK, linewidth=2))

    ax.annotate("", xy=(0.5, y_pos[1]-0.05), xytext=(0.5, y_pos[2]+0.05),
                arrowprops=dict(arrowstyle="-|>", lw=2, color=C_MARK))

    ax.text(0.5, y_pos[2], "Filtered Position\n(smoother, more robust)",
            ha="center", va="top", fontsize=12, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=C_OURS, edgecolor=C_MARK, linewidth=2, alpha=0.7))

    ax.annotate("", xy=(0.5, y_pos[2]-0.05), xytext=(0.5, y_pos[3]+0.05),
                arrowprops=dict(arrowstyle="-|>", lw=2, color=C_MARK))

    ax.text(0.5, y_pos[3], "PREDICT (Motion Model)\nDead-reckoning via velocity",
            ha="center", va="top", fontsize=12, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=civ(0.40), edgecolor=C_MARK, linewidth=2))

    ax.annotate("", xy=(0.5, y_pos[3]-0.05), xytext=(0.5, y_pos[4]+0.05),
                arrowprops=dict(arrowstyle="-|>", lw=2, color=C_MARK))

    ax.text(0.5, y_pos[4], "[Repeat: PREDICT → UPDATE]",
            ha="center", va="top", fontsize=11, style="italic", color=C_MARK, fontweight="bold")

    # Right side: R adaptation concept
    ax.text(0.85, 0.65, "When P(DEGRADED) ↑\nR ↑ (distrust GNSS)\nLean on motion model",
            ha="left", va="center", fontsize=10, color=C_MARK, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.8))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.savefig(OUT / "fig_ekf_mechanism_concept.png", dpi=FONTS["dpi"], bbox_inches="tight")
    plt.close(fig)
    print(f"  [fig] fig_ekf_mechanism_concept")


if __name__ == "__main__":
    print("[presentation] Generating EKF figures for tomorrow's presentation...\n")

    # Generate metrics summary
    fig_ekf_metrics_table()

    # Generate mechanism diagram
    fig_ekf_mechanism_concept()

    print("\n[done] Presentation figures ready in results/paper_figures/")
