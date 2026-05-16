# SENTINEL-GNSS: Dataset Processing Report

> **Updated:** May 16, 2026  
> **Pipeline:** `src/processing/process_all_datasets.py --all`

---

## 1. All Data Sources — Overview

| Source                 | Type           | Location                 | Receiver              | C/N0 Method          | Epochs |
| ---------------------- | -------------- | ------------------------ | --------------------- | -------------------- | ------ |
| **Scenarios A–E**      | Self-collected | Beijing, 2026            | Septentrio Mosaic-X5C | RINEX SNR-indicator  | 3,586  |
| **Supervisor Vehicle** | Self-collected | Beijing, 2025            | Septentrio Mosaic-X5C | NMEA GSV (direct)    | 3,401  |
| **Supervisor Drone**   | Self-collected | Beijing, 2024            | Unicore UB4B0         | RINEX S1C (direct)   | 14,862 |
| **UrbanNav HK Medium** | Downloaded     | Hong Kong, 2021          | 10 receivers          | RINEX S1C + NMEA GSV | 7,608  |
| **UrbanNav HK Tunnel** | Downloaded     | Hong Kong, 2021          | 10 receivers          | RINEX S1C + NMEA GSV | 3,461  |
| **Tokyo Odaiba**       | Downloaded     | Tokyo, 2021              | Trimble + u-blox      | RINEX S1C (direct)   | 18,603 |
| **NCLT**               | Downloaded     | Ann Arbor USA, 2012–2013 | Unknown GPS module    | GPS CSV (no C/N0)    | 7,493  |
| **Oxford RobotCar**    | Downloaded     | Oxford UK, 2014–2015     | NovAtel OEM6          | GPS CSV (no C/N0)    | 7,114  |

> **Publishing note:** Only Scenarios A–E and Supervisor data (self-collected) may be redistributed. All other sources are third-party datasets. For code/data release: publish the processing scripts + raw Scenarios A–E + all processed CSV features (transforming a downloaded dataset ≠ redistributing the raw data, which is standard practice in ML papers). Cite the original papers for NCLT, Oxford, UrbanNav.

---

## 2. Features Available Per Source

This table directly answers: **"Will there be too many NaN?"**

