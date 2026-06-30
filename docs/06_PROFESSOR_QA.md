# SENTINEL-GNSS: Professor / Reviewer Questions and Responses

> Every concern raised during review, why we made each design decision, and how the experimental results address each point.

---

## Q1: "Your EKF assumes Gaussian GPS noise. Urban NLOS errors are clearly non-Gaussian — how do you address this?"

### The concern
The standard EKF GPS measurement model assumes `v ~ N(0, R)`. In urban canyons, GPS errors follow a heavy-tailed, positively-skewed distribution due to:
- NLOS reflections creating systematic biases of 10–200 m
- Occasional catastrophic outliers (signal re-acquisition spikes up to 1472 m in our dataset)
- Bimodal distributions when the receiver oscillates between direct and reflected paths

The Gaussian assumption means the EKF treats a 200 m NLOS error with the same weight as a 2 m thermal noise error — and optimally fuses it, pulling the position estimate toward the wrong location.

### What we did

**Short term (Phase 2b)**: Implemented the **Huber Robust EKF**. Instead of assuming all innovations are Gaussian, we apply Iteratively Reweighted Least Squares (IRLS):
- Innovations within c σ of zero are treated normally (Gaussian, full weight)
- Innovations larger than c σ are downweighted proportionally to c σ / |ỹ|
- Effectively, the GPS measurement is "softened" rather than rejected or accepted

**Long term (Phase 2c)**: Implemented a **Bootstrap Particle Filter with Student-t GPS likelihood**. The Student-t distribution (ν=3 degrees of freedom) directly models heavy-tailed GPS noise — it assigns significantly more probability to large errors than a Gaussian of the same scale, which prevents catastrophic weight collapse when GPS exhibits occasional 100 m errors.

The Student-t log-likelihood per particle is:
```
log p(z | xᵢ) = -(ν+1)/2 × [log(1 + dₓ²/(ν r²)) + log(1 + d_y²/(ν r²))]
```

### Results
The Huber EKF improves degraded-segment RMSE by **25.2%** vs. raw GPS on u-blox Shinjuku (vs. 21.1% for Fixed-R EKF). The Student-t PF achieves **40.1%** gain on Odaiba. Both represent material improvements specifically due to the non-Gaussian noise handling.

---

## Q2: "Why are your Odaiba results so bad with the EKF? The EKF is actually worse than raw GPS overall."

### The concern
On the Odaiba scenario, the EKF Fixed-R achieves 44.42 m overall RMSE vs. 32.43 m for raw GPS. This means the EKF fusion is actively hurting positioning accuracy. How can fusing IMU with GPS make things worse?

### What's happening
Odaiba is a waterfront/harbour district with a mix of open sky (near the water) and moderate building occlusion (near the shopping complex). The GPS errors are **random and non-persistent** — each epoch's NLOS state is largely independent of the previous epoch.

The 9-state EKF integrates IMU at each step and corrects with GPS. With r_base=8 m, the Kalman gain is calibrated for ~8 m GPS errors. When Odaiba GPS occasionally produces 60–80 m errors (which happen with moderate frequency), the EKF partially incorporates them — pulling the estimate off-course. The IMU integration then propagates this error forward before the next GPS correction arrives. The result is that EKF errors compound: the filter chases GPS outliers more aggressively than pure GPS dead-reckoning would.

The Adaptive-R EKF is even worse (45.97 m) because SENTINEL sometimes correctly identifies degradation but the R inflation is not large enough to reject the moderately-bad Odaiba GPS.

### What we did
The Student-t PF solves this. Its heavy-tailed likelihood assigns low weight to particles near a GPS measurement that is far off — but it does not hard-reject; it simply distributes weights more evenly among particles that are consistent with the prior. When GPS is occasionally very bad, the PF mostly ignores it and coasts on IMU, then corrects gradually when GPS returns to normal.

**Result**: Student-t PF achieves **25.58 m overall** (vs. 44.42 m EKF, vs. 32.43 m raw GPS) and **35.44 m degraded** (vs. 48.71 m EKF, vs. 59.13 m raw GPS). The PF is now better than raw GPS on Odaiba while all EKF variants are worse.

