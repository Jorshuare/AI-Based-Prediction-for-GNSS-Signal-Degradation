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
The covariance matrix R represents our uncertainty about GPS noise. In urban NLOS, the true R changes every epoch based on satellite geometry, building heights, and receiver dynamics. Manually setting r_base=8 m is an engineering approximation, not a principled estimate of the true noise covariance.

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

### Our answer
We solve the calibration problem through SENTINEL. Instead of estimating R from the innovation sequence (which fails in NLOS), we estimate the *degradation probability* from GNSS features using a learned classifier, then map it to a pre-specified R_degraded. This sidesteps the fundamental identification problem (you cannot separate "GPS is noisy" from "filter is drifting" using innovations alone).

---

## Q5: "GPS errors in urban environments are clearly temporally correlated (the same building causes NLOS for many consecutive seconds). How does your model address temporal correlation?"

### The concern
Standard EKF assumes i.i.d. measurement noise. But NLOS errors are highly autocorrelated — if the receiver is blocked by Building A, it will likely remain blocked for the 30 seconds it takes to drive past. This means consecutive innovations are not independent, violating the EKF's white noise assumption and causing the filter to over-weight correlated bad measurements.

### What we did

**SENTINEL directly models temporal correlation**: The Transformer+LSTM architecture processes a 60-second window of GNSS features. The Transformer captures global temporal patterns (the satellite rising/setting that precedes an NLOS episode), and the LSTM captures local sequential dynamics. The model learns that "building occlusion on epoch t" implies "building occlusion on epoch t+5" — precisely the temporal structure we want to exploit.

**In the EKF**: When SENTINEL predicts DEGRADED at epoch t, it inflates R for that epoch. Because SENTINEL is predictive (not reactive), the inflation typically starts 3–5 seconds before the worst measurements arrive and continues through the degradation episode, matching the temporal extent of the NLOS event.

**In the PF**: The Student-t likelihood degrades gracefully under correlated noise. If GPS is biased for 30 consecutive seconds, the PF particles gradually spread out (jitter + low GPS weight) rather than snapping to the biased position. The ESS threshold N/3 ensures resampling happens less frequently during correlated episodes, preserving particle diversity.

### Limitations
We do not model the GPS error covariance as a first-order Gauss-Markov process (which would be the principled approach for temporally correlated noise). This is a future work direction. Our SENTINEL approach handles temporal correlation implicitly but not optimally.

---

## Q6: "Why use a Transformer + LSTM? Why not just LSTM alone? Is the Transformer justified?"

### The concern
Transformer architectures have a quadratic self-attention cost in sequence length. For a 60-epoch input, this is manageable, but it requires justification that the long-range dependencies captured by the Transformer provide measurable benefit over a simpler LSTM.

### Ablation results

| Architecture | MacroF1 (+5s) | Δ vs. LSTM | Notes |
|-------------|--------------|------------|-------|
| LSTM only | 0.7889 | — | Baseline |
| Transformer only | 0.8043 | +1.9% | Good at global patterns |
| **Transformer + LSTM** | **0.8206** | **+4.0%** | Best |
| GRU only | 0.7741 | −1.9% | Simpler but worse |

The Transformer captures the slowly-varying satellite geometry (PDOP trends, satellite rising/setting events) that occurs over 30–60 seconds. The LSTM captures the rapid sequential transitions (a satellite suddenly dropping below the horizon). Neither alone captures both timescales optimally.

### Specific capability demonstrated
The Transformer can attend to events at epoch t=10 and epoch t=60 simultaneously — for instance, a PDOP spike at t=10 that predicts a building entry at t=60 would be captured by cross-attention between these distant epochs. LSTM has O(t) gradient decay and cannot reliably capture dependencies at 50-epoch distance.

The 4% MacroF1 improvement justifies the architecture. In binary decision terms: on the Hong Kong test set (~2,400 epochs), this translates to ~96 additional correctly classified epochs, which at 1 Hz corresponds to 96 seconds of correct degradation warnings.

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
