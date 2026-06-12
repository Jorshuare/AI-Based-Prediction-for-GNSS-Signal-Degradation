# EKF Section — Visuals, Charts & Dashboard Screenshots

## Complete breakdown of every image to add, where it goes, and how to generate it

> **Presentation file:** `docs/SENTINEL_GNSS_Presentation_V6.pptx`  
> **EKF section:** Slides 23–29  
> **Dashboard section:** Slides 28–29

---

## OVERVIEW — What each EKF slide currently has vs needs

| Slide | Title                    | Has now                                 | Needs                                                        |
| ----- | ------------------------ | --------------------------------------- | ------------------------------------------------------------ |
| 23    | 5 · EKF divider          | Section title only                      | Nothing (divider is fine)                                    |
| 24    | Standard vs Adaptive EKF | Text bullets + placeholder image        | Replace placeholder with the predict/update loop diagram     |
| 25    | Adaptive-R Formula       | Formula text + annotations              | Add annotated equation image + R(t) timeline plot            |
| 26    | EKF Results — 3 Tiers    | Stats + table                           | Add trajectory+bar combined figure (already generated)       |
| 27    | Severity Sweep           | Text bullets only — **no chart at all** | Add severity sweep line chart (already generated)            |
| 28    | Dashboard Overview       | Panel list (text)                       | Add full dashboard screenshot + individual panel screenshots |
| 29    | Live Demo                | Demo step table                         | Add annotated demo screenshots                               |

---

## SLIDE 24 — "Standard Kalman Filter vs Our Adaptive EKF"

### What to add

**Image:** `results/paper_figures/fig_ekf_mechanism_concept.png`  
**Placement:** Bottom-centre, spanning ~70% of slide width, below the two text columns.

### Why this image

The slide already has the two-column comparison text (fixed-R bullets vs adaptive bullets). The mechanism concept diagram shows the predict→update cycle and where P(DEGRADED) plugs in — it answers the natural question "but HOW does P(DEGRADED) affect the filter?" without needing another slide.

### Current state of the image

The existing `fig_ekf_mechanism_concept.png` is **functional but basic** — plain grey boxes, no colour, no SENTINEL branding. It works for a paper but looks weak on a slide.

### Option A — Use existing (quick)

Insert `fig_ekf_mechanism_concept.png` as-is, cropped to remove the excess whitespace on the right side.

### Option B — Generate a polished version (recommended)

Use the prompt below to create a replacement in ChatGPT / Canva:

```
Create a clean, colour-coded circular flow diagram for an Extended Kalman Filter
(EKF) predict-update cycle. White background, rounded-rectangle nodes, connecting
arrows with labels. Four nodes arranged in a diamond:

TOP node — "PREDICT" (blue fill #E3F2FD, border #003893):
  • x̂⁻_t = F x̂_{t-1}    (state prediction)
  • P⁻_t = F P_{t-1}Fᵀ + Q    (covariance propagation)
  • Sub-label below: "IMU + wheel odometry + NHC + ZUPT"

RIGHT node — "SENTINEL OUTPUT" (amber fill #FFF8E1, border #F57F17):
  • Input: 30-step GNSS window (37 features)
  • Output: P̂(DEGRADED) @ +5s, +15s, +30s
  • Arrow from this node to BOTTOM is orange, labelled "P̂_calib(t)"

BOTTOM node — "ADAPTIVE R(t)" (red fill #FDECEA, border #C62828):
  • R(t) = σ²_base + (σ²_deg − σ²_base) × P̂_calib(t)
  • "P̂=0 → R=9 m²   |   P̂=1 → R=10,000 m²"
  • Arrow from this node to LEFT is red, labelled "measurement noise"

LEFT node — "UPDATE" (green fill #E8F5E9, border #1B873A):
  • Kₜ = P⁻ₜ Hᵀ (H P⁻ₜ Hᵀ + Rₜ)⁻¹
  • x̂_t = x̂⁻_t + Kₜ(zₜ − Hx̂⁻_t)
  • Sub-label: "Fuse GNSS measurement with adaptive trust"
  • Arrow from this node back to TOP is green, labelled "updated state x̂_t"

Centre text (inside the diamond, small): "1 Hz update loop"

Bottom-right callout box (yellow, small):
  "When P(DEGRADED) ↑ → R ↑ → K ↓ → filter leans on motion model"

Typography: clean sans-serif (Inter or Helvetica). Size: 1600×900 px.
Color palette: navy #003366, blue #003893, amber #F57F17, red #C62828, green #1B873A.
```

---

## SLIDE 25 — "Adaptive Measurement Noise — The Mechanism"

### What to add

#### Image 1 — Annotated equation diagram (generate externally)

**Placement:** Left half of slide (replace the current placeholder image).

**Prompt (ChatGPT / Canva AI / Figma):**

