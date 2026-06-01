# SENTINEL-GNSS — Results Reference (Single Source of Truth)

> **Purpose:** This file is the authoritative record of every confirmed number.
> Do not cite a figure in any paper unless it appears here or in `reviewer_experiments.json`.
> Every value below is copied directly from Run 14 (`RUN_SUMMARY.json`, generated 2026-05-31 18:06 UTC).
>
> **Legend:**
> - ✅ **CONFIRMED** — produced by a completed run, traceable to a JSON artefact.
> - ⏳ **PENDING** — experiment designed but results not yet in hand (populate when available).
> - ⚠️ **VERIFY** — external/literature claim that must be checked against the primary source before submission.

---

## 1. Run Provenance

| Item | Value |
|------|-------|
| Run ID | Run 14 |
| Generated | 2026-05-31 18:06 UTC |
| Repo | https://github.com/Jorshuare/AI-Based-Prediction-for-GNSS-Signal-Degradation |
| GPU | Tesla T4 ×2 (Kaggle) |
| PyTorch | 2.10.0+cu128 |
| Best checkpoint (full model) | epoch 10 / 65 |
| Temperature calibration T | 0.4023 |

---

## 2. Dataset & Split (✅ CONFIRMED)

| Split | Windows | CLEAN | WARNING | DEGRADED |
|-------|--------:|------:|--------:|---------:|
| Train (SMOTE, baselines only) | 112,482 | 37,494 | 37,494 | 37,494 |
| Train (no-SMOTE, DL models) | 62,413 | 11,438 | 37,494 | 13,481 |
| Validation | 18,074 | 13,708 | 3,243 | 1,123 |
| **Test** | **1,686** | **731 (43.4%)** | **746 (44.2%)** | **209 (12.4%)** |

- Full labelled dataset: **149,662 rows × 41 columns** across 12 source groups, 4 cities.
- Window: 30-second sliding window, 37 features per timestep → tensor `(N, 30, 37)`.
- Test set includes `scenario_a_r13` (293 instant-blockage windows) — first dedicated blockage test coverage.

---

## 3. Architecture & Hyperparameters (✅ CONFIRMED — from `src/models/train.py` DEFAULT_CONFIG)

| Component | Setting |
|-----------|---------|
| Input projection | 37 → d_model |
| Positional encoding | Sinusoidal (Vaswani et al., 2017) |
| Transformer encoder | 2 layers, 8 heads, d_model=128, d_ff=512 |
| LSTM | 2 layers, hidden=256 |
| Output heads | 4 (logits_5s, logits_15s, logits_30s + auxiliary logits_0s) |
| Loss | Focal loss, γ=1.0, class_weights=[1.0, 2.0, 5.0], label smoothing ε=0.1 |
| Optimiser | AdamW, lr=1e-3, weight_decay=1e-4 |
| LR schedule | 5-epoch linear warm-up → cosine decay |
| Gradient clip | max-norm 1.0 |
| Batch size | 256 |
| Early stopping | patience=50, min_epoch_for_best=15 |
| Dropout | 0.3 |

**Parameter counts (✅ CONFIRMED):**
| Model | Parameters |
|-------|-----------:|
| Transformer + LSTM (full) | 1,456,652 |
| LSTM-only | 1,026,569 |
| Transformer-only | 427,273 |

---

## 4. Main Result — Multi-Horizon (✅ CONFIRMED)

**SENTINEL-GNSS (Transformer + BiLSTM), test set, tuned thresholds + temperature scaling:**

| Horizon | Accuracy | Macro-F1 | Weighted-F1 | Cohen κ | MCC | Bootstrap 95% CI (Macro-F1) |
|---------|---------:|---------:|------------:|--------:|----:|:---------------------------:|
| **+5s** | 0.8535 | **0.8206** | 0.8523 | 0.7620 | 0.7729 | [0.798, 0.840] |
| +15s | 0.7888 | 0.7412 | 0.7906 | 0.6673 | 0.6908 | [0.717, 0.764] |
| +30s | 0.8304 | 0.7825 | 0.8311 | 0.7230 | 0.7314 | [0.758, 0.804] |

*(Bootstrap CIs = 1,000 iterations, from `evaluate.py`.)*

---

## 5. Per-Class F1 (✅ CONFIRMED)

