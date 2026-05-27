# SENTINEL-GNSS: Next Steps Roadmap

**Updated:** May 27, 2026
**Current best result:** Run 10 — MacroF1 = 0.687 (+5s), MCC = 0.761
**Next run:** Run 12 — adds HK Deep + Harsh urban datasets, ~30,000+ new rows

---

## How to Run (Steps 1 → 2 → 3 → 4)

> Run from the project root: `C:\Users\Joel\Desktop\Beihang University\Team-Pilot-Project`
>
> **First time?** Run the smoke-test below to verify the full pipeline works in ~2 minutes before committing to the full run.

---

### Smoke-test (end-to-end in ~2 min — run this first)

```powershell
# Uses 500 rows/source, 5 epochs, outputs to debug dirs — never overwrites real data
python -m src.models.feature_prep --debug
python -m src.models.train --debug
python -m src.models.evaluate --debug
```

If all three complete without errors, the full pipeline is confirmed working.

---

### Step 1 — Install dependencies

```powershell
# Check your GPU / CUDA driver version first:
nvidia-smi
```

Then install PyTorch for your driver (Python 3.13 requires cu118 or cu124):

```powershell
# CUDA 12.4+ (nvidia-smi shows 12.4 or higher):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# CUDA 11.8 (nvidia-smi shows 11.8 – 12.3):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CPU-only (no NVIDIA GPU):
pip install torch torchvision torchaudio

# All other dependencies:
pip install -r requirements.txt
```

### Step 2 — Process new datasets (Deep + Harsh) — Run 12 prerequisite

```powershell
# Process the two new HK urban datasets
python src/processing/process_all_datasets.py --source urbannav_deep
python src/processing/process_all_datasets.py --source urbannav_harsh

# Re-combine all sources into labelled CSV
python src/processing/process_all_datasets.py --combine
```

Expected output:
- `data/processed/urbannav/urbannav_deep_features.csv` — ~14,000 rows
- `data/processed/urbannav/urbannav_harsh_features.csv` — ~30,000 rows
- `data/labelled/sentinel_gnss_labelled.csv` — ~130,000+ rows

Verify sources are present:
```powershell
python -c "
import pandas as pd
df = pd.read_csv('data/labelled/sentinel_gnss_labelled.csv')
print(df['source'].value_counts())
# Should include urbannav_deep_* and urbannav_harsh_* sources
"
```

### Step 3 — Rebuild feature windows (force-rebuild when dataset changes)

```powershell
python -m src.models.feature_prep --force
```

Output: `data/processed/windows/{train,val,test}.npz` + `data/processed/scaler.pkl`

After rebuild, check DEGRADED count in training set:
```powershell
python -c "
import numpy as np
d = np.load('data/processed/windows/train.npz')
import collections
print('y_5s dist:', collections.Counter(d['y_5s'].tolist()))
# DEGRADED (class 2) should be >> 555 (before SMOTE)
"
```

### Step 4 — Train (Run 12)

```powershell
# Full Transformer-LSTM:
python -m src.models.train

# Ablation: LSTM-only (no Transformer encoder):
python -m src.models.train --arch lstm_only

# Ablation: Transformer-only (no LSTM):
python -m src.models.train --arch transformer_only
```

Checkpoints saved to `results/models/checkpoints/`:
- `checkpoint_best.pt` ← best val macro-F1
- `checkpoint_epoch_NNN.pt` ← periodic (every 10 epochs)
- `training_history.json` ← loss + F1 per epoch
- `config.json` ← hyper-parameters used

### Step 5 — Evaluate all three architectures

```powershell
# Full model:
python -m src.models.evaluate --tune_thresholds --temperature_scaling

# Ablation models (each reads its own checkpoints_{model_type}/ directory):
python -m src.models.evaluate --model_type lstm_only       --tune_thresholds
python -m src.models.evaluate --model_type transformer_only --tune_thresholds

# All baselines (loads same test.npz as neural net):
python -m src.models.baselines --include_ablations
```

All figures saved to `results/figures/` as PDF (vector) + PNG (300 DPI).

---

## Completed ✅

### Data Pipeline
- [x] Scenarios A–E, Supervisor Vehicle/Drone processed → CSV
- [x] UrbanNav HK Medium (10 receivers) processed → CSV
- [x] UrbanNav HK Tunnel (10 receivers) processed → CSV  ← critical for DEGRADED class
- [x] Tokyo Odaiba (Trimble + u-blox) processed → CSV
- [x] Tokyo Shinjuku (Trimble + u-blox) processed → CSV
- [x] NCLT Ann Arbor (2 sessions) processed → CSV
- [x] Oxford RobotCar (2 traversals) processed → CSV
- [x] Combined dataset: **97,393 rows** across 10 source groups (pre-Deep/Harsh)
- [x] NMEA no-fix bug fixed — blockage epochs (quality=0) captured as DEGRADED
- [x] Session-based 70/15/15 split (seed=42) — prevents temporal data leakage
- [x] SPLIT_REASSIGN mechanism — moves high-DEGRADED sessions to training