```
Create a slide-ready annotated equation diagram on a white background.

Centre equation (large, LaTeX-style font, dark navy #003366):

  R(t)  =  σ²_base  +  ( σ²_deg − σ²_base )  ×  P̂_calib(t)

Below it, smaller:
  P̂_calib(t)  =  clip( ( P̂(t) − P₅ ) / ( 1 − P₅ ),   0,   1 )

Draw labelled arrows pointing FROM each term TO a description box.
Use this exact color-coding:

  ▶  "R(t)"             →  box (blue border #003893):
       "Measurement noise covariance fed to Kalman filter at time t.
        Controls how much weight the filter gives to GNSS vs motion model."

  ▶  "σ²_base"          →  box (green border #1B873A, fill #E8F5E9):
       "σ²_base = 9 m²
        Baseline noise when signal is CLEAN.
        Filter trusts GNSS tightly."

  ▶  "σ²_deg"           →  box (red border #C62828, fill #FDECEA):
       "σ²_deg = 10,000 m²
        Noise under full degradation.
        Filter ignores GNSS, dead-reckons on IMU."

  ▶  "(σ²_deg − σ²_base)" →  box (grey border):
       "Dynamic range of R.
        How much trust can change end-to-end."

  ▶  "P̂_calib(t)"      →  box (amber border #F57F17, fill #FFF8E1):
       "Calibrated P(DEGRADED) from SENTINEL.
        0 = signal is clean.  1 = signal fully degraded.
        P₅ = 0.153 floor removed (cross-receiver bias correction)."

Three pills at the bottom:
  🟢  "P̂ = 0  →  R = 9 m²  →  Trust GNSS fully"
  🟡  "P̂ = 0.5  →  R ≈ 500 m²  →  Caution"
  🔴  "P̂ = 1  →  R = 10,000 m²  →  Dead-reckon only"

Font: Inter or Helvetica. Background: white. Width: 900 px × 650 px.
```

#### Image 2 — R(t) timeline vs P(DEGRADED) (already generated)

**File:** `results/paper_figures/fig18_ekf_realdata.png`  
**Use:** Panel **(b)** only — the right-side P(DEGRADED) timeline.  
**Placement:** Right half of slide, showing how R inflates as P(DEGRADED) rises to 1.0.

**How to crop panel (b) only:**

```python
from PIL import Image
img = Image.open("results/paper_figures/fig18_ekf_realdata.png")
w, h = img.size
right_panel = img.crop((w//2, 0, w, h))   # right half
right_panel.save("results/paper_figures/fig18b_pdeg_timeline.png")
```

**Caption to add on slide:** "Tokyo Shinjuku — P(DEGRADED) @+5s rises to 1.0 during blocked zone → R inflates from 9 → 10,000 m²"

---

## SLIDE 26 — "EKF Results — Three Tiers of Validation"

### What to add

**File:** `results/paper_figures/figC3_ekf.png`  
**This is the best single image for this slide** — it combines both panels:

- Panel (a): Trajectory map — ground truth (black) vs raw GNSS (grey dots) vs Fixed-R EKF (dashed) vs Adaptive EKF (blue)
- Panel (b): Bar chart — Overall and Blockage RMSE for GNSS / Fixed / Adaptive

**Placement:** Right two-thirds of the slide, with the existing stats (−33.8% / +82% / +48.8%) and the table on the left third.

### Alternative — two separate figures

If the combined figure is too small, use them individually:

| Figure                     | Content                                                              | Placement  |
| -------------------------- | -------------------------------------------------------------------- | ---------- |
| `fig08_ekf_trajectory.png` | Trajectory map (Synthetic data, blockage zone highlighted)           | Left half  |
| `fig07_ekf_rmse.png`       | Bar chart: GNSS 54.4m → Fixed 45.6m → Adaptive 36.0m (blockage RMSE) | Right half |

### What the figures show

- `fig08_ekf_trajectory.png` — synthetic blockage test: raw GNSS scatters wildly in yellow zone; adaptive EKF (blue) stays close to ground truth
- `fig07_ekf_rmse.png` — blockage RMSE drops from 54.4 m (GNSS-only) → 45.6 m (Fixed-R) → 36.0 m (Adaptive-R) = **−33.8%**
- `figC3_ekf.png` — same data, both panels combined (conference-ready)

> **Recommendation:** Use `figC3_ekf.png` as a single full-width image at the bottom of the slide, with the three large numbers (+82%, +48.8%, −33.8%) as headline callouts above it. This is the clearest layout.

---

## SLIDE 27 — "When is Adaptive-R Worth It? — Severity Sweep"

### What to add — THIS SLIDE HAS NO CHART YET, add this first

**File:** `results/paper_figures/fig22_urbannav_severity_sweep.png`  
**Placement:** Right half of slide (the left half keeps the two-column bullet text).

### What the chart shows

- X-axis: Multipath bias during blockage (m), range 5–80 m
- Y-axis: Blocked-segment RMSE (m)
- Three lines:
  - Grey dashed: Raw GNSS (rises steeply from 8 m to 75 m)
  - Dark blue: Aided EKF Fixed-R (stays low, 6–30 m)
  - Gold: Aided EKF Adaptive-R (flat ~25–29 m across all biases; crossover with fixed-R at ~80 m)
- Key annotation: "with wheel-odometry + NHC + ZUPT aiding, keeping GNSS (fixed-R) stays best: inflating R discards heading aiding"

### Actual crossover data (from urbannav_ekf.json — source of truth)

| Bias (m) | Raw GNSS | Fixed-R | Adaptive-R | Winner |
|---|---|---|---|---|
| 5 m | 7.7 m | **5.8 m** | 27.5 m | Fixed by large margin |
| 30 m | 29.8 m | **10.6 m** | 28.5 m | Fixed |
| 60 m | 64.6 m | **18.2 m** | 22.7 m | Fixed (narrowing) |
| **80 m** | 75.4 m | 30.2 m | **29.6 m** | **Adaptive wins (+1.9%)** |

### Why this is important for the presentation

The chart directly proves the "practical rule" statement already on the slide: adaptive-R is best for **GNSS-only platforms** in deep canyons; for full AV sensor suite (IMU + odometry), SENTINEL's role is the **mode-switch trigger**, not R-inflation.

### Suggested annotation to add in PowerPoint

Draw a red callout arrow pointing to where the adaptive-R line exceeds the fixed-R line (~80 m crossover) with text:  
**"Adaptive-R wins when multipath bias > ~80 m — or on GNSS-only platforms (no wheel encoder)"**