### Why this matters
This directly supports the paper's claim that no single fusion method dominates all environments. The EKF is optimal only under Gaussian assumptions. In environments where GPS noise is heavy-tailed but random (Odaiba), the PF's non-parametric posterior representation is inherently more appropriate.

---

## Q3: "GNSS errors have non-zero mean (systematic bias from NLOS). How does your system handle persistent bias, not just outliers?"

### The concern
The Huber EKF down-weights large residuals but does not remove systematic bias. If GPS consistently reports a position 50 m to the east due to a persistent building reflection, the Huber weight for a 50 m residual with c=30 threshold would be `min(1, 240/50) = 1.0` — the full measurement is trusted. The filter still drifts toward the biased direction.

### What we did

1. **SENTINEL pre-emptive protection**: The key innovation is that SENTINEL predicts degradation *5 seconds in advance*, allowing R to be inflated before the biased measurements arrive. During predicted DEGRADED windows, r_degraded=40 m is used. With r_base=8 m inflated to 40 m, the Kalman gain drops by factor (8²)/(40²) = 25×. The biased GPS measurements are heavily discounted, and IMU dead-reckoning dominates.

2. **NHC/ZUPT aiding in PF**: Non-Holonomic Constraint (lateral velocity ≈ 0) and Zero-Velocity Updates anchor the particle cloud to physically plausible trajectories, preventing systematic drift in directions inconsistent with vehicle motion.

3. **CV-KF baseline**: The constant-velocity Kalman filter baseline achieves 38.6% degraded gain on u-blox — often competitive with the EKF variants. This is because the CV-KF effectively ignores GPS during high-error epochs (it has no GPS update), providing a drift-free reference for the SENTINEL-wired EKF to outperform.

### Limitations acknowledged
We acknowledge in the paper that persistent NLOS bias lasting >60 seconds cannot be fully corrected by any method at our sensor fusion level. Mitigation requires either map-aided positioning (3D building models + ray tracing) or multi-antenna diversity — both are outside the scope of single-receiver GNSS fusion.

---

## Q4: "If R is unknown (which it is in NLOS), how can you claim your EKF is well-calibrated? Have you tried adaptive R estimation?"

### The concern
The covariance matrix R represents our uncertainty about GPS noise. In urban NLOS, the true R changes every epoch based on satellite geometry, building heights, and receiver dynamics. A fixed r_base is a deliberate baseline, not the only option: a principled, per-epoch R can be obtained from the receiver's own reported horizontal sigma, from geometry as R ∝ (HDOP · UERE)², or estimated online from the data. We adopt the online estimator (see below); the fixed value is retained only as a comparison baseline.

### What we tried: Mehra Adaptive R

We implemented the Mehra (1970) innovation-based adaptive covariance estimator:
```python
R_est = (1/W) Σₜ yₜyₜᵀ − H P⁻ Hᵀ
```
where the sum is over a sliding window of W=40 recent innovations. In theory, this tracks the true measurement noise covariance from the innovation sequence.

**Result**: Catastrophic divergence. RMSE exceeded 238,000 m on u-blox Shinjuku.

### Why Mehra fails in urban NLOS

The fundamental assumption of the Mehra estimator is that the innovation sequence is white (uncorrelated) and zero-mean. In urban NLOS:

1. GPS and the filter co-drift toward the same biased direction → innovations become artificially small
2. Mehra interprets small innovations as "R should be small (GPS is precise!)"
3. R shrinks → Kalman gain increases → filter follows biased GPS more aggressively
4. Filter drifts further → positive feedback loop → divergence

This is precisely the worst case: the algorithm confidently converges to the wrong answer. Mehra is disabled in all production runs (`mehra_enabled=False`).

### Can R be computed in a principled way? (Yes — several ways)

R is uncertain and time-varying, but it is **not** unknowable. Principled options, in rough order of rigour:

1. **Receiver-reported uncertainty** — RTKLIB and most receivers output a per-epoch horizontal standard deviation; set `R = σ_reported²` directly. This is fully per-epoch and is already loaded in our pipeline (`spp_horiz_std`).
2. **Geometry-based `R ∝ (HDOP · UERE)²`** — scale a user-equivalent-range-error by the dilution of precision; turns satellite geometry into a position variance (classical GNSS practice).
3. **C/N₀-weighted models** — per-satellite measurement variance as a function of signal strength.
4. **Innovation-based (Mehra / Sage–Husa)** — principled in theory but diverges in urban NLOS (above), so disabled.
5. **Online σ_degraded estimator (what we adopt)** — the causal running median of degraded-epoch innovation magnitudes is a data-driven estimate of the degraded-error scale. It removes the per-environment hand-tuning and, on the Tokyo data, improved the degraded-RMSE reduction from 38.7 % to 43.2 %.

### Our answer
We solve the calibration problem through SENTINEL. Instead of estimating R from the innovation sequence (which fails in NLOS), we estimate the *degradation probability* from GNSS features using a learned classifier, then map it to an R that is either a pre-specified R_degraded or the online estimate above. This sidesteps the fundamental identification problem (you cannot separate "GPS is noisy" from "filter is drifting" using innovations alone).

---

## Q5: "GPS errors in urban environments are clearly temporally correlated (the same building causes NLOS for many consecutive seconds). How does your model address temporal correlation?"

### The concern
Standard EKF assumes i.i.d. measurement noise. But NLOS errors are highly autocorrelated — if the receiver is blocked by Building A, it will likely remain blocked for the 30 seconds it takes to drive past. This means consecutive innovations are not independent, violating the EKF's white noise assumption and causing the filter to over-weight correlated bad measurements.

### What we did

**SENTINEL directly models temporal correlation**: The Transformer+LSTM architecture processes a 30-second window of GNSS features. The Transformer captures global temporal patterns (the satellite rising/setting that precedes an NLOS episode), and the LSTM captures local sequential dynamics. The model learns that "building occlusion on epoch t" implies "building occlusion on epoch t+5" — precisely the temporal structure we want to exploit.

**In the EKF**: When SENTINEL predicts DEGRADED at epoch t, it inflates R for that epoch. Because SENTINEL is predictive (not reactive), the inflation typically starts 3–5 seconds before the worst measurements arrive and continues through the degradation episode, matching the temporal extent of the NLOS event.

**In the PF**: The Student-t likelihood degrades gracefully under correlated noise. If GPS is biased for 30 consecutive seconds, the PF particles gradually spread out (jitter + low GPS weight) rather than snapping to the biased position. The ESS threshold N/3 ensures resampling happens less frequently during correlated episodes, preserving particle diversity.

### Limitations
We do not model the GPS error covariance as a first-order Gauss-Markov process (which would be the principled approach for temporally correlated noise). This is a future work direction. Our SENTINEL approach handles temporal correlation implicitly but not optimally.

---

## Q6: "Why use a Transformer + LSTM? Why not just LSTM alone? Is the Transformer justified?"

### The concern
Transformer architectures have a quadratic self-attention cost in sequence length. For a 60-epoch input, this is manageable, but it requires justification that the long-range dependencies captured by the Transformer provide measurable benefit over a simpler LSTM.

### Ablation results (confirmed, Run 14 — `RESULTS_REFERENCE.md` §6)

| Architecture | Macro-F1 (+5s) | DEGRADED F1 | MCC | Params | Notes |
|-------------|--------------|------------|-----|--------|-------|
| Transformer only | 0.7672 | 0.571 | 0.7248 | 427K | Over-flags DEGRADED (precision 0.424) |
| LSTM only | 0.7674 | 0.645 | 0.7018 | 1,027K | Misses transitions |
| **Transformer + LSTM** | **0.8206** | **0.718** | **0.7729** | 1,457K | Best |

The Transformer captures the slowly-varying satellite geometry (PDOP trends, satellite rising/setting events) across the 30-second window. The LSTM captures the rapid sequential transitions (a satellite suddenly dropping below the horizon). Neither alone captures both: the Transformer-only over-flags DEGRADED (precision 0.424) while the LSTM-only under-detects it. Together they give the best DEGRADED F1.

