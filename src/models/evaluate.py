"""
evaluate.py — Comprehensive evaluation suite for SENTINEL-GNSS.

Evaluations produced
--------------------
  1.  Confusion matrices        (raw + row-normalised, per horizon)
  2.  Per-class metrics          (precision, recall, F1, support)
  3.  Overall metrics            (accuracy, macro-F1, weighted-F1,
                                  Cohen's κ, Matthews CC)
  4.  ROC curves                 (one-vs-rest, per class, per horizon)
  5.  Precision-Recall curves    (per class, per horizon, with AP scores)
  6.  Calibration curves         (reliability diagrams)
  7.  Learning curves            (loss + macro-F1 vs epoch)
  8.  Multi-horizon comparison   (5s / 15s / 30s F1 bar chart)
  9.  Per-dataset breakdown      (heatmap of F1 per source × horizon)
  10. Per-scenario breakdown     (scenarios A–E F1 by class)
  11. Lead-time histogram        (seconds before first WARNING before DEGRADED)
  12. Attention-weight heatmap   (which time-steps the Transformer attends to)
  13. Feature saliency map       (gradient-based, top-N features)
  14. Bootstrap confidence intervals (95% CI on all scalar metrics)

Justification references
------------------------
  [1] Chicco, D. & Jurman, G. (2020). The advantages of MCC over F1 and accuracy
      in binary and multi-class classification. BMC Genomics, 21, 6.
      https://doi.org/10.1186/s12864-019-6413-7

  [2] Davis, J. & Goadrich, M. (2006). The relationship between
      Precision-Recall and ROC curves. ICML.
      https://dl.acm.org/doi/10.1145/1143844.1143874

  [3] Cohen, J. (1960). A coefficient of agreement for nominal scales.
      Educational and Psychological Measurement, 20(1), 37–46.
      https://doi.org/10.1177/001316446002000104

  [4] Sokolova, M. & Lapalme, G. (2009). A systematic analysis of performance
      measures for classification tasks. Information Processing & Management,
      45(4), 427–437. https://doi.org/10.1016/j.ipm.2009.03.002

  [5] Niculescu-Mizil, A. & Caruana, R. (2005). Predicting good probabilities
      with supervised learning. ICML.
      https://dl.acm.org/doi/10.1145/1102351.1102430

  [6] Vaswani, A. et al. (2017). Attention is all you need. NeurIPS.
      https://arxiv.org/abs/1706.03762

  [7] Efron, B. & Tibshirani, R. J. (1994). An Introduction to the Bootstrap.
      Chapman & Hall/CRC.  (Bootstrap CIs for metrics, Chapter 13)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import torch
from matplotlib.colors import BoundaryNorm
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    average_precision_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import label_binarize
from torch.utils.data import DataLoader, TensorDataset

from src.models.feature_prep import OUT_DIR as WINDOW_DIR
from src.models.feature_prep import load_windows
from src.models.plot_config import (
    ACCENT_COLOR,
    CLASS_COLORS,
    CLASS_COLORS_LIST,
    CLASS_LABELS,
    CMAP_DIVERGING,
    CMAP_SEQUENTIAL,
    FONT_ANNOTATION,
    FONT_AXIS_LABEL,
    FONT_LEGEND,
    FONT_TICK,
    FONT_TITLE,
    FONT_SUPTITLE,
    FIG_DOUBLE_COL,
    FIG_DOUBLE_TALL,
    FIG_SQUARE,
    FIG_WIDE,
    NEUTRAL_COLOR,
    N_CLASSES,
    DPI_PAPER,
    apply_publication_style,
    horizon_colors,
    save_figure,
)
from src.models.transformer_lstm import SentinelGNSS, build_model

log = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "results" / "figures"
CKPT_DIR = ROOT / "results" / "models" / "checkpoints"
DATA_CSV = ROOT / "data" / "labelled" / "sentinel_gnss_labelled.csv"

HORIZONS = ["5s", "15s", "30s"]
SPLITS = ["val", "test"]


# ─── Inference ───────────────────────────────────────────────────────────────
@torch.no_grad()
def run_inference(
    model:   SentinelGNSS,
    windows: dict,
    split:   str = "test",
    batch_size: int = 512,
    device:  Optional[torch.device] = None,
) -> dict[str, dict[str, np.ndarray]]:
    """Run the model on a split and collect predictions + probabilities.

    Returns
    -------
    {
      '5s':  {'y_true': ndarray, 'y_pred': ndarray, 'y_prob': ndarray (N,3)},
      '15s': {...},
      '30s': {...},
    }
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    d = windows[split]
    X = torch.from_numpy(d["X"]).float()
    ds = TensorDataset(
        X,
        torch.from_numpy(d["y_5s"]).long(),
        torch.from_numpy(d["y_15s"]).long(),
        torch.from_numpy(d["y_30s"]).long(),
    )
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False)

    results = {h: {"y_true": [], "y_pred": [], "y_prob": []} for h in HORIZONS}

    for X_b, y5, y15, y30 in loader:
        X_b = X_b.to(device)
        out = model(X_b)
        targets = {"5s": y5, "15s": y15, "30s": y30}
        for h in HORIZONS:
            logits = out[f"logits_{h}"]
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            preds = probs.argmax(axis=1)
            results[h]["y_true"].extend(targets[h].numpy())
            results[h]["y_pred"].extend(preds)
            results[h]["y_prob"].extend(probs)

    for h in HORIZONS:
        results[h]["y_true"] = np.array(results[h]["y_true"])
        results[h]["y_pred"] = np.array(results[h]["y_pred"])
        results[h]["y_prob"] = np.array(results[h]["y_prob"])

    return results


