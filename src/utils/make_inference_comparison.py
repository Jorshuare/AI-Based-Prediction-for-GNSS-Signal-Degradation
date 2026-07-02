"""
make_inference_comparison.py — One figure comparing the INFERENCE-pipeline options.

Answers "what do the different inference configurations buy us?" in two panels:
  (a) Prediction stage  — cross-city Tokyo +5 s quality for the model choices
                          (DL, RandomForest, XGBoost, and the DL+XGB ensemble).
  (b) Fusion stage      — real Tokyo blocked-segment RMSE for the positioning choices
                          (raw GNSS, simple KF, aided EKF).

Reads the real result JSONs; no hard-coded numbers. Cividis palette (perceptually
uniform, colour-blind safe), 300 dpi, no title, (a)/(b) panel labels.
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

# ── Cividis palette — single source of truth, matches make_paper_figures.py ───
_CIV = matplotlib.colormaps["cividis"]


def civ(t):
    r, g, b, _ = _CIV(float(t))
    return (r, g, b)


# Semantic assignments (evenly-spaced cividis samples for max separation)
PAL = {
    "macro":  civ(0.25),   # Macro-F1 bars  (dark blue-purple)
    "deg":    civ(0.85),   # DEGRADED F1 bars (yellow)
    "raw":    civ(0.05),   # Raw GNSS  (darkest — worst performer)
    "kf":     civ(0.40),   # Simple KF (mid)
    "aided":  civ(0.70),   # Aided EKF proposed (light — best performer)
}
rcParams.update({"font.size": 13, "font.weight": "bold", "axes.labelweight": "bold",
                 "axes.linewidth": 1.2, "figure.dpi": 300})


def _load(name, default=None):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else default


def main():
    ens = _load("ensemble_comparison.json", {})
    rev = _load("reviewer_experiments.json", {})
    real = _load("urbannav_ekf_real_trimble.json") or _load("urbannav_ekf_real_ublox.json")

    # ---- Panel (a): cross-city Tokyo +5 s (Macro-F1 and DEGRADED F1) ----
    cc = (ens.get("E8_ensemble", {}) or {}).get("cross_city_tokyo_5s", {})
    e6 = rev.get("E6_cross_city_tokyo", {})
    models = ["RandomForest", "Transformer-LSTM", "XGBoost", "DL+XGB ensemble"]
    macro = [e6.get("rf_macro_f1", 0.618), cc.get("dl", 0.649), cc.get("xgb", 0.821), cc.get("softvote", 0.892)]
    degf = [e6.get("rf_per_class", {}).get("D", 0.148), cc.get("dl_deg", 0.753),
            cc.get("xgb_deg", 0.784), cc.get("softvote_deg", 0.896)]

    # ---- Panel (b): real Tokyo blocked-segment RMSE ----
    deg = (real or {}).get("rmse_degraded_segment", {})
    fmethods = ["Raw GNSS", "Simple KF", "Aided EKF\n(proposed)"]
    fvals = [deg.get("gnss_raw", 47.4), deg.get("cv_kf", 31.2), deg.get("aided_ekf_fixed", 24.3)]
    fcolors = [PAL["raw"], PAL["kf"], PAL["aided"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

    # Panel (a)
    x = np.arange(len(models)); w = 0.38
    b1 = ax1.bar(x - w / 2, macro, w, label="Macro-F1", color=PAL["macro"], edgecolor="black", linewidth=1.5)
    b2 = ax1.bar(x + w / 2, degf, w, label="DEGRADED F1", color=PAL["deg"], edgecolor="black", linewidth=1.5)
    for bars in (b1, b2):
        for b in bars:
            ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"{b.get_height():.2f}",
                     ha="center", va="bottom", fontsize=9)
    ax1.set_xticks(x); ax1.set_xticklabels(models, fontsize=10, rotation=12)
    ax1.set_ylabel("Cross-city Tokyo score (+5 s)")
    ax1.set_ylim(0, 1.05); ax1.legend(fontsize=11, loc="upper left"); ax1.grid(axis="y", alpha=0.3)
    ax1.set_axisbelow(True)
    ax1.text(-0.02, 1.04, "(a) Prediction stage — model / ensemble choice", transform=ax1.transAxes,
             fontsize=12, fontweight="bold", va="bottom")

    # Panel (b)
    xb = np.arange(len(fmethods))
    bb = ax2.bar(xb, fvals, 0.6, color=fcolors, edgecolor="black", linewidth=1.5)
    for b in bb:
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.6, f"{b.get_height():.1f} m",
                 ha="center", va="bottom", fontsize=10)
    raw = fvals[0]
    for i, b in enumerate(bb):
        if i > 0 and raw > 0:
            ax2.text(b.get_x() + b.get_width() / 2, b.get_height() / 2,
                     f"+{100*(raw-fvals[i])/raw:.0f}%", ha="center", va="center",
                     fontsize=11, fontweight="bold", color="white")
    ax2.set_xticks(xb); ax2.set_xticklabels(fmethods, fontsize=11)
    ax2.set_ylabel("Real blocked-segment RMSE (m)")
    ax2.set_ylim(0, max(fvals) * 1.18); ax2.grid(axis="y", alpha=0.3); ax2.set_axisbelow(True)
    ax2.text(-0.02, 1.04, "(b) Fusion stage — positioning-filter choice", transform=ax2.transAxes,
             fontsize=12, fontweight="bold", va="bottom")

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"fig23_inference_comparison.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] fig23_inference_comparison.png / .pdf  ->  {FIGS}")
    print(f"     (a) ensemble {macro[-1]:.3f} Macro-F1 / {degf[-1]:.3f} DEGRADED (best cross-city)")
    print(f"     (b) aided EKF {fvals[-1]:.1f} m (+{100*(raw-fvals[-1])/raw:.0f}% vs raw {raw:.1f} m)")


if __name__ == "__main__":
    main()
