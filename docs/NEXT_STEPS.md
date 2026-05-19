# SENTINEL-GNSS: Next Steps Roadmap

**Updated:** May 18, 2026
**Data processing:** COMPLETE — all 8 sources processed and combined.
**Model files:** COMPLETE — all 5 model files created.

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

Then install PyTorch for your driver (Python 3.13 requires cu118 or cu124 — cu121 has no py313 wheels):

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

### Step 2 — Build feature windows _(one-time; re-run with `--force` to rebuild)_

```powershell
python -m src.models.feature_prep
```

Output: `data/processed/windows/{train,val,test}.npz` + `data/processed/scaler.pkl`

### Step 3 — Train

```powershell
# Fresh run:
python -m src.models.train

# Resume from last checkpoint (if interrupted):
python -m src.models.train --resume
```

Checkpoints saved to `results/models/checkpoints/`:

- `checkpoint_best.pt` ← best val macro-F1
- `checkpoint_epoch_NNN.pt` ← periodic (every 10 epochs)
- `training_history.json` ← loss + F1 per epoch
- `config.json` ← hyper-parameters used

### Step 4 — Evaluate

```powershell
# Test set (default):
python -m src.models.evaluate

# Validation set:
python -m src.models.evaluate --split val

# Specific checkpoint:
python -m src.models.evaluate --checkpoint results/models/checkpoints/checkpoint_best.pt
```

All figures saved to `results/figures/` as PDF (vector) + PNG (300 DPI).

---

## Completed ✅

- [x] Scenarios A–E, Supervisor Vehicle/Drone processed → CSV
- [x] UrbanNav HK Medium + Tunnel (10 receivers each) processed → CSV
- [x] Tokyo Odaiba (Trimble + u-blox) processed → CSV
- [x] NCLT Ann Arbor (2 sessions) processed → CSV
- [x] Oxford RobotCar (2 traversals) processed → CSV
- [x] Combined dataset: **66,128 rows**, session-based 70/15/15 split (seed=42)
- [x] NMEA no-fix bug fixed — blockage epochs (quality=0) now captured as DEGRADED
- [x] `DATASET_PROCESSING_REPORT.md` — full feature/label justification (in docs/)
- [x] **`src/models/plot_config.py`** — single source of truth for all figures
- [x] **`src/models/feature_prep.py`** — imputation, windowing (T=30), SMOTE
- [x] **`src/models/transformer_lstm.py`** — Transformer-LSTM + FocalLoss
- [x] **`src/models/train.py`** — full training loop with checkpointing
- [x] **`src/models/evaluate.py`** — 14 evaluation analyses with references
- [x] Root-level MD files moved to `docs/`
- [x] `requirements.txt` created

---

## Phase 4: Model Files Summary

| File                  | Purpose             | Key design choices                                                    |
| --------------------- | ------------------- | --------------------------------------------------------------------- |
| `plot_config.py`      | All figure settings | cividis primary; Okabe-Ito class colours; min 14pt fonts; IEEE widths |
| `feature_prep.py`     | Data pipeline       | 34 features; DOP-proxy imputation; MinMax scaler (train only); SMOTE  |
| `transformer_lstm.py` | Architecture        | Transformer (2 layers, 4 heads) → LSTM (2×128) → 3 output heads       |
| `train.py`            | Training            | AdamW + cosine LR; focal loss γ=2; early stopping patience=20; AMP    |
| `evaluate.py`         | Evaluation          | 14 analyses; bootstrap 95% CI; all figures publication-ready          |

---

## Phase 5: Evaluation Analyses Produced by evaluate.py

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

## Phase 6: NaN Feature Handling Reference

| Feature                 | NaN % | Source             | Fix applied                         |
| ----------------------- | ----- | ------------------ | ----------------------------------- |
| `lat`, `lon`            | 54%   | RINEX-only sources | **Excluded from model**             |
| `alt`                   | 54%   | RINEX-only sources | Session-median imputation           |
| `lat_std`, `lon_std`    | 85%   | No GST for most    | hdop × 2.5 proxy                    |
| C/N0 group (5 features) | ~10%  | NCLT + Oxford      | Zero-fill + `cnr_available`=0 flag  |
| DOP group (5 features)  | ~45%  | RINEX-only sources | 30/√N satellite-count approximation |
| All others              | < 5%  | —                  | Forward-fill within session         |

