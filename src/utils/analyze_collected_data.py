"""
Collected Scenario Data Analyser
=================================
Parses RINEX 3 observation files (.26O) produced by the Septentrio MOSAIC-X5C
receiver and generates diagnostic charts for each scenario.

Outputs per scenario:
  1. Satellite count vs time  (all constellations stacked)
  2. C/N0 per constellation vs time
  3. Observation availability heatmap (satellite × epoch)
  4. Summary table

Comparison output:
  5. Side-by-side C/N0 comparison across all scenarios

Usage:
    python src/utils/analyze_collected_data.py
    python src/utils/analyze_collected_data.py --scenario A
    python src/utils/analyze_collected_data.py --all
"""

from matplotlib.cm import get_cmap
from matplotlib.colors import BoundaryNorm
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = PROJECT_ROOT / "data" / "raw" / "scenarios"
OUTPUT_DIR = PROJECT_ROOT / "results" / "scenario_analysis"

SCENARIO_LABELS = {
    "A": "Instant Blockage",
    "B": "Urban Canyon",
    "C": "Partial Blockage (Trees)",
    "D": "Open Sky",
    "E": "Approaching Blockage",
}

# Map RINEX constellation prefix → display name and colour
CONST_INFO = {
    "G": ("GPS",     "#2196F3"),
    "E": ("Galileo", "#4CAF50"),
    "R": ("GLONASS", "#FF9800"),
    "C": ("BeiDou",  "#9C27B0"),
}


# RINEX 3 SNR indicator → approximate C/N0 midpoint (dB-Hz)
# Standard: 0=unknown, 1=<12, 2=12-17, 3=18-23, 4=24-29, 5=30-35,
#            6=36-41, 7=42-47, 8=48-53, 9=>=54
SNR_TO_CNR = {
    0: np.nan, 1: 10.0, 2: 14.5, 3: 20.5, 4: 26.5,
    5: 32.5,   6: 38.5, 7: 44.5, 8: 50.5, 9: 56.0,
}


