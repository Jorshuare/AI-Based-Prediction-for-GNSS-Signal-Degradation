# Conference Paper — Cross-City Generalisation (ION GNSS+ 2026)

> **The conference paper** in the 2-paper + conference plan. It presents our strongest
> confirmed result (E6) as a focused 4-page short paper. The same result also appears as
> robustness §7 of **Paper A** (the flagship journal paper) — presenting at a conference and
> later extending into a journal is standard, accepted practice (the journal version must be
> substantially extended, which it is: full method + multi-horizon + cross-receiver + EKF).

**Working title:**
**"Does GNSS Degradation Transfer Across Cities? Cross-City Generalisation of a
Proactive Transformer–LSTM Predictor from Beihang and Hong Kong to Tokyo"**

**Target venue:** **ION GNSS+ 2026** (Nashville, September 2026) — short paper + presentation.

---

## Abstract (draft — uses confirmed E6 numbers)

> Learning-based GNSS quality models are almost always trained and evaluated within a single
> city, leaving open whether the learned notion of "degradation" transfers to a city with
> different building geometry and satellite visibility. We evaluate a Transformer–LSTM
> degradation predictor and a strong gradient-boosted baseline, both trained on Beihang and
> Hong Kong data, on **31,236 windows from Tokyo Shinjuku — a city absent from training**.
> The neural model retains 79% of its in-domain macro-F1 (0.822 → 0.649) whereas the tree
> baseline retains 67% (0.926 → 0.618). Crucially, on the safety-critical DEGRADED class the
> neural model **holds an F1 of 0.75 across cities while the tree baseline collapses to 0.15**.
> We conclude that the tree ensemble memorises city-specific feature thresholds, whereas the
> neural network learns a transferable degradation representation — a property essential for
> any GNSS safety system deployed beyond its training city.

---

## 1. Introduction

### 1.1 The unspoken assumption

- Every GNSS-ML paper trains in one place and declares success; none test another city.

### 1.2 Why city matters physically

- Beihang: dense, grid-like, inland, wide avenues.
- Hong Kong: extreme vertical canyons, coastal, reflective glass façades.
- Tokyo: mixed, varied terrain, coastal, different satellite-visibility geometry.
- Different geometry → different multipath, different C/N₀ and DOP statistics.

### 1.3 Contribution

- First cross-city transfer study for proactive GNSS degradation prediction (⚠️ soften:
  "to the best of our knowledge").
- Quantified neural-vs-tree transfer gap; safety-critical class breakdown.

---

## 2. Related Work

- Domain shift / out-of-distribution generalisation.
- Memorisation vs generalisation in trees vs neural nets (cite Grinsztajn et al., 2022 for
  the in-domain tabular tree advantage; contrast with OOD behaviour).
- Single-city GNSS-ML precedent (⚠️ verify Liu et al. and others).

---

## 3. Experimental Design

### 3.1 Source domains (training)

- Beihang field (Scenarios A–E, Septentrio) + Hong Kong UrbanNav.

### 3.2 Target domain (held-out)

- Tokyo Shinjuku: 31,236 windows, **never seen in training** (excluded via
  DEFAULT_EXCLUDE_SOURCES). Dense urban canyon, ~92% CLEAN.

### 3.3 Models compared

- SENTINEL-GNSS (Transformer–LSTM, no-SMOTE + focal).
- RandomForest (200 trees, the strongest in-domain baseline tier).

### 3.4 Protocol

- Identical scaler (fit on training only) applied to Tokyo features.
- Same 30-step sliding window construction.
- Metrics: macro-F1, per-class F1, generalisation gap (Tokyo − Beihang).

---

## 4. Results (✅ CONFIRMED — E6)

### 4.1 Headline transfer table

| Model            | Beihang macro-F1 | Tokyo macro-F1 |     Gap | Retention |
| ---------------- | ---------------: | -------------: | ------: | --------: |
| Transformer+LSTM |           0.8218 |     **0.6489** | −0.1729 |       79% |
| RandomForest     |           0.9260 |         0.6178 | −0.3082 |       67% |

### 4.2 Per-class cross-city breakdown (Tokyo)

| Class        |      DL F1 |      RF F1 |
| ------------ | ---------: | ---------: |
| CLEAN        |     0.9256 |     0.9896 |
| WARNING      |     0.2683 |     0.7159 |
| **DEGRADED** | **0.7528** | **0.1478** |

### 4.3 The core finding

- **DEGRADED (loss-of-fix), the safety-critical class: DL 0.75 vs RF 0.15 cross-city.**
- The tree model's degraded detection essentially fails in a new city; the neural model's
  holds. This is the headline figure: `cross_city_degraded_bar.pdf` (⏳ create).
- Trade-off (disclose): DL loses WARNING (0.27) where RF keeps it (0.72). Interpret: DL's
  decision surface for the middle class is city-tuned; its extreme-class (CLEAN/DEGRADED)
  representation transfers.

### 4.4 ⏳ TODO before submission

- Add Tokyo per-class **support counts** (Shinjuku ≈92% CLEAN → small DEGRADED/WARNING n;
  contextualise the F1 contrast and add CIs).
- Add Tokyo Odaiba and HK-Medium as additional target cities for a 3-city transfer curve.
- Repeat with XGBoost (not just RF) for completeness.

---

## 5. Discussion

### 5.1 Why trees memorise and networks generalise

- Trees partition on absolute feature thresholds calibrated to Beihang's distribution;
  Tokyo shifts those distributions, so thresholds misfire on the rare DEGRADED class.
- The network's distributed representation encodes relational/temporal structure that is
  more invariant to absolute-value shift.

### 5.2 Practical implication

- For a GNSS safety system that must work in cities it was not trained on, cross-city
  DEGRADED retention is the deciding metric — and only the neural model delivers it.

## 6. Limitations

- Single target city in the core result (extend to 3).
- Tokyo class imbalance; report support + CIs.
- Within-source label-threshold consistency across cities assumed (document).

## 7. Conclusion

GNSS degradation **does** transfer across cities — but only for the model that learns a
representation rather than memorising thresholds. This reframes model selection for
safety-critical GNSS away from in-domain leaderboard score toward cross-domain robustness.

---

## Status

- **Core result CONFIRMED (E6).** This is the most submission-ready secondary paper.
- **Before submission:** add Tokyo support counts + CIs, extend to Odaiba/HK-Medium,
  add XGBoost, create `cross_city_degraded_bar.pdf`.
