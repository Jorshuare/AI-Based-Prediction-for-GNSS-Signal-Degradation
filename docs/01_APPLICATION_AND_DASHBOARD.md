# SENTINEL-GNSS — Application & Dashboard (Comprehensive Reference)

**What this document is:** the single, authoritative explanation of the SENTINEL-GNSS
*application* — the web dashboard, its backend, the input/“scenario” files it serves, what every
chart means (in plain language), and exactly what is required to deploy it. Every design choice is
justified.

> Companion docs: **[02_DATA_AND_MODELING.md](02_DATA_AND_MODELING.md)** (how the data and the AI
> model were built) and **[03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md)** (every
> command, option, and formula).

---

## 1. What the application is (in one paragraph)

SENTINEL-GNSS is a real-time dashboard that **predicts GNSS (GPS) signal degradation 5, 15 and 30
seconds before it happens**, and shows how an **adaptive sensor-fusion filter** keeps a vehicle
accurately located even when the satellite signal fails. It has two halves: a **Python/FastAPI
backend** that serves the real, pre-computed model outputs and streams them like a live feed, and a
**Next.js/React frontend** that visualises them with gauges, maps, charts, alerts and plain-language
status. It is aimed at both engineers (who read the metrics) and non-expert “civilian” users (who
read the plain-language panels).

**Why a dashboard at all?** A prediction is only useful if a human or system can *act* on it. The
dashboard turns abstract probabilities into an at-a-glance picture: *is the signal about to fail,
how soon, and what is the vehicle doing about it?*

---

## 2. Architecture at a glance

```
┌──────────────────────────────┐         WebSocket (live replay)        ┌───────────────────────────┐
│  Browser  (Next.js + React)  │  ◄─────────────────────────────────►   │   FastAPI backend         │
│  dashboard/client            │         REST  /api/*  (JSON)            │   dashboard/server/main.py │
│  • Live Prediction tab        │  ───────────────────────────────────►  │                            │
│  • Sensor Fusion tab          │                                        │  reads pre-computed files: │
│  • Analytics tab              │                                        │   results/inference/*.csv  │
│  • Minimalist / Extended      │                                        │   results/urbannav_*.json  │
└──────────────────────────────┘                                        └───────────────────────────┘
```

**Key design decision — the heavy AI model is NOT in the live request path.** The Transformer-LSTM
runs *offline* (on Kaggle/Colab/local), writing its predictions to `results/`. The backend simply
**replays** those real outputs over a WebSocket so the UI animates as if live. 

*Justification:* (1) reliability — a demo never hangs loading a 1.46 M-parameter model; (2) speed —
sub-millisecond responses; (3) honesty — every number on screen is a real, reproducible model
output, not a live approximation. Live inference can later be added behind a `/api/infer` endpoint
without changing the UI.

---

## 3. The backend (`dashboard/server/main.py`)

FastAPI + Uvicorn. Stateless except for an in-memory cache of the prediction CSVs.

### 3.1 REST endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | liveness + how many scenarios / whether EKF results exist |
| GET | `/api/scenarios` | list of available **prediction** runs (the Live-tab dropdown) |
| GET | `/api/predictions/{id}` | full prediction table for one run |
| GET | `/api/summary/{id}` | per-run summary (class counts, mean P, first-degraded window) |
| GET | `/api/ekf` | the offline adaptive-EKF **study** (filter comparison + severity sweep) |
| GET | `/api/fusion/sources` | the available real fusion datasets (Trimble, u-blox) |
| GET | `/api/fusion?source=trimble\|ublox` | real Tokyo fusion tracks + RMSE summary |
| WS  | `/ws` | control (`start_replay` / `stop_replay` / `ping`) + the live `epoch` stream |

### 3.2 The replay stream (WebSocket)

On `start_replay {scenario, speed}` the server walks the prediction CSV and emits one `epoch`
message per row at `speed` epochs/second. The UI receives `replay_start` (with the total length),
then a stream of `epoch` messages, then `replay_end`. Speed is user-controllable (2–60 ep/s).

*Justification:* replay decouples visual pacing from data size and faithfully reproduces a live
sensor feed, which is exactly the deployment scenario (epochs arriving over time).

### 3.3 Dependencies

`fastapi`, `uvicorn[standard]`, `pandas`, `numpy` (see `dashboard/server/requirements.txt`). It
reads the repository’s `results/` folder; it does **not** import PyTorch.

---

## 4. The frontend (`dashboard/client`)

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 · **framer-motion** (animation) ·
**react-icons** (consistent Feather icon set). All visualisations are **hand-built SVG** — no chart
library — so there are zero peer-dependency risks and every chart is fully responsive (scales to its
container via `viewBox` + a `ResizeObserver` hook).

### 4.1 Layout & navigation

- **Header** — Beihang + RCSSTEAP logos, live/offline indicator, and the **Extended ↔ Minimalist**
  toggle.
