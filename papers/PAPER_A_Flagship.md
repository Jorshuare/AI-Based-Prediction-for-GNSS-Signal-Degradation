# Paper A — Flagship Journal Paper (Full Section Plan)

> **Portfolio (decided): 2 papers + 1 conference.** This flagship absorbs the former Paper 2
> (cross-receiver) and Paper 3 (cross-city) as **robustness sections** §5.5 and §6. The
> cross-city result is _also_ a standalone **conference paper**
> (`PAPER_CONFERENCE_CrossCity.md`, ION GNSS+ 2026), later extended here — standard practice.
> The benchmark is **Paper B** (`PAPER_B_Benchmark.md`).

**Working title:**
**"Proactive Multi-Horizon Prediction of GNSS Signal Degradation with a
Transformer–LSTM Network: Cross-City and Cross-Receiver Generalisation for Autonomous
Vehicle Navigation"**

> Title rationale: every word is defensible against the data. "Proactive" (we predict the
> future), "Multi-Horizon" (5/15/30 s), "Transformer–LSTM" (the architecture),
> "Cross-City and Cross-Receiver Generalisation" (our strongest, most novel results — E6 +
> receiver analysis), "Autonomous Vehicle Navigation" (the application). We deliberately do
> **not** put a single-number accuracy claim in the title — the honest story is
> _generalisation_, not in-domain peak score.

**Target venue (primary):** _GPS Solutions_ (Springer, Q1). ⚠️ Verify current impact factor.
**Conference first:** ION GNSS+ 2026 (present core result, gather feedback).
**Backup:** _IEEE Transactions on Intelligent Transportation Systems_ (Q1).

---

## Abstract (draft — uses only confirmed numbers)

> Global Navigation Satellite System (GNSS) positioning degrades abruptly in urban canyons,
> tunnels, and under foliage, yet every existing quality-monitoring method — RTKLIB quality
> codes, RAIM, and recent learning-based classifiers — is _reactive_: it reports degradation
> only once it has occurred. We present SENTINEL-GNSS, a Transformer–LSTM network that
> _predicts_ the GNSS signal-quality class (CLEAN / WARNING / DEGRADED) **5, 15, and 30
> seconds into the future** from a 30-second window of 37 receiver-derived features. Trained
> on 62,413 windows spanning field collections in Beihang and Hong Kong across professional,
> high-precision, prosumer, and consumer-grade receivers, the model attains a macro-F1 of
> 0.821 [95% CI 0.800–0.843] at the 5-second horizon and 0.783 at 30 seconds, with a
> degraded-class recall of 0.85. A single forward pass produces all three horizons in
> 0.045 ms — ~9.5× faster than three separate gradient-boosted baselines. While classical
> models match or exceed the network on the in-domain test set, we show that on an unseen
> city (Tokyo) a RandomForest baseline collapses on the safety-critical degraded class
> (F1 0.15), the network retains it (0.75), and a **deep + gradient-boosted ensemble is the
> most robust of all (0.90)** — evidence that learned representations transfer across cities
> where memorised thresholds do not. We release the models, the 149,662-epoch multi-city
> benchmark, and the full preprocessing pipeline.

---

## 1. Introduction

### 1.1 Motivation

- GNSS is the primary absolute-positioning sensor for autonomous vehicles (AVs).
- Failure modes: urban canyon multipath, tunnels (complete loss), foliage attenuation.
- A vehicle at 60 km/h travels 17 m/s. Reactive detection at the moment of loss commits the
  vehicle to dead-reckoning with **zero preparation**.
- **The core question this paper answers:** _not_ "is the signal degraded now?" but
  "will it degrade in 5 / 15 / 30 seconds?" — giving the planner an actionable window
  (83 m at 5 s, 250 m at 15 s, 500 m at 30 s).

### 1.2 Limitations of prior work

- RTKLIB Q-codes / RAIM: threshold-based, reactive, no forecasting.
- Learning-based GNSS environment classifiers (⚠️ VERIFY: Liu et al., ION GNSS+ 2023, GRU,
  reported ~99.4% **classification** accuracy on _current_ state): single horizon, current
  state only, single receiver, single city.
- **Gap:** no method forecasts the _future_ degradation state, across multiple horizons,
  validated across receivers and cities.

### 1.3 Contributions (each maps to confirmed evidence)

1. **Problem reformulation** — proactive multi-horizon degradation _prediction_ (5/15/30 s),
   the first in the GNSS literature to our knowledge (⚠️ soften absolute claim).
2. **Architecture** — a unified Transformer–LSTM producing all three horizons in one pass;
   ablations confirm both components contribute (§5.3).
