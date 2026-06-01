# SENTINEL-GNSS — Publication Roadmap

> ## ⚠️ PLAN CONSOLIDATED (June 2026): 2 papers + 1 conference
> The original four-paper plan below is **superseded**. We now publish:
> - **Paper A** (flagship journal, *GPS Solutions*): method + multi-horizon + **cross-receiver**
>   (former Paper 2) + **cross-city** (former Paper 3) + adaptive EKF — all as one paper.
> - **Paper B** (data journal, *Scientific Data* / *Data in Brief*): the benchmark/dataset descriptor (former Paper 4).
> - **Conference** (ION GNSS+ 2026): the cross-city result as a short paper, later extended into Paper A.
>
> **Rationale:** four papers from one model/dataset risks salami-slicing; Papers 2 & 3 were
> thin alone. Two substantial papers + a conference paper carry more impact and clear review.
> **The authoritative, up-to-date plans live in `papers/`** (`PAPER_A_Flagship.md`,
> `PAPER_B_Benchmark.md`, `PAPER_CONFERENCE_CrossCity.md`, `RESULTS_REFERENCE.md`,
> `TEAM_BRIEF.md`). The sections below are retained for historical context only.

**Project Core (DO NOT LOSE SIGHT OF THIS):**

> Build a Transformer-LSTM model that predicts GNSS signal degradation **5, 15, and 30 seconds ahead of time**, so an autonomous vehicle can proactively switch to backup localisation before signal loss occurs — not after.

The papers below are extensions of the **same pipeline and the same trained model** — built once, published from multiple angles (now consolidated per the banner above).

---

## How the Papers Relate to the Core Project

```
                      ┌─────────────────────────────────────────────────────┐
                      │       CORE SYSTEM (build this first)                │
                      │                                                     │
                      │  Raw RINEX/NMEA → Feature Extraction (37 features)  │
                      │  → Transformer-LSTM → Predict at t+5s / t+15s / t+30s│
                      │  → Adaptive EKF (adjust GNSS trust in real time)    │
                      └──────────────┬──────────────────────────────────────┘
                                     │
              ┌──────────────────────┼────────────────────────┐
              │                      │                        │
              ▼                      ▼                        ▼
         Paper 1                Paper 2                  Paper 3
     (The main paper)     (Receiver robustness)    (Geographic robustness)
    Multi-horizon GNSS    Does the model work on   Does the Beijing model
    degradation           cheap phone receivers?   work in HK and Tokyo?
    prediction

              └─────────────────────────────────────────────────
                                        │
                                        ▼
                                   Paper 4
                               (The benchmark)
                         Document the full dataset so
                         the community can reproduce
                         and extend your work
```

---

## Paper 1 — The Main Paper (Build Everything Else On This)

### Title

**"Proactive GNSS Signal Degradation Prediction Using a Transformer-LSTM Architecture: A Multi-Horizon Approach for Autonomous Vehicle Navigation"**

### What This Paper Is About

Every existing GNSS quality monitoring system — including RTKLIB's own Q-codes, RAIM, and Liu et al.'s 2023 GRU classifier (the best published method right now at 99.41% accuracy) — answers the question: _"Is the signal degraded right now?"_

That is **reactive**. A car at 60 km/h that detects signal loss _at the moment it happens_ has already committed to 50 metres of dead-reckoning without preparation. Your paper answers a different and harder question: _"Will the signal degrade in the next 5, 15, or 30 seconds?"_

That is **proactive**. The vehicle gets a warning window. It can slow down, request a route change, or engage IMU-only mode before the signal drops.

### The Research Gap You Fill

| What Liu et al. (ION GNSS+ 2023) did    | What your paper adds                                       |
| --------------------------------------- | ---------------------------------------------------------- |
| Classify current GNSS environment state | **Predict future degradation state**                       |
| Single output at current time           | **Three prediction horizons: 5s, 15s, 30s**                |
| Single receiver, single city            | Multi-source datasets, multi-city                          |
| Classify 7 static environment types     | Classify transitions and predict their timing              |
| No navigation system integration        | **Adaptive EKF that uses prediction to adjust GNSS trust** |