---

## Phase 7: Ablation Studies (Paper 1)

Run by modifying `--arch` flag (to be implemented) or editing `DEFAULT_CONFIG` in `train.py`:

| Variant            | Change                               | Expected ΔMacro-F1 |
| ------------------ | ------------------------------------ | ------------------ |
| Full model         | Transformer(2L) → LSTM(2L)           | Baseline           |
| LSTM-only          | Remove Transformer encoder           | −3 to −8%          |
| Transformer-only   | Remove LSTM (use CLS token)          | −2 to −5%          |
| Random Forest      | sklearn RF on flattened windows      | −10 to −20%        |
| Threshold baseline | Single-feature threshold on mean_cnr | −30 to −40%        |

---

## Phase 8: Missing Data / Future Work

| Item                                 | Priority    | Notes                                                   |
| ------------------------------------ | ----------- | ------------------------------------------------------- |
| Propagate source metadata per window | HIGH        | Needed for per-dataset and per-scenario breakdown plots |
| Tokyo Shinjuku                       | Low         | No rover RINEX; skip unless data located                |
| NCLT additional sessions             | Low         | 2012-01-08, 2012-04-29 etc. available                   |
| Oxford additional traversals         | Low         | Multiple traversals available                           |
| Paper writing                        | **HIGHEST** | Start after first training run completes                |

### Why Tokyo Shinjuku Was NOT Processed

~~Only the base station OBS file exists (`base_trimble.obs`). The rover file is missing.~~
**Now processed** — `rover_trimble.obs` and `rover_ublox.obs` added; Shinjuku runs through the same pipeline as Odaiba.

---

## Phase 2: Model Training

### Task 2.1 — Feature Preparation

**File to create:** `src/models/feature_prep.py`

Key decisions to implement:

1. **Drop `lat`, `lon` from model inputs** — raw coordinates cause geographic overfitting
2. **Impute `alt` NaN** → fill with training median (~50 m)
3. **Impute `lat_std`, `lon_std` NaN** → `hdop × 2.5` (DOP-to-error proxy, ±3 m)
4. **Scale all features to [0,1]** using training-set min/max — save `scalers.pkl` for inference
5. **SMOTE on training set only** — target 20% WARNING, 10% DEGRADED in balanced set
6. **Create 30-second sliding windows** → `(batch, 30, 33)` input tensors

Expected training input shape: `(N, 30, 33)` — 30 time steps, 33 features (35 minus lat/lon)

---

### Task 2.2 — Transformer-LSTM Architecture

**File to create:** `src/models/transformer_lstm.py`

Architecture specification (from paper design):

```
Input:     (batch, 30, 33)
           ↓
Positional encoding (sinusoidal, seq_len=30)
           ↓
Transformer Encoder:
  - 4 attention heads
  - d_model = 64
  - 2 layers
  - FFN dim = 256
  - dropout = 0.1
           ↓
Reshape for LSTM: (batch, 30, 64)
           ↓
LSTM Decoder:
  - 2 layers
  - hidden_dim = 128
  - dropout = 0.1
           ↓
Take last hidden state: (batch, 128)
           ↓
3 parallel output heads:
  Head_t5:  Linear(128 → 3) + Softmax  → P(CLEAN, WARNING, DEGRADED) at t+5s
  Head_t15: Linear(128 → 3) + Softmax  → P(CLEAN, WARNING, DEGRADED) at t+15s
  Head_t30: Linear(128 → 3) + Softmax  → P(CLEAN, WARNING, DEGRADED) at t+30s
```

---

### Task 2.3 — Training Pipeline

**File to create:** `src/models/train.py`

Hyperparameters:

- Optimizer: `AdamW`, lr = 1e-3, weight_decay = 1e-4
- Scheduler: `CosineAnnealingLR`, T_max = 100
- Epochs: 100, early stopping patience = 15
- Batch size: 64
- Loss: Focal Loss, γ = 2.0
- Class weights: `{0: 1.0, 1: 2.5, 2: 5.0}`
- Seed: 42