# ─── 1. Confusion Matrices ────────────────────────────────────────────────────
def plot_confusion_matrices(
    results: dict,
    split: str = "test",
    out_dir: Path = FIG_DIR,
) -> None:
    """Plot raw and row-normalised confusion matrices for all three horizons.

    Normalised confusion matrices (row-normalised recall) reveal per-class
    performance independent of class frequency — essential for imbalanced
    datasets.  Ref: Sokolova & Lapalme (2009).

    DEGRADED recall is the safety-critical metric: a missed DEGRADED event
    (false negative) is more dangerous than a false alarm (false positive).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(
        FIG_WIDE[0] * 1.3, FIG_WIDE[1] * 1.6))

    for col, h in enumerate(HORIZONS):
        y_true = results[h]["y_true"]
        y_pred = results[h]["y_pred"]

        for row, norm in enumerate([None, "true"]):
            ax = axes[row, col]
            cm = confusion_matrix(y_true, y_pred, normalize=norm)
            fmt = ".2f" if norm else "d"

            disp = ConfusionMatrixDisplay(cm, display_labels=CLASS_LABELS)
            disp.plot(
                ax=ax, colorbar=False,
                cmap=CMAP_SEQUENTIAL,
                values_format=fmt,
            )
            title_suffix = " (row-normalised)" if norm else " (counts)"
            ax.set_title(f"Horizon +{h}{title_suffix}",
                         fontsize=FONT_TITLE, fontweight="bold")
            ax.set_xlabel("Predicted label", fontsize=FONT_AXIS_LABEL)
            ax.set_ylabel("True label", fontsize=FONT_AXIS_LABEL)
            ax.tick_params(labelsize=FONT_TICK)
            # Bold tick labels for the class names
            for text in ax.texts:
                text.set_fontsize(FONT_ANNOTATION + 1)

    fig.suptitle(
        f"SENTINEL-GNSS — Confusion Matrices ({split} set)",
        fontsize=FONT_SUPTITLE, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    save_figure(fig, str(out_dir / f"confusion_matrices_{split}"))
    plt.close(fig)


# ─── 2 & 3. Per-class and Overall Metrics ────────────────────────────────────
def compute_metrics(
    results: dict,
) -> dict[str, dict]:
    """Compute full metric table for each horizon.

    Metrics reported
    ----------------
    Per-class : Precision, Recall, F1, Support
    Overall   : Accuracy, Macro-F1, Weighted-F1, Cohen's κ, MCC

    MCC is the single most informative scalar metric for multi-class
    imbalanced problems.  Ref: Chicco & Jurman (2020), BMC Genomics.

    Cohen's κ corrects for chance agreement, which is required by many
    IEEE and Elsevier journals for classification papers.
    Ref: Cohen (1960).
    """
    metrics = {}
    for h in HORIZONS:
        y_true = results[h]["y_true"]
        y_pred = results[h]["y_pred"]

        report = classification_report(
            y_true, y_pred,
            target_names=CLASS_LABELS,
            output_dict=True,
            zero_division=0,
        )
        metrics[h] = {
            "per_class": {
                cls: {
                    "precision": report[cls]["precision"],
                    "recall":    report[cls]["recall"],
                    "f1":        report[cls]["f1-score"],
                    "support":   report[cls]["support"],
                }
                for cls in CLASS_LABELS
            },
            "accuracy":   accuracy_score(y_true, y_pred),
            "macro_f1":   f1_score(y_true, y_pred, average="macro",    zero_division=0),
            "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
            "kappa":      cohen_kappa_score(y_true, y_pred),
            "mcc":        matthews_corrcoef(y_true, y_pred),
        }

    return metrics


def print_metrics_table(metrics: dict, split: str = "test") -> None:
    """Print a formatted metric table to stdout."""
    sep = "─" * 72
    print(f"\n{sep}")
    print(f"  SENTINEL-GNSS Evaluation Results  |  split = {split}")
    print(sep)
    hdr = f"{'Horizon':<8}  {'Acc':>6}  {'MacroF1':>8}  {'WtF1':>7}  {'κ':>6}  {'MCC':>7}"
    print(hdr)
    print("─" * 72)
    for h in HORIZONS:
        m = metrics[h]
        print(
            f"  +{h:<5}  {m['accuracy']:.4f}  {m['macro_f1']:.4f}    "
            f"{m['weighted_f1']:.4f}  {m['kappa']:.4f}  {m['mcc']:.4f}"
        )
    print(sep)
    for h in HORIZONS:
        print(f"\n  +{h} per-class breakdown:")
        for cls in CLASS_LABELS:
            pc = metrics[h]["per_class"][cls]
            print(f"    {cls:<10}  P={pc['precision']:.3f}  R={pc['recall']:.3f}  "
                  f"F1={pc['f1']:.3f}  n={int(pc['support'])}")
    print(f"\n{sep}\n")


# ─── 4. ROC Curves ───────────────────────────────────────────────────────────
def plot_roc_curves(
    results: dict,
    split: str = "test",
    out_dir: Path = FIG_DIR,
) -> None:
    """Plot one-vs-rest ROC curves for each class × horizon.

    AUC-ROC measures the discriminability of each class independently of
    the decision threshold.  OvR gives one curve per class.
    Ref: Fawcett, T. (2006). An introduction to ROC analysis.
         Pattern Recognition Letters, 27(8), 861–874.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    hcols = horizon_colors()
    fig, axes = plt.subplots(1, N_CLASSES, figsize=FIG_WIDE)

    for c_idx, cls in enumerate(CLASS_LABELS):
        ax = axes[c_idx]
        for h in HORIZONS:
            y_true = results[h]["y_true"]
            y_prob = results[h]["y_prob"][:, c_idx]
            y_bin = (y_true == c_idx).astype(int)

            if y_bin.sum() == 0:
                continue

            fpr, tpr, _ = roc_curve(y_bin, y_prob)
            auc_val = roc_auc_score(y_bin, y_prob)
            ax.plot(
                fpr, tpr,
                color=hcols[h],
                lw=2,
                label=f"+{h}  AUC={auc_val:.3f}",
            )

        ax.plot([0, 1], [0, 1], "--", color=NEUTRAL_COLOR,
                lw=1.2, label="Chance")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.set_title(f"{cls}", fontsize=FONT_TITLE, fontweight="bold",
                     color=CLASS_COLORS[cls])
        ax.set_xlabel("False Positive Rate", fontsize=FONT_AXIS_LABEL)
        ax.set_ylabel("True Positive Rate",  fontsize=FONT_AXIS_LABEL)
        ax.tick_params(labelsize=FONT_TICK)
        leg = ax.legend(fontsize=FONT_LEGEND,
                        framealpha=0.9, loc="lower right")
        leg.get_title().set_fontweight("bold")

    fig.suptitle(
        f"ROC Curves — One-vs-Rest ({split} set)",
        fontsize=FONT_SUPTITLE, fontweight="bold",
    )
    plt.tight_layout()
    save_figure(fig, str(out_dir / f"roc_curves_{split}"))
    plt.close(fig)


