# SENTINEL-GNSS — Runbook & Architecture (Every Step, Option & Formula)

**What this document is:** the operational reference — the end-to-end pipeline, the exact command
for every step with its options, and an appendix with all the mathematical formulas. Use this to
reproduce any result or run any part of the system.

> Companion docs: **[01_APPLICATION_AND_DASHBOARD.md](01_APPLICATION_AND_DASHBOARD.md)** (the app)
> and **[02_DATA_AND_MODELING.md](02_DATA_AND_MODELING.md)** (the science & results).

---

## 1. Pipeline overview

```
 raw NMEA / RINEX / IMU
        │  (1) process            src/processing/process_all_datasets.py
        ▼
 cleaned per-epoch tables
        │  (2) features+labels    src/features/…, src/labeling/labeler.py, src/models/feature_prep.py
        ▼
 37-feature windows (+5/15/30 s labels)
        │  (3) train              src/models/train.py   (or kaggle_train.ipynb / colab_train.ipynb)
        ▼
 checkpoint + scaler             results/models/checkpoints/
        │  (4) evaluate           src/models/evaluate.py
        │  (5) baselines          src/models/baselines.py
        │  (6) ensemble (E8–E10)  src/models/ensemble_compare.py
        │  (7) reviewer exps      (E1–E7, in evaluate / notebooks)
        ▼
 metrics JSONs                   results/*.json
        │  (8) figures           src/utils/make_paper_figures.py
        │  (9) inference          src/models/inference.py  → results/inference/*.csv
        │ (10) GNSS positioning   src/models/spp_rinex.py / RTKLIB rnx2rtkp
        │ (11) sensor fusion      src/models/ekf_urbannav_runner.py
        │ (12) fusion figures     src/utils/make_ekf_urbannav_figures.py
        ▼
 dashboard  (backend + frontend)  dashboard/
```

Run everything from the **repository root**. On Windows use PowerShell; commands below are
shell-agnostic. In China, prefix pip with `-i https://pypi.tuna.tsinghua.edu.cn/simple` and npm with
`--registry=https://registry.npmmirror.com`.

---

## 2. Environment

```bash
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install -r requirements.txt                          # core science stack
pip install -r dashboard/server/requirements.txt         # dashboard backend
```

---

## 3. Data → features → labels

**(1) Process all raw datasets** (NMEA/RINEX/IMU → clean per-epoch tables):
```bash
python -m src.processing.process_all_datasets
```
Per-source processors live in `src/processing/` (e.g. `our_collection_processor.py`,
`nclt_processor.py`, `oxford_processor.py`); extractors for public sets in `src/extraction/`.

**(2) Build features, labels, and windows:**
```bash
python -m src.features.feature_extractor      # 37 engineered features per epoch
python -m src.labeling.labeler                # CLEAN/WARNING/DEGRADED labels at +5/15/30 s
python -m src.models.feature_prep             # scaling, 30-s windows, session-level split
```
*Options that matter:* window length (30 s default), horizons (5/15/30 s), receiver_tier handling,
and the session-level split (never split one drive across train/val/test).

---

## 4. Training

**Local:**
```bash
python -m src.models.train
```
**Cloud (recommended, free GPU):** open `kaggle_train.ipynb` (Kaggle) or `colab_train.ipynb`
(Colab) and run all. They train the full model **and** the LSTM-only / Transformer-only ablations,
then save everything to `results/`.

Model defined in `src/models/transformer_lstm.py`. Key hyper-parameters (all justified in
[02_DATA_AND_MODELING.md](02_DATA_AND_MODELING.md) §5):

| Group | Value |
|---|---|
| Transformer | 2 layers, 8 heads, d_model=128, d_ff=512 |
| BiLSTM | 2 layers, 256 hidden, bidirectional |
| Heads | 3 (one per horizon), 3 classes each |
| Loss | Focal (γ=1.0) + class weights [1, 2, 5] |
| Optimiser | AdamW, lr=1e-3, weight_decay=1e-4 |
| Schedule | 5-epoch warm-up, grad-clip 1.0, label smoothing |
| Params | ≈ 1.46 M |