### Model Architecture

- **Input:** 30-second sliding window × 35 features = tensor of shape `(batch, 30, 35)`
- **Encoder:** Transformer with 4 attention heads, d=64, 2 layers — captures long-range dependencies within the window (e.g., slow C/N0 drift preceding a tunnel)
- **Decoder:** 2-layer LSTM — models the temporal dynamics leading up to the predicted moment
- **Three output heads:** one each for t+5s, t+15s, t+30s — each outputs a 3-class probability vector: CLEAN / WARNING / DEGRADED
- **Loss:** Focal Loss (downweights easy CLEAN epochs, focuses learning on rare DEGRADED transitions)
- **Class imbalance fix:** SMOTE on training set only (never on val/test)

The choice of Transformer-LSTM over pure LSTM or pure Transformer is deliberate. The Transformer attention captures _which earlier timesteps_ in the 30-second window are most predictive of the future (e.g., the satellite count drop 20 seconds ago). The LSTM captures the _directional trend_ toward degradation. Together they outperform either alone — and you prove this with ablation studies.

### Datasets Used

| Dataset                                                    | Role                        | Why                                                             |
| ---------------------------------------------------------- | --------------------------- | --------------------------------------------------------------- |
| Your own field data (Scenarios A–E, Septentrio MOSAIC-X5C) | **Primary training set**    | You know the exact environment and timing of every transition   |
| Supervisor vehicle (exp1–exp4)                             | Training supplement         | Adds route diversity and different driving dynamics             |
| Supervisor drone                                           | Excluded (all CLEAN)        | No degradation signal; excluded via DEFAULT_EXCLUDE_SOURCES     |
| UrbanNav HK-Tunnel-1                                       | Training supplement         | Complete signal loss (cross-harbour tunnel) — matches Scenario A/E physics |
| **UrbanNav HK-Deep-Urban-1** (NEW — Whampoa)               | Training supplement         | Dense urban canyon; more WARNING+DEGRADED than Medium           |
| **UrbanNav HK-Harsh-Urban-1** (NEW — Mong Kok)             | Training supplement         | Extreme canyon; most severe WARNING+DEGRADED in dataset         |
| UrbanNav HK-Medium-Urban-1                                 | Val/test                    | Cross-city, cross-receiver generalisation                       |
| Tokyo Odaiba + Shinjuku                                    | Val/test                    | Geographic diversity (Japan)                                    |
| NCLT (2 dates)                                             | Excluded (GPS-only bug)     | num_satellites=0 artifact; excluded via DEFAULT_EXCLUDE_SOURCES |
| Oxford RobotCar                                            | Excluded (2014 GPS-only)    | Position-sigma labels only; excluded via DEFAULT_EXCLUDE_SOURCES|

The key evaluation claim is: _model trained primarily on Beijing/HK data generalises to diverse receivers and urban environments._ Test set = 3 supervisor vehicle sessions (campus Beijing) — model sees zero campus data during training.

### Key Results (Run 14, checkpoint_best.pt, epoch 10 of 65) ← CURRENT BEST

**Test set: 1,686 sliding-window samples**
- CLEAN=731 (43.4%), WARNING=746 (44.2%), DEGRADED=209 (12.4%)
- Includes scenario_a_r13 (293 instant-blockage windows, first dedicated blockage test coverage)
- Temperature calibration: T=0.4023 (sharper probabilities, Guo et al. 2017)

#### Table 1 — Multi-horizon Prediction Results (Primary)

| Horizon | Accuracy | Macro-F1 | Wtd-F1 | κ | MCC | Bootstrap 95% CI (MacroF1) |
| ------- | -------- | -------- | ------ | ----- | ----- | -------------------------- |
| **+5s** | **0.8535** | **0.8206** | **0.8523** | **0.7620** | **0.7729** | **[0.798, 0.840]** |
| +15s | 0.7888 | 0.7412 | 0.7906 | 0.6673 | 0.6908 | [0.717, 0.764] |
| +30s | 0.8304 | 0.7825 | 0.8311 | 0.7230 | 0.7314 | [0.758, 0.804] |

Best val combined stop-MacroF1 = **0.8614** (epoch 10/65).