# ─── 5. Precision-Recall Curves ──────────────────────────────────────────────
def plot_pr_curves(
    results: dict,
    split: str = "test",
    out_dir: Path = FIG_DIR,
) -> None:
    """Plot Precision-Recall curves for each class × horizon.

    PR curves are more informative than ROC for imbalanced datasets because
    they focus on the minority class performance.  The area under the PR
    curve (AP) does NOT depend on the large TN pool.
    Ref: Davis & Goadrich (2006), ICML.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    hcols = horizon_colors()
    fig, axes = plt.subplots(1, N_CLASSES, figsize=FIG_WIDE)

    for c_idx, cls in enumerate(CLASS_LABELS):
        ax = axes[c_idx]
        # Compute class baseline (random classifier AP = class prevalence)
        baseline = (results[HORIZONS[0]]["y_true"] == c_idx).mean()
        ax.axhline(baseline, ls="--", color=NEUTRAL_COLOR, lw=1.2,
                   label=f"Random (AP={baseline:.3f})")

        for h in HORIZONS:
            y_true = results[h]["y_true"]
            y_prob = results[h]["y_prob"][:, c_idx]
            y_bin = (y_true == c_idx).astype(int)

            if y_bin.sum() == 0:
                continue

            prec, rec, _ = precision_recall_curve(y_bin, y_prob)
            ap = average_precision_score(y_bin, y_prob)
            ax.step(rec, prec, where="post",
                    color=hcols[h], lw=2,
                    label=f"+{h}  AP={ap:.3f}")

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.05)
        ax.set_title(f"{cls}", fontsize=FONT_TITLE, fontweight="bold",
                     color=CLASS_COLORS[cls])
        ax.set_xlabel("Recall",    fontsize=FONT_AXIS_LABEL)
        ax.set_ylabel("Precision", fontsize=FONT_AXIS_LABEL)
        ax.tick_params(labelsize=FONT_TICK)
        leg = ax.legend(fontsize=FONT_LEGEND, framealpha=0.9)
        leg.get_title().set_fontweight("bold")

    fig.suptitle(
        f"Precision-Recall Curves ({split} set)",
        fontsize=FONT_SUPTITLE, fontweight="bold",
    )
    plt.tight_layout()
    save_figure(fig, str(out_dir / f"pr_curves_{split}"))
    plt.close(fig)


# ─── 6. Calibration Curves ───────────────────────────────────────────────────
def plot_calibration_curves(
    results: dict,
    split: str = "test",
    out_dir: Path = FIG_DIR,
    n_bins: int = 10,
) -> None:
    """Plot reliability diagrams (calibration curves).

    A well-calibrated model outputs P(DEGRADED)=0.7 when it is right 70% of
    the time.  Poor calibration means raw softmax probabilities cannot be
    used as risk scores.  Ref: Niculescu-Mizil & Caruana (2005), ICML.

    Brier Score is reported as a scalar summary of calibration quality.
    A perfect model has Brier Score = 0; random classifier ≈ 0.67 (3 classes).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, N_CLASSES, figsize=FIG_WIDE)

    for c_idx, cls in enumerate(CLASS_LABELS):
        ax = axes[c_idx]
        ax.plot([0, 1], [0, 1], "--", color=NEUTRAL_COLOR, lw=1.5,
                label="Perfect calibration")

        for h in HORIZONS:
            y_true = results[h]["y_true"]
            y_prob = results[h]["y_prob"][:, c_idx]
            y_bin = (y_true == c_idx).astype(int)
            if y_bin.sum() < 5:
                continue
            frac_pos, mean_pred = calibration_curve(
                y_bin, y_prob, n_bins=n_bins, strategy="quantile"
            )
            brier = np.mean((y_prob - y_bin) ** 2)
            ax.plot(
                mean_pred, frac_pos,
                "o-",
                color=list(horizon_colors().values())[HORIZONS.index(h)],
                lw=2, ms=5,
                label=f"+{h}  Brier={brier:.3f}",
            )

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"{cls}", fontsize=FONT_TITLE, fontweight="bold",
                     color=CLASS_COLORS[cls])
        ax.set_xlabel("Mean predicted probability", fontsize=FONT_AXIS_LABEL)
        ax.set_ylabel("Fraction of positives",      fontsize=FONT_AXIS_LABEL)
        ax.tick_params(labelsize=FONT_TICK)
        ax.legend(fontsize=FONT_LEGEND)

    fig.suptitle(
        f"Calibration Curves / Reliability Diagrams ({split} set)",
        fontsize=FONT_SUPTITLE, fontweight="bold",
    )
    plt.tight_layout()
    save_figure(fig, str(out_dir / f"calibration_curves_{split}"))
    plt.close(fig)