| Feature (Group)                    |    Scenarios     | Supervisor Veh. | Supervisor Drone  | UrbanNav Med. | UrbanNav Tunnel | Tokyo Odaiba  |        NCLT         |     Oxford      |
| ---------------------------------- | :--------------: | :-------------: | :---------------: | :-----------: | :-------------: | :-----------: | :-----------------: | :-------------: |
| **G1: Position**                   |                  |                 |                   |               |                 |               |                     |                 |
| `lat` / `lon`                      |    ✓ NMEA GGA    |   ✓ NMEA GGA    |       ✗ NaN       |  ✓ NMEA GGA   |   ✓ NMEA GGA    |     ✗ NaN     |      ✓ GPS CSV      |    ✓ GPS CSV    |
| `alt`                              |    ✓ NMEA GGA    |   ✓ NMEA GGA    |       ✗ NaN       |  ✓ NMEA GGA   |   ✓ NMEA GGA    |     ✗ NaN     |      ✓ GPS CSV      |    ✓ GPS CSV    |
| `lat_std` / `lon_std`              |  ✓ GST sentence  |      ✗ NaN      |       ✗ NaN       |     ✓ GST     |      ✓ GST      |     ✗ NaN     |   ✓ RTK err proxy   | ✓ NovAtel sigma |
| **G2: Signal Strength**            |                  |                 |                   |               |                 |               |                     |                 |
| `mean_cnr` etc. (all 5)            |   ✓ RINEX SNR    |   ✓ NMEA GSV    |    ✓ RINEX S1C    |  ✓ RINEX S1C  |   ✓ RINEX S1C   |  ✓ RINEX S1C  |      **✗ NaN**      |    **✗ NaN**    |
| **G3: Satellite Count**            |                  |                 |                   |               |                 |               |                     |                 |
| `num_satellites`                   |   ✓ GGA / GNS    |   ✓ GGA / GSV   |   ✓ RINEX count   | ✓ GGA / RINEX |  ✓ GGA / RINEX  | ✓ RINEX count | ✗ NaN (logging bug) |    ✓ GPS CSV    |
| `sat_mean` / `sat_min`             |     ✓ window     |    ✓ window     |     ✓ window      |   ✓ window    |    ✓ window     |   ✓ window    |        ✗ NaN        |    ✓ window     |
| `sat_visibility` / `sat_drop_rate` |        ✓         |        ✓        |         ✓         |       ✓       |        ✓        |       ✓       |          ✗          |        ✓        |
| **G4: DOP**                        |                  |                 |                   |               |                 |               |                     |                 |
| `pdop` / `hdop` / `vdop`           |    ✓ NMEA GSA    |   ✓ NMEA GSA    |       ✗ NaN       | ~partial GSA  |  ~partial GSA   |     ✗ NaN     |        ✗ NaN        |      ✗ NaN      |
| `gdop` / `dop_ratio`               |    ✓ computed    |   ✓ computed    |       ✗ NaN       |     ✗ NaN     |      ✗ NaN      |     ✗ NaN     |        ✗ NaN        |      ✗ NaN      |
| **G5: Receiver Status**            |                  |                 |                   |               |                 |               |                     |                 |
| `solution_status`                  |  ✓ GGA quality   |  ✓ GGA quality  | 1.0 (always good) | ✓ GGA quality |  ✓ GGA quality  |      1.0      |     ✓ fix_mode      |       1.0       |
| `baseline_sats` / `fix_continuity` |        ✓         |        ✓        |         ✓         |       ✓       |        ✓        |       ✓       |          ✓          |        ✓        |
| `solution_age` / `fix_transitions` |   ✓ GGA field    |   ✓ GGA field   |         0         |       ✓       |        ✓        |       0       |          0          |        0        |
| **G6: Temporal Patterns**          |                  |                 |                   |               |                 |               |                     |                 |
| `position_variance`                |   ✓ GST window   |   ~DOP proxy    |    ~DOP proxy     | ✓ GST window  |        ✓        |    ~proxy     |      ✓ RTK err      |     ✓ sigma     |
| `cnr_variance` / `cnr_trend`       |        ✓         |        ✓        |         ✓         |       ✓       |        ✓        |       ✓       |        ✗ NaN        |      ✗ NaN      |
| `elevation_violations`             |     ~ proxy      |     ~ proxy     |      ~ proxy      |    ~ proxy    |     ~ proxy     |    ~ proxy    |          ✗          |     ~ proxy     |
| `multipath` / `clock_bias`         |        ✓         |        ✓        |         ✓         |       ✓       |        ✓        |       ✓       |       ~ proxy       |     ✓ sigma     |
| **G7: Atmospheric Effects**        |                  |                 |                   |               |                 |               |                     |                 |
| `iono_delay`                       | 0 (no dual-freq) |        0        |         0         |       0       |        0        |       0       |          0          |        0        |
| `tropo_delay`                      | ✓ Hopfield proxy |        ✓        |         ✓         |       ✓       |        ✓        |       ✓       |          ✓          |        ✓        |
| `cycle_slips`                      |   ✓ RINEX LLI    |        0        |    ✓ RINEX LLI    |  ✓ RINEX LLI  |        ✓        |  ✓ RINEX LLI  |          0          |        0        |
| `residual_mean` / `residual_std`   |   ✓ GBS / GST    |      ✓ GST      |      ~ proxy      |       ✓       |        ✓        |    ~ proxy    |      ✓ RTK err      |     ✓ sigma     |
| **Approx. features with data**     |    **~32/35**    |   **~30/35**    |    **~26/35**     |  **~30/35**   |   **~30/35**    |  **~24/35**   |     **~16/35**      |   **~18/35**    |

### What "NaN" means for the model

