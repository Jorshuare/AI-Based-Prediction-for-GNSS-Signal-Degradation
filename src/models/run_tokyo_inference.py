"""
Run SENTINEL inference on pre-processed Tokyo Shinjuku features and save
results in the same format as the Beihang scenarios so the dashboard picks
them up automatically.

Outputs (both required by the dashboard backend):
    results/inference/tokyo_shinjuku_predictions.csv
    results/inference/tokyo_shinjuku_summary.json

Usage:
    python -m src.models.run_tokyo_inference
    python -m src.models.run_tokyo_inference --odaiba   # Odaiba dataset instead
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, str(ROOT))

FEATURE_NAMES = [
    "alt", "baseline_sats", "clock_bias", "cnr_trend", "cnr_variance", "cycle_slips",
    "dop_ratio", "elevation_violations", "fix_continuity", "fix_transitions", "gdop",
    "hdop", "hdop_delta", "iono_delay", "lat_std", "lon_std", "max_cnr", "mean_cnr",
    "min_cnr", "multipath", "num_satellites", "pdop", "pdop_delta", "position_variance",
    "receiver_tier", "residual_mean", "residual_std", "sat_drop_rate", "sat_mean",
    "sat_min", "sat_visibility", "solution_age", "solution_status", "std_cnr",
    "tropo_delay", "vdop", "cnr_available",
]
WINDOW   = 30
HORIZONS = {"5s": 5, "15s": 15, "30s": 30}
CLASSES  = ["CLEAN", "WARNING", "DEGRADED"]

DEFAULT_CKPT   = ROOT / "results" / "models" / "checkpoints" / "checkpoint_best.pt"
DEFAULT_SCALER = ROOT / "data" / "processed" / "scaler.pkl"


def latlon_to_enu(lat, lon, lat0, lon0):
    R = 6_378_137.0
    lat  = np.radians(lat);  lon  = np.radians(lon)
    lat0 = np.radians(lat0); lon0 = np.radians(lon0)
    x = R * (lon - lon0) * np.cos(lat0)
    y = R * (lat - lat0)
    return x, y


def run(features_csv: Path, stem: str, out_dir: Path,
        checkpoint=DEFAULT_CKPT, scaler_path=DEFAULT_SCALER):

    import pickle, torch
    from src.models.transformer_lstm import SentinelGNSS
    from src.models import feature_prep as fp

    print(f"[info] Loading features: {features_csv}")
    feat = pd.read_csv(features_csv)
    print(f"[info]  {len(feat)} epochs, {len(feat.columns)} columns")

    # ── apply the same feature engineering used during training ──────────────
    feat["source"]   = "tokyo"
    feat["scenario"] = stem

    feat = fp.impute(feat)
    feat = fp.clip_features(feat)
    feat = fp.add_delta_features(feat)
    feat["receiver_tier"] = 1.0      # Trimble professional = tier 1
    feat["cnr_available"] = (feat.get("mean_cnr", pd.Series(dtype=float)) > 0).astype(float)

    for c in FEATURE_NAMES:
        if c not in feat.columns:
            feat[c] = 0.0
    feat[FEATURE_NAMES] = feat[FEATURE_NAMES].fillna(0.0)

    # ── ENU positions — merge from SPAN-INS reference.csv ────────────────────
    # The features CSV has no lat/lon (extracted from RINEX obs, not position).
    # Use the reference.csv ground-truth positions aligned by timestamp.
    pos = pd.DataFrame({"timestamp": feat.get("timestamp", pd.RangeIndex(len(feat)))})

    ref_file = features_csv.parents[2] / "raw" / "public" / "urbannav" / "Tokyo" / features_csv.stem.replace("tokyo_", "").replace("_features", "").capitalize() / "reference.csv"
    if not ref_file.exists():
        # Try lower-case folder name
        cap = features_csv.stem.replace("tokyo_", "").replace("_features", "")
        for candidate in features_csv.parents[2].rglob("reference.csv"):
            if cap in str(candidate).lower():
                ref_file = candidate
                break

    lat_arr = np.full(len(feat), np.nan)
    lon_arr = np.full(len(feat), np.nan)

    if ref_file.exists():
        print(f"[info] Merging positions from {ref_file}")
        import datetime
        ref = pd.read_csv(ref_file)
        ref.columns = ref.columns.str.strip()
        gps_epoch = datetime.datetime(1980, 1, 6, tzinfo=datetime.timezone.utc)
        ref_ts = pd.to_datetime([
            gps_epoch + datetime.timedelta(weeks=int(w), seconds=float(t))
            for w, t in zip(ref["GPS Week"], ref["GPS TOW (s)"])
        ], utc=True)
        ref_lat = ref["Latitude (deg)"].values
        ref_lon = ref["Longitude (deg)"].values

        feat_ts = pd.to_datetime(feat["timestamp"], format="mixed", utc=True)

        # Nearest-neighbour join within 0.2 s tolerance
        ref_idx  = ref_ts.values.astype("int64")  # nanoseconds
        feat_idx = feat_ts.values.astype("int64")
        tol_ns   = int(0.2e9)  # 0.2 s

        for i, ft in enumerate(feat_idx):
            diff = np.abs(ref_idx - ft)
            best = int(np.argmin(diff))
            if diff[best] <= tol_ns:
                lat_arr[i] = ref_lat[best]
                lon_arr[i] = ref_lon[best]

        filled = np.sum(~np.isnan(lat_arr))
        print(f"[info]  Matched {filled}/{len(feat)} epochs to reference positions")
    else:
        print(f"[warn] reference.csv not found at {ref_file} — positions will be NaN")

    if not np.all(np.isnan(lat_arr)):
        v    = ~np.isnan(lat_arr)
        lat0 = float(lat_arr[v][0])
        lon0 = float(lon_arr[v][0])
        x, y = latlon_to_enu(lat_arr, lon_arr, lat0, lon0)
        x[np.isnan(lat_arr)] = np.nan
        y[np.isnan(lat_arr)] = np.nan
        pos["lat"] = lat_arr
        pos["lon"] = lon_arr
        pos["x"]   = x
        pos["y"]   = y
    else:
        pos["lat"] = np.nan; pos["lon"] = np.nan
        pos["x"]   = np.nan; pos["y"]   = np.nan

    # ── load model ────────────────────────────────────────────────────────────
    print(f"[info] Loading checkpoint: {checkpoint}")
    with open(scaler_path, "rb") as fh:
        scaler = pickle.load(fh)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck     = torch.load(checkpoint, map_location=device, weights_only=False)
    cfg    = ck.get("config", {})
    model  = SentinelGNSS(
        n_features  = cfg.get("n_features",   37),
        n_classes   = cfg.get("n_classes",     3),
        d_model     = cfg.get("d_model",      128),
        n_heads     = cfg.get("n_heads",        8),
        n_tf_layers = cfg.get("n_tf_layers",    2),
        d_ff        = cfg.get("d_ff",         512),
        lstm_hidden = cfg.get("lstm_hidden",  256),
        n_lstm_layers = cfg.get("n_lstm_layers", 2),
        dropout     = cfg.get("dropout",      0.3),
    ).to(device)
    try:
        model.load_state_dict(ck["model"])
    except RuntimeError:
        model.load_state_dict(ck["model"], strict=False)
    model.eval()

    # ── sliding windows ───────────────────────────────────────────────────────
    Xs = scaler.transform(feat[FEATURE_NAMES].values.astype(np.float32))
    n  = len(Xs)
    if n < WINDOW:
        raise ValueError(f"Only {n} epochs — need at least {WINDOW}.")

    starts  = list(range(0, n - WINDOW + 1))
    Xw      = np.stack([Xs[i:i + WINDOW] for i in starts]).astype(np.float32)
    end_idx = [s + WINDOW - 1 for s in starts]
    print(f"[info]  {n} epochs → {len(Xw)} windows")

    # ── inference ─────────────────────────────────────────────────────────────
    probs = {h: [] for h in HORIZONS}
    bs    = 512
    for i in range(0, len(Xw), bs):
        xb = torch.tensor(Xw[i:i + bs], dtype=torch.float32).to(device)
        with torch.no_grad():
            out = model(xb)
        for h in HORIZONS:
            probs[h].append(torch.softmax(out[f"logits_{h}"], dim=-1).cpu().numpy())
    probs = {h: np.concatenate(v) for h, v in probs.items()}

    # ── build predictions dataframe ───────────────────────────────────────────
    rows = []
    for w, ei in enumerate(end_idx):
        row = {"window": w, "end_epoch": ei}
        if "timestamp" in feat.columns:
            row["timestamp"] = feat["timestamp"].iloc[ei]
        for col in ("lat", "lon", "x", "y"):
            row[col] = pos[col].iloc[ei] if ei < len(pos) else np.nan
        for h in HORIZONS:
            p = probs[h][w]
            row[f"p_clean_{h}"]   = round(float(p[0]), 4)
            row[f"p_warning_{h}"] = round(float(p[1]), 4)
            row[f"p_degraded_{h}"]= round(float(p[2]), 4)
            row[f"pred_{h}"]      = CLASSES[int(p.argmax())]
        rows.append(row)

    pred_df = pd.DataFrame(rows)

    # ── save ──────────────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_csv = out_dir / f"{stem}_predictions.csv"
    pred_df.to_csv(pred_csv, index=False)
    print(f"[ok]  predictions → {pred_csv}")

    summary: dict = {
        "nmea_file"    : str(features_csv),
        "n_epochs"     : int(n),
        "window_size"  : WINDOW,
        "receiver_tier": 1,
        "status"       : "ok",
        "source"       : "UrbanNav Tokyo · Shinjuku · Trimble",
        "note"         : "Pre-processed features (zero-shot cross-city test set)",
    }
    for h in HORIZONS:
        preds = pred_df[f"pred_{h}"].value_counts().to_dict()
        summary[f"class_counts_{h}"]    = {c: int(preds.get(c, 0)) for c in CLASSES}
        summary[f"mean_p_degraded_{h}"] = round(float(pred_df[f"p_degraded_{h}"].mean()), 4)

    deg5 = pred_df.index[pred_df["pred_5s"] == "DEGRADED"].tolist()
    summary["first_degraded_window_5s"] = int(deg5[0]) if deg5 else None
    summary["predictions_csv"] = str(pred_csv)

    summ_json = out_dir / f"{stem}_summary.json"
    with open(summ_json, "w") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print(f"[ok]  summary     → {summ_json}")

    for h in HORIZONS:
        counts = summary[f"class_counts_{h}"]
        total  = sum(counts.values()) or 1
        print(f"      +{h}: CLEAN={counts['CLEAN']} "
              f"WARN={counts['WARNING']} DEG={counts['DEGRADED']} "
              f"(P̄_deg={summary[f'mean_p_degraded_{h}']:.3f})")

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--odaiba", action="store_true",
                    help="run on Tokyo Odaiba instead of Shinjuku")
    ap.add_argument("--out", default=str(ROOT / "results" / "inference"))
    ap.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    ap.add_argument("--scaler",     default=str(DEFAULT_SCALER))
    args = ap.parse_args()

    if args.odaiba:
        csv  = ROOT / "data" / "processed" / "tokyo" / "tokyo_odaiba_features.csv"
        stem = "tokyo_odaiba"
    else:
        csv  = ROOT / "data" / "processed" / "tokyo" / "tokyo_shinjuku_features.csv"
        stem = "tokyo_shinjuku"

    run(csv, stem, Path(args.out), args.checkpoint, args.scaler)


if __name__ == "__main__":
    main()
