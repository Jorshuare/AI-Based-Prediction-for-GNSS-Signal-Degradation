"""
Generate the SENTINEL-GNSS system pipeline diagram.

Outputs:
    results/paper_figures/system_pipeline_diagram.png   (300 dpi, 13.33 x 6.0 in)

Colors match the V5 presentation palette.
"""

import os
import numpy as np
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

os.makedirs("results/paper_figures", exist_ok=True)

# ── Palette (matching V5 slide hex codes) ──────────────────────────────────
NAVY = "#003366"
BLUE = "#003893"
MID_BLUE = "#005BAC"
CYAN = "#4FC3F7"
GREEN = "#1B873A"
RED = "#C62828"
AMBER = "#F57F17"
PURPLE = "#6A1B9A"
DARK = "#0A1733"
GREY = "#333333"
LGREY = "#5A6A86"

BG_WHITE = "#FFFFFF"
FILL_BLUE = "#E3F2FD"
FILL_GREEN = "#E8F5E9"
FILL_RED = "#FDECEA"
FILL_AMB = "#FFF8E1"
FILL_NAVY = "#EEF2FF"
FILL_PURP = "#F3E5F5"
FILL_GREY = "#F5F7FF"


# ── Canvas ─────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13.33, 6.0))
ax.set_xlim(0, 13.33)
ax.set_ylim(0, 6.0)
ax.set_aspect('equal')
ax.axis('off')
fig.patch.set_facecolor(BG_WHITE)

# ── Helper functions ────────────────────────────────────────────────────────


def box(ax, x, y, w, h, fill, border, title, title_color=DARK,
        body_lines=None, body_color=GREY, radius=0.18,
        title_size=8.5, body_size=7.5, bold_title=True):
    """Draw a rounded rectangle with title and optional body lines."""
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={radius}",
                          linewidth=1.5, edgecolor=border, facecolor=fill, zorder=3)
    ax.add_patch(rect)
    # title
    ty = y + h - 0.17
    ax.text(x + w/2, ty, title,
            ha='center', va='top', fontsize=title_size,
            color=title_color, fontweight='bold' if bold_title else 'normal',
            zorder=4)
    # body
    if body_lines:
        by = ty - 0.19
        for line in body_lines:
            ax.text(x + w/2, by, line,
                    ha='center', va='top', fontsize=body_size,
                    color=body_color, zorder=4,
                    linespacing=1.3)
            by -= 0.185


def top_strip(ax, x, y, w, h_strip, color):
    """Colored top strip inside a box."""
    rect = FancyBboxPatch((x, y + h_strip * 3.2 - h_strip), w, h_strip,
                          boxstyle="round,pad=0,rounding_size=0.10",
                          linewidth=0, edgecolor='none', facecolor=color, zorder=4)
    ax.add_patch(rect)


def arrow(ax, x0, y0, x1, y1, color=LGREY, lw=1.5, label=None,
          label_size=6.5, head=0.12, style='->', bidirectional=False):
    """Draw a straight arrow."""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=f'->', color=color,
                                lw=lw, mutation_scale=12),
                zorder=2)
    if bidirectional:
        ax.annotate('', xy=(x0, y0), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=f'->', color=color,
                                    lw=lw, mutation_scale=12),
                    zorder=2)
    if label:
        mx, my = (x0+x1)/2, (y0+y1)/2
        ax.text(mx, my + 0.10, label,
                ha='center', va='bottom', fontsize=label_size,
                color=color, style='italic', zorder=5,
                bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))


def curved_arrow(ax, x0, y0, x1, y1, color=LGREY, lw=1.5, label=None,
                 label_size=6.5, rad=0.3):
    """Curved arrow using connectionstyle."""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, mutation_scale=12,
                                connectionstyle=f'arc3,rad={rad}'),
                zorder=2)
    if label:
        mx = (x0+x1)/2 + rad*0.4
        my = (y0+y1)/2 + abs(rad)*0.3
        ax.text(mx, my, label,
                ha='center', va='bottom', fontsize=label_size,
                color=color, style='italic', zorder=5,
                bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.9))