> Note: `fig07_ekf_rmse.png` and `figC3_ekf.png` are from the OLD 2D toy simulation
> (ekf_demo.json, simple adaptive_ekf.py). Their numbers (54.4→45.6→36.0 m) represent
> a prototype EKF without aiding or 9-state design. For the paper, use `fig21_urbannav_filter_comparison.png`
> (6-method bar chart from the current 9-state aided EKF) and `fig22_urbannav_severity_sweep.png`.

---

## SLIDE 28 — "SENTINEL-GNSS Dashboard — Real-Time Analytics"

### Dashboard component map

| Panel # | Component file        | What it shows                                                  |
| ------- | --------------------- | -------------------------------------------------------------- |
| 01      | `SignalGauge.tsx`     | P(DEGRADED) at +5s / +15s / +30s — dial gauge, green/amber/red |
| 02      | `ProbabilityBars.tsx` | CLEAN / WARNING / DEGRADED bars per horizon                    |
| 03      | `TrajectoryMap.tsx`   | Vehicle path on map, coloured by risk level                    |
| 04      | `TimeSeriesChart.tsx` | P(DEGRADED) streaming timeline, 3 horizons                     |
| 05      | `EkfPanel.tsx`        | Blocked RMSE comparison by filter type                         |
| 06      | `AlarmCenter.tsx`     | CRITICAL / WARNING alert feed with timestamps                  |

### Screenshots you need to take

**Step 1 — Start the dashboard:**

```bash
cd dashboard/client
npm install        # first time only
npm run dev        # starts at http://localhost:3000
```

Then open `http://localhost:3000` in a browser (Chrome preferred for clean screenshots).

**Step 2 — Load a real data scenario:**
Start the backend with pre-computed Tokyo/Beihang data so the panels show real values, not empty state.

```bash
# In a second terminal:
cd dashboard
uvicorn main:app --reload   # or: python -m uvicorn main:app --reload
```

**Step 3 — Take these specific screenshots:**

---

### Screenshot A — Full dashboard overview

**What:** Entire browser window showing all 6 panels in the grid layout  
**When to take:** When P(DEGRADED) is in a DEGRADED period (red state — most visually impactful)  
**Resolution:** 1920×1080 minimum  
**Insert on:** Slide 28 — use as the central image, shrink text columns to make room  
**Filename to save as:** `docs/screenshots/dashboard_full_overview.png`

```
Recommended moment: epoch where AlarmCenter shows a CRITICAL alert AND
the SignalGauge is in red AND the trajectory map shows a red path segment.
This shows all 6 panels active simultaneously.
```

---

### Screenshot B — Signal Gauge panel (close-up)

**What:** Just the SignalGauge component zoomed in — the three dial/arc indicators  
**When to take:** P(DEGRADED @+5s) > 0.8 (CRITICAL — full red)  
**Insert on:** Slide 28 — Panel 01 thumbnail, or Slide 29 Demo step 1  
**Filename:** `docs/screenshots/panel_01_signal_gauge_critical.png`

Also take one in green state (P < 0.3):  
**Filename:** `docs/screenshots/panel_01_signal_gauge_clean.png`

**Why both:** The before/after visual — "here it's green, then SENTINEL predicts degradation 5 seconds out, it turns red — the driver/system has time to act."

---

### Screenshot C — Trajectory Map panel (close-up)

**What:** The TrajectoryMap component showing the vehicle path coloured by risk  
**When to take:** After a full run so the path has both green (clean) and red (degraded) segments  
**Insert on:** Slide 28 Panel 03 thumbnail, or Slide 29 Demo step 3  
**Filename:** `docs/screenshots/panel_03_trajectory_risk_coloured.png`

```
The ideal screenshot shows:
- A clear route with a visible colour transition from green → amber → red
- The red segment corresponds to the blocked zone (building canyon / tunnel entry)
- The SPAN-INS ground truth visible as a reference track
```

---

### Screenshot D — P(DEGRADED) Timeline panel

**What:** TimeSeriesChart showing all three horizon lines (+5s green, +15s amber, +30s blue) with threshold dashed lines  
**When to take:** During or just after a DEGRADED event — so the spike is visible  
**Insert on:** Slide 28 Panel 04 thumbnail, or Slide 29 Demo step 2  
**Filename:** `docs/screenshots/panel_04_pdeg_timeline_spike.png`

```
Ideal: The chart shows the P(DEGRADED @+5s) spike to 1.0 while
+15s and +30s are lagged — demonstrating multi-horizon prediction.
```

---

### Screenshot E — Alert Centre panel

**What:** AlarmCenter showing CRITICAL and WARNING alerts with timestamps  
**When to take:** During/after a degradation event  
**Insert on:** Slide 29 Demo — "this is what the AV route planner receives"  
**Filename:** `docs/screenshots/panel_06_alert_centre_active.png`

---

### Screenshot F — EKF Analytics panel

**What:** EkfPanel showing the RMSE bar comparison (Fixed-R vs Adaptive-R)  
**Insert on:** Slide 29 Demo step 5  
**Filename:** `docs/screenshots/panel_05_ekf_analytics.png`

---

### How to insert screenshots into Slide 28

**Recommended layout for Slide 28:**

```
┌─────────────────────────────────────────────────────────────────┐
│  NAVY HEADER BAR  —  "SENTINEL-GNSS DASHBOARD"                   │
├──────────────────────────────┬──────────────────────────────────┤
│  [Screenshot A]              │  Panel labels (existing text):   │
│  Full dashboard overview     │  01 Signal Gauge                 │
│  (full dashboard PNG)        │  02 Probability Bars             │
│  ~60% width                  │  03 Trajectory Map               │
│                              │  04 P(DEG) Timeline              │
│                              │  05 EKF Analytics                │
│                              │  06 Alert Centre                 │
│                              │                                  │
├──────────────────────────────┴──────────────────────────────────┤
│  "FastAPI backend · Next.js frontend · WebSocket @ 1 Hz · Offline-capable"  │
└─────────────────────────────────────────────────────────────────┘
```

