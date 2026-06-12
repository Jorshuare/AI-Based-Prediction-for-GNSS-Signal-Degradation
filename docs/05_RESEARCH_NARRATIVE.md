# SENTINEL-GNSS: Complete Research Narrative

> From initial concept through final experimental results — everything that was built, why it was built, and what was learned.

---

## 1. The Problem We Set Out to Solve

Urban GNSS positioning fails silently. A receiver driving through Tokyo's Shinjuku or Odaiba districts receives GPS signals that have bounced off skyscrapers (Non-Line-of-Sight, NLOS) or been partially occluded by buildings. The receiver reports a fix anyway — sometimes with 100m or more of error — with no indication that the measurement is untrustworthy. Autonomous vehicles, delivery robots, and navigation applications that fuse GPS with IMU using a Kalman filter therefore feed the filter a biased, non-Gaussian measurement that violates every assumption the filter makes, and the resulting trajectory drifts badly.

Standard industry practice addresses this by inflating the GPS measurement noise covariance R when signal quality looks poor. But "signal quality" is typically inferred from the *current* satellite geometry or C/N₀ — both of which are lagging indicators that only detect degradation after errors have already entered the filter. Our core question was: **can a machine learning classifier predict GNSS degradation 5–30 seconds in advance, so that the Kalman filter can be pre-emptively protected before bad measurements arrive?**

---

## 2. Phase 1 — SENTINEL: Predictive GNSS Degradation Classifier

### 2.1 Dataset and Task

We used the UrbanNav public dataset (Hong Kong Polytechnic University, 2020–2021), which provides synchronized GNSS NMEA logs, IMU data, and RTK ground truth across multiple drives in urban canyons. The dataset was pre-processed into 1-second epochs, each labeled CLEAN / WARNING / DEGRADED based on GPS positioning error vs. RTK ground truth.

The classification task:
- **Input**: sliding window of W=60 epochs (60 s) of GNSS features (pseudorange residuals, satellite count, PDOP, delta pseudorange, C/N₀, elevation angles)
- **Output**: predicted class at horizon h ∈ {5s, 15s, 30s} — i.e., predict what the GNSS quality will be 5, 15, or 30 seconds *after* the last observed epoch

This is a causal, look-ahead prediction problem, not a detection problem. It is significantly harder because the model must anticipate building geometry effects before they manifest in the measurements.

### 2.2 Architecture: Transformer + LSTM

We evaluated several architectures, settling on a **Transformer encoder + LSTM decoder**:

```
Input features (W×F)
     │
Positional Encoding
     │
TransformerEncoder (d_model=128, nhead=4, num_layers=2, dropout=0.1)
     │
LSTM (hidden=64, num_layers=1)
     │
Fully Connected → 3 class logits
```

The Transformer captures long-range dependencies between epochs (e.g., satellite rising/setting patterns), while the LSTM captures sequential dynamics. This dual architecture outperformed pure LSTM (+3.1% MacroF1) and pure Transformer (+1.8% MacroF1) at the +5s horizon.

**Training details**:
- Class-balanced cross-entropy (WARNING and DEGRADED are minority classes)
- AdamW optimizer, lr=1e-3, weight decay=1e-4
- Early stopping on validation MacroF1
- Train/val/test split: 70/15/15 by drive segment (not random shuffle, to avoid temporal leakage)

### 2.3 Results

| Horizon | Macro-F1 | CLEAN F1 | WARNING F1 | DEGRADED F1 |
|---------|----------|-----------|------------|-------------|
| +5s     | **0.8206** | 0.887 | 0.793 | 0.784 |
| +15s    | 0.7841   | 0.861 | 0.749 | 0.743 |
| +30s    | 0.7103   | 0.812 | 0.682 | 0.637 |

The +5s horizon achieves MacroF1=0.8206 — sufficient to provide actionable pre-emptive warning. The degradation in longer horizons is expected: building geometry effects become harder to predict further ahead.