### +5s horizon
| Class | Precision | Recall | F1 | Support |
|-------|----------:|-------:|---:|--------:|
| CLEAN | 0.868 | 0.993 | 0.927 | 731 |
| WARNING | 0.947 | 0.718 | 0.817 | 746 |
| DEGRADED | 0.623 | 0.847 | 0.718 | 209 |

### +15s horizon
| Class | Precision | Recall | F1 | Support |
|-------|----------:|-------:|---:|--------:|
| CLEAN | 0.864 | 0.981 | 0.919 | 732 |
| WARNING | 0.938 | 0.587 | 0.722 | 750 |
| DEGRADED | 0.446 | 0.843 | 0.583 | 204 |

### +30s horizon
| Class | Precision | Recall | F1 | Support |
|-------|----------:|-------:|---:|--------:|
| CLEAN | 0.860 | 0.970 | 0.911 | 732 |
| WARNING | 0.919 | 0.720 | 0.807 | 751 |
| DEGRADED | 0.550 | 0.734 | 0.629 | 203 |

> **Per-class bootstrap CIs (E3): ⏳ PENDING** — populate from `reviewer_experiments.json`.

---

## 6. Ablation Study (✅ CONFIRMED)

| Architecture | Params | Val combined stop-F1 | +5s Macro-F1 | +5s DEGRADED F1 | +5s MCC |
|--------------|-------:|---------------------:|-------------:|----------------:|--------:|
| Transformer-only | 427K | 0.8596 | 0.7672 | 0.571 | 0.7248 |
| LSTM-only | 1,027K | 0.8640 | 0.7674 | 0.645 | 0.7018 |
| **Transformer + LSTM (full)** | **1,457K** | **0.8614** | **0.8206** | **0.718** | **0.7729** |

**Multi-horizon ablation Macro-F1:**
| Architecture | +5s | +15s | +30s |
|--------------|----:|-----:|-----:|
| Transformer-only | 0.7672 | 0.7627 | 0.7012 |
| LSTM-only | 0.7674 | 0.7507 | 0.7805 |
| **Full** | **0.8206** | 0.7412 | 0.7825 |

> **Reading this table:** By Macro-F1 at +5s and by MCC at every horizon, the full model wins.
> By MCC ordering: Full (0.773) > Transformer-only (0.725) > LSTM-only (0.702).
> The Transformer-only achieves CLEAN precision = 1.000 (never confuses degraded for clean)
> but DEGRADED precision only 0.424 — it over-flags. The LSTM supplies the directional
> state that suppresses false alarms; together they give the best DEGRADED F1.

---

## 7. Baselines & Full Comparison (✅ CONFIRMED)

| Method | Architecture | Training data | +5s | +15s | +30s | +5s MCC |
|--------|--------------|---------------|----:|-----:|-----:|--------:|
| MajorityClass | trivial | — | 0.2016 | 0.0720 | 0.0716 | 0.000 |
| CNR Threshold | rule (RTCM) | — | 0.0735 | 0.0720 | 0.0716 | 0.000 |
| RandomForest | classical ML | SMOTE 112K | 0.9094 | 0.8866 | 0.8766 | 0.9148 |
| XGBoost | classical ML | SMOTE 112K | 0.9098 | 0.8983 | 0.8788 | 0.9150 |
| RandomForest | classical ML | no-SMOTE 62K | 0.9103 | 0.8910 | 0.8960 | 0.9158 |
| XGBoost | classical ML | no-SMOTE 62K | **0.9193** | 0.8962 | 0.8787 | **0.9261** |
| Transformer-only | ablation | no-SMOTE + focal | 0.7672 | 0.7627 | 0.7012 | 0.7248 |
| LSTM-only | ablation | no-SMOTE + focal | 0.7674 | 0.7507 | 0.7805 | 0.7018 |
| **SENTINEL-GNSS** | **Transformer+LSTM** | **no-SMOTE + focal** | **0.8206** | 0.7412 | 0.7825 | 0.7729 |

**SMOTE effect on classical ML (✅ CONFIRMED):**
- RandomForest: SMOTE=0.9094, no-SMOTE=0.9103, Δ = −0.0009 (negligible)
- XGBoost: SMOTE=0.9098, no-SMOTE=0.9193, Δ = −0.0095 (SMOTE *hurts*)

---

## 8. Progress Across Runs (✅ CONFIRMED)

