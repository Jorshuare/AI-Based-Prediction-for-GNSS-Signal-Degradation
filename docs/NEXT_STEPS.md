# SENTINEL-GNSS: Next Steps Roadmap

**Updated:** June 1, 2026
**Current best result (Run 14):** +5s Macro-F1 = **0.8206** [95% CI 0.800–0.843], MCC = 0.7729; +30s Macro-F1 = 0.7825
**Run 14 status:** Full ✅ | LSTM-only ✅ | Transformer-only ✅ | Baselines (±SMOTE) ✅ | Reviewer experiments E1–E7 ✅ (E7 calibration re-run inline in Colab)
**Headline:** DEGRADED F1 0.274 (Run 11) → **0.718** (Run 14); cross-city Tokyo retains DEGRADED F1 **0.75 (DL) vs 0.15 (RF)**
**Authoritative numbers:** see `papers/RESULTS_REFERENCE.md`. **Team brief:** `papers/TEAM_BRIEF.md`.

> **Notebooks:** `kaggle_train.ipynb` (primary) and `colab_train.ipynb` (Drive-backed, fully
> synced as of Run 14) both reproduce every number end-to-end. Colab mirrors all outputs to
> `MyDrive/sentinel-gnss-results/`.

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

### Step 2 — Process new datasets (Deep + Harsh) ✅ COMPLETE for Run 12

> **Run 12 status:** Deep and Harsh are already processed and committed.
> `urbannav_deep_features.csv` (15,233 rows) and `urbannav_harsh_features.csv` (33,429 rows) are in `data/processed/urbannav/`.
> The combined `sentinel_gnss_labelled.csv` has **146,055 rows** (was 97,393).
> Skip this step on Colab — `git pull` in Step 1 brings these CSVs directly.

If you need to re-process locally (e.g., raw data changed):

```powershell
# Process the two new HK urban datasets
python src/processing/process_all_datasets.py --source urbannav_deep
python src/processing/process_all_datasets.py --source urbannav_harsh

# Re-combine all sources into labelled CSV
python src/processing/process_all_datasets.py --combine
```

Actual Run 12 output:

- `data/processed/urbannav/urbannav_deep_features.csv` — **15,233 rows** (10 receivers, Whampoa)
- `data/processed/urbannav/urbannav_harsh_features.csv` — **33,429 rows** (10 receivers, Mong Kok)
- `data/labelled/sentinel_gnss_labelled.csv` — **146,055 rows** across 12 source groups

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
- [x] UrbanNav HK Tunnel (10 receivers) processed → CSV ← critical for DEGRADED class
- [x] Tokyo Odaiba (Trimble + u-blox) processed → CSV
- [x] Tokyo Shinjuku (Trimble + u-blox) processed → CSV
- [x] NCLT Ann Arbor (2 sessions) processed → CSV
- [x] Oxford RobotCar (2 traversals) processed → CSV
- [x] Combined dataset: **97,393 rows** across 10 source groups (pre-Deep/Harsh)
- [x] UrbanNav HK-Deep-Urban-1 (Whampoa, 10 receivers): **15,233 rows** — WARNING 73.3% / DEGRADED 17.7% / CLEAN 9.0%
- [x] UrbanNav HK-Harsh-Urban-1 (Mong Kok, 10 receivers): **33,429 rows** — WARNING 66.5% / DEGRADED 20.7% / CLEAN 12.8%
- [x] **Combined dataset (Run 12): 146,055 rows** across 12 source groups, 4 cities
- [x] NMEA no-fix bug fixed — blockage epochs (quality=0) captured as DEGRADED
- [x] Session-based 70/15/15 split (seed=42) — prevents temporal data leakage
- [x] SPLIT_REASSIGN mechanism — moves high-DEGRADED sessions to training
- [x] Pandas 2.2+ groupby-drop bug fixed in `analyze_all_datasets.py` (use `transform()` not `apply()`)

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

### Results (Run 10, checkpoint_best.pt, epoch 23 of 73) — superseded by Run 12

