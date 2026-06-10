# SENTINEL-GNSS — Commercial Deployment Guide

**What this document is:** a practical, step-by-step plan for taking SENTINEL-GNSS from a research
prototype to a commercial product — the deployment options, the **free vs paid** packaging, the
setup and configuration for each, the costs/feasibility, and what still needs to be built. Every
recommendation is justified, and the honest gaps are flagged.

> Companion docs: **[01_APPLICATION_AND_DASHBOARD.md](01_APPLICATION_AND_DASHBOARD.md)** (the app),
> **[02_DATA_AND_MODELING.md](02_DATA_AND_MODELING.md)** (the science),
> **[03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md)** (commands & formulas).

---

## 1. Feasibility at a glance

| Question | Answer |
|---|---|
| Is the core technology proven? | **Yes** — cross-city 0.89 Macro-F1 / 0.90 DEGRADED (ensemble); real Tokyo fusion +49 %. |
| Is it computationally cheap to run? | **Yes** — 0.038 ms/sample inference (GPU), 17.8 MB model, sub-ms filter; runs on a laptop or a Jetson. |
| What is genuinely production-ready today? | The **offline pipeline**, the **dashboard** (backend + frontend), and the **inference CLI**. |
| What must be built for a paid product? | **Live inference service, authentication, multi-tenancy, billing, fleet management, monitoring** (see §7). |
| Realistic time-to-MVP-SaaS | ~**6–10 engineer-weeks** on top of what exists (§7 roadmap). |

**Verdict:** the science and the single-tenant application are ready to demo and to pilot. A paid,
multi-customer SaaS requires a focused but standard productionisation sprint — no research risk
remains.

---

## 2. What we already have (deployable assets)

- **Prediction model** — trained Transformer-LSTM + XGBoost ensemble (`results/models/…`,
  `ensemble_xgb_model.joblib`); ~0.04 ms/sample, 17.8 MB.
- **Inference CLI** — `src/models/inference.py` (NMEA → predictions → optional ensemble + EKF).
- **Sensor-fusion engine** — `src/models/ekf_9state.py` + runner (odometry/NHC/ZUPT, adaptive R).
- **Dashboard** — FastAPI backend + Next.js frontend, fully responsive, brandable.
- **GNSS positioning** — RTKLIB integration + a pure-Python SPP fallback.

*Justification:* every layer of the product (predict → fuse → visualise) already exists and is
tested end-to-end; commercialisation is packaging + operations, not new R&D.

---

## 3. Deployment options (choose by customer type)

| Option | Best for | Pros | Cons |
|---|---|---|---|
| **A. Self-hosted (on-prem / private cloud)** | OEMs, defence, privacy-sensitive fleets | Full data control, one-time cost, no per-seat fees | Customer runs the ops |
| **B. Managed cloud (we host)** | Fleet operators, logistics, mobility startups | Zero ops for the customer, easy scaling, telemetry | Recurring infra cost, data leaves premises |
| **C. Edge / embedded (in-vehicle)** | Autonomous vehicles, robotaxis, drones | Real-time, offline-capable, no network dependency | Per-unit integration, hardware constraints |
| **D. SaaS multi-tenant** | Many small customers (apps, surveyors) | Lowest unit cost, self-serve onboarding | Needs full multi-tenancy + billing (§7) |

*Recommended go-to-market:* start with **B (managed cloud pilots)** to prove value with low customer
friction, while offering **C (edge SDK)** to the AV/robotics segment that needs on-device real-time.
**D (SaaS)** follows once §7 is built.

---

## 4. Free vs Paid packaging

A classic **open-core** model — justification: it drives adoption and academic credibility (the
research is published) while monetising the operational, scale, and support layers that enterprises
actually pay for.

### 4.1 Feature matrix

| Capability | **Free / Community** | **Pro** | **Enterprise** |
|---|---|---|---|
| Prediction model + inference CLI | ✅ | ✅ | ✅ |
| Adaptive EKF fusion | ✅ | ✅ | ✅ |
| Single-user dashboard (self-host) | ✅ | ✅ | ✅ |
| Replay of pre-computed runs | ✅ | ✅ | ✅ |
| **Live streaming inference service** | — | ✅ | ✅ |
| Hosted / managed deployment | — | ✅ (shared) | ✅ (dedicated/VPC) |
| Multi-vehicle **fleet view** | — | up to N | unlimited |
| Authentication, roles, audit log | — | ✅ | ✅ + SSO/SAML |
| Alerting integrations (SMS/Slack/webhook) | — | ✅ | ✅ |
| Receiver tiers / custom thresholds | tier 0 | 0–3 | 0–3 + custom |
| Model retraining on customer data | — | — | ✅ |
| SLA + priority support | community | business hours | 24/7 + on-site |
| Data residency / on-prem | self-host | — | ✅ |

### 4.2 Indicative pricing logic (not final numbers)
- **Free:** £0 — Apache/MIT-style licence on the model + CLI + single-user dashboard. *Why free:*
  adoption, citations, talent funnel; the research is already public.
- **Pro:** per-vehicle/month or per-seat — hosted live inference + fleet + alerts. *Why paid:* we
  carry the ops, scaling, and uptime.
- **Enterprise:** annual contract — dedicated/VPC or on-prem, SSO, custom retraining, SLA. *Why
  paid:* data-residency, integration, and support are the real enterprise costs.

