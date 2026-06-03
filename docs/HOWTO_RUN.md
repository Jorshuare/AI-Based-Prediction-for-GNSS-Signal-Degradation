# SENTINEL-GNSS — How to Run Everything
## Complete Guide with Inputs, Outputs & Justifications

**This is the authoritative guide for running SENTINEL-GNSS.** It explains:
- **What each step does** (and why)
- **Where inputs come from** (raw data, models, config)
- **Where outputs go** (results folder, figures, metrics)
- **How to run it** (commands, notebooks, scripts)

**Two main workflows:**
1. **Full training pipeline** (on Kaggle/Colab) → trains models + ensemble + EKF validation + publication figures
2. **Local inference & testing** → run trained model on new NMEA data, test ensemble, visualize EKF

> **TL;DR** — For a complete reproduction from scratch: run `kaggle_train.ipynb` or `colab_train.ipynb` top to bottom on GPU. For local testing with an existing checkpoint: skip to Section 10 (Inference).

---

## 0. Environment

| Requirement | Notes |
|---|---|
| Python 3.10+ | 3.13 works locally |
| GPU (training) | Kaggle **T4 ×2** or Colab **T4**. CPU works for inference/EKF/figures. |
| Install | `pip install -r requirements.txt` (notebooks also `pip install imbalanced-learn xgboost`) |

**Two ways to run the full pipeline:**
- **Kaggle:** open `kaggle_train.ipynb`, set Accelerator = GPU T4 ×2, Internet ON, Run All.
  Outputs land in `/kaggle/working/sentinel-gnss/results/` (download from the Output tab).
- **Colab:** open `colab_train.ipynb`, set Runtime = GPU, Run All. Outputs **mirror to your
  Google Drive** at `MyDrive/sentinel-gnss-results/` after every step (download from Drive).

Both notebooks clone the repo from GitHub, so all data CSVs arrive automatically.

---

## 1. Repository layout (where things live)

```
data/
  raw/scenarios/...                 INPUT  raw field collections (NMEA/SBF/RINEX)
  raw/public/...                    INPUT  UrbanNav, Tokyo, NCLT, Oxford
  labelled/sentinel_gnss_labelled.csv   the 149,662-row labelled dataset (committed)
  processed/
    windows/         {train,val,test}.npz   SMOTE windows (baselines)
    windows_no_smote/{train,val,test}.npz   no-SMOTE windows (DL models)
    scaler.pkl                       fitted MinMaxScaler (used by inference)
    tokyo/tokyo_shinjuku_features.csv  held-out cross-city set
src/
  processing/process_all_datasets.py   raw → labelled CSV
  models/feature_prep.py               labelled CSV → windows + scaler
  models/train.py                      train a model
  models/evaluate.py                   evaluate + 13 figures + metrics_test.json
  models/baselines.py                  RF/XGBoost/trivial baselines
  models/ensemble_compare.py           E8–E10: ensembles + memory diagnostics
  models/adaptive_ekf.py               prediction-informed EKF (+ --demo)
  models/inference.py                  raw NMEA → predictions → EKF
  utils/make_paper_figures.py          ~15 publication figures
results/
  models/checkpoints/
    checkpoint_best.pt              trained Transformer-LSTM model (37 features)
    config.json                     model architecture + hyperparameters
  ensemble_xgb_model.joblib         trained XGBoost (for soft-vote ensemble; saved by ensemble_compare)
  figures/                          13 evaluation figures + metrics_test.json
  paper_figures/                    ~20 publication figures (no titles, cividis palette, 300 dpi)
  paper_figures/README.md           figure index: which figure goes in which paper/slide
  reviewer_experiments.json         E1–E7 (E1=permutation, E2=temporal, E3–E5=CIs, E6=cross-city, E7=calibration)
  ensemble_comparison.json          E8–E10 (E8=ensembles, E9=persistence, E10=horizon gap)
  ekf_demo.json                     EKF simulation on controlled blockage (synthetic)
  inference/                        per-file inference outputs (<stem>_predictions.csv, _summary.json, _ekf.npz)
  RUN_SUMMARY.md / .json            consolidated metrics + narrative
```