- [x] +5s: MacroF1=0.6868, MCC=0.7614 | +15s: MacroF1=0.6330, MCC=0.6949 | +30s: MacroF1=0.6309, MCC=0.7176
- [x] Best val MacroF1=0.7768 | DEGRADED F1=0.274 | Training DEGRADED=555

### Results (Run 12, checkpoint_best.pt, epoch 16 of 73) ← CURRENT BEST

- [x] **+5s: Accuracy=0.8472, MacroF1=0.7036, MCC=0.7707, CI=[0.671, 0.735]**
- [x] **+15s: Accuracy=0.8009, MacroF1=0.6293, MCC=0.6975, CI=[0.606, 0.655]**
- [x] **+30s: Accuracy=0.8275, MacroF1=0.6043, MCC=0.7125, CI=[0.589, 0.622]**
- [x] **Best val MacroF1=0.8627** (+8.6 pts over Run 10)
- [x] Training DEGRADED: **11,996** (was 555 — 21.6× increase from Deep+Harsh)
- [x] DEGRADED +5s: P=0.216, R=0.527, F1=0.307 (up from 0.274 — precision still low)
- [x] WARNING +5s: P=0.959, R=0.766, F1=0.851 (massive gain — primary Deep/Harsh payoff)
- [x] Temperature: T=0.4442 (sharper, model under-confident on DEGRADED)
- [x] LSTM-only ablation: val MacroF1=0.8593, test +5s MacroF1=0.6082, DEGRADED F1=0.165
- [ ] Transformer-only ablation: **NOT YET TRAINED**

### Documentation

- [x] `DATASET_PROCESSING_REPORT.md` — full feature/label justification
- [x] `PAPER_TOPICS.md` — 4-paper publication roadmap
- [x] All model source files documented with references

---

## Run 13 Prerequisites (Next Run) 🔄

> Run 12 is complete for the full model and LSTM-only. Run 13 should focus on:
>
> 1. Train transformer-only ablation (never ran)
> 2. Reduce DEGRADED false alarms (precision=0.216 still too low)

### Priority fixes for Run 13

- [ ] **Train transformer-only ablation** (on Colab):
  ```bash
  python -m src.models.train --arch transformer_only --batch_size 256
  python -m src.models.evaluate --model_type transformer_only --tune_thresholds --temperature_scaling
  ```
- [ ] **Try reduced DEGRADED weight** — Run 12 precision=0.216, still below 0.30 target.
  - Keep `class_weights=[1.0, 2.0, 5.0]` OR increase DEGRADED FPR cap in `tune_thresholds()` from 0.15 → 0.20 to allow more recall
- [ ] **Run full baseline comparison** with ablation metrics once transformer-only is done:
  ```bash
  python -m src.models.baselines --include_ablations
  ```

---

## Known Issues 🐛

### Issue 1: DEGRADED precision still low (Run 12 actuals)

- **Problem:** DEGRADED F1 at +5s = 0.307. Recall=0.527 but Precision=0.216 (too many false alarms).
- **Root cause:** Test set has only 55 DEGRADED (3.8%). Even 12 false alarms → precision drops badly. Model trained on HK canyon DEGRADED, tested on Beihang campus DEGRADED — different physics (canyon vs. blockage).
- **Fix options:**
  - Keep class_weights=[1.0, 2.0, 5.0] (current) — recall-focused
  - Reduce FPR cap from 0.15 → 0.20 in `tune_thresholds()` to allow more DEGRADED predictions
  - Collect more Beihang DEGRADED data (only long-term fix)

### Issue 2: Val-test MacroF1 gap (Run 12: 0.8627 val vs 0.7036 test)

- **Gap is 15.9 points** (was 9 points in Run 10 — widened because val improved more than test).
- **Root cause:** Val (17,850 windows, CLEAN=76.8%, WARNING=18.1%, DEGRADED=5.1%) vs test (1,452 windows, CLEAN=46.2%, WARNING=49.9%, DEGRADED=3.8%).
- **This is NOT a bug.** Val performance jump reflects the model genuinely learning better WARNING detection from HK data.
- **In paper:** Report both. Val = "training convergence signal". Test = "deployment performance on Beihang campus".

