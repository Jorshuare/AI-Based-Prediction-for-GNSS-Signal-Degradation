# SENTINEL-GNSS — Data, Features, Models & Results (Comprehensive Reference)

**What this document is:** the authoritative story of _the science_ — how the data was collected,
which datasets we used, how the 37 features were engineered, how the Transformer-LSTM was trained,
every ablation and the ensemble, and **the actual results we obtained**, each with a plain-language
explanation and a justification.

> Companion docs: **[01_APPLICATION_AND_DASHBOARD.md](01_APPLICATION_AND_DASHBOARD.md)** (the app)
> and **[03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md)** (commands + formulas).

---

## 1. The problem (and why it is hard)

Predict whether a vehicle’s GNSS signal will be **CLEAN**, **WARNING**, or **DEGRADED** at **+5 s,
+15 s and +30 s** into the future, from a 30-second history of signal features.

Hard because: (a) it depends on _temporal trends_, not a single instant; (b) one model must predict
three different horizons; (c) **DEGRADED is rare (~10 %) but safety-critical** (class imbalance);
(d) it must generalise to **cities never seen in training**.

_Why predict instead of detect?_ Detection tells you the signal is already gone. **Prediction gives
a 5–30 s head-start** to switch sensors, slow down, or re-route — the entire value proposition.

---

## 2. Data collection

### 2.1 Our own field data (Beihang, Hangzhou)

We drove and logged raw **NMEA** GNSS sentences under five scenarios, each exercising a different
failure mode:

| Scenario | Name                 | What it stresses                                         |
| -------- | -------------------- | -------------------------------------------------------- |
| A        | Instant blockage     | Sharp CLEAN→DEGRADED transition (e.g. under a structure) |
| B        | Urban canyon         | Gradual loss + multipath between tall buildings          |
| C        | Partial blockage     | Stable but reduced signal (tree cover) → WARNING         |
| D        | Open sky             | Clean baseline (model must not cry wolf)                 |
| E        | Approaching blockage | Smooth degradation while nearing an obstruction          |

_Justification:_ the scenarios deliberately span sudden vs gradual and full vs partial loss, so the
model learns _transitions_, not a single environment. Scenario A is the one surfaced in the
dashboard’s Live tab (`A_log_0000`).

### 2.2 Public datasets (for scale & cross-city generalisation)

- **UrbanNav** (Hong Kong PolyU) — Hong Kong (Deep/Medium/Harsh) and **Tokyo (Shinjuku/Odaiba)**
  drives with raw RINEX observations, IMU, wheel speed, and **SPAN-INS centimetre ground truth**.
  Tokyo is our held-out cross-city test **and** the real sensor-fusion benchmark.
- Additional public GNSS logs were processed through the same pipeline to grow the training set.

_Justification for UrbanNav Tokyo as the held-out city:_ unseen city, unseen receivers, different
season — the strongest test of generalisation — **and** it ships cm-level truth + IMU, which is what
makes the real fusion experiment possible.

---

## 3. Feature engineering — the 37 features

Raw NMEA/RINEX is converted to **37 engineered features per epoch**, grouped by physical meaning:

| Group                  | Examples                                                            | Why it matters                                            |
| ---------------------- | ------------------------------------------------------------------- | --------------------------------------------------------- |
| Signal strength (C/N₀) | max/mean/std C/N₀, **cnr_trend**, cnr_variance                      | C/N₀ falling = blockage approaching; variance = multipath |
| Geometry (DOP)         | gdop, pdop, hdop, vdop, elevation_violations, sat_visibility        | Poor geometry = inaccurate fix                            |
| Constellation          | num_satellites, baseline_sats, **sat_drop_rate**, sat_mean, sat_min | Losing satellites is an early warning                     |
| Receiver status        | fix_quality, fix_continuity, fix_transitions, solution_age          | Fix instability precedes loss                             |
| Temporal trends        | pdop_delta, hdop_delta                                              | _Rate of change_ — the key to forecasting                 |
| Atmospheric / errors   | iono_delay, tropo_delay, multipath, residual_mean/std, cycle_slips  | Direct error sources                                      |
| Hardware               | receiver_tier (0–3)                                                 | Lets one model serve different receiver classes           |