- **Three tabs:**
  1. **Live Prediction** — the streaming forecast (gauge, probabilities, alerts, trajectory,
     timeline, lead-time, plain-language status).
  2. **Sensor Fusion** — the *real* Tokyo data: the raw GNSS path vs our fused estimate vs truth,
     with a **GNSS-source dropdown** (Trimble-RTKLIB or u-blox-SPP).
  3. **Analytics** — the offline filter study (which filter wins, and when adaptive-R helps).
- **Minimalist mode** strips the dashboard down to the three essentials (gauge, class
  probabilities, alerts) so a busy user can grasp the situation in one glance; **Extended** shows
  everything. *Justification:* different audiences need different densities — an operator wants the
  headline; an engineer wants the detail.

### 4.2 Source-of-truth modules (`lib/`)

- `colors.ts` — the Beihang palette and the CLEAN/WARNING/DEGRADED semantics (one place).
- `types.ts` — the exact TypeScript shape of every backend response.
- `api.ts` — REST + WebSocket client.
- `icons.ts` — the curated react-icons set.
- `ui.tsx` — reusable primitives: `Card`, `SectionTitle`, `Tooltip`, `InfoDot`, `AnimatedNumber`,
  and the `useElementWidth` responsive hook.

This enforces **Separation of Concerns** (data/types/UI are distinct) and **DRY** (colours, types,
and API calls each defined once).

---

## 5. Every chart, in plain language (with the “why”)

Each panel has an **ⓘ info dot**; hovering it gives a one-sentence civilian explanation. Summary:

| Panel | What it shows | Plain-language meaning |
|---|---|---|
| **Plain-language status** | A coloured sentence + icon | “GNSS is healthy / dropping / unreliable, and here is what the vehicle is doing.” The fastest way to understand the situation with zero jargon. |
| **Signal gauge** | A dial of P(DEGRADED) at the chosen horizon | The chance GPS becomes unreliable within +5/15/30 s. Green safe, amber patchy, red danger. |
| **Class probabilities** | Three bars: CLEAN / WARNING / DEGRADED | How likely each signal state is right now. They sum to 100 %. |
| **Alerts & Notifications** | A live feed of warnings | Automatic messages when degradation is *likely* (within 15 s) or *imminent* (within 5 s), with a timestamp. |
| **Early-warning lead time** | Warning epoch → onset epoch | Confirms the model’s usefulness: the long-range (+30 s) forecast raised the alarm N seconds *before* the near-term (+5 s) forecast said “imminent.” That N is the head-start the driver gets. |
| **Live KPIs** | Six tiles | Epochs processed, mean/peak degradation, CLEAN vs DEGRADED counts, first-degraded epoch. |
| **Vehicle trajectory** | The route, dots coloured by risk | Where the car drove, with each spot coloured by how risky GPS was there. |
| **P(DEGRADED) timeline** | Three lines (one per horizon) | The history of the degradation probability. Hover anywhere to read exact values; dashed lines are the warning thresholds. |
| **Sensor Fusion — trajectory** | Truth vs raw GNSS vs aided-EKF | The red line is the raw satellite receiver (jumps wildly in the canyon); the blue line is our fused estimate; green is the true path. Closer to green is better. |
| **Sensor Fusion — accuracy bars** | Blocked-segment RMSE per filter | Average position error (metres) during the hard, sky-blocked moments. Shorter = better. |
| **Analytics — filter comparison** | Blocked-segment RMSE bars | Which positioning filter best survives a GPS blackout on real Tokyo data. |
| **Analytics — severity sweep** | Three lines vs multipath severity | *When* it pays to distrust the satellites. With sensor aiding, keeping GPS (fixed-R) stays best across realistic conditions. |

---

## 6. The “scenario” input files — what they are, how we got them, what they contain

The dashboard is driven by two kinds of **real** input, both produced offline and stored in
`results/`.

### 6.1 Live-prediction scenario — `A_log_0000` (real Beihang field data)

- **What it is:** the model’s degradation forecast along a real drive we collected ourselves.
- **How we got it:** field collection at **Beihang University, Beijing** under *Scenario A
  (instant blockage / degraded data)* — a receiver logged raw **NMEA** sentences while driving
  through abrupt sky-blockage (e.g. under structures). See
  [02_DATA_AND_MODELING.md](02_DATA_AND_MODELING.md) §2 for the collection protocol.
- **How it became a dashboard file:** `src/models/inference.py` reads the NMEA, extracts the 37
  engineered features, runs the trained Transformer-LSTM, and writes
  `results/inference/A_log_0000_predictions.csv` (one row per 30-second window) plus
  `A_log_0000_summary.json`.
- **What each row contains:** `window, end_epoch, timestamp, lat, lon, x, y,` then for each horizon
  `p_clean_Hs, p_warning_Hs, p_degraded_Hs, pred_Hs` (H ∈ {5,15,30}). 
  - *Layman example:* row 63 reads `p_degraded_5s = 0.83, pred_5s = DEGRADED` — i.e. *“five seconds
    from this point, the model is 83 % sure the GPS will be unreliable.”*
- **Add more:** run inference on any NMEA file and it auto-appears in the dropdown (see Runbook §6).

### 6.2 Sensor-fusion scenarios — `UrbanNav Tokyo` (Trimble & u-blox)