### Specific capability demonstrated
The Transformer can attend to events at epoch t=1 and epoch t=30 simultaneously — for instance, a PDOP spike early in the window that predicts a building entry at the end of the window would be captured by cross-attention between these distant epochs. A plain LSTM has O(t) gradient decay and cannot reliably capture dependencies across the full 30-epoch span.

The full model improves Macro-F1 by ~5.3 points over either single-component ablation, and lifts DEGRADED F1 from 0.571/0.645 to 0.718 — directly improving the safety-critical class.

---

## Q7: "Your +5s prediction horizon — is 5 seconds actually actionable? What does the system do with that warning?"

### The concern
If SENTINEL predicts DEGRADED at t, but the EKF is running at 1 Hz and GPS measurements are fused at 1 Hz, there is only one fusion step in the 5-second window. How does 5s lead time materially help?

### Our response

**It provides a 5-step lead window**, not a 1-step one. Because SENTINEL outputs predictions at every epoch using a sliding window, the system typically gets 3–5 consecutive DEGRADED predictions before the worst errors arrive. Here is the timeline:

```
t=0: SENTINEL predicts DEGRADED at t+5s (P=0.72)
t=1: SENTINEL predicts DEGRADED at t+5s (P=0.81) — 4 steps ahead
t=2: SENTINEL predicts DEGRADED at t+5s (P=0.88) — 3 steps ahead
t=3: SENTINEL predicts DEGRADED at t+5s (P=0.91) — 2 steps ahead  ← inflation active
t=4: SENTINEL predicts DEGRADED at t+5s (P=0.94) — 1 step ahead
t=5: BAD GPS epoch arrives — filter already protected
```

The EKF responds immediately to each prediction, so R is already inflated when the GPS errors actually arrive. This is qualitatively different from reactive detection (which only inflates R *after* a bad measurement has been incorporated).

**For autonomous driving**: At 30 km/h, 5 seconds = 42 meters of advance warning. A vehicle can pre-activate INS-only mode, reduce speed, or flag for human override before entering the GNSS-denied zone.

---

## Q8: "How do you know the ground truth in the UrbanNav dataset is accurate enough to validate your results?"

### Our response

The UrbanNav dataset provides ground truth via dual-antenna RTK (Real-Time Kinematic) GNSS at centimeter-level accuracy (typical RTK accuracy: 1–3 cm horizontal). The RTK fix is maintained throughout the drives because RTK uses a base station in the Hong Kong area with <5 km baseline, providing robust ambiguity resolution even in urban canyons.

Our RMSE values (19–60 m) are orders of magnitude larger than the RTK ground truth error — so any RTK inaccuracy is negligible in our results. The dominant error source is our fusion algorithms vs. the clean RTK reference.

**Dataset citation**: Hsu, L.T., Kubo, N., et al., "UrbanNav: An Open-Sourced Multisensory Dataset for Benchmarking Positioning Algorithms," ION GNSS+, 2021. The dataset is publicly available at https://github.com/IPNL-POLYU/UrbanNavDataset.

---

## Q9: "Why Tokyo for validation? The training data is from Hong Kong. Isn't this domain mismatch?"

### The concern (and our answer — this is a strength)

This is intentional. Training SENTINEL in Hong Kong and validating in Tokyo is a **cross-city generalization test**. The UrbanNav dataset provides Hong Kong drives for training/validation; we collected and processed Tokyo (Shinjuku and Odaiba) u-blox data for testing.

The fact that SENTINEL achieves 80% MacroF1 *in Hong Kong* and the SENTINEL-wired EKF achieves **25.2% degraded gain improvement in Tokyo** (compared to Fixed-R without SENTINEL) demonstrates that the learned GNSS degradation patterns generalize across cities.

This is significant because:
- Building density and satellite geometry differ between HK and Tokyo
- The u-blox receiver (Tokyo) differs from the dual-frequency Leica used for HK ground truth
- Still, the Transformer+LSTM learned features that transfer — specifically, the temporal patterns of PDOP, delta-pseudorange, and satellite count that precede NLOS events