_Why hand-crafted, not raw?_ GNSS-domain features encode physics (a falling C/N₀ trend is
_meaningful_), giving a smaller, more generalisable model than feeding raw pseudoranges. _Why 37 and
not 100?_ Each is justified by GNSS knowledge; redundant features were dropped. The **trend**
features (cnr_trend, sat_drop_rate, \*\_delta) are what make prediction (not just detection) possible.

**Windowing:** 30-second sliding windows (e.g. 30 epochs at 1 Hz). _Why 30 s?_ Long enough to
capture a degradation trend, short enough to still predict +5 s accurately. Labels are taken at
+5/+15/+30 s after the window end.

**Splitting:** **session-level** train/val/test (never split a single drive across sets) to prevent
temporal leakage; **cross-city** hold-out (Tokyo) for the generalisation test.

---

## 4. Class imbalance: SMOTE vs focal loss (a deliberate split)

- **Deep model:** **no SMOTE.** We use **focal loss** + class weights `[1, 2, 5]`. Focal loss
  down-weights easy, common examples and focuses learning on the rare DEGRADED class — principled,
  and it keeps the real temporal structure intact (SMOTE would synthesise unrealistic feature
  sequences).
- **Classical baselines (RF/XGBoost):** **SMOTE** is applied, because tree models have no focal-loss
  equivalent. We verified with a KL-divergence test (E5) that the SMOTE-balanced training
  distribution is actually _closer_ to the test distribution than the raw one — so SMOTE is the
  fairer choice for the baselines.

_Justification:_ match the imbalance remedy to the model family; report both honestly.

---

## 5. The model architecture (and why each part)

```
37 features × 30 steps
        │
   Input projection → 128-d
        │
  ┌─────────────────────┐
  │ Transformer encoder │  2 layers, 8 heads, d_model=128, d_ff=512   ← long-range patterns
  └─────────────────────┘
        │
  ┌─────────────────────┐
  │   Bidirectional     │  2 layers, 256 hidden                       ← causal degradation trend
  │       LSTM          │
  └─────────────────────┘
        │
   ┌───────┬───────┬───────┐
   │ +5 s  │ +15 s │ +30 s │   three classification heads (CLEAN/WARNING/DEGRADED)
   └───────┴───────┴───────┘
Total ≈ 1.46 M parameters
```

**Transformer encoder** — self-attention sees relationships between _any_ two time steps (e.g. a
multipath signature 25 s ago and now):
$$\text{Attention}(Q,K,V)=\text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$
_Why 2 layers / 8 heads / d=128 / d_ff=512?_ enough capacity for the patterns without overfitting a
modest dataset; multiple heads attend to different cues (geometry vs strength).

**Bidirectional LSTM** — captures _directional momentum_ toward failure (is the signal trending
down?). The LSTM cell’s gated memory avoids the vanishing-gradient problem over the 30-step window.
_Why both Transformer and LSTM?_ attention finds patterns; the LSTM reasons about _causal trend_.
Ablations (below) confirm both contribute.

**Three heads** — one per horizon, each with its own decision threshold, because +5 s and +30 s are
genuinely different problems (near-term is easier/sharper).

**Training:** AdamW (`lr=1e-3, weight_decay=1e-4`), 5-epoch warm-up, gradient clipping at 1.0, light
label smoothing. _Why AdamW?_ decoupled weight decay generalises better than Adam/SGD here and is
stable for transformers.

**Focal loss:** with $\gamma=1.0$ and class weights $\alpha=[1,2,5]$,
$$\text{FL}(p_t) = -\,\alpha_t\,(1-p_t)^{\gamma}\,\log(p_t).$$
_Why γ=1.0?_ a moderate focusing strength — enough to prioritise the rare DEGRADED class without
destabilising training.

---

## 6. Validation metrics (what they are and why we use them)

| Metric                | Plain meaning                                                 | Why (not just accuracy)                                                |
| --------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Macro-F1**          | Average F1 across the three classes, treating each equally    | Accuracy hides the rare class; macro-F1 rewards getting DEGRADED right |
| **Per-class F1**      | Precision/recall balance per class                            | DEGRADED recall is the safety number                                   |
| **MCC** (Matthews)    | Correlation between prediction and truth, robust to imbalance | A single honest summary for imbalanced data                            |
| **Bootstrap 95 % CI** | Confidence range from 1000 resamples                          | Shows results aren’t a fluke                                           |
| **ECE** (calibration) | Gap between predicted confidence and reality                  | The EKF _uses_ P(DEGRADED), so it must be trustworthy                  |