| Metric | Run 10 | Run 12 | Run 14 | Δ (10→14) |
|--------|-------:|-------:|-------:|----------:|
| +5s Macro-F1 | 0.687 | 0.704 | **0.821** | +13.4 pts |
| +5s DEGRADED F1 | 0.274 | 0.307 | **0.718** | +44.4 pts |
| +5s WARNING F1 | ~0.67 | 0.851 | 0.817 | +15 pts |
| +5s CLEAN F1 | ~0.89 | 0.909 | 0.927 | +4 pts |
| Training DEGRADED rows | 555 | 11,996 | 13,481 | 24× |

---

## 9. Reviewer-Directed Experiments (E1–E7) — ✅ CONFIRMED (from `reviewer_experiments.json`)

> Note: the experiment cell computes DL Macro-F1 by raw argmax (0.8218) rather than the
> tuned-threshold pipeline value (0.8206). Both are legitimate; they differ only by the
> threshold-tuning step. RF reference here is the SMOTE 200-tree model (0.926).

### E1 — Permutation Shuffle Test
| Model | Original | Shuffled | Drop |
|-------|---------:|---------:|-----:|
| Transformer+LSTM | 0.8218 | 0.7897 | 0.0320 |
| RandomForest | 0.9260 | 0.8931 | 0.0329 |

**Verdict: BOTH_DROP_EQUALLY.** Shuffling the 30 timesteps within each window degrades
both models by ~3.2%. **Interpretation: temporal *ordering* is a minor contributor for
both models.** ⚠️ This means we must NOT claim the Transformer's advantage comes from
modelling temporal order — the data does not support it.

### E2 — Temporal-Feature Ablation (RandomForest)
| Configuration | Macro-F1 | CLEAN | WARNING | DEGRADED |
|---------------|---------:|------:|--------:|---------:|
| RF, all 37 features | 0.9260 | 0.9973 | 0.9581 | 0.8225 |
| RF, 28 features (9 temporal removed) | 0.9271 | 0.9966 | 0.9580 | 0.8268 |
| Δ | **−0.0012** | | | |

**Verdict:** Removing `cnr_trend, cnr_variance, fix_continuity, fix_transitions,
position_variance, sat_drop_rate, sat_visibility, sat_mean, sat_min` does **not** hurt RF.
**Interpretation: RF's strength is NOT the engineered temporal features** — it comes from
instantaneous per-timestep features (mean_cnr, num_satellites, hdop) which are individually
highly discriminative for the in-domain (Beijing) test set.

### E3 — Per-Class Bootstrap 95% CIs (DL, 1,000 iterations)
| Class | Mean F1 | 95% CI |
|-------|--------:|:------:|
| CLEAN | 0.9275 | [0.9147, 0.9407] |
| WARNING | 0.8200 | [0.7971, 0.8423] |
| DEGRADED | 0.7169 | [0.6711, 0.7621] |
| **Macro-F1** | **0.8215** | **[0.8001, 0.8430]** |

DEGRADED CI width ≈ ±0.045 reflects the modest support (n=209). Report this CI alongside
every DEGRADED number in the paper.

### E4 — Inference Latency (Tesla T4)
| Model | ms / sample | Notes |
|-------|------------:|-------|
| Transformer+LSTM | 0.0389 | 1 forward pass → +5s, +15s, +30s simultaneously; 17.81 MB |
| RandomForest | 0.4090 | 3 separate models (one per horizon) |
| **Speedup** | **10.52×** | DL is 10.5× faster on GPU |

**Strong DL deployment advantage:** a single unified 17.8 MB model serves all three
horizons in one pass, 10.5× faster than three independent tree ensembles.

### E5 — SMOTE Distribution Analysis (KL divergence)
| Distribution | CLEAN | WARNING | DEGRADED |
|--------------|------:|--------:|---------:|
| SMOTE train | 33.3% | 33.3% | 33.3% |
| no-SMOTE train | 18.3% | 60.1% | 21.6% |
| Validation | 75.8% | 17.9% | 6.2% |
| Test | 43.4% | 44.2% | 12.4% |

- KL(test ‖ SMOTE) = **0.1167**
- KL(test ‖ no-SMOTE) = **0.1692**
- Closer to test: **SMOTE**

