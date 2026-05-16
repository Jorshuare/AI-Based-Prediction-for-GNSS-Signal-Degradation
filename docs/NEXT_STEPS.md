# SENTINEL-GNSS: Next Steps Roadmap

**Updated:** May 16, 2026  
**Data processing:** COMPLETE — all 8 sources processed and combined.

---

## Completed ✅

- [x] Scenarios A–E, Supervisor Vehicle/Drone processed → CSV
- [x] UrbanNav HK Medium (10 receivers) processed → CSV
- [x] **UrbanNav HK Tunnel (10 receivers) processed → CSV** ← NEW
- [x] **Tokyo Odaiba (Trimble + u-blox) processed → CSV** ← NEW
- [x] **NCLT Ann Arbor (2 sessions) processed → CSV** ← NEW
- [x] **Oxford RobotCar (2 traversals) processed → CSV** ← NEW
- [x] Combined dataset with **session-based stratified 70/15/15 split** ← REVISED
- [x] `_assign_label()` NaN-aware (handles missing C/N0 gracefully) ← FIXED
- [x] Separate `_apply_position_sigma_labels()` for NCLT/Oxford labeling
- [x] `DATASET_PROCESSING_REPORT.md` — full feature/label justification
- [x] `NEXT_STEPS.md` — this file

### Why Tokyo Shinjuku Was NOT Processed

Only the base station OBS file exists (`base_trimble.obs`). The rover file is missing. Cannot extract signal quality features from the base station.

---

## Phase 2: Feature Preparation for Model Training

### Task 2.1 — Feature Prep Script

**File to create:** `src/models/feature_prep.py`

```python
# Decisions to implement:
EXCLUDE_FROM_MODEL = ['lat', 'lon']    # Raw coords → geographic overfitting
IMPUTE_MEDIAN = ['alt']                # 54% NaN; fill with session median
IMPUTE_DOP_PROXY = ['lat_std', 'lon_std']  # 85% NaN; fill as hdop * 2.5
MASK_TO_ZERO = ['mean_cnr', 'min_cnr', 'max_cnr', 'std_cnr', 'cnr_trend']  # NaN for NCLT/Oxford

# ADD: boolean flag feature
ADD_FEATURE = 'cnr_available'  # 1 if C/N0 present, 0 if NaN — lets model know what's missing
```

**Model input:** 33 features (35 minus lat/lon) + 1 `cnr_available` flag = **34 features total**

**Windowing:**

- Sliding window: 30 seconds (30 time steps at 1 Hz)
- Output labels: label at t+5s, t+15s, t+30s (look-ahead after the window)
- No overlapping windows across session boundaries

**SMOTE:** Apply on training set ONLY, after session-stratified split.

- Target: ~15% WARNING, ~8% DEGRADED in training batch
- Never apply to validation or test sets

**Scaling:** Min-max [0,1] using TRAINING set statistics. Save scaler to `data/processed/scalers.pkl`.

---

## Phase 3: Transformer-LSTM Model

### Task 3.1 — Architecture

**File to create:** `src/models/transformer_lstm.py`

```
Input:     (batch, 30, 34)       # 30 time steps × 34 features
           ↓
Positional Encoding (sinusoidal)
           ↓
Transformer Encoder:
  4 attention heads, d_model=64, 2 layers, FFN dim=256, dropout=0.1
           ↓
2-layer LSTM: hidden_dim=128, dropout=0.1
           ↓
Last hidden state: (batch, 128)
           ↓
Three parallel output heads (each 128 → 3 → Softmax):
  head_5s   → P(CLEAN, WARNING, DEGRADED) at t+5 seconds
  head_15s  → P(CLEAN, WARNING, DEGRADED) at t+15 seconds
  head_30s  → P(CLEAN, WARNING, DEGRADED) at t+30 seconds
```

### Task 3.2 — Training

**File to create:** `src/models/train.py`

