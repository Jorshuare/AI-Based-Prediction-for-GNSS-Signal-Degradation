# The Kalman Filter, Our EKF, and What Our Results Really Mean
### Written in plain language, with the maths underneath, and full justification

---

## PART 1 — Did we use synthetic or real data? (The honest answer)

**Short answer: fig21 and fig22 use a MIX — real car, real motion sensors, but *synthetic* GNSS.**

Here is exactly what is real and what we generated, for the UrbanNav Tokyo (Shinjuku) run:

| Ingredient | Source | Real or synthetic? |
|---|---|---|
| The route the car drove (ground truth) | UrbanNav `reference.csv` (SPAN-INS, cm-accurate) | **REAL** |
| IMU (accelerometer + gyroscope), 100 Hz | UrbanNav `imu.csv` | **REAL** |
| Wheel speed (odometry) | UrbanNav `imu.csv` | **REAL** |
| **GNSS position measurements** | **We generated them** = truth + fake multipath error inside fake blockage windows | **SYNTHETIC** |
| When the blockages happen | We placed them (~4% of the drive) | **SYNTHETIC** |
| P(DEGRADED) detector signal | We generated it (leads blockage by 5 s) | **SYNTHETIC** |

**So why is the GNSS synthetic?** UrbanNav Tokyo does **not** ship a ready-made GNSS position track.
It ships the *raw* satellite measurements (RINEX files: `rover_trimble.obs`). To turn those raw
measurements into an actual (lat, lon) position — the thing an EKF consumes — you must run a GNSS
**positioning engine** (called SPP/RTK, e.g. RTKLIB). We have **not** done that step yet. So to
test the filter today, we kept the real route + real IMU + real wheels, and *simulated* what bad
GNSS looks like (large errors during blockages).

**This is legitimate for testing the filter's logic, but it is NOT "real GNSS".** I was explicit
about this in `PHASE_2A_FINDINGS.md` ("controlled, semi-synthetic"), but you are right to pin it
down: **fig21/fig22 are semi-synthetic.**

**The path to 100% real (Part 7)** is to compute the real GNSS positions, and we actually have two
ways to do it — including a fast one using real phone/receiver NMEA files we already have on disk.

---

## PART 2 — How a Kalman Filter works (no maths first, then the maths)

### 2.1 The idea in one sentence
> A Kalman filter blends two imperfect guesses of where you are — one from **physics** (where you
> *should* be, given your last position and motion) and one from a **sensor** (GNSS) — weighting
> each by how much you trust it, to get an estimate better than either alone.

### 2.2 The kitchen analogy
You are blindfolded in your kitchen, taking steps.
- **Prediction:** "I was at the sink, I took one step toward the fridge, so I should be ~0.7 m
  closer to the fridge." (You trust your legs, but error builds up the longer you walk blind.)
- **Measurement:** You reach out and touch *something* — maybe the counter. GNSS is like this
  touch: it gives an absolute fix, but it can be wrong (you might be touching the wrong thing in a
  crowded kitchen = multipath in a city).
- **Update:** You combine "where my legs say I am" with "what my hand touched", trusting each by
  how reliable it is right now. If your hand-touch is confident, lean on it; if it feels sketchy,
  trust your legs more.

That trust dial — *how much do I believe the GNSS right now* — is the single most important knob,
and it is exactly the knob our research touches.

### 2.3 The two-step cycle (every 0.1 s)
```
   ┌─────────────┐        ┌─────────────┐
   │  PREDICT    │  --->   │   UPDATE    │  --->  repeat
   │ (physics)   │        │  (GNSS fix) │
   └─────────────┘        └─────────────┘
```
- **PREDICT:** move the estimate forward using the motion model (IMU tells us acceleration and
  turn rate). Uncertainty **grows** (blind walking).
- **UPDATE:** pull the estimate toward the GNSS measurement. Uncertainty **shrinks**.

### 2.4 The maths (this is the whole filter — five lines)

State vector `x` = what we estimate (position, velocity, heading…). Covariance `P` = our
uncertainty about `x` (a big P = "I'm not sure").

**Predict:**
```
x⁻ = f(x)                 # move state forward with the motion model
P⁻ = F P Fᵀ + Q           # grow uncertainty; F = Jacobian of f; Q = process noise
```

**Update (when a GNSS fix z arrives):**
```
y = z − H x⁻              # innovation: how far the fix is from our prediction
S = H P⁻ Hᵀ + R           # innovation covariance; R = MEASUREMENT NOISE (the trust knob)
K = P⁻ Hᵀ S⁻¹             # Kalman gain: how much to move toward the fix (0..1-ish)
x = x⁻ + K y              # corrected state
P = (I − K H) P⁻          # shrink uncertainty
```