---

## 2. Data processing  (raw → labelled CSV)

Only needed if raw data changed; the labelled CSV is committed.

```bash
python src/processing/process_all_datasets.py --source scenarios   # one source
python src/processing/process_all_datasets.py --combine            # rebuild labelled CSV
```
- **Input:** `data/raw/...`  •  **Output:** `data/labelled/sentinel_gnss_labelled.csv`
  and per-source CSVs in `data/processed/...`.

---

## 3. Build windows  (labelled CSV → tensors + scaler)

```bash
python -m src.models.feature_prep --force              # SMOTE windows  (baselines)
python -m src.models.feature_prep --no_smote --force   # no-SMOTE windows (DL)
# optional longer horizons for analysis (adds y_45s/y_60s; default keeps 5/15/30):
python -m src.models.feature_prep --no_smote --force --extra_horizons 45 60
```
- **Input:** `data/labelled/sentinel_gnss_labelled.csv`
- **Output:** `data/processed/windows[_no_smote]/{train,val,test}.npz` + `scaler.pkl`

---

## 4. Train

```bash
python -m src.models.train --batch_size 256 --window_dir data/processed/windows_no_smote
python -m src.models.train --model_type lstm_only        --batch_size 256 --window_dir data/processed/windows_no_smote
python -m src.models.train --model_type transformer_only --batch_size 256 --window_dir data/processed/windows_no_smote
```
- **Input:** windows  •  **Output:** `results/models/checkpoints[_lstm_only|_transformer_only]/checkpoint_best.pt`

## 5. Evaluate  (metrics + 13 figures)

```bash
python -m src.models.evaluate --tune_thresholds --temperature_scaling --window_dir data/processed/windows_no_smote
```
- **Output:** `results/figures/*.{png,pdf}` + `results/figures/metrics_test.json`

## 6. Baselines

```bash
python -m src.models.baselines --windows_dir data/processed/windows            # SMOTE
python -m src.models.baselines --windows_dir data/processed/windows_no_smote   # no-SMOTE
python -m src.models.baselines --include_ablations                             # full table
```
- **Output:** `results/baselines/baseline_comparison*.json`

---

## 7. Experiments & Ensemble Model

```bash
python -m src.models.ensemble_compare
```
**What it does:**
- **E8:** trains DL, RF, XGBoost, soft-vote ensemble, stacking ensemble on in-domain test + Tokyo (cross-city);
  reports Macro-F1, DEGRADED F1, MCC per model.
- **E9:** persistence baseline (predict label@t+h from label@t) — quantifies "is memory needed?"
- **E10:** per-horizon gap (Macro-F1 at +5/+15/+30 s for each method).
- **Saving:** auto-saves trained XGBoost model trained on +5s data as `results/ensemble_xgb_model.joblib` 
  (used by inference `--ensemble` for soft-vote: P = (P_DL + P_XGB) / 2).

**Output:**
- `results/ensemble_comparison.json` — all metrics (E8/E9/E10)
- `results/ensemble_xgb_model.joblib` — XGBoost classifier (for soft-vote inference)
- (also appends summary to `results/RUN_SUMMARY.md`)

> E1–E7 (permutation, temporal ablation, per-class CIs, latency, SMOTE-KL, cross-city, ECE/calibration)
> are produced inside the notebooks (Step 10b) → `results/reviewer_experiments.json`.

---

## 8. Publication figures

```bash
python -m src.utils.make_paper_figures
```
- **Input:** `results/figures/metrics_test.json`, `results/ekf_demo.json`,
  `results/reviewer_experiments.json`, `results/ensemble_comparison.json` (uses confirmed
  Run-14 constants for anything not present locally).
- **Output:** `results/paper_figures/figNN_*.{pdf,png}` (~15 figures) — see
  `results/paper_figures/README.md` for the index of which figure goes in which paper/slide.

---

## 9. Adaptive EKF

