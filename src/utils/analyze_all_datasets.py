"""
SENTINEL-GNSS — Dataset Signal Quality Analyser
================================================
Generates diagnostic plots for EVERY processed dataset using the already-computed
feature CSVs.  Mirrors the 4-panel layout of analyze_collected_data.py (which
works from raw RINEX for scenarios) so results are directly comparable.

Panels per dataset/source:
  1. Mean C/N₀ over time — with CLEAN/WARNING/DEGRADED threshold lines and
     background shading coloured by the assigned label.
  2. Satellite count + HDOP over time — dual-axis; right axis = HDOP.
  3. DOP (PDOP, HDOP) over time with degradation threshold lines.
  4. Label distribution bar chart + summary statistics text box.

Outputs:
  results/dataset_analysis/<dataset>/<source>_ANALYSIS.png  ← per source
  results/dataset_analysis/ALL_DATASETS_COMPARISON.png      ← combined overview
  results/dataset_analysis/LABEL_DISTRIBUTION_HEATMAP.png  ← label heatmap

Usage:
  python src/utils/analyze_all_datasets.py                  # all datasets
  python src/utils/analyze_all_datasets.py --dataset urbannav
  python src/utils/analyze_all_datasets.py --dataset supervisor
  python src/utils/analyze_all_datasets.py --dataset tunnel
  python src/utils/analyze_all_datasets.py --dataset tokyo
  python src/utils/analyze_all_datasets.py --dataset nclt
  python src/utils/analyze_all_datasets.py --dataset oxford
  python src/utils/analyze_all_datasets.py --dataset scenarios

References:
  - Signal quality thresholds: IS-GPS-200 (2022), RTCM SC-104 (2021)
  - GNSS performance metrics: Kaplan & Hegarty (2017), "Understanding GPS/GNSS"
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR     = PROJECT_ROOT / "data" / "processed"
OUT_ROOT     = PROJECT_ROOT / "results" / "dataset_analysis"

# ─── Colour + label mapping ──────────────────────────────────────────────────
LABEL_COLORS = {0: "#4CAF50", 1: "#FF9800", 2: "#F44336"}   # CLEAN / WARN / DEG
LABEL_NAMES  = {0: "CLEAN", 1: "WARNING", 2: "DEGRADED"}

# C/N₀ threshold lines (dBHz) from IS-GPS-200 / RTCM SC-104
CNR_CLEAN    = 35.0
CNR_WARN     = 30.0
CNR_DEGRAD   = 25.0

# DOP thresholds from GNSS literature
HDOP_WARN    = 2.5
HDOP_DEGRAD  = 5.0
PDOP_WARN    = 4.0
PDOP_DEGRAD  = 8.0

# ─── Dataset sources configuration ───────────────────────────────────────────
# Each entry: (csv_path, dataset_label, groupby_col)
#   groupby_col = column used to split into per-source subplots.
DATASETS: dict[str, dict] = {
    "scenarios": {
        "csv":   DATA_DIR / "scenarios" / "all_scenarios_features.csv",
        "label": "Field Collection — Scenarios A–E (Beijing Campus)",
        "group": "scenario",
        "description": "Self-collected data with Septentrio MOSAIC-X5C. "
                        "Five controlled degradation environments.",
    },
    "supervisor": {
        "csv":   DATA_DIR / "supervisor" / "vehicle" / "supervisor_vehicle_features.csv",
        "label": "Supervisor Vehicle (Beijing)",
        "group": "source",
        "description": "Septentrio MOSAIC-X5C vehicle surveys in Beijing urban/suburban areas.",
    },
    "drone": {
        "csv":   DATA_DIR / "supervisor" / "drone" / "supervisor_drone_features.csv",
        "label": "Supervisor Drone (Beijing) — EXCLUDED from training",
        "group": "source",
        "description": "Unicore UB4B0 on aerial UAV. Open-sky only (100% CLEAN). "
                        "Excluded via DEFAULT_EXCLUDE_SOURCES — no degradation signal.",
    },
    "urbannav": {
        "csv":   DATA_DIR / "urbannav" / "urbannav_hk_features.csv",
        "label": "UrbanNav HK-Medium-Urban-1 (Mong Kok / Sham Shui Po, 2021)",
        "group": "source",
        "description": "10 simultaneous receivers, same vehicle. "
                        "Moderate urban canyon. Reference: Hsu et al. (2023) NAVIGATION.",
    },
    "tunnel": {
        "csv":   DATA_DIR / "urbannav" / "urbannav_tunnel_features.csv",
        "label": "UrbanNav HK-Tunnel-1 (Cross-Harbour Tunnel, 2021)",
        "group": "source",
        "description": "10 receivers through Cross-Harbour Tunnel. "
                        "Complete signal loss inside. Mirrors campus Scenario A/E.",
    },
    "tokyo": {
        "csv":   [DATA_DIR / "tokyo" / "tokyo_odaiba_features.csv",
                  DATA_DIR / "tokyo" / "tokyo_shinjuku_features.csv"],
        "label": "Tokyo Odaiba + Shinjuku (2021)",
        "group": "source",
        "description": "Trimble survey-grade + u-blox F9P. "
                        "Odaiba: waterfront mixed. Shinjuku: dense urban canyon.",
    },
    "nclt": {
        "csv":   DATA_DIR / "nclt" / "nclt_features.csv",
        "label": "NCLT Ann Arbor (Michigan, 2012–2013) — EXCLUDED from training",
        "group": "source",
        "description": "Ground robot, campus + urban routes. GPS-only (no C/N₀). "
                        "Satellite count logging bug → excluded from training.",
    },
    "oxford": {
        "csv":   DATA_DIR / "oxford" / "oxford_features.csv",
        "label": "Oxford RobotCar (UK, 2014–2015) — EXCLUDED from training",
        "group": "source",
        "description": "NovAtel OEM6 GPS-only (2014 era). "
                        "Labels from position-sigma, not C/N₀ → excluded.",
    },
}


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_dataset(key: str) -> Optional[pd.DataFrame]:
    """Load a processed features CSV (or list of CSVs for Tokyo)."""
    cfg = DATASETS[key]
    csv = cfg["csv"]

    if isinstance(csv, list):
        dfs = []
        for p in csv:
            if p.exists():
                dfs.append(pd.read_csv(p, low_memory=False))
                log.info(f"  Loaded {len(dfs[-1]):,} rows from {p.name}")
            else:
                log.warning(f"  Not found: {p}")
        if not dfs:
            return None
        return pd.concat(dfs, ignore_index=True)
    else:
        if not csv.exists():
            log.warning(f"  Not found: {csv}")
            return None
        df = pd.read_csv(csv, low_memory=False)
        log.info(f"  Loaded {len(df):,} rows from {csv.name}")
        return df


def _ensure_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure timestamp column is datetime; compute t_sec relative to session start.

    Uses transform() instead of groupby().apply() to avoid the pandas 2.2+
    behaviour where the group-key column is dropped from the result when
    include_groups defaults to False.
    """
    df = df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        # t_sec = seconds since start of each source session
        if "source" in df.columns:
            # transform preserves the DataFrame shape and never drops 'source'
            df["t_sec"] = df.groupby("source")["timestamp"].transform(
                lambda x: (x - x.min()).dt.total_seconds()
            )
        else:
            t0 = df["timestamp"].min()
            df["t_sec"] = (df["timestamp"] - t0).dt.total_seconds()
    else:
        df["t_sec"] = np.arange(len(df))
    return df