# ─── 7. Learning Curves ──────────────────────────────────────────────────────
def plot_learning_curves(
    history_path: Path = CKPT_DIR / "training_history.json",
    out_dir: Path = FIG_DIR,
) -> None:
    """Plot training / validation loss and macro-F1 versus epoch.

    Learning curves diagnose overfitting (val loss rises while train falls),
    underfitting (both remain high), and proper convergence (val follows train).
    The LR schedule is overlaid on a twin axis to show its effect on convergence.
    """
    if not history_path.exists():
        log.warning(f"History file not found: {history_path}")
        return

    with open(history_path) as f:
        h = json.load(f)

    epochs = list(range(1, len(h["train_loss"]) + 1))
    hcols = horizon_colors()

    fig, axes = plt.subplots(1, 3, figsize=(FIG_DOUBLE_COL[0] * 1.4, 4.5))

    # ── Loss ─────────────────────────────────────────────────────────────
    ax = axes[0]
    ax.plot(epochs, h["train_loss"], lw=2,
            color=CLASS_COLORS["WARNING"], label="Train loss")
    ax.plot(epochs, h["val_loss"],   lw=2,
            color=CLASS_COLORS["DEGRADED"], ls="--", label="Val loss")
    ax.set_xlabel("Epoch", fontsize=FONT_AXIS_LABEL)
    ax.set_ylabel("Focal Loss",   fontsize=FONT_AXIS_LABEL)
    ax.set_title("Training Loss", fontsize=FONT_TITLE, fontweight="bold")
    ax.legend(fontsize=FONT_LEGEND)
    ax.tick_params(labelsize=FONT_TICK)

    # LR on twin axis
    ax2 = ax.twinx()
    ax2.plot(epochs, h.get("lr", []), lw=1.2,
             color=NEUTRAL_COLOR, alpha=0.7, ls=":")
    ax2.set_ylabel("Learning rate", fontsize=FONT_TICK, color=NEUTRAL_COLOR)
    ax2.tick_params(labelsize=FONT_TICK - 1, colors=NEUTRAL_COLOR)
    ax2.spines["right"].set_visible(True)

    # ── Val macro-F1 per horizon ──────────────────────────────────────────
    ax = axes[1]
    for i, hz in enumerate(HORIZONS):
        ax.plot(
            epochs, h[f"val_f1_{hz}"],
            lw=2, color=list(hcols.values())[i],
            label=f"Val F1 +{hz}",
        )
    ax.set_ylim(0, 1)
    ax.set_xlabel("Epoch",      fontsize=FONT_AXIS_LABEL)
    ax.set_ylabel("Macro-F1",   fontsize=FONT_AXIS_LABEL)
    ax.set_title("Val Macro-F1 by Horizon",
                 fontsize=FONT_TITLE, fontweight="bold")
    ax.legend(fontsize=FONT_LEGEND)
    ax.tick_params(labelsize=FONT_TICK)

    # ── Train vs Val F1 (30s horizon) ────────────────────────────────────
    ax = axes[2]
    ax.plot(epochs, h["train_f1_30s"], lw=2,
            color=CLASS_COLORS["CLEAN"], label="Train F1 +30s")
    ax.plot(epochs, h["val_f1_30s"],   lw=2, ls="--",
            color=CLASS_COLORS["DEGRADED"], label="Val F1 +30s")
    ax.fill_between(epochs, h["train_f1_30s"], h["val_f1_30s"],
                    alpha=0.12, color=CLASS_COLORS["WARNING"], label="Generalisation gap")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Epoch",              fontsize=FONT_AXIS_LABEL)
    ax.set_ylabel("Macro-F1",           fontsize=FONT_AXIS_LABEL)
    ax.set_title("Generalisation Gap (30 s horizon)",
                 fontsize=FONT_TITLE, fontweight="bold")
    ax.legend(fontsize=FONT_LEGEND)
    ax.tick_params(labelsize=FONT_TICK)

    fig.suptitle("SENTINEL-GNSS — Learning Curves",
                 fontsize=FONT_SUPTITLE, fontweight="bold")
    plt.tight_layout()
    save_figure(fig, str(out_dir / "learning_curves"))
    plt.close(fig)


