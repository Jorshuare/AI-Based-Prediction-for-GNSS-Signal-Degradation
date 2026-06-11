/** Shared types mirroring the FastAPI backend contract. */

export type Horizon = 5 | 15 | 30;

export interface Prediction {
  window: number;
  end_epoch: number;
  timestamp: string;
  lat: number;
  lon: number;
  x: number;
  y: number;
  p_clean_5s: number;
  p_warning_5s: number;
  p_degraded_5s: number;
  pred_5s: string;
  p_clean_15s: number;
  p_warning_15s: number;
  p_degraded_15s: number;
  pred_15s: string;
  p_clean_30s: number;
  p_warning_30s: number;
  p_degraded_30s: number;
  pred_30s: string;
}

export interface Scenario {
  id: string;
  n_epochs: number | null;
  mean_p_degraded_5s: number | null;
  source: string;
}

export interface Summary {
  nmea_file: string;
  n_epochs: number;
  window_size: number;
  class_counts_5s: Record<string, number>;
  mean_p_degraded_5s: number;
  class_counts_15s: Record<string, number>;
  mean_p_degraded_15s: number;
  class_counts_30s: Record<string, number>;
  mean_p_degraded_30s: number;
  first_degraded_window_5s: number | null;
  status: string;
}

export interface SweepRow {
  bias_max_m: number;
  raw: number;
  fixed_R: number;
  adaptive_R: number;
  adaptive_vs_fixed_pct: number;
}

export interface EkfResult {
  scenario: string;
  n_epochs: number;
  n_blocked_epochs: number;
  blocked_pct: number;
  rmse_overall: Record<string, number>;
  rmse_blocked_segment: Record<string, number>;
  gains_vs_raw_blocked: Record<string, number>;
  severity_sweep: SweepRow[];
  adaptive_crossover_bias_m: number | null;
}

export interface FusionResult {
  summary: {
    data_mode: string;
    gnss_source: string;
    engine: string;
    n_epochs: number;
    n_real_fixes: number;
    n_degraded_epochs: number;
    mean_sats: number;
    rmse_overall: Record<string, number>;
    rmse_degraded_segment: Record<string, number>;
    degraded_gain_vs_raw: Record<string, number>;
  };
  /** ENU origin lat/lon (first valid GNSS fix) — used for map overlay */
  origin_lat: number;
  origin_lon: number;
  truth: [number, number][];
  gnss: [number, number][];
  aided_fixed: [number, number][];
  aided_adapt: [number, number][];
  is_degraded: boolean[];
  nsat: number[];
  p_degraded: number[];
}

/** Probabilities for one horizon, extracted from a Prediction. */
export interface HorizonProbs {
  clean: number;
  warning: number;
  degraded: number;
  pred: string;
}

export function horizonProbs(p: Prediction, h: Horizon): HorizonProbs {
  if (h === 5)
    return { clean: p.p_clean_5s, warning: p.p_warning_5s, degraded: p.p_degraded_5s, pred: p.pred_5s };
  if (h === 15)
    return { clean: p.p_clean_15s, warning: p.p_warning_15s, degraded: p.p_degraded_15s, pred: p.pred_15s };
  return { clean: p.p_clean_30s, warning: p.p_warning_30s, degraded: p.p_degraded_30s, pred: p.pred_30s };
}