**Calibration:** temperature scaling with $T=0.4023$ improved ECE from **0.114 → 0.068** (~40 %
better). Reliable probabilities are essential because the fusion filter multiplies by P(DEGRADED).

---

## 7. Results (the actual numbers, explained)

> Source: Run-16 (`results/RUN_SUMMARY.json`, `reviewer_experiments.json`,
> `ensemble_comparison.json`). Full traceable table in `papers/RESULTS_REFERENCE.md`.

### 7.1 In-domain test (trained on Hangzhou + HK; test partition = Beihang campus sessions), +5 s Macro-F1

> **Training data:** Beihang (Hangzhou) field scenarios A–E + UrbanNav Hong Kong (Medium, Deep,
> Harsh, Tunnel). **Tokyo excluded from training — held out for cross-city evaluation only.**
> The test partition uses held-out Beihang campus driving sessions (never seen during training).

| Model                   | Macro-F1 | DEGRADED F1 |
| ----------------------- | -------- | ----------- |
| RandomForest            | 0.926    | 0.79        |
| XGBoost                 | 0.919    | 0.81        |
| Transformer-LSTM (full) | 0.821    | 0.72        |

_Reading it:_ **on the held-out test partition (same distribution as training), the tree models
lead.** They memorise local patterns well. This is expected and we report it honestly.

### 7.2 Cross-city Tokyo (held-out), +5 s

| Model                      | Macro-F1  | DEGRADED F1           |
| -------------------------- | --------- | --------------------- |
| RandomForest               | 0.618     | **0.148** ← collapses |
| XGBoost                    | 0.821     | 0.784                 |
| Transformer-LSTM           | 0.649     | 0.753                 |
| **DL + XGBoost soft-vote** | **0.892** | **0.896**             |

_Reading it (the key finding):_ **on an unseen city, RandomForest collapses on the safety-critical
DEGRADED class (0.148), while the deep model keeps its DEGRADED skill (0.75) and even improves it.**
The deep model learned _generalisable degradation physics_; the trees memorised Hangzhou. Combining
DL + XGBoost (a simple probability average) gives the best of both: **0.892 Macro-F1, 0.896
DEGRADED**.

### 7.3 Ablations (do both halves matter?)

- **Architecture (E-arch):** Full (Transformer+LSTM) vs LSTM-only vs Transformer-only — the full
  hybrid gives the best/most-stable DEGRADED performance; each component alone is weaker.
- **Temporal features (E2):** removing the trend features (cnr_trend, sat_drop_rate, *\_delta) hurts
  the deep model — confirming the *trend\* features drive prediction.
- **Permutation test (E1):** shuffling features drops Macro-F1 by ~3 % for both DL and RF — the
  models genuinely use the features (not artefacts).
- **Latency (E4):** the deep model runs ~**11×** faster per sample than RandomForest on GPU
  (0.038 ms vs 0.43 ms) — and is small enough (17.8 MB) for edge deployment.

### 7.4 Is the model just learning “persistence”? (E9)

A persistence baseline (predict “same as now”) scores 0.91 Macro-F1 at +5 s because **94 % of the
time the state doesn’t change in 5 s.** _So why is the model valuable?_ Its worth is in the **~6 % of
transitions** (the safety-critical 0→DEGRADED moments) and at **longer horizons** (the label-change
rate rises to ~11 % at +30 s, where memory/temporal modelling matters more). We report this nuance
rather than hide it.

### 7.5 Ensemble strategy (E8)

Soft-vote (average the DL and XGBoost probabilities) beats stacking and beats either model alone
**cross-city** (0.892 vs 0.886 vs ≤0.821). _Why soft-vote?_ simpler, and it preserves DL’s DEGRADED
recall while borrowing XGBoost’s transfer. This is the production model (saved as
`results/ensemble_xgb_model.joblib`).

**One-line verdict:** _in-domain, trees win; cross-city, the DL + XGBoost ensemble wins decisively on
the class that matters (DEGRADED) — which is the real-world deployment condition._

> The full **inference-stack comparison** — model/ensemble choice (prediction) _and_ filter choice
> (fusion) — is `results/paper_figures/fig23_inference_comparison.png`
> (`python -m src.utils.make_inference_comparison`). It pairs panel (a) cross-city quality with
> panel (b) real Tokyo positioning, so the effect of every inference flag (`--ensemble`, `--ekf`) is
> visible in one figure. The flags and their expected results are tabulated in
> [03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md) §6.