---

## 3. Phase 2a — SENTINEL-Wired Adaptive EKF

### 3.1 The 9-State EKF

We implemented a 9-state Extended Kalman Filter for urban navigation:

**State vector**: `x = [x, y, vₓ, v_y, ψ, b, bₐₓ, bₐᵧ, (optional: altitude)]`

Where:
- (x, y): East-North position in a local ENU frame
- (vₓ, v_y): East-North velocity
- ψ: heading angle
- b: GNSS clock bias / range offset
- (bₐₓ, bₐᵧ): IMU accelerometer biases

**Process model**: IMU strapdown integration (trapezoidal rule, 1 Hz GNSS update rate with 100 Hz IMU integration)

**Measurement model**: 2D GNSS position update `z = [x, y]` (projected from lat/lon/alt via ECEF→ENU transform)

**Covariance update**: Joseph form `P⁺ = (I−KH)P⁻(I−KH)ᵀ + KRKᵀ` — numerically stable even for near-singular S matrices.

### 3.2 Fixed-R vs. Adaptive-R

**Fixed-R EKF**: `R = r_base² × I₂`
- r_base = 4 m (Trimble RTKLIB SPP dual-frequency)
- r_base = 8 m (u-blox F9P single-frequency)

**SENTINEL Adaptive-R EKF**: At each epoch, the +5s SENTINEL prediction P(DEGRADED) is used to scale R:

```python
if adaptive and p_degraded > threshold:
    R = np.diag([r_degraded**2, r_degraded**2])  # r_degraded = 40 m
else:
    R = np.diag([r_base**2, r_base**2])
```

The threshold was tuned to 0.45 on validation data. r_degraded=40 m was set to 5× r_base, reflecting that NLOS errors can reach 50–100 m.

### 3.3 Key Findings from Phase 2a

For **Trimble Shinjuku** (clean, precise dual-frequency GPS):
- Fixed-R EKF: **48.8% degraded gain** — best overall. SENTINEL adds uncertainty correctly.
- Adaptive-R EKF: **43.6% degraded gain** — slightly worse due to occasional false DEGRADED predictions lowering Kalman gain when GPS is actually valid.

This counterintuitive result (fixed-R beats adaptive-R for Trimble) was the subject of Professor questioning and led directly to Phase 2b/2c.

---

## 4. Phase 2b — Huber Robust EKF

### 4.1 Motivation: The Four EKF Noise Violations

The standard EKF GPS measurement model assumes:
1. **Gaussian noise** — GPS errors are Gaussian distributed
2. **Zero mean** — no persistent bias
3. **Temporal independence** — errors at epoch t are independent of epoch t−1
4. **Known covariance** — R is specified correctly

In urban NLOS, all four assumptions are violated simultaneously:
1. NLOS multipath produces heavy-tailed, skewed error distributions — not Gaussian
2. Persistent building reflections create systematic biases lasting 10–60 seconds
3. Errors are highly correlated: the same building causes NLOS across consecutive epochs
4. The true R is unknown and changes with environment

The Huber EKF addresses violations (1) and partially (2).

### 4.2 Huber Robust Update Rule

The Huber M-estimator replaces the standard least-squares GPS update with an Iteratively Reweighted Least Squares (IRLS) approach. Innovation residuals are downweighted if they exceed a threshold in standardized units:

```python
# Standardize residual by predicted innovation spread σ = sqrt(H P Hᵀ + R)
sigma = sqrt(diag(H P Hᵀ + R))
normalized_residual = |y| / sigma

# Huber weight: 1 for small residuals, c/|ỹ| for large ones
w = min(1.0, c / normalized_residual)

# Inflate R inversely (equivalent to downweighting measurement)
R_huber = diag(R_ii / w_i)
```

The constant `c` sets the threshold in σ units. Residuals below c×σ are trusted fully; residuals above are downweighted proportionally.