# ═══════════════════════════════════════════════════════════════════════════
# HEADER BAR
# ═══════════════════════════════════════════════════════════════════════════
header = FancyBboxPatch((0, 5.60), 13.33, 0.40,
                        boxstyle="round,pad=0,rounding_size=0",
                        linewidth=0, facecolor=NAVY, zorder=1)
ax.add_patch(header)
ax.text(6.67, 5.80, "SENTINEL-GNSS  —  COMPLETE SYSTEM PIPELINE",
        ha='center', va='center', fontsize=11, color='white', fontweight='bold', zorder=4)

# Cyan accent
accent = mpatches.Rectangle((0, 5.57), 13.33, 0.04, color=CYAN, zorder=2)
ax.add_patch(accent)


# ═══════════════════════════════════════════════════════════════════════════
# COLUMN LABELS
# ═══════════════════════════════════════════════════════════════════════════
col_labels = [
    (0.50,  "SENSORS"),
    (2.65,  "FEATURE\nENGINEERING"),
    (5.00,  "SENTINEL MODEL"),
    (8.55,  "ADAPTIVE EKF"),
    (11.20, "OUTPUTS &\nDASHBOARD"),
]
for cx, lbl in col_labels:
    ax.text(cx, 5.48, lbl, ha='center', va='top', fontsize=7.5,
            color=NAVY, fontweight='bold', zorder=4,
            bbox=dict(boxstyle='round,pad=0.20', fc=FILL_NAVY,
                      ec=BLUE, linewidth=0.8, alpha=0.95))

# ── Column separator lines ──────────────────────────────────────────────────
for xsep in [1.55, 3.80, 7.30, 10.00]:
    ax.plot([xsep, xsep], [0.12, 5.40], color='#DDDDDD', lw=0.8,
            linestyle='--', zorder=1)


# ═══════════════════════════════════════════════════════════════════════════
# COL 0 — SENSORS  (x: 0.05 → 1.50)
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 0.08, 3.90, 1.38, 1.10, FILL_NAVY, BLUE,
    "GNSS RECEIVER",
    title_color=BLUE,
    body_lines=["u-blox / Trimble /", "Septentrio  F9P",
                "NMEA · RINEX", "1 Hz position + obs"])

box(ax, 0.08, 2.60, 1.38, 1.00, FILL_AMB, AMBER,
    "IMU  (100 Hz)",
    title_color="#7B5200",
    body_lines=["Accelerometer (3-axis)", "Gyroscope (3-axis)", "Heading + motion"])

box(ax, 0.08, 1.50, 1.38, 0.82, FILL_GREEN, GREEN,
    "WHEEL ENCODER",
    title_color=GREEN,
    body_lines=["Vehicle speed", "Non-Holonomic", "Constraint (NHC)"])

box(ax, 0.08, 0.20, 1.38, 1.00, "#F3E5F5", PURPLE,
    "GROUND TRUTH",
    title_color=PURPLE,
    body_lines=["SPAN-INS (cm-level)", "UrbanNav Tokyo", "Validation only"])


# ═══════════════════════════════════════════════════════════════════════════
# COL 1 — FEATURE ENGINEERING  (x: 1.60 → 3.75)
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 1.63, 3.00, 2.10, 2.20, FILL_GREY, LGREY,
    "FEATURE EXTRACTION",
    title_color=DARK,
    body_lines=["37 engineered features", "per 1 Hz epoch:",
                "• C/N₀: max/mean/std/trend",
                "• DOP: gdop/pdop/hdop/vdop",
                "• Satellites: count/drop-rate",
                "• Receiver: fix quality/age",
                "• Atmospheric: iono/tropo",
                "• Temporal Δ: pdop_delta"],
    body_size=7.0)

box(ax, 1.63, 1.55, 2.10, 1.25, FILL_BLUE, BLUE,
    "SLIDING WINDOW",
    title_color=BLUE,
    body_lines=["30 epochs × 37 features",
                "= 30×37 input tensor",
                "Labels: +5 / +15 / +30 s"])