*Justification for open-core vs fully-paid:* GNSS/autonomy buyers distrust black boxes; an open,
citable core builds the trust that closes enterprise deals, while the paid tier captures the
genuinely expensive parts (operations, scale, support, compliance).

---

## 5. Step-by-step setup per tier

### 5.1 Free / Community (self-host, single user)
1. Clone the repo; create the Python env; `pip install -r requirements.txt` and
   `dashboard/server/requirements.txt`.
2. Provide a trained checkpoint (ship a default, or train per
   [03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md) §4).
3. Generate at least one run: `python -m src.models.inference --nmea <file> --ensemble --ekf`.
4. Start backend (`python dashboard/server/main.py`) and frontend (`npm run build && npm start`).
5. Done — browse `http://localhost:3000`.

### 5.2 Pro (managed cloud)
1. **Containerise** backend and frontend (Dockerfiles in
   [01_APPLICATION_AND_DASHBOARD.md](01_APPLICATION_AND_DASHBOARD.md) §7.3).
2. **Add a live inference service** (§7.1) behind `/api/infer` so streams are scored in real time
   (not just replayed).
3. **Deploy** to a managed platform (e.g. cloud Run / ECS / a small k8s): backend + inference as
   services, frontend on a CDN/Vercel.
4. **Configure** `NEXT_PUBLIC_API_BASE`/`WS_URL`, restrict CORS to the frontend domain, terminate
   TLS (the UI auto-uses `wss`).
5. **Add auth** (§7.2) and **alerting webhooks**.
6. **Onboard** a customer by pointing their receiver/telemetry feed at the inference endpoint.

### 5.3 Enterprise (dedicated / on-prem)
1. Same as Pro, but deploy into the customer’s **VPC or on-prem** k8s.
2. Wire **SSO/SAML**, **audit logging**, and **data-residency** controls.
3. Optionally **retrain** on the customer’s receivers/region for best accuracy.
4. Provide an **SLA**, monitoring dashboards, and a support channel.

### 5.4 Edge / embedded (in-vehicle SDK)
1. Export the model to a portable runtime (TorchScript/ONNX) — quantise if needed (the model is
   already small).
2. Package the feature extractor + model + EKF as a C++/Python library with a streaming API.
3. Integrate on the target (Jetson/automotive ECU); feed it the receiver’s NMEA/IMU/odometry.
4. Validate latency on-device (budget ~0.6 ms/epoch end-to-end; comfortably real-time at 10 Hz).

---

## 6. Configuration reference

| Setting | Where | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_WS_URL` | frontend env | point the UI at the backend |
| CORS origins | `dashboard/server/main.py` | lock to the frontend domain in production |
| `--checkpoint` / `--scaler` | inference CLI | select the deployed model |
| `--receiver_tier` | inference CLI | match receiver hardware (0–3) |
| EKF `r_base` / `r_degraded` | `EKF9StateParams` | tune the GNSS trust dial per receiver |
| Replay `speed` | WebSocket message | demo pacing (not used in live mode) |
| TLS / `wss` | reverse proxy | the UI auto-upgrades when served over HTTPS |

---

## 7. What must be built for a paid product (honest gap list + roadmap)

| Gap | Why it matters | Effort |
|---|---|---|
| **Live inference service** (`/api/infer` streaming the real model) | today the server *replays* saved runs; a paid product must score live feeds | ~1–2 wks |
| **Authentication & RBAC** (API keys, OAuth/SSO, roles) | multi-customer access control | ~1–2 wks |
| **Multi-tenancy** (per-customer data isolation) | required for SaaS | ~1–2 wks |
| **Billing/metering** (per-vehicle or per-call) | monetisation | ~1 wk + provider |
| **Fleet management** (many vehicles, map overview) | the headline Pro/Enterprise feature | ~2 wks |
| **Alerting integrations** (SMS/Slack/webhook/email) | operational value | ~3–5 days |
| **Observability** (logs/metrics/traces, uptime) | run it reliably | ~1 wk |
| **Hardening** (rate limits, input validation, secrets mgmt) | security | ~1 wk |

**Sequencing (justified):** live inference → auth → fleet view → alerting → billing → multi-tenancy.
This front-loads the features that make the *first pilot* compelling (live + fleet + alerts) and
defers SaaS-only plumbing (billing/tenancy) until there is paying demand.

---

## 8. Cost & feasibility notes

- **Compute:** the model is tiny; a single small GPU instance (or even CPU at 10 Hz) serves many
  vehicles. Edge runs on a Jetson-class device. *So infra cost per vehicle is low* — the margin lives
  in software/support, which suits the open-core model.
- **Data:** training data already collected + public benchmarks; per-customer retraining is optional
  upsell, not a blocker.
- **Risk:** the remaining work (§7) is standard productionisation — **no open research risk**. The
  honest caveat is real-GNSS NLOS robustness (innovation-gating), which improves the fusion margin
  further and is a clear, bounded engineering task.

---

## 9. One-paragraph pitch (for a deck)

> SENTINEL-GNSS predicts GPS failure 5–30 seconds before it happens and fuses that foresight with a
> vehicle’s motion sensors to stay accurately located through urban canyons and tunnels — validated
> on real Tokyo data with centimetre ground truth (cross-city 0.90 DEGRADED F1; +49 % positioning
> accuracy during blackouts). It runs in under a millisecond per update on edge hardware. We ship an
> open core for adoption and trust, and monetise hosted live inference, fleet management, and
> enterprise support.