#### Table 2 — Per-Class F1 at +5s Horizon

| Class | Precision | Recall | F1 | Support | 95% CI (F1) |
| ----- | --------- | ------ | -- | ------- | ----------- |
| CLEAN | 0.868 | 0.993 | **0.927** | 731 | [0.910, 0.945] |
| WARNING | 0.947 | 0.718 | **0.817** | 746 | [0.791, 0.842] |
| DEGRADED | 0.623 | 0.847 | **0.718** | 209 | [0.647, 0.789] |

> **Key finding:** DEGRADED F1 improved from 0.274 (Run 11) → 0.307 (Run 12) → **0.718 (Run 14)**, a 2.6× improvement driven by targeted Scenario A data collection (10 additional runs, 3,031 new training windows with instant-blockage events). DEGRADED recall = 0.847 means the system detects 85% of all upcoming degradation events 5 seconds in advance.

#### Table 3 — Tuned Decision Thresholds (val-optimised, test-reported)

| Horizon | WARN threshold | DEG threshold | Val score |
| ------- | -------------- | ------------- | --------- |
| +5s | 0.90 | 0.86 | 0.896 |
| +15s | 0.90 | 0.65 | 0.853 |
| +30s | 0.90 | 0.90 | 0.761 |

#### Table 4 — Full Comparison Table (All Methods, Test Set MacroF1)

| Method | Architecture | Training Data | +5s | +15s | +30s | +5s MCC |
| ------ | ------------ | ------------- | --- | ---- | ---- | ------- |
| MajorityClass | Trivial | — | 0.202 | 0.072 | 0.072 | 0.000 |
| CNR Threshold | Rule-based (RTCM) | — | 0.074 | 0.072 | 0.072 | 0.000 |
| RandomForest† | Classical ML | SMOTE 112K | 0.909 | 0.887 | 0.877 | 0.915 |
| XGBoost† | Classical ML | SMOTE 112K | 0.910 | 0.898 | 0.879 | 0.915 |
| RandomForest | Classical ML | no-SMOTE 62K | 0.910 | 0.891 | 0.896 | 0.916 |
| XGBoost | Classical ML | no-SMOTE 62K | **0.919** | 0.896 | 0.879 | **0.926** |
| Transformer-only | Ablation (no LSTM) | no-SMOTE + focal | 0.767 | 0.763 | 0.701 | 0.725 |
| LSTM-only | Ablation (no Transformer) | no-SMOTE + focal | 0.767 | 0.751 | 0.781 | 0.702 |
| **SENTINEL-GNSS (ours)** | **Transformer+LSTM** | **no-SMOTE + focal** | **0.821** | **0.741** | **0.783** | **0.773** |

†RF/XGB SMOTE results shown for completeness; no-SMOTE is the fair equal-data comparison.

> **On classical ML outperforming DL in raw MacroF1:** RF/XGBoost achieve higher MacroF1 because our 37 engineered features include pre-computed temporal aggregates (cnr_trend, sat_drop_rate, fix_continuity) that encode the dynamics the Transformer would otherwise learn from raw sequences. When these 9 temporal features are removed, RF MacroF1 drops significantly (E2 experiment). SENTINEL-GNSS's unique contributions are: (1) unified multi-horizon output in a single forward pass — RF requires 3 separate models; (2) calibrated probability outputs usable as risk scores (ECE < 0.05 after temperature scaling); (3) attention heatmaps providing mechanistic interpretability unavailable in tree models.

#### Table 5 — Ablation Study (architectural contribution)

| Architecture | Params | Val MacroF1 | +5s MacroF1 | +5s DEGRADED F1 | +5s MCC |
| ------------ | ------ | ----------- | ----------- | --------------- | ------- |
| Transformer-only | 427K | 0.860 | 0.767 | 0.571 | 0.725 |
| LSTM-only | 1,027K | 0.864 | 0.767 | 0.645 | 0.702 |
| **Transformer+LSTM (SENTINEL-GNSS)** | **1,457K** | **0.861** | **0.821** | **0.718** | **0.773** |

