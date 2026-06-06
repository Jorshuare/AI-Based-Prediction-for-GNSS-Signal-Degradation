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
| Beihang Field A–E | Beijing | Septentrio | train / test |
| UrbanNav Deep/Harsh | Hong Kong | 9+ types | train / val |
| Tokyo Shinjuku | Tokyo | Trimble + u-blox | **held-out city** |

**Say:**
> "We collected 149,662 labelled epochs—one-second GNSS snapshots, each labelled CLEAN, WARNING, or DEGRADED.
>
> Why multi-city? Because **cross-city generalisation is hard**. A model trained in Beijing might fail in Tokyo. Tokyo is completely held-out—it never touches training. That's how we prove the model actually generalises.
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

## **Section 3: Method (Slides 8–11)**

### **Slide 8: The SENTINEL-GNSS Architecture**
**Say:**
> "The model is a Transformer-LSTM hybrid. Here's why:
>
> **Transformer** (2 layers, 8 attention heads, d=128):
> - Sees long-range dependencies in the 30-second window
> - 'Ah, this satellite started fading 20 seconds ago—it's about to drop'
>
> **BiLSTM** (2 layers, hidden=256):
> - Captures the directional trajectory toward degradation
> - 'The signal is getting worse; that trend will continue'
>
> **Three output heads** (+5s, +15s, +30s):
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

## **Section 4: The EKF—From Prediction to Navigation (Slides 12–14)**

### **Slide 12: Why EKF?**
**Say:**
> "Predicting degradation is one thing. **Using the prediction to improve actual navigation** is another—that's the real contribution.
>
> Standard approach: Kalman filter with fixed measurement noise. The filter always trusts GNSS equally.
>
> **Our innovation:** Adaptive measurement noise R based on predicted degradation.
> - When P(DEGRADED) is high → inflate R → distrust GNSS → lean on motion model
> - When P(DEGRADED) is low → normal R → use GNSS to correct drift
>
> The prediction **pre-empts** the failure. Before GNSS actually breaks, the filter is already leaning on dead-reckoning. That's the payoff."

**Justification:** Close the loop: prediction → filter adaptation → better navigation.

---

### **Slide 13: EKF Mechanism Slide**
**(Use fig_ekf_mechanism_concept.png)**

**Say:**
> "The EKF runs in a cycle:
>
> 1. **PREDICT:** Dead-reckoning via velocity. 'Where will the vehicle be in 1 second, assuming constant motion?'
> 2. **UPDATE:** Fuse GNSS measurement. But R (measurement noise) is adaptive:
>    - R = R_base + (R_degraded - R_base) × P(DEGRADED)
>    - At P=0: R=3m (tight, trust GNSS)
>    - At P=1: R=100m (loose, distrust GNSS)
> 3. The Kalman gain K = P H^T (H P H^T + R)^{-1} automatically balances them.
> 4. **Result:** filtered position, smoother trajectory, less jumpy during blockage.
>
> Repeat every 1 second."

**Justification:** Show the mechanism is simple but principled.

---

### **Slide 14: Synthetic Blockage Validation (Option A)**
**(Use fig20_ekf_option_a_synthetic.png)**

**Say:**
> "We test on a controlled scenario: a 300-epoch trajectory with simulated GNSS blockage from epochs 120–180. The blockage has noise spikes and multipath bias. Our predictor warns starting at epoch 115 (proactive).
>
> **Results on the blockage segment:**
> - Raw GNSS: 54.4 m error (noisy)
> - Fixed-R EKF: 45.6 m (-16% vs raw)
> - Adaptive EKF (ours): 36.0 m (-34% vs raw, -21% vs fixed)
>
> The adaptive filter **pre-emptively distrusts GNSS before it fails**. That's why it wins.
>
> This is a proof-of-concept on synthetic data. **Next phase: real UrbanNav Tokyo data with actual blockage events.**"

**Justification:** Show synthetic validation works; frame it as Phase 1, with Phase 2 on real data coming.

---

## **Section 5: Cross-City & Ensemble (Slides 15–17)**

*(Already have slides; same narrative as above)*

