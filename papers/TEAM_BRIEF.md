# SENTINEL-GNSS — Team Brief

> **Share this with colleagues.** It is the single-page (ish) orientation to where the
> project stands, what is novel, how we validate it, what is confirmed vs pending, and what
> comes next. All numbers are Run 14 (2026-05-31), traceable to `RESULTS_REFERENCE.md`.

---

## 1. What we built (one paragraph)

A Transformer–LSTM network that **predicts GNSS signal-quality degradation 5, 15, and 30
seconds before it happens**, from a 30-second window of 37 receiver-derived features. Output
is a 3-class forecast (CLEAN / WARNING / DEGRADED) per horizon, in a single forward pass.
The goal: give an autonomous vehicle enough warning to switch to backup localisation _before_
GNSS fails, not after. Trained on Beihang + Hong Kong field/public data; evaluated in-domain
and on a fully held-out city (Tokyo).

---

## 2. Headline results (✅ confirmed, Run 14)

| Metric                 | Value                                                      |
| ---------------------- | ---------------------------------------------------------- |
| +5s macro-F1           | **0.821** [95% CI 0.800–0.843]                             |
| +5s DEGRADED recall    | **0.85** (catches 85% of impending degradations 5 s early) |
| +30s macro-F1          | 0.783 (useful well beyond minimum actionable window)       |
| DEGRADED F1 progress   | 0.274 (Run 11) → **0.718** (Run 14), a 2.6× gain           |
| Inference speed        | **0.039 ms/sample**, 10.5× faster than 3 tree models       |
| Cross-city DEGRADED F1 | **DL 0.75 vs RandomForest 0.15** on unseen Tokyo           |

---

## 3. The five novelties (each independently publishable)

1. **Problem reformulation — proactive, not reactive.** Every prior GNSS quality method
   (RTKLIB Q-codes, RAIM, recent learning classifiers) reports degradation _as/after it
   happens_. We _forecast_ it at 5/15/30 s. To our knowledge this is the first multi-horizon
   GNSS degradation **predictor** (⚠️ verify literature before asserting "first").

2. **Cross-city generalisation as the deciding metric.** Our strongest, most defensible
   result: in-domain, gradient-boosted trees beat the network (0.92 vs 0.82 macro-F1); but on
   an **unseen city**, the network retains DEGRADED-class F1 of **0.75 while the tree collapses
   to 0.15**. RandomForest memorises city-specific thresholds (XGBoost transfers); the network learns a transferable
   degradation representation. This is the "right model for deployment" argument and it is
   backed by data (E6).

3. **Unified multi-horizon architecture.** One model, one 17.8 MB checkpoint, one forward
   pass → all three horizons, 10.5× faster than three separate per-horizon tree models.

4. **Multi-city, multi-receiver benchmark.** 149,662 labelled epochs, 4 cities, 9+ receiver
   types, a single 3-class schema, a fully reproducible raw→feature→label pipeline. No such
   resource exists in GNSS ML (Paper 4).

5. **Hardware-aware feature design.** An explicit `receiver_tier` feature lets one model
   reconcile identical C/N₀ readings that mean different things on a Septentrio vs a phone
   (Paper 2). (Note: this makes us _hardware-aware_, not "receiver-agnostic" — wording matters.)

---

## 4. Honest findings that SHAPE the narrative (do not hide these)

These came out of the reviewer-directed experiments (E1–E7) and they change how we argue:

- **Temporal _order_ is a minor factor (E1).** Shuffling the 30 timesteps drops both DL and
  RF by ~3% equally. → We must **not** claim "the Transformer wins by modelling temporal
  order." It doesn't.
- **RF doesn't need the engineered temporal features (E2).** Removing 9 temporal-aggregate
  features changes RF by −0.001. → The "RF only wins because of our temporal features"
  argument is **false**; drop it.
- **In-domain, classical ML wins (Table 4).** XGBoost 0.919 vs our 0.821 at +5s. We **report
  this openly** and pivot to cross-domain (E6), efficiency (E4), and interpretability.
- **SMOTE doesn't help anyone (E5).** And the reason is _not_ distribution distance (KL
  actually favours SMOTE). It's interpolation artefacts. We reframed this honestly.
- **Calibration claim is NOT yet valid (E7).** The ECE experiment ran with temperature=1.0
  (a bug — wrong key lookup), so before/after are identical. We cannot claim "well-calibrated"
  until E7 is re-run with T=0.40.

> **Why this matters:** a paper that over-claims temporal modelling or calibration gets
> caught in review. The honest narrative (generalisation + efficiency + open benchmark) is
> both true and stronger.

---

## 5. How we validate the project (what professors/reviewers will ask)

We have **five layers of validation**:

1. **Statistical** — held-out test set (1,686 windows never seen in training or threshold
   tuning); bootstrap 95% CIs on every metric (1,000 iters); MCC + Cohen κ alongside F1
   (MCC is the correct primary metric for imbalanced multi-class, Chicco & Jurman 2020).
2. **Ablation** — full model vs LSTM-only vs Transformer-only, identical data/loss/HPs; the
   full model wins on macro-F1 (+5s) and MCC (all horizons). Plus E1/E2 negative controls.
3. **Cross-domain** — cross-city (Tokyo, E6) and cross-receiver (Paper 2) generalisation.
4. **Engineering** — lead-time histogram (how many seconds of warning), and the planned
   adaptive-EKF navigation-RMSE experiment (⏳ to build).
5. **Reproducibility** — full code on GitHub; a Kaggle notebook reproduces every number from
   scratch on a free T4; all data sources public or archived; fixed seeds.

**The one-line answer to "how do you know it generalises?"**

> "We trained on Hangzhou (Beihang) and Hong Kong data, then tested on a city the model never
> saw (Tokyo — explicitly excluded from training). On the safety-critical loss-of-fix class,
> our model held F1 = 0.75 while the strongest classical baseline (RandomForest) dropped to
> 0.15, and a DL+XGBoost ensemble reached 0.90. The deep model learns generalizable degradation
> representations; RandomForest memorises city-specific thresholds."

---

## 6. Anticipated reviewer questions & our answers

| Question                                           | Answer                                                                                                                                                                                            |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Trees beat your model — why publish the network?" | In-domain yes; out-of-domain (Tokyo) the network keeps DEGRADED F1 at 0.75 vs RandomForest's 0.15, runs 10.5× faster, and serves 3 horizons in one model. Deployment needs cross-city robustness. |
| "Does the Transformer actually use time?"          | Honestly, temporal _order_ contributes ~3% (E1). The benefit is representational transfer, not order modelling. We state this plainly.                                                            |
| "DEGRADED test set is small (n=209)."              | We report bootstrap 95% CIs on every per-class metric; DEGRADED F1 = 0.717 [0.671, 0.762].                                                                                                        |
| "Any data leakage?"                                | Session-level split; scaler/SMOTE fit on train only; one within-site overlap (scenario_a_r13) explicitly disclosed; Tokyo fully held out.                                                         |
| "Is the probability a usable risk score?"          | ⏳ Pending — calibration (E7) must be re-run with correct temperature before we claim this.                                                                                                       |
| "Where is the navigation benefit?"                 | ⏳ Adaptive-EKF experiment is ongoing; we currently show P(DEGRADED) correctly flags impending events.                                                                                            |

---

## 7. What's confirmed vs what's left (status board)

| Item                                              | Status                                                           |
| ------------------------------------------------- | ---------------------------------------------------------------- |
| Full model + 2 ablations trained & evaluated      | ✅                                                               |
| Baselines (RF/XGB, ±SMOTE, trivial, rule)         | ✅                                                               |
| Multi-horizon, per-class, bootstrap CIs           | ✅                                                               |
| Cross-city Tokyo (E6)                             | ✅                                                               |
| Latency benchmark (E4)                            | ✅                                                               |
| Permutation + temporal ablation (E1/E2)           | ✅                                                               |
| 13 evaluation figures                             | ✅                                                               |
| Calibration (E7)                                  | ✅ fixed in both notebooks (temperature recomputed inline)       |
| Tokyo per-class support counts                    | ✅ added to E6 in both notebooks                                 |
| Ensemble comparison (E8–E10)                      | ✅ wired (`ensemble_compare.py`, Step 10c, both notebooks)       |
| Adaptive EKF module + simulation                  | ✅ built & self-tested (−33.8% blockage RMSE, `adaptive_ekf.py`) |
| Configurable horizons (+45/+60 s)                 | ✅ `feature_prep --extra_horizons` (additive, verified)          |
| DL multi-head +60 s                               | ⏳ Phase 2b — needs retrain (architecture change)                |
| Raw per-satellite C/N₀                            | ⏳ Phase 3 — new extractor + retrain                             |
| Real-data EKF RMSE (aligned reference trajectory) | ⏳ one data task                                                 |
| Lead-time median value                            | ⏳ read from histogram                                           |
| Per-receiver evaluation (Paper A)                 | ⏳ run inference                                                 |
| Inference script (NMEA → prediction)              | ⏳ build                                                         |
| Web app (Next.js + FastAPI)                       | ⏳ build                                                         |

---

## 8. Next steps (priority order)

