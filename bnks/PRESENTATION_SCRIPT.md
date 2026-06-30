# SENTINEL-GNSS Presentation Script

## Every Slide with Full Justification & Speaking Notes

**Audience:** Professors, committee members, stakeholders  
**Duration:** 20–25 minutes  
**Goal:** Convince them the project is novel, rigorous, and deployable

---

## **Slide 1: Title Slide**

**Text:** SENTINEL-GNSS | Predicting GNSS Signal Degradation for Autonomous Driving

**Say:**

> "Good morning/afternoon. I'm presenting SENTINEL-GNSS, a system that predicts when GNSS signals will degrade 5 to 30 seconds into the future. Why is this important? Because autonomous vehicles depend on precise positioning every single second, and GNSS can fail suddenly in cities—without warning. Our system gives the vehicle time to prepare."

**Why:** Frame the problem as real and urgent.

---

## **Section 1: The Problem (Slides 2–4)**

### **Slide 2: Why GNSS Prediction Matters**

**Bullets:**

- GNSS is the primary absolute-positioning sensor for autonomous vehicles
- It fails abruptly: urban canyons, tunnels, foliage, multipath
- Every existing monitor (RTKLIB, RAIM, ML classifiers) is REACTIVE—only reports degradation AFTER it happens
- Our question is harder: will the signal degrade in the next 5 / 15 / 30 seconds?

**Say:**

> "GNSS works great on open highways. But cities are different. Buildings block signals. Reflections create multipath errors. A car at 60 km/h travels 17 metres every second—by the time the system detects a GNSS failure, it's too late.
>
> Existing monitors are **reactive**. They say 'GNSS is bad NOW.' We ask a harder question: **'Is GNSS going to be bad in the next 5 seconds?'** That's the hard part—prediction, not detection. And that's what SENTINEL-GNSS does."

**Justification:** Establish the gap between existing (reactive) and our approach (proactive).

---

### **Slide 3: What Proactive Warning Buys**

**Table:**
| Horizon | Distance @ 60 km/h | Action |
|---------|-------------------|--------|
| +5 s | 83 m | Tighten IMU fusion, slow down |
| +15 s | 250 m | Pre-engage dead-reckoning, adjust speed |
| +30 s | 500 m | Re-route to avoid the degradation zone |

**Say:**

> "With 5 seconds warning, the vehicle can tighten up its IMU-based dead-reckoning. With 15 seconds, it can pre-plan a route change. With 30 seconds, it can avoid the problem entirely.
>
> Prediction converts a sudden failure into a **planned hand-off** to backup localisation. That's the safety benefit."

**Justification:** Show concrete operational value, not just academic novelty.

---

### **Slide 4: Three Signal Classes**

**Visuals (or describe):** CLEAN sky, WARNING partial shadow, DEGRADED dense urban

**Say:**

> "We classify GNSS signal quality into three states:
>
> - **CLEAN**: healthy, full constellation, high C/N₀ (signal strength)
> - **WARNING**: partial blockage, some satellites lost, degrading C/N₀
> - **DEGRADED**: heavy blockage, few satellites, low C/N₀, potential loss of fix
>
> Our job is to predict transitions—especially **CLEAN → WARNING → DEGRADED**—before they happen."

**Justification:** Define the three-class problem that the model solves.

---

## **Section 2: Data (Slides 5–7)**

### **Slide 5: A Multi-City, Multi-Receiver Dataset**

**Table:**
| Source | City | Receivers | Role |
|--------|------|-----------|------|
| Beihang Field A–E | Hangzhou | Septentrio | train / test |
| UrbanNav Deep/Harsh | Hong Kong | 9+ types | train / val |
| Tokyo Shinjuku | Tokyo | Trimble + u-blox | **held-out city** |

**Say:**

> "We collected 149,662 labelled epochs—one-second GNSS snapshots, each labelled CLEAN, WARNING, or DEGRADED.
>
> Why multi-city? Because **cross-city generalisation is hard**. A model trained in Hangzhou might fail in Tokyo. Tokyo is completely held-out—it never touches training. That's how we prove the model actually generalises.
>
> Why multi-receiver? Because different receivers see GNSS quality differently. Septentrio (professional) vs. u-blox (cheap) vs. smartphone receivers—all different. We handle all of them."

**Justification:** Show rigor: unseen city, unseen receiver types, realistic complexity.

---

### **Slide 6: From Raw Signals to Model-Ready Features**

**Say:**

> "Raw GNSS data is noisy and high-dimensional. We don't feed raw phase/pseudorange to the model. Instead, we compute 37 engineered features from raw observations:
>
> - **Signal strength:** C/N₀ (carrier-to-noise ratio) per satellite
> - **Geometry:** DOP metrics (dilution of precision)
> - **Satellite health:** constellation count, visibility, elevation masks
> - **Receiver status:** fix quality, solution age, clock drift
> - **Temporal patterns:** how C/N₀ is trending, how many satellites just dropped
> - **Atmospheric:** ionospheric delay, tropospheric delay (computed from models)
>
> A 30-second sliding window—30 epochs × 37 features—becomes a tensor that the model ingests. We predict the signal class 5, 15, or 30 seconds ahead."