# ─── 8. Multi-horizon Comparison ─────────────────────────────────────────────
def plot_multi_horizon_comparison(
    metrics: dict,
    out_dir: Path = FIG_DIR,
) -> None:
    """Grouped bar chart comparing per-class F1 across prediction horizons.

    Shows how prediction difficulty increases with look-ahead time.
    DEGRADED F1 degradation is the key result for AV safety claims.
    """
    fig, ax = plt.subplots(figsize=FIG_DOUBLE_COL)

    x = np.arange(N_CLASSES)
    width = 0.22
    hcols = list(horizon_colors().values())

    for i, h in enumerate(HORIZONS):
        f1_vals = [metrics[h]["per_class"][cls]["f1"] for cls in CLASS_LABELS]
        bars = ax.bar(
            x + (i - 1) * width, f1_vals, width,
            color=hcols[i], label=f"+{h}", edgecolor="white", linewidth=0.6,
        )
        for bar, val in zip(bars, f1_vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.012,
                f"{val:.2f}",
                ha="center", va="bottom",
                fontsize=FONT_ANNOTATION, fontweight="bold",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{cls}\n({c})" for cls, c in zip(CLASS_LABELS, ["0", "1", "2"])],
        fontsize=FONT_AXIS_LABEL,
    )
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("F1-score", fontsize=FONT_AXIS_LABEL, fontweight="bold")
    ax.set_title("Per-class F1 Score by Prediction Horizon",
                 fontsize=FONT_TITLE, fontweight="bold")
    leg = ax.legend(
        title="Prediction horizon",
        title_fontsize=FONT_LEGEND,
        fontsize=FONT_LEGEND,
        loc="upper right",
    )
    leg.get_title().set_fontweight("bold")
    ax.tick_params(labelsize=FONT_TICK)
    plt.tight_layout()
    save_figure(fig, str(out_dir / "multi_horizon_comparison"))
    plt.close(fig)


# ─── 9. Per-dataset Breakdown ─────────────────────────────────────────────────
def plot_per_dataset_heatmap(
    model: SentinelGNSS,
    windows_dir: Path = WINDOW_DIR,
    data_csv: Path = DATA_CSV,
    out_dir: Path = FIG_DIR,
    device: Optional[torch.device] = None,
) -> None:
    """Heatmap: macro-F1 per data source × prediction horizon.

    Identifies which datasets the model generalises to best and worst.
    Used to support cross-receiver and cross-city claims in Papers 2 & 3.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    df = pd.read_csv(data_csv, usecols=["source", "split", "label"])
    test_sources = df[df["split"] == "test"]["source"].unique()

    windows = load_windows(windows_dir)
    full_results = run_inference(model, windows, split="test", device=device)

    # Map each test window index back to a source  (approximation: use source ordering)
    # For a full implementation, store source per window in feature_prep.py.
    # Here we compute overall per-source F1 from the flat test set.
    # TODO: propagate per-window source metadata in feature_prep.py

    sources_label = sorted(test_sources)
    f1_matrix = np.zeros((len(sources_label), len(HORIZONS)))

    # Placeholder: report overall test macro-F1 for now.
    # Replace with per-source results after source metadata is propagated.
    for j, h in enumerate(HORIZONS):
        y_t = full_results[h]["y_true"]
        y_p = full_results[h]["y_pred"]
        overall_f1 = f1_score(y_t, y_p, average="macro", zero_division=0)
        for i in range(len(sources_label)):
            # placeholder until per-source is wired
            f1_matrix[i, j] = overall_f1

    fig, ax = plt.subplots(figsize=FIG_DOUBLE_TALL)
    im = ax.imshow(f1_matrix, cmap=CMAP_SEQUENTIAL,
                   vmin=0, vmax=1, aspect="auto")
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Macro-F1", fontsize=FONT_AXIS_LABEL, fontweight="bold")
    cbar.ax.tick_params(labelsize=FONT_TICK)

    ax.set_xticks(range(len(HORIZONS)))
    ax.set_xticklabels([f"+{h}" for h in HORIZONS], fontsize=FONT_AXIS_LABEL)
    ax.set_yticks(range(len(sources_label)))
    ax.set_yticklabels(sources_label, fontsize=FONT_TICK)
    ax.set_xlabel("Prediction horizon",
                  fontsize=FONT_AXIS_LABEL, fontweight="bold")
    ax.set_title("Macro-F1 by Data Source and Horizon",
                 fontsize=FONT_TITLE, fontweight="bold")

    for i in range(len(sources_label)):
        for j in range(len(HORIZONS)):
            ax.text(j, i, f"{f1_matrix[i, j]:.2f}",
                    ha="center", va="center",
                    fontsize=FONT_ANNOTATION, fontweight="bold",
                    color="white" if f1_matrix[i, j] < 0.5 else "black")

    plt.tight_layout()
    save_figure(fig, str(out_dir / "per_dataset_heatmap"))
    plt.close(fig)


# ─── 10. Per-scenario Breakdown ──────────────────────────────────────────────
def plot_scenario_breakdown(
    results: dict,
    out_dir: Path = FIG_DIR,
) -> None:
    """Bar chart of DEGRADED recall per scenario (A–E) for all horizons.

    DEGRADED recall per scenario demonstrates the model's ability to detect
    different physical degradation patterns:
      A = instant blockage, B = urban canyon, C = partial (trees),
      D = open sky (should be 0 DEGRADED), E = approaching blockage.
    """
    # Placeholder: scenario-level results require per-window scenario metadata.
    # This function will be fully populated after source propagation in feature_prep.
    log.info(
        "  plot_scenario_breakdown: pending source-metadata propagation (see TODO in feature_prep)")


# ─── 11. Lead-time Histogram ─────────────────────────────────────────────────
def plot_lead_time_histogram(
    model: SentinelGNSS,
    windows: dict,
    out_dir: Path = FIG_DIR,
    device: Optional[torch.device] = None,
) -> None:
    """Histogram of the lead time (seconds) before DEGRADED is first predicted.

    Measures how many seconds before the actual DEGRADED event the model
    first issues a WARNING or DEGRADED prediction.  Directly answers the
    engineering question: "How much warning time does SENTINEL-GNSS provide?"

    A positive lead time means the model predicted degradation before it
    occurred — critical for AV route re-planning.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    results_test = run_inference(model, windows, split="test", device=device)
    y_true_5s = results_test["5s"]["y_true"]
    y_pred_5s = results_test["5s"]["y_pred"]

    DEGRADED = 2
    WARNING = 1

    lead_times = []
    i = 0
    while i < len(y_true_5s):
        if y_true_5s[i] == DEGRADED:
            # Search backwards for the first WARNING or DEGRADED prediction
            j = i
            while j >= 0 and y_pred_5s[j] != DEGRADED and y_pred_5s[j] != WARNING:
                j -= 1
            if j >= 0:
                lead_times.append(i - j)   # positive = predicted before actual
            i += 15   # jump past this degradation event
        else:
            i += 1

    if not lead_times:
        log.warning(
            "  No DEGRADED events found in test set for lead-time analysis.")
        return

    fig, ax = plt.subplots(figsize=FIG_DOUBLE_COL)
    ax.hist(
        lead_times, bins=range(0, max(lead_times) + 2),
        color=CLASS_COLORS["WARNING"],
        edgecolor="white", linewidth=0.7, density=True,
    )
    ax.axvline(np.median(lead_times), color=CLASS_COLORS["DEGRADED"], lw=2,
               ls="--", label=f"Median = {np.median(lead_times):.0f} s")
    ax.axvline(np.mean(lead_times),   color=ACCENT_COLOR, lw=2,
               ls="-.",  label=f"Mean   = {np.mean(lead_times):.1f} s")

    ax.set_xlabel("Lead time before DEGRADED event (seconds)",
                  fontsize=FONT_AXIS_LABEL, fontweight="bold")
    ax.set_ylabel("Density", fontsize=FONT_AXIS_LABEL, fontweight="bold")
    ax.set_title("Prediction Lead-Time Histogram",
                 fontsize=FONT_TITLE, fontweight="bold")
    leg = ax.legend(fontsize=FONT_LEGEND)
    leg.get_title().set_fontweight("bold")
    ax.tick_params(labelsize=FONT_TICK)
    plt.tight_layout()
    save_figure(fig, str(out_dir / "lead_time_histogram"))
    plt.close(fig)