# ─── Single-source plot ───────────────────────────────────────────────────────

def make_source_chart(
    source_key: str,
    source_label: str,
    df: pd.DataFrame,
    out_dir: Path,
    dataset_description: str = "",
) -> dict:
    """
    4-panel diagnostic chart for one source/session from processed CSV.

    Returns a summary dict for the ALL_DATASETS_COMPARISON chart.
    """
    if df.empty:
        return {}

    df = df.copy()
    if "t_sec" not in df.columns:
        df = _ensure_timestamp(df)

    # Sort by time
    if "t_sec" in df.columns:
        df = df.sort_values("t_sec").reset_index(drop=True)

    duration_s = df["t_sec"].max() if "t_sec" in df.columns else len(df)
    n_epochs   = len(df)

    # ── label counts ──────────────────────────────────────────────────────
    label_counts = df["label"].value_counts().sort_index() if "label" in df.columns else {}
    total = len(df)
    clean_pct   = 100 * label_counts.get(0, 0) / max(total, 1)
    warn_pct    = 100 * label_counts.get(1, 0) / max(total, 1)
    degrad_pct  = 100 * label_counts.get(2, 0) / max(total, 1)

    # ── mean_cnr ──────────────────────────────────────────────────────────
    has_cnr = "mean_cnr" in df.columns and df["mean_cnr"].notna().any()
    cnr_global_mean = float(df["mean_cnr"].mean()) if has_cnr else float("nan")

    # ── fig setup ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(
        f"{source_label}\n{dataset_description}",
        fontsize=12, fontweight="bold", y=0.99
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    t = df["t_sec"].values if "t_sec" in df.columns else np.arange(len(df))

    # ── Panel 1: Mean C/N₀ over time ──────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    if has_cnr:
        cnr = df["mean_cnr"].values

        # Background shading by label
        if "label" in df.columns:
            labels = df["label"].values
            for i in range(len(t) - 1):
                lbl = int(labels[i]) if not np.isnan(labels[i]) else 0
                ax1.axvspan(t[i], t[i + 1],
                            color=LABEL_COLORS.get(lbl, "#888888"),
                            alpha=0.08, linewidth=0)

        ax1.plot(t, cnr, color="#1565C0", linewidth=1.2, alpha=0.9, label="Mean C/N₀")

        # Fill between min and max if available
        if "min_cnr" in df.columns and "max_cnr" in df.columns:
            ax1.fill_between(t, df["min_cnr"].values, df["max_cnr"].values,
                             alpha=0.12, color="#607D8B", label="Min–Max range")

        ax1.axhline(CNR_CLEAN,  color="#4CAF50", linestyle="--", linewidth=0.8,
                    label=f"CLEAN ≥{CNR_CLEAN:.0f} dBHz")
        ax1.axhline(CNR_WARN,   color="#FF9800", linestyle="--", linewidth=0.8,
                    label=f"WARN ≥{CNR_WARN:.0f} dBHz")
        ax1.axhline(CNR_DEGRAD, color="#F44336", linestyle="--", linewidth=0.8,
                    label=f"DEGRAD <{CNR_DEGRAD:.0f} dBHz")
        ax1.set_ylim(0, 55)
    else:
        ax1.text(0.5, 0.5, "C/N₀ not available\n(no RINEX S1C data)",
                 ha="center", va="center", transform=ax1.transAxes,
                 fontsize=10, color="#888888")

    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Mean C/N₀ (dBHz)")
    ax1.set_title("Signal Strength (Mean C/N₀)")
    ax1.legend(fontsize=7, loc="lower right", ncol=2)
    ax1.set_xlim(0, max(duration_s, 1))
    ax1.grid(True, alpha=0.25)

    # ── Panel 2: Satellite count + HDOP ───────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    has_sats = "num_satellites" in df.columns and df["num_satellites"].notna().any()
    has_hdop = "hdop" in df.columns and df["hdop"].notna().any()

    if has_sats:
        sats = df["num_satellites"].values
        ax2.fill_between(t, 0, sats, alpha=0.3, color="#1976D2")
        ax2.plot(t, sats, color="#1565C0", linewidth=1.2, label="Satellites tracked")
        ax2.axhline(8, color="#4CAF50", linestyle="--", linewidth=0.7,
                    label="CLEAN ≥8 sats")
        ax2.axhline(4, color="#F44336", linestyle="--", linewidth=0.7,
                    label="DEGRAD <4 sats")
        ax2.set_ylabel("Satellites tracked", color="#1565C0")
        ax2.tick_params(axis="y", labelcolor="#1565C0")
        ax2.set_ylim(0, max(df["num_satellites"].max() * 1.2, 12))

    if has_hdop:
        ax2b = ax2.twinx()
        ax2b.plot(t, df["hdop"].values, color="#E91E63", linewidth=1.2,
                  alpha=0.7, label="HDOP")
        ax2b.axhline(HDOP_WARN,   color="#FF9800", linestyle=":", linewidth=0.7)
        ax2b.axhline(HDOP_DEGRAD, color="#F44336", linestyle=":", linewidth=0.7)
        ax2b.set_ylabel("HDOP", color="#E91E63")
        ax2b.tick_params(axis="y", labelcolor="#E91E63")
        ax2b.set_ylim(0, 12)

    if not has_sats and not has_hdop:
        ax2.text(0.5, 0.5, "Satellite count / HDOP\nnot available",
                 ha="center", va="center", transform=ax2.transAxes,
                 fontsize=10, color="#888888")

    ax2.set_xlabel("Time (s)")
    ax2.set_title("Satellite Count & HDOP")
    ax2.set_xlim(0, max(duration_s, 1))
    ax2.grid(True, alpha=0.25)
    lines1, labels1 = ax2.get_legend_handles_labels()
    ax2.legend(lines1, labels1, fontsize=7, loc="upper right")

    # ── Panel 3: PDOP + HDOP together ─────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    has_pdop = "pdop" in df.columns and df["pdop"].notna().any()

    if has_pdop:
        ax3.plot(t, df["pdop"].values, color="#7B1FA2", linewidth=1.2,
                 label="PDOP", alpha=0.85)
        ax3.axhline(PDOP_WARN,   color="#FF9800", linestyle="--", linewidth=0.8,
                    label=f"WARN PDOP={PDOP_WARN}")
        ax3.axhline(PDOP_DEGRAD, color="#F44336", linestyle="--", linewidth=0.8,
                    label=f"DEGRAD PDOP={PDOP_DEGRAD}")
    if has_hdop:
        ax3.plot(t, df["hdop"].values, color="#E91E63", linewidth=1.2,
                 linestyle="-.", label="HDOP", alpha=0.85)
        ax3.axhline(HDOP_DEGRAD, color="#E91E63", linestyle=":", linewidth=0.6)

    if not has_pdop and not has_hdop:
        ax3.text(0.5, 0.5, "DOP not available\n(no NMEA GSA data)",
                 ha="center", va="center", transform=ax3.transAxes,
                 fontsize=10, color="#888888")
    else:
        ax3.set_ylim(0, 15)
        ax3.legend(fontsize=7)

    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("DOP value")
    ax3.set_title("Dilution of Precision (DOP)")
    ax3.set_xlim(0, max(duration_s, 1))
    ax3.grid(True, alpha=0.25)

    # ── Panel 4: Label distribution + summary stats ────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")

    if "label" in df.columns:
        # Mini bar chart inset
        ax4_bar = ax4.inset_axes([0.0, 0.55, 0.95, 0.42])
        bars_x = [0, 1, 2]
        bars_h = [clean_pct, warn_pct, degrad_pct]
        bars_c = ["#4CAF50", "#FF9800", "#F44336"]
        bars_n = ["CLEAN", "WARNING", "DEGRADED"]
        bars = ax4_bar.bar(bars_x, bars_h, color=bars_c, width=0.6, alpha=0.85)
        for bar, pct, cnt_key in zip(bars, bars_h, [0, 1, 2]):
            cnt = label_counts.get(cnt_key, 0)
            ax4_bar.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 0.5,
                         f"{pct:.1f}%\n({cnt:,})", ha="center",
                         va="bottom", fontsize=8)
        ax4_bar.set_xticks(bars_x)
        ax4_bar.set_xticklabels(bars_n, fontsize=8)
        ax4_bar.set_ylabel("% of epochs", fontsize=8)
        ax4_bar.set_ylim(0, max(bars_h) * 1.35 + 2)
        ax4_bar.set_title("Label Distribution", fontsize=9, fontweight="bold")
        ax4_bar.grid(True, alpha=0.25, axis="y")

    # Summary text
    solution_ok = float("nan")
    if "solution_status" in df.columns:
        sol = df["solution_status"]
        solution_ok = 100.0 * (sol > 0).sum() / max(len(sol), 1)

    summary = [
        f"Rows / epochs:  {n_epochs:,}",
        f"Duration:       {duration_s/60:.1f} min  ({duration_s:.0f} s)",
        f"",
        f"Mean C/N₀:      {cnr_global_mean:.1f} dBHz" if not np.isnan(cnr_global_mean) else "Mean C/N₀:      N/A",
        f"Sats (mean):    {df['num_satellites'].mean():.1f}" if has_sats else "Sats (mean):    N/A",
        f"HDOP (mean):    {df['hdop'].mean():.2f}" if has_hdop else "HDOP (mean):    N/A",
        f"PDOP (mean):    {df['pdop'].mean():.2f}" if has_pdop else "PDOP (mean):    N/A",
        f"Fix rate:       {solution_ok:.1f}%" if not np.isnan(solution_ok) else "Fix rate:       N/A",
        f"",
        f"CLEAN:          {clean_pct:.1f}%  ({label_counts.get(0, 0):,})",
        f"WARNING:        {warn_pct:.1f}%  ({label_counts.get(1, 0):,})",
        f"DEGRADED:       {degrad_pct:.1f}%  ({label_counts.get(2, 0):,})",
    ]

    ax4.text(0.02, 0.50, "\n".join(summary),
             transform=ax4.transAxes,
             fontsize=9, verticalalignment="top",
             fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5",
                       edgecolor="#BDBDBD", alpha=0.9))

    out_dir.mkdir(parents=True, exist_ok=True)
    safe_key = source_key.replace("/", "_").replace(" ", "_")
    fname = out_dir / f"{safe_key}_ANALYSIS.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"  Saved: {fname}")

    return {
        "source":     source_key,
        "label":      source_label,
        "n_rows":     n_epochs,
        "duration_s": duration_s,
        "mean_cnr":   cnr_global_mean,
        "clean_pct":  clean_pct,
        "warn_pct":   warn_pct,
        "degrad_pct": degrad_pct,
        "mean_sats":  float(df["num_satellites"].mean()) if has_sats else float("nan"),
        "mean_hdop":  float(df["hdop"].mean()) if has_hdop else float("nan"),
        "mean_pdop":  float(df["pdop"].mean()) if has_pdop else float("nan"),
    }