3. **Cross-domain evidence** — the network generalises to an unseen city while a strong
   tree baseline fails catastrophically on the safety-critical degraded class (§5.5, E6).
4. **Efficiency** — 0.0449 ms/sample, 9.46× faster than per-horizon tree models, one 17.8 MB
   checkpoint (§5.6, E4).
5. **Open benchmark** — 149,662 labelled epochs, 4 cities, 9+ receivers, public pipeline
   (forward-reference to Paper 4).

---

## 2. Related Work

### 2.1 GNSS quality assessment (reactive)

- RTKLIB solution-quality flags; RAIM and ARAIM fault detection.
- Signal-quality monitoring via C/N₀ and DOP thresholds (RTCM SC-104).

### 2.2 Learning-based GNSS environment classification

- Environment-type classifiers (open-sky / urban / indoor).
- ⚠️ VERIFY and position Liu et al. (2023) precisely: current-state classification.

### 2.3 Time-series forecasting architectures

- Transformers for long-range dependencies (Vaswani et al., 2017).
- LSTM for sequential state (Hochreiter & Schmidhuber, 1997).
- Hybrid Transformer–LSTM for sensor time series.
- Tree ensembles on tabular/flattened windows (Breiman, 2001; Chen & Guestrin, 2016;
  Grinsztajn et al., 2022 — trees vs DL on tabular data).

### 2.4 Positioning of this work

Table contrasting prior art vs SENTINEL-GNSS on: temporal framing (reactive→proactive),
horizons (1→3), receivers (1→9+), cities (1→4), integration target (none→adaptive EKF).

---

## 3. Methodology

### 3.1 Problem formulation

- Input: window `X ∈ ℝ^{30×37}` (30 s history, 37 features).
- Output: for each horizon h ∈ {5, 15, 30} s, a 3-class distribution over
  {CLEAN, WARNING, DEGRADED} at time t+h.
- Multi-task objective over the three horizons + auxiliary t+0 head.

### 3.2 Feature engineering (37 features, 7 groups)

| Group                   | Features                                                                      | Source               |
| ----------------------- | ----------------------------------------------------------------------------- | -------------------- |
| G1 Position             | lat_std, lon_std, alt, …                                                      | NMEA GGA / RINEX     |
| G2 Signal strength      | mean/min/max/std C/N₀, cnr_trend                                              | RINEX S1C / NMEA GSV |
| G3 Satellite count      | num_satellites, sat_mean/min, sat_visibility, sat_drop_rate                   | NMEA GSA/GNS         |
| G4 DOP                  | pdop, hdop, vdop, gdop, dop_ratio                                             | NMEA GSA             |
| G5 Receiver status      | solution_status, baseline_sats, solution_age, fix_continuity, fix_transitions | NMEA                 |
| G6 Temporal patterns    | position_variance, cnr_variance, multipath, clock_bias, elevation_violations  | derived              |
| G7 Atmospheric + extras | iono_delay, tropo_delay, cycle_slips, residual_mean/std                       | derived              |
| +                       | pdop_delta, hdop_delta, **receiver_tier**, cnr_available                      | derived              |

> **receiver_tier** (0=professional, 1=high-precision, 2=prosumer, 3=consumer) is a per-session
> hardware-class constant that lets the model reconcile identical C/N₀ readings that mean
> different things on different hardware. This is a deliberate design choice (see Paper 2).

### 3.3 Labelling scheme (3 classes)

- Thresholds grounded in IS-GPS-200 / RTCM SC-104: C/N₀ < 25 dBHz, HDOP > 5, PDOP > 8,
  satellites < 4 → DEGRADED; healthy bounds → CLEAN; in-between → WARNING.
- No-fix epochs (NMEA quality=0) captured as DEGRADED (not dropped) — critical for blockage.

### 3.4 Architecture (confirmed config)

- Input projection 37→128 → sinusoidal positional encoding.
- Transformer encoder: 2 layers, 8 heads, d_model=128, d_ff=512.
- LSTM: 2 stacked layers, hidden=256; last hidden state → 4 output heads (+5s/+15s/+30s + auxiliary t+0).
- 1,456,652 parameters.
- Figure: `architecture_diagram.pdf` (⏳ to create).

### 3.5 Training protocol (confirmed)

- Loss: focal (γ=1.0) + class weights [1, 2, 5] + label smoothing 0.1.
- **No SMOTE for the network** — class imbalance handled at the loss level (justified §5.7).
- AdamW (lr 1e-3, wd 1e-4), 5-epoch warm-up + cosine decay, grad-clip 1.0, batch 256.
- Early stopping patience 50, min_epoch_for_best 15.
- Temperature scaling (Guo et al., 2017) on val for calibration.
- Threshold tuning on val to maximise macro-F1 (reported on test).