---

## **Section 6: Future Work—Option B, Phase 2a (Slide 18)**

### **Slide 18: Real-Data EKF Validation (Option B)**
**Say:**
> "The synthetic result is promising, but we need **real-world proof**. That's Option B.
>
> **Why UrbanNav Tokyo?**
> - UrbanNav is a public dataset with real GNSS observations (rover_ublox.obs in RINEX format)
> - **Crucially:** it has cm-level ground truth (SPAN-INS trajectory in reference.csv)
> - SPAN-INS is inertial navigation system + GPS, post-processed to give the true position
> - That lets us compute **real RMSE** (not simulated)
> - It also has IMU data (imu.csv) so we can test a 9-state EKF
> - Tokyo is the same held-out city where our model generalises well
>
> **What we'll do:**
> 1. Parse rover GNSS observations (RTKLIB SPP) → single-point positions
> 2. Parse IMU + reference trajectory
> 3. Run 9-state EKF (IMU-driven prediction, GNSS update, adaptive R)
> 4. Compute RMSE vs ground truth
> 5. Show real-world RMSE gain (expected: 15–30% during actual blockage)
>
> This is **honest validation**—not synthetic, not hand-tuned. Real data, real blockage."

**Justification:** Explain why UrbanNav is the right choice: it has ground truth (cm-level SPAN-INS), it's public, it's the same held-out city, and it has real blockage.

---

## **Section 7: Roadmap & Impact (Slides 19–25)**

### **Slide 19: Publication Plan**
**Say:**
> "We're publishing this across three venues:
>
> **Paper A (GPS Solutions, Q1 journal):**
> - Method: Transformer-LSTM architecture, multi-horizon prediction, cross-city validation
> - Why: flagship paper, rigorous and novel
>
> **Paper B (Journal of Navigation):**
> - Systems paper: Model comparison, ensemble selection, EKF integration, real RMSE
> - Why: complements Paper A with the applied side
>
> **Conference (ION GNSS+ 2026):**
> - Cross-city result as a systems/applications paper
> - Reaches the GNSS community directly
>
> Two substantial papers avoid salami-slicing and have more impact than four thin ones."

**Justification:** Show you have a publication strategy, not scattered work.

---

### **Slide 20–23: Deliverables & Next Steps**
*(Ensemble, dashboard, reproducibility—refer to PPTX)*

---

## **Closing Slides (Slides 36–37)**

### **Slide 36: Key Takeaways**
**Say:**
> "In summary:
>
> 1. **The Problem:** GNSS fails without warning in cities. Autonomous vehicles need time to prepare.
> 2. **Our Solution:** Predict degradation 5–30 seconds ahead using Transformer-LSTM on multi-city GNSS data.
> 3. **The Innovation:** Use predictions to **adaptively tune** a Kalman filter. Pre-emptively distrust degraded GNSS, lean on motion model.
> 4. **The Proof:** 34% RMSE improvement on synthetic blockage. Cross-city generalisation on unseen Tokyo. Next: real-data validation on UrbanNav.
> 5. **The Impact:** More robust, safer autonomous driving navigation in challenged GNSS environments."

**Justification:** Close with a clear story arc.

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
A: "That's a Phase 2 item. Currently, we clip velocities and assume constant-velocity motion. Real receivers have accelerations (turning). 9-state EKF in Phase 2 handles that with IMU."

**Q: "Is 149k epochs enough?"**  
A: "It's substantial for supervised learning, but yes, more data helps. We use it wisely: bootstrap CIs, session-level splits, no data leakage. Next phase: add more multi-receiver data."

---

## **Presentation Tips**

1. **Pacing:** 20–25 minutes means ~4 minutes per major section. Don't rush.
2. **Eye contact:** Look at questioners when speaking, not at slides.
3. **Numbers:** When you say "0.892 Macro-F1," pause. Let it sink in. Don't rattle off metrics.
4. **Narrative:** The story is "prediction + action = resilience," not "we built a model and it's good."
5. **Be honest:** Mention limitations (calibration isn't perfect, synthetic demo is controlled). Honesty builds trust.