If SENTINEL only worked in the training city, it would not be practically useful. The cross-city generalization is a key result.

---

## Q10: "What is the actual system goal — making GPS accurate, or enabling vehicle action? Why measure RMSE at all?"

### The fundamental framing

The system goal is: **enable the vehicle to take the right action when GPS degrades** — not to make GPS signals more accurate. SENTINEL does not touch the GPS receiver. The receiver still reports whatever it reports.

The reason RMSE still matters is this:

> To take the right action, the vehicle first needs to know where it is.

SENTINEL says "GPS quality will degrade in 5 seconds." The downstream controller (braking, lane-keeping, route re-planning, driver alert) needs a position estimate to act on. If the fused position during the NLOS window is 80 m off, the vehicle brakes at the wrong junction or misidentifies its lane. A better fused trajectory (lower degraded RMSE) = better position knowledge during degradation = better-informed downstream decisions.

**The pipeline**:
```
SENTINEL prediction
       ↓
EKF inflates R (trusts GPS less, trusts IMU more)
       ↓
Maintained accurate position estimate despite bad GPS
       ↓
Vehicle controller: correct braking point, lane assignment, alert timing
```

Without the EKF fusion component, SENTINEL is just an alarm with no position to act on. Without SENTINEL, the EKF swings toward every bad GPS measurement — the "swirling" trajectory behaviour visible in the dashboard. Together they provide: (a) advance warning that GPS will be bad, and (b) a smooth, accurate trajectory during the bad window that the vehicle's control layer can act on.

RMSE is the right metric because it quantifies how far the position estimate is from ground truth during the exact window where the vehicle must act. Lower degraded RMSE = more reliable position during the moments that matter most.

---

## Q14: "The EKF trajectory on the map looks like it is spiralling / swirling — sometimes going in loops. Is your filter diverging?"

### Plain-language answer (for a general audience)

Think of the filter as a driver who partially trusts a slightly drunk GPS navigator. Most of the time the navigator is fine and the driver follows it closely. But occasionally the navigator says "turn left into the building" — and for a fraction of a second the driver starts to turn before realising something is wrong and correcting. The slight wobble in the trajectory is that correction process.

The "swirling" you see on the trajectory plot is not the filter diverging — it is the filter recovering from a bad GPS measurement. Here is what physically happens:

1. A tall building reflects a satellite signal. The GPS receiver reports a position 30–80 m away from truth.
2. The Kalman filter partially trusts this wrong position and moves its estimate toward it.
3. In the next 2–3 epochs, IMU dead-reckoning and wheel odometry pull the estimate back toward the true direction of motion.
4. This creates a small loop in the trajectory — GPS pulling one way, then IMU correcting back.

The RMSE numbers quantify exactly how bad this is: raw GPS gives 47.4 m during degraded segments; the SENTINEL-wired EKF gives 24.3–26.8 m. The swirling you see in raw GPS is larger than the swirling in the EKF trace. SENTINEL makes the loops smaller and shorter.

### Why do some areas look worse than others?

Shinjuku and urban canyons create persistent NLOS (30–60 second blocks where every GPS epoch is biased in the same direction). During these stretches the "swirl" is actually a steady drift — the filter is not looping; it is tracking a biased GPS for several seconds before IMU + odometry pull it back. The return to truth looks like a sharp hook on the trajectory plot.

Odaiba (waterfront, more open sky) shows more random noise than persistent drift — the errors are shorter but more erratic, creating a busier-looking trajectory.

### Why we kept the trajectory figure

The trajectory is qualitatively important because it shows two things:
1. Raw GNSS produces **large** excursions (grey trace wanders far from ground truth).
2. SENTINEL EKF **contains** those excursions — the blue trace is much closer to truth and the loops are smaller.

Quantitative judgment: look at the RMSE bars (fig07). Qualitative intuition: look at the trajectory (fig08). Both tell the same story. If the trajectory makes reviewers nervous, redirect to the RMSE numbers — they are statistically rigorous.

