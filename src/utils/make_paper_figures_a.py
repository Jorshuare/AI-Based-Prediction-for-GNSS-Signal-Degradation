"""
Paper A figure preparation — SENTINEL GPS Solutions.

Strategy:
  - Copy publication-quality existing figures from results/ to papers/paper_a/figures/
  - All figures reuse the existing high-quality outputs; no regeneration needed
  - New figures (if any) generated with cividis colormap to match existing style

Usage:
    python src/utils/make_paper_figures_a.py

Outputs in papers/paper_a/figures/ :
    fig_architecture.pdf/png       — SENTINEL architecture block diagram
    fig_proactive.pdf/png          — Proactive vs reactive timeline
    fig_pipeline.pdf/png           — Data/training pipeline
    fig_model_comparison.pdf/png   — All-model comparison @ 5s horizon
    fig_multi_horizon.pdf/png      — Macro-F1 + DEGRADED Recall by horizon
    fig_perclass_f1.pdf/png        — Per-class F1 at 3 horizons
    fig_ablation.pdf/png           — Ablation: Transformer-only / LSTM-only / Full
    fig_cross_city.pdf/png         — Cross-city generalisation
    fig_cross_city_gap.pdf/png     — Domain gap visualisation
    fig_confusion_matrices.png     — 6-panel confusion matrices (row-norm)
    fig_saliency.png               — Gradient saliency top-15 features @ 5s
    fig_roc.png                    — ROC curves on test set
    fig_persistence.pdf/png        — Persistence paradox analysis
    fig_class_distribution.pdf/png — Class label distribution
    fig_ensemble.pdf/png           — Ensemble fusion comparison
"""

import shutil
from pathlib import Path
import sys

ROOT     = Path(__file__).resolve().parents[2]
SRC_PFX  = ROOT / "results" / "paper_figures"   # existing publication figures
SRC_FIG  = ROOT / "results" / "figures"          # raw experiment outputs
DST      = ROOT / "papers" / "paper_a" / "figures"

DST.mkdir(parents=True, exist_ok=True)

# ── (source_dir, source_filename, destination_filename) ─────────────────────
COPIES = [
    # Architecture & motivation
    (SRC_PFX, "fig14_architecture.pdf",          "fig_architecture.pdf"),
    (SRC_PFX, "fig14_architecture.png",          "fig_architecture.png"),
    (SRC_PFX, "fig13_reactive_vs_proactive.pdf", "fig_proactive.pdf"),
    (SRC_PFX, "fig13_reactive_vs_proactive.png", "fig_proactive.png"),
    (SRC_PFX, "fig15_pipeline.pdf",              "fig_pipeline.pdf"),
    (SRC_PFX, "fig15_pipeline.png",              "fig_pipeline.png"),

    # Main quantitative results
    (SRC_PFX, "fig03_model_comparison.pdf",      "fig_model_comparison.pdf"),
    (SRC_PFX, "fig03_model_comparison.png",      "fig_model_comparison.png"),
    (SRC_PFX, "fig01_multihorizon.pdf",          "fig_multi_horizon.pdf"),
    (SRC_PFX, "fig01_multihorizon.png",          "fig_multi_horizon.png"),
    (SRC_PFX, "fig02_perclass_f1.pdf",           "fig_perclass_f1.pdf"),
    (SRC_PFX, "fig02_perclass_f1.png",           "fig_perclass_f1.png"),

    # Ablation
    (SRC_PFX, "fig04_ablation.pdf",              "fig_ablation.pdf"),
    (SRC_PFX, "fig04_ablation.png",              "fig_ablation.png"),

    # Cross-city
    (SRC_PFX, "fig05_crosscity_degraded.pdf",    "fig_cross_city.pdf"),
    (SRC_PFX, "fig05_crosscity_degraded.png",    "fig_cross_city.png"),
    (SRC_PFX, "fig06_crosscity_gap.pdf",         "fig_cross_city_gap.pdf"),
    (SRC_PFX, "fig06_crosscity_gap.png",         "fig_cross_city_gap.png"),

    # Confusion matrices & analysis (PNG rasters — 300 dpi, suitable for journal)
    (SRC_FIG, "confusion_matrices_test.png",     "fig_confusion_matrices.png"),
    (SRC_FIG, "feature_saliency_5s.png",         "fig_saliency.png"),
    (SRC_FIG, "roc_curves_test.png",             "fig_roc.png"),

    # Discussion / supplementary
    (SRC_PFX, "fig17_persistence.pdf",           "fig_persistence.pdf"),
    (SRC_PFX, "fig17_persistence.png",           "fig_persistence.png"),
    (SRC_PFX, "fig11_class_distribution.pdf",    "fig_class_distribution.pdf"),
    (SRC_PFX, "fig11_class_distribution.png",    "fig_class_distribution.png"),
    (SRC_PFX, "fig16_ensemble.pdf",              "fig_ensemble.pdf"),
    (SRC_PFX, "fig16_ensemble.png",              "fig_ensemble.png"),
    (SRC_PFX, "fig12_latency.pdf",               "fig_latency.pdf"),
    (SRC_PFX, "fig12_latency.png",               "fig_latency.png"),
    (SRC_PFX, "fig09_degraded_progress.pdf",     "fig_degraded_progress.pdf"),
    (SRC_PFX, "fig09_degraded_progress.png",     "fig_degraded_progress.png"),
    (SRC_PFX, "fig10_dataset_composition.pdf",   "fig_dataset_composition.pdf"),
    (SRC_PFX, "fig10_dataset_composition.png",   "fig_dataset_composition.png"),
]

ok = skip = 0
for src_dir, src_name, dst_name in COPIES:
    src = src_dir / src_name
    dst = DST / dst_name
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  [OK]   {dst_name}")
        ok += 1
    else:
        print(f"  [SKIP] {src_name} not found")
        skip += 1

print(f"\nPaper A figures ready: {ok} copied, {skip} skipped -> {DST}")