**The one line that matters most:** `K = P⁻ Hᵀ / (H P⁻ Hᵀ + R)`.
- If **R is small** (we trust GNSS): K is large → we jump to the GNSS fix.
- If **R is large** (we distrust GNSS): K is ~0 → we ignore GNSS and coast on physics.

> **"R" is the trust dial.** Everything our project does to the filter is about setting R
> intelligently — and about giving the "physics" half better information so that coasting works.

---

## PART 3 — Our 9-state EKF formulation

A plain Kalman filter assumes straight-line (linear) motion. A car turns, so the motion model is
**non-linear** → we use the **Extended** Kalman Filter (EKF), which linearises the motion model
each step (that's the Jacobian `F`).

**Our 9-state vector** (what we track):
```
x = [ x, y,        position east/north (m)
      vx, vy,      velocity (m/s)
      ψ,           heading / which way the car points (rad)
      b,           GNSS clock bias (m)
      ba_x, ba_y ] accelerometer biases (m/s²)
```
Why these? Position is the answer we want; velocity + heading let us *coast* when GNSS drops; the
biases let the filter learn and subtract the IMU's systematic errors (cheap sensors drift).

**Motion model (predict):** rotate the IMU's body-frame acceleration into the world frame using
heading ψ, integrate to update velocity and position; advance heading with the gyro's turn rate.

**Measurement model (update):** GNSS observes position only → `H` picks out (x, y). `R` is the
GNSS trust dial.

---

## PART 4 — The changes WE made to the standard filter (our contribution)

### Change 1 — Prediction-driven **adaptive R** (the original idea)
Standard EKF uses a fixed R. We make R depend on our SENTINEL model's prediction:
```
R(t) = r_base + (r_degraded − r_base) · P(DEGRADED at t)
```
- Signal predicted clean → R small → trust GNSS.
- Signal predicted degraded → R large → distrust GNSS, coast on physics.
- Because the model predicts **5 s ahead**, R rises *before* the blockage hits (pre-emptive).

**Justification:** this is the textbook "quality-based adaptive Kalman filter" (Groves 2013;
Petovello 2015) — we just drive the quality signal with a learned predictor instead of raw
satellite geometry. We cap `r_degraded = 30 m` (not infinity) because the literature warns that
over-inflating R makes the filter diverge.

### Change 2 — **Aiding** the physics half: wheel-odometry + NHC + ZUPT (the decisive upgrade)
Coasting on a cheap IMU alone drifts fast. We added three GNSS-independent helpers that run **every
step**, so the "physics" estimate stays good even with GNSS switched off:
- **Wheel odometry:** the wheel-speed sensor tells us how fast we're actually going (real data,
  matches truth to <0.5 %).
- **NHC (non-holonomic constraint):** a car cannot slide sideways → we tell the filter "lateral
  velocity ≈ 0". This kills a whole direction of drift for free.
- **ZUPT (zero-velocity update):** when the wheels say we're stopped (35 % of this Shinjuku drive —
  traffic!), we pin velocity to exactly zero, so the estimate can't wander while parked.

**Justification:** these are the standard tools for "GNSS-denied" navigation in the literature
(Groves Ch. 6). Without them, distrusting GNSS is useless because the fallback is garbage; with
them, the fallback is trustworthy.

### Two bugs we had to fix to make any of this work (worth knowing)
1. **Initialisation:** we were starting velocity at 0 and heading at 0°, but the car was moving at
   ~10 m/s heading 258°. Coasting from a wrong heading diverges instantly (this caused the famous
   −366 %). Fixed by seeding velocity/heading from the first clean GNSS step.
2. **Gyro sign/frame:** the IMU's turn-rate is measured clockwise-from-North; our heading is
   math-style counter-clockwise-from-East, so heading-rate = −gyro. We verified the relationship
   on the real data (correlation 0.9997) and flipped the sign. Before the fix, the odometry pushed
   the car in the wrong direction.

---

## PART 5 — Every metric, explained

| Metric | What it literally is | Why we use it / how to read it |
|---|---|---|
| **RMSE (m)** | Root-Mean-Square Error: typical distance between our estimate and the true position, in metres | The headline accuracy. **Lower is better.** 5 m means "typically 5 m off." |
| **Overall RMSE** | RMSE across the *whole* drive | Everyday accuracy (mostly clean signal). |
| **Blocked-segment RMSE** | RMSE computed **only during the blockage windows** | The safety-critical number — accuracy exactly when GNSS is failing. This is what we care about most. |
| **Gain / improvement %** | `(raw − filtered) / raw × 100` | How much the filter cut the error vs raw GNSS. **+82 %** = error cut to less than a fifth. |
| **Crossover (severity sweep)** | The multipath-bias level where adaptive-R starts beating fixed-R | Tells us *when* a technique is worth using. |
| **r_base / r_degraded** | GNSS noise std assumed when clean / degraded (m) | The two ends of the trust dial. |
| **P(DEGRADED)** | The model's predicted probability the signal is bad | Drives the adaptive trust dial. |