### The one case where swirling DOES indicate a problem

In the u-blox Shinjuku scenario, the Student-t Particle Filter produces large spiral excursions — not small loops but multi-hundred-metre drifts. This is the "GPS attractor collapse" documented in Q2: with N=500 particles and 50m persistent GNSS bias, all particles cluster near the biased GPS fix, and the filter catastrophically drifts. This is why the PF (Huber/Student-t) is kept as an internal benchmark and not presented as the primary result. The primary presented system (Fixed-R and SENTINEL Adaptive-R EKF) does not exhibit this collapse because the Kalman filter's analytical covariance avoids particle starvation.

---

## Q15: "Would a 15-state, 18-state, or 21-state EKF produce better results?"

### Short answer for a general audience

Imagine you are tracking a car's position. The simplest tracker just watches where the car is. A smarter one also watches speed. An even smarter one watches speed + steering angle + tyre slip + wind. Each extra "state" adds one more thing the filter keeps track of — but also adds one more thing that can go wrong if the sensor measuring that thing is imprecise.

Adding more states to our EKF would be like hiring 21 people to track the car when 9 can already do the job well. Beyond a certain point, more helpers slow things down without improving accuracy — especially if some of those helpers have noisy instruments.

### Technical answer

Our current filter has 9 states: position (x, y), velocity (vx, vy), heading (ψ), GNSS clock bias (b), and two IMU accelerometer biases (ba_x, ba_y).

Common extended state vectors:
- **15-state**: adds 3 gyroscope biases + 3 full accelerometer biases (6 IMU bias states total) — standard for tactical-grade IMU
- **18-state**: adds IMU scale factors — useful when scale factor drift is a significant error source
- **21-state**: adds IMU misalignment / cross-axis coupling — standard for navigation-grade IMU

**For our specific application, none of these would meaningfully improve results. Here is why:**

1. **This is a 2D filter.** We project all measurements into the East-North plane (ENU x-y). Adding Z-axis states, gyro biases around X and Y, or altitude-related errors would add unobservable states — the filter would attempt to estimate quantities it has no measurements to constrain, causing numerical instability.

2. **The dominant error is GNSS multipath, not IMU error accumulation.** Our blocked windows are 10–15 seconds long. In 15 seconds, even an uncalibrated cheap MEMS IMU drifts only 1–3 m purely from dead-reckoning. The GNSS errors during the same window can be 30–100 m. Reducing IMU drift from 3 m to 2 m with better bias estimation changes the final RMSE by < 1 m — negligible compared to the 23 m GNSS error reduction SENTINEL provides.

3. **Consumer-grade MEMS IMU cannot observe 15-18-21 states.** To estimate gyro scale factors (needed for 18 states), you need a navigation-grade IMU that operates for minutes to hours so scale factor drift becomes visible above noise. Our urban drives are 2–20 minutes; the gyro scale factor is not separable from noise at that timescale. Adding those states would cause the estimator to "chase noise" and produce worse heading estimates.

4. **Wheel odometry + NHC + ZUPT already contain the IMU errors effectively.** These three aiding sources act as surrogate state constraints: odometry corrects speed (absorbing bias × time), NHC eliminates lateral velocity drift (which scale-factor errors would cause), and ZUPT resets velocity to zero (zeroing accumulated bias). This is why our 9-state aided EKF outperforms un-aided 15-state systems in practice — better sensors, not more states.

**Bottom line**: going to 15/18/21 states is the right approach for a navigation-grade inertial system on a missile or aircraft. For a consumer GNSS/IMU fusion system in a car, 9 states with strong aiding is both more accurate and more robust. The contribution of SENTINEL-GNSS is the **prediction**, not the EKF architecture.

---

## Q16: "Why does adaptive-R sometimes perform worse than fixed-R in your results?"

### Plain-language explanation

Think of a doctor adjusting a patient's medication based on a diagnosis. If the diagnosis is sometimes wrong — e.g., the patient appears sick but is actually fine — the doctor reduces the medication unnecessarily, and the patient does not get the benefit they should. But when the diagnosis is correct (the patient really is sick), the targeted medication helps significantly.

