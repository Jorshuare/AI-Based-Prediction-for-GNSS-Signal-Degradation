# SENTINEL-GNSS: AI-Based Prediction for GNSS Signal Degradation

> Predict GNSS signal degradation 5–30 seconds before failure so an autonomous platform can switch to backup localization before position accuracy is lost.

---

## Project Overview

GNSS receivers fail silently in urban environments. The receiver keeps reporting a position even when that position is wrong. This project builds a supervised machine-learning model that monitors the _leading indicators_ of GNSS failure — falling C/N0, rising PDOP, increasing position uncertainty, growing carrier-phase residuals — and fires an early warning before the position solution degrades to an unusable state.

The model is trained on five environment scenarios:

| Label | Scenario             | Description                                                                                     |
| ----- | -------------------- | ----------------------------------------------------------------------------------------------- |
| A     | Instant blockage     | Abrupt transition from open sky to complete signal loss (tunnel entrance, underground car park) |
| B     | Urban canyon         | Sustained multipath and partial blockage between tall buildings                                 |
| C     | Partial blockage     | Stable but reduced signal under tree canopy, overhang, or partial roof                          |
| D     | Open sky             | Baseline — clean geometry, maximum signal strength                                              |
| E     | Approaching blockage | Gradual smooth degradation while moving toward a blocking structure                             |

---

## Repository Structure

```
Team-Pilot-Project/
│
├── data/                         ← All data (raw + processed + labelled)
│   ├── README.md                 ← Full data documentation and download instructions
│   ├── raw/
│   │   ├── supervisor/           ← Supervisor-provided drone and vehicle RINEX data
│   │   ├── our_collection/       ← Our Septentrio field collection (5 scenarios)
│   │   └── public/
│   │       ├── urbannav/         ← UrbanNav: HK-Medium-Urban-1, HK-Tunnel-1, tokyo
│   │       ├── nclt/             ← NCLT: to be downloaded (see data/README.md)
│   │       ├── oxford/           ← Oxford RobotCar: to be downloaded (see data/README.md)
│   │       └── kaist/            ← KAIST: deferred
│   ├── rinex/                    ← RINEX files after format conversion
│   ├── processed/                ← RTKLIB .pos files + extracted feature CSVs
│   └── labelled/                 ← Final labelled training data
│
├── src/
│   ├── processing/               ← Full pipeline scripts (RTKLIB → features → labels)
│   │   ├── pipeline.py           ← Master pipeline runner (run this)
│   │   ├── our_collection_processor.py
│   │   ├── nclt_processor.py
│   │   └── oxford_processor.py
│   ├── extraction/               ← Dataset-specific GNSS parsers
│   │   ├── supervisor_vehicle.py
│   │   ├── supervisor_drone.py
│   │   ├── urbannav_extractor.py
│   │   ├── nclt_extractor.py
│   │   ├── oxford_extractor.py
│   │   └── kaist_extractor.py
│   ├── rtklib/
│   │   └── rtklib_pipeline.py    ← RTKLIB automation for RINEX → .pos
│   ├── features/
│   │   ├── feature_extractor.py  ← Extract 35 raw base features from .pos files (model uses 37 after feature_prep.py)
│   │   └── dataset_assembler.py  ← Combine + train/val/test split
│   ├── labeling/
│   │   └── labeler.py            ← Assign scenario labels to feature windows
│   └── utils/
│       └── analyze_route_testing_v2.py  ← Phone GNSS log analysis
│
├── docs/
│   └── receiver_guide/           ← Septentrio receiver manual + sample output
│       ├── sample_output/        ← Example .25O, .25N, .pos files from real collection
│       └── lab_reference/        ← MATLAB RINEX parsers from course lab
│
├── route_planning/               ← Phone reconnaissance data + analysis charts
│   ├── phone_a/                  ← Android GNSS Logger files (Phone A)
│   ├── Phone_b/                  ← Android GNSS Logger files (Phone B) + GPX/KML routes
│   └── analysis/                 ← Generated charts (phone_a and phone_b)
│
├── proposal/                     ← Project proposal documents and presentations
├── results/                      ← Model training outputs
├── notebooks/                    ← Jupyter notebooks for exploration
├── config/                       ← RTKLIB configuration files
│
├── PROJECT_GUIDE_LAYMAN_EXPLANATION.md   ← Master field guide (read this before going out)
└── README.md                             ← This file
```

---

## Quick Start

