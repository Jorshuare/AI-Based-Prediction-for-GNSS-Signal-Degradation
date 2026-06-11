"""
make_paper_figures.py — Publication-quality figures for SENTINEL-GNSS papers + slides.

Design rules (per project standard):
  • Colour-blind-safe **cividis** palette only — single source of truth (PALETTE/civ()).
  • NO figure titles (captions live in the paper). Context goes in axis labels.
  • Multi-panel figures carry (a)/(b)/(c) labels for caption referencing.
  • Legends + axis labels are BOLD at 14 pt; tick labels bold.
  • Vector PDF + 300-dpi PNG into results/paper_figures/.

Every number is read from a confirmed results JSON when present, else from the confirmed
Run-14 constants below (traceable to papers/RESULTS_REFERENCE.md).

Run:  python -m src.utils.make_paper_figures
"""
from __future__ import annotations
import matplotlib as _mpl
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.pyplot as plt
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
OUT = RES / "paper_figures"
OUT.mkdir(parents=True, exist_ok=True)

# ── Single source of truth: cividis colour-blind-safe palette ─────────────────
# cividis is perceptually uniform and safe for all colour-vision deficiencies.
# Categorical colours are evenly-spaced samples of the cividis colormap; callout
# TEXT/ARROWS use a dark colour (C_MARK) because the cividis high end is yellow.
_CIV = _mpl.colormaps["cividis"]


def civ(t):
    r, g, b, _ = _CIV(float(t))
    return (r, g, b)


PALETTE = {
    "c0": civ(0.00), "c1": civ(0.20), "c2": civ(0.40),
    "c3": civ(0.60), "c4": civ(0.80), "c5": civ(1.00),
    "black": "#000000", "grey": "#7A7A7A", "white": "#FFFFFF",
}
# semantic assignments (consistent across every figure), sampled from cividis
C_CLEAN = civ(0.12)            # CLEAN    (dark blue)
C_WARN = civ(0.52)            # WARNING  (slate)
C_DEG = civ(0.92)            # DEGRADED (yellow)  -- bars/fills only
C_OURS = civ(0.18)            # SENTINEL-GNSS / DL (dark)
C_BASE = civ(0.70)            # tree / baseline    (light)
C_ACC = civ(0.45)            # secondary series (e.g. MCC)
C_ENS = civ(0.62)            # ensemble series
C_NEU = PALETTE["grey"]
# readable callout text / arrows (never yellow on white)
C_MARK = PALETTE["black"]

# ── Single source of truth: font sizes (pt) ───────────────────────────────────
FONTS = {
    "base":   14,   # base font
    "label":  14,   # axis labels (bold)
    "tick":   13,   # tick labels (bold)
    "legend": 14,   # legend text (bold)
    "value":  12,   # in-bar / on-point value annotations (bold)
    "annot":  13,   # callout annotations (bold)
    "big":    15,   # emphasis text in concept figures
    "panel":  17,   # (a)/(b)/(c) panel labels
    "dpi":    300,  # export resolution
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": FONTS["base"],
    "axes.titlesize": 1,                # titles disabled by rule
    "axes.labelsize": FONTS["label"], "axes.labelweight": "bold",
    "xtick.labelsize": FONTS["tick"], "ytick.labelsize": FONTS["tick"],
    "axes.edgecolor": "#444444", "axes.linewidth": 1.1,
    "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.8,
    "legend.fontsize": FONTS["legend"], "figure.dpi": 110,
    "savefig.bbox": "tight", "savefig.facecolor": "white",
})


def style(ax):
    """Bold tick labels; clean look."""
    for lab in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        lab.set_fontweight("bold")
    ax.set_axisbelow(True)


def blegend(ax, **kw):
    leg = ax.legend(prop={"weight": "bold", "size": FONTS["legend"]}, **kw)
    return leg


def panel(ax, letter):
    ax.text(-0.10, 1.06, f"({letter})", transform=ax.transAxes,
            fontsize=FONTS["panel"], fontweight="bold", va="top", ha="right")


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=FONTS["dpi"])
    plt.close(fig)
    print(f"  [fig] {name}")


def load_json(p):
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return None