**Justification:** Show engineering rigor; these features have domain meaning, not just ML magic.

---

### **Slide 7: Data Split Strategy**

**Say:**

> "Here's how we avoided data leakage:
>
> - **Session-level split:** all data from a collection session goes to train/val/test together (never mixed)
> - **SMOTE on train only:** if we use class balancing, it's only on training data
> - **Scaler fit on train only:** then apply to val/test
> - **Tokyo fully held-out:** not even a peek in training
>
> This is stricter than typical ML because we're validating a **physical phenomenon**—if we leak temporal information, the model learns artifacts, not physics. We don't let that happen."

**Justification:** Honest handling of data prevents overoptimism.

---

## **Section 3: Method (Slides 8–12)**

### **Slide 8: Complete System Pipeline** ← NEW SLIDE

**Title:** "Complete System Pipeline — SENTINEL-GNSS"

**Content:** Full-width annotated pipeline diagram showing five stages:
`SENSORS → FEATURE ENGINEERING → SENTINEL MODEL → ADAPTIVE EKF → OUTPUTS & DASHBOARD`

**Say:**

> "Before we dive into each component, let me show you the whole system in one picture.
>
> On the left, we have three sensors. The **GNSS receiver** gives us raw position observations — C/N₀ ratios, DOP values, satellite counts — at 1 Hz. The **IMU** at 100 Hz gives us acceleration and heading. **Wheel encoders** give us odometry.
>
> These raw signals go into **feature engineering**: 37 handcrafted features extracted per 1-second epoch, arranged into a 30×37 sliding window tensor. Critically, we exclude latitude and longitude — we deliberately blocked the model from learning 'this city looks like Hangzhou' — it has to learn signal physics, not geography.
>
> That tensor goes into **SENTINEL**, our ML model — a Transformer-LSTM hybrid. One forward pass produces three calibrated probability outputs: P(DEGRADED) at +5 s, +15 s, and +30 s.
>
> Those probabilities feed directly into the **Adaptive EKF**. When P(DEGRADED) is high, the EKF increases R — it distrusts the GNSS measurement and falls back on IMU and odometry. When P is low, it trusts GNSS fully.
>
> The filter outputs a smoothed 9-state position estimate, which goes to the **dashboard** for real-time monitoring, and to an **alert engine** that gives the route planner early warning — up to 30 seconds ahead.
>
> Notice the ground-truth path at the bottom — the dashed purple line — that's only used for validation, never during inference. The system runs entirely from live sensor data."

**Justification:** The audience will see EKF, dashboard, model, and data slides coming up. This overview anchors everything — when they see a detail slide, they know exactly where it fits in the flow.

---

### **Slide 9: The SENTINEL-GNSS Architecture**

**Say:**

> "The model is a Transformer-LSTM hybrid. Here's why:
>
> **Transformer** (2 layers, 8 attention heads, d=128):
>
> - Sees long-range dependencies in the 30-second window
> - 'Ah, this satellite started fading 20 seconds ago—it's about to drop'
>
> **LSTM** (2 layers, hidden=256):
>
> - Captures the directional trajectory toward degradation
> - 'The signal is getting worse; that trend will continue'
>
> **Three output heads** (+5s, +15s, +30s):
>
> - One forward pass, three predictions
> - Calibrated probabilities P(CLEAN), P(WARNING), P(DEGRADED) at each horizon
>
> **Total:** 1.46 million parameters. Focal loss (γ=1.0) to handle class imbalance. No SMOTE in the DL path—the loss function does the weighting."

**Justification:** Explain the architectural choices and why they're fit for purpose.

---

### **Slide 9: Honest Validation**

**Say:**

> "We don't just report in-domain accuracy. We validate honesty:
>
> 1. **Ablations:** Does the Transformer contribute? Does the LSTM? Yes to both.
> 2. **Permutation test:** Does temporal order matter? Yes, ~3%. (But the real win is representation transfer, not temporal modelling.)
> 3. **Bootstrap CIs:** On every metric. The 95% confidence intervals are wide—we show them. No false precision.
> 4. **Calibration:** Is P(DEGRADED) = 0.7 really 70% likely? We use temperature scaling to improve it. Still not perfect, and we say so.
> 5. **Cross-city:** The hard test. Tokyo—unseen city, unseen receivers. How do we do? (Spoiler: our DL + ensemble beat single models.)"

**Justification:** Credibility comes from being honest about limitations.

---

### **Slide 10: The KEY RESULT—Cross-City Generalization**

**Table:**
| Model | Beihang (In-Domain) | Tokyo (Unseen City) | Tokyo DEGRADED F1 |
|-------|-------------------|-------------------|------------------|
| DL + XGBoost Ensemble | 0.911 | **0.892** | **0.896** |
| SENTINEL-GNSS (DL only) | 0.822 | 0.649 | 0.753 |
| XGBoost | 0.919 | 0.821 | 0.784 |
| RandomForest | 0.926 | 0.618 | **0.148** |

