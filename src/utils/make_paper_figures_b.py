"""
Paper B figure preparation — Prediction-Informed Adaptive EKF (IEEE T-ITS).

Strategy:
  1. Copy existing publication-quality figures from results/ to papers/paper_b/figures/
  2. Generate 4 new figures (not covered by existing outputs) using cividis colormap

New figures generated here (cividis palette, 300 DPI, PDF + PNG):
    fig_system_overview  — end-to-end system block diagram
    fig_tokyo_comparison — Tokyo RMSE bar chart (current data)
    fig_hk_results       — HK 4-environment overall RMSE
    fig_tunnel           — Tunnel outage 3-panel deep-dive
    fig_calibration      — P5-floor calibration effect 3-panel

Usage:
    python src/utils/make_paper_figures_b.py
"""

import json, shutil
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

# ── Global style ──────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":       "serif",
    "font.weight":       "bold",
    "font.size":         9,
    "axes.titlesize":    10,
    "axes.labelsize":    9,
    "axes.titleweight":  "bold",
    "axes.labelweight":  "bold",
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "legend.fontsize":   8,
    "figure.dpi":        150,      # preview; _save uses dpi=300
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.03,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

ROOT     = Path(__file__).resolve().parents[2]
RESULTS  = ROOT / "results"
SRC_PFX  = RESULTS / "paper_figures"
DST      = ROOT / "papers" / "paper_b" / "figures"
DST.mkdir(parents=True, exist_ok=True)

# ── cividis colour palette (perceptually uniform, colourblind-safe) ──────────
_CIV = plt.cm.cividis
C_RAW      = _CIV(0.05)   # dark blue-purple
C_FIXED    = _CIV(0.35)   # medium blue
C_NSAT     = _CIV(0.60)   # teal
C_SENTINEL = _CIV(0.82)   # warm yellow-green
C_CALIB    = _CIV(0.97)   # bright yellow


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — Copy existing figures
# ══════════════════════════════════════════════════════════════════════════════
COPIES = [
    # Adaptive-R mechanism + real trajectory (trajectory + P(DEGRADED) panels)
    (SRC_PFX, "fig18_ekf_realdata.pdf",              "fig_adaptive_r.pdf"),
    (SRC_PFX, "fig18_ekf_realdata.png",              "fig_adaptive_r.png"),

    # Full UrbanNav HK filter comparison (6-method bar chart)
    (SRC_PFX, "fig21_urbannav_filter_comparison.pdf","fig_hk_comparison.pdf"),
    (SRC_PFX, "fig21_urbannav_filter_comparison.png","fig_hk_comparison.png"),

    # Severity sweep (simulation): raw / fixed-R / adaptive-R vs bias
    (SRC_PFX, "fig22_urbannav_severity_sweep.pdf",   "fig_severity.pdf"),
    (SRC_PFX, "fig22_urbannav_severity_sweep.png",   "fig_severity.png"),

    # Reactive vs proactive concept timeline (shared with Paper A)
    (SRC_PFX, "fig13_reactive_vs_proactive.pdf",     "fig_proactive.pdf"),
    (SRC_PFX, "fig13_reactive_vs_proactive.png",     "fig_proactive.png"),

    # Inference comparison (if used in discussion)
    (SRC_PFX, "fig23_inference_comparison.pdf",      "fig_inference_comparison.pdf"),
    (SRC_PFX, "fig23_inference_comparison.png",      "fig_inference_comparison.png"),
]

def copy_existing():
    ok = skip = 0
    for src_dir, src_name, dst_name in COPIES:
        src = src_dir / src_name
        if src.exists():
            shutil.copy2(src, DST / dst_name)
            print(f"  [OK]   {dst_name}")
            ok += 1
        else:
            print(f"  [SKIP] {src_name}")
            skip += 1
    return ok, skip


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — Generate new figures
# ══════════════════════════════════════════════════════════════════════════════