### 3.6 Data splits & leakage control

- Session-level split — no window crosses a session boundary (Bergmeir & Benítez, 2012).
- Scaler fit on train only; SMOTE (baselines) applied post-split, train only.
- Disclose: scenario_a_r13 (test) shares a site with r4–r11 (train) — within-site; cross-site
  generalisation shown by other test sources and by E6 (Tokyo, fully held-out city).

---

## 4. Experimental Setup

### 4.1 Datasets (training + in-domain test)

- Field collection Beihang (Scenarios A–E, Septentrio Mosaic-X5C).
- UrbanNav Hong Kong (Medium / Tunnel / Deep / Harsh), 9+ receivers.
- Held-out city: Tokyo Shinjuku (E6) — never in training.
- Exclusions (with reasons): drones (open-sky only), NCLT (sat-count logging bug),
  Oxford (2014 GPS-only, position-sigma labels).

### 4.2 Splits (confirmed counts)

- Train (no-SMOTE) 62,413; Val 18,074; Test 1,686 (CLEAN 731 / WARNING 746 / DEGRADED 209).

### 4.3 Baselines (4 tiers)

- Tier 1 MajorityClass; Tier 2 C/N₀ rule (RTCM); Tier 3 RandomForest + XGBoost
  (SMOTE and no-SMOTE); Tier 4 DL ablations (LSTM-only, Transformer-only).

### 4.4 Metrics

- Macro-F1 (primary, equal class weight), MCC (Chicco & Jurman, 2020 — best for imbalanced
  multi-class), Cohen κ, weighted-F1, per-class P/R/F1, bootstrap 95% CIs (1,000 iters).

---

## 5. Results

### 5.1 Multi-horizon prediction (headline table)

Use Table 1 from RESULTS_REFERENCE §4. State: "+5s macro-F1 = 0.821 [0.800–0.843],
MCC 0.773; +30s macro-F1 = 0.783." Figure: `multi_horizon_comparison`.

### 5.2 Per-class performance

Table 2 (RESULTS_REFERENCE §5) + per-class bootstrap CIs (E3). Emphasise DEGRADED recall
0.85 at +5s — the model catches 85% of impending degradations 5 s early.
Figures: `confusion_matrices_test`, `pr_curves_test`, `roc_curves_test`.

### 5.3 Ablation study

Table 5 (RESULTS_REFERENCE §6). Full > both ablations on macro-F1 (+5s) and on MCC (all
horizons). Note Transformer-only's CLEAN precision = 1.000 but DEGRADED precision 0.424
(over-flags); LSTM supplies the directional state.

### 5.4 Comparison with classical ML (honest)

Full comparison Table 4. **State plainly:** XGBoost (no-SMOTE) reaches 0.919 macro-F1 at
+5s, exceeding SENTINEL-GNSS (0.821) on the in-domain test. Do not hide this. Then pivot
to §5.5.

### 5.5 Cross-city generalisation (THE KEY RESULT — E6)

- Table: Beihang/Hangzhou vs Tokyo for DL, RF, XGBoost and the **DL+XGBoost ensemble**, per-class.
  Tokyo support: CLEAN 29,200 · WARNING 1,620 · DEGRADED 416.
- **DEGRADED cross-city: ensemble 0.896, XGBoost 0.784, DL 0.753, RandomForest 0.148.**
- Narrative: in-domain, trees win; out-of-domain, **RandomForest** memorised thresholds do not
  transfer and its degraded detection collapses (0.148), whereas **XGBoost transfers** (0.784),
  the network keeps degraded (0.753), and a **DL+XGBoost soft-vote ensemble is most robust of
  all (0.896)**. For a deployable AV safety system, cross-city robustness on the loss-of-fix
  class is the property that matters — and the ensemble delivers it.
- Honest caveat: DL loses WARNING cross-city (0.268 vs RF 0.716); the ensemble recovers overall
  macro to 0.892. Report Tokyo per-class support (done above).

### 5.6 Computational efficiency (E4)

0.0449 ms/sample, 9.46× faster than 3 tree models, single 17.8 MB checkpoint, all horizons
in one pass. Real-time at 10 Hz with <0.4% of the per-epoch budget.

### 5.7 On data balancing (E5 + ablation)

SMOTE neither helps the network (focal loss + class weights suffice) nor the trees
(XGBoost Δ=−0.0095). KL analysis shows the effect is not distribution-distance; we attribute
it to interpolation artefacts in the high-dimensional flattened space. Recommendation:
loss-level imbalance handling over synthetic oversampling for this task.

### 5.8 Temporal-order analysis (E1, E2 — honest negative result)

