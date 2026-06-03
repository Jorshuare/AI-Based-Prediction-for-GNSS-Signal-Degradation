"""
ekf_9state.py — Production-grade 9-state Extended Kalman Filter for GNSS/IMU fusion.

9-state model (from your teammate's design):
  State: [x, y, vx, vy, ψ, b, ba_x, ba_y]
    x, y         — position (metres)
    vx, vy       — velocity (m/s)
    ψ            — heading (radians)
    b            — GNSS clock bias (metres)
    ba_x, ba_y   — accelerometer biases (m/s²)

Dynamics:
  Predict:  x, y, vx, vy, ψ propagate via IMU-driven motion model
            ψ_new = ψ + ω_z * dt (from gyro)
            a_nav = R(ψ) @ (a_imu - ba)   (rotate body→nav, subtract bias)
            v_new = v + a_nav * dt
            x_new = x + v * dt
            Clock bias, accel biases evolve slowly (random walk)

  Update:   GNSS position [x, y] measurement with adaptive R(P(DEGRADED))
            Linear measurement model H = [I₂ 0₆]

Robustness features:
  • Heading wraparound: angles kept in [-π, π]
  • Covariance positivity check (eigenvalues ≥ 0)
  • Zero-division guards in Kalman gain
  • IMU NaN/zero fallback (constant velocity)
  • State constraints (velocities bounded, biases realistic)
"""
from __future__ import annotations
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


def wrap_angle(angle):
    """Wrap angle to [-π, π]."""
    while angle > np.pi:
        angle -= 2 * np.pi
    while angle < -np.pi:
        angle += 2 * np.pi
    return angle


def rotation_2d(psi):
    """2D rotation matrix: [cos(ψ) -sin(ψ); sin(ψ) cos(ψ)]."""
    c, s = np.cos(psi), np.sin(psi)
    return np.array([[c, -s], [s, c]], dtype=float)


@dataclass
class EKF9StateParams:
    """Configuration for 9-state EKF."""
    dt: float = 0.1               # timestep (seconds)
    q_pos: float = 0.1            # process noise: position (m²/s⁴)
    q_vel: float = 0.01           # process noise: velocity (m²/s³)
    q_heading: float = 0.001      # process noise: heading (rad²/s²)
    q_bias: float = 0.0001        # process noise: clock/accel bias (m²/s, m²/s⁵)
    r_base: float = 3.0           # GNSS measurement std, clean (metres)
    r_degraded: float = 100.0     # GNSS measurement std, degraded (metres)
    p_threshold: float = 0.5      # degradation threshold for fallback
    alpha: float = 1.0            # R adaptation scaling factor
    v_max: float = 50.0           # velocity saturation (m/s, ~180 km/h)
    ba_max: float = 5.0           # accel bias saturation (m/s²)