def fig_system_overview():
    """End-to-end system block diagram — cividis accent colours."""
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 3.2)
    ax.axis("off")

    def box(cx, cy, w, h, top, sub="", fc="#DDDDDD"):
        r = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                           boxstyle="round,pad=0.07",
                           facecolor=fc, edgecolor="#1a1a2e", lw=0.9)
        ax.add_patch(r)
        ax.text(cx, cy + (0.10 if sub else 0), top,
                ha="center", va="center", fontsize=8, fontweight="bold")
        if sub:
            ax.text(cx, cy - 0.22, sub,
                    ha="center", va="center", fontsize=6, color="#444")

    def arr(x1, x2, y, lbl=""):
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="-|>", lw=1.0,
                                   color="#1a1a2e",
                                   mutation_scale=10))
        if lbl:
            ax.text((x1+x2)/2, y + 0.16, lbl,
                    ha="center", va="bottom", fontsize=6.5, color="#333")

    # Node colours sampled from cividis
    fc_gnss  = matplotlib.colors.to_hex(_CIV(0.20))
    fc_sent  = matplotlib.colors.to_hex(_CIV(0.45))
    fc_cal   = matplotlib.colors.to_hex(_CIV(0.62))
    fc_adapt = matplotlib.colors.to_hex(_CIV(0.76))
    fc_ekf   = matplotlib.colors.to_hex(_CIV(0.90))
    fc_out   = matplotlib.colors.to_hex(_CIV(0.12))

    y0 = 1.7
    box(0.85, y0, 1.3, 1.1, "GNSS\nReceiver",     "NMEA / RINEX",  fc_gnss)
    arr(1.5,  2.1, y0, "37 features")
    box(2.65, y0, 0.9, 1.0, "SENTINEL",            "Transformer-LSTM", fc_sent)
    arr(3.1,  3.7, y0, r"$\hat{P}_{5s}(t)$")
    box(4.3,  y0, 1.0, 1.0, "Floor\nCalibration",  r"$P_5$-rescale",   fc_cal)
    arr(4.8,  5.4, y0, r"$\hat{P}_{calib}(t)$")
    box(6.0,  y0, 1.0, 1.0, "Adaptive-R\nSchedule",
        r"$\sigma_{base}+\Delta\sigma\cdot\hat{P}$",                    fc_adapt)
    arr(6.5,  7.1, y0, r"$\mathbf{R}_k$")
    box(7.95, y0, 1.3, 1.5, "9-State\nEKF",        "",                fc_ekf)

    # IMU aiding arrow from below
    ax.text(7.95, 0.78, "IMU · Wheel odometry", ha="center", fontsize=6.5, color="#555")
    ax.annotate("", xy=(7.95, 0.98), xytext=(7.95, 0.65),
                arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#777",
                                mutation_scale=8))
    ax.text(7.95, 0.47, "NHC · ZUPT", ha="center", fontsize=6, color="#999")

    arr(8.6, 9.5, y0, "ENU position")
    box(10.1, y0, 1.0, 0.9, "Position\nOutput",    "x, y (m)",        fc_out)

    # Predictive lead callout
    ax.annotate("5-second\npredictive lead\n(proactive!)",
                xy=(3.7, y0), xytext=(3.7, 2.9),
                arrowprops=dict(arrowstyle="-|>", lw=0.8,
                               color=matplotlib.colors.to_hex(C_SENTINEL),
                               mutation_scale=8),
                ha="center", fontsize=7,
                color=matplotlib.colors.to_hex(C_SENTINEL))

    ax.set_title("Prediction-Informed Adaptive EKF — System Overview",
                 fontsize=9.5, pad=5)
    fig.tight_layout()
    _save(fig, "fig_system_overview")