Outputs: `results/models/checkpoints/checkpoint_best.pt`, `config.json`, `training_history.json`,
and the scaler.

---

## 5. Evaluation, baselines, ensemble, reviewer experiments

```bash
python -m src.models.evaluate          # Macro-F1, per-class F1, MCC, bootstrap CIs, ECE,
                                        #   temperature scaling, confusion/ROC/PR/calibration figs
python -m src.models.baselines         # MajorityClass, C/N0-threshold, RandomForest, XGBoost
                                        #   (SMOTE and no-SMOTE variants)
python -m src.models.ensemble_compare  # E8 ensembles (soft-vote/stacking), E9 persistence,
                                        #   E10 per-horizon gap; saves ensemble_xgb_model.joblib
```

Reviewer experiments **E1–E7** (permutation test, temporal ablation, per-class bootstrap CIs,
latency, SMOTE-KL, cross-city metrics, calibration/ECE) are produced by the evaluation step /
notebooks into `results/reviewer_experiments.json`. Consolidated metrics land in
`results/RUN_SUMMARY.json`; the human-readable map is `papers/RESULTS_REFERENCE.md`.

---

## 6. Inference on a new drive (produces a Live-tab scenario)

```bash
python -m src.models.inference --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" \
                               --ensemble --ekf --ekf_horizon 5s
```

### 6.1 All inference options (and what each buys you)

| Flag | Default | Effect | Expected result |
|---|---|---|---|
| `--nmea PATH` | *(required)* | the input NMEA file | drives everything below |
| `--out DIR` | `results/inference` | output directory | where the CSV/JSON/NPZ land |
| `--checkpoint PATH` | best checkpoint | which trained model to use | swap models without code changes |
| `--scaler PATH` | trained scaler | feature scaler (must match the checkpoint) | correct feature normalisation |
| `--receiver_tier N` | `0` | hardware tier 0–3 | adapts thresholds to receiver quality |
| `--ensemble` | off | soft-vote the DL with the saved XGBoost (`ensemble_xgb_model.joblib`) | **best cross-city quality** (Tokyo +5 s Macro-F1 0.65→**0.89**, DEGRADED 0.75→**0.90**) |
| `--ekf` | off | run the adaptive EKF on the predicted P(DEGRADED) | adds a fused position track; real Tokyo blocked-RMSE **−49 %** vs raw |
| `--ekf_horizon {5s,15s,30s}` | `5s` | which horizon’s P(DEGRADED) drives the EKF | shorter = sharper/pre-emptive, longer = earlier but softer |

**Outputs** (auto-discovered by the dashboard): `results/inference/<stem>_predictions.csv`,
`<stem>_summary.json`, and (with `--ekf`) `<stem>_ekf.npz`. Edge cases handled: missing/malformed
NMEA, too-few epochs, no-fix periods, checkpoint/scaler mismatch.

### 6.2 Comparing the inference configurations

The trade-offs above are summarised in **`results/paper_figures/fig23_inference_comparison.png`**
(generate with `python -m src.utils.make_inference_comparison`):
- **(a) Prediction stage** — cross-city Tokyo quality for RandomForest vs Transformer-LSTM vs
  XGBoost vs the **DL+XGB ensemble**. The ensemble wins (0.89 Macro-F1 / 0.90 DEGRADED); RandomForest
  collapses on DEGRADED (0.15).
- **(b) Fusion stage** — real Tokyo blocked-segment RMSE for raw GNSS vs simple KF vs **aided EKF**.
  The aided EKF cuts error by **+49 %** (47.4 → 24.3 m).

*Recommended production configuration:* `--ensemble --ekf` — best prediction quality **and** the
fused position track.

---