⚠️ **This REFUTES the earlier hypothesis** that no-SMOTE wins because it is closer to test.
SMOTE's balanced distribution is in fact *nominally closer* to the test distribution, yet
SMOTE still does not improve XGBoost (Δ=−0.0095). **Correct interpretation:** with
`class_weight='balanced'` already handling imbalance, SMOTE's synthetic interpolated samples
in the 1,110-dimensional flattened space add interpolation artefacts that slightly outweigh
any distributional benefit. The practical takeaway stands — *SMOTE is unnecessary here* —
but the reason is interpolation noise, not distribution distance.

### E6 — Cross-City Generalisation (Tokyo Shinjuku, 31,236 windows, never seen in training)
| Model | Beijing Macro-F1 | Tokyo Macro-F1 | Gap | Tokyo CLEAN | Tokyo WARNING | Tokyo DEGRADED |
|-------|-----------------:|---------------:|----:|------------:|--------------:|---------------:|
| Transformer+LSTM | 0.8218 | **0.6489** | **−0.1729** | 0.9256 | 0.2683 | **0.7528** |
| RandomForest | 0.9260 | 0.6178 | −0.3082 | 0.9896 | 0.7159 | **0.1478** |

**HEADLINE FINDING (Paper 1 + Paper 3):**
- DL generalises better overall cross-city (0.649 vs 0.618) and **retains 79%** of its
  Beijing performance vs RF's 67%.
- **On the safety-critical DEGRADED class, DL holds at 0.753 while RF collapses to 0.148.**
  The tree ensemble memorises Beijing-specific feature thresholds and cannot detect
  degradation in a new city; the neural model learns a transferable degradation concept.
- Trade-off (disclose honestly): DL loses WARNING cross-city (0.268) where RF holds it
  (0.716). For an AV safety system, DEGRADED (loss-of-fix) is the critical class.

⏳ **TODO:** add Tokyo per-class **support counts** (Shinjuku is ~92% CLEAN, so DEGRADED
support is small — report n to contextualise the F1 contrast).

### E7 — Calibration (ECE) — ⚠️ INVALID RUN, MUST RE-RUN
| Metric | Value |
|--------|------:|
| Temperature loaded | 1.0 (❌ key lookup failed — should be 0.4023) |
| ECE raw | 0.1139 |
| ECE "scaled" | 0.1139 (identical — T=1.0 is a no-op) |

**The E7 cell failed to read the temperature from `metrics_test.json`, so it applied T=1.0
(no scaling). The before/after comparison is therefore meaningless.** The only valid number
is raw ECE = 0.114 (moderate, not <0.05). **DO NOT claim the model is well-calibrated yet.**
**ACTION:** re-run E7 with `T=0.4023` hard-set, recompute ECE before/after, then update.

---

## 10. Figures Generated (✅ CONFIRMED — in `results/figures/`)

All saved as both `.pdf` (vector, for LaTeX) and `.png` (300 DPI):

1. `confusion_matrices_test` — per-class confusion at each horizon
2. `roc_curves_test` — one-vs-rest ROC
3. `pr_curves_test` — precision-recall (preferred for imbalance)
4. `calibration_curves_test` — reliability diagram
5. `learning_curves` — train/val loss + F1 across epochs
6. `multi_horizon_comparison` — Macro-F1 vs horizon
7. `attention_heatmap_clean` / `_warning` / `_degraded` — Transformer attention
8. `feature_saliency_5s` / `_15s` / `_30s` — gradient saliency per feature
9. `lead_time_histogram` — seconds of advance warning before DEGRADED events

> **Lead-time median value: ⏳ PENDING** — read directly from `lead_time_histogram` data; this is the headline engineering number for Paper 1.

---

## 11. Claims That MUST Be Verified Before Submission (⚠️ VERIFY)

1. **Liu et al. (ION GNSS+ 2023), "99.41% accuracy", GRU classifier** — confirm the exact citation, venue, year, and reported metric. Do not state a competitor's number you have not read in the primary source.
2. **"Zero papers on cross-receiver / cross-city GNSS degradation prediction"** — soften to *"to the best of our knowledge, after a systematic search of [databases], we found no prior work that …"*. Never assert an absolute absence as fact.
3. **GPS Solutions impact factor (4.9)** — verify the current JCR value at submission time.
4. **Dataset epoch counts per source** — regenerate from the final committed CSVs before writing Paper 4's table.