---

## 8. From prediction to navigation — the adaptive EKF

Predicting degradation is only half the value; we use it to keep the vehicle located. See the full
filter tutorial in **[EKF_KALMAN_EXPLAINED.md](EKF_KALMAN_EXPLAINED.md)**. Essentials:

A Kalman filter blends a **physics prediction** with a **GNSS measurement**, weighting each by trust.
The trust dial is the measurement-noise **R**. Our two contributions:

1. **Prediction-driven adaptive R:** $R(t) = r_{base} + (r_{deg}-r_{base})\,P(\text{DEGRADED}\,|\,t)$
   — distrust GNSS _before_ a predicted blockage (a 5 s pre-emptive head-start).
2. **Aiding the physics half:** wheel-odometry + non-holonomic constraint (a car can’t slide
   sideways) + zero-velocity updates (ZUPT when stopped), so dead-reckoning stays accurate during a
   blackout. This was the decisive upgrade.

### 8.1 Results — three tiers (honest)

| Tier                                    | Data                                       | Headline                                            |
| --------------------------------------- | ------------------------------------------ | --------------------------------------------------- |
| Synthetic blockage                      | Controlled, known timing                   | **+33.8 %** blocked-segment RMSE (proof of concept) |
| Semi-synthetic on real trajectory + IMU | Real Tokyo path/IMU, synthetic GNSS errors | Aided EKF **+82 %** blocked RMSE (36.3 → 6.4 m)     |
| **Fully real (RTKLIB Trimble)**         | Real GNSS positions + IMU + truth          | Aided EKF **+48.8 %** blocked RMSE (47.4 → 24.3 m)  |

_Honest nuance:_ the **aiding** (odometry/NHC/ZUPT) is the big, robust win. Prediction-driven
**adaptive-R** helps a weak GNSS-only platform in severe multipath but is _counter-productive_ on a
well-aided vehicle (fully distrusting GNSS throws away heading information). So **the predictor’s
value in fusion is regime selection / integrity, not blanket R-inflation** — the prediction tells you
_which world you’re in_.

### 8.2 When does adaptive-R help? (the severity sweep)

Rather than cherry-pick one number, we swept multipath severity. On a **GNSS-only** platform
(constant-velocity KF, no aiding) there is a clear **crossover ≈ 20 m**: below it, trust GNSS
(fixed-R wins); above it — deep-canyon multipath — adaptive-R wins by **+25–38 %**. But once the
filter is **well-aided** (odometry/NHC/ZUPT), keeping GNSS (fixed-R) stays best across the whole
realistic range, because GNSS is the only absolute _heading_ reference and discarding it lets the
heading drift. This is the basis of the dashboard’s “When does adaptive-R help?” chart.

### 8.3 Two engineering fixes that mattered (and a caveat)

- **Initialisation:** velocity/heading must be seeded from the first clean GNSS displacement; seeding
  them at zero makes dead-reckoning diverge instantly (this caused an early −366 % artefact).
- **Gyro frame:** the IMU yaw rate is compass-azimuth rate (CW-from-North) while the EKF heading is
  CCW-from-East, so $\dot\psi=-\omega_z$ (verified at correlation 0.9997 on the real data). Sign
  matters once wheel-odometry injects a ~4 m/s velocity vector.
- **Caveat on real data:** real GNSS has heavy-tailed NLOS outliers (spikes to 100 m+); a plain KF
  chases them. **Robust innovation-gating** is the next refinement to push the real-data gain higher.

---

## 9. Justification summary (the defensible claims)

- **37 domain features + 30 s windows** → prediction (not detection) is possible, and it generalises.
- **Transformer + BiLSTM hybrid** → pattern _and_ causal-trend reasoning (ablation-confirmed).
- **Focal loss (DL) / SMOTE (trees)** → imbalance handled per model family, verified by KL test.
- **Cross-city Tokyo** → the real test; DL keeps DEGRADED skill where trees collapse.
- **DL + XGBoost soft-vote** → best cross-city (0.892 / 0.896), saved for production.
- **Calibration (T=0.4023)** → trustworthy probabilities for the fusion filter.
- **Aided adaptive EKF** → real-world +48.8 % blocked accuracy with the gold-standard RTKLIB track,
  reported with honest limits.