**Say:**

> "This table is the heart of the paper. In-domain, RandomForest wins—0.926 Macro-F1. But **cross-city, RandomForest collapses to 0.148 on the safety-critical DEGRADED class**. That's terrible.
>
> XGBoost transfers better—0.784. DL alone is solid—0.753.
>
> But **our ensemble—DL + XGBoost soft-vote—is best: 0.892 in-domain, 0.892 cross-city**. It beats every single model on the **held-out city**. That's what matters for deployment.
>
> The lesson: don't over-optimize in-domain. Optimize for generalisation. That's what we did."

**Justification:** Cross-city results are the proof of generalization.

---

### **Slide 11: Efficiency & Calibration**

**Say:**

> "Fast inference (0.045 ms/sample on GPU) means we can run at 10 Hz on edge hardware.
>
> One 17.8 MB checkpoint handles all three horizons—not three separate models.
>
> **Calibration:** P(DEGRADED) from the model should match reality. We use temperature scaling (Guo et al., 2017). It cuts ECE from 0.114 to 0.069—good, but not perfect. We're honest: this is a limitation for Phase 2."

**Justification:** Real-world constraints matter; show you've thought about them.

---

## **Section 5: EKF — From Prediction to Position (4 slides)**

> **These 4 slides replace slides 22–24 in the PPTX. Section numbering corrected to 5
> (was labelled 5.5). Slides 23 and 24 (currently blank) become EKF-2 and EKF-3.**

---

### **EKF Slide 1: Why the EKF? (slide 22)**

**Slide layout:** Two-column comparison table

| Standard Kalman Filter         | Our Adaptive EKF                             |
| ------------------------------ | -------------------------------------------- |
| R = fixed (e.g. 9 m²)          | R(t) = adaptive — grows with P(DEGRADED)     |
| Always trusts GNSS equally     | Pre-emptively distrusts GNSS before blockage |
| Position jumps when GNSS fails | Smooth handoff to dead-reckoning             |

**Bottom callout (bold):** _"Prediction closes the loop: we don't wait for GNSS to fail — we pre-empt it."_

**Say:**

> "Predicting degradation is one thing. **Using the prediction to actually improve navigation** is the real contribution.
>
> A standard Kalman filter fuses GNSS and a motion model with a fixed trust ratio — it always trusts GNSS equally. It waits until GNSS is corrupted, then slowly recovers.
>
> Our EKF is adaptive. SENTINEL's P(DEGRADED) output directly controls how much the filter trusts GNSS at every time step. When the probability is high, the filter **pre-emptively shifts authority to dead-reckoning** — before the failure hits. That's the closed loop."

**Justification:** Frames EKF as the system-level payoff of the prediction work.

---

### **EKF Slide 2: The Adaptive-R Formula (slide 23 — replace blank)**

**Slide layout:** Large centred formula with annotated arrows, 3 concrete values at bottom.

**Main formula (large, centred):**

```
σ(t) = σ_base + (σ_deg − σ_base) × P̂_calib(t)

R(t)  = σ(t)² · I₂
```

**Calibration line:**

```
P̂_calib(t) = clip( (P̂(t) − P₅) / (1 − P₅),  0,  1 )
```

**Kalman gain:**

```
K_t = P⁻_t Hᵀ (H P⁻_t Hᵀ + R_t)⁻¹
```

**Three concrete values (bottom row, colour-coded):**

- 🟢 P̂=0 → σ=3 m → R = 9 m² → Trust GNSS fully
- 🟡 P̂=0.5 → σ=51.5 m → R ≈ 2,652 m² → Significant caution
- 🔴 P̂=1 → σ=100 m → R = 10,000 m² → Dead-reckon on odometry

**Say:**

> "Here's the mechanism. Measurement noise R controls how much the Kalman filter trusts GNSS. We make R a function of time, driven by our prediction.
>
> The key is that we interpolate in **standard-deviation space first**, then square. When P_calib is zero — signal is clean — sigma stays at σ_base = 3 metres, so R = 9 m². The filter trusts GNSS tightly. When P_calib is one — degradation is predicted — sigma reaches σ_deg = 100 metres, so R = 10,000 m². The Kalman gain K shrinks to near zero. The filter ignores GNSS and dead-reckons on wheel odometry alone.
>
> At P=0.5, sigma is 51.5 metres, giving R = 2,652 m² — which is intermediate but much closer to the degraded end than you might expect. This is intentional: the interpolation in sigma-space gives more aggressive R-inflation at intermediate probabilities than linear interpolation in variance-space would.
>
> The P̂_calib line is a one-line unsupervised calibration: we subtract the floor P₅ = 0.153 (the 5th-percentile probability floor for this receiver type, estimated from unlabelled data) and rescale to the full [0,1] range. This removes the receiver-domain offset without any labelled data from Tokyo.
>
> The beauty is that R-inflation happens 5 seconds **before** the actual failure. The handoff is smooth, not reactive."

**Justification:** Shows the formula is principled and simple; the calibration line explains cross-domain deployment.

---

### **EKF Slide 3: Results — Real Tokyo Data (slide 24 — replace blank)**

