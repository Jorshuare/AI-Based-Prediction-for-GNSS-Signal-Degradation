"""
ensemble_compare.py — Model-family & ensemble comparison + "is memory needed?" diagnostics.

Single source of truth for E8–E10 so Kaggle and Colab notebooks stay identical: both call
`python -m src.models.ensemble_compare`. Results → results/ensemble_comparison.json (+ a
markdown block appended to results/RUN_SUMMARY.md if present).

  E8  Ensembles: DL (Transformer-LSTM) + XGBoost via soft-vote and stacking,
      reported IN-DOMAIN (test) and CROSS-CITY (Tokyo Shinjuku).
  E9  Persistence baseline: predict the t+h label from the CURRENT (t+0) label.
      Quantifies how much the future is already determined by the present
      (the core of the "do we even need memory?" question).
  E10 Per-horizon gap: DL vs XGBoost vs RandomForest Macro-F1 at +5/+15/+30 s.

All experiments are wrapped so one failure does not abort the rest.
"""
from __future__ import annotations
import json
import os
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
import joblib

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
WND = ROOT / "data" / "processed" / "windows_no_smote"
SCALER = ROOT / "data" / "processed" / "scaler.pkl"
TOKYO_CSV = ROOT / "data" / "processed" / "tokyo" / "tokyo_shinjuku_features.csv"
HORIZONS = ["5s", "15s", "30s"]

FEATURE_NAMES = [
    "alt", "baseline_sats", "clock_bias", "cnr_trend", "cnr_variance", "cycle_slips",
    "dop_ratio", "elevation_violations", "fix_continuity", "fix_transitions", "gdop",
    "hdop", "hdop_delta", "iono_delay", "lat_std", "lon_std", "max_cnr", "mean_cnr",
    "min_cnr", "multipath", "num_satellites", "pdop", "pdop_delta", "position_variance",
    "receiver_tier", "residual_mean", "residual_std", "sat_drop_rate", "sat_mean",
    "sat_min", "sat_visibility", "solution_age", "solution_status", "std_cnr",
    "tropo_delay", "vdop", "cnr_available",
]


def macro(yt, yp):
    return float(f1_score(yt, yp, average="macro", zero_division=0))


def deg_f1(yt, yp):
    return float(f1_score(yt, yp, average=None, labels=[0, 1, 2], zero_division=0)[2])


# ─── DL model ─────────────────────────────────────────────────────────────────
def load_dl():
    import torch
    import sys
    sys.path.insert(0, str(ROOT))
    from src.models.transformer_lstm import SentinelGNSS
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(RESULTS / "models" / "checkpoints" / "checkpoint_best.pt",
                    map_location=dev, weights_only=False)
    cfg = ck.get("config", {})
    m = SentinelGNSS(
        n_features=cfg.get("n_features", 37), n_classes=cfg.get("n_classes", 3),
        d_model=cfg.get("d_model", 128), n_heads=cfg.get("n_heads", 8),
        n_tf_layers=cfg.get("n_tf_layers", 2), d_ff=cfg.get("d_ff", 512),
        lstm_hidden=cfg.get("lstm_hidden", 256), n_lstm_layers=cfg.get("n_lstm_layers", 2),
        dropout=cfg.get("dropout", 0.3),
    ).to(dev)
    m.load_state_dict(ck["model"])
    m.eval()
    return m, dev


def dl_probs(model, dev, X, horizon, bs=512):
    import torch
    out = []
    for i in range(0, len(X), bs):
        xb = torch.tensor(X[i:i + bs], dtype=torch.float32).to(dev)
        with torch.no_grad():
            o = model(xb)
        out.append(torch.softmax(o[f"logits_{horizon}"], dim=-1).cpu().numpy())
    return np.concatenate(out)