- **What it is:** a *fully real* demonstration that fusing GNSS with the car’s motion sensors keeps
  it located through real urban canyon blackouts.
- **Where the data comes from:** the public, peer-reviewed **UrbanNav** dataset (Hong Kong PolyU),
  drive *Tokyo / Shinjuku*. We use four real streams from it:
  - `rover_trimble.obs` / `rover_ublox.obs` — raw satellite measurements (RINEX) from two real
    receivers.
  - `base.nav` — broadcast satellite orbit/clock data (ephemeris).
  - `imu.csv` — real 100 Hz inertial measurements (accelerometer + gyroscope) **and wheel speed**.
  - `reference.csv` — the **ground truth** path from a survey-grade SPAN-INS system (centimetre
    accuracy).
- **How we turned raw measurements into a GNSS position track** (this is the crucial step):
  - **Trimble (gold standard):** processed with **RTKLIB** (`rnx2rtkp`, single-point mode,
    GPS+GLONASS). Result: median **2.7 m** horizontal error, with realistic NLOS spikes to 100 m+.
  - **u-blox:** processed with our own georinex-based GPS-only single-point engine
    (`src/models/spp_rinex.py`). Result: median **14 m** (a cheaper, noisier receiver).
- **How it became a dashboard file:** `src/models/ekf_urbannav_runner.py --real` fuses that real
  GNSS with the real IMU + wheel odometry against the real truth and writes
  `results/urbannav_ekf_real_{trimble,ublox}.json` + `_tracks.npz`.
- **What it contains:** the truth path, the raw GNSS path, our fused path, the per-filter RMSE
  (overall and during blockages), satellite counts, and the degradation flags.
  - *Layman example:* during the blocked moments, the raw Trimble GNSS is off by **47 m** on
    average; our aided filter cuts that to **24 m** — a **+49 %** improvement.

> **Why two receivers?** It demonstrates the method works across hardware tiers — a survey receiver
> (Trimble) and a consumer receiver (u-blox) — which is exactly the generalisation a reviewer asks
> for.

---

## 7. Deploying the application

### 7.1 What is required

| Component | Needs |
|---|---|
| Backend | Python 3.11+, the four packages in `dashboard/server/requirements.txt`, and a populated `results/` folder (predictions + fusion outputs). |
| Frontend | Node 18+, `npm install` in `dashboard/client`. In China, add `--registry=https://registry.npmmirror.com`. |
| Wiring | The frontend reads `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`) and `NEXT_PUBLIC_WS_URL` (default `ws://localhost:8000/ws`). |

### 7.2 Local run (development)

```bash
# Terminal 1 — backend
cd dashboard/server && pip install -r requirements.txt && python main.py     # :8000

# Terminal 2 — frontend
cd dashboard/client && npm install && npm run dev                            # :3000
```
Open **http://localhost:3000**, pick a dataset, press **Play**.

### 7.3 Production process

1. **Backend:** run Uvicorn behind a process manager / container:
   `uvicorn main:app --host 0.0.0.0 --port 8000` (add `--workers N` for load). Mount the `results/`
   folder read-only. Put it behind HTTPS (the UI auto-upgrades `ws→wss`).
2. **Frontend:** `npm run build && npm run start` (Next standalone server) **or** deploy to Vercel.
   Set `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_WS_URL` to the backend’s public URL.
3. **CORS:** the backend currently allows all origins; lock this to the frontend domain for
   production.
4. **Containerisation (optional):**
   ```dockerfile
   # backend
   FROM python:3.11-slim
   WORKDIR /app; COPY . .
   RUN pip install -r dashboard/server/requirements.txt
   CMD ["uvicorn","dashboard.server.main:app","--host","0.0.0.0","--port","8000"]
   ```

### 7.4 Refreshing the data

The dashboard shows whatever is in `results/`. To update it, re-run the offline pipeline
(inference and/or the fusion runner) — no UI change needed. See
[03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md).

### 7.5 Performance & footprint

Replay + SVG rendering is trivial (sub-millisecond backend, 60 fps UI). The only heavy step is the
*offline* model inference (~0.04 ms/sample on GPU; see Data & Modeling doc), which never touches the
live server. The app runs comfortably on a laptop or a small cloud instance.

---

## 8. Why these technology choices (justification summary)

| Choice | Why |
|---|---|
| FastAPI | Async, WebSocket-native, automatic validation, tiny footprint. |
| Replay architecture | Reliable, fast, fully-real data; decouples UI from the heavy model. |
| Next.js + React 19 | Modern, typed, deploy-anywhere (Vercel/Node/Docker). |
| Hand-built SVG charts | Zero dependency risk with React 19, fully responsive, pixel-perfect, brandable. |
| framer-motion | Natural, physics-based motion for alerts/cards/tabs without hand-rolled animation. |
| react-icons (Feather) | One consistent, legible icon language across the app. |
| Beihang palette on white | Matches the papers/branding; high contrast and accessible. |
| Minimalist toggle | Serves both expert and civilian audiences from one app. |