**Slide title:** `EKF RESULTS — THREE TIERS OF VALIDATION`

**Table:**

| Tier           | Data                                                     | Blocked-Segment RMSE | Gain        |
| -------------- | -------------------------------------------------------- | -------------------- | ----------- |
| Synthetic      | Controlled simulation, known blockage timing             | 54.4 m → 36.0 m      | **−33.8 %** |
| Semi-synthetic | Real Tokyo path + real IMU, synthetic GNSS errors        | 36.3 m → **6.4 m**   | **+82 %**   |
| **Fully real** | RTKLIB Trimble GNSS + real IMU + cm-level SPAN-INS truth | **47.4 m → 24.3 m**  | **+48.8 %** |

**Bottom callout (bold):** _"Aided 9-state EKF (odometry + non-holonomic + ZUPT) is the decisive contribution. Adaptive-R adds on top in severe multipath."_

**Say:**

> "We validated at three levels of realism, because a single cherry-picked result isn't convincing.
>
> The controlled simulation gives −33.8% — proof of concept, but the GNSS errors are synthetic. The semi-synthetic run uses the real Tokyo trajectory and real IMU, but injects synthetic GNSS multipath — the 82% gain shows the aided EKF is powerful.
>
> The number that matters is the **fully real validation**: real GNSS from a Trimble receiver, real IMU, real cm-level ground truth from SPAN-INS, on the streets of Tokyo Shinjuku — the city our model never saw in training. Blocked-segment RMSE drops from 47.4 metres to 24.3 metres. **That is a 48.8% improvement on real data, on a held-out city.**
>
> Honest note: the dominant win is the **aiding** — wheel odometry, the non-holonomic constraint, ZUPT. SENTINEL adaptive-R adds on top of that, particularly in severe multipath."

**Justification:** Three-tier validation is credible and honest.

---

### **EKF Slide 4: When Does Adaptive-R Help? (new slide)**

**Slide title:** `WHEN IS ADAPTIVE-R WORTH IT? — SEVERITY SWEEP`

**Layout:** Left — severity sweep figure from `results/paper_figures/`; Right — two-bullet conclusion.

**Right column:**

- **Aided EKF (our system — odometry + NHC + ZUPT):** adaptive-R clearly wins at extreme multipath above ~80–100 m. At 100 m bias: adaptive-R 30.4 m vs. fixed-R 36.0 m, a 15.6% improvement. Below 80 m, the aiding is strong enough that both converge.
- **Well-aided platform crossover:** at 80 m bias they tie (+1.9%). At 100 m bias adaptive-R wins decisively. This represents deep canyons, tunnel entrances, and heavily reflective building districts.
- **SENTINEL's role on a full AV platform:** both an R-scaling signal (for extreme multipath) AND an integrity flag for route-planning and mode-switching at medium severity.

**Say:**

> "We swept across nine multipath severity levels — 5 m through 100 m — so we're not cherry-picking one scenario.
>
> At modest bias (5–60 m), the wheel odometry + NHC + ZUPT aiding is so effective that fixed-R wins — inflating R unnecessarily discards valid GPS information that the aided filter could use.
>
> At extreme bias (100 m) — deep urban canyons, tunnel entrances — GPS is 100 metres wrong. Fixed-R still partially incorporates this, getting pulled off-track. Adaptive-R inflates R to 10,000 m², effectively dead-reckoning on wheel odometry, and gives 30.4 m vs. 36.0 m for fixed-R. 15.6% improvement in the highest-risk regime.
>
> Full sweep table:
>
> | Bias | Raw GNSS | Fixed-R | Adaptive-R | Winner |
> |------|----------|---------|------------|--------|
> | 5 m  | 7.7 m    | 5.8 m   | 27.5 m     | Fixed-R |
> | 60 m | 64.6 m   | 18.2 m  | 22.7 m     | Fixed-R |
> | 80 m | 75.4 m   | 30.2 m  | 29.6 m     | Tie (+1.9%) |
> | 100 m| 96.1 m   | 36.0 m  | **30.4 m** | **Adaptive-R +15.6%** |
>
> The message: both strategies are part of our system. We rigorously mapped the crossover instead of cherry-picking one scenario. That is more credible than a single number."

**Justification:** Honesty about when the contribution works builds more credibility than over-claiming.

---

## **Section 6: Dashboard Demo (2 slides — NEW)**

> **Insert these 2 slides after the EKF section and before the Novelty section.**

---

### **Dashboard Slide 1: SENTINEL Dashboard Overview**

**Slide title:** `SENTINEL-GNSS DASHBOARD — REAL-TIME ANALYTICS`

**Layout:** Screenshot mosaic of the 6 panels, each labelled.

| Panel                    | What it shows                                               |
| ------------------------ | ----------------------------------------------------------- |
| **Signal Gauge**         | P(DEGRADED) at +5/+15/+30 s — green/amber/red               |
| **Probability Bars**     | CLEAN / WARNING / DEGRADED live confidence                  |
| **Trajectory Map**       | Vehicle path coloured by predicted risk level               |
| **P(DEGRADED) Timeline** | All 3 horizons streaming with threshold lines               |
| **EKF Analytics**        | Blocked-segment RMSE by filter strategy                     |
| **Alert Centre**         | CRITICAL (P > 0.8) and WARNING (P > 0.6) auto-notifications |