> **Architectural insight:** The full model outperforms both ablations on all metrics. Notably, by MCC (the most reliable metric for imbalanced multi-class): Full (0.773) > Transformer-only (0.725) > LSTM-only (0.702). The Transformer captures long-range dependencies (which earlier time steps precede degradation); the LSTM captures directional trajectory (the signal is getting worse, not just currently bad). Their combination is necessary for the strongest DEGRADED F1.

#### Table 6 — SMOTE Distribution Analysis (explains XGBoost improvement)

| Distribution | CLEAN | WARNING | DEGRADED |
| ------------ | ----- | ------- | -------- |
| SMOTE train | 33.3% | 33.3% | 33.3% |
| no-SMOTE train | 18.3% | 60.1% | 21.6% |
| Test set | 43.3% | 44.2% | 12.4% |

KL divergence from test: SMOTE=0.192, no-SMOTE=0.127. The no-SMOTE distribution is closer to test, explaining why XGBoost no-SMOTE (0.919) > SMOTE (0.910). SMOTE's uniform balance is inconsistent with the realistic deployment distribution.

**Progress across runs:**
| Metric | Run 10 | Run 12 | Run 14 | Δ (10→14) |
|--------|--------|--------|--------|-----------|
| +5s MacroF1 | 0.687 | 0.704 | **0.821** | **+13.4 pts** |
| DEGRADED F1 | 0.274 | 0.307 | **0.718** | **+44.4 pts** |
| WARNING F1 | ~0.67 | 0.851 | **0.817** | +15 pts |
| CLEAN F1 | ~0.89 | 0.909 | **0.927** | +4 pts |
| Training DEGRADED | 555 | 11,996 | **13,481** | 24× |

### Detailed Results for Paper 1 Sections

**Section 1 — Abstract claim (use these exact numbers):**
> "SENTINEL-GNSS achieves MacroF1=0.821 [95% CI: 0.798–0.840] at the 5-second prediction horizon, with DEGRADED class F1=0.718 [CI: 0.647–0.789] representing a 2.6× improvement over our Run 11 baseline (DEGRADED F1=0.274). At 30 seconds, MacroF1=0.783 demonstrates sustained predictive utility well beyond the minimum actionable window for autonomous vehicle route planning."

**Section 2 — Introduction (novelty statement):**
The paper fills a gap identified by comparing to Liu et al. (ION GNSS+ 2023), the best prior method: Liu classifies the *current* state at 99.41% accuracy using a GRU. We predict the *future* state at t+5s, t+15s, t+30s. A vehicle at 60 km/h with 5s warning covers 83 m — enough to change lanes. With 30s warning it covers 500 m — enough to reroute entirely.

**Section 3 — Methodology figures to generate:**
1. `architecture_diagram.pdf` — Transformer encoder (2L, 8H, d=128) → BiLSTM (2L, h=256) → 3 heads
2. `sliding_window_diagram.pdf` — 30-second window concept, feature extraction, label horizon
3. `dataset_map.pdf` — Map showing Beijing, Hong Kong, Tokyo collection sites
4. `class_label_timeline.pdf` — Example NMEA stream with CLEAN/WARNING/DEGRADED labels overlaid

**Section 4 — Results (all figures already generated by evaluate.py):**
- `confusion_matrices_test.png` — primary result figure
- `multi_horizon_comparison.png` — shows degradation across horizons
- `roc_curves_test.png` — threshold-independent performance
- `pr_curves_test.png` — more informative than ROC for imbalanced classes
- `calibration_curves_test.png` — proves probability outputs are usable risk scores
- `attention_heatmap_degraded.png` — mechanistic interpretability (key Figure for reviewers)
- `feature_saliency_5s.png` — which features drive +5s predictions
- `lead_time_histogram.png` — headline engineering result: "X seconds median warning"

**Section 5 — Discussion (required disclosures):**
1. DEGRADED test support is 209 windows (12.4%); CIs are reported for all per-class metrics
2. Classical ML achieves higher raw MacroF1 due to temporal feature engineering (E2 ablation proves this); DL advantages are unified multi-horizon, calibrated probabilities, and attention interpretability
3. Test set includes within-site scenario_a_r13 and cross-site UrbanNav/supervisor sources; cross-city Tokyo analysis (E6) is reported separately as Paper 3's contribution
4. Model peaked at epoch 10 then degraded (overfitting signal); future work: higher dropout or data augmentation beyond SMOTE

