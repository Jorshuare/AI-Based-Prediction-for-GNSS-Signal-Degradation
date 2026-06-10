# EKF Section — Visuals, Charts & Dashboard Screenshots
## Complete breakdown of every image to add, where it goes, and how to generate it

> **Presentation file:** `docs/SENTINEL_GNSS_Presentation_V6.pptx`  
> **EKF section:** Slides 23–29  
> **Dashboard section:** Slides 28–29

---

## OVERVIEW — What each EKF slide currently has vs needs

| Slide | Title | Has now | Needs |
|-------|-------|---------|-------|
| 23 | 5 · EKF divider | Section title only | Nothing (divider is fine) |
| 24 | Standard vs Adaptive EKF | Text bullets + placeholder image | Replace placeholder with the predict/update loop diagram |
| 25 | Adaptive-R Formula | Formula text + annotations | Add annotated equation image + R(t) timeline plot |
| 26 | EKF Results — 3 Tiers | Stats + table | Add trajectory+bar combined figure (already generated) |
| 27 | Severity Sweep | Text bullets only — **no chart at all** | Add severity sweep line chart (already generated) |
| 28 | Dashboard Overview | Panel list (text) | Add full dashboard screenshot + individual panel screenshots |
| 29 | Live Demo | Demo step table | Add annotated demo screenshots |

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

| Figure | Content | Placement |
|--------|---------|-----------|
| `fig08_ekf_trajectory.png` | Trajectory map (Synthetic data, blockage zone highlighted) | Left half |
| `fig07_ekf_rmse.png` | Bar chart: GNSS 54.4m → Fixed 45.6m → Adaptive 36.0m (blockage RMSE) | Right half |

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
  - Gold: Aided EKF Adaptive-R (similar to fixed, slightly higher at crossover ~30 m)
- Key annotation: "with wheel-odometry + NHC + ZUPT aiding, keeping GNSS (fixed-R) stays best: inflating R discards heading aiding"

### Why this is important for the presentation
The chart directly proves the "practical rule" statement already on the slide: adaptive-R is best for **GNSS-only platforms** in deep canyons; for full AV sensor suite (IMU + odometry), SENTINEL's role is the **mode-switch trigger**, not R-inflation.

### Suggested annotation to add in PowerPoint
Draw a red callout arrow pointing to where the adaptive-R line exceeds the fixed-R line (~30 m crossover) with text:  
**"Adaptive-R wins when multipath bias > ~30 m (deep urban canyon / tunnel)"**

---

## SLIDE 28 — "SENTINEL-GNSS Dashboard — Real-Time Analytics"

### Dashboard component map

| Panel # | Component file | What it shows |
|---------|---------------|---------------|
| 01 | `SignalGauge.tsx` | P(DEGRADED) at +5s / +15s / +30s — dial gauge, green/amber/red |
| 02 | `ProbabilityBars.tsx` | CLEAN / WARNING / DEGRADED bars per horizon |
| 03 | `TrajectoryMap.tsx` | Vehicle path on map, coloured by risk level |
| 04 | `TimeSeriesChart.tsx` | P(DEGRADED) streaming timeline, 3 horizons |
| 05 | `EkfPanel.tsx` | Blocked RMSE comparison by filter type |
| 06 | `AlarmCenter.tsx` | CRITICAL / WARNING alert feed with timestamps |

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

| Position | Screenshot | Caption |
|----------|-----------|---------|
| Left | `panel_01_signal_gauge_clean.png` → `panel_01_signal_gauge_critical.png` (side-by-side) | "Step 1: Signal transitions CLEAN → CRITICAL (5 s warning)" |
| Centre | `panel_04_pdeg_timeline_spike.png` | "Step 2: P(DEGRADED) spikes — +5s / +15s / +30s all rise" |
| Right | `panel_06_alert_centre_active.png` | "Step 3: CRITICAL alert fires — AV route planner notified" |

### Demo script (updated with visual cues)

**Step 1 — Show CLEAN state (0:00–0:30)**
> "Dashboard is live. All gauges green. P(DEGRADED) flat near zero across all three horizons."  
> *Point to Screenshot: `panel_01_signal_gauge_clean.png`*

**Step 2 — Trigger degradation sequence (0:30–1:30)**
> "Watch the +5s gauge. SENTINEL is reading the GNSS features — satellite count dropping, C/N₀ degrading. P(DEGRADED @+5s) climbing..."  
> *Point to Screenshot: `panel_04_pdeg_timeline_spike.png`*

**Step 3 — CRITICAL alert fires (1:30–2:00)**
> "Alert fired — CRITICAL at 5 seconds out. The EKF has already started inflating R. The vehicle hasn't lost positioning yet, but the filter is already preparing the handoff to dead-reckoning."  
> *Point to Screenshot: `panel_06_alert_centre_active.png`*

**Step 4 — Show trajectory map (2:00–2:30)**
> "Look at the trajectory map — the path turns red right where we predicted. Ground truth is within 24 metres. Without adaptive-R it would be 47 metres."  
> *Point to Screenshot: `panel_03_trajectory_risk_coloured.png`*

**Step 5 — EKF analytics (2:30–3:00)**
> "Panel 5 shows the filter comparison live. Adaptive EKF consistently outperforms Fixed-R in the blocked segment. That's the SENTINEL loop closed — prediction into action."  
> *Point to Screenshot: `panel_05_ekf_analytics.png`*

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
"Zero-shot cross-city generalisation — trained on Beijing (Beihang A–E) + HK UrbanNav  
 |  tested on Tokyo Shinjuku (zero Tokyo data in training)"

Typography: Inter, Helvetica, or any clean sans-serif. Avoid decorative fonts.
```

---

## QUICK REFERENCE — Which existing figures to use on which slide

| Slide | File to insert | Location on slide |
|-------|---------------|-------------------|
| 24 | `results/paper_figures/fig_ekf_mechanism_concept.png` | Bottom-centre (below text columns) OR replace with new generated version |
| 25 | External: annotated equation image (Prompt above) | Left half (replace placeholder) |
| 25 | `results/paper_figures/fig18_ekf_realdata.png` (panel b only) | Right half |
| 26 | `results/paper_figures/figC3_ekf.png` | Bottom two-thirds (keeps headline stats above) |
| 27 | `results/paper_figures/fig22_urbannav_severity_sweep.png` | Right half (left half keeps bullet text) |
| 28 | `docs/screenshots/dashboard_full_overview.png` | Centre-left (~60% width) |
| 29 | 3-panel strip: gauge + timeline + alerts | Bottom strip |

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