```bash
python -m src.models.adaptive_ekf --demo
```
- **Output:** `results/ekf_demo.json` (controlled blockage simulation; adaptive EKF cuts
  blockage-segment RMSE ~34% vs raw GNSS). For real-data RMSE call `run_ekf_experiment(
  gnss_xy, reference_xy, p_degraded)` with an aligned reference trajectory.

---

## 10. End-to-end inference  (raw NMEA → predictions → EKF)

**DL-only (single model, fastest):**
```bash
python -m src.models.inference \
    --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" \
    --out results/inference --receiver_tier 0 --ekf
```

**Ensemble (DL + XGBoost soft-vote, recommended for deployment):**
```bash
python -m src.models.inference \
    --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" \
    --out results/inference --receiver_tier 0 --ensemble --ekf
```

**Test different scenarios:**
```bash
# Scenario A (urban blockage)
python -m src.models.inference --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" --ensemble --ekf

# Scenario B (multipath)
python -m src.models.inference --nmea "data/raw/scenarios/Degraded data/B/log_0001.nmea" --ensemble --ekf

# UrbanNav Tokyo (cross-city validation)
python -m src.models.inference --nmea "data/raw/public/urbannav/Tokyo/Odaiba/rover_ublox.obs" --ensemble --ekf
```

**Options:**
- `--nmea PATH` — any NMEA file (required)
- `--receiver_tier N` — 0=Septentrio/professional (default), 1=u-blox, 2=Trimble, 3=smartphone
- `--ensemble` — use DL + XGBoost soft-vote (requires `results/ensemble_xgb_model.joblib`; saved
  by `ensemble_compare` during training; gracefully falls back to DL if not found)
- `--ekf` — also run the adaptive 2D constant-velocity EKF
- `--ekf_horizon {5s|15s|30s}` — which P(DEGRADED) to use for EKF adaptation (default 5s)
- `--checkpoint` — path to trained model (default `results/models/checkpoints/checkpoint_best.pt`)
- `--scaler` — path to fitted MinMaxScaler (default `data/processed/scaler.pkl`)

**Output** (in `results/inference/<stem>_...`):
- `_predictions.csv` — per 30-s window: timestamp, lat/lon, ENU x/y,
  P(CLEAN/WARNING/DEGRADED) + predicted class at **+5/+15/+30 s** (all three horizons every window).
- `_summary.json` — epochs/windows, per-horizon class counts, mean P(DEGRADED), first DEGRADED window
  (lead-time), `"ensemble": "DL + XGBoost soft-vote"` if --ensemble used.
- `_ekf.npz` (with `--ekf`) — raw GNSS trajectory, fixed-EKF trajectory, adaptive-EKF trajectory, 
  P(DEGRADED) per epoch.

**Edge cases handled:** missing/empty/malformed NMEA, too-few epochs for a window, missing
features (imputed), no GPS fix (predictions still produced; EKF skipped with a message),
checkpoint/scaler mismatch (clear error), CPU fallback when no GPU.

---

## 11. One-shot reproduction (recommended)

Run the notebook end-to-end: `kaggle_train.ipynb` or `colab_train.ipynb`.

**What the notebook does:**
- **Step 3:** build windows (30-s tensors + scaler)
- **Step 4:** train Transformer-LSTM + LSTM-only + Transformer-only
- **Step 5:** evaluate (metrics, 13 figures, calibration)
- **Step 6:** RF/XGBoost/trivial baselines (SMOTE)
- **Step 10b:** E1–E7 reviewer experiments (permutation, ablations, CIs, latency, cross-city, ECE)
- **Step 10c:** E8–E10 ensemble comparison → **saves `ensemble_xgb_model.joblib`**
- **Step 12:** adaptive EKF demo (controlled blockage simulation)
- **Step 13:** publication figures (cividis, no titles, 300 dpi, panel labels)
- **Step 14:** archive results to zip (download from Kaggle Output / Google Drive)

**Download & local test:**
1. Run on Kaggle T4 ×2 (or Colab GPU).
2. Download `results/` folder from Kaggle Output tab (or sync from Google Drive).
3. Replace local `results/` with the downloaded folder.
4. Test ensemble inference locally:
   ```bash
   python -m src.models.inference --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" --ensemble --ekf
   ```