# Bias shield note
ax.text(2.68, 1.30, "✗  lat/lon excluded (geo-overfitting)", ha='center',
        va='top', fontsize=6.5, color=RED, style='italic', zorder=4)


# ═══════════════════════════════════════════════════════════════════════════
# COL 2 — SENTINEL MODEL  (x: 3.85 → 7.25)
# ═══════════════════════════════════════════════════════════════════════════

# Sub-boxes inside SENTINEL
sentinel_bg = FancyBboxPatch((3.88, 0.45), 3.30, 4.75,
                             boxstyle="round,pad=0,rounding_size=0.20",
                             linewidth=2, edgecolor=BLUE,
                             facecolor="#F8F9FF", zorder=2)
ax.add_patch(sentinel_bg)
ax.text(5.53, 5.12, "SENTINEL  ML  MODEL  —  1.46 M parameters",
        ha='center', va='center', fontsize=8, color=BLUE,
        fontweight='bold', zorder=4)

# Transformer
box(ax, 3.95, 3.80, 3.15, 1.00, FILL_BLUE, BLUE,
    "Transformer Encoder",
    title_color=BLUE,
    body_lines=["2 layers · 8 heads · d_model = 128 · d_ff = 512",
                "Self-attention: long-range signal patterns",
                "Attention(Q,K,V) = softmax(QKᵀ/√d) V"])

# BiLSTM
box(ax, 3.95, 2.60, 3.15, 0.92, FILL_AMB, AMBER,
    "Bidirectional LSTM",
    title_color="#7B5200",
    body_lines=["2 layers · hidden = 256",
                "Causal trend: is signal worsening?",
                "Gates: forget/input/output"])

# Three heads
head_labels = ["+5 s", "+15 s", "+30 s"]
head_colors = [("#E8F5E9", GREEN), (FILL_AMB, AMBER), (FILL_RED, RED)]
hx = [3.95, 4.93, 5.91]
for i, (lbl, (fc, bc)) in enumerate(zip(head_labels, head_colors)):
    box(ax, hx[i], 1.50, 0.92, 0.85, fc, bc,
        lbl, title_color=bc,
        body_lines=["P(CLEAN)", "P(WARN)", "P(DEG)"],
        body_size=6.8)

ax.text(5.53, 1.42, "3 prediction heads  —  one forward pass",
        ha='center', va='top', fontsize=7, color=DARK, style='italic', zorder=4)

# Temperature scaling
box(ax, 3.95, 0.50, 3.15, 0.75, FILL_GREY, LGREY,
    "Temperature Scaling  (T = 0.4023)",
    title_color=DARK,
    body_lines=["ECE: 0.114 → 0.068  (−40%)",
                "P(DEGRADED) = trustworthy risk score"])

# Focal loss note
ax.text(5.53, 0.35, "Focal loss γ=1.0 · class weights [1, 2, 5] · no SMOTE",
        ha='center', va='top', fontsize=6.5, color=LGREY, style='italic', zorder=4)


# ═══════════════════════════════════════════════════════════════════════════
# COL 3 — ADAPTIVE EKF  (x: 7.35 → 9.95)
# ═══════════════════════════════════════════════════════════════════════════

ekf_bg = FancyBboxPatch((7.38, 0.45), 2.55, 4.75,
                        boxstyle="round,pad=0,rounding_size=0.20",
                        linewidth=2, edgecolor=GREEN,
                        facecolor="#F5FFF7", zorder=2)
ax.add_patch(ekf_bg)
ax.text(8.65, 5.12, "9-STATE ADAPTIVE EKF",
        ha='center', va='center', fontsize=8, color=GREEN,
        fontweight='bold', zorder=4)

# Adaptive R
box(ax, 7.45, 3.80, 2.40, 1.10, FILL_RED, RED,
    "ADAPTIVE R(t)",
    title_color=RED,
    body_lines=["R(t) = σ²_base + (σ²_deg−σ²_base)×P̂_calib",
                "P̂_calib = clip((P̂−P₅)/(1−P₅), 0, 1)",
                "P̂=0 → R=9 m²  |  P̂=1 → R=10,000 m²"])