---

## SLIDE 29 — "Live Demo — 3 Minutes"

### Screenshots to add

Use a **3-panel strip** at the bottom of the slide showing the demo progression:

| Position | Screenshot                                                                              | Caption                                                     |
| -------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Left     | `panel_01_signal_gauge_clean.png` → `panel_01_signal_gauge_critical.png` (side-by-side) | "Step 1: Signal transitions CLEAN → CRITICAL (5 s warning)" |
| Centre   | `panel_04_pdeg_timeline_spike.png`                                                      | "Step 2: P(DEGRADED) spikes — +5s / +15s / +30s all rise"   |
| Right    | `panel_06_alert_centre_active.png`                                                      | "Step 3: CRITICAL alert fires — AV route planner notified"  |

### Demo script (updated with visual cues)

**Step 1 — Show CLEAN state (0:00–0:30)**

> "Dashboard is live. All gauges green. P(DEGRADED) flat near zero across all three horizons."  
> _Point to Screenshot: `panel_01_signal_gauge_clean.png`_

**Step 2 — Trigger degradation sequence (0:30–1:30)**

> "Watch the +5s gauge. SENTINEL is reading the GNSS features — satellite count dropping, C/N₀ degrading. P(DEGRADED @+5s) climbing..."  
> _Point to Screenshot: `panel_04_pdeg_timeline_spike.png`_

**Step 3 — CRITICAL alert fires (1:30–2:00)**

> "Alert fired — CRITICAL at 5 seconds out. The EKF has already started inflating R. The vehicle hasn't lost positioning yet, but the filter is already preparing the handoff to dead-reckoning."  
> _Point to Screenshot: `panel_06_alert_centre_active.png`_

**Step 4 — Show trajectory map (2:00–2:30)**

> "Look at the trajectory map — the path turns red right where we predicted. Ground truth is within 24 metres. Without adaptive-R it would be 47 metres."  
> _Point to Screenshot: `panel_03_trajectory_risk_coloured.png`_

**Step 5 — EKF analytics (2:30–3:00)**

> "Panel 5 shows the filter comparison live. Adaptive EKF consistently outperforms Fixed-R in the blocked segment. That's the SENTINEL loop closed — prediction into action."  
> _Point to Screenshot: `panel_05_ekf_analytics.png`_

---

## SYSTEM PIPELINE DIAGRAM — Generation Prompt

> For when you want a redesigned or externally-generated version of the pipeline diagram
> (instead of the auto-generated `results/paper_figures/system_pipeline_diagram.png`).
> Use in ChatGPT (GPT-4o), Canva AI, or hand to a Figma/PowerPoint designer.

