# Paper B — Systems Paper: Model Comparison → Selection → Adaptive EKF (Full Section Plan)

> **This replaces the former benchmark paper** (dropped per team decision). Paper B is now the
> **systems/application** paper: it fairly compares model families, selects the deployable
> model, integrates it into a prediction-informed **adaptive EKF**, and measures the
> **navigation accuracy gain**. This is the paper that proves the whole project _matters_ —
> prediction is only useful if it improves positioning.

**Working title:**
**"From Prediction to Position: Comparing Learning Models and a Prediction-Informed Adaptive
Kalman Filter for Resilient GNSS Navigation in Degraded Environments"**

**Target venue:** _IEEE Transactions on Intelligent Transportation Systems_ (Q1) or
_Journal of Navigation_ (Cambridge). Different community from Paper A (method) → no overlap.

---

## Abstract (draft — uses confirmed numbers; EKF real-data RMSE ⏳)

> A proactive GNSS degradation predictor is only valuable if it improves navigation. We first
> conduct a fair comparison of model families — gradient-boosted trees, deep sequence models
> (Transformer–LSTM and ablations), and their ensembles — for predicting GNSS signal-quality
> 5–30 s ahead, evaluating both in-domain and on an unseen city. We find that trees lead
> in-domain (Macro-F1 0.92 vs 0.82) but **fail to transfer** (cross-city DEGRADED F1 0.15),
> whereas the Transformer–LSTM retains DEGRADED F1 0.75 across cities and runs 10.5× faster as
> a single unified multi-horizon model; static ensembles do not reconcile the two regimes. We
> therefore select the deep model for deployment and integrate its P(DEGRADED) output into an
> **adaptive Extended Kalman Filter** that inflates GNSS measurement noise pre-emptively. In a
> controlled blockage simulation the adaptive filter reduces position RMSE during the
> degraded segment by **33.8%** versus raw GNSS (54.4 m → 36.0 m) and 21% versus a fixed-gain
> EKF; a real-data case study is reported on the Beihang field collection. ⏳ (Insert
> real-data RMSE when the aligned reference trajectory is processed.)

---

## 1. Introduction

- Prediction without action is academic; the contribution is **closed-loop**: predict → adapt
  the filter → measurably better position.
- Two questions: (Q1) which model should we deploy? (Q2) does feeding its prediction into the
  navigation filter actually help, and by how much?

## 2. Related Work

- Adaptive Kalman filtering for GNSS/INS (innovation-based R adaptation, variance inflation).
- Fault-detection / RAIM (reactive) vs predictive trust adaptation (ours).
- Trees vs deep nets on tabular/sequence data (Grinsztajn et al., 2022).
- ⚠️ VERIFY all competitor numbers against primary sources.

## 3. Model-Family Comparison (the selection rationale)

### 3.1 Candidates

Trivial, C/N₀ rule, RandomForest, XGBoost (±SMOTE), LSTM-only, Transformer-only,
Transformer–LSTM (full), soft-vote ensemble, stacking ensemble.

### 3.2 Protocol

Identical windows/splits; in-domain test **and** cross-city (Tokyo); Macro-F1, MCC,
per-class F1, bootstrap CIs; inference latency.

### 3.3 Results (✅ confirmed Run 15 — RESULTS_REFERENCE §7, §10c)

> **Training corpus:** Hangzhou (Beihang field Scenarios A–E) + UrbanNav Hong Kong (Medium,
> Deep, Harsh, Tunnel) — 62,413 windows. **UrbanNav Tokyo: excluded from training; zero-shot
> cross-city test only.**

- **In-domain test (Beihang campus partition, +5 s Macro-F1):** RF 0.926, XGB 0.919, soft-vote 0.911, DL 0.822 — trees lead.
- **Cross-city zero-shot (Tokyo Shinjuku, +5 s):** **soft-vote 0.892**, stacking 0.886, XGB 0.821, DL 0.649,
  RF 0.618. On DEGRADED: **soft-vote 0.896**, XGB 0.784, DL 0.753, **RF 0.148**.
