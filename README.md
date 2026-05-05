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
│   │   ├── feature_extractor.py  ← Extract 35 features from .pos files
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

| Dataset                         | Location                                      | Size (GNSS only) | Purpose                                           | Status             |
| ------------------------------- | --------------------------------------------- | ---------------- | ------------------------------------------------- | ------------------ |
| Our collection (Septentrio)     | `data/raw/our_collection/`                    | ~10–50 MB        | Primary labeled training data for all 5 scenarios | To be collected    |
| Supervisor vehicle (Septentrio) | `data/raw/supervisor/vehicle/`                | ~20 MB           | Training + validation                             | Present            |
| Supervisor drone (Septentrio)   | `data/raw/supervisor/drone/`                  | ~5 MB            | Training + validation                             | Present            |
| UrbanNav HK-Medium-Urban-1      | `data/raw/public/urbannav/HK-Medium-Urban-1/` | ~100 MB          | Scenario B validation (urban canyon)              | Present            |
| UrbanNav HK-Tunnel-1            | `data/raw/public/urbannav/HK-Tunnel-1/`       | ~8 MB            | Scenario A validation (complete loss)             | ✅ Extracted       |
| UrbanNav Tokyo                  | `data/raw/public/urbannav/tokyo/`             | ~60 MB           | Cross-country generalization                      | Present            |
| NCLT                            | `data/raw/public/nclt/`                       | ~50 MB           | Long-term stability test                          | Not yet downloaded |
| Oxford RobotCar                 | `data/raw/public/oxford/`                     | ~50 MB           | Global generalization                             | Not yet downloaded |
| KAIST                           | `data/raw/public/kaist/`                      | TBD              | Deferred                                          | Not downloaded     |

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

The model uses 35 standardized features extracted from each 1-second epoch of a `.pos` file. Features are grouped into 7 categories:

| Category               | Features                                                                      |
| ---------------------- | ----------------------------------------------------------------------------- |
| Position               | lat, lon, alt, lat_std, lon_std                                               |
| Signal Strength (C/N0) | mean_cnr, min_cnr, max_cnr, std_cnr, cnr_trend                                |
| Satellite Count        | num_satellites, sat_mean, sat_min, sat_visibility, sat_drop_rate              |
| DOP                    | pdop, hdop, vdop, gdop, dop_ratio                                             |
| Receiver Status        | solution_status, baseline_sats, solution_age, fix_continuity, fix_transitions |
| Temporal Patterns      | position_variance, cnr_variance, elevation_violations, multipath, clock_bias  |
| Atmospheric Effects    | iono_delay, tropo_delay, cycle_slips, residual_mean, residual_std             |

See `src/features/feature_extractor.py` for exact computation logic.

---

## Train / Validation / Test Split

Time-based split (not random) — mandatory for time-series data to prevent data leakage:

| Split      | Data source                                      | Ratio |
| ---------- | ------------------------------------------------ | ----- |
| Train      | Our collection (scenarios A–E) + supervisor data | 70%   |
| Validation | UrbanNav HK + Tokyo                              | 15%   |
| Test       | NCLT + Oxford                                    | 15%   |

Random shuffling is explicitly forbidden. GNSS data is sequential — shuffling allows the model to "see the future" during training and inflates test accuracy without real generalization.

---

## References

- UrbanNav Dataset: Hsu et al., NAVIGATION 2023. https://doi.org/10.33012/navi.602
- Oxford RobotCar: Maddern et al., IJRR 2016
- NCLT Dataset: Carlevaris-Bianco et al., IJRR 2016. https://robots.engin.umich.edu/nclt/
- RTKLIB: Takasu T., 2011. https://rtklib.com
- Septentrio AsteRx: https://www.septentrio.com