```
Create a clean, professional horizontal infographic for a research presentation slide.
Title: "COMPLETE SYSTEM PIPELINE — SENTINEL-GNSS"
Canvas size: 1920×864 px (16:9 landscape). Background: white #FFFFFF.
A thin navy (#003366) header bar at the top (40 px tall) holds the title in white bold text.
A thin cyan (#4FC3F7) accent stripe (5 px) runs below the header bar.

The diagram flows left-to-right in FIVE colour-coded stage columns separated by
light grey dashed vertical dividers:

──────────────────────────────────────────────────────────────────────────────
COLUMN 1 — SENSORS  (column label in navy pill at top: "SENSORS")

Three rounded-rectangle boxes stacked vertically:

Box 1 — "GNSS RECEIVER" (fill #E3F2FD, border #003893):
  Sub-text: "u-blox / Trimble F9P"
  Sub-text: "NMEA · RINEX"
  Sub-text: "C/N₀ · DOP · sat count @ 1 Hz"

Box 2 — "IMU (100 Hz)" (fill #FFF8E1, border #F57F17):
  Sub-text: "Accelerometer (3-axis)"
  Sub-text: "Gyroscope (3-axis)"
  Sub-text: "Heading + motion"

Box 3 — "WHEEL ENCODER" (fill #E8F5E9, border #1B873A):
  Sub-text: "Vehicle speed"
  Sub-text: "Non-holonomic constraint (NHC)"

Small dashed purple box below all three — "SPAN-INS Ground Truth":
  Sub-text: "cm-level reference — validation only"
  Border: #6A1B9A (dashed)

──────────────────────────────────────────────────────────────────────────────
COLUMN 2 — FEATURE ENGINEERING  (column label: "FEATURE ENGINEERING")

Box 1 — "37 FEATURES · 7 GROUPS" (fill #F5F7FF, border #5A6A86):
  Bullet list inside:
  • C/N₀: max / mean / std / trend
  • DOP: gdop / pdop / hdop / vdop
  • Satellites: count / drop-rate
  • Receiver: fix quality / age
  • Atmospheric: iono / tropo
  • Temporal Δ: pdop_delta

Box 2 — "SLIDING WINDOW" (fill #E3F2FD, border #003893):
  "30 epochs × 37 features"
  "= 30×37 input tensor"
  Labels: +5 s  /  +15 s  /  +30 s

Red italic note below boxes: "✗  lat / lon excluded — prevents geo-overfitting"

──────────────────────────────────────────────────────────────────────────────
COLUMN 3 — SENTINEL MODEL  (column label: "SENTINEL MODEL")
Outer container box with blue border #003893 and very light blue tint.
Sub-title inside: "1.46 M parameters"

Nested boxes top to bottom:

Box A — "Transformer Encoder" (fill #E3F2FD):
  "2 layers · 8 heads · d_model=128"
  "Self-attention: long-range signal patterns"
  Formula: "Attention(Q,K,V) = softmax(QKᵀ/√d)V"

Box B — "Bidirectional LSTM" (fill #FFF8E1):
  "2 layers · hidden=256"
  "Causal trend — is signal worsening?"

Three small side-by-side boxes:
  "+5 s" (green fill #E8F5E9)  |  "+15 s" (amber fill #FFF8E1)  |  "+30 s" (red fill #FDECEA)
  Each shows: P(CLEAN) / P(WARN) / P(DEG)

Box C — "Temperature Scaling T=0.4023" (fill #F5F7FF):
  "ECE: 0.114 → 0.068  (−40%)"
  "Calibrated probability = trustworthy risk score"

──────────────────────────────────────────────────────────────────────────────
COLUMN 4 — ADAPTIVE EKF  (column label: "ADAPTIVE EKF")
Outer container with green border #1B873A and very light green tint.
Sub-title: "9-STATE FILTER"

Nested boxes top to bottom:

Box A — "ADAPTIVE R(t)" (fill #FDECEA, border #C62828):
  "R(t) = σ²_base + (σ²_deg − σ²_base) × P̂_calib"
  "P̂=0 → R=9 m²  (trust GNSS)"
  "P̂=1 → R=10,000 m²  (dead-reckon)"

Box B — "PREDICT STEP" (fill #FFF8E1, border #F57F17):
  "x̂⁻_t = F x̂_{t-1}"
  "IMU + Odometry + NHC + ZUPT"

Box C — "UPDATE STEP" (fill #E8F5E9, border #1B873A):
  "Kₜ = P⁻Hᵀ(HP⁻Hᵀ+Rₜ)⁻¹"
  "Fuse GNSS with adaptive trust"

Box D — "STATE OUTPUT" (fill #E3F2FD, border #003893):
  "[x, y, vx, vy, heading, ax, ay, ωz, baro]"
  "Filtered position + velocity"

──────────────────────────────────────────────────────────────────────────────
COLUMN 5 — OUTPUTS & DASHBOARD  (column label: "OUTPUTS & DASHBOARD")

Box A — "FILTERED POSITION" (fill #E8F5E9, border #1B873A):
  "Blocked RMSE: 47.4 m → 24.3 m"
  "+48.8%  on real Tokyo data"

Box B — "ALERT ENGINE" (fill #FDECEA, border #C62828):
  "CRITICAL: P(DEG) > 0.8 @ +5 s"
  "WARNING:  P(DEG) > 0.6 @ +15 s"

Box C — "AV ROUTE PLANNER" (fill #FFF8E1, border #F57F17):
  "+5 s → tighten IMU fusion"
  "+15 s → engage dead-reckoning"
  "+30 s → re-route"

Tall box at bottom — "DASHBOARD  (FastAPI + Next.js)" (fill #EEF2FF, border #003893):
  Six bullet lines with colour-coded left bars:
  ● green: Signal Gauge (P @ +5/+15/+30 s)
  ● blue: Probability Bars (CLEAN/WARN/DEG)
  ● purple: Trajectory Map (risk-coloured path)
  ● blue: P(DEGRADED) Timeline (3 horizons)
  ● amber: EKF Analytics (RMSE by filter type)
  ● red: Alert Centre (CRITICAL / WARNING)

──────────────────────────────────────────────────────────────────────────────
ARROWS (connecting the columns):

1. Thick blue arrow (2px): GNSS Receiver → Feature Extraction (label: "raw obs")
2. Thick blue arrow: Feature Extraction → SENTINEL (label: "30×37 tensor")
3. Thick red arrow: SENTINEL +5s head → Adaptive R(t) (label: "P̂(DEG)")
4. Orange arrow: SENTINEL output → Alert Engine (label: "P(CLEAN/WARN/DEG)")
5. Amber curved arrow sweeping under the diagram: IMU → Predict Step (label: "IMU @ 100 Hz")
6. Green curved arrow: Wheel Encoder → Predict Step (label: "odometry")
7. Medium blue arrow: GNSS Receiver → Update Step (label: "GNSS position zₜ", curves above)
8. Green arrow: State Output → Filtered Position + Dashboard
9. Purple dashed arrow spanning bottom: SPAN-INS → right edge (label: "validation only — never in training")

──────────────────────────────────────────────────────────────────────────────
BOTTOM BANNER (navy #003366, full width, 35 px):
Star symbol ★ in amber, then white bold text:
"Zero-shot cross-city generalisation — trained on Hangzhou (Beihang A–E) + HK UrbanNav
 |  tested on Tokyo Shinjuku (zero Tokyo data in training)"

Typography: Inter, Helvetica, or any clean sans-serif. Avoid decorative fonts.
```

---

## QUICK REFERENCE — Which existing figures to use on which slide

| Slide | File to insert                                                | Location on slide                                                        |
| ----- | ------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 24    | `results/paper_figures/fig_ekf_mechanism_concept.png`         | Bottom-centre (below text columns) OR replace with new generated version |
| 25    | External: annotated equation image (Prompt above)             | Left half (replace placeholder)                                          |
| 25    | `results/paper_figures/fig18_ekf_realdata.png` (panel b only) | Right half                                                               |
| 26    | `results/paper_figures/figC3_ekf.png`                         | Bottom two-thirds (keeps headline stats above)                           |
| 27    | `results/paper_figures/fig22_urbannav_severity_sweep.png`     | Right half (left half keeps bullet text)                                 |
| 28    | `docs/screenshots/dashboard_full_overview.png`                | Centre-left (~60% width)                                                 |
| 29    | 3-panel strip: gauge + timeline + alerts                      | Bottom strip                                                             |