## 7. Real GNSS positioning (Tokyo) — two engines

**(A) RTKLIB single-point (gold standard, Trimble):**
```bash
# from the Shinjuku data dir (avoids the space in the project path)
cd "data/raw/public/urbannav/Tokyo/Shinjuku"
"/c/Program Files/RTKLIB_EX_2.5.0/rnx2rtkp.exe" -p 0 -m 10 -e \
    -o tokyo_spp.pos rover_trimble.obs base.nav
mv tokyo_spp.pos ../../../../../../results/tokyo_trimble_spp.pos
```
| Option | Meaning |
|---|---|
| `-p 0` | single-point positioning (shows the *real* multipath; RTK would be too clean) |
| `-m 10` | 10° elevation mask |
| `-e` | output x/y/z ECEF |
| (default sys) | GPS + GLONASS (more satellites in the canyon) |

Result: 18,533 epochs, mean 7.8 sats, **median 2.7 m** horizontal error.

**(B) Our georinex GPS-only SPP (consumer u-blox):**
```bash
python -m src.models.spp_rinex          # → results/urbannav_spp.npz  (median ~14 m)
```
Implements broadcast-ephemeris satellite positions, satellite-clock + relativistic correction,
Sagnac rotation, Saastamoinen troposphere, and iterated least squares (see `src/models/spp_rinex.py`
and Appendix A.4).

---

## 8. Sensor fusion (the EKF experiments)

**Synthetic + semi-synthetic study (filter comparison + severity sweep):**
```bash
python -m src.models.ekf_urbannav_runner          # writes results/urbannav_ekf.json
python -m src.utils.make_ekf_urbannav_figures      # fig21 (filters), fig22 (sweep)
```

**Fully-real fusion (uses §7 outputs):**
```bash
python -m src.models.ekf_urbannav_runner --real --both     # trimble + ublox
#   --real            run on real GNSS positions
#   --both            do both receivers
#   (default source: trimble; add --ublox for u-blox only)
```
Outputs per source: `results/urbannav_ekf_real_{trimble,ublox}.json` and `_tracks.npz`
(consumed by the dashboard’s `/api/fusion`).

EKF tuning knobs (`src/models/ekf_9state.py`, `EKF9StateParams`): `r_base`, `r_degraded` (the trust
dial), process noise `q_*`, ZUPT threshold, and the odometry/NHC aiding (`update_odometry_nhc`).

---

## 9. Figures

```bash
python -m src.utils.make_paper_figures             # fig01–fig18, composites (cividis, 300 dpi)
python -m src.utils.make_ekf_urbannav_figures      # fig21 (filters), fig22 (severity sweep)
python -m src.utils.make_inference_comparison       # fig23 (inference-stack comparison)
```
Style: cividis/Beihang palette (single source), 300 dpi, no titles, bold 14 pt labels, (a)/(b)/(c)
panel labels. Index: `results/paper_figures/README.md`.

---

## 10. Run the dashboard

```bash
# Terminal 1 — backend (needs a populated results/ folder)
cd dashboard/server && pip install -r requirements.txt && python main.py        # :8000

# Terminal 2 — frontend
cd dashboard/client && npm install && npm run dev                               # :3000
```
Open **http://localhost:3000**. Production: `npm run build && npm run start`; set
`NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_WS_URL`. Full deployment guide in
[01_APPLICATION_AND_DASHBOARD.md](01_APPLICATION_AND_DASHBOARD.md) §7.

---

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| npm / pip time-outs (China) | use the npmmirror / Tsinghua mirrors (above) |
| Next “Failed to load SWC binary” | `npm install @next/swc-win32-x64-msvc@<ver> --registry=https://registry.npmmirror.com` |
| RTKLIB “no obs data” with `-o` | run from the data dir with a local output path (project path has a space) |
| Dashboard “fusion unavailable” | run `ekf_urbannav_runner.py --real --both` first |
| WebSocket won’t connect | ensure the backend is on :8000 and not blocked by a firewall |