- **E8 (headline):** a **DL + XGBoost soft-vote ensemble beats every single model cross-city**
  (and on the safety-critical DEGRADED class) — DL and XGB make complementary errors that
  averaging corrects. Trees lead in-domain; the ensemble leads where it matters (unseen city).
- **Correction:** it is **RandomForest specifically** that collapses cross-city (DEGRADED
  0.148); **XGBoost transfers well** (0.784). State "RandomForest-specific", not "trees".
- **E9 persistence:** at +5 s the label is unchanged 94.4% of the time → a persistence baseline
  scores 0.908. Report persistence as a baseline; the models' value is transitions + longer
  horizons.
- **E1/E2:** temporal _order_ contributes ~3%; removing temporal features doesn't hurt RF →
  the value is representation transfer, not memory.

### 3.4 Selection ⭐

**Deploy the DL + XGBoost soft-vote ensemble.** It is competitive in-domain (0.911) and the
**best model cross-city** (macro 0.892, DEGRADED 0.896) — exactly the robustness a deployed AV
system needs. This ensemble is what we integrate into the adaptive EKF (§4). (Pure DL remains
the choice if a single lightweight model is mandatory: 17.8 MB, ~9.5× faster than 3 trees.)
Future work: confidence-gated fusion to also top the in-domain leaderboard.

## 4. Prediction-Informed Adaptive EKF

### 4.1 Filter

2-D constant-velocity EKF; state [x, y, vx, vy]; GNSS position measurements.
Implemented in `src/models/adaptive_ekf.py`.

### 4.2 Adaptation law

Measurement noise std interpolates base→degraded with P(DEGRADED):
`σ_R = σ_base + (σ_deg − σ_base)·P(DEGRADED)`. High predicted degradation ⇒ distrust GNSS,
lean on the motion model (proactive dead-reckoning) — _before_ the fix corrupts.

### 4.3 Compared strategies

(a) GNSS-only, (b) fixed-R EKF, (c) adaptive EKF (ours).

### 4.4 Results

- **Controlled simulation (✅ runs now, `results/ekf_demo.json`):** blockage epochs 120–180,
  predictor warns from epoch 115. Blockage-segment RMSE: GNSS-only 54.4 m → fixed-EKF 45.6 m →
  **adaptive-EKF 36.0 m (−33.8% vs GNSS, −21% vs fixed)**. Overall RMSE 25.8 → 21.5 → 17.0 m.
- **Real-data case study (⏳):** apply to a Beihang field run with a reference trajectory and
  per-epoch P(DEGRADED). Report RMSE during real blockage events. _(Needs aligned
  reference/RTK trajectory — the one remaining data step.)_

### 4.5 Figures

- `fig_ekf_trajectory.pdf` — true vs GNSS vs fixed vs adaptive during blockage (⏳ create).
- `fig_ekf_rmse_bar.pdf` — RMSE by strategy, overall + degraded segment (⏳ create).

## 5. Discussion

- The selection result + EKF gain together justify the architecture choice on _deployment_
  grounds, not in-domain leaderboard score.
- Honest limits: simulation first, real-data case study second; constant-velocity model is a
  simplification; gating ensemble left to future work.

## 6. Conclusion

Selecting for cross-domain robustness and feeding prediction into the filter yields a
measurable navigation improvement during degradation — the practical payoff of proactive
prediction.

---

## Status & Dependencies

- **EKF module:** ✅ built and self-tested (`src/models/adaptive_ekf.py`, `--demo`).
- **Comparison experiments (E8–E10):** ✅ wired into both notebooks via
  `src/models/ensemble_compare.py`; numbers populate on next run.
- **Real-data EKF case study:** ⏳ needs an aligned (gnss_xy, reference_xy, p_degraded)
  sequence — the one remaining data task. `run_ekf_experiment(...)` already accepts it.
- **Figures:** ⏳ trajectory + RMSE bar charts from the EKF outputs.

> **Note on the dataset/benchmark:** dropped as a standalone paper, but the multi-city dataset
> is still **released alongside Paper A** (data + pipeline on GitHub/Zenodo) so the work is
> reproducible and citable — without spending a separate paper slot on it.