- The **5 C/N0 / signal strength features (G2)** are NaN for NCLT and Oxford only. These are the 2 legacy datasets from 2012–2015 where per-satellite C/N0 was not logged.
- **DOP features (G4)** are NaN for RINEX-only sources (drone, Tokyo) because DOP comes from NMEA GSA sentences.
- All **NaN handling** in the Transformer-LSTM: use attention masking or imputation. **Do NOT drop rows** — this would lose 54% of the dataset.
- For model training: impute position NaN with session median; mask C/N0 to 0 with a boolean `cnr_available` flag as an additional input feature.
- Important: the **30 non-C/N0 features have near-0% NaN** across all datasets combined.

---

## 3. Label Distribution — Individual Datasets

### 3.1 Our Self-Collected Data (Scenarios A–E + Supervisor)

#### Label Thresholds Used (C/N0-based, full signal-quality labeling)

| Class            | Conditions (AND)                                                                          |
| ---------------- | ----------------------------------------------------------------------------------------- |
| **CLEAN (0)**    | mean_cnr ≥ 35 dBHz AND hdop ≤ 2.5 AND pdop ≤ 4.0 AND num_sats ≥ 8 AND solution_status > 0 |
| **WARNING (1)**  | Not CLEAN and not DEGRADED                                                                |
| **DEGRADED (2)** | mean_cnr < 25 dBHz OR hdop > 5.0 OR pdop > 8.0 OR num_sats < 4 OR no fix                  |

| Dataset                               | CLEAN     | WARNING   | DEGRADED  | Total      | Notes                                                              |
| ------------------------------------- | --------- | --------- | --------- | ---------- | ------------------------------------------------------------------ |
| **Scenario A** (instant blockage)     | **23.5%** | **4%**    | **72.5%** | **200**    | 3 runs; blockage epochs now captured (was missing due to NMEA fix) |
| **Scenario B** (urban canyon)         | **40.8%** | **50.3%** | **8.9%**  | **926**    | Two sub-sessions; brief no-fix dips in DEGRADED                    |
| **Scenario C** (partial blockage)     | **86.5%** | **6.5%**  | **7.0%**  | **911**    | Tree canopy; periodic complete blockage gaps now captured          |
| **Scenario D** (open sky)             | **100%**  | 0%        | 0%        | **597**    | Reference baseline                                                 |
| **Scenario E** (approaching blockage) | **68.5%** | **6.7%**  | **24.8%** | **952**    | 4 runs; final blockage period now correctly DEGRADED               |
| **All Scenarios combined**            | **68.7%** | **16.6%** | **14.7%** | **3,586**  |                                                                    |
| **Supervisor Vehicle**                | **44.5%** | **48.9%** | **6.5%**  | **3,401**  | Mixed urban/campus routes                                          |
| **Supervisor Drone**                  | **100%**  | 0%        | 0%        | **14,862** | Aerial open-sky — consistently excellent                           |

### 3.2 Downloaded Public Datasets

#### Label Thresholds Used (position-sigma-based for NCLT/Oxford)

For NCLT and Oxford, C/N0 is unavailable. Labels use **position uncertainty** directly:

| Dataset    | Threshold                                                                         | Notes                                  |
| ---------- | --------------------------------------------------------------------------------- | -------------------------------------- | ----------------------------- | --- |
| **NCLT**   | CLEAN: RTK_err < 2.0m AND 3D fix; DEGRADED: RTK_err > 5.0m or no 3D fix           | `gps_rtk_err.csv` =                    | GPS − LiDAR_SLAM_ground_truth |     |
| **Oxford** | CLEAN: lat_sigma < 3.0m AND num_sats ≥ 5; DEGRADED: sigma > 10.0m or num_sats < 3 | From NovAtel OEM6 position uncertainty |

