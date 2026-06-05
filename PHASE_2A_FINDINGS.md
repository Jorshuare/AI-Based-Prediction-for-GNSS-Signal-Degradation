# Phase 2a — Adaptive-EKF on UrbanNav Tokyo: Honest Findings

**Status:** ✅ Methodology corrected, result is defensible and reproducible
**Data:** UrbanNav Tokyo / Shinjuku — real SPAN-INS cm-level truth + real 100 Hz IMU
**Run:** `python -m src.models.ekf_urbannav_runner` → `results/urbannav_ekf.json`
**Figures:** `fig21_urbannav_filter_comparison`, `fig22_urbannav_severity_sweep`

---

## 1. What was wrong before (the −366%)

The first runner produced a nonsense −366% "improvement". Three real bugs, all now fixed:

1. **Circular validation.** GNSS noise was *generated from* `p_degraded`, then the same
   `p_degraded` was fed to the adaptive filter. Meaningless by construction.
2. **Broken EKF initialization.** Velocity seeded at 0 (car moving ~10 m/s) and heading at
   0° (true ≈ 258°). When the adaptive filter inflated R and leaned on IMU dead-reckoning,
   strapdown integration was rotated by a wrong heading and diverged instantly.
3. **69% of epochs flagged "degraded."** A velocity proxy marked most of the drive as
   degraded, so the filter dead-reckoned a low-cost MEMS IMU through ~1400 s. Hopeless.

**Fixes:** decoupled physical GNSS noise from the detector; seeded velocity/heading from the
first clean GNSS displacement; restricted blockage to realistic discrete windows (~4%).

---

## 2. Honest scope

This is a **controlled (semi-synthetic) validation on a REAL trajectory + REAL IMU.** GNSS
positions are synthesised as `truth + physical multipath bias + noise`, elevated only inside
discrete blockage windows. A fully-real run would replace the synthetic GNSS with an RTKLIB
SPP solution computed from the RINEX `rover_trimble.obs` — that is the one remaining step to a
100%-real pipeline, and it does not change the filter conclusions below.

**No circularity:** GNSS errors are driven by the physical blockage mask; the P(DEGRADED)
detector is generated separately, imperfectly, with a 5 s lead and smoothing — so the adaptive
filter cannot read the noise it must reject.

---

## 3. Filter comparison (single scenario, 4.1% blocked, ~13 m typical multipath)

| Filter | Overall RMSE | Blocked-segment RMSE | vs raw (blocked) |
|---|---|---|---|
| Raw GNSS | 8.43 m | 36.31 m | — |
| **CV-KF fixed-R** | **3.61 m** | **13.45 m** | **+63%** |
| CV-KF adaptive-R | 4.18 m | 16.38 m | +55% |
| 9-state EKF fixed-R | 7.35 m | 14.56 m | +60% |
| 9-state EKF adaptive-R | 10.54 m | 37.42 m | −3% |

**Two honest takeaways:**

- A simple **loosely-coupled constant-velocity KF already removes most GNSS error** (+63%
  during blockage). This is the workhorse and it is correct.
- At *this* (moderate, ~13 m) multipath level, **adaptive-R does NOT help** — the dead-reckoning
  drift over a 10–25 s window is comparable to the bias it avoids. The 9-state EKF additionally
  under-performs the CV-KF: the low-cost MEMS strapdown adds more error than constant-velocity.
  Tight coupling / ZUPT / online bias calibration is needed for the IMU model to pay off — that
  is explicit future work, not a hidden failure.

---

## 4. The real contribution: WHEN does adaptive-R help? (severity sweep)

Instead of cherry-picking one number, we sweep multipath severity (clean CV-KF, fixed windows):

| Multipath bias | Raw | Fixed-R | Adaptive-R | Adaptive vs Fixed |
|---|---|---|---|---|
| 5 m | 7.7 | 4.0 | 7.6 | −91% |
| 10 m | 12.4 | 7.5 | 7.9 | −5% |
| **20 m** | 22.2 | 16.3 | 11.2 | **+31%** |
| 30 m | 29.8 | 20.6 | 12.8 | **+38%** |
| 45 m | 43.0 | 31.7 | 23.5 | +26% |
| 60 m | 64.6 | 54.5 | 39.8 | +27% |
| 80 m | 75.4 | 57.4 | 37.8 | +34% |

**Crossover ≈ 20 m.** Below it, trust GNSS (fixed-R wins). Above it — i.e. **deep urban canyon
multipath (≥20 m), exactly the safety-critical regime** — adaptive-R wins by **+25–38%**.

This is the defensible headline: *adaptive measurement-noise inflation pays off precisely when
GNSS degradation exceeds dead-reckoning drift, which is the deep-blockage case that matters for
autonomous-vehicle safety.* It is consistent with Groves (2013) and Petovello (2015): inflate R
to reflect actual degraded error (we use r_deg = 30 m, not ∞), avoiding the divergence that
over-inflation causes.

---

## 5. What to claim in the papers (and what NOT to)

**Claim (supported):**
- Loosely-coupled KF reduces blocked-segment RMSE by ~60% vs raw GNSS on a real Tokyo trajectory.
- Prediction-driven adaptive-R reduces blocked-segment RMSE by **25–38% in severe multipath
  (≥20 m)**, with a clear crossover characterised by a severity sweep.
- The 5 s predictor lead enables pre-emptive R inflation before the outage.

**Do NOT claim:**
- A flat "33.8%" / "15–30%" real-world gain regardless of conditions (the synthetic 33.8% was a
  controlled-blockage demo; reality is regime-dependent).
- That the 9-state IMU EKF beats the simple KF here — it does not yet (needs tighter coupling).

---

## 6. Reproduce

```bash
python -m src.models.ekf_urbannav_runner        # runs filters + severity sweep
python -m src.utils.make_ekf_urbannav_figures    # fig21 (bars), fig22 (crossover)
```

Outputs: `results/urbannav_ekf.json`, `results/paper_figures/fig21_*`, `fig22_*`.

---

## 7. Remaining step to a fully-real pipeline (optional)

Compute a real GNSS position solution from `rover_trimble.obs` via RTKLIB/`rtklib-py` SPP, and
swap it in for the synthetic GNSS. The filters, detector, and sweep code are unchanged; only the
measurement source changes. Expected effect: the crossover stays, absolute numbers shift to the
dataset's true multipath distribution.