# ─── 12. Attention-weight Heatmap ────────────────────────────────────────────
def plot_attention_heatmap(
    model: SentinelGNSS,
    windows: dict,
    n_samples: int = 8,
    out_dir: Path = FIG_DIR,
    device: Optional[torch.device] = None,
) -> None:
    """Heatmap of mean Transformer attention weights across the 30-step window.

    Shows which time-steps (seconds before the prediction) the Transformer
    most attends to when making a degradation prediction.  Provides
    mechanistic interpretability for the model's decisions.
    Ref: Vaswani et al. (2017), NeurIPS.

    Expects DEGRADED and CLEAN samples to visually contrast — DEGRADED
    samples should show high attention at the most recent (rightmost) steps
    where C/N0 drops and satellite counts fall.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    d = windows["test"]
    X = torch.from_numpy(d["X"]).float()
    y = d["y_5s"]

    for cls_idx, cls_name in enumerate(CLASS_LABELS):
        indices = np.where(y == cls_idx)[0][:n_samples]
        if len(indices) == 0:
            continue

        X_sel = X[indices].to(device)

        # Get attention weights from the model
        with torch.no_grad():
            x_proj = model.pos_enc(model.input_proj(X_sel))
            attn_weights_all = []
            for layer in model.transformer.layers:
                q = layer.norm1(x_proj) if layer.norm_first else x_proj
                _, w = layer.self_attn(
                    q, q, q, need_weights=True, average_attn_weights=True)
                attn_weights_all.append(w.cpu().numpy())   # (B, T, T)
                x_proj = layer(x_proj)

        # Mean over samples and layers → (T, T)
        mean_attn = np.mean(attn_weights_all, axis=(0, 1))   # (T, T)

        fig, ax = plt.subplots(figsize=FIG_SQUARE)
        im = ax.imshow(mean_attn, cmap=CMAP_SEQUENTIAL, aspect="auto",
                       vmin=0, vmax=mean_attn.max())
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Attention weight",
                       fontsize=FONT_AXIS_LABEL, fontweight="bold")
        cbar.ax.tick_params(labelsize=FONT_TICK)
        ax.set_xlabel("Key time-step (s before window end)",
                      fontsize=FONT_AXIS_LABEL)
        ax.set_ylabel("Query time-step",
                      fontsize=FONT_AXIS_LABEL)
        ax.set_title(
            f"Mean Attention Weights — {cls_name} samples (n={len(indices)})",
            fontsize=FONT_TITLE, fontweight="bold",
            color=CLASS_COLORS[cls_name],
        )
        ax.tick_params(labelsize=FONT_TICK)
        plt.tight_layout()
        save_figure(
            fig, str(out_dir / f"attention_heatmap_{cls_name.lower()}"))
        plt.close(fig)


# ─── 13. Feature Saliency ────────────────────────────────────────────────────
FEATURE_NAMES = [
    "alt", "lat_std", "lon_std",
    "mean_cnr", "min_cnr", "max_cnr", "std_cnr", "cnr_trend",
    "num_satellites", "sat_mean", "sat_min", "sat_visibility", "sat_drop_rate",
    "pdop", "hdop", "vdop", "gdop", "dop_ratio",
    "solution_status", "baseline_sats", "solution_age", "fix_continuity",
    "fix_transitions", "position_variance", "cnr_variance",
    "elevation_violations", "multipath", "clock_bias",
    "iono_delay", "tropo_delay", "cycle_slips", "residual_mean", "residual_std",
    "cnr_available",
]


def plot_feature_saliency(
    model: SentinelGNSS,
    windows: dict,
    horizon: str = "5s",
    top_n: int = 15,
    out_dir: Path = FIG_DIR,
    device: Optional[torch.device] = None,
) -> None:
    """Gradient-based feature saliency (input × gradient).

    For each input feature, computes the mean absolute gradient of the loss
    with respect to that feature, averaged over the DEGRADED test samples and
    all 30 time steps.

    This is the 'vanilla saliency' method (Simonyan et al., 2014).  Higher
    saliency = the model's prediction is more sensitive to that feature.
    Top-N features are shown in a horizontal bar chart.

    Ref: Simonyan, K., Vedaldi, A., & Zisserman, A. (2014). Deep inside
         convolutional networks: Visualising image classification models and
         saliency maps. ICLR Workshop.
         https://arxiv.org/abs/1312.6034
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    d = windows["test"]
    X = torch.from_numpy(d["X"]).float().to(device)
    y = torch.from_numpy(d[f"y_{horizon}"]).long().to(device)

    DEGRADED_IDX = 2
    mask = (y == DEGRADED_IDX)
    if mask.sum() == 0:
        log.warning(
            "  No DEGRADED samples in test set; skipping saliency plot.")
        return

    X_deg = X[mask].requires_grad_(True)
    out = model(X_deg)
    logit = out[f"logits_{horizon}"][:, DEGRADED_IDX].sum()
    logit.backward()

    # Saliency: mean |grad| over samples and time steps → (n_features,)
    saliency = X_deg.grad.abs().mean(dim=(0, 1)).detach().cpu().numpy()

    top_idx = np.argsort(saliency)[-top_n:][::-1]
    top_sal = saliency[top_idx]
    top_names = [FEATURE_NAMES[i] if i < len(FEATURE_NAMES) else f"feat_{i}"
                 for i in top_idx]

    # Normalise to [0, 1]
    top_sal_norm = top_sal / top_sal.max()

    cmap = plt.get_cmap(CMAP_SEQUENTIAL)
    colours = [cmap(v) for v in top_sal_norm]

    fig, ax = plt.subplots(figsize=(FIG_DOUBLE_COL[0], max(4.5, top_n * 0.38)))
    bars = ax.barh(
        range(top_n), top_sal_norm[::-1],
        color=colours[::-1], edgecolor="white", linewidth=0.5,
    )
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(top_names[::-1], fontsize=FONT_TICK)
    ax.set_xlabel("Normalised mean |∂ DEGRADED / ∂ feature|",
                  fontsize=FONT_AXIS_LABEL, fontweight="bold")
    ax.set_title(
        f"Feature Saliency — DEGRADED Class, Horizon +{horizon}",
        fontsize=FONT_TITLE, fontweight="bold",
    )
    ax.set_xlim(0, 1.05)
    ax.tick_params(labelsize=FONT_TICK)
    plt.tight_layout()
    save_figure(fig, str(out_dir / f"feature_saliency_{horizon}"))
    plt.close(fig)