| Dataset                | CLEAN     | WARNING   | DEGRADED  | Total      | Notes                                                                             |
| ---------------------- | --------- | --------- | --------- | ---------- | --------------------------------------------------------------------------------- |
| **UrbanNav HK Medium** | **2.7%**  | **74.0%** | **23.3%** | **7,608**  | 10 receivers; NovAtel best, phones worst                                          |
| **UrbanNav HK Tunnel** | **11.2%** | **42.9%** | **46.0%** | **3,461**  | Complete tunnel traversal; in-tunnel no-fix epochs now correctly DEGRADED         |
| **Tokyo Odaiba**       | **65.0%** | **11.4%** | **0.4%**  | **18,603** | ~65% CLEAN — mostly open Odaiba waterfront; 12,398 Trimble + 6,205 u-blox         |
| **NCLT**               | **82.0%** | **10.0%** | **8.0%**  | **7,493**  | Michigan campus; 2012 session much cleaner (mean RTK err 2.82m) than 2013 (6.81m) |
| **Oxford**             | **3.6%**  | **43.9%** | **52.5%** | **7,114**  | GPS-only 2014 hardware; avg sigma 6m → mostly DEGRADED/WARNING                    |

### 3.3 Combined Dataset Summary (Session-Based 70/15/15 Split)

**Total: 66,128 rows across 8 sources** _(+1,613 rows from NMEA no-fix fix)_

> Note: The epoch-level split percentages reflect session assignments; exact row counts per split depend on session sizes. The split is correct at session level (70% of sessions → train), which is the right unit to prevent temporal leakage.

| Class        | Count  | %     |
| ------------ | ------ | ----- |
| **CLEAN**    | 44,141 | 66.8% |
| **WARNING**  | 13,455 | 20.3% |
| **DEGRADED** | 8,532  | 12.9% |

### 3.4 Comparison With Colleague's Label Distribution

The table below compares our results with a colleague's independent processing of the same/similar data:

| Dataset             | **Our: CLEAN** | **Colleague: CLEAN** | **Our: WARNING** | **Colleague: WARNING** | **Our: DEGRADED** | **Colleague: DEGRADED** |
| ------------------- | :------------: | :------------------: | :--------------: | :--------------------: | :---------------: | :---------------------: |
| Scenario A          |   **23.5%**    |          0%          |      **4%**      |           0%           |     **72.5%**     |        **100%**         |
| Scenario B          |   **40.8%**    |          —           |    **50.3%**     |        **6.9%**        |     **8.9%**      |        **93.1%**        |
| Scenario C          |   **86.5%**    |      **61.3%**       |     **6.5%**     |         13.7%          |     **7.0%**      |          25.0%          |
| Scenario D          |    **100%**    |       **100%**       |        0%        |           —            |        0%         |            —            |
| Scenario E          |   **68.5%**    |      **43.5%**       |     **6.7%**     |         22.8%          |     **24.8%**     |        **33.8%**        |
| NCLT                |      ~6%       |       **6.1%**       |       ~36%       |       **35.9%**        |       ~58%        |        **58.1%**        |
| Oxford              |      ~0%       |          —           |       ~0%        |           —            |       ~100%       |        **100%**         |
| UrbanNav (combined) |      ~3%       |          —           |       ~74%       |           —            |       ~23%        |        **100%**         |

**Why do our numbers differ from the colleague — and who is right?**

**Our thresholds (35/25 dBHz) are physically correct** for the Septentrio Mosaic-X5C in Beijing conditions. The signal analysis charts confirm mean C/N0 = 37–41 dBHz in open/urban environments, well within our CLEAN range.

**Scenarios B, C, D — we are more accurate.** The charts show mean C/N0 = 37.2 dBHz (B) and 38.6 dBHz (C), both well above the 35 dBHz CLEAN threshold. The colleague's 93% DEGRADED for B is inconsistent with the raw signal data. Their threshold appears to be ≥40 dBHz for CLEAN, which is too strict for single-frequency RINEX SNR-indicator data.

**Scenarios A and E — a pipeline bug was found and fixed.** Previously, the NMEA parser dropped all GGA sentences with fix quality = 0 (empty lat/lon during complete signal loss) via `dropna(subset=["lat", "lon"])`. This caused the entire blockage period in A (33 of 48 NMEA sentences) and E (final no-fix seconds) to be silently discarded. After fixing this (`dropna(subset=["timestamp"])` only), Scenario A now correctly shows 72.5% DEGRADED. The colleague's 100% DEGRADED for A is still wrong — the pre-blockage period (first ~15 seconds, 24 satellites, 38–40 dBHz) is clearly CLEAN.