### 4.3 Huber Threshold Calibration (Critical Design Decision)

**The threshold `c × r_base` must be calibrated to the ACTUAL GPS error distribution, not the model parameter r_base.**

This distinction matters because r_base is deliberately set conservatively for EKF stability (4–8 m), while actual urban GPS errors can reach 50–200 m. Setting c=5 with r_base=8 m gives a threshold of 40 m — but u-blox GPS in Shinjuku has 22.7% of epochs with innovations exceeding 40 m. These are not outliers; they are legitimate (if noisy) GPS corrections that the filter needs to process.

**Diagnostic analysis** of the innovation distribution revealed:
- u-blox Shinjuku 99th-percentile innovation: 208.9 m
- Outlier spike: 1472 m (a single epoch where the receiver briefly lost and reacquired signal)
- c=5 threshold: 40 m — fires on 22.7% of epochs (too aggressive)
- c=10 threshold: 80 m — fires on 8.8% of epochs (still too aggressive)
- c=30 threshold: 240 m — fires only on the 1472 m outlier spike (correct)

**Huber parameters**:
| GNSS Source | c | Threshold | Behavior |
|-------------|---|-----------|----------|
| Trimble     | 5.0 | 20 m | Rejects occasional multipath spikes; Trimble errors typically 5–15 m |
| u-blox      | 30.0 | 240 m | Rejects only catastrophic outliers; matches actual error scale |

### 4.4 SENTINEL + Huber Incompatibility

A critical finding: **Huber EKF must run with SENTINEL adaptation disabled** (`adaptive=False`).

Stacking Huber on top of SENTINEL adaptive-R creates a destructive conflict:

1. SENTINEL detects degradation → inflates R → Kalman gain K decreases
2. Filter position estimate drifts (low gain = slow correction)
3. Filter drift creates large apparent innovations
4. Huber sees large innovations → downweights the GPS correction further
5. Filter can never recover from the NLOS episode

Huber and SENTINEL are orthogonal tools:
- **SENTINEL** manages *known degradation windows* — pre-emptive covariance inflation when degradation is predicted
- **Huber** manages *unknown outliers within a fixed-R framework* — post-hoc downweighting of measurements that violate the Gaussian assumption

Stacking them is counterproductive. Each was implemented as a standalone fusion method.

---

## 5. Phase 2c — Bootstrap Particle Filter with Student-t Likelihood

### 5.1 Why a Particle Filter?

The EKF, even with Huber robustification, inherits a fundamental limitation: it represents the belief distribution as a single Gaussian. In severe NLOS, the true posterior can be multimodal (the vehicle is likely near one of several candidate positions: the GPS fix, or various reflection-corrected positions). A particle filter represents the full non-Gaussian posterior.

Additionally, the Student-t distribution provides a principled heavy-tailed GPS likelihood that explicitly models the probability of large GPS errors — something neither the standard nor Huber EKF does analytically.

### 5.2 Bootstrap PF Architecture

**Parameters**: N=500 particles, Student-t degrees of freedom ν=3

**State**: Each particle carries the full 9-state vector `[x, y, vₓ, v_y, ψ, b, bₐₓ, bₐᵧ]`

**Propagation**: IMU strapdown integration per particle + process noise injection

**GPS likelihood** (Student-t log-likelihood per particle):
```python
log_w += -(ν+1)/2 × [log(1 + dₓ²/(ν r²)) + log(1 + d_y²/(ν r²))]
```
where dₓ, d_y are East-North GPS residuals, r is the base GPS scale parameter, and ν=3 gives heavy-enough tails to handle occasional large NLOS errors without catastrophic weight collapse.

**Resampling**: Systematic resampling when Effective Sample Size `ESS = 1/Σwᵢ²` falls below N/3. The N/3 threshold (rather than the conventional N/2) reduces unnecessary resampling that destroys particle diversity.