**Bottom line:** _FastAPI backend + Next.js frontend · WebSocket at 1 Hz · Runs on any laptop_

**Say:**

> "Everything we've described — prediction, EKF, calibration — lives in a real, running dashboard. It's not a mock-up.
>
> FastAPI streams real pre-computed inference outputs over WebSocket. The Next.js frontend updates at each epoch. Six panels: signal gauge, class probability bars, trajectory map coloured by risk, streaming P(DEGRADED) timeline, EKF analytics, and an alert centre that fires CRITICAL warnings when P exceeds 0.8 at 5 seconds.
>
> Pure SVG visualisations — zero external dependencies. Works offline. Runs on the same laptop we'll demo on today."

---

### **Dashboard Slide 2: Live Demo — Step by Step**

**Slide title:** `LIVE DEMO — 3 MINUTES`

**On-slide step table:**

| Step | Action                                          | What audience sees                           |
| ---- | ----------------------------------------------- | -------------------------------------------- |
| 1    | Open localhost:3000                             | Full dashboard loads — 6 panels              |
| 2    | Select "A_log_0000" (instant blockage scenario) | Prediction data populates                    |
| 3    | Press ▶ Play at 5× speed                        | Timeline starts streaming                    |
| 4    | Watch gauge spike before GNSS drop              | Gauge turns red; CRITICAL alert fires        |
| 5    | Pause — point to lead time                      | "83 m of reaction distance at 60 km/h"       |
| 6    | Switch to EKF Analytics tab                     | Blocked-segment RMSE chart loads             |
| 7    | Point to trajectory map                         | Path colour shifts red through blockage zone |

**Bottom callout:** _"Everything is real pre-computed inference on real GNSS data — not a demo mode."_

**Say during demo:**

> "I'm opening the dashboard now."
> _(select scenario)_
> "Scenario A — the instant blockage scenario from our Beihang campus collection. Real NMEA data, real inference output."
> _(press play)_
> "Watch the signal gauge top-left."
> _(when gauge turns red)_
> "There — P(DEGRADED) at the +5s horizon just crossed 0.8. CRITICAL alert fires. But look at the GNSS quality signal — it hasn't actually failed yet. That's the 5-second window. At 60 km/h, this vehicle has 83 metres to respond."
> _(switch to EKF tab)_
> "EKF analytics — these are the real Tokyo results. Three filter strategies on the blocked segment. Aided EKF wins at 24.3 metres."
> _(point to map)_
> "The trajectory map shifts from green to red as the vehicle approaches the blockage zone. A dispatcher watching this would reroute before entry."
> "Everything you're seeing is real inference output on real GNSS data."

---

## **Section 7: Roadmap & Impact (Slides 19–25)**

### **Slide 19: Publication Plan**

**Say:**

> "We're publishing this across three venues:
>
> **Paper A (GPS Solutions, Q1 journal):**
>
> - Method: Transformer-LSTM architecture, multi-horizon prediction, cross-city validation
> - Why: flagship paper, rigorous and novel
>
> **Paper B (Journal of Navigation):**
>
> - Systems paper: Model comparison, ensemble selection, EKF integration, real RMSE
> - Why: complements Paper A with the applied side
>
> **Conference (ION GNSS+ 2026):**
>
> - Cross-city result as a systems/applications paper
> - Reaches the GNSS community directly
>
> Two substantial papers avoid salami-slicing and have more impact than four thin ones."

**Justification:** Show you have a publication strategy, not scattered work.

---

### **Slide 20–23: Deliverables & Next Steps**

_(Ensemble, dashboard, reproducibility—refer to PPTX)_

---

## **Closing Slides (Slides 36–37)**

### **Slide 36: Key Takeaways**

**Say:**

> "In summary:
>
> 1. **The Problem:** GNSS fails without warning in cities. Autonomous vehicles need time to prepare.
> 2. **Our Solution:** Predict degradation 5–30 seconds ahead using Transformer-LSTM trained on Hangzhou and Hong Kong data.
> 3. **The Proof of Generalisation:** On unseen Tokyo, DEGRADED F1 = 0.75 (ours) vs 0.15 (RandomForest). The deep model learns physics; the trees memorise city-specific patterns.
> 4. **The Navigation Payoff:** Adaptive EKF on real Tokyo data — 47.4 m → 24.3 m blocked-segment RMSE. 48.8% improvement, real data, real streets, held-out city.
> 5. **The System:** Running dashboard, FastAPI + Next.js, WebSocket streaming, deployable today."

**Justification:** Close with a clear story arc — updated to include the real EKF result and the dashboard.

---

### **Slide 37: Thank You**

**Say:**

> "Thank you for your attention. Our code and dataset will be released on GitHub and Zenodo for reproducibility. Questions?"

---

## **Handling Common Questions**