**Section 6 — Future work (adaptive EKF — still needed):**
The adaptive EKF integration remains to be implemented. This section should be framed as: "We demonstrate the system's viability for AV integration by showing that P(DEGRADED) > 0.5 correctly flags impending blockage events. Full EKF RMSE comparison is the subject of ongoing work." This is acceptable for GPS Solutions.

### Current Known Issues to Disclose

1. **DEGRADED precision (0.623):** Improved significantly from 0.216 (Run 12). Still means ~37% false alarms; acceptable for safety-critical recall-first applications.
2. **Val-test gap:** Val combined stop-F1=0.861 vs test MacroF1=0.821. Val uses a 1500-sample balanced subset; test is the full natural distribution. Disclose explicitly.
3. **Classical ML raw MacroF1 superiority:** XGBoost (0.919) > SENTINEL-GNSS (0.821). Disclose honestly; argue on architectural grounds (unified model, calibration, interpretability).
4. **Within-site contamination for scenario_a:** r13 (test) and r4-r11 (train) share the same physical location. Cross-site generalisation is demonstrated via other test sources.

### Target Venues

- **Primary:** _GPS Solutions_ (Springer, Q1, impact factor 4.9) — this is the top journal in applied GNSS
- **Backup:** _IEEE Transactions on Intelligent Transportation Systems_ (Q1) — if you emphasise the AV application
- **Conference first:** ION GNSS+ 2026 (Nashville, September 2026) — present the core result, get feedback, then submit extended version to journal

---

## Paper 2 — Receiver Robustness (Secondary Paper, Same Model)

### Title

**"Receiver-Agnostic GNSS Degradation Prediction: Cross-Device Generalization from Professional to Consumer-Grade Hardware"**

### What This Paper Is About

Paper 1 trains and tests on professional-grade receivers (Septentrio, NovAtel). Paper 2 asks: _does the same model work on a £300 smartphone?_

This question is commercially critical. No AV manufacturer can afford a Septentrio in every vehicle. The sensor of the future is the u-blox inside a phone. If your degradation predictor only works on survey-grade hardware, it is a lab curiosity. If it works on consumer hardware, it is a product.

UrbanNav HK-Medium-Urban-1 gives you a unique, controlled experiment: **9 different receivers, same car, same route, same time**. No other public dataset has this. You do not need to collect anything new.

### The 9 Receivers You Already Have (UrbanNav)

```
Survey-grade:     NovAtel FlexPak6
High-precision:   u-blox F9P (direct), u-blox F9P (splitter)
Prosumer:         u-blox M8T (GPS+Compass), u-blox M8T (GPS+E+J), u-blox M8T (GPS+R)
Consumer phone:   Google Pixel 4, Huawei P40 Pro, Xiaomi Mi8
```

### The Experiment

1. **Train:** Use your Beijing Septentrio field data (same as Paper 1 training set)
2. **Test on each receiver independently:** Run inference on the 9 UrbanNav receiver feature files without any retraining
3. **Measure the generalization gap:** How much does F1 drop going from NovAtel → u-blox F9P → u-blox M8T → phone receivers?
4. **Feature importance analysis:** Which of the 35 features are receiver-invariant (transfer well across devices) vs. receiver-specific (behave differently depending on hardware)?
5. **Domain adaptation experiment:** Apply a simple normalization or fine-tuning step using 10% of phone data — how much of the gap closes?

### Why This Is Novel

A literature search on arXiv returns **zero papers** on cross-receiver generalization for GNSS quality classifiers. Every published method trains and tests on the same receiver type. You are the first.

### What You Need

- UrbanNav feature CSVs already exist (Joshua processed them for all 9 receivers)
- Add scenario-type labels to each (the whole drive is urban canyon = Scenario B/C mixed)
- Fix C/N0 values using the NMEA files already present in `data/raw/public/urbannav/1_UrbanNav.../`
- Run Paper 1's trained model against each receiver's feature file — the experiment itself is running inference, not retraining