---

## FILES TO CREATE (screenshots — not yet taken)

```
docs/screenshots/
├── dashboard_full_overview.png          ← Full dashboard, all 6 panels, DEGRADED state
├── panel_01_signal_gauge_clean.png      ← Signal gauge, green state
├── panel_01_signal_gauge_critical.png   ← Signal gauge, red/critical state
├── panel_03_trajectory_risk_coloured.png ← Map with green→red path
├── panel_04_pdeg_timeline_spike.png     ← Timeline with P spike to 1.0
├── panel_05_ekf_analytics.png          ← EKF RMSE bars
└── panel_06_alert_centre_active.png    ← Alert feed with CRITICAL alert
```

To take these, run the dashboard (`npm run dev` + `uvicorn main:app`) and replay the
Tokyo Shinjuku or Beihang Scenario E pre-computed data through the WebSocket stream.

---

---

# SENSOR FUSION PAGE — Full Explainer

## "What does everything on the Sensor Fusion tab mean?"

> Use this section to answer any question about the Sensor Fusion dashboard tab —
> from a layperson asking "what is RTKLIB?" to a professor asking "why is adaptive-R worse?"

---

## What is the Sensor Fusion page showing?

The Sensor Fusion tab answers one specific question:

> **"When the car loses GNSS signal, how well does each positioning filter hold position?"**

It shows a real driving run in **Tokyo Shinjuku** where the car drove through streets with tall buildings that blocked satellite signals. It compares four strategies for staying positioned during those blocked segments:

1. Do nothing — just use the raw GNSS (worst)
2. Use a simple Kalman filter
3. Use a full 9-state EKF (Extended Kalman Filter)
4. Use a full 9-state EKF + wheel odometry + motion constraints (best)

The SENTINEL model feeds its P(DEGRADED) prediction into each filter to optionally make them distrust GNSS before it fails.

---

## GNSS Source Picker — "Trimble" vs "u-blox"

### What does "Trimble · RTKLIB SPP · GPS+GLONASS dual-freq" mean?

**Trimble** is the brand of professional-grade GNSS receiver used to collect the raw signal data during the Tokyo Shinjuku drive.

- The Trimble receiver logged raw GNSS observations in **RINEX format** (`.obs` files)
- **RTKLIB** is open-source positioning software that reads the Trimble RINEX file and computes positions using **SPP (Single Point Positioning)** — see below
- Trimble's receiver tracked **GPS + GLONASS** on two frequencies (L1+L2), so RTKLIB had more satellites and better geometry to work with
- In short: Trimble collected the raw signals → RTKLIB processed them into positions → our EKF filtered those positions

**Dashboard label:** `Trimble · RTKLIB SPP · GPS+GLONASS dual-freq`  
**What it is:** Professional survey-grade receiver (~$5,000–15,000). RTKLIB is the de facto standard open-source tool for GNSS processing — used in research, PPP services, and academic benchmarks worldwide.

---

### What does "u-blox F9P · georinex SPP · GPS L1 only" mean?

**u-blox F9P** is a different GNSS chip — cheaper (~$200) but still dual-frequency capable. It was driven simultaneously on the same route as the Trimble.

The key difference in how the u-blox data was processed:

- **georinex** — a lightweight Python RINEX reader library — was used instead of RTKLIB
- The u-blox RINEX file was processed in **GPS-only, L1 single-frequency** mode
- GPS L1 single-frequency = only one signal per satellite, only GPS constellation — fewer measurements, weaker geometry than Trimble's GPS+GLONASS dual-freq

**Why does this matter?**

- Both receivers physically collected signals on two frequencies and multiple constellations
- The _processing choice_ determines what gets used: RTKLIB is a full-featured positioning engine that exploits all available signals; georinex is a simpler reader that we used in basic L1-only mode
- The result is that the u-blox track has more position noise — not because the u-blox hardware is worse, but because we used a simpler processing pipeline on it

**SPP = Single Point Positioning (applies to BOTH sources):**

- The most basic positioning method — uses only pseudorange measurements, one receiver, no base station
- No differential corrections, no carrier phase processing
- Typical accuracy: **2–5 m in open sky, 10–50 m in urban canyons**
- This is what car navigation, smartphones, and low-cost trackers use
- Our EKF is designed to handle this level of accuracy (not RTK-corrected positions)

**Dashboard label:** `u-blox F9P · georinex SPP · GPS L1 only`  
**Bottom line:** Same route, worse processing pipeline → noisier input → harder test for the EKF. Showing the EKF helps even here proves the approach is robust.

---

### Why two sources?

| Property            | Trimble                                        | u-blox F9P                                |
| ------------------- | ---------------------------------------------- | ----------------------------------------- |
| Hardware cost       | ~$10,000                                       | ~$200                                     |
| Hardware frequency  | Dual (L1+L2)                                   | Dual (L1+L2)                              |
| Constellations used | GPS + GLONASS                                  | GPS only                                  |
| Processing tool     | **RTKLIB** (full engine)                       | **georinex** (basic reader)               |
| Processing mode     | SPP dual-freq                                  | SPP L1-only                               |
| Noise level         | Lower (more signals)                           | Higher (fewer signals)                    |
| Dashboard label     | `Trimble · RTKLIB SPP · GPS+GLONASS dual-freq` | `u-blox F9P · georinex SPP · GPS L1 only` |
| Our use             | Primary EKF study                              | Robustness check (harder input)           |

**Key point:** The _hardware_ difference is smaller than the _processing_ difference. The u-blox track is noisier primarily because we processed it in GPS L1-only SPP mode, not because the receiver is worse. The Trimble track benefits from RTKLIB's more sophisticated estimator and dual-constellation geometry.