---

### Task 2.4 — Evaluation & Analysis

Report for each of 3 prediction horizons (t+5s, t+15s, t+30s):

- Precision, Recall, F1 per class (CLEAN / WARNING / DEGRADED)
- Macro-F1
- AUC-ROC (one-vs-rest)
- Confusion matrix

Additional analyses for papers:

- **Lead time plot** — histogram of how many seconds before actual DEGRADED the model issues first WARNING
- **Per-receiver breakdown** — NovAtel vs u-blox F9P vs Xiaomi Mi8 (validates cross-receiver paper)
- **Ablation table** — Transformer-LSTM vs. LSTM-only vs. RF vs. rule-based threshold baseline

---

## Phase 3: Missing Public Datasets

These will form the **held-out test set** — critical for Paper 1 generalization claim.

### Task 3.1 — NCLT Dataset

- **Source:** http://robots.engin.umich.edu/nclt/
- **Download:** `2012-08-04` and `2013-04-05` traversals (GPS data only needed)
- **Extractor:** `src/extraction/nclt_extractor.py` (exists, verify it works)
- **Output:** `data/processed/nclt/nclt_features.csv`
- **Use:** Test generalization to different city + different platform (ground robot)

### Task 3.2 — Oxford RobotCar Dataset

- **Source:** https://robotcar-dataset.robots.ox.ac.uk/
- **Download:** 4 traversals from January 2019
- **Extractor:** `src/extraction/oxford_extractor.py` (exists)
- **Output:** `data/processed/oxford/oxford_features.csv`
- **Use:** Test generalization to European city + different vehicle

### Task 3.3 — UrbanNav Tokyo (Optional — Paper 3)

- **Source:** UrbanNav Dataset — Tokyo traversal
- **Purpose:** Geographic generalization: Beijing → Hong Kong → Tokyo
- **Use:** Paper 3 argument (pan-Asian city generalization)

---

## Phase 4: Documentation & Paper Writing

### Task 4.1 — Feature Justification Table

Full academic table linking each feature to a GNSS degradation mechanism. Suitable for insertion into Paper 1 Section 3 (Feature Engineering).  
→ See `docs/DATASET_PROCESSING_REPORT.md` Section 3 for draft content.

### Task 4.2 — Threshold Justification

Document why CLEAN ≥ 35 dBHz (not 38) for SNR-indicator data. Cite ITU-R and GNSS literature on typical urban C/N0 distributions.

### Task 4.3 — Dataset Novelty Table (Paper 4)

Summary table comparing our dataset against KAIST Urban, Oxford RobotCar, UrbanNav, NUDT Urban GNSS. Show that no existing dataset covers all 5 scenario types + multi-receiver + labelled + multi-city.

---

## Class Imbalance — Quick Reference

| Approach                | Where Applied                                         |
| ----------------------- | ----------------------------------------------------- |
| SMOTE                   | Training set only                                     |
| Focal Loss (γ=2)        | Training loss function                                |
| Class weights (1:2.5:5) | Both loss and evaluation reporting                    |
| Drone downsampling      | Reduce 14,862 CLEAN drone rows to ~2,000 before SMOTE |

**⚠️ Important:** Apply SMOTE AFTER train/val split. Never SMOTE on validation or test data.

---

## NaN Handling — Quick Reference

| Feature               | NaN Rate | Cause               | Fix                         |
| --------------------- | -------- | ------------------- | --------------------------- |
| `lat`, `lon`          | 54%      | RINEX-only sources  | Drop from model input       |
| `alt`                 | 54%      | RINEX-only sources  | Impute with training median |
| `lat_std`, `lon_std`  | 85%      | Only Septentrio GST | Impute as `hdop × 2.5`      |
| All other 30 features | 0%       | Fully present       | No action needed            |

---

## Priority Order

1. **Feature prep + windowing script** (2.1) — prerequisite for everything else
2. **Transformer-LSTM implementation** (2.2)
3. **Training + evaluation pipeline** (2.3 + 2.4)
4. **NCLT and Oxford processing** (3.1, 3.2)
5. **Paper writing** (4.x)