For the prediction model (separate from the filter) you'll also see Macro-F1, MCC, ECE — those
grade the *classifier*, not the filter, and are explained in `ARCHITECTURE_COMPLETE_EXPLANATION.md`.

---

## PART 6 — So... does our adaptive EKF work best? (The honest verdict, with numbers)

Here are the actual blocked-segment results (semi-synthetic Tokyo run):

| Method | Blocked-segment RMSE | vs raw |
|---|---|---|
| Raw GNSS | 36.3 m | — |
| Constant-velocity KF | 13.4 m | +63 % |
| 9-state EKF (no aiding), fixed-R | 12.1 m | +67 % |
| 9-state EKF (no aiding), adaptive-R | 14.4 m | +60 % |
| **Aided EKF (odom+NHC+ZUPT), fixed-R — BEST** | **6.4 m** | **+82 %** |
| Aided EKF, adaptive-R | 10.7 m | +70 % |

**What this tells us, in plain terms:**

1. **The biggest win is the aiding, not the adaptive trust dial.** Adding wheel-odometry + NHC +
   ZUPT cut the blockage error from 36 m to **6.4 m**. That is the real, robust, defensible result.

2. **Adaptive-R (the original idea) does NOT win once the filter is well-aided.** Why? When we
   crank R up during a blockage, we throw GNSS away entirely. But GNSS was the only thing telling
   us our **heading**. Odometry gives speed and NHC stops sideways drift, but nothing else pins
   heading — so heading slowly rotates and the car's coasted path curves away from the truth.
   Keeping a *little* GNSS trust (fixed-R) preserves heading and wins. We proved this with the
   severity sweep: even at 40–60 m multipath, fixed-R still beat adaptive-R.

3. **But adaptive-R IS the right tool for a *weak* system.** On a phone-grade device with **no**
   wheel odometry (just GNSS + a constant-velocity model), the severity sweep showed adaptive-R
   wins by **+25–38 %** once multipath exceeds ~20 m. There's no good fallback there, so switching
   off bad GNSS genuinely helps.

**The honest, defensible story (and it's a strong one):**
> Our SENTINEL predictor's value for fusion is **regime selection / integrity**, not a blanket
> "distrust GNSS" command. On a well-equipped car: keep using GNSS for heading and use P(DEGRADED)
> to raise an integrity flag / hand off to other sensors. On a cheap GNSS-only device: use
> P(DEGRADED) to actively down-weight GNSS in severe multipath. **The prediction tells you which
> world you're in** — that is the contribution, and the data backs it precisely.

This is *more* credible to reviewers than "our knob always wins," because it shows exactly when and
why each technique helps — and the engineering headline (**aided EKF, +82 %**) is excellent.

> One nuance you'll notice: the aided filter's *overall* RMSE (8.5 m) is a touch worse than the
> plain EKF's (5.6 m), while its *blocked* RMSE is far better (6.4 vs 12.1 m). That's because
> odometry/heading noise competes slightly with already-good GNSS in clean times, but rescues us
> during blockages. For a safety system, winning during the blockage is the right trade.

---

## PART 7 — How to make it 100% REAL (and we can do it)

We have two routes to replace the synthetic GNSS with real receiver positions:

**Route A (fast, uses files we already have):** UrbanNav's **Hong Kong deep-urban** drives ship
real receiver **NMEA** files (e.g. `UrbanNav-HK-Deep-Urban-1.ublox.f9p.nmea`) — these are an actual
GNSS chip's computed positions in a real skyscraper canyon, with **real multipath and real
outages**, plus SPAN-CPT ground truth. We parse the NMEA (we already have an NMEA parser in
`inference.py`), align to truth + IMU, and rerun the exact same filters. The numbers then reflect
real GNSS errors.

**Route B (gold standard, Tokyo):** run a GNSS positioning engine (RTKLIB / `rtklib-py`) on the
Tokyo `rover_trimble.obs` RINEX to compute the real position track, then rerun. More setup, but it
keeps the same Tokyo trajectory.

Either way, **none of the filter code changes** — only the GNSS source. Given your network, Route A
is the quickest path to a defensible "real GNSS" result.

> **Recommendation:** do Route A next. It turns fig21/fig22 from "semi-synthetic" into "real
> receiver in a real Hong Kong canyon," which is exactly the credibility you want for the paper.