# ── Confirmed Run-14 constants (traceable to RESULTS_REFERENCE.md) ────────────
HZ = ["+5s", "+15s", "+30s"]
FULL = {
    "+5s":  {"macro_f1": 0.8206, "mcc": 0.7729, "accuracy": 0.8535, "CLEAN": 0.927, "WARNING": 0.817, "DEGRADED": 0.718},
    "+15s": {"macro_f1": 0.7412, "mcc": 0.6908, "accuracy": 0.7888, "CLEAN": 0.919, "WARNING": 0.722, "DEGRADED": 0.583},
    "+30s": {"macro_f1": 0.7825, "mcc": 0.7314, "accuracy": 0.8304, "CLEAN": 0.911, "WARNING": 0.807, "DEGRADED": 0.629},
}
CI = {"+5s": (0.798, 0.840), "+15s": (0.717, 0.764), "+30s": (0.758, 0.804)}
COMPARISON = {
    "Majority": 0.2016, "C/N0 rule": 0.0735, "RF (SMOTE)": 0.9094, "XGB (SMOTE)": 0.9098,
    "RF (no-SMOTE)": 0.9103, "XGB (no-SMOTE)": 0.9193, "Transformer-only": 0.7672,
    "LSTM-only": 0.7674, "SENTINEL-GNSS": 0.8206,
}
ABLATION = {
    "Transformer-only": {"macro": 0.7672, "mcc": 0.7248, "deg": 0.571},
    "LSTM-only":        {"macro": 0.7674, "mcc": 0.7018, "deg": 0.645},
    "Full (ours)":      {"macro": 0.8206, "mcc": 0.7729, "deg": 0.718},
}
CROSS = {
    "DL": {"Hangzhou": 0.8218, "tokyo": 0.6489, "tok_CLEAN": 0.9256, "tok_WARNING": 0.2683, "tok_DEGRADED": 0.7528},
    "RF": {"Hangzhou": 0.9260, "tokyo": 0.6178, "tok_CLEAN": 0.9896, "tok_WARNING": 0.7159, "tok_DEGRADED": 0.1478},
}
LAT = {"DL": 0.0389, "RF": 0.4090}
DEG_PROG = {"Run 10": 0.274, "Run 11": 0.274, "Run 12": 0.307, "Run 14": 0.718}
DATASET = {
    "Scenarios A-E\n(Beihang/Hangzhou)": 7193, "Supervisor Veh.\n(Hangzhou)": 3401,
    "UrbanNav Deep\n(Hong Kong)": 15233, "UrbanNav Harsh\n(Hong Kong)": 33429,
    "UrbanNav Med/Tun\n(Hong Kong)": 11069, "Tokyo\n(Odaiba+Shinjuku)": 49868,
}
SPLITS = {"Train": (11438, 37494, 13481), "Val": (
    13708, 3243, 1123), "Test": (731, 746, 209)}


def _full_from_json():
    m = load_json(RES / "figures" / "metrics_test.json")
    if not m:
        return "constants"
    for hk, h in [("5s", "+5s"), ("15s", "+15s"), ("30s", "+30s")]:
        r = m.get(hk, {})
        if r:
            FULL[h]["macro_f1"] = r.get("macro_f1", FULL[h]["macro_f1"])
            FULL[h]["mcc"] = r.get("mcc", FULL[h]["mcc"])
            FULL[h]["accuracy"] = r.get("accuracy", FULL[h]["accuracy"])
            for c in ("CLEAN", "WARNING", "DEGRADED"):
                if c in r.get("per_class", {}):
                    FULL[h][c] = r["per_class"][c].get("f1", FULL[h][c])
    return "metrics_test.json"


def _bars(ax, x, vals, w, color, label, fmt="{:.3f}", fs=12, ytext=0.012):
    ax.bar(x, vals, w, color=color, label=label,
           edgecolor="white", linewidth=0.6)
    for xi, v in zip(x, vals):
        ax.text(xi, v + ytext, fmt.format(v), ha="center",
                fontsize=fs, fontweight="bold")


