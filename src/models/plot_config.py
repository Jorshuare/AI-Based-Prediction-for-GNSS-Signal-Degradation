"""
plot_config.py — Single source of truth for all SENTINEL-GNSS visualizations.

Enforces publication-quality standards (IEEE / Elsevier / Springer) with:
  - Colorblind-safe palettes  (cividis primary; alternatives commented)
  - Minimum 14 pt font sizes  (IEEE Author Center Graphics Guide, 2023)
  - IEEE double-column figure widths
  - Okabe-Ito class colours   (CUD gold standard for categorical data)

References
----------
Nunez, J. R. et al. (2018). Optimizing colormaps with consideration for color
    vision deficiency. PLOS ONE, 13(7), e0199239.
    https://doi.org/10.1371/journal.pone.0199239

Okabe, M. & Ito, K. (2008). Color Universal Design (CUD) — How to make figures
    and presentations that are friendly to colorblind people.
    https://jfly.uni-koeln.de/color/

Rougier, N. P., Droettboom, M., & Ness, P. E. (2014). Ten simple rules for
    better figures. PLOS Computational Biology, 10(9), e1003833.
    https://doi.org/10.1371/journal.pcbi.1003833

IEEE Author Center (2023). Graphics Specifications for IEEE Journals.
    https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/
    preparing-your-manuscript/
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


# ─── Sequential / diverging colormaps ────────────────────────────────────────
# PRIMARY: cividis — perceptually uniform, monochrome-safe, deuteranopia-safe
#   Ref: Nunez et al. (2018), PLOS ONE
CMAP_SEQUENTIAL = "cividis"
# Colorblind-safe diverging  (red→yellow→blue)
CMAP_DIVERGING = "RdYlBu_r"
CMAP_CYCLIC = "twilight_shifted"  # Colorblind-safe cyclic     (for phase data)

# ── ALTERNATIVE sequential palettes — comment in to test ─────────────────────
# CMAP_SEQUENTIAL = "viridis"     # Matplotlib default; CVD-safe, purple→yellow
# CMAP_SEQUENTIAL = "plasma"      # High-contrast purple → bright yellow
# CMAP_SEQUENTIAL = "magma"       # Dark purple → near-white
# CMAP_SEQUENTIAL = "inferno"     # Black → deep red → yellow; avoids red/green
# CMAP_SEQUENTIAL = "mako"        # Seaborn; dark teal → near-white (elegant)
# CMAP_SEQUENTIAL = "rocket"      # Seaborn; dark → salmon → near-white
# CMAP_SEQUENTIAL = "YlOrRd"      # Sequential yellow-orange-red (light bg only)
# CMAP_SEQUENTIAL = "Blues"       # Perceptually monotone blue (single variable)
# ── NOT recommended for CVD: "jet", "rainbow", "hsv", "gist_rainbow" ────────

# ── ALTERNATIVE diverging palettes ───────────────────────────────────────────
# CMAP_DIVERGING  = "BrBG"        # Brown-white-green (CVD friendly)
# CMAP_DIVERGING  = "PuOr"        # Purple-orange (Brewer palette)
# CMAP_DIVERGING  = "PRGn"        # Purple-green (Brewer palette)


# ─── Class colours (3-class: CLEAN / WARNING / DEGRADED) ─────────────────────
# Okabe-Ito palette — CUD-recommended for categorical data with up to 8 classes.
# Distinguishable by deuteranopes, protanopes, and tritanopes.
#   Ref: Okabe & Ito (2008); https://jfly.uni-koeln.de/color/
CLASS_COLORS: dict[str, str] = {
    "CLEAN":    "#0072B2",   # Blue      — safe sky signal
    "WARNING":  "#E69F00",   # Orange    — caution
    "DEGRADED": "#D55E00",   # Vermilion — danger / loss of fix
}
CLASS_COLORS_LIST: list[str] = [
    CLASS_COLORS["CLEAN"],
    CLASS_COLORS["WARNING"],
    CLASS_COLORS["DEGRADED"],
]
CLASS_LABELS: list[str] = ["CLEAN", "WARNING", "DEGRADED"]
N_CLASSES: int = 3

# ── ALTERNATIVE categorical palettes — comment in to test ────────────────────
# IBM Carbon v11 (colorblind-friendly corporate palette):
# CLASS_COLORS = {"CLEAN": "#0f62fe", "WARNING": "#f1c21b", "DEGRADED": "#da1e28"}
#
# Seaborn built-in colorblind (8-color):
# import seaborn as sns
# _pal = sns.color_palette("colorblind", 3)
# CLASS_COLORS_LIST = [_pal[0], _pal[2], _pal[1]]  # blue, green, orange
#
# Tol bright (Paul Tol — excellent for up to 7 classes, CVD-safe):
# CLASS_COLORS = {"CLEAN": "#4477AA", "WARNING": "#CCBB44", "DEGRADED": "#EE6677"}


# ─── Prediction-horizon colours (sampled from cividis) ───────────────────────
# Three visually distinct, ordered positions along the sequential colormap.
def horizon_colors() -> dict[str, tuple]:
    """Return distinct colours for the three prediction horizons (5s/15s/30s)."""
    cmap = plt.get_cmap(CMAP_SEQUENTIAL)
    return {"5s": cmap(0.15), "15s": cmap(0.50), "30s": cmap(0.85)}


# ─── Accent / neutral colours ────────────────────────────────────────────────
# Reddish-purple (Okabe-Ito)  — highlights, best model
ACCENT_COLOR = "#CC79A7"
# Grey           (Okabe-Ito)  — baselines, reference
NEUTRAL_COLOR = "#999999"


# ─── Font sizes — IEEE minimum is 6 pt; we enforce ≥ 14 pt for readability ───
FONT_SUPTITLE = 18    # Figure-level super-title
FONT_TITLE = 16    # Axes title
FONT_AXIS_LABEL = 14    # x- and y-axis labels  ← IEEE recommended minimum
FONT_TICK = 13    # Tick labels
FONT_LEGEND = 13    # Legend entries and legend title
FONT_ANNOTATION = 12    # In-figure annotations / text boxes


# ─── Figure sizes (inches) ───────────────────────────────────────────────────
# IEEE double-column article: text width ≈ 7.16 in
# Elsevier double-column:     text width ≈ 7.48 in
# Springer (LNCS):            text width ≈ 5.04 in (single col)
FIG_SINGLE_COL = (3.5,  2.8)   # IEEE single-column, compact
FIG_DOUBLE_COL = (7.16, 4.5)   # IEEE double-column, landscape
FIG_DOUBLE_TALL = (7.16, 6.0)   # IEEE double-column, taller (confusion matrix)
FIG_SQUARE = (5.5,  5.5)   # Square (confusion matrix, attention heatmap)
FIG_WIDE = (10.0, 4.5)   # Wide (multi-horizon comparison, time series)
FIG_POSTER = (14.0, 8.0)   # Conference poster panel


# ─── Line / marker styles ─────────────────────────────────────────────────────
LINE_STYLES: list[str] = ["-", "--", "-.", ":"]
MARKERS:     list[str] = ["o", "s", "^", "D", "v", "P", "*"]


# ─── Resolution settings ─────────────────────────────────────────────────────
DPI_SCREEN = 100     # Notebook / on-screen rendering
DPI_PAPER = 300     # IEEE/Springer minimum for halftone figures
# Vector formats (PDF, SVG, EPS) ignore DPI — use savefig(format='pdf') directly


# ─── Apply style to current matplotlib session ───────────────────────────────
def apply_publication_style() -> None:
    """Set rcParams for publication-quality figures.

    Call once at the top of any script or notebook before the first plot.
    All subsequent figures will inherit these settings automatically.

    Notes
    -----
    Times New Roman is used if available (required by many journals).
    Falls back to DejaVu Serif for environments without MS fonts.
    For camera-ready submissions, verify font embedding with the journal's
    PDF checker (e.g., IEEE PDF eXpress).
    """
    mpl.rcParams.update(
        {
            # ── Fonts ───────────────────────────────────────────────────────
            "font.family":            "serif",
            "font.serif":             ["Times New Roman", "DejaVu Serif"],
            "font.size":              FONT_AXIS_LABEL,
            "axes.titlesize":         FONT_TITLE,
            "axes.titleweight":       "bold",
            "axes.labelsize":         FONT_AXIS_LABEL,
            "axes.labelweight":       "bold",
            "xtick.labelsize":        FONT_TICK,
            "ytick.labelsize":        FONT_TICK,
            "legend.fontsize":        FONT_LEGEND,
            "legend.title_fontsize":  FONT_LEGEND,
            # ── Figure ──────────────────────────────────────────────────────
            "figure.dpi":             DPI_SCREEN,
            "savefig.dpi":            DPI_PAPER,
            "figure.facecolor":       "white",
            "axes.facecolor":         "white",
            "figure.autolayout":      False,   # use tight_layout() or constrained
            # ── Grid ────────────────────────────────────────────────────────
            "axes.grid":              True,
            "grid.alpha":             0.35,
            "grid.linewidth":         0.5,
            "grid.color":             "#cccccc",
            "axes.axisbelow":         True,    # grid behind data
            # ── Lines / markers ─────────────────────────────────────────────
            "lines.linewidth":        2.0,
            "lines.markersize":       6,
            # ── Legend ──────────────────────────────────────────────────────
            "legend.framealpha":      0.92,
            "legend.edgecolor":       "#aaaaaa",
            "legend.fancybox":        False,
            "legend.frameon":         True,
            "legend.borderpad":       0.5,
            # ── Axes spines ─────────────────────────────────────────────────
            "axes.spines.top":        False,
            "axes.spines.right":      False,
            "axes.linewidth":         1.0,
            # ── Ticks ───────────────────────────────────────────────────────
            "xtick.direction":        "out",
            "ytick.direction":        "out",
            "xtick.major.size":       4.0,
            "ytick.major.size":       4.0,
            "xtick.minor.visible":    False,
            # ── Color ───────────────────────────────────────────────────────
            "image.cmap":             CMAP_SEQUENTIAL,
            "axes.prop_cycle":        mpl.cycler(color=CLASS_COLORS_LIST),
            # ── Save ────────────────────────────────────────────────────────
            "savefig.bbox":           "tight",
            "savefig.pad_inches":     0.05,
            "savefig.format":         "pdf",    # vector default; override per call
        }
    )


def get_class_cmap() -> mcolors.ListedColormap:
    """Return a 3-colour ListedColormap using Okabe-Ito class colours."""
    return mcolors.ListedColormap(CLASS_COLORS_LIST, name="sentinel_classes")


def save_figure(
    fig: plt.Figure,
    path: str,
    formats: tuple[str, ...] = ("pdf", "png"),
    dpi: int = DPI_PAPER,
) -> None:
    """Save a figure in multiple formats for submission + presentation.

    Parameters
    ----------
    fig    : matplotlib Figure to save.
    path   : Base path WITHOUT extension (e.g. 'results/figures/confusion_matrix').
    formats: Iterable of format strings ('pdf', 'png', 'svg', 'eps').
    dpi    : Resolution for raster formats (ignored for pdf/svg/eps).
    """
    for fmt in formats:
        out = f"{path}.{fmt}"
        fig.savefig(out, dpi=dpi if fmt == "png" else None, format=fmt)
        print(f"  Saved → {out}")