**Key files to keep & version:**
- `models/checkpoints/checkpoint_best.pt` + `config.json` — trained model
- `ensemble_xgb_model.joblib` — XGBoost for soft-vote ensemble
- `reviewer_experiments.json` + `ensemble_comparison.json` — all metrics
- `ekf_demo.json` — EKF simulation results
- `figures/` — 13 evaluation figures + `metrics_test.json`
- `paper_figures/` — ~20 publication figures + `README.md` (index)
- `RUN_SUMMARY.{md,json}` — consolidated narrative + metrics

---

## 🔴 **12. Adaptive EKF: From Prediction to Navigation (Phase 2a)**

### **Why EKF?**

Prediction alone doesn't improve positioning. We need to **use** the prediction. The Adaptive Extended Kalman Filter (EKF) does this:

- **Standard EKF:** Fuses GNSS measurements with a motion model (constant velocity). Trusts GNSS equally always.
- **Our Adaptive EKF:** Same fusion, but **adapts measurement noise R based on our predicted P(DEGRADED)**:
  - When P(DEGRADED) is high → inflate R → distrust GNSS → lean on motion model
  - When P(DEGRADED) is low → normal R → use GNSS to correct drift

**Why adaptive?** When GNSS is about to fail, pre-emptively leaning on dead-reckoning prevents large position jumps. By the time failure hits, the filter has already adapted.

### **How to Run EKF**

#### **Option A: Synthetic Blockage Demo (Proof-of-Concept)**
```bash
python -m src.models.adaptive_ekf --demo
```
- Creates synthetic 300-epoch trajectory with blockage (epochs 120–180)
- Predictor warns from epoch 115 (proactive)
- Compares: raw GNSS vs. fixed-R EKF vs. adaptive EKF
- **Results:** Adaptive EKF cuts blockage-segment RMSE by **33.8%** vs raw GNSS
- Output: `results/ekf_demo.json` with metrics

#### **Option B: Real-Data Validation (Phase 2a, Coming)**
```bash
# (Not yet integrated; coming after UrbanNav runner is built)
python -m src.models.ekf_urbannav --scenario "Tokyo/Odaiba" --adaptive
```
- Parses UrbanNav rover GNSS (RINEX format)
- Parses IMU data (imu.csv) and reference trajectory (reference.csv, cm-level SPAN-INS)
- Runs 9-state EKF (IMU-driven prediction, GNSS update, adaptive R)
- Computes real RMSE vs. ground truth
- **Expected:** 15–30% RMSE improvement during actual blockage events
- Output: `results/ekf_urbannav_option_b.json` with real-world metrics

### **Understanding EKF Outputs**

When you run inference with `--ekf`, you get:

1. **`<stem>_ekf.npz`** — Binary file with trajectory data:
   - `gnss`: raw GNSS positions (N, 2) — noisy
   - `fixed`: fixed-R EKF output (N, 2) — smoother than raw
   - `adaptive`: adaptive-R EKF output (N, 2) — smoothest, our method
   - `p_degraded`: per-epoch P(DEGRADED) from model (N,) — drives R adaptation

2. **`<stem>_summary.json`** — JSON with:
   - `ekf.status`: "ok" if EKF ran successfully
   - `ekf.rmse_*`: RMSE metrics (if reference trajectory provided)
   - Other fields: epoch counts, class distributions, lead-time stats

### **Interpreting Results**

**Example output (synthetic blockage):**
```json
{
  "rmse_overall": {
    "gnss_only": 25.763,
    "fixed_ekf": 21.521,
    "adaptive_ekf": 17.033
  },
  "rmse_degraded_segment": {
    "gnss_only": 54.390,
    "fixed_ekf": 45.624,
    "adaptive_ekf": 35.985
  },
  "adaptive_improvement_pct_degraded": 33.8
}
```

**What this means:**
- During clean signal, all methods are similar (~25 m error).
- During blockage (degraded segment), adaptive EKF wins by a lot (36 m vs 54 m raw).
- The 33.8% improvement is the headline: prediction-aware adaptation works.

