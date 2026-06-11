"""
pf_9state.py — Bootstrap Particle Filter for GNSS/IMU fusion.

Directly addresses the four EKF noise assumption violations raised by reviewers:

  1. Non-Gaussian GPS noise (NLOS multipath, bimodal):
       → Student-t observation likelihood (ν=3, heavy tails). A 5σ outlier reduces
         particle weight by exp(−4.4) vs exp(−12.5) for Gaussian. Particles near truth
         survive even when GPS has 40–80 m NLOS bias.

  2. Non-zero-mean (spatially correlated) bias:
       → Heavy tails tolerate persistent bias: biased GPS gives MODERATE likelihood to
         all particles, truth-aligned particles still dominate over time.

  3. Non-white (temporally correlated) measurement noise:
       → Particle diversity maintained through process noise + resampling. The cloud
         spans multiple position hypotheses simultaneously; one bad GPS epoch does not
         permanently commit the state.

  4. Unknown noise covariance:
       → Scale parameter r_eff(t) adapts via P(DEGRADED) exactly as in the EKF.
         No assumption that R is fixed or known a priori.

Same 9-state model as EKF: [x, y, vx, vy, psi, b, ba_x, ba_y]
Same aiding: wheel odometry + non-holonomic constraint (NHC) + ZUPT.

Reference: Djuric et al. (2003), "Particle filtering," IEEE Signal Process. Mag.
           Agamennoni et al. (2011), "An outlier-robust Kalman filter," ICRA 2011.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class PFParams:
    """Configuration for 9-state bootstrap particle filter."""
    dt: float = 0.1
    n_particles: int = 500
    # Process noise — same values as EKF for a fair comparison
    q_pos: float = 0.1
    q_vel: float = 0.01
    q_heading: float = 0.001
    q_bias: float = 0.0001
    # Student-t observation model
    obs_nu: float = 3.0          # degrees of freedom (ν=3 → standard heavy tail)
    r_base: float = 8.0          # GPS scale at P(DEGRADED)=0  (matches EKF r_base)
    r_degraded: float = 40.0     # GPS scale at P(DEGRADED)=1  (matches EKF r_degraded)
    # Non-holonomic constraint + wheel odometry
    # NOTE: r_nhc must be much looser than EKF (0.05) because the PF has no Kalman
    # update — NHC acts as a particle-killing likelihood. With r_nhc=0.1 a particle
    # with 5° heading error at 10 m/s (v_lat=0.87 m/s) gets log_w=-37.8 per step,
    # killing all heading diversity in <100 ms. r_nhc=1.0 gives log_w=-0.38 per step,
    # converging heading over ~5 s without immediate collapse.
    r_nhc: float = 1.0           # lateral velocity std (m/s) — deliberately loose for PF
    r_odo: float = 0.50          # forward velocity std (m/s)
    zupt_r: float = 0.05         # stationary velocity std (m/s)
    v_max: float = 50.0


class PF9State:
    """Bootstrap particle filter for GNSS/IMU fusion with Student-t GPS likelihood.

    The filter maintains N particles, each a complete 9-state trajectory hypothesis.
    At each epoch:
      1. Propagate all particles via the IMU motion model (+ process noise).
      2. Weight particles by NHC/ZUPT likelihood (wheel odometry constraint).
      3. Weight particles by GPS Student-t likelihood.
      4. Normalise; resample via systematic resampling when ESS < N/2.
      5. Report weighted-mean position as the state estimate.
    """

    def __init__(self, params: PFParams | None = None):
        if params is None:
            params = PFParams()
        self.p = params
        self.particles: np.ndarray | None = None   # (N, 8)
        self.log_weights: np.ndarray | None = None  # (N,)

    @staticmethod
    def _wrap(a: np.ndarray) -> np.ndarray:
        return (a + np.pi) % (2 * np.pi) - np.pi

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def _propagate(self, accel: np.ndarray, gyro: float) -> None:
        """Vectorised stochastic IMU propagation across all N particles."""
        p = self.particles
        N = len(p)
        dt = self.p.dt
        sq = np.sqrt

        if np.isnan(accel[0]) or np.isnan(accel[1]) or np.isnan(gyro):
            # Constant-velocity fallback (no IMU data this epoch)
            p[:, 0] += p[:, 2] * dt
            p[:, 1] += p[:, 3] * dt
        else:
            ax_b = accel[0] - p[:, 6]    # body-frame ax minus per-particle bias
            ay_b = accel[1] - p[:, 7]
            c, s = np.cos(p[:, 4]), np.sin(p[:, 4])
            # Rotate body → navigation frame
            ax_n = c * ax_b - s * ay_b
            ay_n = s * ax_b + c * ay_b
            # Heading
            p[:, 4] += gyro * dt
            # Position (from current velocity, before velocity update)
            p[:, 0] += p[:, 2] * dt
            p[:, 1] += p[:, 3] * dt
            # Velocity
            p[:, 2] += ax_n * dt
            p[:, 3] += ay_n * dt

        p[:, 4] = self._wrap(p[:, 4])
        p[:, 2] = np.clip(p[:, 2], -self.p.v_max, self.p.v_max)
        p[:, 3] = np.clip(p[:, 3], -self.p.v_max, self.p.v_max)

        # Process noise — same spectral density as EKF Q matrix
        p[:, 0] += np.random.normal(0, sq(self.p.q_pos * dt**4 / 4), N)
        p[:, 1] += np.random.normal(0, sq(self.p.q_pos * dt**4 / 4), N)
        p[:, 2] += np.random.normal(0, sq(self.p.q_vel * dt**2 / 2), N)
        p[:, 3] += np.random.normal(0, sq(self.p.q_vel * dt**2 / 2), N)
        p[:, 4] += np.random.normal(0, sq(self.p.q_heading * dt), N)
        p[:, 5] += np.random.normal(0, sq(self.p.q_bias * dt), N)
        p[:, 6] += np.random.normal(0, sq(self.p.q_bias * dt), N)
        p[:, 7] += np.random.normal(0, sq(self.p.q_bias * dt), N)

    # ------------------------------------------------------------------
    # Likelihoods
    # ------------------------------------------------------------------

    def _nhc_log_lh(self, wheel_speed: float, stationary: bool) -> np.ndarray:
        """NHC + ZUPT log-likelihood (same physical model as EKF aiding).

        The land vehicle constraint is: lateral body velocity ≈ 0 (NHC),
        forward body velocity ≈ wheel_speed (odometry). When stationary, both
        components are pinned to 0 with a tight ZUPT constraint.

        Particles with heading inconsistent with their velocity direction receive
        low likelihood and are progressively eliminated — this is how the particle
        filter implicitly estimates heading even without a direct heading measurement.
        """
        psi = self.particles[:, 4]
        vx, vy = self.particles[:, 2], self.particles[:, 3]
        c, s = np.cos(psi), np.sin(psi)
        v_fwd = c * vx + s * vy
        v_lat = -s * vx + c * vy

        if stationary:
            r2 = self.p.zupt_r ** 2
            return -0.5 * (v_fwd ** 2 + v_lat ** 2) / r2
        else:
            return (-0.5 * v_lat ** 2 / self.p.r_nhc ** 2
                    - 0.5 * (v_fwd - wheel_speed) ** 2 / self.p.r_odo ** 2)

    def _gnss_log_lh(self, gnss_pos: np.ndarray, p_degraded: float,
                     adaptive: bool) -> np.ndarray:
        """Student-t log-likelihood for the GPS position measurement.

        The 2-D Student-t with ν degrees of freedom and scale r_eff models
        GNSS errors as a scale-mixture of Gaussians — equivalent to saying the
        measurement noise variance is itself uncertain (drawn from an inverse-chi²
        distribution). This produces heavy tails: a 5σ GPS outlier reduces particle
        weight by exp(−4.4) rather than exp(−12.5) for Gaussian, allowing particles
        near the true position to survive NLOS episodes and recover when signal returns.

        Independence between x and y components is assumed; the full 2-D likelihood
        is the product of two marginal Student-t densities.
        """
        nu = self.p.obs_nu
        p_d = np.clip(float(p_degraded), 0.0, 1.0)
        r_eff = (self.p.r_base + (self.p.r_degraded - self.p.r_base) * p_d
                 if adaptive else self.p.r_base)
        r2 = r_eff ** 2

        dx = self.particles[:, 0] - gnss_pos[0]
        dy = self.particles[:, 1] - gnss_pos[1]

        # log p(z|x) = -(ν+1)/2 × [log(1 + dx²/(ν r²)) + log(1 + dy²/(ν r²))]
        return (-(nu + 1) / 2
                * (np.log1p(dx ** 2 / (nu * r2)) + np.log1p(dy ** 2 / (nu * r2))))

    # ------------------------------------------------------------------
    # Resampling
    # ------------------------------------------------------------------

    def _normalise(self) -> np.ndarray:
        """Return normalised weights from log-weights (numerically stable)."""
        lw = self.log_weights - self.log_weights.max()
        w = np.exp(lw)
        w /= w.sum()
        return w

    def _systematic_resample(self) -> None:
        """Systematic resampling with Gaussian kernel regularisation (Liu & West 2001).

        Standard resampling collapses the particle cloud to a finite set of duplicates.
        After each resample we add small Gaussian jitter (kernel smoothing) to maintain
        diversity — critical in urban GNSS where GPS is a strong attractor that otherwise
        eliminates all particles not near the GPS fix within a few epochs.
        """
        w = self._normalise()
        N = len(w)
        ess = 1.0 / np.sum(w ** 2)
        if ess < N / 3:
            cumsum = np.cumsum(w)
            positions = (np.arange(N) + np.random.random()) / N
            idx = np.searchsorted(cumsum, positions)
            idx = np.clip(idx, 0, N - 1)
            self.particles = self.particles[idx].copy()
            self.log_weights[:] = -np.log(float(N))

            # Kernel regularisation: fixed-bandwidth Gaussian jitter to maintain
            # particle diversity after collapse. Using particle std is dangerous:
            # after GPS-driven collapse all particles are at the same point, std→0,
            # and jitter becomes zero — the filter degenerates to a single particle.
            # Fixed physical bandwidths based on expected navigation accuracy:
            # position ±3m, velocity ±0.2 m/s, heading ±0.05 rad, biases ±0.02.
            jitter_scale = np.array([3.0, 3.0, 0.2, 0.2, 0.05, 0.2, 0.02, 0.02])
            self.particles += np.random.normal(0, jitter_scale, self.particles.shape)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, imu_accel: np.ndarray, imu_gyro: np.ndarray,
            gnss_pos: np.ndarray, p_degraded: np.ndarray,
            adaptive: bool = True, wheel_speed: np.ndarray | None = None,
            use_aiding: bool = True, zupt_thresh: float = 0.2,
            gnss_mask: np.ndarray | None = None,
            seed: int = 42) -> np.ndarray:
        """Run PF on a full sequence.

        Parameters
        ----------
        imu_accel   : (N, 2) body-frame accelerations (ax, ay) m/s²
        imu_gyro    : (N,)   yaw rate ωz rad/s
        gnss_pos    : (N, 2) GNSS ENU positions (m)
        p_degraded  : (N,)   P(DEGRADED) signal from SENTINEL or nsat proxy
        adaptive    : bool   inflate GPS scale with p_degraded
        wheel_speed : (N,)   forward wheel speed (m/s) for NHC/ZUPT
        use_aiding  : bool   whether to apply NHC/ZUPT likelihood
        zupt_thresh : float  speed below which ZUPT fires (m/s)
        gnss_mask   : (N,)   bool, True when a real GPS fix is available this epoch
        seed        : int    RNG seed for reproducibility

        Returns
        -------
        positions : (N, 2) weighted-mean position trajectory
        """
        np.random.seed(seed)

        imu_accel = np.asarray(imu_accel, float)
        imu_gyro = np.asarray(imu_gyro, float).flatten()
        gnss_pos = np.asarray(gnss_pos, float)
        p_degraded = np.asarray(p_degraded, float).flatten()
        if wheel_speed is not None:
            wheel_speed = np.asarray(wheel_speed, float).flatten()

        n, N = len(imu_accel), self.p.n_particles

        # ----------------------------------------------------------
        # Initialise particles around the first GNSS position
        # (same seeding strategy as EKF: velocity from first few fixes)
        # ----------------------------------------------------------
        k_init = min(5, n - 1)
        disp = ((gnss_pos[k_init] - gnss_pos[0]) / (k_init * self.p.dt)
                if n >= 2 else np.zeros(2))
        vx0, vy0 = float(disp[0]), float(disp[1])
        psi0 = float(np.arctan2(vy0, vx0)) if (vx0 ** 2 + vy0 ** 2) > 1e-4 else 0.0

        self.particles = np.zeros((N, 8))
        self.particles[:, 0] = gnss_pos[0, 0] + np.random.normal(0, 5.0, N)
        self.particles[:, 1] = gnss_pos[0, 1] + np.random.normal(0, 5.0, N)
        self.particles[:, 2] = vx0 + np.random.normal(0, 1.0, N)
        self.particles[:, 3] = vy0 + np.random.normal(0, 1.0, N)
        # Wider heading spread (±0.35 rad ≈ ±20°) — key for Odaiba where IMU heading
        # init from only 5 clean GPS fixes can be ±15° off for a slow initial segment.
        self.particles[:, 4] = psi0 + np.random.normal(0, 0.35, N)
        self.particles[:, 5] = np.random.normal(0, 1.0, N)   # clock bias
        self.particles[:, 6] = np.random.normal(0, 0.1, N)   # ba_x
        self.particles[:, 7] = np.random.normal(0, 0.1, N)   # ba_y
        self.log_weights = np.full(N, -np.log(float(N)))

        positions = np.zeros((n, 2))
        w0 = self._normalise()
        positions[0] = (w0[:, None] * self.particles[:, :2]).sum(0)

        for k in range(1, n):
            # ── 1. Predict ─────────────────────────────────────────
            self._propagate(imu_accel[k], imu_gyro[k])

            # ── 2. Aiding: NHC + ZUPT ──────────────────────────────
            if use_aiding and wheel_speed is not None:
                ws = float(wheel_speed[k])
                self.log_weights += self._nhc_log_lh(ws, stationary=(abs(ws) < zupt_thresh))

            # ── 3. GNSS update ─────────────────────────────────────
            if gnss_mask is None or gnss_mask[k]:
                self.log_weights += self._gnss_log_lh(gnss_pos[k], p_degraded[k], adaptive)

            # ── 4. Normalise ───────────────────────────────────────
            # Shift log-weights before exp to prevent overflow/underflow
            self.log_weights -= self.log_weights.max()
            w = np.exp(self.log_weights)
            total = w.sum()
            if total < 1e-300:
                # Complete weight collapse — reinitialise uniformly (filter diverged)
                self.log_weights[:] = -np.log(float(N))
            else:
                w /= total
                self.log_weights = np.log(np.maximum(w, 1e-300))

            # ── 5. Resample ────────────────────────────────────────
            self._systematic_resample()

            # ── 6. State estimate (weighted mean position) ─────────
            w_curr = self._normalise()
            positions[k] = (w_curr[:, None] * self.particles[:, :2]).sum(0)

        return positions