# ─── Overall comparison chart ─────────────────────────────────────────────────

def make_comparison_chart(summaries: list[dict], out_dir: Path) -> None:
    """
    Multi-panel comparison chart across ALL datasets / sources.

    Panel 1: Stacked bar chart of CLEAN / WARNING / DEGRADED % per source
    Panel 2: Mean C/N₀ per source (with error bars = std if available)
    Panel 3: Mean satellite count per source
    Panel 4: Mean HDOP per source
    """
    if not summaries:
        return

    summaries = [s for s in summaries if s]   # drop empty dicts

    # Sort by degrad_pct descending so most challenged sources appear first
    summaries.sort(key=lambda s: s.get("degrad_pct", 0), reverse=True)

    labels    = [s["source"] for s in summaries]
    clean_pcts = [s.get("clean_pct", 0) for s in summaries]
    warn_pcts  = [s.get("warn_pct", 0) for s in summaries]
    degrad_pcts = [s.get("degrad_pct", 0) for s in summaries]
    mean_cnrs   = [s.get("mean_cnr", float("nan")) for s in summaries]
    mean_sats   = [s.get("mean_sats", float("nan")) for s in summaries]
    mean_hdops  = [s.get("mean_hdop", float("nan")) for s in summaries]

    n = len(labels)
    x = np.arange(n)
    max_label_len = max(len(l) for l in labels)
    fig_width = max(14, n * 0.55 + 2)

    fig, axes = plt.subplots(2, 2, figsize=(fig_width, 10))
    fig.suptitle("SENTINEL-GNSS: All Datasets Signal Quality Comparison",
                 fontsize=13, fontweight="bold", y=1.01)

    # ── Panel 1: Stacked label distribution ──────────────────────────────
    ax = axes[0, 0]
    bar_width = 0.6
    ax.bar(x, clean_pcts,  bar_width, label="CLEAN",    color="#4CAF50", alpha=0.85)
    ax.bar(x, warn_pcts,   bar_width, label="WARNING",  color="#FF9800", alpha=0.85,
           bottom=clean_pcts)
    ax.bar(x, degrad_pcts, bar_width, label="DEGRADED", color="#F44336", alpha=0.85,
           bottom=[c + w for c, w in zip(clean_pcts, warn_pcts)])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
    ax.set_ylabel("Percentage of epochs")
    ax.set_ylim(0, 110)
    ax.set_title("Label Distribution per Source")
    ax.legend(loc="upper right", fontsize=8)
    ax.axhline(100, color="#888", linewidth=0.5)
    ax.grid(True, alpha=0.25, axis="y")

    # ── Panel 2: Mean C/N₀ ────────────────────────────────────────────────
    ax = axes[0, 1]
    has_cnr = [not np.isnan(c) for c in mean_cnrs]
    x_valid  = x[has_cnr]
    cnr_valid = [c for c, h in zip(mean_cnrs, has_cnr) if h]
    bars = ax.bar(x_valid, cnr_valid, bar_width,
                  color=["#4CAF50" if c >= 35 else ("#FF9800" if c >= 30 else "#F44336")
                         for c in cnr_valid],
                  alpha=0.85)
    ax.axhline(CNR_CLEAN,  color="#4CAF50", linestyle="--", linewidth=0.8,
               label=f"CLEAN ≥{CNR_CLEAN:.0f}")
    ax.axhline(CNR_WARN,   color="#FF9800", linestyle="--", linewidth=0.8,
               label=f"WARN ≥{CNR_WARN:.0f}")
    ax.axhline(CNR_DEGRAD, color="#F44336", linestyle="--", linewidth=0.8,
               label=f"DEGRAD <{CNR_DEGRAD:.0f}")
    if not has_cnr or not x_valid.size:
        ax.text(0.5, 0.5, "No C/N₀ data", ha="center", va="center",
                transform=ax.transAxes, color="#888")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
    ax.set_ylabel("Mean C/N₀ (dBHz)")
    ax.set_ylim(0, 55)
    ax.set_title("Mean C/N₀ per Source")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.25, axis="y")

    # Add "N/A" labels for missing
    for i, h in enumerate(has_cnr):
        if not h:
            ax.text(i, 2, "N/A", ha="center", va="bottom", fontsize=7, color="#888")

    # ── Panel 3: Mean satellite count ─────────────────────────────────────
    ax = axes[1, 0]
    has_sats = [not np.isnan(s) for s in mean_sats]
    x_valid  = x[has_sats]
    sats_valid = [s for s, h in zip(mean_sats, has_sats) if h]
    ax.bar(x_valid, sats_valid, bar_width,
           color=["#4CAF50" if s >= 8 else ("#FF9800" if s >= 4 else "#F44336")
                  for s in sats_valid],
           alpha=0.85)
    ax.axhline(8, color="#4CAF50", linestyle="--", linewidth=0.8, label="CLEAN ≥8")
    ax.axhline(4, color="#F44336", linestyle="--", linewidth=0.8, label="DEGRAD <4")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
    ax.set_ylabel("Mean satellites tracked")
    ax.set_title("Mean Satellite Count per Source")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.25, axis="y")
    for i, h in enumerate(has_sats):
        if not h:
            ax.text(i, 0.2, "N/A", ha="center", va="bottom", fontsize=7, color="#888")

    # ── Panel 4: Mean HDOP ────────────────────────────────────────────────
    ax = axes[1, 1]
    has_hdop = [not np.isnan(h) for h in mean_hdops]
    x_valid  = x[has_hdop]
    hdop_valid = [h for h, hv in zip(mean_hdops, has_hdop) if hv]
    ax.bar(x_valid, hdop_valid, bar_width,
           color=["#4CAF50" if h <= 2.5 else ("#FF9800" if h <= 5 else "#F44336")
                  for h in hdop_valid],
           alpha=0.85)
    ax.axhline(HDOP_WARN,   color="#FF9800", linestyle="--", linewidth=0.8,
               label=f"WARN HDOP>{HDOP_WARN}")
    ax.axhline(HDOP_DEGRAD, color="#F44336", linestyle="--", linewidth=0.8,
               label=f"DEGRAD HDOP>{HDOP_DEGRAD}")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
    ax.set_ylabel("Mean HDOP")
    ax.set_title("Mean HDOP per Source")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.25, axis="y")
    for i, h in enumerate(has_hdop):
        if not h:
            ax.text(i, 0.05, "N/A", ha="center", va="bottom", fontsize=7, color="#888")

    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / "ALL_DATASETS_COMPARISON.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved comparison chart: {fname}")