# ══════════════════════════════════════════════════════════════════════════════
# Individual figures
# ══════════════════════════════════════════════════════════════════════════════
def fig_multihorizon():
    x = np.arange(len(HZ))
    w = 0.35
    fig, ax = plt.subplots(figsize=(7, 4.6))
    mf = [FULL[h]["macro_f1"] for h in HZ]
    mc = [FULL[h]["mcc"] for h in HZ]
    err = [[max(0, FULL[h]["macro_f1"] - CI[h][0]) for h in HZ],
           [max(0, CI[h][1] - FULL[h]["macro_f1"]) for h in HZ]]
    ax.bar(x - w/2, mf, w, yerr=err, capsize=5,
           color=C_OURS, label="Macro-F1", edgecolor="white")
    ax.bar(x + w/2, mc, w, color=C_ACC, label="MCC", edgecolor="white")
    for xi, v in zip(x - w/2, mf):
        ax.text(xi, v + 0.012, f"{v:.3f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    for xi, v in zip(x + w/2, mc):
        ax.text(xi, v + 0.012, f"{v:.3f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(HZ)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Prediction horizon")
    ax.set_ylabel("Score")
    blegend(ax, loc="lower left")
    style(ax)
    save(fig, "fig01_multihorizon")


def fig_perclass():
    x = np.arange(len(HZ))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for k, (cls, col) in enumerate([("CLEAN", C_CLEAN), ("WARNING", C_WARN), ("DEGRADED", C_DEG)]):
        vals = [FULL[h][cls] for h in HZ]
        ax.bar(x + (k - 1) * w, vals, w, color=col,
               label=cls, edgecolor="white")
        for xi, v in zip(x + (k - 1) * w, vals):
            ax.text(xi, v + 0.012, f"{v:.2f}", ha="center",
                    fontsize=FONTS["value"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(HZ)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Prediction horizon")
    ax.set_ylabel("F1")
    blegend(ax, ncol=3, loc="lower center")
    style(ax)
    save(fig, "fig02_perclass_f1")


def fig_comparison():
    items = sorted(COMPARISON.items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    cols = [C_OURS if "SENTINEL" in n else (C_BASE if (
        "XGB" in n or "RF" in n) else C_NEU) for n in names]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(names, vals, color=cols, edgecolor="white")
    for i, v in enumerate(vals):
        ax.text(v + 0.01, i, f"{v:.3f}", va="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Macro-F1  (+5 s, in-domain test)")
    ax.axvline(0.3333, color=C_NEU, ls="--", lw=1.2)
    ax.text(0.3333, -0.8, "random", color=C_NEU,
            fontsize=11, ha="center", fontweight="bold")
    style(ax)
    save(fig, "fig03_model_comparison")


def fig_ablation():
    names = list(ABLATION.keys())
    x = np.arange(len(names))
    w = 0.25
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for k, (key, lbl, col) in enumerate([("macro", "Macro-F1", C_OURS), ("mcc", "MCC", C_ACC), ("deg", "DEGRADED F1", C_DEG)]):
        vals = [ABLATION[n][key] for n in names]
        ax.bar(x + (k - 1) * w, vals, w, color=col,
               label=lbl, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(["Transformer\nonly", "LSTM\nonly", "Full\n(ours)"])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score  (+5 s)")
    blegend(ax, ncol=3, loc="lower center")
    style(ax)
    save(fig, "fig04_ablation")


def fig_crosscity_degraded():
    classes = ["CLEAN", "WARNING", "DEGRADED"]
    x = np.arange(3)
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    dl = [CROSS["DL"][f"tok_{c}"] for c in classes]
    rf = [CROSS["RF"][f"tok_{c}"] for c in classes]
    ax.bar(x - w/2, dl, w, color=C_OURS,
           label="SENTINEL-GNSS (DL)", edgecolor="white")
    ax.bar(x + w/2, rf, w, color=C_BASE,
           label="RandomForest", edgecolor="white")
    for xi, v in zip(x - w/2, dl):
        ax.text(xi, v + 0.015, f"{v:.2f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    for xi, v in zip(x + w/2, rf):
        ax.text(xi, v + 0.015, f"{v:.2f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.annotate("RF collapses\non DEGRADED", xy=(2 + w/2, rf[2]), xytext=(1.25, 0.45),
                arrowprops=dict(arrowstyle="->", color=C_MARK, lw=2),
                color=C_MARK, fontsize=FONTS["annot"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("F1 on unseen Tokyo")
    blegend(ax, loc="upper right")
    style(ax)
    save(fig, "fig05_crosscity_degraded")


def fig_crosscity_gap():
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    models = ["SENTINEL-GNSS\n(DL)", "RandomForest"]
    x = np.arange(2)
    w = 0.35
    bj = [CROSS["DL"]["Hangzhou"], CROSS["RF"]["Hangzhou"]]
    tk = [CROSS["DL"]["tokyo"], CROSS["RF"]["tokyo"]]
    ax.bar(x - w/2, bj, w, color=C_OURS,
           label="Beihang/Hangzhou (in-domain)", edgecolor="white")
    ax.bar(x + w/2, tk, w, color=C_BASE,
           label="Tokyo (unseen)", edgecolor="white")
    for i in range(2):
        ax.annotate(f"{tk[i]-bj[i]:+.2f}", xy=(i, tk[i]), xytext=(i, tk[i] - 0.14),
                    ha="center", color=(C_DEG if i == 1 else C_OURS), fontweight="bold", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Macro-F1")
    blegend(ax, loc="upper right")
    style(ax)
    save(fig, "fig06_crosscity_gap")


def fig_ekf_rmse():
    d = load_json(RES / "ekf_demo.json")
    if not d:
        print("  [skip] fig07 — no ekf_demo.json")
        return
    ov = d["rmse_overall"]
    seg = d.get("rmse_degraded_segment", {})
    labels = ["GNSS-only", "Fixed-R EKF", "Adaptive EKF\n(ours)"]
    keys = ["gnss_only", "fixed_ekf", "adaptive_ekf"]
    x = np.arange(3)
    w = 0.38
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.bar(x - w/2, [ov[k] for k in keys], w, color=C_NEU,
           label="Overall", edgecolor="white")
    ax.bar(x + w/2, [seg.get(k, 0) for k in keys], w,
           color=C_DEG, label="During blockage", edgecolor="white")
    for i, k in enumerate(keys):
        ax.text(i - w/2, ov[k] + 0.6, f"{ov[k]:.1f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
        if seg:
            ax.text(i + w/2, seg[k] + 0.6, f"{seg[k]:.1f}",
                    ha="center", fontsize=FONTS["value"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Position RMSE (m)")
    blegend(ax, loc="upper right")
    style(ax)
    save(fig, "fig07_ekf_rmse")


def fig_ekf_trajectory():
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from src.models.adaptive_ekf import AdaptiveEKF
        rng = np.random.default_rng(42)
        n = 300
        t = np.arange(n)
        truth = np.zeros((n, 2))
        truth[:, 0] = 2.0 * t
        truth[:, 1] = np.where(t < 150, 0.5 * t, 0.5 *
                               150 + 0.02 * (t - 150) ** 2)
        p = np.zeros(n)
        p[115:120] = np.linspace(0, 1, 5)
        p[120:180] = 1.0
        p[180:185] = np.linspace(1, 0, 5)
        gnss = truth.copy() + rng.normal(0, 3, (n, 2))
        gnss[120:180] += rng.normal(0, 30, (60, 2)) + np.array([25.0, -25.0])
        ekf = AdaptiveEKF()
        fixed = ekf.run(gnss, p, adaptive=False)
        adapt = ekf.run(gnss, p, adaptive=True)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(truth[:, 0], truth[:, 1], color=PALETTE["black"],
                lw=2.5, label="Ground truth")
        ax.scatter(gnss[:, 0], gnss[:, 1], s=9,
                   color=C_NEU, label="GNSS (raw)")
        ax.plot(fixed[:, 0], fixed[:, 1], color=C_WARN,
                lw=1.8, ls="--", label="Fixed-R EKF")
        ax.plot(adapt[:, 0], adapt[:, 1], color=C_OURS,
                lw=2.2, label="Adaptive EKF (ours)")
        ax.axvspan(2 * 120, 2 * 180, color=C_DEG, alpha=0.10)
        ax.text(2 * 150, truth[:, 1].max() * 0.95, "GNSS blockage",
                color=C_MARK, ha="center", fontsize=FONTS["annot"], fontweight="bold")
        ax.set_xlabel("East (m)")
        ax.set_ylabel("North (m)")
        blegend(ax, loc="upper left")
        style(ax)
        save(fig, "fig08_ekf_trajectory")
    except Exception as e:
        print(f"  [skip] fig08 — {e}")


def fig_deg_progress():
    runs = list(DEG_PROG.keys())
    vals = list(DEG_PROG.values())
    fig, ax = plt.subplots(figsize=(6.5, 4.3))
    ax.plot(runs, vals, "-o", color=C_OURS, lw=2.6, markersize=9)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.03, f"{v:.3f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.set_ylim(0, 0.85)
    ax.set_ylabel("DEGRADED F1  (+5 s)")
    ax.set_xlabel("Run")
    style(ax)
    save(fig, "fig09_degraded_progress")


def fig_dataset():
    items = sorted(DATASET.items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    cols = [C_OURS if ("Beihang" in n or "Hangzhou" in n) else (
        C_BASE if "Hong Kong" in n else C_ACC) for n in names]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(names, vals, color=cols, edgecolor="white")
    for i, v in enumerate(vals):
        ax.text(v + 400, i, f"{v:,}", va="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.set_xlabel("Labelled epochs")
    style(ax)
    save(fig, "fig10_dataset_composition")


def fig_splits():
    fig, ax = plt.subplots(figsize=(7, 4.4))
    names = list(SPLITS.keys())
    x = np.arange(len(names))
    c = np.array([SPLITS[n][0] for n in names], float)
    w = np.array([SPLITS[n][1] for n in names], float)
    g = np.array([SPLITS[n][2] for n in names], float)
    tot = c + w + g
    ax.bar(x, c / tot, color=C_CLEAN, label="CLEAN", edgecolor="white")
    ax.bar(x, w / tot, bottom=c / tot, color=C_WARN,
           label="WARNING", edgecolor="white")
    ax.bar(x, g / tot, bottom=(c + w) / tot, color=C_DEG,
           label="DEGRADED", edgecolor="white")
    for i in range(len(names)):
        ax.text(i, 1.02, f"n={int(tot[i]):,}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Class proportion")
    blegend(ax, ncol=3, loc="lower center")
    style(ax)
    save(fig, "fig11_class_distribution")


def fig_latency():
    fig, ax = plt.subplots(figsize=(6, 4.3))
    names = ["SENTINEL-GNSS\n(1 model, 3 horizons)",
             "RandomForest\n(3 models)"]
    vals = [LAT["DL"], LAT["RF"]]
    ax.bar(names, vals, color=[C_OURS, C_BASE], edgecolor="white")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.008, f"{v:.3f} ms", ha="center",
                fontsize=FONTS["annot"], fontweight="bold")
    ax.set_ylabel("Inference time (ms / sample, GPU)")
    ax.text(0.5, 0.85, f"{LAT['RF']/LAT['DL']:.1f}x faster", transform=ax.transAxes,
            ha="center", fontsize=FONTS["legend"], fontweight="bold", color=C_OURS)
    style(ax)
    save(fig, "fig12_latency")


def fig_reactive_vs_proactive():
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.plot([0.5, 9.5], [1, 1], color=C_NEU, lw=2.2)
    for s, lbl in [(3, "t-30s"), (5, "t-15s"), (6.5, "t-5s"), (8, "blockage\nt=0")]:
        ax.plot([s, s], [0.9, 1.1], color=C_NEU, lw=2)
        ax.text(s, 0.5, lbl, ha="center", fontsize=12,
                color=C_NEU, fontweight="bold")
    ax.add_patch(FancyBboxPatch((7.6, 1.4), 0.85, 0.5,
                 boxstyle="round,pad=0.05", fc=C_DEG, ec="none"))
    ax.text(8.02, 1.65, "REACTIVE", ha="center", va="center",
            color=PALETTE["black"], fontsize=FONTS["value"], fontweight="bold")
    for s, c in [(3, C_CLEAN), (5, C_WARN), (6.5, C_DEG)]:
        ax.add_patch(FancyBboxPatch((s - 0.42, 1.4), 0.85, 0.5,
                     boxstyle="round,pad=0.05", fc=c, ec="none"))
    ax.text(4.8, 2.55, "SENTINEL-GNSS: proactive warnings before the event",
            ha="center", color=C_OURS, fontsize=FONTS["big"], fontweight="bold")
    save(fig, "fig13_reactive_vs_proactive")


def fig_architecture():
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.axis("off")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    blocks = [("Input\n30x37", "#E8EEF5"), ("Linear\nProj.", "#D7E6F5"), ("Positional\nEncoding", "#D7E6F5"),
              ("Transformer\nx2 (8 heads)", C_BASE), ("BiLSTM\nx2 (h=256)", C_OURS),
              ("3 Heads\n+5/+15/+30s", PALETTE["black"])]
    xs = np.linspace(0.5, 10.0, len(blocks))
    for i, (txt, col) in enumerate(blocks):
        tc = "white" if col in (
            C_BASE, C_OURS, PALETTE["black"]) else PALETTE["black"]
        ax.add_patch(FancyBboxPatch(
            (xs[i], 1.0), 1.42, 1.0, boxstyle="round,pad=0.06", fc=col, ec=PALETTE["black"], lw=1.2))
        ax.text(xs[i] + 0.71, 1.5, txt, ha="center", va="center",
                color=tc, fontsize=FONTS["value"], fontweight="bold")
        if i < len(blocks) - 1:
            ax.add_patch(FancyArrowPatch(
                (xs[i] + 1.42, 1.5), (xs[i + 1], 1.5), arrowstyle="-|>", mutation_scale=15, color=C_NEU, lw=2))
    save(fig, "fig14_architecture")


def fig_pipeline():
    fig, ax = plt.subplots(figsize=(10.5, 2.8))
    ax.axis("off")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 2.4)
    steps = ["Raw RINEX\n+ NMEA", "Feature\nExtract (37)", "Label\nC/W/D", "30s Windows\n+ split",
             "Transformer\n-LSTM", "Predict\n+5/15/30s", "Adaptive\nEKF"]
    xs = np.linspace(0.3, 10.4, len(steps))
    for i, txt in enumerate(steps):
        col = PALETTE["black"] if i in (
            4, 6) else C_OURS if i == 5 else "#D7E6F5"
        tc = "white" if col in (PALETTE["black"], C_OURS) else PALETTE["black"]
        ax.add_patch(FancyBboxPatch(
            (xs[i], 0.7), 1.46, 1.0, boxstyle="round,pad=0.05", fc=col, ec=PALETTE["black"], lw=1.1))
        ax.text(xs[i] + 0.73, 1.2, txt, ha="center", va="center",
                color=tc, fontsize=FONTS["value"], fontweight="bold")
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch(
                (xs[i] + 1.46, 1.2), (xs[i + 1], 1.2), arrowstyle="-|>", mutation_scale=13, color=C_NEU, lw=2))
    save(fig, "fig15_pipeline")


# ══════════════════════════════════════════════════════════════════════════════
# Composite multi-panel figures (with (a)/(b)/(c) for captions)
# ══════════════════════════════════════════════════════════════════════════════
def fig_main_results():
    """(a) multi-horizon  (b) per-class  (c) ablation — the main results panel."""
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    # (a)
    x = np.arange(len(HZ))
    w = 0.35
    mf = [FULL[h]["macro_f1"] for h in HZ]
    mc = [FULL[h]["mcc"] for h in HZ]
    err = [[max(0, FULL[h]["macro_f1"] - CI[h][0]) for h in HZ],
           [max(0, CI[h][1] - FULL[h]["macro_f1"]) for h in HZ]]
    axs[0].bar(x - w/2, mf, w, yerr=err, capsize=4,
               color=C_OURS, label="Macro-F1", edgecolor="white")
    axs[0].bar(x + w/2, mc, w, color=C_ACC, label="MCC", edgecolor="white")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(HZ)
    axs[0].set_ylim(0, 1.0)
    axs[0].set_xlabel("Horizon")
    axs[0].set_ylabel("Score")
    blegend(axs[0], loc="lower left")
    # (b)
    for k, (cls, col) in enumerate([("CLEAN", C_CLEAN), ("WARNING", C_WARN), ("DEGRADED", C_DEG)]):
        axs[1].bar(x + (k - 1) * 0.26, [FULL[h][cls]
                   for h in HZ], 0.26, color=col, label=cls, edgecolor="white")
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(HZ)
    axs[1].set_ylim(0, 1.0)
    axs[1].set_xlabel("Horizon")
    axs[1].set_ylabel("F1")
    blegend(axs[1], ncol=1, loc="lower center")
    # (c)
    nm = list(ABLATION.keys())
    xa = np.arange(len(nm))
    for k, (key, lbl, col) in enumerate([("macro", "Macro-F1", C_OURS), ("mcc", "MCC", C_ACC), ("deg", "DEG F1", C_DEG)]):
        axs[2].bar(xa + (k - 1) * 0.25, [ABLATION[n][key]
                   for n in nm], 0.25, color=col, label=lbl, edgecolor="white")
    axs[2].set_xticks(xa)
    axs[2].set_xticklabels(["Trans.", "LSTM", "Full"])
    axs[2].set_ylim(0, 1.0)
    axs[2].set_xlabel("Architecture")
    axs[2].set_ylabel("Score (+5 s)")
    blegend(axs[2], loc="lower center")
    for a, l in zip(axs, "abc"):
        style(a)
        panel(a, l)
    fig.tight_layout()
    save(fig, "figC1_main_results")


def fig_crosscity_panel():
    """(a) per-class on Tokyo  (b) in-domain vs Tokyo gap."""
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
    classes = ["CLEAN", "WARNING", "DEGRADED"]
    x = np.arange(3)
    w = 0.36
    dl = [CROSS["DL"][f"tok_{c}"] for c in classes]
    rf = [CROSS["RF"][f"tok_{c}"] for c in classes]
    axs[0].bar(x - w/2, dl, w, color=C_OURS,
               label="SENTINEL-GNSS", edgecolor="white")
    axs[0].bar(x + w/2, rf, w, color=C_BASE,
               label="RandomForest", edgecolor="white")
    axs[0].annotate("RF collapses", xy=(2 + w/2, rf[2]), xytext=(1.2, 0.45),
                    arrowprops=dict(arrowstyle="->", color=C_MARK, lw=2), color=C_MARK, fontsize=FONTS["value"], fontweight="bold")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(classes)
    axs[0].set_ylim(0, 1.05)
    axs[0].set_ylabel("F1 on unseen Tokyo")
    blegend(axs[0], loc="upper right")
    x2 = np.arange(2)
    axs[1].bar(x2 - w/2, [CROSS["DL"]["Hangzhou"], CROSS["RF"]["Hangzhou"]],
               w, color=C_OURS, label="Beihang/Hangzhou", edgecolor="white")
    axs[1].bar(x2 + w/2, [CROSS["DL"]["tokyo"], CROSS["RF"]["tokyo"]],
               w, color=C_BASE, label="Tokyo", edgecolor="white")
    axs[1].set_xticks(x2)
    axs[1].set_xticklabels(["DL", "RF"])
    axs[1].set_ylim(0, 1.0)
    axs[1].set_ylabel("Macro-F1")
    blegend(axs[1], loc="upper right")
    for a, l in zip(axs, "ab"):
        style(a)
        panel(a, l)
    fig.tight_layout()
    save(fig, "figC2_crosscity")


def fig_ekf_panel():
    """(a) trajectory  (b) RMSE bars."""
    d = load_json(RES / "ekf_demo.json")
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from src.models.adaptive_ekf import AdaptiveEKF
        rng = np.random.default_rng(42)
        n = 300
        t = np.arange(n)
        truth = np.zeros((n, 2))
        truth[:, 0] = 2.0 * t
        truth[:, 1] = np.where(t < 150, 0.5 * t, 0.5 *
                               150 + 0.02 * (t - 150) ** 2)
        p = np.zeros(n)
        p[115:120] = np.linspace(0, 1, 5)
        p[120:180] = 1.0
        p[180:185] = np.linspace(1, 0, 5)
        gnss = truth.copy() + rng.normal(0, 3, (n, 2))
        gnss[120:180] += rng.normal(0, 30, (60, 2)) + np.array([25.0, -25.0])
        ekf = AdaptiveEKF()
        fixed = ekf.run(gnss, p, adaptive=False)
        adapt = ekf.run(gnss, p, adaptive=True)
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
        axs[0].plot(truth[:, 0], truth[:, 1],
                    color=PALETTE["black"], lw=2.4, label="Ground truth")
        axs[0].scatter(gnss[:, 0], gnss[:, 1], s=8,
                       color=C_NEU, label="GNSS (raw)")
        axs[0].plot(fixed[:, 0], fixed[:, 1], color=C_WARN,
                    lw=1.8, ls="--", label="Fixed-R EKF")
        axs[0].plot(adapt[:, 0], adapt[:, 1], color=C_OURS,
                    lw=2.2, label="Adaptive EKF")
        axs[0].axvspan(2 * 120, 2 * 180, color=C_DEG, alpha=0.10)
        axs[0].set_xlabel("East (m)")
        axs[0].set_ylabel("North (m)")
        blegend(axs[0], loc="upper left")
        if d:
            ov = d["rmse_overall"]
            seg = d.get("rmse_degraded_segment", {})
            keys = ["gnss_only", "fixed_ekf", "adaptive_ekf"]
            xx = np.arange(3)
            w = 0.38
            axs[1].bar(xx - w/2, [ov[k] for k in keys], w,
                       color=C_NEU, label="Overall", edgecolor="white")
            axs[1].bar(xx + w/2, [seg.get(k, 0) for k in keys], w,
                       color=C_DEG, label="Blockage", edgecolor="white")
            for i, k in enumerate(keys):
                axs[1].text(i + w/2, seg.get(k, 0) + 0.6,
                            f"{seg.get(k, 0):.1f}", ha="center", fontsize=FONTS["value"], fontweight="bold")
            axs[1].set_xticks(xx)
            axs[1].set_xticklabels(["GNSS", "Fixed", "Adaptive"])
            axs[1].set_ylabel("RMSE (m)")
            blegend(axs[1], loc="upper right")
        for a, l in zip(axs, "ab"):
            style(a)
            panel(a, l)
        fig.tight_layout()
        save(fig, "figC3_ekf")
    except Exception as e:
        print(f"  [skip] figC3 — {e}")


def fig_ensemble():
    """E8 — DL/XGB/RF/Soft-vote/Stack, in-domain vs cross-city. The ensemble is best cross-city."""
    e = load_json(RES / "ensemble_comparison.json")
    rev = load_json(RES / "reviewer_experiments.json")
    # in-domain (test) +5s
    if e and "E8_ensemble" in e and "5s" in e["E8_ensemble"]:
        d = e["E8_ensemble"]["5s"]
        cc = e["E8_ensemble"].get("cross_city_tokyo_5s", {})
        ind = {"DL": d.get("dl"), "XGB": d.get("xgb"), "RF": d.get("rf"),
               "Soft-vote": d.get("softvote"), "Stack": d.get("stack")}
        rf_cc = (rev or {}).get("E6_cross_city_tokyo",
                                {}).get("rf_macro_f1", 0.6178)
        cro = {"DL": cc.get("dl", 0.6489), "XGB": cc.get("xgb", 0.8208), "RF": rf_cc,
               "Soft-vote": cc.get("softvote", 0.8919), "Stack": cc.get("stack", 0.8863)}
    else:  # confirmed Run-15 fallback
        ind = {"DL": 0.8218, "XGB": 0.9187, "RF": 0.926,
               "Soft-vote": 0.9112, "Stack": 0.8987}
        cro = {"DL": 0.6489, "XGB": 0.8208, "RF": 0.6178,
               "Soft-vote": 0.8919, "Stack": 0.8863}
    names = list(ind.keys())
    x = np.arange(len(names))
    w = 0.4
    cols = [C_OURS, C_BASE, C_NEU, C_ENS, civ(0.80)]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.bar(x - w/2, [ind[n] for n in names], w, color=C_NEU,
           label="In-domain (Beihang/Hangzhou)", edgecolor="white")
    ax.bar(x + w/2, [cro[n] for n in names], w, color=C_ENS,
           label="Cross-city (unseen Tokyo)", edgecolor="white")
    for xi, n in zip(x - w/2, names):
        ax.text(xi, ind[n] + 0.012, f"{ind[n]:.2f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    for xi, n in zip(x + w/2, names):
        ax.text(xi, cro[n] + 0.012, f"{cro[n]:.2f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Macro-F1 (+5 s)")
    ax.annotate("ensemble best\ncross-city", xy=(3 + w/2, cro["Soft-vote"]), xytext=(2.4, 0.42),
                arrowprops=dict(arrowstyle="->", color=C_MARK, lw=2), color=C_MARK, fontsize=FONTS["annot"], fontweight="bold")
    blegend(ax, loc="lower left")
    style(ax)
    save(fig, "fig16_ensemble")


def fig_persistence():
    """E9 — persistence baseline vs models across horizons (is memory needed?)."""
    e = load_json(RES / "ensemble_comparison.json")
    pers = {"+5s": 0.9077, "+15s": 0.871, "+30s": 0.8263}
    chg = {"+5s": 0.0558, "+15s": 0.0795, "+30s": 0.1068}
    tree = {"+5s": 0.926, "+15s": 0.9121, "+30s": 0.8989}
    if e and "E9_persistence" in e:
        for h, k in [("+5s", "5s"), ("+15s", "15s"), ("+30s", "30s")]:
            if k in e["E9_persistence"]:
                pers[h] = e["E9_persistence"][k].get(
                    "persistence_macro_f1", pers[h])
                chg[h] = e["E9_persistence"][k].get(
                    "label_change_rate", chg[h])
        for h, k in [("+5s", "5s"), ("+15s", "15s"), ("+30s", "30s")]:
            if k in e.get("E10_horizon_gap", {}):
                g = e["E10_horizon_gap"][k]
                tree[h] = max(g.get("rf", 0), g.get("xgb", 0)) or tree[h]
    dl = {h: FULL[h]["macro_f1"] for h in HZ}
    x = np.arange(len(HZ))
    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    ax.plot(x, [pers[h] for h in HZ], "-o", color=C_NEU,
            lw=2.4, ms=9, label="Persistence baseline")
    ax.plot(x, [tree[h] for h in HZ], "-s", color=C_BASE,
            lw=2.4, ms=9, label="Best tree (RF/XGB)")
    ax.plot(x, [dl[h] for h in HZ], "-^", color=C_OURS,
            lw=2.4, ms=9, label="SENTINEL-GNSS (DL)")
    for h, xi in zip(HZ, x):
        ax.text(xi, pers[h] + 0.012, f"{pers[h]:.2f}", ha="center",
                fontsize=FONTS["value"], fontweight="bold", color=C_MARK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{h}\n({chg[h]*100:.0f}% change)" for h in HZ])
    ax.set_ylim(0.6, 1.0)
    ax.set_xlabel("Horizon  (label-change rate)")
    ax.set_ylabel("Macro-F1")
    blegend(ax, loc="lower left")
    style(ax)
    save(fig, "fig17_persistence")


def fig_ekf_realdata():
    """Real-data case study: adaptive EKF on an actual Beihang field NMEA run.

    Reads the EKF track produced by `python -m src.models.inference --ekf` on a real
    collection (no synthetic). Shows (a) the real GNSS track vs the adaptive-EKF track with
    predicted-degraded epochs shaded, and (b) the model's per-epoch P(DEGRADED). RMSE is NOT
    reported here because these files have no independent reference trajectory (that needs the
    UrbanNav reference.csv / RTK step) — this panel demonstrates the closed loop on real data.
    """
    inf = RES / "inference"
    npzs = sorted(inf.glob("*_ekf.npz")) if inf.exists() else []
    if not npzs:
        print(
            "  [skip] fig18_ekf_realdata — no results/inference/*_ekf.npz (run inference --ekf)")
        return
    d = np.load(npzs[0])
    gnss, adapt, p = d["gnss"], d["adaptive"], d["p_degraded"]
    # local ENU-ish metres: centre and scale lon by cos(lat) already handled upstream; here the
    # arrays are already projected x,y in metres from inference. Recentre for readability.
    g = gnss - gnss.mean(0)
    a = adapt - adapt.mean(0)
    deg = p > 0.5
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(
        12.4, 4.9), gridspec_kw={"width_ratios": [1.25, 1]})
    # (a) trajectory
    ax0.plot(g[:, 0], g[:, 1], "-", color=C_NEU,
             lw=1.3, alpha=0.7, label="Raw GNSS")
    ax0.plot(a[:, 0], a[:, 1], "-", color=C_OURS,
             lw=2.2, label="Adaptive EKF (ours)")
    ax0.scatter(g[deg, 0], g[deg, 1], s=16, color=C_DEG, edgecolor=C_MARK, lw=0.3,
                zorder=5, label="Predicted DEGRADED")
    ax0.set_xlabel("East (m)")
    ax0.set_ylabel("North (m)")
    ax0.set_aspect("equal", "datalim")
    blegend(ax0, loc="best")
    style(ax0)
    panel(ax0, "a")
    # (b) P(DEGRADED) timeline
    t = np.arange(len(p))
    ax1.fill_between(t, 0, p, color=C_ENS, alpha=0.35)
    ax1.plot(t, p, "-", color=C_OURS, lw=2.0)
    ax1.axhline(0.5, color=C_MARK, ls="--", lw=1.4)
    ax1.text(len(p) * 0.02, 0.53, "trust threshold", color=C_MARK,
             fontsize=FONTS["annot"], fontweight="bold")
    ax1.set_xlabel("Epoch (1 Hz)")
    ax1.set_ylabel("P(DEGRADED)  +5 s")
    ax1.set_ylim(0, 1.02)
    style(ax1)
    panel(ax1, "b")
    save(fig, "fig18_ekf_realdata")


def main():
    src = _full_from_json()
    print(f"SENTINEL-GNSS paper figures -> {OUT}")
    print(
        f"Full-model numbers source: {src}  | palette: cividis (colour-blind safe)")
    figs = [fig_multihorizon, fig_perclass, fig_comparison, fig_ablation, fig_crosscity_degraded,
            fig_crosscity_gap, fig_ekf_rmse, fig_ekf_trajectory, fig_deg_progress, fig_dataset,
            fig_splits, fig_latency, fig_reactive_vs_proactive, fig_architecture, fig_pipeline,
            fig_ensemble, fig_persistence, fig_ekf_realdata,
            fig_main_results, fig_crosscity_panel, fig_ekf_panel]
    for fn in figs:
        try:
            fn()
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {e}")
    n = len(list(OUT.glob("*.png")))
    print(f"\n[done] {n} figures in {OUT}")


if __name__ == "__main__":
    main()
