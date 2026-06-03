# SENTINEL-GNSS — How to Run (Inputs & Outputs)

This is the single guide for running every part of the project: training, evaluation,
experiments, publication figures, real-time inference, and the adaptive EKF. It states
**where inputs come from** and **where outputs go** for each step.

> **TL;DR** — for a full reproduction, run `kaggle_train.ipynb` (or `colab_train.ipynb`) top to
> bottom on a GPU. Everything below explains the individual entry points and the local scripts.

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
  models/checkpoints/checkpoint_best.pt   trained model
  figures/                          13 evaluation figures + metrics_test.json
  paper_figures/                    ~15 publication figures (this project's figure set)
  reviewer_experiments.json         E1–E7
  ensemble_comparison.json          E8–E10
  ekf_demo.json                     EKF simulation result
  inference/                        per-file inference outputs
  RUN_SUMMARY.md / .json            consolidated metrics
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

## 7. Experiments

```bash
python -m src.models.ensemble_compare     # E8 ensembles + E9 persistence + E10 horizon gap
```
- **Input:** windows + `checkpoint_best.pt`  •  **Output:** `results/ensemble_comparison.json`
  (also appends a section to `results/RUN_SUMMARY.md`)

> E1–E7 (permutation, temporal ablation, per-class CIs, latency, SMOTE-KL, cross-city, ECE)
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

```bash
python -m src.models.inference \
    --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" \
    --out results/inference --receiver_tier 0 --ekf
```
- **Input:** any NMEA file (`--receiver_tier` 0=Septentrio … 3=phone).
- **Requires:** a trained `checkpoint_best.pt` matching the 37-feature scaler (`--checkpoint`,
  `--scaler` override the defaults).
- **Output:** in `results/inference/`:
  - `<stem>_predictions.csv` — per 30-s window: timestamp, lat/lon, ENU x/y, and
    P(CLEAN/WARNING/DEGRADED) + predicted class at **+5/+15/+30 s**.
  - `<stem>_summary.json` — epoch/window counts, per-horizon class counts, mean P(DEGRADED),
    first DEGRADED window (lead-time).
  - `<stem>_ekf.npz` (with `--ekf`) — raw GNSS, fixed-EKF, adaptive-EKF trajectories +
    P(DEGRADED).

**Edge cases handled:** missing/empty/malformed NMEA, too-few epochs for a window, missing
features (imputed), no GPS fix (predictions still produced; EKF skipped with a message),
checkpoint/scaler mismatch (clear error), CPU fallback when no GPU.

---

## 11. One-shot reproduction (recommended)

Run the notebook end-to-end. It executes Steps 3–10 above and writes everything to
`results/` (Kaggle Output tab / Google Drive). Key files to keep:
`RUN_SUMMARY.{md,json}`, `reviewer_experiments.json`, `ensemble_comparison.json`,
`ekf_demo.json`, `figures/`, `paper_figures/`, `models/checkpoints/`.
