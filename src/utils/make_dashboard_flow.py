"""Generate dashboard architecture flowchart for the SENTINEL-GNSS poster."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "results" / "paper_figures" / "dashboard_flow.png"

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = "#0A1A2F"   # slide background
BAND1   = "#0D2240"   # data layer band
BAND2   = "#102847"   # backend band
BAND3   = "#112A4D"   # frontend band
BAND4   = "#0D2240"   # output band

BOX_BLU = "#1A4A8A"   # data / rest box
BOX_AMB = "#7A4A00"   # websocket box
BOX_LIV = "#1A3D6B"   # live tab column
BOX_FUS = "#1A3D6B"   # fusion tab column
BOX_ANA = "#1A3D6B"   # analytics tab column
BOX_OUT = "#162A4A"   # output boxes

CYAN    = "#00D4FF"   # WS arrow
LT_BLU  = "#5B9BD5"   # REST arrow / internal arrow
WHITE   = "#FFFFFF"
OFF_W   = "#C8D8EC"
SLATE   = "#8AAABF"
AMBER   = "#FFB300"
GREEN   = "#43A047"
RED_C   = "#EF5350"
TEAL    = "#00BFA5"

# ── Canvas ─────────────────────────────────────────────────────────────────────
W, H = 16, 8
fig, ax = plt.subplots(figsize=(W, H), facecolor=BG)
ax.set_facecolor(BG)
ax.set_xlim(0, W); ax.set_ylim(0, H)
ax.axis("off")

# ── Helper functions ───────────────────────────────────────────────────────────
def band(y0, y1, color):
    ax.add_patch(mpatches.Rectangle((0, y0), W, y1-y0, color=color, zorder=0))

def box(x, y, w, h, fc, ec="#2A5AA0", label=None, sublabel=None,
        label_size=8.5, sub_size=7, lc=WHITE, slc=SLATE, radius=0.12, zorder=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0,rounding_size={radius}",
                 facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=zorder))
    cy = y + h/2
    if label and sublabel:
        ax.text(x+w/2, cy+0.08, label,   color=lc, fontsize=label_size, fontweight="bold",
                ha="center", va="center", zorder=zorder+1)
        ax.text(x+w/2, cy-0.20, sublabel, color=slc, fontsize=sub_size,
                ha="center", va="center", zorder=zorder+1)
    elif label:
        ax.text(x+w/2, cy, label, color=lc, fontsize=label_size, fontweight="bold",
                ha="center", va="center", zorder=zorder+1)

def arrow(x0, y0, x1, y1, color=LT_BLU, lw=1.6, label=None):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=12))
    if label:
        mx, my = (x0+x1)/2, (y0+y1)/2
        ax.text(mx+0.08, my, label, color=color, fontsize=6.5, ha="left", va="center",
                fontweight="bold")

def layer_header(y, text, fc, size=8.5):
    ax.add_patch(mpatches.Rectangle((0, y), W, 0.32, color=fc, zorder=1))
    ax.text(W/2, y+0.16, text, color=WHITE, fontsize=size, fontweight="bold",
            ha="center", va="center", zorder=2, family="monospace")

def pill(x, y, text, color=AMBER, tc="#1A0A00", size=6.5):
    ax.add_patch(FancyBboxPatch((x, y), 1.5, 0.22,
                 boxstyle="round,pad=0,rounding_size=0.08",
                 facecolor=color, edgecolor="none", zorder=5))
    ax.text(x+0.75, y+0.11, text, color=tc, fontsize=size,
            ha="center", va="center", fontweight="bold", zorder=6)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER BANDS
# ══════════════════════════════════════════════════════════════════════════════
band(6.55, 8.00, BAND1)   # data
band(4.50, 6.55, BAND2)   # backend
band(1.70, 4.50, BAND3)   # frontend
band(0.00, 1.70, BAND4)   # outputs

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — DATA SOURCES (y=6.55–8.00)
# ══════════════════════════════════════════════════════════════════════════════
layer_header(7.65, "01  DATA SOURCES  (pre-computed · 0 ms inference overhead)", BAND1, 8)

bw, bh, bx0, by = 4.6, 0.78, 0.40, 6.72
gap = 0.40

box(bx0,          by, bw, bh, BOX_BLU,
    label="Inference CSVs", sublabel="results/inference/*_predictions.csv\nwindow · x · y · p_deg_5s/15s/30s · pred_class")
box(bx0+bw+gap,   by, bw, bh, BOX_BLU,
    label="EKF Track Files",
    sublabel="urbannav_ekf_real_{source}_tracks.npz\ntruth · gnss · aided_fixed · adapt · huber · pf")
box(bx0+2*(bw+gap), by, bw, bh, BOX_BLU,
    label="EKF Summary JSON",
    sublabel="urbannav_ekf.json\nRMSE · degraded gain · nSat stats · engine")

# Caption
ax.text(W/2, 6.59, "All data pre-computed from real Tokyo GNSS drives",
        color=SLATE, fontsize=7, ha="center", va="bottom", style="italic")

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — FASTAPI BACKEND (y=4.50–6.55)
# ══════════════════════════════════════════════════════════════════════════════
layer_header(6.20, "02  FastAPI BACKEND  ·  port 8000", BAND2, 8)

# REST endpoints block
rx, ry, rw, rh = 0.40, 4.64, 6.8, 1.46
ax.add_patch(FancyBboxPatch((rx, ry), rw, rh,
             boxstyle="round,pad=0,rounding_size=0.10",
             facecolor=BOX_BLU, edgecolor="#2A5AA0", linewidth=1.2, zorder=2))
ax.text(rx+rw/2, ry+rh-0.16, "REST API", color=WHITE, fontsize=8.5,
        fontweight="bold", ha="center", va="center", zorder=3)

endpoints = [
    "GET  /api/predictions/{id}   →  full CSV as JSON",
    "GET  /api/fusion?source=x    →  tracks + RMSE (≤1200 pts)",
    "GET  /api/ekf                →  EKF comparison table",
    "GET  /api/scenarios          →  list available runs",
]
for i, ep in enumerate(endpoints):
    ax.text(rx+0.18, ry+rh-0.40-i*0.25, ep, color=OFF_W, fontsize=6.8,
            va="center", family="monospace", zorder=3)

# WebSocket block
wx, wy, ww, wh = 7.80, 4.64, 7.80, 1.46
ax.add_patch(FancyBboxPatch((wx, wy), ww, wh,
             boxstyle="round,pad=0,rounding_size=0.10",
             facecolor=BOX_AMB, edgecolor=AMBER, linewidth=1.5, zorder=2))
ax.text(wx+ww/2, wy+wh-0.16, "WebSocket  /ws", color=AMBER, fontsize=8.5,
        fontweight="bold", ha="center", va="center", zorder=3)

ws_lines = [
    "recv:  start_replay {scenario, speed}",
    "emit:  replay_start {total}",
    "emit:  epoch {index, data}  × N  [delay = 1/speed s]",
    "emit:  replay_end | replay_stopped",
]
for i, ln in enumerate(ws_lines):
    ax.text(wx+0.22, wy+wh-0.40-i*0.25, ln, color=OFF_W, fontsize=6.8,
            va="center", family="monospace", zorder=3)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — FRONTEND  (y=1.70–4.50)
# ══════════════════════════════════════════════════════════════════════════════
layer_header(4.15, "03  Next.js 15 FRONTEND  ·  port 3000  ·  React 19", BAND3, 8)

cw, ch = 4.9, 2.26
cx0, cy = 0.30, 1.80

# Live Tab
lx = cx0
ax.add_patch(FancyBboxPatch((lx, cy), cw, ch,
             boxstyle="round,pad=0,rounding_size=0.12",
             facecolor=BOX_LIV, edgecolor=RED_C, linewidth=1.5, zorder=2))
ax.text(lx+cw/2, cy+ch-0.20, "🔴  Live Tab", color=RED_C, fontsize=8.5,
        fontweight="bold", ha="center", va="center", zorder=3)
live_items = [
    "ControlBar  (scenario ▾  horizon ▾  ▶ Play)",
    "SignalGauge  · ProbabilityBars  · AlarmCenter",
    "LeadTimeCard  (early-warning seconds)",
    "TrajectoryMap  · TimeSeriesChart",
]
for i, it in enumerate(live_items):
    ax.text(lx+cw/2, cy+ch-0.52-i*0.38, it, color=OFF_W, fontsize=7,
            ha="center", va="center", zorder=3)

# Fusion Tab
fx = cx0 + cw + 0.35
ax.add_patch(FancyBboxPatch((fx, cy), cw, ch,
             boxstyle="round,pad=0,rounding_size=0.12",
             facecolor=BOX_FUS, edgecolor=TEAL, linewidth=1.5, zorder=2))
ax.text(fx+cw/2, cy+ch-0.20, "🗺  Fusion Tab", color=TEAL, fontsize=8.5,
        fontweight="bold", ha="center", va="center", zorder=3)
fus_items = [
    "Source: Trimble · u-blox Shinjuku · Odaiba",
    "OSM tile map + EKF track overlays",
    "Truth · GNSS · Fixed · Adaptive · Huber · PF",
    "RMSE bars (blockage segment) + SatelliteStrip",
]
for i, it in enumerate(fus_items):
    ax.text(fx+cw/2, cy+ch-0.52-i*0.38, it, color=OFF_W, fontsize=7,
            ha="center", va="center", zorder=3)

# Analytics Tab
ax_ = fx + cw + 0.35
ax.add_patch(FancyBboxPatch((ax_, cy), cw, ch,
             boxstyle="round,pad=0,rounding_size=0.12",
             facecolor=BOX_ANA, edgecolor=LT_BLU, linewidth=1.5, zorder=2))
ax.text(ax_+cw/2, cy+ch-0.20, "📊  Analytics Tab", color=LT_BLU, fontsize=8.5,
        fontweight="bold", ha="center", va="center", zorder=3)
ana_items = [
    "EKF study on real Tokyo data",
    "GNSS-only  47.4 m  →  SENTINEL  26.9 m",
    "−43.2% position error (blockage segment)",
    "Method × environment × RMSE table",
]
for i, it in enumerate(ana_items):
    ax.text(ax_+cw/2, cy+ch-0.52-i*0.38, it, color=OFF_W, fontsize=7,
            ha="center", va="center", zorder=3)

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — OUTPUTS (y=0.00–1.70)
# ══════════════════════════════════════════════════════════════════════════════
layer_header(1.36, "04  REAL-TIME OUTPUTS", BAND4, 8)

outputs = [
    ("🎯 Risk Dial",   "P(DEG) + confidence"),
    ("🚨 Alarm Log",   "coalesced episodes"),
    ("🗺 Live Map",    "risk-coloured trail"),
    ("📈 Timeline",    "+5 / +15 / +30 s"),
    ("📍 Lead Time",   "N s early warning"),
    ("💾 CSV Export",  "one-click download"),
]
ow, oh, oy = 2.40, 0.70, 0.36
ox0 = (W - len(outputs)*ow - (len(outputs)-1)*0.10) / 2
for i, (lbl, sub) in enumerate(outputs):
    ox = ox0 + i*(ow+0.10)
    box(ox, oy, ow, oh, BOX_OUT, ec=LT_BLU,
        label=lbl, sublabel=sub, label_size=7.5, sub_size=6.5, lc=WHITE, slc=SLATE)

# ══════════════════════════════════════════════════════════════════════════════
# ARROWS  (data → backend → frontend → outputs)
# ══════════════════════════════════════════════════════════════════════════════

# Data → REST
arrow(3.70, 6.72, 3.70, 6.10, LT_BLU, lw=1.8)
# Data → WS
arrow(11.65, 6.72, 11.65, 6.10, CYAN, lw=1.8)

# WS → Live tab (WebSocket stream)
arrow(wx+ww/2, wy, lx+cw/2, cy+ch, CYAN, lw=2.2, label="WS stream")

# REST → Fusion tab
arrow(rx+rw*0.70, ry, fx+cw/2, cy+ch, LT_BLU, lw=1.6, label="HTTP GET")

# REST → Analytics tab
arrow(rx+rw*0.92, ry, ax_+cw/2, cy+ch, LT_BLU, lw=1.6)

# Frontend → Outputs (3 short arrows centred on each tab)
for tab_cx in [lx+cw/2, fx+cw/2, ax_+cw/2]:
    arrow(tab_cx, cy, tab_cx, 1.70, WHITE, lw=1.2)

# ══════════════════════════════════════════════════════════════════════════════
# PILL BADGES
# ══════════════════════════════════════════════════════════════════════════════
pill(0.25, 7.33, "0 ms latency",  AMBER, "#2A1000")
pill(4.65, 5.18, "≤1200 pts/tab", "#1A4A8A", WHITE)
pill(9.60, 5.18, "1 Hz stream",   AMBER, "#2A1000")
pill(3.40, 3.42, "audio alert",   RED_C, WHITE)

# ══════════════════════════════════════════════════════════════════════════════
# TITLE + FOOTER
# ══════════════════════════════════════════════════════════════════════════════
ax.text(W/2, 7.90, "SENTINEL-GNSS  Real-Time Dashboard — Architecture & Data Flow",
        color=WHITE, fontsize=11, fontweight="bold", ha="center", va="center")

ax.text(W/2, 0.09, "FastAPI 0.110  ·  Next.js 15  ·  React 19  ·  WebSocket  ·  "
                    "Beihang University 2026",
        color=SLATE, fontsize=6.5, ha="center", va="bottom")

# ══════════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════════
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(str(OUT), dpi=200, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close(fig)
print(f"Saved -> {OUT}")