---

## Appendix A — All the formulas

**A.1 Multi-head self-attention**
$$\text{Attention}(Q,K,V)=\text{softmax}\!\left(\tfrac{QK^\top}{\sqrt{d_k}}\right)V,\quad
\text{MHA}=\text{Concat}(head_1,\dots,head_8)W^O$$

**A.2 Focal loss** (γ=1.0, α=[1,2,5])
$$\text{FL}(p_t)=-\,\alpha_t\,(1-p_t)^{\gamma}\log(p_t)$$

**A.3 Metrics**
$$\text{F1}=\frac{2PR}{P+R},\quad
\text{Macro-F1}=\tfrac{1}{3}\sum_c \text{F1}_c,\quad
\text{MCC}=\frac{TP\cdot TN-FP\cdot FN}{\sqrt{(TP{+}FP)(TP{+}FN)(TN{+}FP)(TN{+}FN)}}$$
$$\text{ECE}=\sum_{b}\frac{|B_b|}{N}\,\bigl|\,\text{acc}(B_b)-\text{conf}(B_b)\,\bigr|,\qquad
\text{temperature scaling: } \hat p=\text{softmax}(z/T),\ T=0.4023$$

**A.4 GNSS single-point positioning (SPP)** — receiver position $\mathbf{r}$ and clock $b$ from
pseudoranges $P_i$:
$$P_i = \lVert \mathbf{s}_i-\mathbf{r}\rVert + b - c\,\delta t^{sv}_i + T_i + I_i + \varepsilon_i$$
solved by iterated least squares; satellite position $\mathbf{s}_i$ from broadcast ephemeris
(Keplerian + harmonic corrections), with satellite-clock $\delta t^{sv}=a_{f0}+a_{f1}\Delta t+
a_{f2}\Delta t^2+\delta t_{rel}$, relativistic $\delta t_{rel}=F\,e\sqrt{A}\sin E_k$, and Sagnac
rotation by $\omega_e\cdot(P_i/c)$.

**A.5 Kalman filter** (predict / update)
$$\mathbf{x}^-=f(\mathbf{x}),\quad P^-=FPF^\top+Q$$
$$\mathbf{y}=\mathbf{z}-H\mathbf{x}^-,\quad S=HP^-H^\top+R,\quad K=P^-H^\top S^{-1}$$
$$\mathbf{x}=\mathbf{x}^-+K\mathbf{y},\quad P=(I-KH)P^-$$

**A.6 9-state EKF** state $\mathbf{x}=[x,y,v_x,v_y,\psi,b,b_{ax},b_{ay}]$; IMU-driven motion with
heading $\dot\psi=\omega_z$ and $\dot{\mathbf v}=R(\psi)(\mathbf a_{imu}-\mathbf b_a)$.

**A.7 Adaptive measurement noise** (the prediction→fusion link)
$$R(t)=r_{base}+(r_{deg}-r_{base})\,P(\text{DEGRADED}\,|\,t)$$
small $R$ ⇒ trust GNSS; large $R$ ⇒ coast on the motion model.

**A.8 Odometry + non-holonomic constraint (NHC) aiding** — body-frame velocity
$$\begin{bmatrix}v_{fwd}\\ v_{lat}\end{bmatrix}=R(\psi)^\top\begin{bmatrix}v_x\\ v_y\end{bmatrix},
\qquad v_{fwd}\approx v_{wheel},\quad v_{lat}\approx 0\ (\text{NHC}),\quad
\mathbf v\!\approx\!0\ (\text{ZUPT when stopped})$$

**A.9 Frame note (verified on data):** the IMU yaw rate is compass-azimuth rate (CW-from-North);
the EKF math-heading is CCW-from-East, so $\dot\psi=-\omega_z^{IMU}$ (correlation 0.9997 vs the
reference heading rate).