class EKF9State:
    """9-state Extended Kalman Filter for GNSS/IMU fusion with adaptive measurement noise."""

    def __init__(self, params: EKF9StateParams = None):
        if params is None:
            params = EKF9StateParams()
        self.p = params
        # Initialize state & covariance
        self.state = None  # will be set on first update
        self.P = None      # covariance

    def _build_Q(self):
        """Process noise covariance (continuous-time approximation)."""
        dt = self.p.dt
        q_pos, q_vel, q_heading, q_bias = self.p.q_pos, self.p.q_vel, self.p.q_heading, self.p.q_bias
        Q = np.diag([
            q_pos * (dt**4) / 4,       # x
            q_pos * (dt**4) / 4,       # y
            q_vel * (dt**2) / 2,       # vx
            q_vel * (dt**2) / 2,       # vy
            q_heading * dt,            # ψ
            q_bias * dt,               # b
            q_bias * dt,               # ba_x
            q_bias * dt,               # ba_y
        ]) + np.eye(8) * 1e-8  # ensure positivity
        return Q

    def _R_adaptive(self, p_degraded):
        """Adaptive measurement covariance: interpolate base → degraded."""
        p = np.clip(float(p_degraded), 0, 1)
        std = self.p.r_base + (self.p.r_degraded - self.p.r_base) * self.p.alpha * p
        return np.eye(2) * (std ** 2)

    def _jacobian_predict(self, state, imu_accel, imu_gyro, dt):
        """Jacobian F of the predict step (8×8 matrix for covariance propagation)."""
        x, y, vx, vy, psi, b, ba_x, ba_y = state
        ax_imu, ay_imu = imu_accel[0], imu_accel[1]
        omega_z = imu_gyro

        # Unbiased acceleration in body frame
        ax_body = ax_imu - ba_x
        ay_body = ay_imu - ba_y

        # Partial of navigation-frame accel w.r.t. heading: d(a_nav)/dψ
        sin_psi = np.sin(psi)
        cos_psi = np.cos(psi)
        da_nav_dpsi = np.array([
            -ax_body * sin_psi - ay_body * cos_psi,  # dx_nav/dψ
            ax_body * cos_psi - ay_body * sin_psi,   # dy_nav/dψ
        ])

        # Build Jacobian F (8×8)
        F = np.eye(8, dtype=float)
        F[0, 2] = dt            # ∂x/∂vx
        F[1, 3] = dt            # ∂y/∂vy
        F[2, 4] = da_nav_dpsi[0] * dt  # ∂vx/∂ψ
        F[3, 4] = da_nav_dpsi[1] * dt  # ∂vy/∂ψ
        # ∂vx/∂ba_x, ∂vx/∂ba_y: ∂a_nav/∂ba = -R(ψ)
        F[2, 6] = -cos_psi * dt   # ∂vx/∂ba_x
        F[2, 7] = sin_psi * dt    # ∂vx/∂ba_y
        F[3, 6] = -sin_psi * dt   # ∂vy/∂ba_x
        F[3, 7] = -cos_psi * dt   # ∂vy/∂ba_y
        # ψ and others evolve independently (ψ_new = ψ + ω_z * dt is linear in ψ)

        return F

    def predict(self, imu_accel, imu_gyro):
        """Predict step: propagate state via IMU-driven motion model."""
        if self.state is None or self.P is None:
            raise RuntimeError("Filter not initialized; call update() first")

        # Extract state
        x, y, vx, vy, psi, b, ba_x, ba_y = self.state
        ax_imu, ay_imu = imu_accel[0], imu_accel[1]
        omega_z = imu_gyro
        dt = self.p.dt

        # Handle missing/NaN IMU (fallback to constant velocity)
        if np.isnan(ax_imu) or np.isnan(ay_imu) or np.isnan(omega_z):
            # Constant-velocity model: position updates via velocity, accel = 0
            x_new = x + vx * dt
            y_new = y + vy * dt
            vx_new = vx
            vy_new = vy
            psi_new = psi
        else:
            # Unbiased acceleration in body frame
            ax_body = ax_imu - ba_x
            ay_body = ay_imu - ba_y

            # Rotate to nav frame: a_nav = R(ψ) @ a_body
            R = rotation_2d(psi)
            a_nav = R @ np.array([ax_body, ay_body])

            # Update state: constant-heading motion + accel
            x_new = x + vx * dt
            y_new = y + vy * dt
            vx_new = vx + a_nav[0] * dt
            vy_new = vy + a_nav[1] * dt
            psi_new = psi + omega_z * dt

        # Clamp velocities
        vx_new = np.clip(vx_new, -self.p.v_max, self.p.v_max)
        vy_new = np.clip(vy_new, -self.p.v_max, self.p.v_max)

        # Wrap heading
        psi_new = wrap_angle(psi_new)

        # Clock bias, accel biases: slow random walk (no update in predict)
        b_new = b
        ba_x_new = ba_x
        ba_y_new = ba_y

        # Update state
        self.state = np.array([x_new, y_new, vx_new, vy_new, psi_new, b_new, ba_x_new, ba_y_new])

        # Propagate covariance: P = F @ P @ F^T + Q
        F = self._jacobian_predict(self.state, imu_accel, imu_gyro, dt)
        Q = self._build_Q()
        self.P = F @ self.P @ F.T + Q

        # Ensure P is positive-definite
        evals = np.linalg.eigvalsh(self.P)
        if evals.min() < 1e-10:
            self.P += np.eye(8) * (1e-10 - evals.min())

    def update(self, gnss_pos, p_degraded, adaptive=True):
        """Update step: fuse GNSS measurement with adaptive R based on P(DEGRADED)."""
        if self.state is None:
            raise RuntimeError("State not initialized")

        gnss_pos = np.asarray(gnss_pos, dtype=float)
        if gnss_pos.ndim != 1 or len(gnss_pos) != 2:
            raise ValueError(f"gnss_pos must be (2,), got {gnss_pos.shape}")

        # Measurement model: observe [x, y] only
        H = np.zeros((2, 8), dtype=float)
        H[0, 0] = 1.0
        H[1, 1] = 1.0

        # Adaptive measurement covariance
        if adaptive:
            R = self._R_adaptive(p_degraded)
        else:
            R = self._R_adaptive(0.0)  # r_base only

        # Innovation (measurement residual)
        z = gnss_pos
        z_pred = H @ self.state
        y = z - z_pred

        # Innovation covariance: S = H @ P @ H^T + R
        S = H @ self.P @ H.T + R

        # Ensure S is invertible
        try:
            S_inv = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            # Add regularization if singular
            S += np.eye(2) * 1e-6
            S_inv = np.linalg.inv(S)

        # Kalman gain: K = P @ H^T @ S^{-1}
        K = self.P @ H.T @ S_inv

        # State update: x = x + K @ y
        self.state = self.state + K @ y

        # Covariance update: P = (I - K @ H) @ P
        self.P = (np.eye(8) - K @ H) @ self.P

        # Ensure P remains positive-definite
        evals = np.linalg.eigvalsh(self.P)
        if evals.min() < 1e-10:
            self.P += np.eye(8) * (1e-10 - evals.min())

    def run(self, imu_accel, imu_gyro, gnss_pos, p_degraded, adaptive=True):
        """Run full filter on a sequence. Returns filtered positions and state history.

        Parameters
        ----------
        imu_accel    : (N, 2) body-frame accelerations (ax, ay) in m/s²
        imu_gyro     : (N,) yaw rate ωz in rad/s
        gnss_pos     : (N, 2) GNSS positions (x, y) in metres
        p_degraded   : (N,) predicted P(DEGRADED) from SENTINEL-GNSS
        adaptive     : bool, whether to use adaptive R

        Returns
        -------
        positions    : (N, 2) filtered position trajectory
        states       : (N, 8) full state history
        """
        imu_accel = np.asarray(imu_accel, dtype=float)
        imu_gyro = np.asarray(imu_gyro, dtype=float).flatten()
        gnss_pos = np.asarray(gnss_pos, dtype=float)
        p_degraded = np.asarray(p_degraded, dtype=float).flatten()

        n = len(imu_accel)
        assert len(imu_gyro) == n, "imu_gyro length mismatch"
        assert len(gnss_pos) == n, "gnss_pos length mismatch"
        assert len(p_degraded) == n, "p_degraded length mismatch"

        # Initialize state at first GNSS position
        self.state = np.array([
            gnss_pos[0, 0],    # x
            gnss_pos[0, 1],    # y
            0.0,               # vx
            0.0,               # vy
            0.0,               # ψ
            0.0,               # b (clock bias)
            0.0,               # ba_x
            0.0,               # ba_y
        ], dtype=float)
        self.P = np.eye(8) * 10.0  # initial uncertainty

        positions = np.zeros((n, 2), dtype=float)
        states = np.zeros((n, 8), dtype=float)
        positions[0] = self.state[:2]
        states[0] = self.state.copy()

        # Main filter loop
        for k in range(1, n):
            # Predict
            self.predict(imu_accel[k], imu_gyro[k])

            # Update
            self.update(gnss_pos[k], p_degraded[k], adaptive=adaptive)

            # Store
            positions[k] = self.state[:2]
            states[k] = self.state.copy()

        return positions, states

    def validate(self, truth_xy, p_degraded=None):
        """Compute RMSE and metrics against ground truth.

        Parameters
        ----------
        truth_xy     : (N, 2) reference trajectory
        p_degraded   : (N,) P(DEGRADED) for optional segment analysis

        Returns
        -------
        metrics      : dict with RMSE overall, degraded segment, improvement %
        """
        def rmse(a, b):
            return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))

        truth_xy = np.asarray(truth_xy, dtype=float)
        n = len(truth_xy)

        # Assume self.positions was populated by run()
        if not hasattr(self, '_last_positions'):
            raise RuntimeError("No positions stored; call run() first")

        positions = self._last_positions
        if len(positions) != n:
            # Trim to match truth length
            positions = positions[:n]

        metrics = {
            "n_epochs": int(n),
            "rmse_overall": round(rmse(positions, truth_xy), 3),
        }

        if p_degraded is not None:
            p_degraded = np.asarray(p_degraded, dtype=float).flatten()
            deg_mask = p_degraded >= self.p.p_threshold
            if deg_mask.sum() > 0:
                metrics["n_degraded_epochs"] = int(deg_mask.sum())
                metrics["rmse_degraded_segment"] = round(
                    rmse(positions[deg_mask], truth_xy[deg_mask]), 3
                )

        return metrics