# Prediction step
box(ax, 7.45, 2.60, 2.40, 0.92, FILL_AMB, AMBER,
    "PREDICT STEP",
    title_color="#7B5200",
    body_lines=["x̂⁻ₜ = F x̂ₜ₋₁   (motion model)",
                "P⁻ₜ = F Pₜ₋₁Fᵀ + Q",
                "IMU + Odometry + NHC + ZUPT"])

# Update step
box(ax, 7.45, 1.55, 2.40, 0.85, FILL_GREEN, GREEN,
    "UPDATE STEP",
    title_color=GREEN,
    body_lines=["Kₜ = P⁻ₜHᵀ(HP⁻ₜHᵀ+Rₜ)⁻¹",
                "x̂ₜ = x̂⁻ₜ + Kₜ(zₜ − Hx̂⁻ₜ)"])

# Output state
box(ax, 7.45, 0.50, 2.40, 0.80, FILL_BLUE, BLUE,
    "STATE OUTPUT",
    title_color=BLUE,
    body_lines=["[x, y, vx, vy, heading,",
                " ax, ay, ωz, baro]",
                "Filtered position  +  velocity"])


# ═══════════════════════════════════════════════════════════════════════════
# COL 4 — OUTPUTS & DASHBOARD  (x: 10.05 → 13.25)
# ═══════════════════════════════════════════════════════════════════════════

# Position output
box(ax, 10.08, 4.30, 3.15, 0.90, FILL_GREEN, GREEN,
    "FILTERED POSITION",
    title_color=GREEN,
    body_lines=["Blocked RMSE: 47.4 m → 24.3 m",
                "+48.8%  real Tokyo data"])

# Alerts
box(ax, 10.08, 3.20, 3.15, 0.85, FILL_RED, RED,
    "ALERT ENGINE",
    title_color=RED,
    body_lines=["CRITICAL:  P(DEG) > 0.8 @ +5 s",
                "WARNING:  P(DEG) > 0.6 @ +15 s"])

# Route planner
box(ax, 10.08, 2.20, 3.15, 0.76, FILL_AMB, AMBER,
    "AV ROUTE PLANNER",
    title_color="#7B5200",
    body_lines=["+5 s → tighten IMU fusion",
                "+15 s → pre-engage dead-reckon",
                "+30 s → re-route"])

# Dashboard
dash_bg = FancyBboxPatch((10.08, 0.20), 3.15, 1.78,
                         boxstyle="round,pad=0,rounding_size=0.15",
                         linewidth=2, edgecolor=MID_BLUE,
                         facecolor=FILL_NAVY, zorder=3)
ax.add_patch(dash_bg)
ax.text(11.65, 1.88, "DASHBOARD  (FastAPI + Next.js)",
        ha='center', va='top', fontsize=7.5, color=BLUE,
        fontweight='bold', zorder=4)
dash_items = [
    (GREEN,    "Signal Gauge  (P @ +5/+15/+30 s)"),
    (BLUE,     "Probability Bars  (CLEAN / WARN / DEG)"),
    (PURPLE,   "Trajectory Map  (risk-coloured path)"),
    (MID_BLUE, "P(DEGRADED) Timeline  (3 horizons)"),
    (AMBER,    "EKF Analytics  (RMSE by strategy)"),
    (RED,      "Alert Centre  (CRITICAL / WARNING)"),
]
dy = 1.67
for col, txt in dash_items:
    ax.plot([10.18, 10.26], [dy-0.02, dy-0.02], color=col, lw=3, zorder=5)
    ax.text(10.32, dy-0.02, txt, va='center', fontsize=6.5,
            color=DARK, zorder=5)
    dy -= 0.22


# ═══════════════════════════════════════════════════════════════════════════
# ARROWS — main pipeline flow
# ═══════════════════════════════════════════════════════════════════════════