### 1. Environment Setup

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install pandas numpy matplotlib pyproj scikit-learn
```

### 2. RTKLIB Setup

RTKLIB must be installed at `C:\Program Files\RTKLIB\`.
Download from: https://rtkexplorer.com/downloads/rtklib-code/

Verify installation:

```powershell
& "C:\Program Files\RTKLIB\bin\rnx2rtkp.exe" --help
```

### 3. Processing Our Own Collection Data

After collecting data in the field with the Septentrio receiver:

```powershell
# Place .25O, .25N, .25G, .25P files under data/raw/our_collection/scenario_A/ etc.
python src/processing/our_collection_processor.py --all
python src/features/feature_extractor.py --input data/processed/our_collection/scenario_A_solution.pos --output data/processed/our_collection/scenario_A.features.csv --source our_collection_A
python src/labeling/labeler.py
```

### 4. Processing Public Datasets

See `data/README.md` for download instructions for NCLT and Oxford.

```powershell
python src/processing/nclt_processor.py       # After downloading NCLT
python src/processing/oxford_processor.py     # After downloading Oxford
python src/extraction/urbannav_extractor.py   # UrbanNav already present
```

### 5. Full Pipeline

```powershell
python src/processing/pipeline.py --all
```

### 6. Analyze Phone Reconnaissance Data

```powershell
python src/utils/analyze_route_testing_v2.py route_planning/phone_a route_planning/analysis --dataset-name phone_a
python src/utils/analyze_route_testing_v2.py route_planning/Phone_b route_planning/analysis/phone_b --dataset-name phone_b
```

---

## Data Sources

| Dataset                         | Location                                    | City      | Purpose                                         | Status                     |
| ------------------------------- | ------------------------------------------- | --------- | ----------------------------------------------- | -------------------------- |
| Supervisor vehicle (Septentrio) | `data/raw/supervisor/vehicle/`              | Beihang   | Urban + suburban driving                        | ✅ Processed               |
| Supervisor drone (Septentrio)   | `data/raw/supervisor/drone/`                | Beihang   | Aerial open-sky reference (training excluded)   | ✅ Processed               |
| Field collection — Scenarios    | `data/raw/scenarios/`                       | Beihang   | 5 controlled degradation scenarios (A–E)        | ✅ Processed               |
| UrbanNav HK-Medium-Urban-1      | `data/raw/public/urbannav/urbanNav_Medium/` | Hong Kong | Urban canyon, 10 receivers simultaneously       | ✅ Processed               |
| UrbanNav HK-Tunnel-1            | `data/raw/public/urbannav/urbanNav_tunnel/` | Hong Kong | Complete signal loss (cross-harbour tunnel)     | ✅ Processed               |
| **UrbanNav HK-Deep-Urban-1**    | `data/raw/public/urbannav/urbanNav_Deep/`   | Hong Kong | Dense urban canyon, Whampoa, 10 receivers       | ✅ Processed (15,233 rows) |
| **UrbanNav HK-Harsh-Urban-1**   | `data/raw/public/urbannav/urbanNav_Harsh/`  | Hong Kong | Extreme urban canyon, Mong Kok, 10 receivers    | ✅ Processed (33,429 rows) |
| UrbanNav Tokyo-Odaiba           | `data/raw/public/urbannav/Tokyo/Odaiba/`    | Tokyo     | Mixed open-sky + moderate urban                 | ✅ Processed               |
| UrbanNav Tokyo-Shinjuku         | `data/raw/public/urbannav/Tokyo/Shinjuku/`  | Tokyo     | Dense urban canyon                              | ✅ Processed               |
| NCLT                            | `data/raw/public/nclt/`                     | Michigan  | Campus driving (excluded: GPS-only artifact)    | ✅ Processed               |
| Oxford RobotCar                 | `data/raw/public/oxford/`                   | Oxford    | Cross-continent (excluded: 2014 position-sigma) | ✅ Processed               |

**Combined labelled dataset (Run 12):** **146,055 rows** × 41 columns across **12 source groups** and 4 cities.

| Role                                     | Cities / Sources                                                                       |
| ---------------------------------------- | -------------------------------------------------------------------------------------- |
| **Training + in-domain test**            | Beihang (Hangzhou) field collection + UrbanNav Hong Kong (Medium, Deep, Harsh, Tunnel) |
| **Cross-city zero-shot evaluation only** | UrbanNav Tokyo Shinjuku (never in training)                                            |
| **Excluded from training**               | NCLT (Michigan), Oxford RobotCar, drone data                                           |

Labels: CLEAN ~45%, WARNING ~42%, DEGRADED ~13% (varies by split — see NEXT_STEPS.md).

**Note on exclusions:** Drone data (all CLEAN, no degradation signal), NCLT (num_satellites artifact), and Oxford 2014 (GPS-only, labels derived from position sigma only) are excluded from the primary training/test pipeline via `DEFAULT_EXCLUDE_SOURCES` in `feature_prep.py`. **UrbanNav Tokyo** data are also excluded from the main train/val/test windows and reserved exclusively for the cross-city zero-shot experiment (E6 in `reviewer_experiments.json`). All excluded sources remain in the combined CSV for research reference.

---

## RTKLIB — What It Does and Why

RTKLIB converts raw GNSS measurements (RINEX files from the receiver) into a **post-processed position solution** (`.pos` file). It applies:

- Integer ambiguity resolution (carrier-phase RTK) for centimetre accuracy
- Differential corrections using a base station (if available)
- Kalman filter smoothing over the trajectory

**Output quality codes (Q column in .pos file):**

| Q   | Meaning                | Accuracy |
| --- | ---------------------- | -------- |
| 1   | Fixed RTK              | 1–3 cm   |
| 2   | Float RTK              | 10–30 cm |
| 5   | Single (no correction) | 3–10 m   |

The Q column itself is one of the most powerful features for the model: transitions from Q=1 → Q=2 → Q=5 directly indicate degradation onset.

Full RTKLIB usage documentation: `data/README.md` → section "RTKLIB Explained"

---

## Feature Engineering

The model uses **37 standardized features** extracted from each 1-second epoch of a `.pos` file. Features are grouped into 7 categories:

| Category               | Features                                                                      |
| ---------------------- | ----------------------------------------------------------------------------- |
| Position               | lat, lon, alt, lat_std, lon_std                                               |
| Signal Strength (C/N0) | mean_cnr, min_cnr, max_cnr, std_cnr, cnr_trend                                |
| Satellite Count        | num_satellites, sat_mean, sat_min, sat_visibility, sat_drop_rate              |
| DOP                    | pdop, hdop, vdop, gdop, dop_ratio                                             |
| Receiver Status        | solution_status, baseline_sats, solution_age, fix_continuity, fix_transitions |
| Temporal Patterns      | position_variance, cnr_variance, elevation_violations, multipath, clock_bias  |
| Atmospheric Effects    | iono_delay, tropo_delay, cycle_slips, residual_mean, residual_std             |
| Added features         | cnr_available (flag), pdop_delta, hdop_delta (Run 6), receiver_tier (Run 7)   |

See `src/features/feature_extractor.py` for exact computation logic.

---

## Train / Validation / Test Split

**Session-based split** — each source group's sessions are assigned 70/15/15 by session (not by epoch). `SPLIT_REASSIGN` then moves specific high-DEGRADED sessions to training to ensure sufficient minority-class representation. This prevents temporal data leakage while maximising training signal for rare classes (Bergmeir & Benitez, 2012).

**Current split (Run 12, with Deep+Harsh, before SMOTE):**

| Split      | Windows | CLEAN  | WARNING | DEGRADED |
| ---------- | ------- | ------ | ------- | -------- |
| Train      | 59,854  | 10,563 | 37,295  | 11,996   |
| Validation | 17,850  | 13,704 | 3,229   | 917      |
| Test       | 1,452   | 671    | 726     | 55       |

SMOTE is applied to training only — training set balanced to 37,295 per class (111,885 total after SMOTE). Val and test windows are never modified.

**Test set composition:** 3 supervisor vehicle sessions (Beihang campus only) — the model never sees any Beihang campus data during training, making the test set a genuine held-out cross-city evaluation. Test DEGRADED=55 is by design and does not change regardless of training data volume.

Random shuffling is explicitly forbidden. GNSS data is sequential — shuffling allows the model to "see the future" during training and inflates test accuracy without real generalization (Bergmeir & Benitez, 2012).

---

## Current Model Performance

**Run 12 — Transformer-LSTM (checkpoint_best.pt, epoch 16 of 73)** ← Current best

Architecture: TransformerEncoder (2 layers, 8 heads, d_model=128) → LSTM (2 layers, hidden=256, unidirectional) → 3 output heads + 1 aux head. Input: 37 features × 30-step sliding window. Temperature calibration T=0.4442.

| Horizon | Accuracy | Macro-F1   | MCC    | 95% CI (MacroF1) |
| ------- | -------- | ---------- | ------ | ---------------- |
| +5s     | 0.8472   | **0.7036** | 0.7707 | [0.671, 0.735]   |
| +15s    | 0.8009   | 0.6293     | 0.6975 | [0.606, 0.655]   |
| +30s    | 0.8275   | 0.6043     | 0.7125 | [0.589, 0.622]   |

Best validation MacroF1 = **0.8627** (balanced class subset, epoch 16).
DEGRADED F1 at +5s = **0.307** (P=0.216, R=0.527) — improved from Run 10's 0.274.
WARNING F1 at +5s = **0.851** — primary gain from Deep+Harsh training data.

**LSTM-only ablation (Run 12):** val MacroF1=0.8593, +5s MacroF1=0.6082, DEGRADED F1=0.165
**Transformer-only ablation:** not yet trained — pending Run 13.

---

## References

- UrbanNav Dataset: Hsu et al., NAVIGATION 2023. https://doi.org/10.33012/navi.602
- Oxford RobotCar: Maddern et al., IJRR 2016
- NCLT Dataset: Carlevaris-Bianco et al., IJRR 2016. https://robots.engin.umich.edu/nclt/
- RTKLIB: Takasu T., 2011. https://rtklib.com
- Septentrio AsteRx: https://www.septentrio.com
- Focal Loss: Lin et al., ICCV 2017. arXiv:1708.02002
- SMOTE: Chawla et al., JAIR 2002. doi:10.1613/jair.953
- Temporal split: Bergmeir & Benitez, Neural Networks 2012. doi:10.1016/j.neunet.2011.07.014
- Temperature calibration: Guo et al., ICML 2017. arXiv:1706.04599