**Q: "Why not just use better hardware (RTK, INS)?"**  
A: "Those are expensive (£10k+). Our approach works with any standard GNSS receiver (£100). And on top of RTK—yes, please, layer it on. Robustness is additive."

**Q: "Why Transformer-LSTM, not just Transformer?"**  
A: "Transformer sees long-range dependencies, LSTM captures directional trends. Ablations show both contribute. Pure Transformer gives 0.767 Macro-F1; full model: 0.821."

**Q: "How do you handle receiver drift?"**  
A: "The 9-state EKF uses wheel odometry, the non-holonomic constraint (a car can't slide sideways), and zero-velocity updates. These three aiding sources together constrain all six position and velocity states. Heading is the hardest — GNSS provides the only absolute heading reference, which is why blanket R-inflation hurts; we use GNSS selectively."

**Q: "Is 149k epochs enough?"**  
A: "It's substantial for supervised learning, but yes, more data helps. We use it wisely: bootstrap CIs, session-level splits, no data leakage. The cross-city result is the most honest test — Tokyo was never in training, and we still hold F1 = 0.75 on the safety-critical class."

**Q: "How do you know the EKF improvement is real and not cherry-picked?"**  
A: "We ran a full severity sweep across multiple multipath levels — not just one scenario. We also validated at three tiers: synthetic, semi-synthetic, and fully real (RTKLIB Trimble GNSS on UrbanNav Tokyo with cm-level SPAN-INS ground truth). The 48.8% on real data is the honest number."

**Q: "Why not just use a fixed EKF with conservative noise?"**  
A: "Conservative fixed-R protects you in blockage but costs accuracy in clean segments — you're always distrusting GNSS even when it's fine. Adaptive-R is the best of both: tight when clean, loose when degraded, driven by prediction rather than a static guess."

**Q: "The dashboard — is this real-time?"**  
A: "Currently it replays pre-computed inference at configurable speed. The model itself runs at 0.039 ms/sample — fast enough for live 10 Hz operation. Adding live inference is a one-endpoint change in the FastAPI backend."

**Q: "The EKF trajectory looks like it is swirling / making loops on the map. Is the filter diverging?"**  
A: "What you are seeing is not divergence — it is the filter recovering from a bad GPS measurement. When GPS reports a position 30–80 m off, the Kalman filter partially moves toward it. In the next 2–3 epochs, wheel odometry + non-holonomic constraint pull the estimate back toward the true direction. That creates a small loop. The RMSE numbers quantify the size: 47.4 m for raw GPS vs. 24.3 m for our EKF. The swirling in the EKF is smaller and shorter than the swirling in raw GPS — that is exactly what we are demonstrating. The RMSE bar chart is the quantitative summary."

**Q: "Some EKF trajectories are far from ground truth. Does that mean the system failed?"**  
A: "The trajectories are on different environments with different characteristics. Odaiba is a waterfront area where GPS errors are random (not persistent) — the EKF can be occasionally worse than raw GPS there because it partially incorporates random spikes. That is documented in our results — we do not hide it. The Student-t Particle Filter handles Odaiba better. No single fusion method dominates every environment — that is itself a finding. For Shinjuku, which is the primary urban canyon case, the EKF gives 48.8% improvement. The trajectory quality reflects the RMSE numbers — look at the bar chart alongside the trajectory and they tell consistent stories."

**Q: "Would using 15 states, 18 states, or 21 states in the EKF give better results?"**  
A: "No, and for clear reasons. Our filter is 2D — we work in the East-North plane. Adding 3D IMU bias states would add unobservable parameters with no measurements to constrain them, which causes numerical instability. The dominant error source is GPS multipath at 30–100 m — the IMU drift during our 10–15 second blockage windows is only 1–3 m. Improving IMU bias estimation from 3 m to 2 m drift would change RMSE by under 1 m — negligible against the 23 m GPS error reduction SENTINEL provides. More importantly, consumer MEMS IMUs cannot observably estimate gyroscope scale factors at the timescales of our drives (2–20 minutes) — those states would be chasing noise. Our 9 states with wheel odometry + NHC + ZUPT aiding already outperforms bare 15-state systems because the aiding provides better constraints than extra bias states alone."

**Q: "Why do you show slides with trajectories if they look messy?"**  
A: "The trajectory is qualitative evidence that the system is working — the SENTINEL EKF trace is visually closer to ground truth than raw GPS, and the excursions are shorter. The RMSE bars are the quantitative evidence. Both tell the same story. If the trajectory confuses more than it helps, redirect to the RMSE figure — 47.4 m to 24.3 m is unambiguous regardless of what the path looks like."

---

## **Equation Diagram Generation Prompts**

> Use these prompts with any AI image tool (ChatGPT, Canva AI, etc.) or recreate in PowerPoint
> using the text boxes and arrow shapes described.

### **Prompt 1 — Adaptive-R Equation (main formula)**