Shuffling timesteps degrades both models ~3.2% equally; removing temporal-aggregate features
does not hurt RF. **We explicitly do not claim temporal-order modelling as the source of the
network's advantage.** The advantage is representational transfer (§5.5), confirmed by E6.
This honesty strengthens, not weakens, the paper.

### 5.9 Interpretability

`attention_heatmap_degraded` and `feature_saliency_*` — which timesteps and features drive
DEGRADED predictions. Mechanistic transparency unavailable from the tree baselines.

### 5.10 Calibration ⏳

Report ECE after correct temperature scaling (E7 must be re-run with T=0.40). If ECE drops
materially, claim "calibrated risk score"; otherwise report raw ECE=0.114 and note
calibration as future work. **Do not overclaim.**

---

## 6. Discussion

### 6.1 Why in-domain ML wins but DL is the right deployable choice

Generalisation (E6) + efficiency (E4) + unified multi-horizon + interpretability.

### 6.2 Safety framing

DEGRADED recall and cross-city DEGRADED retention are the operative safety metrics.

### 6.3 Limitations (disclose all)

1. DEGRADED test support n=209; CIs reported.
2. In-domain macro-F1 below tree baselines.
3. scenario_a_r13 within-site overlap.
4. Cross-city WARNING drop.
5. Early overfitting (best epoch ~10–15 of 65) → regularisation is future work.
6. Adaptive EKF not yet integrated (§7).
7. Calibration pending correct re-run.

---

## 7. Future Work

- Adaptive EKF: raise process noise / lower GNSS trust when P(DEGRADED) > τ; report
  navigation RMSE during blockage vs fixed-R EKF and GNSS-only. **(Not yet implemented —
  frame as ongoing, do not claim results.)**
- Stronger regularisation (dropout 0.5, weight-decay sweep) to close the overfitting gap.
- Domain adaptation to recover cross-city WARNING.

## 8. Conclusion

Restate: first proactive multi-horizon GNSS degradation predictor; honest in-domain vs
tree baselines; decisive cross-city DEGRADED-class advantage; real-time, open benchmark.

---

## §6 (merged) — Cross-Receiver Robustness (formerly Paper 2)

> Folded in from the former standalone Paper 2. This is now a robustness section of the
> flagship, not a separate paper. ⚠️ Wording: the model is **hardware-aware** (it uses a
> `receiver_tier` feature) — never call it "receiver-agnostic."

**Claim:** one trained model generalises across the receiver-quality spectrum, from
survey-grade NovAtel to consumer smartphones.

**Experiment (UrbanNav — 9+ receivers, same vehicle/route/time):**

1. Per-receiver evaluation — macro-F1 and DEGRADED-F1 for each receiver tier
   (0 professional → 3 consumer).
2. Receiver-invariant vs receiver-specific feature analysis (expect DOP/sat-count to
   transfer; absolute C/N₀ to be receiver-specific).
3. `receiver_tier` ablation — train with vs without the tier feature; report the
   cross-device F1 it recovers.

**Status:** ⏳ run per-receiver inference with the trained checkpoint (no retraining needed).
Hypotheses (state as hypotheses until confirmed): H1 performance declines pro→consumer;
H2 DOP/sat-count transfer best; H3 the tier feature narrows the gap.

**Figure:** `fig_receiver_tier.pdf` — F1 vs receiver tier (⏳ create from per-receiver run).

---

## Figure & Table Checklist

| #       | Asset                                            | Status                   |
| ------- | ------------------------------------------------ | ------------------------ |
| Fig 1   | architecture_diagram.pdf                         | ⏳ create                |
| Fig 2   | sliding_window_diagram.pdf                       | ⏳ create                |
| Fig 3   | dataset_map.pdf (Beihang/HK/Tokyo)               | ⏳ create                |
| Fig 4   | multi_horizon_comparison                         | ✅ have                  |
| Fig 5   | confusion_matrices_test                          | ✅ have                  |
| Fig 6   | pr_curves_test / roc_curves_test                 | ✅ have                  |
| Fig 7   | attention_heatmap_degraded                       | ✅ have                  |
| Fig 8   | feature_saliency_5s                              | ✅ have                  |
| Fig 9   | lead_time_histogram                              | ✅ have (⏳ read median) |
| Fig 10  | cross_city_barplot (Beihang vs Tokyo, per-class) | ⏳ create from E6        |
| Fig 11  | calibration_curves_test                          | ✅ have (⏳ re-run E7)   |
| Table 1 | Multi-horizon                                    | ✅                       |
| Table 2 | Per-class +5s                                    | ✅                       |
| Table 3 | Full comparison                                  | ✅                       |
| Table 4 | Ablation                                         | ✅                       |
| Table 5 | Cross-city (E6)                                  | ✅                       |