| Parameter     | Value                                                       |
| ------------- | ----------------------------------------------------------- |
| Optimizer     | AdamW, lr=1e-3, weight_decay=1e-4                           |
| Scheduler     | CosineAnnealingLR, T_max=100                                |
| Epochs        | 100 with early stopping (patience=15, monitor val macro-F1) |
| Batch size    | 64                                                          |
| Loss          | Focal Loss, γ=2.0                                           |
| Class weights | {0: 1.0, 1: 2.5, 2: 5.0}                                    |
| Seed          | 42                                                          |

### Task 3.3 — Evaluation

Report for each horizon (t+5s, t+15s, t+30s):

- Precision / Recall / F1 per class
- Macro-F1 (primary metric)
- AUC-ROC (one-vs-rest)
- Confusion matrix

**Additional analyses for papers:**

1. **Lead-time histogram**: how many seconds before actual DEGRADED does first WARNING appear?
2. **Ablation table**: Transformer-LSTM vs. LSTM-only vs. Transformer-only vs. RF vs. threshold baseline
3. **Per-receiver breakdown**: NovAtel vs. u-blox F9P vs. Xiaomi Mi8 F1 scores → Paper 2
4. **Leave-city-out generalization**: train without Tokyo → test on Tokyo → Paper 3

---

## Phase 4: Train/Validation/Test Split — Reminder

The split is now **session-based 70/15/15**, NOT source-based. Key rules:

- Each unique session (one recording run) is assigned as a whole to one split
- Within each source category, sessions are proportionally distributed
- Applied in `combine_all()` with seed=42 (reproducible)
- All three splits contain examples from ALL sources

**This replaces the previous "UrbanNav = validation only" approach**, which was scientifically incorrect because it created distribution mismatch between train and test.

**Leave-dataset-out experiments are SEPARATE** — run as generalization ablations, not as the primary evaluation.

---

## Phase 5: NaN Feature Handling Reference

| Feature                 | NaN % | Source             | Fix                                |
| ----------------------- | ----- | ------------------ | ---------------------------------- |
| `lat`, `lon`            | 54%   | RINEX-only sources | **Exclude from model**             |
| `alt`                   | 54%   | RINEX-only sources | Impute with session median         |
| `lat_std`, `lon_std`    | 85%   | No GST for most    | Impute as `hdop × 2.5`             |
| C/N0 group (5 features) | ~10%  | NCLT + Oxford      | Set to 0 + `cnr_available`=0 flag  |
| DOP group (5 features)  | ~45%  | RINEX-only sources | Impute with DOP-from-sats estimate |
| All others              | < 5%  | —                  | OK, no action                      |

---

## Phase 6: Missing Data / Future Work

| Item                         | Priority | Notes                                    |
| ---------------------------- | -------- | ---------------------------------------- |
| Tokyo Shinjuku               | Low      | No rover RINEX; skip unless data located |
| NCLT additional sessions     | Low      | 2012-01-08, 2012-04-29 etc. available    |
| Oxford additional traversals | Low      | Multiple traversals available            |
| Paper writing                | HIGH     | Start after first model training run     |

---

## Completed ✅

- [x] Raw data explored (scenarios A–E, supervisor vehicle/drone, UrbanNav HK)
- [x] 35 features justified (all derivable from NMEA + RINEX, physically meaningful)
- [x] 3-label scheme designed (CLEAN / WARNING / DEGRADED)
- [x] Unified processing pipeline: `src/processing/process_all_datasets.py`
- [x] All datasets processed → standardized CSVs in `data/processed/`
- [x] Combined dataset: **28,871 rows × 41 columns**
- [x] Labels applied: 66% CLEAN, 27.3% WARNING, 6.7% DEGRADED
- [x] Train/validation split assigned (UrbanNav = validation)
- [x] Labelled copy at `data/labelled/sentinel_gnss_labelled.csv`

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