# ─── Tokyo cross-city windows ─────────────────────────────────────────────────
def build_tokyo(t_steps):
    import pandas as pd
    if not TOKYO_CSV.exists() or not SCALER.exists():
        return None, None
    df = pd.read_csv(TOKYO_CSV, low_memory=False)
    with open(SCALER, "rb") as fh:
        scaler = pickle.load(fh)
    for c in FEATURE_NAMES:
        if c not in df.columns:
            df[c] = 0.0
    Xs = scaler.transform(df[FEATURE_NAMES].fillna(0).values.astype(np.float32))
    y = df["label"].values.astype(int)
    wx, wy = [], []
    for i in range(t_steps - 1, len(Xs)):
        wx.append(Xs[i - t_steps + 1:i + 1])
        wy.append(y[i])
    return np.asarray(wx, dtype=np.float32), np.asarray(wy, dtype=int)


def main():
    res = {}
    try:
        from xgboost import XGBClassifier
        HAS_XGB = True
    except Exception:
        HAS_XGB = False

    tr = np.load(WND / "train.npz")
    va = np.load(WND / "val.npz")
    te = np.load(WND / "test.npz")
    Xtr, Xva, Xte = tr["X"], va["X"], te["X"]
    T = Xtr.shape[1]
    Xtrf = Xtr.reshape(len(Xtr), -1)
    Xvaf = Xva.reshape(len(Xva), -1)
    Xtef = Xte.reshape(len(Xte), -1)

    model, dev = load_dl()
    Xtok, ytok = build_tokyo(T)
    Xtokf = Xtok.reshape(len(Xtok), -1) if Xtok is not None else None

    # ── E8 + E10 : per-horizon model family + ensembles ──────────────────────
    res["E8_ensemble"] = {}
    res["E10_horizon_gap"] = {}
    for h in HORIZONS:
        ytr, yva, yte = tr[f"y_{h}"], va[f"y_{h}"], te[f"y_{h}"]
        row = {}
        try:
            # DL
            dl_te = dl_probs(model, dev, Xte, h)
            row["dl"] = round(macro(yte, dl_te.argmax(1)), 4)
            row["dl_deg"] = round(deg_f1(yte, dl_te.argmax(1)), 4)
            # RandomForest
            rf = RandomForestClassifier(200, class_weight="balanced", n_jobs=-1,
                                        random_state=42).fit(Xtrf, ytr)
            rf_te = rf.predict_proba(Xtef)
            row["rf"] = round(macro(yte, rf_te.argmax(1)), 4)
            # XGBoost
            if HAS_XGB:
                classes, counts = np.unique(ytr, return_counts=True)
                w = {int(c): len(ytr) / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
                sw = np.array([w[int(t)] for t in ytr])
                xgb = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, n_jobs=-1,
                                    eval_metric="mlogloss", random_state=42)
                xgb.fit(Xtrf, ytr, sample_weight=sw)
                # Save the +5s XGBoost model for ensemble inference
                if h == "5s":
                    joblib.dump(xgb, RESULTS / "ensemble_xgb_model.joblib")
                    print("[saved] results/ensemble_xgb_model.joblib")
                xgb_te = xgb.predict_proba(Xtef)
                row["xgb"] = round(macro(yte, xgb_te.argmax(1)), 4)
                # E8a soft-vote (mean of DL + XGB)
                sv_te = (dl_te + xgb_te) / 2.0
                row["softvote"] = round(macro(yte, sv_te.argmax(1)), 4)
                row["softvote_deg"] = round(deg_f1(yte, sv_te.argmax(1)), 4)
                # E8b stacking (LogReg meta on val: [DL|XGB] probs)
                dl_va = dl_probs(model, dev, Xva, h)
                xgb_va = xgb.predict_proba(Xvaf)
                meta = LogisticRegression(max_iter=1000, class_weight="balanced")
                meta.fit(np.hstack([dl_va, xgb_va]), yva)
                stk_te = meta.predict(np.hstack([dl_te, xgb_te]))
                row["stack"] = round(macro(yte, stk_te), 4)
                row["stack_deg"] = round(deg_f1(yte, stk_te), 4)
                # ── cross-city (Tokyo) for the +5s headline ──
                if Xtok is not None and h == "5s":
                    dl_tok = dl_probs(model, dev, Xtok, h)
                    xgb_tok = xgb.predict_proba(Xtokf)
                    sv_tok = (dl_tok + xgb_tok) / 2.0
                    stk_tok = meta.predict(np.hstack([dl_tok, xgb_tok]))
                    res["E8_ensemble"]["cross_city_tokyo_5s"] = {
                        "dl": round(macro(ytok, dl_tok.argmax(1)), 4),
                        "xgb": round(macro(ytok, xgb_tok.argmax(1)), 4),
                        "softvote": round(macro(ytok, sv_tok.argmax(1)), 4),
                        "stack": round(macro(ytok, stk_tok), 4),
                        "dl_deg": round(deg_f1(ytok, dl_tok.argmax(1)), 4),
                        "xgb_deg": round(deg_f1(ytok, xgb_tok.argmax(1)), 4),
                        "softvote_deg": round(deg_f1(ytok, sv_tok.argmax(1)), 4),
                        "stack_deg": round(deg_f1(ytok, stk_tok), 4),
                    }
            res["E8_ensemble"][h] = row
            res["E10_horizon_gap"][h] = {
                "dl": row.get("dl"), "rf": row.get("rf"), "xgb": row.get("xgb"),
                "best_single": max((row.get(k, 0) for k in ("dl", "rf", "xgb"))),
            }
            print(f"  [{h}] " + "  ".join(f"{k}={v}" for k, v in row.items()))
        except Exception as e:  # noqa
            res["E8_ensemble"][h] = {"error": str(e)}
            print(f"  [{h}] ERROR {e}")

    # ── E9 : persistence baseline (predict t+h from current t+0 label) ───────
    res["E9_persistence"] = {}
    try:
        y0 = te["y_0s"]
        for h in HORIZONS:
            yh = te[f"y_{h}"]
            res["E9_persistence"][h] = {
                "persistence_macro_f1": round(macro(yh, y0), 4),
                "persistence_accuracy": round(float((yh == y0).mean()), 4),
                "label_change_rate": round(float((yh != y0).mean()), 4),
            }
        print("  E9 persistence:", res["E9_persistence"])
    except Exception as e:  # noqa
        res["E9_persistence"] = {"error": str(e)}

    # ── interpretation note ───────────────────────────────────────────────────
    res["_notes"] = {
        "E8": "Static ensembles (soft-vote / stacking) of DL+XGB; compare in-domain vs Tokyo. "
              "If neither dominates both regimes, domain-aware/confidence-gated fusion is needed.",
        "E9": "persistence_accuracy = how often the t+h label equals the current label. "
              "High value ⇒ the present already determines the future ⇒ limited room for "
              "'memory'. label_change_rate rising with horizon ⇒ longer horizons need temporal modelling.",
        "E10": "Per-horizon Macro-F1 by model family; does the DL–tree gap shrink at longer horizons?",
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "ensemble_comparison.json"
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2, default=str)
    print(f"\n[saved] {out}")

    # Append a section to RUN_SUMMARY.md if it exists
    rs = RESULTS / "RUN_SUMMARY.md"
    if rs.exists():
        lines = ["\n\n## E8–E10 — Ensemble & Memory Diagnostics\n"]
        lines.append("| Horizon | DL | RF | XGB | SoftVote | Stack |")
        lines.append("|---|---|---|---|---|---|")
        for h in HORIZONS:
            r = res["E8_ensemble"].get(h, {})
            lines.append(f"| +{h} | {r.get('dl','-')} | {r.get('rf','-')} | "
                         f"{r.get('xgb','-')} | {r.get('softvote','-')} | {r.get('stack','-')} |")
        cc = res["E8_ensemble"].get("cross_city_tokyo_5s")
        if cc:
            lines.append("\n**Cross-city (Tokyo, +5s):** "
                         f"DL={cc['dl']} (DEG {cc['dl_deg']}), XGB={cc['xgb']} (DEG {cc['xgb_deg']}), "
                         f"SoftVote={cc['softvote']}, Stack={cc['stack']}")
        if "error" not in res["E9_persistence"]:
            lines.append("\n**E9 persistence (present→future):**")
            for h in HORIZONS:
                p = res["E9_persistence"][h]
                lines.append(f"- +{h}: persistence acc={p['persistence_accuracy']}, "
                             f"label-change rate={p['label_change_rate']}")
        with open(rs, "a") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"[appended] E8–E10 section to {rs}")

    return res


if __name__ == "__main__":
    main()