### Issue 3: `pos_enc` AttributeError in evaluate.py for LSTM-only ← FIXED in current session

- **Fixed:** Added `hasattr(model, "pos_enc")` guard in `plot_attention_heatmap()`.
- LSTM-only ablation evaluations will now complete without crashing.

### Issue 4: Baseline MCC vs MacroF1 apparent discrepancy

- **Reported values:** RF MCC=0.891 with MacroF1=0.647; XGBoost MCC=0.909 with MacroF1=0.669.
- **This is NOT a bug.** On a test set with 46% CLEAN, 50% WARNING, and only 4% DEGRADED, a classifier that gets CLEAN and WARNING nearly perfect can achieve high MCC even with poor DEGRADED performance. MCC measures overall covariance; MacroF1 equally weights all 3 classes including the nearly-missed DEGRADED.
- **In paper:** Report both metrics and note the difference: "MCC rewards strong majority-class performance; MacroF1 exposes the DEGRADED class gap."

---

## Run 12 — Summary of Results ✅

Run 12 is complete. Full results:

| Metric                        | Run 10 | Run 12               | Δ        |
| ----------------------------- | ------ | -------------------- | -------- |
| Val MacroF1                   | 0.7768 | **0.8627**           | +8.6 pts |
| +5s MacroF1                   | 0.6868 | **0.7036**           | +1.7 pts |
| +15s MacroF1                  | 0.6330 | **0.6293**           | -0.4 pts |
| +30s MacroF1                  | 0.6309 | **0.6043**           | -2.7 pts |
| +5s DEGRADED F1               | 0.274  | **0.307**            | +3.3 pts |
| +5s WARNING F1                | ~0.67  | **0.851**            | +18 pts  |
| +5s MCC                       | 0.7614 | **0.7707**           | +0.9 pts |
| Training DEGRADED (pre-SMOTE) | 555    | **11,996**           | 21.6×    |
| Temperature T                 | —      | **0.4442** (sharper) | —        |

Window distribution (Run 12):

- train (pre-SMOTE): 59,854 — CLEAN=10,563, WARNING=37,295, DEGRADED=11,996
- train (post-SMOTE): 111,885 — balanced 37,295 per class
- val: 17,850 — CLEAN=13,704, WARNING=3,229, DEGRADED=917
- test: 1,452 — CLEAN=671, WARNING=726, DEGRADED=55

LSTM-only ablation (Run 12):

- Val MacroF1=0.8593, +5s MacroF1=0.6082, DEGRADED F1=0.165
- Attention heatmap crash fixed (pos_enc guard added to evaluate.py)

## Run 13 — Colab Instructions (next training run)

Run in this exact order:

```bash
# === Step 1: git pull (gets Run 12 results, fixed evaluate.py) ===
git pull origin main

# === Step 2: Transformer-only ablation (skipped in Run 12) ===
python -m src.models.train --arch transformer_only --batch_size 256
python -m src.models.evaluate --model_type transformer_only --tune_thresholds --temperature_scaling

# === Step 3: Full baseline comparison with all ablations ===
python -m src.models.baselines --include_ablations

# === Optional: retrain full model if adjusting class weights ===
# Current DEGRADED precision=0.216 (< 0.30 target) → keep class_weights=[1.0, 2.0, 5.0]
# python -m src.models.train  # only if changing config
```

### Class weight guidance after Run 12

DEGRADED precision = 0.216 at +5s (below 0.30 threshold):

- **Keep `class_weights=[1.0, 2.0, 5.0]`** — do NOT reduce to 3.5 yet
- Consider relaxing FPR cap from 0.15 → 0.20 in `evaluate.py tune_thresholds()` to trade some WARNING precision for DEGRADED recall

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