# ─── Label distribution heatmap ───────────────────────────────────────────────

def make_label_heatmap(summaries: list[dict], out_dir: Path) -> None:
    """Heatmap: each row = one source, columns = CLEAN / WARNING / DEGRADED %."""
    summaries = [s for s in summaries if s]
    if not summaries:
        return

    summaries.sort(key=lambda s: s.get("degrad_pct", 0), reverse=True)
    labels = [s["source"] for s in summaries]
    data   = np.array([[s.get("clean_pct", 0), s.get("warn_pct", 0), s.get("degrad_pct", 0)]
                        for s in summaries])

    fig_h = max(6, len(labels) * 0.45 + 2)
    fig, ax = plt.subplots(figsize=(9, fig_h))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r",
                   vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, label="% of epochs")

    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["CLEAN", "WARNING", "DEGRADED"], fontsize=10)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)

    for i in range(len(labels)):
        for j, val in enumerate(data[i]):
            text_color = "white" if (j == 2 and val > 30) or (j == 0 and val < 30) else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=8, color=text_color, fontweight="bold")

    ax.set_title("Label Distribution Heatmap — All Sources\n"
                 "(sorted by DEGRADED % descending)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    fname = out_dir / "LABEL_DISTRIBUTION_HEATMAP.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved label heatmap: {fname}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_dataset(key: str) -> list[dict]:
    """Process and plot one dataset key. Returns list of per-source summary dicts."""
    cfg = DATASETS[key]
    log.info(f"\n{'='*65}")
    log.info(f"Processing: {cfg['label']}")
    log.info(f"{'='*65}")

    df = load_dataset(key)
    if df is None or df.empty:
        log.warning(f"  No data for dataset '{key}'")
        return []

    df = _ensure_timestamp(df)
    out_dir = OUT_ROOT / key

    group_col = cfg.get("group", "source")
    summaries = []

    if group_col not in df.columns:
        # Single group
        log.info(f"  No '{group_col}' column — treating as single source")
        summary = make_source_chart(
            source_key=key,
            source_label=cfg["label"],
            df=df,
            out_dir=out_dir,
            dataset_description=cfg.get("description", ""),
        )
        summaries.append(summary)
    else:
        sources = sorted(df[group_col].dropna().unique())
        log.info(f"  {len(sources)} sources: {sources}")
        for src in sources:
            src_df = df[df[group_col] == src].copy()
            summary = make_source_chart(
                source_key=str(src),
                source_label=f"{cfg['label']}\n[{src}]",
                df=src_df,
                out_dir=out_dir,
                dataset_description=cfg.get("description", ""),
            )
            summaries.append(summary)

        # Within-dataset comparison chart
        if len(summaries) > 1:
            make_comparison_chart(summaries, out_dir)

    return summaries


def main():
    parser = argparse.ArgumentParser(
        description="SENTINEL-GNSS: Generate diagnostic plots for all processed datasets"
    )
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()) + ["all"],
        default="all",
        help="Which dataset to analyse (default: all)",
    )
    args = parser.parse_args()

    if args.dataset == "all":
        keys = list(DATASETS.keys())
    else:
        keys = [args.dataset]

    all_summaries = []
    for key in keys:
        sums = run_dataset(key)
        all_summaries.extend(sums)

    if len(keys) > 1 and all_summaries:
        log.info("\n" + "=" * 65)
        log.info("Generating combined ALL_DATASETS_COMPARISON chart …")
        make_comparison_chart(all_summaries, OUT_ROOT)
        make_label_heatmap(all_summaries, OUT_ROOT)

    log.info(f"\nAll figures saved to: {OUT_ROOT}")
    log.info("Done.")


if __name__ == "__main__":
    main()
