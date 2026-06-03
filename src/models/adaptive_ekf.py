"""
adaptive_ekf.py — Prediction-informed Adaptive Extended Kalman Filter (Paper 2 core).

The SENTINEL-GNSS predictor outputs P(DEGRADED) at t+5/15/30 s. This module shows the
*navigation payoff*: when the predictor warns of impending degradation, the filter
pre-emptively distrusts the GNSS position fix (inflates measurement noise R) and leans on the
constant-velocity motion model — i.e. proactive dead-reckoning. We compare three strategies
on position RMSE:

  (a) GNSS-only            — raw fixes, no filtering
  (b) Fixed-R EKF          — standard filter, constant trust in GNSS
  (c) Adaptive EKF (ours)  — R inflated as a function of predicted P(DEGRADED)

State: [x, y, vx, vy] (2-D constant-velocity). Measurement: GNSS position [x, y].

Usage
-----
  python -m src.models.adaptive_ekf --demo        # synthetic blockage demo + self-test
  # or import and call run_ekf_experiment(...) with real aligned arrays.

NOTE ON SCOPE
-------------
The `--demo` runs a *controlled simulation* (a trajectory with a simulated GNSS-blockage
segment) and proves the adaptive mechanism reduces RMSE. Real-data RMSE requires a per-epoch
aligned (gnss_xy, reference_xy, p_degraded) sequence; `run_ekf_experiment` accepts exactly
that, so the real-data case study plugs in once a reference trajectory is available.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


class AdaptiveEKF:
    """2-D constant-velocity EKF with prediction-informed adaptive measurement noise."""

    def __init__(self, dt=1.0, q=0.5, r_base=3.0, r_degraded=100.0, p_threshold=0.5):
        self.dt = dt
        self.q = q                      # process-noise scale (motion-model uncertainty)
        self.r_base = r_base            # GNSS measurement std (m) when signal is CLEAN
        self.r_degraded = r_degraded    # GNSS measurement std (m) when DEGRADED
        self.p_threshold = p_threshold
        # State transition (constant velocity)
        self.F = np.array([[1, 0, dt, 0],
                           [0, 1, 0, dt],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]], dtype=float)
        # Measurement model: observe position only
        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]], dtype=float)
        g = (dt ** 4) / 4.0
        h = (dt ** 3) / 2.0
        i = dt ** 2
        self.Q = self.q * np.array([[g, 0, h, 0],
                                    [0, g, 0, h],
                                    [h, 0, i, 0],
                                    [0, h, 0, i]], dtype=float)

    def _R(self, p_degraded, adaptive):
        """Measurement covariance. If adaptive, interpolate base→degraded by P(DEGRADED)."""
        if adaptive:
            # smoothly raise the GNSS noise as predicted degradation rises
            std = self.r_base + (self.r_degraded - self.r_base) * float(np.clip(p_degraded, 0, 1))
        else:
            std = self.r_base
        return np.eye(2) * (std ** 2)

    def run(self, gnss_xy, p_degraded=None, adaptive=False):
        """Filter a sequence of GNSS positions. Returns filtered (N,2) positions."""
        n = len(gnss_xy)
        if p_degraded is None:
            p_degraded = np.zeros(n)
        x = np.array([gnss_xy[0, 0], gnss_xy[0, 1], 0.0, 0.0])
        P = np.eye(4) * 10.0
        out = np.zeros((n, 2))
        out[0] = x[:2]
        for k in range(1, n):
            # Predict
            x = self.F @ x
            P = self.F @ P @ self.F.T + self.Q
            # Update with GNSS measurement
            R = self._R(p_degraded[k], adaptive)
            z = gnss_xy[k]
            y = z - self.H @ x
            S = self.H @ P @ self.H.T + R
            K = P @ self.H.T @ np.linalg.inv(S)
            x = x + K @ y
            P = (np.eye(4) - K @ self.H) @ P
            out[k] = x[:2]
        return out


def rmse(a, b):
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def run_ekf_experiment(gnss_xy, truth_xy, p_degraded, dt=1.0,
                       q=0.5, r_base=3.0, r_degraded=100.0, p_threshold=0.5):
    """Compare GNSS-only / fixed-R EKF / adaptive EKF on position RMSE.

    Parameters
    ----------
    gnss_xy   : (N,2) measured GNSS positions (metres, local ENU).
    truth_xy  : (N,2) reference/ground-truth positions (metres).
    p_degraded: (N,)  predicted P(DEGRADED) per epoch from SENTINEL-GNSS.

    Returns dict of RMSEs + the degraded-segment RMSEs.
    """
    gnss_xy = np.asarray(gnss_xy, float)
    truth_xy = np.asarray(truth_xy, float)
    p_degraded = np.asarray(p_degraded, float)

    ekf = AdaptiveEKF(dt, q, r_base, r_degraded, p_threshold)
    fixed = ekf.run(gnss_xy, p_degraded, adaptive=False)
    adapt = ekf.run(gnss_xy, p_degraded, adaptive=True)

    deg_mask = p_degraded >= p_threshold
    out = {
        "rmse_overall": {
            "gnss_only": round(rmse(gnss_xy, truth_xy), 3),
            "fixed_ekf": round(rmse(fixed, truth_xy), 3),
            "adaptive_ekf": round(rmse(adapt, truth_xy), 3),
        },
        "n_epochs": int(len(gnss_xy)),
        "n_degraded_epochs": int(deg_mask.sum()),
        "p_threshold": p_threshold,
    }
    if deg_mask.sum() > 0:
        out["rmse_degraded_segment"] = {
            "gnss_only": round(rmse(gnss_xy[deg_mask], truth_xy[deg_mask]), 3),
            "fixed_ekf": round(rmse(fixed[deg_mask], truth_xy[deg_mask]), 3),
            "adaptive_ekf": round(rmse(adapt[deg_mask], truth_xy[deg_mask]), 3),
        }
    g = out["rmse_overall"]["gnss_only"]
    a = out["rmse_overall"]["adaptive_ekf"]
    out["adaptive_improvement_pct_overall"] = round(100.0 * (g - a) / g, 1) if g else 0.0
    if "rmse_degraded_segment" in out:
        gd = out["rmse_degraded_segment"]["gnss_only"]
        ad = out["rmse_degraded_segment"]["adaptive_ekf"]
        out["adaptive_improvement_pct_degraded"] = round(100.0 * (gd - ad) / gd, 1) if gd else 0.0
    return out


def synthetic_demo(seed=42, save=True):
    """Controlled simulation: straight-then-turn trajectory with a GNSS-blockage segment.

    During the blockage, GNSS noise spikes (multipath). The predictor is assumed to flag the
    blockage (P(DEGRADED)→1) a few epochs early, so the adaptive filter is already distrusting
    GNSS when the spike hits.
    """
    rng = np.random.default_rng(seed)
    n = 300
    t = np.arange(n)
    # ground truth: constant velocity then a gentle curve
    truth = np.zeros((n, 2))
    truth[:, 0] = 2.0 * t
    truth[:, 1] = np.where(t < 150, 0.5 * t, 0.5 * 150 + 0.02 * (t - 150) ** 2)

    # degradation event between epochs 120 and 180 (e.g. under a bridge / canyon)
    deg = np.zeros(n)
    deg[120:180] = 1.0
    # predictor warns 5 s early (proactive): ramp up from epoch 115
    p_deg = np.zeros(n)
    p_deg[115:120] = np.linspace(0, 1, 5)
    p_deg[120:180] = 1.0
    p_deg[180:185] = np.linspace(1, 0, 5)

    # GNSS measurements: small noise normally, large biased noise during blockage
    gnss = truth.copy()
    base_noise = rng.normal(0, 3.0, (n, 2))
    spike_noise = rng.normal(0, 30.0, (n, 2)) + np.array([25.0, -25.0])  # multipath bias
    gnss += base_noise
    gnss[120:180] += spike_noise[120:180]

    res = run_ekf_experiment(gnss, truth, p_deg)
    res["_scenario"] = "synthetic blockage epochs 120-180; predictor warns from epoch 115"
    print(json.dumps(res, indent=2))
    print(f"\nOverall RMSE:  GNSS-only {res['rmse_overall']['gnss_only']} m  |  "
          f"Fixed-EKF {res['rmse_overall']['fixed_ekf']} m  |  "
          f"Adaptive-EKF {res['rmse_overall']['adaptive_ekf']} m")
    if "rmse_degraded_segment" in res:
        d = res["rmse_degraded_segment"]
        print(f"Blockage RMSE: GNSS-only {d['gnss_only']} m  |  Fixed-EKF {d['fixed_ekf']} m  |  "
              f"Adaptive-EKF {d['adaptive_ekf']} m")
        print(f"Adaptive EKF cuts blockage-segment error by "
              f"{res.get('adaptive_improvement_pct_degraded', 0)}% vs raw GNSS.")
    if save:
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / "ekf_demo.json"
        with open(out, "w") as fh:
            json.dump(res, fh, indent=2)
        print(f"\n[saved] {out}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prediction-informed adaptive EKF")
    ap.add_argument("--demo", action="store_true", help="run synthetic blockage demo + self-test")
    args = ap.parse_args()
    if args.demo:
        r = synthetic_demo()
        # self-test: adaptive must beat fixed and raw during the blockage
        d = r["rmse_degraded_segment"]
        assert d["adaptive_ekf"] < d["gnss_only"], "adaptive should beat raw GNSS in blockage"
        assert d["adaptive_ekf"] <= d["fixed_ekf"] + 1e-6, "adaptive should not be worse than fixed"
        print("\n[self-test PASSED] adaptive EKF reduces blockage-segment RMSE.")
    else:
        ap.print_help()