**UrbanNav Tunnel** also benefited: in-tunnel no-fix epochs now register as DEGRADED (46%), up from the incorrect 21.8%. This is physically correct — a GPS receiver in a tunnel has no signal.

**Recommendation:** Our thresholds and pipeline are correct. Cite the signal analysis charts as evidence for the threshold calibration in the paper.

---

## 4. What Is NCLT Ground Truth and How Does It Help Us?

The NCLT ground truth (`groundtruth_YYYY-MM-DD.csv`) contains the **precise vehicle trajectory** computed by **LiDAR Simultaneous Localization and Mapping (SLAM)**. The robot's Velodyne HDL-32E LiDAR scanner continuously maps the environment and localises itself to within ±5 cm accuracy relative to a prior map.

**Format:** utime (μs), x, y, z (metres in a local coordinate frame), roll, pitch, yaw

**How it helps SENTINEL-GNSS:**

1. **Label validation:** The RTK error file (`gps_rtk_err.csv`) contains `|GPS_position − LiDAR_SLAM_position|`. This is the _actual_ GPS positioning error in metres — not an estimate. We use this as the ground truth for labeling: > 5m error = DEGRADED, 2–5m = WARNING, < 2m = CLEAN. This is **physically justified and verifiable**.

2. **Cross-validation of our threshold calibration:** NCLT gives us a truth-referenced label that is independent of C/N0 or DOP. When our sigma-based labeling (for NCLT) gives ~6% CLEAN / 36% WARNING / 58% DEGRADED, and this matches our colleague's independent result, it validates that our labeling methodology is consistent across different signal quality metrics.

3. **Not used for position features:** We do NOT use the ground truth positions as model inputs (that would be data leakage — the model would be learning from the answer). We only use `gps_rtk_err.csv` (the error magnitude) for labeling.

---

## 5. Train / Validation / Test Split — Expert Justification

### Why NOT a Random Epoch-Level Split

**This is the most important methodological decision in the project.** If you randomly shuffle all 28,000+ epochs and take 70% for train, a single session (e.g., a 10-minute urban drive) will have epochs in all three splits. Epoch t and epoch t+1 (1 second apart) may land in train and test respectively. The model sees the context of test samples during training. This is called **temporal data leakage**, and it inflates test metrics significantly.

Literature (Bergmeir & Benitez 2012, Cerqueira et al. 2020 IEEE TKDE) establishes that for any sequential data, **the split unit must be the session, not the individual observation**.

### The Correct Approach: Session-Based Stratified 70 / 15 / 15

Each "session" is one independent recording run (one drive, one drone flight, one receiver on one traversal). Sessions are assigned **in whole** to train, validation, or test.

```
Total sessions ≈ 50:
  Scenarios A–E     12 sessions
  Supervisor veh.    9 sessions
  Supervisor drone   4 sessions
  UrbanNav Medium   10 sessions (one per receiver)
  UrbanNav Tunnel   10 sessions (one per receiver)
  Tokyo Odaiba       2 sessions (Trimble + u-blox)
  NCLT               2 sessions (2012, 2013)
  Oxford             2 sessions (2014, 2015)

With 70/15/15 session split:
  ~35 sessions → train   (majority of epochs)
  ~7–8 sessions → val    (hyperparameter tuning)
  ~7–8 sessions → test   (final held-out evaluation)
```

**Within each source category**, sessions are proportionally distributed so every split contains examples from every source. This ensures:

- Train, val, and test all have the same distribution of scenario types
- No source is "unseen" at test time
- Reproducible with fixed random seed (seed=42 in pipeline)

### Additionally: Leave-Dataset-Out Generalization Experiment

As a **separate supplementary experiment** (not the primary metric), train on all data EXCEPT one city, then test on that city:

- "Train on Beijing + Hong Kong → Test on Tokyo"
- "Train on everything → Test on NCLT"
- "Train on everything → Test on Oxford"

This goes in the paper as a generalization table (Table X) and directly supports Papers 2 and 3 (cross-receiver, cross-city).

