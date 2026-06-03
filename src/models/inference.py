"""
inference.py — End-to-end SENTINEL-GNSS inference: raw NMEA → proactive predictions → EKF.

Turns a receiver's NMEA log into:
  • per-window predictions P(CLEAN/WARNING/DEGRADED) at +5/+15/+30 s,
  • a P(DEGRADED) time series + local-ENU positions ready for the adaptive EKF,
  • a human-readable summary (counts, lead-time stats).
Optionally runs the adaptive EKF (and computes RMSE if a reference trajectory is supplied).

The feature transform replicates training exactly (impute → clip → delta → receiver_tier →
saved MinMaxScaler), using the canonical 37-feature order so it always matches the fitted
scaler regardless of input column order.

INPUT   : an NMEA file (e.g. data/raw/scenarios/Degraded data/A/log_0000.nmea)
OUTPUT  : <out>/<stem>_predictions.csv, <out>/<stem>_summary.json
          (+ <stem>_ekf.json if --ekf)

Usage
-----
  python -m src.models.inference --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea"
  python -m src.models.inference --nmea PATH --out results/inference --receiver_tier 0 --ekf
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Canonical 37-feature order (alphabetical + cnr_available last) — matches the fitted scaler.
FEATURE_NAMES = [
    "alt", "baseline_sats", "clock_bias", "cnr_trend", "cnr_variance", "cycle_slips",
    "dop_ratio", "elevation_violations", "fix_continuity", "fix_transitions", "gdop",
    "hdop", "hdop_delta", "iono_delay", "lat_std", "lon_std", "max_cnr", "mean_cnr",
    "min_cnr", "multipath", "num_satellites", "pdop", "pdop_delta", "position_variance",
    "receiver_tier", "residual_mean", "residual_std", "sat_drop_rate", "sat_mean",
    "sat_min", "sat_visibility", "solution_age", "solution_status", "std_cnr",
    "tropo_delay", "vdop", "cnr_available",
]
WINDOW = 30
HORIZONS = {"5s": 5, "15s": 15, "30s": 30}
CLASSES = ["CLEAN", "WARNING", "DEGRADED"]
DEFAULT_CKPT = ROOT / "results" / "models" / "checkpoints" / "checkpoint_best.pt"
DEFAULT_SCALER = ROOT / "data" / "processed" / "scaler.pkl"


# ─── helpers ──────────────────────────────────────────────────────────────────
def latlon_to_enu(lat, lon, lat0, lon0):
    """Equirectangular local ENU (metres) about (lat0, lon0). Good for short routes."""
    R = 6_378_137.0
    lat = np.radians(lat); lon = np.radians(lon)
    lat0 = np.radians(lat0); lon0 = np.radians(lon0)
    x = R * (lon - lon0) * np.cos(lat0)   # East
    y = R * (lat - lat0)                  # North
    return x, y


class SentinelInference:
    def __init__(self, checkpoint=DEFAULT_CKPT, scaler=DEFAULT_SCALER, receiver_tier=0):
        import torch
        import pickle
        self.torch = torch
        if not Path(checkpoint).exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint}\nTrain the model first.")
        if not Path(scaler).exists():
            raise FileNotFoundError(f"Scaler not found: {scaler}\nRun feature_prep first.")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.receiver_tier = int(receiver_tier)
        with open(scaler, "rb") as fh:
            self.scaler = pickle.load(fh)
        from src.models.transformer_lstm import SentinelGNSS
        ck = torch.load(checkpoint, map_location=self.device, weights_only=False)
        cfg = ck.get("config", {})
        self.model = SentinelGNSS(
            n_features=cfg.get("n_features", 37), n_classes=cfg.get("n_classes", 3),
            d_model=cfg.get("d_model", 128), n_heads=cfg.get("n_heads", 8),
            n_tf_layers=cfg.get("n_tf_layers", 2), d_ff=cfg.get("d_ff", 512),
            lstm_hidden=cfg.get("lstm_hidden", 256), n_lstm_layers=cfg.get("n_lstm_layers", 2),
            dropout=cfg.get("dropout", 0.3),
        ).to(self.device)
        # strict load when the checkpoint matches; otherwise load compatible weights and
        # warn (the auxiliary +0s head is not used at inference — only +5/+15/+30s).
        try:
            self.model.load_state_dict(ck["model"])
        except RuntimeError as e:
            missing = self.model.load_state_dict(ck["model"], strict=False)
            mk = list(missing.missing_keys); uk = list(missing.unexpected_keys)
            if any(not k.startswith("head_0s") for k in mk + uk):
                raise RuntimeError(
                    f"Checkpoint architecture mismatch beyond the auxiliary head:\n{e}")
            print(f"[warn] loaded with strict=False (auxiliary head differs): "
                  f"missing={mk} unexpected={uk}")
        self.model.eval()

    # ── raw NMEA → per-epoch features + positions ────────────────────────────
    def features_from_nmea(self, nmea_path):
        nmea_path = Path(nmea_path)
        if not nmea_path.exists():
            raise FileNotFoundError(f"NMEA file not found: {nmea_path}")
        if nmea_path.stat().st_size == 0:
            raise ValueError(f"NMEA file is empty: {nmea_path}")

        from src.processing.process_all_datasets import NmeaParser, compute_features
        from src.models import feature_prep as fp

        parser = NmeaParser()
        epoch_df = parser.parse_file(nmea_path)
        if epoch_df is None or len(epoch_df) == 0:
            raise ValueError(f"No GNSS epochs parsed from {nmea_path} (malformed NMEA?)")

        feat = compute_features(epoch_df)
        if feat is None or len(feat) == 0:
            raise ValueError("Feature computation produced no rows.")

        # metadata columns some transforms expect
        feat = feat.copy()
        feat["source"] = "inference"
        feat["scenario"] = "inference"

        # exact training transform order
        feat = fp.impute(feat)
        feat = fp.clip_features(feat)
        feat = fp.add_delta_features(feat)
        feat["receiver_tier"] = float(self.receiver_tier)

        # guarantee all 37 canonical features exist
        for c in FEATURE_NAMES:
            if c not in feat.columns:
                feat[c] = 0.0
        feat[FEATURE_NAMES] = feat[FEATURE_NAMES].fillna(0.0)

        # positions for the EKF (local ENU about the first valid fix)
        pos = pd.DataFrame({"timestamp": feat.get("timestamp", pd.RangeIndex(len(feat)))})
        if "lat" in feat.columns and "lon" in feat.columns and feat["lat"].notna().any():
            v = feat["lat"].notna() & feat["lon"].notna()
            lat0 = float(feat.loc[v, "lat"].iloc[0]); lon0 = float(feat.loc[v, "lon"].iloc[0])
            x, y = latlon_to_enu(feat["lat"].values, feat["lon"].values, lat0, lon0)
            pos["lat"] = feat["lat"].values; pos["lon"] = feat["lon"].values
            pos["x"] = x; pos["y"] = y
        else:
            pos["lat"] = np.nan; pos["lon"] = np.nan; pos["x"] = np.nan; pos["y"] = np.nan
        return feat, pos

    # ── features → sliding windows ────────────────────────────────────────────
    def windows(self, feat):
        Xs = self.scaler.transform(feat[FEATURE_NAMES].values.astype(np.float32))
        n = len(Xs)
        max_h = max(HORIZONS.values())
        # windows whose label horizon stays in range; for live prediction we also
        # allow windows up to the end (no future label needed at inference time).
        starts = list(range(0, n - WINDOW + 1))
        if not starts:
            return None, None
        Xw = np.stack([Xs[i:i + WINDOW] for i in starts]).astype(np.float32)
        end_idx = [s + WINDOW - 1 for s in starts]   # epoch index the window ends on
        return Xw, end_idx

    # ── predict ──────────────────────────────────────────────────────────────
    def predict(self, Xw, bs=512, xgb_model=None):
        torch = self.torch
        probs = {h: [] for h in HORIZONS}
        for i in range(0, len(Xw), bs):
            xb = torch.tensor(Xw[i:i + bs], dtype=torch.float32).to(self.device)
            with torch.no_grad():
                out = self.model(xb)
            for h in HORIZONS:
                probs[h].append(torch.softmax(out[f"logits_{h}"], dim=-1).cpu().numpy())
        probs = {h: np.concatenate(v) for h, v in probs.items()}
        # Soft-vote ensemble: (DL + XGB) / 2
        if xgb_model is not None:
            Xwf = Xw.reshape(len(Xw), -1)
            xgb_probs = xgb_model.predict_proba(Xwf)
            for h in HORIZONS:
                probs[h] = (probs[h] + xgb_probs) / 2.0
        return probs

    # ── orchestration ─────────────────────────────────────────────────────────
    def run_file(self, nmea_path, out_dir, run_ekf=False, ekf_horizon="5s", use_ensemble=False):
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(nmea_path).parent.name + "_" + Path(nmea_path).stem \
            if Path(nmea_path).stem == "log_0000" else Path(nmea_path).stem

        feat, pos = self.features_from_nmea(nmea_path)
        n_epochs = len(feat)
        result = {"nmea_file": str(nmea_path), "n_epochs": int(n_epochs),
                  "window_size": WINDOW, "receiver_tier": self.receiver_tier}

        # Load XGBoost ensemble model if requested
        xgb_model = None
        if use_ensemble:
            try:
                import joblib
                xgb_path = ROOT / "results" / "ensemble_xgb_model.joblib"
                if xgb_path.exists():
                    xgb_model = joblib.load(xgb_path)
                    result["ensemble"] = "DL + XGBoost soft-vote"
                else:
                    print(f"[warn] --ensemble requested but {xgb_path} not found; using DL only")
            except Exception as e:
                print(f"[warn] failed to load ensemble model: {e}")

        Xw, end_idx = self.windows(feat)
        if Xw is None:
            result["status"] = "too_short"
            result["message"] = f"Only {n_epochs} epochs; need >= {WINDOW} for one window."
            with open(out_dir / f"{stem}_summary.json", "w") as fh:
                json.dump(result, fh, indent=2, default=str)
            print(f"[warn] {result['message']}")
            return result

        probs = self.predict(Xw, xgb_model=xgb_model)

        # per-window prediction table
        rows = []
        for w, ei in enumerate(end_idx):
            row = {"window": w, "end_epoch": ei}
            if "timestamp" in feat.columns:
                row["timestamp"] = feat["timestamp"].iloc[ei]
            for col in ("lat", "lon", "x", "y"):
                row[col] = pos[col].iloc[ei] if ei < len(pos) else np.nan
            for h in HORIZONS:
                p = probs[h][w]
                row[f"p_clean_{h}"] = round(float(p[0]), 4)
                row[f"p_warning_{h}"] = round(float(p[1]), 4)
                row[f"p_degraded_{h}"] = round(float(p[2]), 4)
                row[f"pred_{h}"] = CLASSES[int(p.argmax())]
            rows.append(row)
        pred_df = pd.DataFrame(rows)
        pred_csv = out_dir / f"{stem}_predictions.csv"
        pred_df.to_csv(pred_csv, index=False)

        # summary stats
        for h in HORIZONS:
            preds = pred_df[f"pred_{h}"].value_counts().to_dict()
            result[f"class_counts_{h}"] = {c: int(preds.get(c, 0)) for c in CLASSES}
            result[f"mean_p_degraded_{h}"] = round(float(pred_df[f"p_degraded_{h}"].mean()), 4)
        # lead time: first window flagging DEGRADED at +5s
        deg5 = pred_df.index[pred_df["pred_5s"] == "DEGRADED"].tolist()
        result["first_degraded_window_5s"] = int(deg5[0]) if deg5 else None
        result["predictions_csv"] = str(pred_csv)
        result["status"] = "ok"

        # optional EKF
        if run_ekf:
            result["ekf"] = self._run_ekf(pred_df, ekf_horizon, out_dir, stem)

        with open(out_dir / f"{stem}_summary.json", "w") as fh:
            json.dump(result, fh, indent=2, default=str)
        print(f"[ok] {n_epochs} epochs -> {len(pred_df)} windows")
        print(f"     predictions: {pred_csv}")
        print(f"     summary    : {out_dir / f'{stem}_summary.json'}")
        return result

    def _run_ekf(self, pred_df, horizon, out_dir, stem):
        from src.models.adaptive_ekf import AdaptiveEKF
        if pred_df[["x", "y"]].isna().all().all():
            return {"status": "no_positions",
                    "message": "NMEA had no usable lat/lon fixes; EKF needs positions."}
        sub = pred_df.dropna(subset=["x", "y"]).reset_index(drop=True)
        gnss = sub[["x", "y"]].values.astype(float)
        p_deg = sub[f"p_degraded_{horizon}"].values.astype(float)
        ekf = AdaptiveEKF()
        fixed = ekf.run(gnss, p_deg, adaptive=False)
        adapt = ekf.run(gnss, p_deg, adaptive=True)
        out = {"status": "ok", "horizon": horizon, "n_positions": int(len(gnss)),
               "note": "No ground truth in NMEA → filtered trajectories saved; RMSE needs a "
                       "reference trajectory (pass to run_ekf_experiment).",
               "mean_p_degraded": round(float(p_deg.mean()), 4)}
        np.savez(out_dir / f"{stem}_ekf.npz", gnss=gnss, fixed=fixed, adaptive=adapt, p_degraded=p_deg)
        out["ekf_npz"] = str(out_dir / f"{stem}_ekf.npz")
        return out


def main():
    ap = argparse.ArgumentParser(description="SENTINEL-GNSS end-to-end inference (NMEA -> predictions -> EKF)")
    ap.add_argument("--nmea", required=True, help="path to an NMEA file")
    ap.add_argument("--out", default=str(ROOT / "results" / "inference"), help="output directory")
    ap.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    ap.add_argument("--scaler", default=str(DEFAULT_SCALER))
    ap.add_argument("--receiver_tier", type=int, default=0,
                    help="0=professional(Septentrio) .. 3=consumer phone (default 0)")
    ap.add_argument("--ensemble", action="store_true",
                    help="use DL + XGBoost soft-vote ensemble (requires ensemble_xgb_model.joblib)")
    ap.add_argument("--ekf", action="store_true", help="also run the adaptive EKF")
    ap.add_argument("--ekf_horizon", default="5s", choices=list(HORIZONS))
    args = ap.parse_args()

    eng = SentinelInference(args.checkpoint, args.scaler, args.receiver_tier)
    eng.run_file(args.nmea, args.out, run_ekf=args.ekf, ekf_horizon=args.ekf_horizon, use_ensemble=args.ensemble)


if __name__ == "__main__":
    main()
