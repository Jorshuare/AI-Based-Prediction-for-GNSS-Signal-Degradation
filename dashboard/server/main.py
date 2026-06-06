"""
SENTINEL-GNSS Dashboard Backend — FastAPI + WebSocket.

Design: the heavy Transformer-LSTM is NOT loaded into the live server (slow, fragile).
Instead the server reads the REAL pre-computed inference outputs in results/inference/
and the EKF study in results/urbannav_ekf.json, and REPLAYS predictions over a WebSocket
so the UI animates as if live. This is fast, reliable, fully real data, and demo-proof.

Optional: POST /api/infer runs the real model on an NMEA file via subprocess (best-effort).

Endpoints
---------
GET  /api/health                  - liveness + what data is available
GET  /api/scenarios               - list available prediction runs
GET  /api/predictions/{scenario}  - full prediction table for a run
GET  /api/summary/{scenario}      - summary json for a run
GET  /api/ekf                     - UrbanNav adaptive-EKF results (sweep + comparison)
WS   /ws                          - control + live replay stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinel")

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
INFER_DIR = RESULTS / "inference"
EKF_JSON = RESULTS / "urbannav_ekf.json"

app = FastAPI(title="SENTINEL-GNSS Dashboard", version="2.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Data access (cached)
# --------------------------------------------------------------------------- #
_cache: dict[str, object] = {}


def list_scenarios() -> list[dict]:
    """Discover prediction runs from results/inference/*_predictions.csv."""
    out = []
    if INFER_DIR.exists():
        for csv in sorted(INFER_DIR.glob("*_predictions.csv")):
            stem = csv.name.replace("_predictions.csv", "")
            summary = INFER_DIR / f"{stem}_summary.json"
            meta = {}
            if summary.exists():
                try:
                    meta = json.loads(summary.read_text())
                except Exception:
                    meta = {}
            out.append({
                "id": stem,
                "n_epochs": meta.get("n_epochs"),
                "mean_p_degraded_5s": meta.get("mean_p_degraded_5s"),
                "source": meta.get("nmea_file", stem),
            })
    return out


def load_predictions(scenario: str) -> list[dict]:
    key = f"pred::{scenario}"
    if key in _cache:
        return _cache[key]  # type: ignore
    csv = INFER_DIR / f"{scenario}_predictions.csv"
    if not csv.exists():
        raise HTTPException(404, f"Unknown scenario: {scenario}")
    df = pd.read_csv(csv)
    # JSON-safe records (replace NaN/inf).
    df = df.where(pd.notnull(df), None)
    records = json.loads(df.to_json(orient="records"))
    _cache[key] = records
    return records


def load_summary(scenario: str) -> dict:
    js = INFER_DIR / f"{scenario}_summary.json"
    if not js.exists():
        raise HTTPException(404, f"No summary for: {scenario}")
    return json.loads(js.read_text())


def load_ekf() -> dict:
    if not EKF_JSON.exists():
        raise HTTPException(404, "EKF results not found; run ekf_urbannav_runner first")
    return json.loads(EKF_JSON.read_text())


FUSION_SOURCES = {
    "trimble": "UrbanNav Tokyo · Trimble (RTKLIB)",
    "ublox": "UrbanNav Tokyo · u-blox (SPP)",
}


def load_fusion(source: str = "trimble") -> dict:
    """Real UrbanNav fusion tracks (downsampled) + RMSE summary, for the Fusion tab."""
    import numpy as np
    if source not in FUSION_SOURCES:
        raise HTTPException(400, f"unknown source: {source}")
    tracks = RESULTS / f"urbannav_ekf_real_{source}_tracks.npz"
    summ = RESULTS / f"urbannav_ekf_real_{source}.json"
    if not tracks.exists() or not summ.exists():
        raise HTTPException(404, f"Run `python -m src.models.ekf_urbannav_runner --real` ({source})")
    z = np.load(tracks)
    n = len(z["truth"])
    step = max(1, n // 1200)                      # cap ~1200 points for the browser
    sl = slice(0, n, step)

    def xy(a):
        return [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in a[sl]]

    summary = json.loads(summ.read_text())
    return {
        "summary": summary,
        "truth": xy(z["truth"]),
        "gnss": xy(z["gnss"]),
        "aided_fixed": xy(z["aided_fixed"]),
        "aided_adapt": xy(z["aided_adapt"]),
        "is_degraded": [bool(b) for b in z["is_degraded"][sl]],
        "nsat": [int(s) for s in z["nsat"][sl]],
        "p_degraded": [round(float(p), 3) for p in z["p_degraded"][sl]],
    }


# --------------------------------------------------------------------------- #
# REST
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "scenarios": len(list_scenarios()),
        "ekf_available": EKF_JSON.exists(),
    }


@app.get("/api/scenarios")
def scenarios():
    return list_scenarios()


@app.get("/api/predictions/{scenario}")
def predictions(scenario: str):
    return load_predictions(scenario)


@app.get("/api/summary/{scenario}")
def summary(scenario: str):
    return load_summary(scenario)


@app.get("/api/ekf")
def ekf():
    return load_ekf()


@app.get("/api/fusion/sources")
def fusion_sources():
    return [{"id": k, "label": v} for k, v in FUSION_SOURCES.items()]


@app.get("/api/fusion")
def fusion(source: str = "trimble"):
    return load_fusion(source)


# --------------------------------------------------------------------------- #
# WebSocket: live replay
# --------------------------------------------------------------------------- #
class Hub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)


hub = Hub()


async def replay(ws: WebSocket, scenario: str, speed: float = 10.0):
    """Stream predictions one epoch at a time at `speed` epochs/sec."""
    try:
        records = load_predictions(scenario)
    except HTTPException as e:
        await ws.send_json({"type": "error", "message": e.detail})
        return

    delay = 1.0 / max(speed, 0.5)
    await ws.send_json({"type": "replay_start", "scenario": scenario, "total": len(records)})
    for i, rec in enumerate(records):
        if ws not in hub.clients:
            break
        await ws.send_json({"type": "epoch", "index": i, "total": len(records), "data": rec})
        await asyncio.sleep(delay)
    await ws.send_json({"type": "replay_end", "scenario": scenario})


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await hub.connect(ws)
    task: Optional[asyncio.Task] = None
    logger.info("WS connected (%d clients)", len(hub.clients))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            kind = msg.get("type")
            if kind == "ping":
                await ws.send_json({"type": "pong"})
            elif kind == "start_replay":
                if task and not task.done():
                    task.cancel()
                scenario = msg.get("scenario") or (list_scenarios() or [{}])[0].get("id")
                speed = float(msg.get("speed", 10.0))
                if scenario:
                    task = asyncio.create_task(replay(ws, scenario, speed))
                else:
                    await ws.send_json({"type": "error", "message": "no scenarios available"})
            elif kind == "stop_replay":
                if task and not task.done():
                    task.cancel()
                await ws.send_json({"type": "replay_stopped"})
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa
        logger.warning("WS error: %s", e)
    finally:
        if task and not task.done():
            task.cancel()
        hub.disconnect(ws)
        logger.info("WS disconnected (%d clients)", len(hub.clients))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