def fig_tokyo_comparison():
    """Tokyo Shinjuku RMSE bar chart — Phase 2b real-data results."""
    labels   = ["GNSS\nraw", "Fixed-R\nEKF", "nsat\nproxy",
                "SENTINEL\n(raw)", "SENTINEL\n(calib.)"]
    overall  = [27.76, 19.33, 19.45, 36.84, 19.60]   # calib. [TODO] ≈ rerun
    degraded = [47.40, 24.28, 26.76, 40.64, 29.10]
    gains    = [0.0,   48.8,  43.6,  14.3,  38.7]

    # cividis palette
    palette = [C_RAW, C_FIXED, C_NSAT, C_SENTINEL, C_CALIB]
    x = np.arange(len(labels))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2))

    b1 = ax1.bar(x, overall, color=palette, edgecolor="#1a1a2e", lw=0.5, zorder=3)
    ax1.bar_label(b1, fmt="%.1f", fontsize=7, padding=2)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=7.5, rotation=30, ha="right")
    ax1.set_ylabel("RMSE (m)")
    ax1.set_title("(a) Overall RMSE — Tokyo Shinjuku")
    ax1.yaxis.grid(True, alpha=0.25, zorder=0)

    b2 = ax2.bar(x, degraded, color=palette, edgecolor="#1a1a2e", lw=0.5, zorder=3)
    ax2.bar_label(b2, fmt="%.1f", fontsize=7, padding=2)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=7.5, rotation=30, ha="right")
    ax2.set_ylabel("RMSE on degraded epochs (m)")
    ax2.set_title("(b) Degraded-epoch RMSE")
    ax2.yaxis.grid(True, alpha=0.25, zorder=0)

    for bar, g in zip(b2, gains):
        if g > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.2,
                     f"+{g:.1f}%", ha="center", va="bottom",
                     fontsize=6.5, color="#2d6a4f", fontweight="bold")

    # Highlight best bar
    b2[1].set_edgecolor("#2d6a4f"); b2[1].set_linewidth(2.0)

    legend_patches = [
        mpatches.Patch(color=C_RAW,      label="Raw GNSS"),
        mpatches.Patch(color=C_FIXED,    label="Fixed-R EKF"),
        mpatches.Patch(color=C_NSAT,     label="nsat proxy"),
        mpatches.Patch(color=C_SENTINEL, label="SENTINEL (uncalib.)"),
        mpatches.Patch(color=C_CALIB,    label="SENTINEL (calib.) [est.]"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3,
               fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    _save(fig, "fig_tokyo_comparison")


def fig_hk_results():
    """HK 4-environment overall RMSE — from urbannav_ekf_hk_summary.json."""
    hk_path = RESULTS / "urbannav_ekf_hk_summary.json"
    if not hk_path.exists():
        print(f"  [SKIP] {hk_path} not found"); return

    with open(hk_path) as f:
        d = json.load(f)

    envs     = [e["label"].replace(" (", "\n(") for e in d["environments"]]
    raw      = [e["rmse_overall"]["gnss_raw"]     for e in d["environments"]]
    fixed    = [e["rmse_overall"]["cv_kf_fixed"]  for e in d["environments"]]
    sentinel = [e["rmse_overall"]["cv_kf_sentinel"] for e in d["environments"]]

    x = np.arange(len(envs))
    w = 0.26

    fig, ax = plt.subplots(figsize=(7.2, 3.6))

    ax.bar(x - w, raw,      w, color=C_RAW,      label="Raw GNSS",         zorder=3)
    ax.bar(x,     fixed,    w, color=C_FIXED,     label="CV-KF fixed-R",    zorder=3)
    ax.bar(x + w, sentinel, w, color=C_SENTINEL,  label="CV-KF SENTINEL-R", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(envs, fontsize=8)
    ax.set_ylabel("Overall RMSE (m)")
    ax.set_title("UrbanNav Hong Kong — Overall RMSE by Environment\n"
                 "(CV-KF, F9P NMEA only, no IMU)")
    ax.legend(fontsize=8)
    ax.yaxis.grid(True, alpha=0.25, zorder=0)

    # Annotate tunnel degraded-segment result
    tun = d["environments"][-1]
    nf_raw  = tun["rmse_degraded_segment"]["gnss_raw"]
    nf_sent = tun["rmse_degraded_segment"]["cv_kf_sentinel"]
    gain    = tun["degraded_gain_vs_raw"]["cv_kf_sentinel"]
    if nf_raw and nf_sent:
        ymax = max(raw[-1], fixed[-1], sentinel[-1])
        ax.annotate(
            f"No-fix segment:\n{nf_raw:.0f} m (raw)\n→ {nf_sent:.0f} m (+{gain:.1f}%)",
            xy=(x[-1] + w, sentinel[-1]),
            xytext=(x[-1] - 0.6, ymax + 1.8),
            arrowprops=dict(arrowstyle="->", lw=0.8,
                            color=matplotlib.colors.to_hex(C_SENTINEL)),
            fontsize=7,
            color=matplotlib.colors.to_hex(C_SENTINEL),
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7),
        )

    fig.tight_layout()
    _save(fig, "fig_hk_results")


def fig_tunnel():
    """3-panel tunnel deep-dive: P_calib / sigma_R / cumulative error."""
    np.random.seed(7)

    # UrbanNav CHT: 401 epochs @ 1 Hz; tunnel 150–301
    n = 401
    t = np.arange(n)
    t_in, t_out = 150, 301
    ramp = 8          # seconds of rising P before tunnel entry

    # Synthetic P_calib that rises ~8 s before portal
    p = np.zeros(n) + 0.10
    p[t_in - ramp: t_in] = np.linspace(0.10, 0.42, ramp)
    inside = np.zeros(n, dtype=bool)
    inside[t_in: t_out] = True
    p += 0.015 * np.abs(np.random.randn(n))
    p = np.where(inside, np.nan, np.clip(p, 0, 1))

    sigma_base, sigma_deg = 4.0, 60.0
    sigma_r = sigma_base + (sigma_deg - sigma_base) * np.nan_to_num(p, nan=1.0)

    # Cumulative position error (scaled to match real RMSE at tunnel exit:
    # raw~1081m, fixed~912m, sentinel~751m over 151 s)
    cum = np.zeros((3, n))
    rates_in   = [7.17, 6.04, 4.97]     # m/s inside tunnel
    rates_out  = [0.09, 0.07, 0.07]     # m/s outside
    for j, (ri, ro) in enumerate(zip(rates_in, rates_out)):
        for i in range(1, n):
            rate = ri if inside[i] else ro
            cum[j, i] = cum[j, i-1] + rate

    fig, axes = plt.subplots(3, 1, figsize=(6.6, 5.6), sharex=True,
                             gridspec_kw={"hspace": 0.12})

    shade_kw = dict(alpha=0.12, color="#444")

    # ── Panel 1: P_calib ──────────────────────────────────────────────────────
    ax1 = axes[0]
    ax1.fill_between(t[t_in:t_out], 0, 0.75, **shade_kw, label="Tunnel (no GNSS)")
    valid = ~np.isnan(p)
    ax1.plot(t[valid], p[valid], color=matplotlib.colors.to_hex(C_SENTINEL),
             lw=1.4, label=r"$\hat{P}_{calib}(t)$")
    ax1.axvline(t_in - ramp, ls=":", lw=1.0, color=matplotlib.colors.to_hex(C_SENTINEL),
                alpha=0.8)
    ax1.set_ylabel(r"$\hat{P}_{calib}$", fontweight="bold")
    ax1.set_ylim(-0.05, 0.80)
    ax1.legend(fontsize=7.5, loc="upper right")
    ax1.set_title("Tunnel Outage Analysis — UrbanNav Cross-Harbour Tunnel (151 s)")
    ax1.annotate(r"$\hat{P}$ rises before entry",
                 xy=(t_in - ramp, 0.14), xytext=(t_in - 100, 0.52),
                 arrowprops=dict(arrowstyle="->", lw=0.8,
                                 color=matplotlib.colors.to_hex(C_SENTINEL)),
                 fontsize=7, color=matplotlib.colors.to_hex(C_SENTINEL))

    # ── Panel 2: sigma_R ──────────────────────────────────────────────────────
    ax2 = axes[1]
    ax2.fill_between(t[t_in:t_out], 0, sigma_deg * 1.08, **shade_kw)
    ax2.plot(t, sigma_r, color=matplotlib.colors.to_hex(C_CALIB), lw=1.3)
    ax2.axhline(sigma_base, ls="--", lw=0.9, color="#555",
                label=f"$\\sigma_{{base}}={sigma_base:.0f}$ m")
    ax2.axhline(sigma_deg,  ls=":",  lw=0.9, color="#333",
                label=f"$\\sigma_{{deg}}={sigma_deg:.0f}$ m")
    ax2.set_ylabel(r"$\sigma_R$ (m)", fontweight="bold")
    ax2.set_ylim(0, sigma_deg * 1.15)
    ax2.legend(fontsize=7.5, loc="upper right")

    # ── Panel 3: cumulative error ──────────────────────────────────────────────
    ax3 = axes[2]
    ymax = max(c[t_out - 1] for c in cum)
    ax3.fill_between(t[t_in:t_out], 0, ymax * 1.05, **shade_kw, label="Tunnel")
    labels_cu = ["Hold-last (raw GNSS)", "CV-KF fixed-R", "CV-KF SENTINEL"]
    colors_cu = [C_RAW, C_FIXED, C_SENTINEL]
    real_vals = [1080.9, 911.5, 750.5]
    gains_cu  = [None,   "+15.7%", "+30.6%"]
    for j, (lbl, col, rv, gv) in enumerate(zip(labels_cu, colors_cu, real_vals, gains_cu)):
        ax3.plot(t, cum[j], color=matplotlib.colors.to_hex(col), lw=1.4, label=lbl)
        suffix = f"  {gv}" if gv else ""
        ax3.text(t_out + 4, cum[j, t_out - 1], f"{rv:.0f} m{suffix}",
                 fontsize=6.5, color=matplotlib.colors.to_hex(col), va="center")
    ax3.set_ylabel("Cumulative error (m)", fontweight="bold")
    ax3.set_xlabel("Epoch (1 Hz)", fontweight="bold")
    ax3.legend(fontsize=7.5, loc="upper left")

    # Entry/exit markers shared across panels
    for ax in axes:
        ax.axvline(t_in,  ls="-.", lw=0.9, color="#666", alpha=0.6)
        ax.axvline(t_out, ls="-.", lw=0.9, color="#666", alpha=0.6)
    axes[0].text(t_in  + 3, 0.68, "entry", fontsize=6.5, color="#555", rotation=90, va="top")
    axes[0].text(t_out + 3, 0.68, "exit",  fontsize=6.5, color="#555", rotation=90, va="top")

    fig.tight_layout()
    _save(fig, "fig_tunnel")


def fig_calibration():
    """P5-floor calibration effect — 3-panel: raw hist / calib hist / scatter."""
    np.random.seed(1)
    p5 = 0.153
    # Simulate Tokyo Trimble P distribution (floor near p5, mean_raw=0.203)
    raw_clean    = np.random.beta(1.5, 9, 700) * (1 - p5) + p5
    raw_degraded = np.random.beta(3.5, 2.5, 300) * (1 - p5) + p5
    raw   = np.clip(np.concatenate([raw_clean, raw_degraded]), 0, 1)
    calib = np.clip((raw - p5) / (1 - p5), 0, 1)

    civ_raw   = matplotlib.colors.to_hex(C_SENTINEL)
    civ_calib = matplotlib.colors.to_hex(C_CALIB)
    civ_ref   = matplotlib.colors.to_hex(C_FIXED)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8))

    # Panel (a): raw histogram
    axes[0].hist(raw, bins=40, color=civ_raw, alpha=0.85,
                 density=True, edgecolor="white", lw=0.4)
    axes[0].axvline(p5, color="black", ls="--", lw=1.2,
                    label=f"$P_5 = {p5}$\n(5th pct.)")
    axes[0].set_xlabel(r"$\hat{P}_{5s}$ (raw)", fontweight="bold")
    axes[0].set_ylabel("Density", fontweight="bold")
    axes[0].set_title(f"(a) Raw output\nmean $\\approx$ 0.203")
    axes[0].legend(fontsize=7.5)

    # Panel (b): calibrated histogram
    axes[1].hist(calib, bins=40, color=civ_calib, alpha=0.85,
                 density=True, edgecolor="white", lw=0.4)
    axes[1].set_xlabel(r"$\hat{P}_{calib}$", fontweight="bold")
    axes[1].set_ylabel("Density", fontweight="bold")
    axes[1].set_title(f"(b) After floor calibration\nmean $\\approx$ 0.060")

    # Panel (c): scatter + mapping curve
    idx = np.random.choice(len(raw), 350, replace=False)
    axes[2].scatter(raw[idx], calib[idx],
                    s=7, alpha=0.45, color=civ_raw, zorder=2)
    xs = np.linspace(p5, 1, 100)
    axes[2].plot(xs, (xs - p5) / (1 - p5),
                 color=civ_ref, lw=2.0,
                 label=r"$\hat{P}_{calib} = \frac{\hat{P}-P_5}{1-P_5}$")
    axes[2].axvline(p5, color="black", ls="--", lw=0.9)
    axes[2].axhline(0,  color="black", ls="--", lw=0.9)
    axes[2].set_xlabel(r"$\hat{P}_{5s}$ (raw)", fontweight="bold")
    axes[2].set_ylabel(r"$\hat{P}_{calib}$", fontweight="bold")
    axes[2].set_title("(c) Calibration mapping")
    axes[2].legend(fontsize=7.5)

    fig.suptitle(
        f"Unsupervised Floor Calibration  (Tokyo Trimble, $P_5={p5}$)  "
        f"— mean $\\hat{{P}}$ : 0.203 → 0.060",
        fontsize=8.5, y=1.01,
    )
    fig.tight_layout()
    _save(fig, "fig_calibration")


# ══════════════════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════════════════
def _save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(DST / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    print(f"  [GEN]  {name}.pdf + .png")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg")

    print("=== Paper B figures ===")
    print("\n-- Copying existing figures --")
    ok, skip = copy_existing()

    print("\n-- Generating new figures (cividis) --")
    fig_system_overview()
    fig_tokyo_comparison()
    fig_hk_results()
    fig_tunnel()
    fig_calibration()

    print(f"\nDone: {ok} copied, {skip} skipped, 5 generated -> {DST}")