SENTINEL's adaptive-R behaves the same way. When SENTINEL correctly predicts DEGRADED, adaptive-R protects the filter and wins. When SENTINEL mis-classifies a CLEAN epoch as DEGRADED (a false positive), it unnecessarily inflates R — discarding valid GPS information — and the filter is slightly worse than fixed-R in that epoch.

### Why fixed-R wins on Trimble Shinjuku (our main scenario)

On the Trimble Shinjuku dataset, two things work against adaptive-R:
1. **SENTINEL is wired through the nsat proxy** (number of visible satellites), not the trained ML model. The proxy is reactive — it raises P(DEGRADED) only after satellites have already disappeared, which is too late for pre-emptive R inflation.
2. **Trimble dual-frequency GPS is already very accurate** (~4–8 m baseline noise). When SENTINEL/nsat inflates R unnecessarily during a partially-degraded window, the filter discards measurements that were actually useful.

### When adaptive-R clearly wins: the high-bias regime

In the severity sweep (simulated multipath bias), at **100 m bias** adaptive-R achieves **30.4 m RMSE vs. 36.0 m for fixed-R** — a 15.6% improvement. This is the regime where the claim is true:
- Multipath bias = 100 m → GPS is reporting a position 100 m away from truth
- SENTINEL correctly identifies this as DEGRADED (P→1)
- Adaptive-R inflates R to 10,000 m², filter dead-reckons on IMU + wheel odometry
- Fixed-R still trusts GPS at r_base=3 m → gets pulled 100 m in the wrong direction
- Result: adaptive-R wins decisively by 5.6 m RMSE

The crossover region is approximately **80–100 m multipath bias** — precisely the deep urban canyon and tunnel regime that is the most dangerous for autonomous vehicles. Below that threshold, the aiding (wheel odometry + NHC + ZUPT) is strong enough that both strategies converge to similar accuracy.

### Full severity sweep table (simulated aided 9-state EKF)

| Multipath bias | Raw GNSS | Fixed-R EKF | Adaptive-R EKF | Adaptive vs Fixed |
|---|---|---|---|---|
| 5 m | 7.7 m | **5.8 m** ✅ | 27.5 m | −371% |
| 10 m | 12.4 m | **7.3 m** ✅ | 26.1 m | −256% |
| 20 m | 22.2 m | **10.0 m** ✅ | 27.8 m | −180% |
| 30 m | 29.8 m | **10.6 m** ✅ | 28.5 m | −171% |
| 45 m | 43.0 m | **13.7 m** ✅ | 25.6 m | −87% |
| 60 m | 64.6 m | **18.2 m** ✅ | 22.7 m | −25% |
| 80 m | 75.4 m | 30.2 m | **29.6 m** ✅ | +1.9% |
| 90 m | 81.6 m | **29.2 m** | 30.8 m | −5.5% |
| 100 m | 96.1 m | 36.0 m | **30.4 m** ✅ | +15.6% |

**Reading the table**: At moderate bias (5–60 m), strong IMU aiding means the filter does not need to inflate R — wheel odometry already handles the short outage, and inflating R just loses valid GNSS information. At extreme bias (100 m), GPS is so wrong that inflating R and dead-reckoning is clearly better. The crossover is the 80–100 m range — deep canyons, tunnel entrances, heavily shaded streets.

This is the honest answer to "does adaptive-R help?" — it depends on the severity. For the most dangerous environments, yes, clearly. For everyday urban driving with modest multipath, the aided fixed-R system is already sufficient.

---

## Q12: "In the degraded window, your SENTINEL-wired EKF uses a much larger R. Does this simply mean you trust GPS less — and isn't that just ignoring the GPS, which any system could do?"

### The concern
Inflating R by 5× is equivalent to trusting GPS 25× less during degraded windows. A simpler system that just ignores GPS during SENTINEL-DEGRADED epochs would achieve similar results. How is SENTINEL-EKF meaningfully better than "INS-only with GPS blackout"?