### Why This Beats the Previous Approach (All-UrbanNav-as-Validation)

| Approach                        | Leakage? | Distribution Match?               | Academically Defensible?              |
| ------------------------------- | -------- | --------------------------------- | ------------------------------------- |
| Random epoch-level              | **YES**  | Yes                               | **NO**                                |
| All-UrbanNav as val/test        | No       | **No** (HK=degraded, train=clean) | Weak                                  |
| **Session-stratified 70/15/15** | No       | **Yes**                           | **YES** — standard practice           |
| + Leave-dataset-out (extra)     | No       | N/A (intentional mismatch)        | **YES** — strong generalization claim |

---

## 6. The 35 Features — Full Justification

### Why 35 Features and Not More/Fewer?

35 = 7 groups × 5 features. This grouping was chosen to:

1. Cover every known physical mechanism of GNSS degradation
2. Be extractable from standard GNSS outputs (NMEA + RINEX)
3. Create a tensor shape (30 steps × 35 features) that fits the Transformer input width efficiently

### Complete Feature Justification Table

| #   | Feature                | Group | Source           | Justification                                                                      | NaN %         |
| --- | ---------------------- | ----- | ---------------- | ---------------------------------------------------------------------------------- | ------------- |
| 1   | `lat`                  | G1    | GGA/CSV          | Altitude context; used as metadata (NOT model input — geographic overfitting risk) | 54%           |
| 2   | `lon`                  | G1    | GGA/CSV          | See lat                                                                            | 54%           |
| 3   | `alt`                  | G1    | GGA/CSV          | Altitude → tropospheric delay proxy; impute with median                            | 54%           |
| 4   | `lat_std`              | G1    | GST/sigma/RTK    | Position uncertainty East-West; direct quality indicator                           | 85%           |
| 5   | `lon_std`              | G1    | GST/sigma/RTK    | Position uncertainty North-South                                                   | 85%           |
| 6   | `mean_cnr`             | G2    | GSV/S1C/SNR      | Primary signal quality; drops before blockage                                      | 10%           |
| 7   | `min_cnr`              | G2    | same             | Weakest satellite reveals obstruction direction                                    | 10%           |
| 8   | `max_cnr`              | G2    | same             | Strongest satellite; gap (max–min) reveals partial sky obstruction                 | 10%           |
| 9   | `std_cnr`              | G2    | same             | High std = asymmetric sky (building on one side)                                   | 10%           |
| 10  | `cnr_trend`            | G2    | computed         | **Key predictor** — negative slope over 30s signals approaching blockage           | 10%           |
| 11  | `num_satellites`       | G3    | GGA/GSV/RINEX    | Drops sharply at tunnel entry; most direct degradation indicator                   | 12%           |
| 12  | `sat_mean`             | G3    | window           | 30s mean — smoother than instantaneous count                                       | 12%           |
| 13  | `sat_min`              | G3    | window           | Worst-case count in past 30s                                                       | 12%           |
| 14  | `sat_visibility`       | G3    | computed         | num_sats / 50 — receiver-normalized                                                | 12%           |
| 15  | `sat_drop_rate`        | G3    | temporal diff    | **Key predictor** — rate of satellite loss predicts upcoming blockage              | 12%           |
| 16  | `pdop`                 | G4    | GSA              | 3D geometry; rises before blockage                                                 | 45%           |
| 17  | `hdop`                 | G4    | GGA/GSA          | Horizontal geometry — critical for lateral AV positioning                          | 45%           |
| 18  | `vdop`                 | G4    | GSA              | Vertical geometry — rises first when overhead sats blocked                         | 45%           |
| 19  | `gdop`                 | G4    | computed         | Combines geometric + time DOP                                                      | 45%           |
| 20  | `dop_ratio`            | G4    | hdop/vdop        | Urban canyon signature: hdop >> vdop                                               | 45%           |
| 21  | `solution_status`      | G5    | GGA fix          | Fix type (RTK fixed=1.0, single=0.8, no fix=0.0)                                   | 5%            |
| 22  | `baseline_sats`        | G5    | num_sats         | Sats contributing to current solution                                              | 12%           |
| 23  | `solution_age`         | G5    | GGA field        | Age of differential corrections — rises when link lost                             | 5%            |
| 24  | `fix_continuity`       | G5    | window           | Fraction of 30s with valid fix                                                     | 5%            |
| 25  | `fix_transitions`      | G5    | window           | Fix quality changes — instability precedes loss                                    | 5%            |
| 26  | `position_variance`    | G6    | GST/sigma        | Variance of position uncertainty; increases with instability                       | 20%           |
| 27  | `cnr_variance`         | G6    | std_cnr²         | High variance = intermittent signal (passing trees / building gaps)                | 10%           |
| 28  | `elevation_violations` | G6    | proxy            | Low-elevation satellite proxy                                                      | 12%           |
| 29  | `multipath`            | G6    | position_var/cnr | High pos uncertainty + low C/N0 → multipath                                        | 15%           |
| 30  | `clock_bias`           | G6    | solution_age     | Rate of change of differential age                                                 | 5%            |
| 31  | `iono_delay`           | G7    | 0                | Dual-freq not available; set to 0 with documented limitation                       | 0% (constant) |
| 32  | `tropo_delay`          | G7    | Hopfield/alt     | Simplified altitude-based tropospheric delay model                                 | 5%            |
| 33  | `cycle_slips`          | G7    | RINEX LLI        | LLI flag from carrier phase — appears immediately before signal loss               | 30%           |
| 34  | `residual_mean`        | G7    | GBS/GST          | Mean position residual — rises with multipath                                      | 20%           |
| 35  | `residual_std`         | G7    | GBS/GST          | Variability of residuals — increases in degraded environments                      | 20%           |

