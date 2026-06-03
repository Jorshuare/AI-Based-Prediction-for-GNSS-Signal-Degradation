# SENTINEL-GNSS — Run Summary
**Generated:** 2026-06-03 10:17 UTC  
**Repo:** https://github.com/Jorshuare/AI-Based-Prediction-for-GNSS-Signal-Degradation  

## Training Summary (best checkpoint by combined stop-F1 across 3 horizons)
- **Transformer + LSTM (full)**: best epoch 10/65, best combined stop-MacroF1 = 0.8614
- **LSTM-only ablation**: best epoch 20/70, best combined stop-MacroF1 = 0.864
- **Transformer-only ablation**: best epoch 12/75, best combined stop-MacroF1 = 0.8596

## Complete Comparison Table — Test Set MacroF1

| Method | Data | +5s MacroF1 | +15s MacroF1 | +30s MacroF1 | +5s MCC |
|---|---|---|---|---|---|
| MajorityClass | — | 0.2016 | 0.0720 | 0.0716 | 0.000 |
| CNR Threshold | — | 0.0735 | 0.0720 | 0.0716 | 0.000 |
| RandomForest (SMOTE) | SMOTE 112K | 0.9094 | 0.8866 | 0.8766 | 0.9148 |
| XGBoost (SMOTE) | SMOTE 112K | 0.9098 | 0.8983 | 0.8788 | 0.9150 |
| RandomForest (no-SMOTE) | no-SMOTE 62K | 0.9103 | 0.8910 | 0.8960 | 0.9158 |
| XGBoost (no-SMOTE) | no-SMOTE 62K | 0.9193 | 0.8962 | 0.8787 | 0.9261 |
| Transformer-only | no-SMOTE + focal | 0.7672 | 0.7627 | 0.7012 | 0.7248 |
| LSTM-only | no-SMOTE + focal | 0.7674 | 0.7507 | 0.7805 | 0.7018 |
| **Transformer + LSTM (SENTINEL-GNSS)** | no-SMOTE + focal | 0.8206 | 0.7412 | 0.7825 | 0.7729 |

## SMOTE Effect on Classical ML
- **RandomForest**: SMOTE=0.9094  no-SMOTE=0.9103  Δ=-0.0009
- **XGBoost**: SMOTE=0.9098  no-SMOTE=0.9193  Δ=-0.0095

## Per-Model Detail
### Transformer + LSTM (full model)
| Horizon | Accuracy | MacroF1 | WtF1 | κ | MCC |
|---|---|---|---|---|---|
| +5s | 0.8535 | **0.8206** | 0.8523 | 0.7620 | 0.7729 |
| +15s | 0.7888 | **0.7412** | 0.7906 | 0.6673 | 0.6908 |
| +30s | 0.8304 | **0.7825** | 0.8311 | 0.7230 | 0.7314 |

**Per-class @ +5s:**
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| CLEAN | 0.868 | 0.993 | 0.927 | 731 |
| WARNING | 0.947 | 0.718 | 0.817 | 746 |
| DEGRADED | 0.623 | 0.847 | 0.718 | 209 |

### LSTM-only ablation
| Horizon | Accuracy | MacroF1 | WtF1 | κ | MCC |
|---|---|---|---|---|---|
| +5s | 0.8031 | **0.7674** | 0.8052 | 0.6877 | 0.7018 |
| +15s | 0.7942 | **0.7507** | 0.8010 | 0.6751 | 0.6924 |
| +30s | 0.8286 | **0.7805** | 0.8308 | 0.7196 | 0.7236 |

**Per-class @ +5s:**
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| CLEAN | 0.881 | 0.944 | 0.911 | 731 |
| WARNING | 0.890 | 0.642 | 0.746 | 746 |
| DEGRADED | 0.507 | 0.885 | 0.645 | 209 |

### Transformer-only ablation
| Horizon | Accuracy | MacroF1 | WtF1 | κ | MCC |
|---|---|---|---|---|---|
| +5s | 0.8126 | **0.7672** | 0.8280 | 0.7081 | 0.7248 |
| +15s | 0.8126 | **0.7627** | 0.8285 | 0.7064 | 0.7213 |
| +30s | 0.7550 | **0.7012** | 0.7808 | 0.6268 | 0.6550 |

**Per-class @ +5s:**
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| CLEAN | 1.000 | 0.936 | 0.967 | 731 |
| WARNING | 0.880 | 0.676 | 0.764 | 746 |
| DEGRADED | 0.424 | 0.871 | 0.571 | 209 |


## Data & Split Summary
- **Train (SMOTE):** 112,482 — CLEAN=37,494 WARNING=37,494 DEGRADED=37,494
- **Train (no-SMOTE):** 62,413 — CLEAN=11,438 WARNING=37,494 DEGRADED=13,481
- **Val:** 18,074 — CLEAN=13,708 WARNING=3,243 DEGRADED=1,123
- **Test:** 1,686 — CLEAN=731 WARNING=746 DEGRADED=209

## Figures Generated
- attention_heatmap_clean.png
- attention_heatmap_degraded.png
- attention_heatmap_warning.png
- calibration_curves_test.png
- confusion_matrices_test.png
- feature_saliency_15s.png
- feature_saliency_30s.png
- feature_saliency_5s.png
- lead_time_histogram.png
- learning_curves.png
- multi_horizon_comparison.png
- pr_curves_test.png
- roc_curves_test.png