### Model Architecture (Run 10/11 final config)
- [x] Transformer encoder: 2 layers, 8 heads, d_model=128, d_ff=512
- [x] LSTM decoder: 2 layers, hidden=256
- [x] 37 features: 33 signal + cnr_available + pdop_delta + hdop_delta + receiver_tier
- [x] 3 output heads (t+5s, t+15s, t+30s) + 1 aux head (t+0s, weight=0.3)
- [x] Focal loss γ=1.0 + class weights [1.0, 2.0, 5.0] for [CLEAN, WARNING, DEGRADED]
- [x] Label smoothing ε=0.1
- [x] SMOTE on training set only (strategy="auto")
- [x] Constrained threshold tuning: FPR caps 5s≤0.15, 15s≤0.20, 30s≤0.25
- [x] Temperature calibration (Guo et al. 2017) — Run 11

### Results (Run 10, checkpoint_best.pt, epoch 23 of 73)
- [x] +5s: Accuracy=0.8528, MacroF1=0.6868, MCC=0.7614, CI=[0.658, 0.715]
- [x] +15s: Accuracy=0.7980, MacroF1=0.6330, MCC=0.6949, CI=[0.608, 0.657]
- [x] +30s: Accuracy=0.8262, MacroF1=0.6309, MCC=0.7176, CI=[0.608, 0.654]
- [x] Best val MacroF1=0.7768
- [x] Ablation val results: lstm_only=0.7898, transformer_only=0.7552

### Documentation
- [x] `DATASET_PROCESSING_REPORT.md` — full feature/label justification
- [x] `PAPER_TOPICS.md` — 4-paper publication roadmap
- [x] All model source files documented with references

---

## In Progress / Run 12 Prerequisites 🔄

- [ ] **Process UrbanNav HK-Deep-Urban-1** (Whampoa, 10 receivers) → Phase 1 ✅ (code added)
- [ ] **Process UrbanNav HK-Harsh-Urban-1** (Mong Kok, 10 receivers) → Phase 1 ✅ (code added)
- [ ] **Rebuild combined dataset + windows** with Deep+Harsh included
- [ ] **Run 12 training** with expanded DEGRADED/WARNING training pool

---

## Known Issues to Address 🐛

### Issue 1: DEGRADED class bottleneck (primary model weakness)
- **Problem:** DEGRADED F1 at +5s = 0.261. Only 55 test windows (4.3% of test).
- **Root cause:** The test set is campus (Beijing) data only, biased to Scenarios B/C (mild WARNING). Scenario A/E have very few test windows.
- **Fix (Run 12):** Add Deep+Harsh to training. DEGRADED training rows grow from ~555 → ~5,000+.
- **Expected improvement:** DEGRADED F1 at +5s → 0.40–0.55.

### Issue 2: Val-test MacroF1 gap (9 points)
- **Problem:** Best val MacroF1=0.7768 vs test MacroF1=0.6868 (9-point gap).
- **Root cause:** Val uses balanced class subset (500/class) for early stopping; test is naturally imbalanced (52.5% CLEAN, 43.3% WARNING, 4.3% DEGRADED).
- **This is NOT a bug** — it reflects the real deployment challenge.
- **Fix in paper:** Document explicitly. Val metric = "balanced performance ceiling". Test metric = "real-world performance". Both are important.

### Issue 3: Ablation metrics look identical in Colab output
- **Problem:** All three architectures (full, lstm_only, transformer_only) may show same test metrics.
- **Root cause:** The ablation checkpoint evaluation JSON files may not exist yet. `evaluate.py` saves to `metrics_test_lstm_only.json` correctly — they just haven't been run yet.
- **Fix:** Run `python -m src.models.evaluate --model_type lstm_only` and `--model_type transformer_only` separately to generate their metrics files.

### Issue 4: DEGRADED precision still low (false alarms)
- **Problem:** DEGRADED precision = 0.168 at +5s (many false alarms).
- **Root cause:** With only 55 DEGRADED test cases, even a few false alarms dominate the precision metric.
- **Fix (Run 12):** More natural DEGRADED training examples should improve precision. After retraining:
  - If DEGRADED precision > 0.40: reduce class weight from 5.0 → 3.5
  - If DEGRADED precision < 0.30: keep 5.0

---

## Run 12 — Full Colab Instructions

Run in this exact order:

```bash
# === Step 1: Process new datasets (on local machine, upload results) ===
python src/processing/process_all_datasets.py --source urbannav_deep
python src/processing/process_all_datasets.py --source urbannav_harsh

# === Step 2: Rebuild combined CSV + windows ===
python src/processing/process_all_datasets.py --combine
python -m src.models.feature_prep --force

# Verify DEGRADED count increased:
python -c "
import numpy as np, collections
d = np.load('data/processed/windows/train.npz')
print('y_5s before SMOTE:', collections.Counter(d['y_5s'].tolist()))
# Expect DEGRADED (2) >> 555
"

# === Step 3: Train full model ===
python -m src.models.train
# Expected: best val MacroF1 should improve from 0.7768

# === Step 4: Run ablations ===
python -m src.models.train --arch lstm_only
python -m src.models.train --arch transformer_only

# === Step 5: Evaluate ===
python -m src.models.evaluate --tune_thresholds --temperature_scaling
python -m src.models.evaluate --model_type lstm_only       --tune_thresholds
python -m src.models.evaluate --model_type transformer_only --tune_thresholds

# === Step 6: Baselines (comparison table) ===
python -m src.models.baselines --include_ablations
```

### Class weight tuning for Run 12

After seeing DEGRADED precision from Run 12:
- **If precision > 0.40:** Reduce to `class_weights=[1.0, 2.0, 3.5]` in `train.py` DEFAULT_CONFIG
- **If precision < 0.30:** Keep `[1.0, 2.0, 5.0]`
- **If false-alarm rate (FPR) for DEGRADED is > 10%:** Tighten threshold cap in `tune_thresholds_constrained()` in evaluate.py

---

## Phase 5 Analysis Produced by evaluate.py

| #   | Figure                                | Justification                                        | Reference                        |
| --- | ------------------------------------- | ---------------------------------------------------- | -------------------------------- |
| 1   | Confusion matrices (raw + normalised) | Per-class recall, safety-critical for DEGRADED       | Sokolova & Lapalme (2009)        |
| 2   | Per-class metrics table               | P/R/F1/support per class × horizon                   | Manning et al. (2008)            |
| 3   | Overall metrics (acc/F1/κ/MCC)        | MCC is best single metric for imbalanced multi-class | Chicco & Jurman (2020)           |
| 4   | ROC curves (OvR)                      | Threshold-independent discriminability               | Fawcett (2006)                   |
| 5   | Precision-Recall curves               | More informative than ROC for minority class         | Davis & Goadrich (2006)          |
| 6   | Calibration curves                    | Validates P(DEGRADED) as a usable risk score         | Niculescu-Mizil & Caruana (2005) |
| 7   | Learning curves                       | Diagnoses overfitting / underfitting                 | Standard practice                |
| 8   | Multi-horizon comparison              | Shows prediction difficulty vs look-ahead time       | Paper 1 main result              |
| 9   | Per-dataset heatmap                   | Cross-receiver / cross-city generalisation           | Papers 2 & 3                     |
| 10  | Per-scenario breakdown                | Validates model on each degradation type             | Paper 1 ablation                 |
| 11  | Lead-time histogram                   | "How many seconds warning?" — engineering value      | Paper 1 key claim                |
| 12  | Attention heatmaps                    | Mechanistic interpretability of Transformer          | Vaswani et al. (2017)            |
| 13  | Feature saliency (gradient)           | Which features drive the prediction                  | Simonyan et al. (2014)           |
| 14  | Bootstrap 95% CI                      | Uncertainty quantification on all scalar metrics     | Efron & Tibshirani (1994)        |

---

## Feature NaN Handling Reference

| Feature                 | NaN % | Source             | Fix applied                         |
| ----------------------- | ----- | ------------------ | ----------------------------------- |
| `lat`, `lon`            | 54%   | RINEX-only sources | **Excluded from model**             |
| `alt`                   | 54%   | RINEX-only sources | Session-median imputation           |
| `lat_std`, `lon_std`    | 85%   | No GST for most    | hdop × 2.5 proxy                    |
| C/N0 group (5 features) | ~10%  | NCLT + Oxford      | Zero-fill + `cnr_available`=0 flag  |
| DOP group (5 features)  | ~45%  | RINEX-only sources | 30/√N satellite-count approximation |
| All others              | < 5%  | —                  | Forward-fill within session         |

---

## References

- Bergmeir & Benitez (2012). On the use of cross-validation for time series predictor evaluation. Neural Networks, 32, 182–192. ← temporal split justification
- Chawla et al. (2002). SMOTE: Synthetic minority over-sampling technique. JAIR, 16, 321–357.
- Chicco & Jurman (2020). The advantages of the Matthews correlation coefficient (MCC) over F1 score. BMC Genomics, 21, 6.
- Guo et al. (2017). On calibration of modern neural networks. ICML. ← temperature scaling
- Hsu et al. (2023). UrbanNav: An open-sourced multisensory dataset. NAVIGATION, 70(1). doi:10.33012/navi.602
- Lin et al. (2017). Focal loss for dense object detection. ICCV. arXiv:1708.02002
- Loshchilov & Hutter (2019). Decoupled weight decay regularization. ICLR. ← AdamW
- Müller et al. (2019). When does label smoothing help? NeurIPS.
- Vaswani et al. (2017). Attention is all you need. NeurIPS. ← Transformer architecture