---

## Ground Truth — "SPAN-INS"

**SPAN-INS** is the NovAtel SPAN Inertial Navigation System.

- It combines a tactical-grade IMU (Inertial Measurement Unit) with RTK-corrected GNSS
- Accuracy: **1–3 cm position, 0.01° heading**
- This is the "truth" track shown as a thick green line on the trajectory map
- Every RMSE (Root Mean Square Error) number in this dashboard is computed against SPAN-INS

**Why not just use RTK?** SPAN-INS gives accurate position even during the brief satellite blockages, because its IMU continues dead-reckoning at 100 Hz even when GNSS drops out. Pure RTK would also lose position in the blockage zones.

The SPAN-INS data is used **only for evaluation** — our EKF does not use it during operation. This ensures the results are honest.

---

## Trajectory Map

The map shows the actual driving route projected into a local East-North coordinate frame (ENU — East, North, Up). The origin (0,0) is the first valid GNSS fix.

| Track                  | Colour          | Meaning                                                     |
| ---------------------- | --------------- | ----------------------------------------------------------- |
| Ground truth           | Thick green     | SPAN-INS reference (always correct)                         |
| Raw GNSS               | Red dashed      | What the SPP solution gives you — scattered during blockage |
| Aided EKF (fixed-R)    | Teal/cyan solid | Our recommended filter — stays close to truth               |
| Aided EKF (adaptive-R) | Yellow dashed   | SENTINEL-driven adaptive trust — slightly worse with aiding |

**Toggle buttons** under the map let you turn each track on/off to compare directly.

The path is displayed in **metres** relative to the starting point. The rotation (if any) is automatic — the code aligns the longest axis of the route to fill the horizontal space.

---

## Accuracy Panel — "Accuracy during GPS blackout"

This panel shows RMSE (Root Mean Square Error) measured **only during the blackout segments** — the moments when GNSS signal was blocked.

| Filter label               | What it is                                                                      |
| -------------------------- | ------------------------------------------------------------------------------- |
| **Raw GNSS**               | No filtering — raw SPP position output                                          |
| **Simple KF**              | Constant-velocity Kalman filter (CV-KF). Predicts position using velocity only. |
| **Aided EKF (fixed-R)**    | Full 9-state EKF + wheel odometry + NHC + ZUPT, fixed measurement noise         |
| **Aided EKF (adaptive-R)** | Same as above, but R(t) inflates with P(DEGRADED) from SENTINEL                 |

**Why does adaptive-R do worse here?** Inflating R tells the filter to distrust GNSS more — but with wheel odometry already providing dead-reckoning, the filter needs GNSS primarily for heading correction. When R is inflated, heading drifts slightly, and the odometry-based dead-reckoning accumulates angular error. The fixed-R filter uses GNSS heading updates more aggressively, which keeps the track straight.

**RMSE formula:**  
`RMSE = sqrt( (1/N) Σ [(x_filter - x_truth)² + (y_filter - y_truth)²] )`  
where N = number of epochs inside blockage windows.

---

## EKF Analytics Panel (inside the main dashboard, not Fusion tab)

### Bar chart — "Blocked-segment RMSE by filter"

Shows the same information as above but with all 6 filter variants, including the unaided EKF variants.

| Bar                   | What it means                                   |
| --------------------- | ----------------------------------------------- |
| GNSS Raw              | Baseline — no filtering at all                  |
| CV Kalman (fixed-R)   | Simple velocity extrapolation during blockage   |
| EKF 9-state (fixed-R) | IMU integration without wheel odometry          |
| EKF 9-state (adapt-R) | IMU + SENTINEL, but no wheel constraint         |
| Aided EKF (fixed-R) ★ | **Winner** — full aiding suite, fixed R         |
| Aided EKF (adapt-R)   | Full aiding suite + adaptive R — slightly worse |

The `★` marks the recommended configuration.

### Severity sweep chart — "When does adaptive-R help?"

This chart answers the question: "if the GNSS multipath error is very bad, does adaptive-R eventually become better?"

- **X-axis:** How severe the GNSS error is during blockage (metres of injected multipath bias)
- **Y-axis:** RMSE during blockage (metres)
- **Three lines:** Raw GNSS (red), Fixed-R (dark blue), Adaptive-R (gold)

**Reading the chart:**

- At low severity (5–30 m bias): Fixed-R EKF dominates. The filter's odometry holds position well, and GNSS helps with heading.
- At very high severity (60–80 m): Adaptive-R starts to catch up because at that level of corruption it's correct to distrust GNSS completely.
- The crossover (~80 m) is beyond typical urban canyon conditions — even harsh Mong Kok GNSS errors rarely exceed 60 m.

**The practical conclusion (on slide 27 of the presentation):**

> On a full AV sensor suite (IMU + wheel encoder), use SENTINEL's P(DEGRADED) as a **mode-switch trigger** — not as direct R-inflation. On a GNSS-only platform (no IMU, no encoder), adaptive-R wins clearly above 20 m multipath.

---

## Satellite Strip

Shows the number of visible GPS satellites at each epoch across the full drive.

- **Green bars:** Good satellite count (≥7 satellites = reliable 3D fix)
- **Amber bars:** Marginal (4–6 satellites = degraded DOP)
- **Red/short bars:** Blockage (< 4 satellites = no reliable fix)

The drop-off zones in the strip correspond exactly to where the trajectory map shows the raw GNSS track diverging from ground truth.

---

## Frequently Asked Questions — Sensor Fusion

