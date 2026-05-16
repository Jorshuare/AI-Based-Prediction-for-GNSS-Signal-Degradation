# SENTINEL-GNSS — Publication Roadmap

**Project Core (DO NOT LOSE SIGHT OF THIS):**

> Build a Transformer-LSTM model that predicts GNSS signal degradation **5, 15, and 30 seconds ahead of time**, so an autonomous vehicle can proactively switch to backup localisation before signal loss occurs — not after.

All four papers below are extensions of the **same pipeline and the same trained model**. You build it once. You publish four different angles of it.

---

## How the Papers Relate to the Core Project

```
                      ┌─────────────────────────────────────────────────────┐
                      │       CORE SYSTEM (build this first)                │
                      │                                                     │
                      │  Raw RINEX/NMEA → Feature Extraction (35 features)  │
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

| Dataset                                                    | Role                     | Why                                                             |
| ---------------------------------------------------------- | ------------------------ | --------------------------------------------------------------- |
| Your own field data (Scenarios A–E, Septentrio MOSAIC-X5C) | **Primary training set** | You know the exact environment and timing of every transition   |
| Supervisor vehicle (exp1–exp4)                             | Training supplement      | Adds route diversity and different driving dynamics             |
| Supervisor drone                                           | Training supplement      | Unique elevated sky-view geometry                               |
| UrbanNav HK-Medium-Urban-1                                 | **Held-out validation**  | Never seen during training, different city, different receivers |
| NCLT (2 dates)                                             | **Held-out test**        | Different continent, long routes, ground truth error available  |
| Oxford RobotCar (4 traversals)                             | **Held-out test**        | Seasonal variation, repeated routes                             |

The key evaluation claim is: _model trained in Beijing on a Septentrio receiver achieves >X% macro-F1 on Hong Kong UrbanNav data without any fine-tuning._ This proves the model generalises, not just memorises.

### Key Results to Report

1. **Prediction accuracy at each horizon** — Precision, Recall, F1, AUC-ROC for each class at t+5s, t+15s, t+30s. Expected pattern: t+5s > t+15s > t+30s accuracy.
2. **Lead time analysis** — How many seconds before actual signal loss does the model first issue a WARNING? Report mean and distribution over all Scenario A and E test cases.
3. **Ablation table** — Transformer-LSTM vs. LSTM-only vs. RF vs. threshold classifier. Shows each component contributes.
4. **Navigation RMSE** — Compare three conditions: (a) raw GNSS-only, (b) standard fixed-R EKF, (c) adaptive EKF driven by your model predictions. Show RMSE drops in condition (c) during degradation events.
5. **Confusion matrix** — Where does the model get confused? Expected: C vs. E are the hardest pair.

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