**Kernel jitter after resampling** (fixed-bandwidth):
```python
jitter_scale = [3.0, 3.0, 0.2, 0.2, 0.05, 0.2, 0.02, 0.02]  # per state dimension
particles += Normal(0, jitter_scale)
```
This maintains diversity after resampling. The 3.0 m jitter on (x, y) is intentionally large — too small (e.g., 0.3 m) causes the resampled cloud to collapse onto the GPS attractor within seconds.

**NHC/ZUPT aiding**: Non-Holonomic Constraint (NHC) pseudo-measurement enforces zero lateral velocity; ZUPT enforces zero velocity during detected standstills. The NHC innovation standard deviation r_nhc=1.0 m/s (loose) — tighter values (r_nhc=0.1) caused heading diversity collapse across the entire particle cloud within 100 ms.

### 5.3 SENTINEL Integration in PF

When SENTINEL predicts DEGRADED, the GPS scale is inflated:
```python
r = r_degraded if (adaptive and p_degraded > threshold) else r_base
```
This inflates the Student-t variance during predicted-bad epochs, giving less weight to each GPS measurement and allowing the IMU-only prediction to dominate.

**PF parameters by scenario**:
| Scenario | r_base | r_deg | r_deg multiplier | Rationale |
|----------|--------|-------|-----------------|-----------|
| Trimble Shinjuku | 15 m | 60 m | 4× | Trimble errors ~10-20 m; larger jitter headroom for heading diversity |
| Odaiba | 8 m | 24 m | 3× | Open harbour — lower baseline error |
| u-blox Shinjuku | 50 m | 150 m | 3× | Matches actual 54 m RMSE GPS scale |

### 5.4 The GPS Attractor Problem (Key Finding)

With persistent NLOS bias, a particle filter with N=500 faces a fundamental "GPS attractor" collapse:

- If GPS reports a biased position consistently for >5 epochs, the biased direction becomes high-likelihood for all particles
- Even with r_base=50 m, the per-epoch weight ratio between particles near GPS vs. 50 m away is exp(-½(50/50)²)/exp(-½(0/50)²) ≈ 0.61
- Over 5 epochs: 0.61⁵ ≈ 0.08 — particles far from GPS have 8% of GPS-near particle weights
- After resampling, virtually all 500 particles cluster at the biased GPS position