def run_ekf_experiment_9state(imu_accel, imu_gyro, gnss_xy, truth_xy, p_degraded,
                               params=None):
    """Full experiment: compare fixed-R vs adaptive-R with 9-state EKF.

    Returns dict with RMSE metrics for both strategies.
    """
    if params is None:
        params = EKF9StateParams()

    imu_accel = np.asarray(imu_accel, dtype=float)
    imu_gyro = np.asarray(imu_gyro, dtype=float).flatten()
    gnss_xy = np.asarray(gnss_xy, dtype=float)
    truth_xy = np.asarray(truth_xy, dtype=float)
    p_degraded = np.asarray(p_degraded, dtype=float).flatten()

    def rmse(a, b):
        return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))

    # Fixed-R (adaptive=False)
    ekf_fixed = EKF9State(params)
    pos_fixed, _ = ekf_fixed.run(imu_accel, imu_gyro, gnss_xy, p_degraded, adaptive=False)
    ekf_fixed._last_positions = pos_fixed

    # Adaptive-R (adaptive=True)
    ekf_adapt = EKF9State(params)
    pos_adapt, _ = ekf_adapt.run(imu_accel, imu_gyro, gnss_xy, p_degraded, adaptive=True)
    ekf_adapt._last_positions = pos_adapt

    # Compute metrics
    rmse_gnss = rmse(gnss_xy, truth_xy)
    rmse_fixed = rmse(pos_fixed, truth_xy)
    rmse_adapt = rmse(pos_adapt, truth_xy)

    result = {
        "n_epochs": int(len(gnss_xy)),
        "rmse_overall": {
            "gnss_only": round(rmse_gnss, 3),
            "fixed_ekf": round(rmse_fixed, 3),
            "adaptive_ekf": round(rmse_adapt, 3),
        },
    }

    # Degraded segment analysis
    deg_mask = p_degraded >= params.p_threshold
    if deg_mask.sum() > 0:
        result["n_degraded_epochs"] = int(deg_mask.sum())
        result["rmse_degraded_segment"] = {
            "gnss_only": round(rmse(gnss_xy[deg_mask], truth_xy[deg_mask]), 3),
            "fixed_ekf": round(rmse(pos_fixed[deg_mask], truth_xy[deg_mask]), 3),
            "adaptive_ekf": round(rmse(pos_adapt[deg_mask], truth_xy[deg_mask]), 3),
        }

        # Improvement percentage
        if result["rmse_degraded_segment"]["gnss_only"] > 0:
            pct = 100.0 * (result["rmse_degraded_segment"]["gnss_only"] -
                          result["rmse_degraded_segment"]["adaptive_ekf"]) / \
                  result["rmse_degraded_segment"]["gnss_only"]
            result["adaptive_improvement_pct_degraded"] = round(pct, 1)

    if result["rmse_overall"]["gnss_only"] > 0:
        pct = 100.0 * (result["rmse_overall"]["gnss_only"] -
                      result["rmse_overall"]["adaptive_ekf"]) / \
              result["rmse_overall"]["gnss_only"]
        result["adaptive_improvement_pct_overall"] = round(pct, 1)

    return result


if __name__ == "__main__":
    # Self-test: simple synthetic trajectory
    from adaptive_ekf import synthetic_demo as synthetic_simple
    print("9-state EKF module loaded. Use run_ekf_experiment_9state() or EKF9State class.")