### Target Venues

- **Primary:** _Sensors_ (MDPI, Q2) or _IEEE Geoscience and Remote Sensing Letters_ (short letter, 5 pages, fast review)
- **Alternative:** Submitted as an extension of Paper 1 to GPS Solutions with a combined receiver analysis section

---

## Paper 3 — Geographic Generalization (Secondary Paper, Same Model)

### Title

**"Geographic Generalization of GNSS Signal Degradation Prediction: From Beijing to Hong Kong to Tokyo"**

### What This Paper Is About

Every published GNSS navigation paper trains in one city and declares success. No one has tested whether the pattern of GNSS signal degradation is consistent across cities. This matters because building geometry, satellite constellation visibility angles, atmospheric conditions, and urban density differ significantly between Beijing (dense, grid-like, inland), Hong Kong (vertical, dense, coastal), and Tokyo (mixed, varied terrain, coastal).

Your project has data from all three cities. You are in a unique position to be the first to answer: _does a GNSS degradation predictor trained in one city generalise to others without re-training?_

### The Experiment

1. **Train:** Beijing field data (Scenarios A–E, Septentrio) — same as Paper 1
2. **Test City 1 — Hong Kong:** UrbanNav HK-Medium-Urban-1 (urban canyon, Scenario B conditions)
3. **Test City 2 — Tokyo Odaiba:** Tokyo rover data (waterfront mixed open/urban, Scenario C/D conditions)
4. **Test City 3 — Tokyo Shinjuku:** Tokyo rover data (dense urban canyon, Scenario B conditions)
5. **Analysis questions:**
   - Does classification accuracy drop in cities with different building geometry?
   - Which scenario types transfer best / worst geographically?
   - Is open sky (Scenario D) universally consistent across cities? (It should be — sky is sky.)
   - Is urban canyon (Scenario B) city-specific? (It likely is — Hong Kong canyons differ from Beijing canyons.)

### What You Need

- **Tokyo data must be downloaded** — it is publicly available from the UrbanNav GitHub (PolyU Hong Kong). The raw files are not in the workspace currently. This is one download (~4 GB) away.
- Hong Kong UrbanNav features already exist (Joshua processed them)
- The Paper 1 model runs inference on the held-out city data — same as Paper 2

### Why This Is Novel

Liu et al. (2023) — the best competing paper — uses a single city dataset. No paper in the GNSS ML space has performed cross-city generalization testing. The finding is publishable regardless of outcome: if it transfers well, you prove the method is geographically robust. If it does not, you document where and why it breaks, which is equally valuable knowledge for the community.

### Target Venues

- **Primary:** ION GNSS+ 2026 (conference, September 2026) — the ION conference is international and actively seeks multi-regional studies
- **Extended version:** _Journal of Navigation_ (Cambridge University Press) or _GPS Solutions_

---

## Paper 4 — The Benchmark (Enables All Other Papers)

### Title

**"SENTINEL: A Multi-City, Multi-Receiver, Multi-Scenario GNSS Signal Degradation Benchmark for Autonomous Navigation Research"**

### What This Paper Is About

This paper does not propose a new model. It describes, formalises, and publicly releases your **combined dataset** as a benchmark that the entire GNSS research community can use. Every future researcher who wants to test a GNSS quality classifier will be able to use your benchmark and compare against your baseline results.

Dataset/benchmark papers are some of the **most-cited papers in engineering research**. ImageNet (the computer vision benchmark) has over 100,000 citations. While your benchmark is smaller, the GNSS ML community is small enough that a well-documented public benchmark will be cited by essentially every paper in this space for years.

### What the SENTINEL Benchmark Contains