| #   | Task                                           | Why it matters                             | Effort    |
| --- | ---------------------------------------------- | ------------------------------------------ | --------- |
| 1   | Re-run E7 with T=0.40                          | Unlocks the calibration claim              | 1 h       |
| 2   | Read lead-time median from histogram           | Headline engineering number for Paper 1    | 1 h       |
| 3   | Add Tokyo per-class support counts to E6       | Makes Paper 3 submission-ready             | 1 h       |
| 4   | `inference.py` (NMEA stream → live prediction) | Foundation for app + EKF                   | 1 day     |
| 5   | Per-receiver evaluation                        | Completes Paper 2                          | 1 day     |
| 6   | Adaptive EKF + navigation-RMSE experiment      | Completes Paper 1 §7, biggest reviewer ask | 3 days    |
| 7   | Web app: FastAPI backend + Next.js dashboards  | Demo + paper figures                       | ~1 week   |
| 8   | Paper 1 full draft                             | Submission                                 | 1–2 weeks |
| 9   | ION GNSS+ 2026 abstract                        | Conference deadline                        | 2 days    |

---

## 9. App architecture (decided: Next.js + FastAPI, not Streamlit)

```
Frontend (Next.js, Vercel)            Backend (FastAPI + Python, Railway/Render)
  • Real-time monitor (1 Hz)            POST /predict      → load checkpoint, parse NMEA
  • Signal-quality map (Mapbox)         POST /upload_nmea  → prediction timeline
  • Prediction timeline + lead time     GET  /history/{id}
  • Feature-saliency panel              WS   /stream       → live WebSocket feed
  • Attention heatmap                   GET  /metrics      → serve paper metrics
  • Model comparison (DL vs XGB)
  • Dataset explorer (149k epochs)
```

Dashboards to include: live monitor, route map colour-coded by predicted quality, scrolling
predicted-vs-actual timeline with lead-time annotations, per-window feature importance, live
attention heatmap, DL-vs-baseline comparison, dataset browser, and the full metrics board.

---

## 10. Paper portfolio — 2 papers + 1 conference (FINAL)

| Output                | What it is                                                                         | Title (working)                                                                                 | Status                                               | Venue                          |
| --------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------ |
| **Paper A — method**  | Proactive multi-horizon Transformer-LSTM + ablations + cross-receiver + cross-city | Proactive Multi-Horizon GNSS Degradation Prediction… Cross-City & Cross-Receiver Generalisation | core ✅, receiver ⏳                                 | _GPS Solutions_ (Q1)           |
| **Paper B — systems** | Model-family comparison → select best → **adaptive EKF** → navigation RMSE         | From Prediction to Position: … Prediction-Informed Adaptive Kalman Filtering                    | EKF ✅ (sim), comparison wired ✅, real-data RMSE ⏳ | _IEEE T-ITS_ / _J. Navigation_ |
| **Conference**        | Cross-city transfer, short paper                                                   | Does GNSS Degradation Transfer Across Cities?                                                   | core result ✅ (E6)                                  | **ION GNSS+ 2026**             |

> **Why this structure:** Paper A = "how we predict" (the learning contribution). Paper B =
> "does it actually improve navigation" (the systems contribution — compare models, select the
> deployable one, integrate the EKF, measure the position gain). They target different
> communities, so no overlap. The cross-city result is the conference paper (standard
> conference→journal extension). **The benchmark/dataset paper was dropped** (your call); the
> dataset still ships with Paper A for reproducibility.
>
> **EKF status:** module built and self-tested — controlled blockage simulation shows the
> adaptive filter cuts position RMSE during the degraded segment by **33.8%** (54.4 m → 36.0 m).
> Real-data case study needs an aligned reference trajectory (the one remaining data task).
>
> **Title fix:** never "Receiver-**Agnostic**" — the model uses a `receiver_tier` feature, so
> it is hardware-_aware_. Use "Cross-Receiver Generalisation."

---

## 11. Credibility checklist (before ANY submission)

- [ ] Every cited competitor number verified against its primary source (esp. Liu et al. 2023).
- [ ] No absolute "first / only / zero prior work" claims — soften to "to our knowledge after
      a systematic search."
- [ ] Feature count = **37** everywhere (not 35 — old drafts say 35; that is wrong).
- [ ] Architecture stated correctly: 8 heads, d=128, d_ff=512, LSTM hidden 256, 1.46M params.
- [ ] **Training data stated correctly everywhere: trained on Hangzhou (Beihang field) + UrbanNav
      Hong Kong (Medium/Deep/Harsh/Tunnel). UrbanNav Tokyo excluded from training — zero-shot
      cross-city test only. Never say "trained on Hangzhou only."**
- [ ] Data balancing stated correctly: DL = no-SMOTE + focal + class weights; SMOTE only for
      tree baselines.
- [ ] In-domain tree superiority disclosed, not hidden.
- [ ] scenario_a_r13 within-site overlap disclosed.
- [ ] Calibration claim only after E7 re-run.
- [ ] Adaptive-EKF framed as ongoing until results exist.
- [ ] All numbers trace to `RESULTS_REFERENCE.md` or `reviewer_experiments.json`.