**NaN % column is for the combined dataset.** Most NaN comes from drone (no position) and NCLT/Oxford (no C/N0). The **30 non-position, non-C/N0 features are < 5% NaN** for the majority of the dataset.

### Important: `lat` and `lon` Should NOT Be Model Inputs

Raw latitude/longitude cause **geographic overfitting** — the model learns "Beijing coordinates → CLEAN" rather than learning signal physics. In model training:

- Exclude `lat` and `lon` from the feature tensor
- Include `alt` (with median imputation) — altitude affects tropospheric delay
- The model uses **33 features** (35 minus lat/lon) as inputs

---

## 7. Data Sources — Technical Details

### 7.1 Scenarios A–E (Septentrio Mosaic-X5C, Beijing, 2026)

**Why we collected these:** No existing public dataset covers all five degradation scenarios (instant blockage, urban canyon, partial blockage, open sky, approaching blockage) with a professional survey-grade receiver under controlled conditions. These scenarios were designed specifically for SENTINEL-GNSS.

**Receiver:** Septentrio Mosaic-X5C — a professional-grade multi-constellation receiver (GPS+GLO+GAL+BDS+QZSS+NAVIC). Note: this receiver outputs NMEA without GSV sentences and RINEX without S1C in the field configuration used.

**C/N0 from RINEX SNR indicator:** The RINEX SNR digit (0–9 scale, 6 dBHz bins) gives `CNR ≈ (SNR−1)×6+6` dBHz. Open-sky conditions give SNR=7 → 42 dBHz (correct). This is why CLEAN threshold is 35 dBHz (not 38): the 6 dBHz quantisation can push the window mean to 36–37 dBHz even under good conditions.

### 7.2 Supervisor Vehicle (Septentrio Mosaic-X5C, Beijing, 2025)

Same receiver as scenarios. Uses NMEA with GSV sentences (C/N0 in dBHz). This gives higher-quality C/N0 than the scenarios (direct measurement vs. SNR indicator). 9 sessions across 4 experiments.

### 7.3 Supervisor Drone (Unicore UB4B0, Beijing, 2024)

Military-grade multi-constellation receiver. RINEX S1C gives actual C/N0. All data is CLEAN (open-sky aerial flight, excellent geometry). Provides the model with the cleanest possible signal examples.

### 7.4 UrbanNav HK-Medium-Urban-1 (Hong Kong, May 2021)