```
Create a slide-ready annotated equation diagram for the two-line formula:

  σ(t)  = σ_base + (σ_deg − σ_base) × P̂_calib(t)
  R(t)  = σ(t)² · I₂

NOTE: interpolation is in standard-deviation space (sigma), then squared — NOT in variance
space. This gives more aggressive R-inflation at intermediate probabilities.

Draw both lines large in the centre, with a brace showing they form one adaptive mechanism.
Add labelled arrows pointing to each part:
- "R(t)" → "GNSS measurement noise covariance fed to Kalman filter at time t (2×2 matrix)"
- "σ_base" → "σ_base = 3 m (std dev). Baseline noise when signal is CLEAN. R_base = 9 m²."
- "σ_deg" → "σ_deg = 100 m (std dev). Full degradation. R_deg = 10,000 m²."
- "(σ_deg − σ_base)" → "Dynamic range in σ-space — 97 m from clean to fully degraded"
- "P̂_calib(t)" → "Calibrated DEGRADED probability from SENTINEL (0 = clean, 1 = degraded)"
- "σ(t)²" → "Squaring converts std dev to variance — the EKF measurement covariance"

Style: dark navy background, white equation text (LaTeX-style font), colour-coded annotation
boxes: green for σ_base, red for σ_deg, blue for the P̂ term. University presentation style.
Add three coloured pills at the bottom:
  green  "P=0   →  σ=3 m   →  R=9 m²       → Trust GNSS"
  amber  "P=0.5 →  σ=51.5 m →  R≈2,652 m²  → Significant caution"
  red    "P=1   →  σ=100 m  →  R=10,000 m² → Dead-reckon"
```

### **Prompt 2 — Kalman Gain Equation**

```
Create an annotated equation diagram for:

  K_t = P⁻_t Hᵀ (H P⁻_t Hᵀ + R_t)⁻¹

Label each component with a pointing arrow:
- "K_t" → "Kalman gain: weight given to the GNSS measurement vs the motion model prediction"
- "P⁻_t" → "Predicted state covariance — uncertainty in dead-reckoning before GNSS correction"
- "H" → "Measurement matrix mapping 4D state [x, y, vx, vy] to 2D GNSS output [x, y]"
- "R_t" → "ADAPTIVE measurement noise — from SENTINEL's P(DEGRADED) — grows during predicted blockage"
- "(H P⁻_t Hᵀ + R_t)⁻¹" → "Total system uncertainty — when R_t is large, K_t shrinks → filter leans on motion model"

Add a callout box: "When SENTINEL predicts degradation → R_t ↑ → K_t ↓ → filter trusts
dead-reckoning over GNSS"

Style: clean white background, LaTeX-style math font, blue/grey annotation arrows pointing
from each symbol to its description box. Academic slide style.
```

### **Prompt 3 — EKF Predict-Update Flow Diagram**

```
Create a circular/loop flow diagram showing the Kalman filter cycle with 4 nodes:

Node 1 TOP — "PREDICT":
  x̂⁻_t = F x̂_{t-1}    (state prediction via motion model)
  P⁻_t = F P_{t-1} Fᵀ + Q   (covariance propagation)
  Annotation: "Wheel odometry + NHC constraint + ZUPT"

Node 2 RIGHT — "SENTINEL INPUT":
  Input: 30-step GNSS feature window (37 features)
  Output: P̂(DEGRADED) at t
  Arrow colour: orange

Node 3 BOTTOM — "ADAPTIVE R":
  R(t) = R_base + (R_deg − R_base) × P̂_calib(t)
  Annotation: "Pre-emptive noise inflation — 5 s before failure"
  Arrow colour: red

Node 4 LEFT — "UPDATE":
  K_t = P⁻_t Hᵀ (H P⁻_t Hᵀ + R_t)⁻¹
  x̂_t = x̂⁻_t + K_t(z_t − H x̂⁻_t)
  Annotation: "Fuse GNSS measurement with adaptive trust"
  Arrow colour: green

Centre text: "1 Hz update loop"
Node colours: PREDICT = blue, SENTINEL = orange, ADAPTIVE R = red, UPDATE = green.
Rounded rectangle nodes, connecting arrows with labels.
```

### **Prompt 4 — Complete System Pipeline Diagram**

> **Use this in:** ChatGPT (GPT-4o image generation), Canva AI, or give it to a designer.  
> **Target size:** 1920×864 px (16:9, landscape, fills one slide)