# ─── 14. Bootstrap Confidence Intervals ──────────────────────────────────────
def bootstrap_metrics(
    results: dict,
    n_boot: int = 1000,
    alpha: float = 0.05,
    random_state: int = 42,
) -> dict:
    """Compute 95% bootstrap CIs for macro-F1, MCC, and Cohen's κ.

    Bootstrap is the standard method for computing CIs on classification
    metrics when the test set is too small for analytical intervals.
    Ref: Efron & Tibshirani (1994), Chapter 13.

    Parameters
    ----------
    n_boot : Number of bootstrap resamples (1000 is the recommended minimum).
    alpha  : Significance level (0.05 → 95% CI).
    """
    rng = np.random.default_rng(random_state)
    ci = {}

    for h in HORIZONS:
        y_true = results[h]["y_true"]
        y_pred = results[h]["y_pred"]
        n = len(y_true)

        boot_f1 = []
        boot_mcc = []
        boot_kap = []

        for _ in range(n_boot):
            idx = rng.integers(0, n, size=n)
            yt = y_true[idx]
            yp = y_pred[idx]
            boot_f1.append(f1_score(yt, yp, average="macro",  zero_division=0))
            boot_mcc.append(matthews_corrcoef(yt, yp))
            boot_kap.append(cohen_kappa_score(yt, yp)
                            if len(np.unique(yt)) > 1 else 0.0)

        lo, hi = alpha / 2, 1.0 - alpha / 2
        ci[h] = {
            "macro_f1": (np.quantile(boot_f1,  lo), np.quantile(boot_f1,  hi)),
            "mcc":      (np.quantile(boot_mcc, lo), np.quantile(boot_mcc, hi)),
            "kappa":    (np.quantile(boot_kap, lo), np.quantile(boot_kap, hi)),
        }
        log.info(
            f"  Bootstrap CI ({h}):  "
            f"macro-F1=[{ci[h]['macro_f1'][0]:.3f}, {ci[h]['macro_f1'][1]:.3f}]  "
            f"MCC=[{ci[h]['mcc'][0]:.3f}, {ci[h]['mcc'][1]:.3f}]"
        )

    return ci