# GNSS → Feature extraction
arrow(ax, 1.46, 4.45, 1.63, 4.05, color=BLUE, lw=1.8,
      label="raw obs")

# IMU note  (→ EKF, skips SENTINEL)
# Will draw as curved later

# Feature extraction → SENTINEL input tensor
arrow(ax, 3.73, 3.85, 3.88, 3.85, color=BLUE, lw=2.0,
      label="30×37")

# Sliding window → Transformer
arrow(ax, 2.68, 2.80, 2.68, 2.75, color=LGREY, lw=1.0)  # internal
arrow(ax, 3.73, 2.18, 3.88, 3.80+0.50, color=BLUE, lw=1.5)

# SENTINEL → (P̂_calib) → Adaptive R
arrow(ax, 7.10, 3.90, 7.38, 4.05, color=RED, lw=2.2,
      label="P̂(DEG)")

# SENTINEL → Alerts / Dashboard (direct prediction output)
arrow(ax, 7.10, 2.45, 10.08, 3.62, color=AMBER, lw=1.8,
      label="P(CLEAN/WARN/DEG)")

# Adaptive R → Update step
arrow(ax, 8.65, 3.80, 8.65, 3.45, color=RED, lw=1.8)

# Predict → Update
arrow(ax, 8.65, 2.60, 8.65, 2.40, color=AMBER, lw=1.8)

# IMU → Predict step (curved, bypasses SENTINEL)
curved_arrow(ax, 1.46, 3.10, 7.45, 3.06, color=AMBER, lw=1.5,
             label="IMU @ 100 Hz", rad=-0.25)

# Wheel → Predict step
curved_arrow(ax, 1.46, 1.91, 7.45, 2.65, color=GREEN, lw=1.5,
             label="odometry", rad=-0.20)

# Update → Position output
arrow(ax, 9.85, 2.00, 10.08, 4.75, color=GREEN, lw=2.0,
      label="x̂, ŷ")

# Update → Dashboard
arrow(ax, 9.85, 1.00, 10.08, 1.10, color=MID_BLUE, lw=1.8,
      label="filtered pos")

# Ground truth → validation (dashed)
ax.annotate('', xy=(9.85, 0.25), xytext=(1.46, 0.70),
            arrowprops=dict(arrowstyle='->', color=PURPLE,
                            lw=1.2, linestyle='dashed', mutation_scale=10),
            zorder=2)
ax.text(5.65, 0.10, "SPAN-INS ground truth  (validation only)",
        ha='center', va='bottom', fontsize=6.5, color=PURPLE,
        style='italic', zorder=4,
        bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.9))

# GNSS → EKF (GNSS position measurements for the update step)
curved_arrow(ax, 1.46, 4.95, 7.45, 4.35, color=BLUE, lw=1.5,
             label="GNSS position zₜ", rad=-0.15)

# ═══════════════════════════════════════════════════════════════════════════
# CROSS-CITY BADGE
# ═══════════════════════════════════════════════════════════════════════════
badge = FancyBboxPatch((3.95, 0.08), 3.15, 0.30,
                       boxstyle="round,pad=0,rounding_size=0.10",
                       linewidth=1.2, edgecolor=RED, facecolor=FILL_RED, zorder=5)
ax.add_patch(badge)
ax.text(5.53, 0.23, "★  Zero-shot cross-city:  trained Hangzhou + HK  |  tested Tokyo (never in training)",
        ha='center', va='center', fontsize=7, color=RED,
        fontweight='bold', zorder=6)

# ═══════════════════════════════════════════════════════════════════════════
# BOTTOM ACCENT
# ═══════════════════════════════════════════════════════════════════════════
bot_bar = mpatches.Rectangle((0, 0), 13.33, 0.06, color=NAVY, zorder=1)
ax.add_patch(bot_bar)

# ═══════════════════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════════════════
out = "results/paper_figures/system_pipeline_diagram.png"
plt.tight_layout(pad=0)
plt.savefig(out, dpi=200, bbox_inches='tight',
            facecolor=BG_WHITE, edgecolor='none')
plt.close()
print(f"Saved: {out}")
