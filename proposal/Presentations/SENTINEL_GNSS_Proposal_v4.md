---
marp: true
title: SENTINEL-GNSS — Proactive GNSS Degradation Prediction (v4)
author: Team Pilot Project, Beihang University
paginate: true
size: 16:9
math: katex
style: |
  /* ===== BEIHANG (BUAA) THEME — satellite / vehicle ===== */
  :root {
    --beihang-blue:  #005BAC;   /* primary */
    --beihang-navy:  #003366;   /* deep headers */
    --beihang-sky:   #00A0E9;   /* accent */
    --beihang-grey:  #5A5A5A;   /* body text secondary */
    --bg-light:      #F5F8FC;   /* slide background */
    --clean:         #4CAF50;   /* CLEAN class */
    --warning:       #FF9800;   /* WARNING class */
    --degraded:      #F44336;   /* DEGRADED class */
  }
  section {
    background: var(--bg-light);
    color: #1A1A1A;
    font-family: "Calibri", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 24px;          /* body >= 24px; nothing below 16px anywhere */
    line-height: 1.5;          /* 1.5 line spacing */
    letter-spacing: 0.2px;
    padding: 60px 70px;
  }
  h1 { color: var(--beihang-navy); font-size: 44px; line-height: 1.4; border-bottom: 4px solid var(--beihang-blue); padding-bottom: 12px; }
  h2 { color: var(--beihang-blue); font-size: 34px; line-height: 1.4; }
  h3 { color: var(--beihang-navy); font-size: 26px; line-height: 1.4; }
  strong { color: var(--beihang-blue); }
  table { font-size: 20px; line-height: 1.4; border-collapse: collapse; width: 100%; }
  th { background: var(--beihang-blue); color: #fff; padding: 8px 10px; }
  td { padding: 6px 10px; border-bottom: 1px solid #D0DCE8; }
  tr:nth-child(even) td { background: #ECF3FA; }
  .clean    { color: var(--clean);    font-weight: 700; }
  .warning  { color: var(--warning);  font-weight: 700; }
  .degraded { color: var(--degraded); font-weight: 700; }
  .small { font-size: 18px; color: var(--beihang-grey); line-height: 1.4; }
  .figbox { background:#fff; border:1px solid #C8D6E5; border-radius:10px; padding:10px; }
  section.title { background: linear-gradient(135deg, var(--beihang-navy) 0%, var(--beihang-blue) 60%, var(--beihang-sky) 100%); color:#fff; }
  section.title h1 { color:#fff; border-bottom: 4px solid #fff; font-size: 50px; }
  section.title h2 { color:#E6F2FB; }
  section.section-divider { background: var(--beihang-navy); color:#fff; }
  section.section-divider h1 { color:#fff; border:none; font-size: 52px; }
  header { color: var(--beihang-blue); font-size: 16px; }
  footer { color: var(--beihang-grey); font-size: 14px; }
---

<!-- _class: title -->
<!-- _paginate: false -->

# SENTINEL-GNSS

## Proactive Multi-Horizon Prediction of GNSS Signal Degradation for Autonomous Vehicle Navigation

**Team Pilot Project — Beihang University**
Progress Presentation · Version 4 · Run 14 results

<span class="small">A Transformer–LSTM that forecasts GNSS degradation 5, 15 and 30 seconds **before** it happens.</span>

> **[IMAGE PROMPT — title background]** "Cinematic wide shot of an autonomous car on an
> elevated urban expressway between glass skyscrapers at dusk, faint GNSS satellite signal
> beams descending from orbit, some beams blocked by buildings; deep navy-to-blue gradient
> (#003366→#005BAC→#00A0E9), subtle orbital grid lines, clean futuristic, no text, 16:9."
> _(Place at low opacity behind the title; theme already provides the gradient fallback.)_

---

<!-- _class: section-divider -->

# 1 · The Problem

---

## Why GNSS prediction matters for autonomous driving

- GNSS is the **primary absolute-positioning sensor** for autonomous vehicles.
- It fails **abruptly**: urban canyons, tunnels, foliage, multipath.
- A car at 60 km/h travels **17 m every second**.
- Every existing monitor — RTKLIB quality codes, RAIM, recent ML classifiers — is
  **reactive**: it reports degradation only **after** it happens.

> **The gap:** detecting loss _at the moment it occurs_ gives the vehicle **zero**
> preparation time. We ask a harder question — **"will the signal degrade in the next
> 5 / 15 / 30 seconds?"**

> **[FIGURE]** Concept timeline: a car approaching a tunnel; reactive system flags red at
> the mouth of the tunnel; our system flags <span class="warning">WARNING</span> 5–30 s
> earlier. → create `fig_reactive_vs_proactive.pdf`
> **[IMAGE PROMPT]** "Side-view infographic: car on a road approaching a tunnel; a horizontal
> time axis underneath; green/amber/red markers showing prediction at t-30s, t-15s, t-5s,
> t=0; Beihang blue palette, flat vector, clean, no clutter."

---

## What proactive warning buys the vehicle

| Horizon   | Distance at 60 km/h | Action the planner can take             |
| --------- | ------------------- | --------------------------------------- |
| **+5 s**  | 83 m                | Tighten IMU fusion, slow down           |
| **+15 s** | 250 m               | Pre-engage dead-reckoning, adjust speed |
| **+30 s** | 500 m               | Re-route to avoid the degradation zone  |

- Prediction converts a **sudden failure** into a **planned hand-off** to backup localisation.

> **[IMAGE PROMPT]** "Three stacked road-distance bars (83 m, 250 m, 500 m) beside a car
> icon and a satellite icon, Beihang blue with sky-blue accents, minimalist, vector."

---

<!-- _class: section-divider -->

# 2 · Data

---

## A multi-city, multi-receiver dataset

- **149,662 labelled epochs**, 4 cities, 9+ receiver types, one unified 3-class schema.
- Field collection (Beihang, Septentrio Mosaic-X5C) + public datasets (Hong Kong, Tokyo).
- 5 controlled degradation scenarios (A–E): instant blockage, urban canyon, partial,
  open-sky, approaching blockage.

| Source                            | City      | Receivers        | Role              |
| --------------------------------- | --------- | ---------------- | ----------------- |
| Field Scenarios A–E               | Beihang   | Septentrio       | train / test      |
| UrbanNav Medium/Tunnel/Deep/Harsh | Hong Kong | 9+               | train / val       |
| Tokyo Shinjuku                    | Tokyo     | Trimble + u-blox | **held-out city** |

> **[FIGURE]** `fig_dataset_map.pdf` — world map with pins on Beihang, Hong Kong, Tokyo;
> bubble size = epoch count.
> **[IMAGE PROMPT]** "Minimalist East-Asia map, three glowing location pins (Beihang, Hong
> Kong, Tokyo) connected by thin satellite-orbit arcs, Beihang blue ocean, white land,
> sky-blue arcs, flat vector, no labels."

---

## From raw signals to model-ready features

- Raw **RINEX + NMEA** → **37 engineered features** in 7 groups, per 1-second epoch.
- Feature groups: position, signal strength (C/N₀), satellite count, DOP, receiver status,
  temporal patterns, atmospheric.
- A **30-second sliding window** → tensor `(30 × 37)`; labels at t+5 / t+15 / t+30 s.

| Class                                  | Meaning              | Colour |
| -------------------------------------- | -------------------- | ------ |
| <span class="clean">CLEAN</span>       | healthy fix          | green  |
| <span class="warning">WARNING</span>   | partial degradation  | amber  |
| <span class="degraded">DEGRADED</span> | loss of fix / severe | red    |

> **[FIGURE]** `fig_pipeline.pdf` — RINEX/NMEA → feature extraction → 30 s window →
> Transformer-LSTM → 3 horizon outputs.
> **[IMAGE PROMPT]** "Horizontal data-pipeline diagram, 5 rounded stages connected by arrows,
> satellite icon at the left, car icon at the right, Beihang blue stages with sky-blue arrows,
> flat vector, clean."

---

<!-- _class: section-divider -->

# 3 · Method

---

## The SENTINEL-GNSS architecture

- **Transformer encoder** (2 layers, 8 heads, d=128) — long-range dependencies inside the
  30-second window.
- **BiLSTM** (2 layers, hidden=256) — directional trajectory toward degradation.
- **Three output heads** (+5 s, +15 s, +30 s) + auxiliary head — one model, one forward pass.
- **1.46 M parameters**; focal loss (γ=1.0) + class weights [1, 2, 5]; **no SMOTE** for the
  network (imbalance handled at the loss level).

> **[FIGURE]** `fig_architecture.pdf` — block diagram: input 30×37 → projection → positional
> encoding → Transformer ×2 → BiLSTM ×2 → 3 heads.
> **[IMAGE PROMPT]** "Neural-network architecture block diagram, left-to-right: input tensor,
> transformer blocks (stacked), LSTM blocks, three coloured output heads (green/amber/red),
> Beihang blue blocks, sky-blue connectors, white background, academic, flat vector."

---

## Why a hybrid, and how we validate it honestly

- The **receiver_tier** feature (0 professional → 3 consumer phone) lets one model reconcile
  identical C/N₀ readings that mean different things on different hardware.
- We run a **4-tier baseline** (trivial, rule-based, RandomForest/XGBoost, DL ablations).
- **Ablation:** full model vs LSTM-only vs Transformer-only — identical data, loss, HPs.
- **Honesty controls:** permutation test + temporal-feature ablation to check _what actually
  drives performance_ — we report negative results too.

> <span class="small">Validation layers: held-out test · bootstrap 95% CIs · MCC + κ ·
> ablations · cross-city + cross-receiver · reproducible Kaggle/Colab notebook.</span>

---

<!-- _class: section-divider -->

# 4 · Results (Run 14)

---

## Headline: multi-horizon prediction

| Horizon  | Accuracy | **Macro-F1** | MCC   | 95% CI (Macro-F1) |
| -------- | -------- | ------------ | ----- | ----------------- |
| **+5 s** | 0.854    | **0.821**    | 0.773 | [0.800, 0.843]    |
| +15 s    | 0.789    | 0.741        | 0.691 | [0.717, 0.764]    |
| +30 s    | 0.830    | 0.783        | 0.731 | [0.758, 0.804]    |

- <span class="degraded">DEGRADED</span> **recall = 0.85 at +5 s** — catches 85% of impending
  degradations five seconds early.
- DEGRADED F1 improved **0.274 → 0.718** across runs (2.6×) via targeted data collection.

> **[FIGURE — insert]** `multi_horizon_comparison.png` (already generated).
> **[FIGURE — insert]** `confusion_matrices_test.png` (already generated).

---

## Per-class performance at +5 s

| Class                                  | Precision | Recall |        F1 | Support |
| -------------------------------------- | --------: | -----: | --------: | ------: |
| <span class="clean">CLEAN</span>       |     0.868 |  0.993 | **0.927** |     731 |
| <span class="warning">WARNING</span>   |     0.947 |  0.718 | **0.817** |     746 |
| <span class="degraded">DEGRADED</span> |     0.623 |  0.847 | **0.718** |     209 |

- High **recall** on the safety-critical DEGRADED class is the priority for an AV system.

> **[FIGURE — insert]** `pr_curves_test.png` and `roc_curves_test.png` (already generated).
> **[FIGURE — insert]** `lead_time_histogram.png` — median seconds of advance warning
> _(read the median value from the figure and add it here as the headline engineering number)_.

---

## Ablation — every component contributes

| Architecture                |     Params | +5 s Macro-F1 |  +5 s MCC | DEGRADED F1 |
| --------------------------- | ---------: | ------------: | --------: | ----------: |
| Transformer-only            |     0.43 M |         0.767 |     0.725 |       0.571 |
| LSTM-only                   |     1.03 M |         0.767 |     0.702 |       0.645 |
| **Full (Transformer+LSTM)** | **1.46 M** |     **0.821** | **0.773** |   **0.718** |

- Full model wins on Macro-F1 (+5 s) and on **MCC at every horizon**.
- Transformer alone over-flags (DEGRADED precision 0.42); the LSTM supplies directional
  state that suppresses false alarms.

> **[FIGURE — insert]** `attention_heatmap_degraded.png` + `feature_saliency_5s.png`
> (interpretability — which timesteps and features drive a DEGRADED forecast).

---

## The key result: cross-city generalisation

Trained on Beihang + Hong Kong, tested on **Tokyo (never seen)**:

| Model             | Beihang | Tokyo |    Gap |                   **Tokyo DEGRADED F1** |
| ----------------- | ------: | ----: | -----: | --------------------------------------: |
| **SENTINEL-GNSS** |   0.822 | 0.649 | −0.173 |    **<span class="clean">0.753</span>** |
| RandomForest      |   0.926 | 0.618 | −0.308 | **<span class="degraded">0.148</span>** |

- In-domain, tree ensembles win; **out-of-domain, the network keeps the safety-critical
  DEGRADED class (0.75) while the tree collapses (0.15).**
- **Trees memorise city-specific thresholds; the network learns a transferable representation.**

> **[FIGURE]** `fig_cross_city_degraded.pdf` — grouped bar chart, DL vs RF, per class,
> Beihang vs Tokyo; highlight the DEGRADED collapse in red.
> **[IMAGE PROMPT]** "Grouped bar chart mockup, two cities, two models, three classes
> (green/amber/red), one red bar dramatically shorter than the others, Beihang blue framing,
> clean academic chart, white background."

---

## Efficiency & calibration

- **Inference: 0.039 ms/sample on GPU — 10.5× faster** than three separate tree models;
  one 17.8 MB checkpoint serves all three horizons.
- Real-time at 10 Hz using <0.4% of the per-epoch time budget.
- **Calibration:** temperature scaling applied (Guo et al., 2017); reliability diagram in
  `calibration_curves_test.png`. _(ECE re-measured with corrected temperature — confirm
  before claiming "well-calibrated".)_

> **[FIGURE — insert]** `calibration_curves_test.png`.
> **[IMAGE PROMPT]** "Speedometer-style comparison: one fast needle (DL) vs three slow needles
> (RF), with a '10.5x faster' badge, Beihang blue + sky accent, flat vector."

---

<!-- _class: section-divider -->

# 5 · Novelty & Validation

---

## What is genuinely new

1. **Reactive → proactive.** First multi-horizon GNSS degradation **predictor** (to our
   knowledge — pending systematic literature confirmation).
2. **Cross-city generalisation as the deciding metric** — network retains DEGRADED F1 0.75
   where trees fall to 0.15 on an unseen city.
3. **Unified multi-horizon model** — one pass, three horizons, 10.5× faster than per-horizon
   trees.
4. **Multi-city, multi-receiver open benchmark** — 149,662 labelled epochs, reproducible
   pipeline.
5. **Hardware-aware design** — explicit receiver-tier conditioning across 9+ receivers.

---

## How we will defend it to reviewers

| Question                         | Our evidence                                                                                                         |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| "Trees beat you in-domain."      | True; we disclose it. Out-of-domain we win on DEGRADED (0.75 vs 0.15), run 10.5× faster, one model for 3 horizons.   |
| "Does the Transformer use time?" | Honestly, temporal _order_ adds ~3% (permutation test). The win is **representation transfer**, not order modelling. |
| "Small DEGRADED test set?"       | Bootstrap 95% CIs on every per-class metric.                                                                         |
| "Data leakage?"                  | Session-level split; scaler/SMOTE on train only; one within-site overlap disclosed; Tokyo fully held out.            |

> <span class="small">The honest narrative is the strong narrative — we lead with
> generalisation and efficiency, not an in-domain leaderboard score.</span>

---

<!-- _class: section-divider -->

# 6 · Roadmap & Deliverables

---

## Publication plan (2 papers + 1 conference)

- **Paper A — flagship** (_GPS Solutions_, Q1): method + multi-horizon + cross-receiver +
  cross-city + adaptive EKF. _(Cross-receiver and cross-city are robustness sections, not
  separate thin papers.)_
- **Paper B — benchmark** (_Scientific Data_ / _Data in Brief_): the dataset descriptor.
- **Conference — ION GNSS+ 2026**: cross-city result as a short paper, later extended.

> <span class="small">Two substantial papers avoid "salami-slicing" and carry more impact
> than four thin ones.</span>

---

## What is left to build

| #   | Task                                               | Status                    |
| --- | -------------------------------------------------- | ------------------------- |
| 1   | Re-run calibration (E7) with correct temperature   | ⏳                        |
| 2   | Read median lead-time from histogram               | ⏳                        |
| 3   | `inference.py` — NMEA stream → live prediction     | ⏳                        |
| 4   | Per-receiver evaluation (Paper A §receiver)        | ⏳                        |
| 5   | **Adaptive EKF** — navigation RMSE during blockage | ⏳ (biggest reviewer ask) |
| 6   | Web app — **Next.js + FastAPI** dashboards         | ⏳                        |
| 7   | Paper A full draft                                 | ⏳                        |

---

## The application (Next.js + FastAPI)

- **Real-time monitor** (1 Hz): C/N₀, DOP, satellite count + live 3-horizon prediction bars.
- **Route map** (Mapbox): colour-coded predicted signal quality along the path.
- **Prediction timeline** with lead-time annotations; **attention heatmap**; **DL vs baseline**
  comparison; **dataset explorer** (149k epochs).

> **[IMAGE PROMPT]** "Clean modern web-dashboard mockup on a laptop: left panel live line
> charts (green/amber/red), centre a city map with a coloured route, right panel three large
> probability gauges labelled +5s/+15s/+30s; Beihang blue UI, sky-blue accents, professional
> SaaS look, 16:9."

---

<!-- _class: title -->
<!-- _paginate: false -->

# Thank you

## SENTINEL-GNSS — predicting GNSS degradation before it happens

**Team Pilot Project · Beihang University**

<span class="small">Code + data + reproducible notebook:
github.com/Jorshuare/AI-Based-Prediction-for-GNSS-Signal-Degradation</span>

> **[IMAGE PROMPT — closing]** "Hero shot: autonomous vehicle on a clear road emerging from a
> tunnel into open sky, GNSS satellites reacquiring with green signal beams, sense of
> resolution/safety, Beihang navy-to-sky gradient, cinematic, no text, 16:9."

---

<!-- _class: section-divider -->

# Appendix

---

## Build & formatting notes (for the team)

- **Format:** Marp Markdown → export to **PPTX or PDF**.
  - VS Code: install "Marp for VS Code" → "Export slide deck" → `.pptx` / `.pdf`.
  - CLI: `marp SENTINEL_GNSS_Proposal_v4.md --pptx` (or `--pdf`).
- **Typography (already set in theme):** body 24px, tables 20px, captions 18px (all ≥ 16px);
  **line-height 1.5**; headings 1.4. Calibri/Segoe UI.
- **Beihang palette:** primary `#005BAC`, navy `#003366`, sky `#00A0E9`; class colours
  CLEAN `#4CAF50`, WARNING `#FF9800`, DEGRADED `#F44336`.
- **Figures to drop in from `results/figures/`:** `multi_horizon_comparison.png`,
  `confusion_matrices_test.png`, `pr_curves_test.png`, `roc_curves_test.png`,
  `lead_time_histogram.png`, `attention_heatmap_degraded.png`, `feature_saliency_5s.png`,
  `calibration_curves_test.png`.
- **Figures to create:** `fig_reactive_vs_proactive.pdf`, `fig_dataset_map.pdf`,
  `fig_pipeline.pdf`, `fig_architecture.pdf`, `fig_cross_city_degraded.pdf`.
- **Image-generation prompts:** see each slide's `[IMAGE PROMPT]` block — feed to an
  image model (consistent palette wording is already embedded in every prompt).
- **All numbers** trace to `papers/RESULTS_REFERENCE.md` (Run 14).