# ─── Master evaluation runner ─────────────────────────────────────────────────
def run_all(
    model_path: Optional[Path] = None,
    split: str = "test",
    out_dir: Path = FIG_DIR,
    windows_dir: Path = WINDOW_DIR,
    ckpt_dir: Path = CKPT_DIR,
    n_bootstrap: int = 1000,
) -> None:
    """Run the complete evaluation pipeline and save all figures.

    Parameters
    ----------
    model_path  : Path to a .pt checkpoint.  Defaults to best checkpoint.
    split       : 'val' or 'test'.
    out_dir     : Root directory for output figures.
    windows_dir : Directory containing .npz window files.
    ckpt_dir    : Checkpoint directory (used to locate training_history.json).
    n_bootstrap : Bootstrap iterations for CI computation.
    """
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s  %(message)s")
    apply_publication_style()
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Device: {device}")

    # ── Load model ────────────────────────────────────────────────────────
    if model_path is None:
        model_path = CKPT_DIR / "checkpoint_best.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"No checkpoint found at {model_path}")

    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    model = build_model(ckpt.get("config", {})).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    log.info(
        f"  Loaded model from {model_path.name}  (epoch={ckpt.get('epoch', '?')})")

    # ── Load windows ──────────────────────────────────────────────────────
    windows = load_windows(windows_dir)

    # ── Inference ─────────────────────────────────────────────────────────
    log.info(f"  Running inference on '{split}' split …")
    results = run_inference(model, windows, split=split, device=device)

    # ── Metrics ──────────────────────────────────────────────────────────
    metrics = compute_metrics(results)
    print_metrics_table(metrics, split)

    # Save metrics JSON
    metrics_path = out_dir / f"metrics_{split}.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    log.info(f"  Metrics saved → {metrics_path}")

    # ── Bootstrap CIs ────────────────────────────────────────────────────
    log.info(f"  Computing {n_bootstrap}-iteration bootstrap CIs …")
    ci = bootstrap_metrics(results, n_boot=n_bootstrap)
    ci_path = out_dir / f"bootstrap_ci_{split}.json"
    with open(ci_path, "w") as f:
        json.dump(ci, f, indent=2)

    # ── All plots ─────────────────────────────────────────────────────────
    log.info("  Generating figures …")

    plot_confusion_matrices(results,    split=split, out_dir=out_dir)
    log.info("    ✓ Confusion matrices")

    plot_roc_curves(results,            split=split, out_dir=out_dir)
    log.info("    ✓ ROC curves")

    plot_pr_curves(results,             split=split, out_dir=out_dir)
    log.info("    ✓ Precision-Recall curves")

    plot_calibration_curves(results,    split=split, out_dir=out_dir)
    log.info("    ✓ Calibration curves")

    plot_learning_curves(history_path=ckpt_dir /
                         "training_history.json", out_dir=out_dir)
    log.info("    ✓ Learning curves")

    plot_multi_horizon_comparison(metrics, out_dir=out_dir)
    log.info("    ✓ Multi-horizon comparison")

    plot_attention_heatmap(model, windows, out_dir=out_dir, device=device)
    log.info("    ✓ Attention heatmaps")

    for h in HORIZONS:
        plot_feature_saliency(model, windows, horizon=h,
                              out_dir=out_dir, device=device)
    log.info("    ✓ Feature saliency maps")

    plot_lead_time_histogram(model, windows, out_dir=out_dir, device=device)
    log.info("    ✓ Lead-time histogram")

    log.info(f"\n{'='*60}")
    log.info(f"  All evaluation artefacts saved to: {out_dir}")
    log.info(f"{'='*60}\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate SENTINEL-GNSS")
    parser.add_argument("--split",       default="test",
                        choices=["val", "test"])
    parser.add_argument("--checkpoint",  default=None,    type=Path)
    parser.add_argument("--n_bootstrap", default=1000,    type=int)
    parser.add_argument("--debug",       action="store_true",
                        help="Smoke-test: use windows_debug/ and checkpoints_debug/")
    args = parser.parse_args()

    if args.debug:
        debug_window_dir = ROOT / "data" / "processed" / "windows_debug"
        debug_ckpt_dir = ROOT / "results" / "models" / "checkpoints_debug"
        debug_ckpt = debug_ckpt_dir / "checkpoint_best.pt"
        model_path = args.checkpoint or debug_ckpt
        run_all(
            model_path=model_path,
            split=args.split,
            n_bootstrap=50,     # fast: 50 bootstrap iterations instead of 1000
            windows_dir=debug_window_dir,
            ckpt_dir=debug_ckpt_dir,
        )
    else:
        run_all(
            model_path=args.checkpoint,
            split=args.split,
            n_bootstrap=args.n_bootstrap,
        )