def parse_rinex_obs(obs_file: Path) -> pd.DataFrame:
    """
    Parse a RINEX 3 observation file.
    Returns a DataFrame with one row per (epoch × satellite), columns:
        epoch_utc, satellite, constellation, cnr (approx C/N0 dB-Hz)

    Note: Septentrio MOSAIC-X5C exports C/L observations only (no S-type).
    Signal quality is extracted from the 1-char SNR indicator embedded in
    each observation slot (position 15 of each 16-char block, digit 0-9)
    and converted to approximate C/N0 via the RINEX 3 standard mapping.
    """
    records = []
    in_header = True
    obs_types: dict[str, list[str]] = {}
    current_epoch = None

    with open(obs_file, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")

            # ── header ────────────────────────────────────────────────────────
            if in_header:
                if "SYS / # / OBS TYPES" in line:
                    sys = line[0]
                    if sys in CONST_INFO:
                        parts = line[:60].split()
                        obs_types[sys] = parts[2:]
                if "END OF HEADER" in line:
                    in_header = False
                continue

            # ── epoch record header ">" ────────────────────────────────────
            if line.startswith(">"):
                parts = line.split()
                try:
                    yr, mo, dy = int(parts[1]), int(parts[2]), int(parts[3])
                    hr, mi = int(parts[4]), int(parts[5])
                    sec = float(parts[6])
                    current_epoch = datetime(yr, mo, dy, hr, mi, int(sec),
                                             int((sec % 1) * 1e6),
                                             tzinfo=timezone.utc)
                except (ValueError, IndexError):
                    current_epoch = None
                continue

            if current_epoch is None or len(line) < 3:
                continue

            sys = line[0]
            if sys not in CONST_INFO:
                continue

            prn = line[:3].strip()
            types = obs_types.get(sys, [])
            if not types:
                continue

            # Each obs = 14 chars value + 1 char LLI + 1 char SNR indicator = 16 chars
            data_str = line[3:]
            num_obs = len(types)

            # Extract SNR indicator from first L-type (carrier-phase) obs;
            # fall back to any obs with non-zero SNR.
            snr_indicator = 0
            for i in range(num_obs):
                chunk = data_str[i * 16: i * 16 + 16]
                if len(chunk) < 16:
                    continue
                if types[i].startswith("L"):
                    try:
                        v = int(chunk[15])
                        if v > 0:
                            snr_indicator = v
                            break
                    except ValueError:
                        pass

            if snr_indicator == 0:
                for i in range(num_obs):
                    chunk = data_str[i * 16: i * 16 + 16]
                    if len(chunk) < 16:
                        continue
                    try:
                        v = int(chunk[15])
                        if v > 0:
                            snr_indicator = v
                            break
                    except ValueError:
                        pass

            cnr = SNR_TO_CNR.get(snr_indicator, np.nan)

            records.append({
                "epoch_utc": current_epoch,
                "satellite": prn,
                "constellation": sys,
                "cnr": cnr,
            })

    if not records:
        logger.warning(f"No records parsed from {obs_file}")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["epoch_utc"] = pd.to_datetime(df["epoch_utc"], utc=True)
    t0 = df["epoch_utc"].min()
    df["t_sec"] = (df["epoch_utc"] - t0).dt.total_seconds()
    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  FIND OBSERVATION FILES
# ═══════════════════════════════════════════════════════════════════════════════

def find_obs_files(scenario_id: str) -> list[tuple[str, Path]]:
    """
    Find all .26O RINEX observation files for a given scenario.
    Returns list of (run_label, obs_path).

    Folder conventions:
      - Normal scenarios:   data/raw/scenarios/scenario_X/X/          → Run_1
                            data/raw/scenarios/scenario_X/X/X2/       → X2
      - Scenario E only:    data/raw/scenarios/scenario_a_to_e/E2/    → E2
                            data/raw/scenarios/scenario_a_to_e/E3/    → E3
      - Combined A→E run:   data/raw/scenarios/scenario_a_to_e/       → A_to_E_Run
                            (shown only for scenario A to avoid duplication)
    """
    scen_id = scenario_id.upper()
    runs = []

    # ── Standard scenario folder ───────────────────────────────────────────
    base_dir = SCENARIOS_DIR / f"scenario_{scen_id.lower()}" / scen_id
    if base_dir.exists():
        for f in base_dir.glob("*.26O"):
            runs.append(("Run_1", f))
        for sub in sorted(base_dir.iterdir()):
            if sub.is_dir():
                for f in sub.glob("*.26O"):
                    runs.append((sub.name, f))

    # ── scenario_a_to_e — E sub-runs + root combined run ──────────────────
    mixed_dir = SCENARIOS_DIR / "scenario_a_to_e"
    if mixed_dir.exists():
        # E-specific sub-folders (E2, E3, …) → always included for E
        for sub in sorted(mixed_dir.iterdir()):
            if sub.is_dir() and sub.name.upper().startswith(scen_id):
                for f in sub.glob("*.26O"):
                    runs.append((sub.name, f))

        # Root combined file (full A→E drive) — only attach to scenario A
        # to avoid duplicating it across every scenario's charts
        if scen_id == "A":
            for f in mixed_dir.glob("*.26O"):
                runs.append(("A_to_E_Run", f))

    if not runs:
        logger.warning(
            f"No RINEX files found for scenario {scen_id}. "
            f"Expected in {SCENARIOS_DIR}/scenario_{scen_id.lower()}/{scen_id}/"
        )

    return runs


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART: INDIVIDUAL SCENARIO
# ═══════════════════════════════════════════════════════════════════════════════

def make_scenario_chart(scenario_id: str, run_label: str,
                        df: pd.DataFrame, out_dir: Path) -> dict:
    """
    Generate a 4-panel chart for one run of one scenario.
    Returns a summary dict for the comparison chart.
    """
    if df.empty:
        return {}

    label = SCENARIO_LABELS.get(scenario_id.upper(), scenario_id)
    title = f"Scenario {scenario_id.upper()} — {label}\n{run_label}"

    # ── per-epoch aggregations ─────────────────────────────────────────────
    epoch_cnr = (df.dropna(subset=["cnr"])
                   .groupby("t_sec")
                   .agg(mean_cnr=("cnr", "mean"),
                        min_cnr=("cnr", "min"),
                        max_cnr=("cnr", "max"),
                        sat_count=("satellite", "nunique"))
                   .reset_index())

    const_cnr = (df.dropna(subset=["cnr"])
                   .groupby(["t_sec", "constellation"])
                   .agg(mean_cnr=("cnr", "mean"))
                   .reset_index())

    sat_count_by_const = (df.groupby(["t_sec", "constellation"])
                            .agg(count=("satellite", "nunique"))
                            .reset_index())

    duration_s = df["t_sec"].max()
    total_epochs = df["t_sec"].nunique()

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.98)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.32)

    # ── Panel 1: Satellite count per constellation ────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    t_vals = sorted(sat_count_by_const["t_sec"].unique())
    bottom = np.zeros(len(t_vals))
    for sys, (name, color) in CONST_INFO.items():
        sub = sat_count_by_const[sat_count_by_const["constellation"] == sys]
        count_series = sub.set_index("t_sec")["count"].reindex(
            t_vals, fill_value=0).values.astype(float)
        ax1.bar(t_vals, count_series, bottom=bottom,
                label=name, color=color, width=1.0, alpha=0.85)
        bottom += count_series
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Satellites tracked")
    ax1.set_title("Satellite Count by Constellation")
    ax1.legend(fontsize=7, ncol=2)
    ax1.set_xlim(0, duration_s)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: Mean C/N0 per constellation ─────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    for sys, (name, color) in CONST_INFO.items():
        sub = const_cnr[const_cnr["constellation"] == sys]
        if not sub.empty:
            ax2.plot(sub["t_sec"], sub["mean_cnr"], label=name,
                     color=color, linewidth=1.5, alpha=0.9)
    ax2.axhline(35, color="#2196F3", linestyle="--",
                linewidth=0.8, label="Good (35 dB-Hz)")
    ax2.axhline(30, color="#FF9800", linestyle="--",
                linewidth=0.8, label="Warn (30 dB-Hz)")
    ax2.axhline(25, color="#F44336", linestyle="--",
                linewidth=0.8, label="Degrad (25 dB-Hz)")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Mean C/N0 (dB-Hz)")
    ax2.set_title("C/N0 by Constellation")
    ax2.legend(fontsize=7, ncol=2)
    ax2.set_xlim(0, duration_s)
    ax2.set_ylim(0, 55)
    ax2.grid(True, alpha=0.3)

    # ── Panel 3: Overall mean C/N0 with shaded range ──────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    if not epoch_cnr.empty:
        ax3.fill_between(epoch_cnr["t_sec"],
                         epoch_cnr["min_cnr"], epoch_cnr["max_cnr"],
                         alpha=0.2, color="#607D8B", label="Min–Max range")
        ax3.plot(epoch_cnr["t_sec"], epoch_cnr["mean_cnr"],
                 color="#1976D2", linewidth=2, label="Mean C/N0")
        ax3.axhline(35, color="#2196F3", linestyle="--", linewidth=0.8)
        ax3.axhline(25, color="#F44336", linestyle="--", linewidth=0.8)
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("C/N0 (dB-Hz)")
        ax3.set_title("Overall Signal Strength (All Constellations)")
        ax3.legend(fontsize=8)
        ax3.set_xlim(0, duration_s)
        ax3.set_ylim(0, 55)
        ax3.grid(True, alpha=0.3)

    # ── Panel 4: Summary stats text box ──────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    all_cnr = df["cnr"].dropna()
    below_30 = (all_cnr < 30).sum() / max(len(all_cnr), 1) * 100
    below_25 = (all_cnr < 25).sum() / max(len(all_cnr), 1) * 100

    const_means = {}
    for sys, (name, _) in CONST_INFO.items():
        vals = df[df["constellation"] == sys]["cnr"].dropna()
        if len(vals):
            const_means[name] = f"{vals.mean():.1f} dB-Hz"
        else:
            const_means[name] = "no data"

    summary_lines = [
        f"Receiver:     Septentrio MOSAIC-X5C",
        f"Duration:     {duration_s:.0f} s  ({duration_s/60:.1f} min)",
        f"Total epochs: {total_epochs}",
        f"Obs / epoch:  {len(df)/max(total_epochs, 1):.1f}",
        "",
        f"Mean C/N0:    {all_cnr.mean():.1f} dB-Hz",
        f"Median C/N0:  {all_cnr.median():.1f} dB-Hz",
        f"Std C/N0:     {all_cnr.std():.1f} dB-Hz",
        f"Min C/N0:     {all_cnr.min():.1f} dB-Hz",
        "",
        f"Epochs < 30 dB-Hz: {below_30:.1f}%",
        f"Epochs < 25 dB-Hz: {below_25:.1f}%",
        "",
        "Per-constellation mean:",
    ] + [f"  {k}: {v}" for k, v in const_means.items()]

    ax4.text(0.05, 0.97, "\n".join(summary_lines),
             transform=ax4.transAxes,
             fontsize=9, verticalalignment="top",
             fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5",
                       edgecolor="#BDBDBD", alpha=0.9))
    ax4.set_title("Summary Statistics", loc="left", fontsize=10)

    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / \
        f"Scenario_{scenario_id.upper()}_{run_label}_ANALYSIS.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"  Saved: {fname.name}")

    return {
        "scenario": scenario_id.upper(),
        "label": label,
        "run": run_label,
        "duration_s": duration_s,
        "mean_cnr": all_cnr.mean() if len(all_cnr) else np.nan,
        "below_25_pct": below_25,
        "total_epochs": total_epochs,
        "obs_file": str(out_dir / fname.name),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART: COMPARISON ACROSS SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

def make_comparison_chart(summaries: list[dict], all_dfs: dict, out_dir: Path):
    """
    Generate a multi-panel comparison chart with one C/N0 trace per scenario.
    """
    if not all_dfs:
        return

    fig, axes = plt.subplots(2, 1, figsize=(14, 10),
                             gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle("GNSS Signal Quality — All Scenarios Comparison\n"
                 "Septentrio MOSAIC-X5C | May 5, 2026 | Beihang University Area",
                 fontsize=13, fontweight="bold")

    colors = ["#2196F3", "#F44336", "#4CAF50", "#9C27B0", "#FF9800",
              "#00BCD4", "#795548", "#607D8B"]

    ax = axes[0]
    ci = 0
    for scen_id in sorted(all_dfs.keys()):
        for run_label, df in all_dfs[scen_id]:
            if df.empty:
                continue
            epoch_cnr = (df.dropna(subset=["cnr"])
                           .groupby("t_sec")
                           .agg(mean_cnr=("cnr", "mean"))
                           .reset_index())
            if epoch_cnr.empty:
                continue
            lbl = f"{scen_id} — {SCENARIO_LABELS.get(scen_id, scen_id)}"
            if run_label != "Run_1":
                lbl += f" ({run_label})"
            ax.plot(epoch_cnr["t_sec"], epoch_cnr["mean_cnr"],
                    label=lbl, color=colors[ci % len(colors)], linewidth=1.8)
            ci += 1

    ax.axhline(35, color="#2196F3", linestyle="--", linewidth=1.0,
               label="Good threshold (35 dB-Hz)")
    ax.axhline(30, color="#FF9800", linestyle="--", linewidth=1.0,
               label="Warning threshold (30 dB-Hz)")
    ax.axhline(25, color="#F44336", linestyle="--", linewidth=1.0,
               label="Degraded threshold (25 dB-Hz)")

    ax.set_xlabel("Time since start of recording (s)", fontsize=10)
    ax.set_ylabel("Mean C/N0 — all constellations (dB-Hz)", fontsize=10)
    ax.set_title("C/N0 Trends — All Collected Scenarios", fontsize=11)
    ax.legend(fontsize=8, loc="lower left", ncol=2)
    ax.set_ylim(0, 55)
    ax.grid(True, alpha=0.3)

    # ── Summary table ───────────────────────────────────────────────────
    ax2 = axes[1]
    ax2.axis("off")
    if summaries:
        cols = ["Scenario", "Description", "Duration (s)", "Mean C/N0",
                "% Epochs < 25 dB-Hz", "Epochs"]
        rows = []
        for s in summaries:
            rows.append([
                s["scenario"],
                s["label"],
                f"{s['duration_s']:.0f}",
                f"{s['mean_cnr']:.1f}" if not np.isnan(
                    s["mean_cnr"]) else "N/A",
                f"{s['below_25_pct']:.1f}%",
                str(s["total_epochs"]),
            ])
        tbl = ax2.table(cellText=rows, colLabels=cols,
                        loc="center", cellLoc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.5)
        for (r, c), cell in tbl.get_celld().items():
            if r == 0:
                cell.set_facecolor("#1565C0")
                cell.set_text_props(color="white", fontweight="bold")
            elif r % 2 == 0:
                cell.set_facecolor("#E3F2FD")

    fname = out_dir / "ALL_SCENARIOS_COMPARISON.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Comparison chart saved: {fname}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_scenario(scenario_id: str, out_dir: Path) -> tuple[list[dict], list]:
    """Analyse all runs for one scenario. Returns (summaries, [(label, df), ...])."""
    runs = find_obs_files(scenario_id)
    if not runs:
        logger.warning(f"No RINEX files found for scenario {scenario_id}. "
                       f"Expected in {SCENARIOS_DIR}/scenario_{scenario_id.lower()}/{scenario_id}/")
        return [], []

    summaries = []
    run_dfs = []
    for run_label, obs_file in runs:
        logger.info(f"Parsing {scenario_id} / {run_label}: {obs_file.name}")
        df = parse_rinex_obs(obs_file)
        if df.empty:
            continue
        s = make_scenario_chart(scenario_id, run_label, df, out_dir)
        if s:
            summaries.append(s)
        run_dfs.append((run_label, df))

    return summaries, run_dfs


def main():
    parser = argparse.ArgumentParser(
        description="Analyse Septentrio RINEX data for collected scenarios."
    )
    parser.add_argument("--scenario", help="Analyse a single scenario (A–E)")
    parser.add_argument("--all", action="store_true",
                        help="Analyse all scenarios and produce comparison chart")
    args = parser.parse_args()

    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.all or (not args.scenario):
        all_summaries = []
        all_dfs: dict[str, list] = {}
        for scen_id in ["A", "B", "C", "D", "E"]:
            sums, dfs = analyse_scenario(scen_id, out_dir)
            all_summaries.extend(sums)
            if dfs:
                all_dfs[scen_id] = dfs
        if all_dfs:
            make_comparison_chart(all_summaries, all_dfs, out_dir)
        logger.info(f"\nAll charts written to: {out_dir}")
    elif args.scenario:
        sums, dfs = analyse_scenario(args.scenario.upper(), out_dir)
        if dfs:
            make_comparison_chart(sums,
                                  {args.scenario.upper(): dfs}, out_dir)
        logger.info(f"Charts written to: {out_dir}")


if __name__ == "__main__":
    main()