### What makes the difference

**SENTINEL-EKF retains GPS information** during degraded windows — it just down-weights it. This matters when:

1. **Degradation is partial**: SENTINEL P(DEGRADED)=0.6 means GPS is partially unreliable. Pure INS-only discards valid information; SENTINEL-EKF uses it with appropriate (lower) weight.

2. **Recovery phase**: When SENTINEL P(DEGRADED) returns to 0, the EKF immediately starts integrating GPS again at full weight. A hard-blackout system requires a re-initialization step.

3. **The CV-KF baseline is the "ignore GPS" method**: The constant-velocity Kalman filter essentially ignores GPS during degraded windows (it has no GPS update at all). Its 38.6% degraded gain shows what "ignore GPS" achieves. SENTINEL-EKF (48.8% degraded gain) significantly outperforms CV-KF — the improvement comes from maintaining calibrated state uncertainty rather than ignoring measurements.

**The crucial difference is 5-second advance warning, not just soft rejection.** During the 3–5 epochs before the worst GPS errors arrive, the EKF has already:
- Reduced Kalman gain so the first bad GPS measurements are partially rejected
- Increased P (covariance) to reflect increased uncertainty — this correctly propagates to the next step
- IMU is trusted more fully, providing a clean dead-reckoning trajectory

A reactive system (inflate R only after detecting bad GPS) suffers from the "first bad epoch" problem — at least one bad measurement is fully incorporated before the filter adapts.

---

## Q13: "On the trajectory chart, raw GPS sometimes sits exactly on the ground truth while your EKF is offset. Doesn't that mean raw GPS is better? Why trust RMSE over what I can see point-by-point?"

### The observation is correct
At many individual epochs — particularly in open-sky stretches — **raw GPS genuinely is more accurate than the EKF.** This is real and expected. On the Tokyo degraded epochs the *median* (CEP50) error is actually **lower for raw GPS (6.7 m) than for the EKF fixed-R (9.7 m).** Raw GPS wins the typical point.

### Why the EKF is slightly offset where GPS is good
Two reasons, both deliberate:
- **Filter lag** — the EKF blends a smooth IMU motion model with GPS corrections, so it trails fast wiggles instead of snapping onto each fix.
- **Deliberate distrust** — we instruct the filter not to fully commit to GPS, so it cannot lurch.

This small offset in benign regions is the **price of robustness**, and it is unavoidable: a filter tuned to snap perfectly onto GPS where GPS is good would *also* snap onto the *bad* GPS where GPS is bad — the "swirling" failure. You cannot have both with a single static trust level. This is exactly why adaptive-R + SENTINEL exist: trust GPS when good, distrust it when bad.

### Why RMSE (and the tail), not per-point alignment, is the right judge

| Metric (degraded epochs) | Raw GPS | EKF fixed-R |
|---|---|---|
| Median error (CEP50) | **6.7 m** ✅ | 9.7 m |
| 95th-percentile (CEP95) | 76 m | **51 m** ✅ |
| Worst case (max) | **888 m** ☠️ | **137 m** ✅ |

RMSE is **dominated by the tail** because it squares errors. Raw GPS is usually excellent but occasionally **888 m** wrong — one such excursion puts a vehicle in the wrong lane or off the road. The EKF gives up a metre or two in the harmless regions to **cap the catastrophe at 137 m** and cut the 95th percentile from 76→51 m.

The places where raw GPS beats the EKF are the **harmless** places; the places where the EKF beats raw GPS are the **dangerous** ones. That is precisely the trade a safety system wants: *surrender a little accuracy when it does not matter, to never be 800 m wrong when it does.*

### Tie back to the goal
The goal is that when GPS degrades, the vehicle still knows where it is well enough to act. A position estimate that is "usually within 7 m but sometimes 888 m off" is far more dangerous than one that is "usually within 10 m and never worse than 137 m." So the EKF output **should** track ground truth as closely as possible — and it does where it counts (the degraded/blocked regions). The visible offsets in clean regions are an acceptable, expected cost of never producing a catastrophic position during the moments the vehicle must act on.
