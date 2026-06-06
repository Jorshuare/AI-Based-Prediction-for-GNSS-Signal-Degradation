# SENTINEL-GNSS Dashboard

Real-time GNSS degradation prediction + adaptive EKF analytics. FastAPI backend streams the
**real** pre-computed inference outputs over a WebSocket; a Next.js (React 19, Tailwind 4)
frontend animates them. Pure-SVG visualisations → zero chart/map dependency risk, works offline.

```
Browser (Next.js)  ──WS──►  FastAPI  ──reads──►  results/inference/*_predictions.csv
       ▲                       │                  results/urbannav_ekf.json
       └────── REST /api ───────┘
```

## What it shows

- **Live signal gauge** — P(DEGRADED) at +5 / +15 / +30 s, colour-coded (green/amber/red).
- **Class probabilities** — CLEAN / WARNING / DEGRADED bars for the selected horizon.
- **Alert centre** — auto CRITICAL (P>0.8 @ +5 s) / WARNING (P>0.6 @ +15 s) notifications.
- **Trajectory map** — vehicle path coloured by risk, animated head marker (self-contained SVG).
- **P(DEGRADED) timeline** — all three horizons streaming, with threshold lines.
- **EKF analytics** — blocked-segment RMSE by filter (aided EKF wins at 6.4 m) + severity sweep.
- **Live KPIs** — epochs streamed, mean/peak P(degraded), CLEAN/DEGRADED counts.

## Run it (two terminals)

**1 — Backend** (needs the repo's Python env with the results folder populated):
```bash
cd dashboard/server
pip install -r requirements.txt          # fastapi, uvicorn, pandas, numpy
python main.py                            # serves on http://localhost:8000
```
Check: `curl http://localhost:8000/api/health` → `{"status":"ok","scenarios":1,...}`

**2 — Frontend**:
```bash
cd dashboard/client
npm install
npm run dev                               # http://localhost:3000
```

Open **http://localhost:3000**, pick a scenario, press **▶ Play**. Predictions stream in at the
chosen rate (epochs/sec slider); the gauge, map, timeline, KPIs and alerts update live.

> Frontend talks to the backend at `http://localhost:8000` by default. Override with
> `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_WS_URL` env vars if hosting elsewhere.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + data availability |
| GET | `/api/scenarios` | list prediction runs in `results/inference/` |
| GET | `/api/predictions/{id}` | full prediction table for a run |
| GET | `/api/summary/{id}` | per-run summary JSON |
| GET | `/api/ekf` | UrbanNav adaptive-EKF results (filter comparison + sweep) |
| WS  | `/ws` | control (`start_replay`/`stop_replay`/`ping`) + live `epoch` stream |

## Adding more scenarios

Run inference on any NMEA file; the dashboard auto-discovers the output:
```bash
python -m src.models.inference --nmea "data/raw/scenarios/Degraded data/A/log_0000.nmea" --ekf
# -> results/inference/<stem>_predictions.csv  (appears in the scenario dropdown)
```

## Design notes (SoC / DRY)

- `lib/` — single source of truth: `colors.ts` (Beihang palette), `types.ts` (backend contract),
  `api.ts` (REST + WS client).
- `components/` — one focused, reusable component per visualisation; no business logic.
- `app/dashboard.tsx` — orchestration only (WebSocket lifecycle + state), composes components.
- Backend keeps the heavy model OUT of the request path: it replays real saved outputs, so the
  UI is fast and demo-proof. Live model inference can be added later behind `/api/infer`.