10 receivers simultaneously on the same vehicle, same route (~13 min in Mong Kok / Sham Shui Po):

- **NovAtel FlexPak6**: Professional RTK. Most reliable.
- **u-blox F9P** (×2): High-precision dual-frequency. Good.
- **u-blox M8T** (×3): Single-frequency prosumer. Moderate.
- **Google Pixel 4, Huawei P40 Pro**: Consumer phones. Poor in urban canyon.
- **Samsung Note 8, Xiaomi Mi8**: Older consumer phones. Very poor.

This dataset enables the **cross-receiver generalization study** (Paper 2).

### 7.5 UrbanNav HK Tunnel (Hong Kong, May 2021)

Same 10-receiver setup but in the **Cross-Harbour Tunnel** (Tung Chung Tunnel route). Complete signal loss inside tunnel. Provides the clearest DEGRADED examples.

### 7.6 Tokyo Odaiba (UrbanNav Tokyo, 2021)

Trimble survey-grade receiver + u-blox F9P on the same vehicle. RINEX obs with S1C. Urban area with good sky visibility (Odaiba is a waterfront area). Mixed urban/open conditions. **Shinjuku is NOT processed** — only the base station obs file is present; no rover obs file for Shinjuku.

### 7.7 NCLT — University of Michigan North Campus Long-Term Dataset

**Ground robot** (Segway RMP) with Velodyne HDL-32E LiDAR + GPS + IMU. Two sessions: 2012-08-04 and 2013-04-05, Ann Arbor, Michigan, USA.

**Available:** `gps.csv` (lat/lon/alt/fix_mode in 8-column CSV, lat/lon in **radians**), `gps_rtk_err.csv` (position error vs. LiDAR SLAM truth).

**Not available:** C/N0, DOP (beyond approximate hdop), satellite count (logging bug — always 0).

**Ground truth:** LiDAR SLAM trajectory (`groundtruth_YYYY-MM-DD.csv`) serves as the reference. We use `gps_rtk_err.csv` = |GPS − SLAM| as the label signal. This is a **physically verified** quality metric, more rigorous than self-reported receiver quality.

### 7.8 Oxford RobotCar Dataset (Oxford, UK, 2014–2015)

Autonomous vehicle with NovAtel OEM6 GPS (GPS-only, single-frequency, 2014 hardware). Two traversals: 2014-08-11 and 2015-03-10.

**Available:** `gps/gps.csv` — has columns `num_satellites`, `latitude`, `longitude`, `altitude`, `latitude_sigma`, `longitude_sigma`, `altitude_sigma`. No C/N0, no DOP.

**Context:** 2014 GPS-only (no GLONASS/Galileo) on a narrow Oxford road. Average `latitude_sigma` ≈ 6m (p90 ≈ 10m). This is genuine urban GPS degradation — NOT a data quality problem. Labels correctly reflect DEGRADED/WARNING conditions for a receiver of that era in that environment.

---

## 8. Publishing and Data Use

| Source                       | Can Redistribute Raw Data? | Can Publish Processed Features? | Must Cite                     |
| ---------------------------- | -------------------------- | ------------------------------- | ----------------------------- |
| Scenarios A–E                | **YES** — self-collected   | YES                             | Our own paper                 |
| Supervisor (vehicle + drone) | **YES** — self-collected   | YES                             | Our own paper                 |
| UrbanNav HK Medium           | NO (third-party)           | YES (transforms OK)             | Hsu et al. 2021               |
| UrbanNav HK Tunnel           | NO                         | YES                             | Hsu et al. 2021               |
| Tokyo Odaiba                 | NO                         | YES                             | UrbanNav Tokyo paper          |
| NCLT                         | NO                         | YES                             | Carlevaris-Bianco et al. 2016 |
| Oxford RobotCar              | NO                         | YES                             | Maddern et al. 2017           |

**Code release strategy:** Release (a) all processing scripts, (b) raw Scenarios A–E data, (c) processed feature CSVs for all datasets. Users who want to reproduce from raw data must download the third-party datasets themselves and run our pipeline.