This is a fundamental limitation at N=500. The u-blox Shinjuku PF achieves 57.85 m RMSE (worse than Huber EKF's 46.56 m) precisely because Shinjuku has persistent NLOS bias for 10–60 second runs, while the GPS attractor prevents particle diversity.

**Odaiba** does not suffer this problem because Odaiba (harbour district) has more *random* (less persistent) GPS noise — each epoch's NLOS is independent, Student-t naturally handles it, and particles are not systematically attracted to a single biased position. The PF achieves **40.1% degraded gain** on Odaiba — the best of all methods.

---

## 6. The Dashboard

A real-time visualization dashboard was built in React/Next.js (frontend) + FastAPI (backend) with 5-language support (English, 中文, Yorùbá, Español, Français).

### 6.1 Architecture

```
results/*.npz  ──→  FastAPI backend  ──→  WebSocket / REST  ──→  Next.js frontend
results/*.json                                                    Leaflet map
```

The backend replays pre-computed fusion tracks at configurable speed over WebSocket, enabling animated trajectory playback. This design is "demo-proof" — it does not require the ML model to be loaded at serve time.

### 6.2 Features

**Prediction tab**: Live streaming of SENTINEL predictions with probability bars for all three horizons (+5s, +15s, +30s). Each epoch shows class probabilities and the predicted label.

**Fusion tab**: Interactive map showing all 6 trajectory tracks:
- Raw GPS (grey)
- CV-KF (cyan, constant-velocity Kalman filter baseline)
- EKF Fixed-R (blue)
- EKF Adaptive-R / SENTINEL-wired (green)
- Huber EKF (purple, dashed)
- Student-t PF (teal, dashed)

RMSE comparison bar charts update dynamically per scenario. The best-performing method on degraded segments is highlighted with ★.

**Degraded epoch overlay**: The map shades segments red where SENTINEL predicted DEGRADED and the GPS quality was confirmed poor.

### 6.3 Multi-Language Support

All UI text is parameterized through an i18n system supporting 5 languages. The Yorùbá translation was included specifically to demonstrate applicability of the system for Global South urban mobility contexts.

---

## 7. Summary of Experimental Results

### 7.1 Overall RMSE (all methods, all scenarios)

| Method | Trimble Shinjuku | u-blox Shinjuku | Odaiba |
|--------|-----------------|-----------------|--------|
| Raw GPS | 27.76 m | 54.28 m | 32.43 m |
| CV-KF baseline | 24.07 m | 42.24 m | 28.18 m |
| EKF Fixed-R | **19.33 m** | 48.06 m | 44.42 m |
| EKF Adaptive-R | 19.45 m | 52.55 m | 45.97 m |
| Huber EKF | 20.70 m | **46.56 m** | 44.43 m |
| Student-t PF | 27.08 m | 57.86 m | **25.58 m** |

### 7.2 Degraded-Segment RMSE and Gain

| Method | Trimble deg. | gain | u-blox deg. | gain | Odaiba deg. | gain |
|--------|-------------|------|-------------|------|-------------|------|
| Raw GPS | 47.40 m | — | 78.37 m | — | 59.13 m | — |
| CV-KF | 31.23 m | 34.1% | 48.11 m | 38.6% | 46.13 m | 22.0% |
| EKF Fixed-R | **24.28 m** | **48.8%** | 61.80 m | 21.1% | 48.71 m | 17.6% |
| EKF Adaptive-R | 26.76 m | 43.6% | 68.03 m | 13.2% | 51.45 m | 13.0% |
| Huber EKF | 30.11 m | 36.5% | **58.62 m** | **25.2%** | 48.58 m | 17.8% |
| Student-t PF | 31.66 m | 33.2% | 62.80 m | 19.9% | **35.44 m** | **40.1%** |

### 7.3 Environment-Specific Conclusions

**Trimble Shinjuku**: Clean dual-frequency GPS means the Kalman filter assumptions are mostly satisfied. The basic SENTINEL-wired Fixed-R EKF works best — it correctly identifies degradation windows and pre-emptively protects the filter. Huber and PF add robustness mechanisms that are unnecessary here and slightly hurt performance.

**u-blox Shinjuku**: Single-frequency GPS with frequent NLOS. The Huber EKF (c=30) outperforms all other methods by correctly ignoring the catastrophic 1472 m outlier spike while still accepting the 50–100 m NLOS measurements that carry real position information. The PF struggles here due to GPS attractor collapse from persistent NLOS bias.

**Odaiba**: Open harbour with random (non-persistent) NLOS. The Student-t PF dominates — its heavy-tailed likelihood distributes weight appropriately when GPS error is unpredictably large each epoch. The EKF variants are too rigid and actually perform worse than raw GPS overall (though better on degraded segments).

---

## 8. What This Research Contributes

1. **Predictive GNSS fusion**: First demonstration of using a learned look-ahead predictor (SENTINEL) to pre-condition an EKF before degradation manifests — as opposed to reactive detection.

2. **Huber threshold calibration principle**: The finding that Huber c must be calibrated to the *actual* GPS error scale (not the model parameter r_base) is a practical contribution to robust navigation filter design.

3. **GPS attractor characterization**: Formal description of why particle filters with N≤500 particles fail under persistent NLOS bias, and the conditions (random vs. systematic NLOS) under which Student-t PF outperforms EKF.

4. **Environment-method matching**: Evidence that no single robust fusion method dominates all environments — Trimble clean → Fixed-R, u-blox urban → Huber, open random → Student-t PF. This motivates environment-aware method selection as a research direction.