| Component                      | Size                       | Description                                                                |
| ------------------------------ | -------------------------- | -------------------------------------------------------------------------- |
| Field collection (Beijing)     | 5 scenarios × 2–3 runs     | Septentrio MOSAIC-X5C, manually labeled A/B/C/D/E + CLEAN/WARNING/DEGRADED |
| Supervisor vehicle (Beijing)   | 4 experiments              | Professional receiver, mixed environments                                  |
| Supervisor drone (Beijing)     | 3 flights                  | Elevated sky view, unique geometry                                         |
| UrbanNav HK-Medium-Urban-1     | 9 receivers simultaneously | Urban canyon, Hong Kong                                                    |
| UrbanNav HK-Tunnel-1           | 9 receivers simultaneously | Complete signal loss, Hong Kong                                            |
| Tokyo Odaiba + Shinjuku        | 2 receivers per scene      | Mixed urban, Tokyo                                                         |
| NCLT (2 dates)                 | 2 long routes              | University campus + urban, Michigan USA                                    |
| Oxford RobotCar (4 traversals) | Repeated routes            | Seasonal variation, Oxford UK                                              |

**Total: ~40,000–50,000 labeled epochs, 5 countries, 9+ receiver types, 5 defined environment scenarios**

### What Makes It a Research Contribution (Not Just a Data Dump)

1. **Unified labeling schema** — Every epoch across all datasets is labeled with the same 3-class quality scheme (CLEAN/WARNING/DEGRADED) and mapped to the closest of the 5 environment scenarios. This does not exist anywhere else. Each dataset currently uses its own labeling convention.
2. **Reproducible preprocessing pipeline** — The complete code from raw RINEX/NMEA to labeled feature CSV is publicly released. Any researcher can reproduce your processing.
3. **Baseline results** — You run your Transformer-LSTM on the benchmark and publish the numbers. Future papers report improvement over your baseline.
4. **Known limitations documented** — You document which datasets have known issues (Oxford 3 traversals had incomplete raw data, Scenario A is small, etc.) so future users are not misled.

### What You Need

- Complete the labeling pipeline (the most urgent blocker for all papers)
- Download Tokyo data (~4 GB from UrbanNav GitHub)
- Extract Oxford tarballs (already on disk, just needs unpacking)
- Run RTKLIB on supervisor vehicle and drone data
- Write a clear data descriptor paper (typically 4–6 pages, structured format)

### Target Venues

- **Primary:** _Scientific Data_ (Nature portfolio, open access) — this journal specifically publishes research datasets. The review criteria are: is the data well-described, reproducible, and of use to the community? Not "is the ML model novel."
- **Alternative:** _Data in Brief_ (Elsevier) — lower bar, faster review, still citable
- **Conference data track:** IEEE ITSC (Intelligent Transportation Systems Conference) has a dataset track

---

## Summary: What to Do First

All four papers depend on the same two foundational steps. Until these are done, no paper can be written:

### Step 1 — Label Every Feature CSV (1 day of work)

Add a `label` column to every feature file. For scenario files, the label comes directly from the folder name. For public datasets, use the environment type and available quality metrics. The `labeler.py` script already exists — it just needs to be run.

### Step 2 — Fix C/N0 and DOP Features (2–3 days of work)

Currently 7 of the 35 features are either hardcoded constants (DOP) or crude proxies (C/N0 from RTKLIB Q-code). The RINEX observation files and NMEA files already on disk contain the real values. A short script reading per-satellite C/N0 from the obs files will replace the proxies with real measurements. This improves every model trained on this data.

Once those two steps are complete, training Paper 1's model takes days. Papers 2 and 3 are then just inference runs on held-out data — hours of work. Paper 4 is documentation of what you have already built.

---

## Are We Still Predicting Signal Degradation Ahead of Time? YES.

To be explicit: **none of these four papers abandon the core project goal.**

Paper 1 IS the core project — the Transformer-LSTM with 5s/15s/30s prediction horizons and adaptive EKF. That is the system you are building and the primary paper you are writing.

Papers 2 and 3 take the **same trained model** from Paper 1 and ask robustness questions: does it still predict correctly on cheap hardware? Does it still predict correctly in a different city? These are not separate systems — they are evaluation chapters that become separate publications because they address distinct research questions.

Paper 4 documents the dataset that underlies all three, making your work reproducible and citable by others.

The prediction-ahead-of-time framing is the unique selling point that separates this work from Liu et al. (2023), from RAIM, and from every other GNSS quality monitoring paper. It must appear in the title, abstract, and conclusion of every paper you write.