**Q: Why is the RMSE measured only during blockage, not the full drive?**  
A: In open sky, all filters perform similarly — GNSS SPP gives 2–3 m accuracy and every filter tracks it closely. The interesting difference only appears when GNSS is blocked. Reporting full-drive RMSE would dilute the signal and hide the benefit.

**Q: What is "wheel odometry + NHC + ZUPT"?**  
A: These are three motion constraints that allow the EKF to keep positioning even when GNSS drops:

- **Wheel odometry:** Forward velocity from wheel rotation speed sensor. Gives accurate speed along the driving direction.
- **NHC (Non-Holonomic Constraint):** A land vehicle cannot slide sideways — lateral velocity must be ~0. This eliminates one degree of freedom and dramatically reduces position drift.
- **ZUPT (Zero-velocity Update):** When the vehicle is stopped (speed ≈ 0), use this to reset IMU bias drift. Very effective at traffic lights.

**Q: Why does the Aided EKF (fixed-R) use 6.4 m blockage RMSE but the EKF without aiding uses 12.1 m?**  
A: The difference is entirely the aiding constraints. Without wheel odometry, the filter relies on the IMU gyroscope + accelerometer alone, which drifts. With wheel speed + NHC, the filter knows exactly how fast the car is moving and that it isn't sliding — this collapses the uncertainty by ~50%.

**Q: If fixed-R is better, why did we build adaptive-R at all?**  
A: Adaptive-R is the right architecture for GNSS-only platforms (drones, ships, cheap IoT trackers, phones) that have no wheel encoder. For those, there is no dead-reckoning backup — so the filter's only choice is whether to use corrupted GNSS (low R) or to wait for a valid fix (high R). SENTINEL's P(DEGRADED) makes that choice predictively rather than reactively.

**Q: What is "semi-synthetic" validation?**  
A: The trajectory is 100% real (SPAN-INS driven, real streets). The GNSS positions are synthesised by taking the real Trimble SPP output and adding physically-motivated multipath bias + noise only inside discrete blockage windows that match real building geometry. This gives a controlled ground truth while keeping the motion and sensor dynamics authentic.

**Q: What does the slide say about the EKF results?**  
A:

- Synthetic blockage test: **−33.8%** improvement (54.4 m → 36.0 m)
- Semi-synthetic Tokyo: **+82%** improvement (36.3 m → 6.4 m)
- Fully real Tokyo: **+48.8%** improvement (47.4 m → 24.3 m)

The fully real run uses real RTKLIB SPP positions as GNSS input (no synthetic bias injection) and evaluates against SPAN-INS. The improvement comes from the EKF's motion model filling the gap when satellites drop, not from SENTINEL specifically — SENTINEL's role is to pre-warn the filter, not to replace it.

**Q: What does "engine" mean in the banner?**  
A: The `engine` field shows which positioning processing pipeline generated the GNSS positions: `RTKLIB SPP` means the positions were computed using RTKLIB (open-source) in Single Point Positioning mode from the raw RINEX observations.

**Q: Why is the path shown in metres and not on a real map (e.g. Google Maps)?**  
A: For privacy, accuracy, and offline capability. The dashboard converts lat/lon to a local East-North (ENU) coordinate frame centred on the start point. This also avoids any external map API dependency — the dashboard runs fully offline.

---

## Glossary

| Term            | Definition                                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------------------------- |
| **GNSS**        | Global Navigation Satellite System — umbrella term for GPS (USA), GLONASS (Russia), BeiDou (China), Galileo (EU) |
| **GPS**         | The US constellation specifically. Colloquially used to mean GNSS                                                |
| **SPP**         | Single Point Positioning — simplest GNSS solution, 2–5 m accuracy, no base station                               |
| **RTK**         | Real-Time Kinematic — cm-level GNSS using carrier phase + base station                                           |
| **RTKLIB**      | Open-source toolkit for GNSS processing. We use it in SPP mode to get positions from RINEX files                 |
| **RINEX**       | Receiver Independent Exchange Format — standard file format for raw GNSS measurements                            |
| **Trimble**     | Professional GNSS receiver brand (here: Trimble R10 or equivalent survey receiver)                               |
| **u-blox F9P**  | Dual-frequency GNSS receiver module. Popular in drones and research (~$200)                                      |
| **SPAN-INS**    | NovAtel Synchronized Position Attitude Navigation — tactical IMU + RTK fusion, cm-level ground truth             |
| **EKF**         | Extended Kalman Filter — recursive Bayesian estimator for non-linear systems                                     |
| **NHC**         | Non-Holonomic Constraint — land vehicles cannot slide laterally; used as a virtual measurement                   |
| **ZUPT**        | Zero-velocity Update — IMU bias reset applied when vehicle speed ≈ 0                                             |
| **IMU**         | Inertial Measurement Unit — accelerometers + gyroscopes, measures motion at 100 Hz                               |
| **RMSE**        | Root Mean Square Error — standard accuracy metric, here in metres vs SPAN-INS truth                              |
| **Multipath**   | GNSS signal reflections off buildings that corrupt the pseudorange measurement                                   |
| **DOP**         | Dilution of Precision — how satellite geometry amplifies positioning error                                       |
| **Blockage**    | Period when GNSS satellites are physically blocked (building overhang, tunnel, canyon)                           |
| **P(DEGRADED)** | SENTINEL's output probability that GNSS quality will degrade in the next 5/15/30 s                               |
| **Adaptive-R**  | EKF variant where measurement noise R grows with P(DEGRADED), reducing GNSS trust pre-emptively                  |
| **Fixed-R**     | EKF variant where measurement noise R is constant — always trusts GNSS equally                                   |
| **Aiding**      | Supplementary sensors (wheel encoder, IMU) that let the filter continue when GNSS drops                          |