### **Next Steps: Real Data Validation**

After Kaggle training run:
1. Download `ensemble_xgb_model.joblib` (saves automatically during ensemble_compare)
2. Test ensemble: `python -m src.models.inference --nmea <file> --ensemble --ekf`
3. Build UrbanNav runner (Phase 2a-i, ~2-3 hours)
4. Validate on real Tokyo data with ground truth
5. Update papers with real RMSE numbers

---

## **Understanding the Full Pipeline**

### **Data Flow:**
```
Raw NMEA/RINEX files
    ↓
Features extraction (37 engineered features per epoch)
    ↓
Feature scaling (MinMaxScaler, fit on train only)
    ↓
Sliding windows (30-second tensors, labels at +5/15/30s)
    ↓
Deep learning model (Transformer-LSTM, multi-task multi-horizon)
    ↓
Predictions: P(CLEAN), P(WARNING), P(DEGRADED) per horizon
    ↓
Ensemble (soft-vote: DL + XGBoost)
    ↓
Adaptive EKF (uses P(DEGRADED) to adjust measurement trust)
    ↓
Output: filtered position + metrics + figures
```

### **Key Design Decisions (and Why)**

| Decision | Why |
|----------|-----|
| **37 features** | Domain-relevant (C/N₀, DOP, constellation) + temporal patterns. Not raw phase/pseudorange. |
| **Transformer + LSTM** | Transformer sees long-range dependencies, LSTM captures degradation trends. Together: 0.892 cross-city. |
| **Multi-horizon (+5/15/30s)** | Different prediction leads suit different planning horizons. One model, three outputs. |
| **Cross-city validation (Tokyo)** | Unseen city proves generalization. In-domain results can be misleading. |
| **Soft-vote ensemble** | DL excels cross-city, XGB excels in-domain. Averaging their probabilities is robust. |
| **Adaptive R in EKF** | Pre-emptive: distrust GNSS before it breaks. Standard filter can't do this. |
| **UrbanNav for Phase 2a** | Has cm-level ground truth (SPAN-INS), real blockage, IMU data, public. Perfect for validation. |

---

## **Troubleshooting**

| Problem | Solution |
|---------|----------|
| "NMEA file not found" | Check path is absolute, not relative. Use `data/raw/scenarios/Degraded data/A/log_0000.nmea` |
| "Checkpoint not found" | Run training first (`kaggle_train.ipynb`), or download results folder from Kaggle. |
| "No GPS fix; EKF skipped" | Some NMEA files have periods of no valid position. EKF needs at least one fix to start. Use a different file. |
| "Ensemble model not found" | Run `ensemble_compare` first (or re-run Kaggle), which saves `ensemble_xgb_model.joblib`. |
| "torch.cuda.OutOfMemory" | Reduce batch size (change in checkpoint config or code). Or use CPU (slower). |

---

## **Performance & Latency**

| Component | Latency | Notes |
|-----------|---------|-------|
| Feature extraction | 0.5 ms | Per epoch, CPU |
| DL inference | 0.045 ms | Per sample, GPU. 1.46M parameters. |
| Ensemble (soft-vote) | 0.010 ms | XGB prediction. Negligible. |
| EKF update | 0.001 ms | Kalman gain computation. Negligible. |
| **Total per epoch** | **~0.6 ms** | Real-time at 10 Hz, low CPU/GPU load. |

Suitable for embedded systems (Jetson, automotive ECUs) or edge inference.

---

## **Reproducibility & Citation**

All code, models, and results are:
- ✅ Version-controlled (GitHub)
- ✅ Reproducible (notebooks from scratch, deterministic seeds)
- ✅ Released with DOI (Zenodo)
- ✅ Fully documented (this guide + docstrings + papers)

**For citation:**
```bibtex
@article{sentinel-gnss-2026,
  title={Predicting GNSS Signal Degradation with Deep Learning},
  author={...},
  journal={GPS Solutions},
  year={2026}
}
```

For exact citation, see `papers/` folder once published.