```
Create a clean, professional infographic showing the full data pipeline for an AI-based
GNSS degradation prediction system for autonomous vehicles. The diagram flows left-to-right
in 5 colour-coded stages across a white background.

STAGE 1 — SENSORS (left, dark navy border #003366):
  Three stacked boxes:
  • "GNSS RECEIVER" (navy fill #E3F2FD): u-blox / Trimble / Septentrio F9P,
    outputs: NMEA · RINEX · C/N₀ · DOP · sat count @ 1 Hz
  • "IMU (100 Hz)" (amber fill #FFF8E1): accelerometer + gyroscope, 3-axis heading + motion
  • "WHEEL ENCODER" (green fill #E8F5E9): vehicle speed, non-holonomic constraint (NHC)
  Small dashed purple box below: "SPAN-INS Ground Truth — validation only (never in training)"

STAGE 2 — FEATURE ENGINEERING (navy/grey border #5A6A86):
  One tall box (grey fill #F5F7FF) with two sub-boxes:
  • "37 FEATURES · 7 GROUPS": C/N₀ max/mean/std/trend · DOP: gdop/pdop/hdop · Satellites:
    count/drop-rate · Receiver: fix quality · Atmospheric: iono/tropo · Temporal Δ: pdop_delta
  • "SLIDING WINDOW" (blue fill #E3F2FD): 30 epochs × 37 features = 30×37 input tensor.
    Labels: +5 s / +15 s / +30 s
  Red italic note below box: "✗  lat/lon excluded — prevents geographic overfitting"

STAGE 3 — SENTINEL MODEL (blue border #003893, light blue tint background):
  Title bar: "SENTINEL ML MODEL — 1.46 M parameters"
  Three stacked boxes inside:
  • "Transformer Encoder" (blue fill): 2 layers · 8 heads · d_model=128 · d_ff=512
    Sub-text: Self-attention captures long-range signal patterns
  • "LSTM (unidirectional)" (amber fill): 2 layers · hidden=256.
    Sub-text: Causal trend — is signal getting worse?
  • Three side-by-side smaller boxes labelled "+5 s" (green), "+15 s" (amber), "+30 s" (red),
    each showing: P(CLEAN) / P(WARNING) / P(DEGRADED)
  Bottom box: "Temperature Scaling T=0.4023": ECE: 0.114 → 0.068 (−40%)
  Small italic: "Focal loss γ=1.0 · class weights [1, 2, 5]"

STAGE 4 — ADAPTIVE EKF (green border #1B873A, light green tint background):
  Title bar: "9-STATE ADAPTIVE EKF"
  Four stacked boxes:
  • "ADAPTIVE R(t)" (red fill #FDECEA): R(t) = σ²_base + (σ²_deg − σ²_base) × P̂_calib
    P̂=0 → R=9 m² (trust) | P̂=1 → R=10,000 m² (ignore)
  • "PREDICT STEP" (amber fill): x̂⁻_t = F x̂_{t-1} · IMU + Odometry + NHC + ZUPT
  • "UPDATE STEP" (green fill): Kₜ = P⁻Hᵀ(HP⁻Hᵀ+Rₜ)⁻¹ · fuse GNSS with adaptive trust
  • "STATE OUTPUT" (blue fill): [x, y, vx, vy, heading, ax, ay, ωz, baro]

STAGE 5 — OUTPUTS & DASHBOARD (right, multi-coloured):
  Three boxes top to bottom:
  • "FILTERED POSITION" (green fill): Blocked RMSE 47.4 m → 24.3 m (+48.8% Tokyo data)
  • "ALERT ENGINE" (red fill): CRITICAL P(DEG)>0.8 @+5s | WARNING P(DEG)>0.6 @+15s
  • "AV ROUTE PLANNER" (amber fill): +5s tighten IMU fusion · +15s pre-engage dead-reckon
    +30s re-route
  Tall box at bottom: "DASHBOARD (FastAPI + Next.js)" with 6 bullet points in matching colours:
    ● Signal Gauge (green) · ● Probability Bars (blue) · ● Trajectory Map (purple)
    ● P(DEGRADED) Timeline (blue) · ● EKF Analytics (amber) · ● Alert Centre (red)

ARROWS:
  - Thick blue arrow: GNSS → Feature Engineering → SENTINEL
  - Thick red arrow: SENTINEL P(DEGRADED) → Adaptive R(t)
  - Amber arrow: IMU → Predict Step (bypasses SENTINEL, curves under the diagram)
  - Green arrow: Wheel Encoder → Predict Step
  - Blue arrow (GNSS position measurement zₜ): curves from GNSS box to Update Step
  - Green arrow: State Output → Filtered Position + Dashboard
  - Orange dotted arrow: SENTINEL P(CLEAN/WARN/DEG) → Alert Engine
  - Purple dashed arrow: SPAN-INS ground truth → right edge (labelled "validation only")

BOTTOM BANNER (navy #003366):
  White text: "Zero-shot cross-city: trained on Hangzhou (Beihang A–E) + HK UrbanNav
              — tested on Tokyo Shinjuku (never seen during training)"
  Star symbol ★ in amber before the text.

TYPOGRAPHY: Clean sans-serif (Inter, Helvetica, or similar).
COLOR PALETTE: navy #003366, blue #003893, cyan #4FC3F7, green #1B873A, red #C62828,
amber #F57F17, purple #6A1B9A, light fills as specified.
```

---

## **Presentation Tips**

1. **Pacing:** 20–25 minutes means ~4 minutes per major section. Don't rush.
2. **Eye contact:** Look at questioners when speaking, not at slides.
3. **Numbers:** When you say "0.892 Macro-F1," pause. Let it sink in. Don't rattle off metrics.
4. **Narrative:** The story is "prediction + action = resilience," not "we built a model and it's good."
5. **Be honest:** Mention limitations (calibration isn't perfect, synthetic demo is controlled). Honesty builds trust.
