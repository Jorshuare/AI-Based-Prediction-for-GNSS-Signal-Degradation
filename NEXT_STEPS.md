# SENTINEL-GNSS · Next Steps & Complete Project Roadmap

> **Written: May 5, 2026 — after field collection day**
>
> This document is your single source of truth for what needs to happen next, why each step matters, what you will get from it, and how to execute it. Read top-to-bottom. Each step builds on the previous one.

---

## Project Objective Recap

Build a machine-learning classifier that, given raw GNSS signal metrics, can automatically identify **which of 5 degradation scenarios** the receiver is experiencing:

| Label | Scenario             | Real-world cause                       |
| ----- | -------------------- | -------------------------------------- |
| A     | Instant blockage     | Tunnel, underpass, entering a building |
| B     | Urban canyon         | Dense tall buildings, severe multipath |
| C     | Partial blockage     | Trees, one-sided obstruction           |
| D     | Open sky             | Clear nominal conditions (baseline)    |
| E     | Approaching blockage | Gradual sky obstruction as you move    |

**Why this matters:** Autonomous vehicles and drones need to know _in real time_ whether GNSS is degraded and _why_ — so they can switch to dead reckoning, warn the operator, or request a different route.

---

## Where We Are Now (May 5, 2026)

### ✅ What is done

| Item                                                                    | Status |
| ----------------------------------------------------------------------- | ------ |
| Septentrio MOSAIC-X5C field data collected — all 5 scenarios            | ✅     |
| RINEX 3 files on disk (`data/raw/scenarios/`)                           | ✅     |
| Signal quality analysis charts generated (`results/scenario_analysis/`) | ✅     |
| NCLT dataset downloaded (2 dates)                                       | ✅     |
| Oxford RobotCar dataset downloaded (4 traversals)                       | ✅     |
| Supervisor vehicle + drone RINEX files on disk                          | ✅     |
| UrbanNav HK + Tokyo on disk                                             | ✅     |
| RTKLIB installed at `C:\Program Files\RTKLIB\bin\`                      | ✅     |
| All processing scripts written                                          | ✅     |
| Python venv with all packages ready                                     | ✅     |

### ⚠️ What is NOT yet done (the work that remains)

1. Run RTKLIB on our field data → get `.pos` files
2. Run RTKLIB on supervisor vehicle + drone data → get `.pos` files
3. Run RTKLIB on UrbanNav data → get `.pos` files
4. Standardise NCLT and Oxford CSVs → unified format
5. Extract 35 features from every `.pos` file
6. Label every feature CSV with the correct scenario class
7. Assemble the train/val/test splits
8. Train and evaluate the ML model

---

## Step-by-Step Plan

---

### STEP 1 — Run RTKLIB on Our Field Data

**Why:** Our RINEX `.26O` files contain raw pseudorange and carrier-phase measurements — they are NOT positions yet. RTKLIB computes the position solution from these measurements.

**What you get:** A `.pos` file for each run, containing lat/lon/height + quality code (Q) + satellite count (ns) + uncertainty (sdn/sde/sdu) per second.

**Expected result:** For Scenario D (open sky), you should get mostly Q=1 (Fixed RTK) or Q=2 (Float). For Scenario A (blockage), you'll see sudden jumps to Q=5, ns dropping to 0–2, sdn/sde/sdu exploding to 10–50 m.

**How to run:**

```powershell
cd "c:\Users\Joel\Desktop\Beihang University\Team-Pilot-Project"
& ".venv\Scripts\python.exe" src/processing/our_collection_processor.py --all
```

This processes every run under `data/raw/scenarios/`, for all 5 scenarios, and writes `.pos` files to `data/processed/our_collection/`.

**To verify it worked:**

```powershell
Get-ChildItem data/processed/our_collection/ -Filter "*.pos"
# Should see: scenario_A_Run_1_solution.pos, scenario_A_A2_solution.pos, etc.
```

**If it fails (no base station warning):** That is expected — we don't have a base station file for our data, so it will run in Single mode (Q=5). The `.pos` file will still be created and is still useful for extracting features. The position accuracy will be ~3–5 m rather than ~3 cm, but the Q-code transitions and satellite count behaviour are what the model needs.

> **Key insight:** Even Q=5 solutions show the _pattern_ of signal degradation — ns drops, ratio collapses, sdn spikes. These patterns are what the model learns, not the absolute position.

---

### STEP 2 — Run RTKLIB on Supervisor Vehicle Data

**Why:** Same reason as Step 1. The supervisor vehicle data has RINEX files that need post-processing.

**What you get:** `.pos` files for each experiment run, under `data/processed/supervisor/vehicle/`.

**Expected result:** Vehicle data has multiple experiments (exp1–exp4) with different environments. exp3 and exp4 likely have pre-processed `.pos` files already in their `rtkre/` folders — check those first.

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/rtklib/rtklib_pipeline.py --dataset vehicle
```

**Check first — are there existing .pos files?**

```powershell
Get-ChildItem data/raw/supervisor/vehicle -Recurse -Filter "*.pos"
```

If `.pos` files already exist in `rtkre/` subfolders, the pipeline will pick them up directly and skip re-processing.

---

### STEP 3 — Run RTKLIB on Supervisor Drone Data

**Why:** The drone dataset has a base station file (`base2410.24o`) which enables PPK (Post-Processed Kinematic) — this means we can get Q=1 Fixed solutions instead of Q=5 Single. This gives the best quality reference.

**What you get:** High-accuracy drone `.pos` files using base+rover PPK.

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/rtklib/rtklib_pipeline.py --dataset drone
```

**Manual command (if script fails):**

```powershell
& "C:\Program Files\RTKLIB\bin\rnx2rtkp.exe" -p 2 `
  -o data/processed/supervisor/drone/drone1_solution.pos `
  data/raw/supervisor/drone/base2410.24o `
  data/raw/supervisor/drone/drone1_241h.24o
```

Wait — in RTKLIB the navigation file must come first. The exact argument order for `rnx2rtkp` is:

```
rnx2rtkp [options] -o outfile navfile... rovfile [basefile]
```

---

### STEP 4 — Standardise NCLT Data

**Why:** NCLT provides pre-computed RTK positions, but in ECEF (Earth-Centred Earth-Fixed) coordinates (x, y, z in metres), not lat/lon. We need to convert to WGS-84 geodetic and align the timestamps to a common format.

**What you get:** `data/processed/nclt/nclt_2012-08-04.csv` and `nclt_2013-04-05.csv` — each with columns: `timestamp_utc, lat, lon, height, mode, num_sats, speed, error_m`.

**Why NCLT is valuable:** The `gps_rtk_err.csv` gives us the ground truth error per epoch — we know exactly how degraded the GPS was at every moment. This is rare and powerful for labelling.

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/processing/nclt_processor.py
```

**Verify:**

```powershell
Get-ChildItem data/processed/nclt/
# Should see nclt_2012-08-04.csv (and maybe nclt_combined.csv)
```

---

### STEP 5 — Standardise Oxford Data

**Why:** Oxford provides INS-fused NovAtel positions (very accurate). The `ins.csv` gives position + velocity, the `gps.csv` gives satellite count and sigma — both are needed for feature extraction.

**What you get:** `data/processed/oxford/oxford_{date}.csv` — columns: `timestamp_utc, lat, lon, height, num_sats, lat_sigma, lon_sigma, vel_n, vel_e, vel_d, ins_status`.

**Why Oxford is valuable:** Multiple repeat traversals of the same route under different seasonal conditions. This tests whether the model generalises across weather and environment changes.

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/processing/oxford_processor.py
```

---

### STEP 6 — Process UrbanNav Data

**Why:** UrbanNav is a Hong Kong + Tokyo dataset with challenging urban GNSS scenarios. It directly matches our Scenarios B (urban canyon) and A (tunnel). Using it expands the model's training set with non-Beijing data.

**What you get:** `.pos` files from RTKLIB for each UrbanNav recording.

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/extraction/urbannav_extractor.py
```

**Note:** First check if HK-Tunnel-1 is still zipped:

```powershell
Get-ChildItem data/raw/public/urbannav/HK-Tunnel-1/ | Select-Object -First 5
# If you see a .zip file, extract it first
```

---

### STEP 7 — Extract Features from All `.pos` Files

**Why:** Raw `.pos` files have lat/lon/Q/ns per second. The ML model doesn't learn from raw positions — it learns from derived features: how rapidly the quality changes, how many satellites drop in a window, how the standard deviations evolve over a sliding window.

**What features are extracted (35 total):**

| Category          | Features (5 per category)                                         |
| ----------------- | ----------------------------------------------------------------- |
| Position spread   | sdn, sde, sdu, sqrt(sdn²+sde²), sqrt(sdn²+sde²+sdu²)              |
| Quality codes     | Q value, Q variance (window), Q transitions/min, ratio test, age  |
| Satellite count   | ns mean, ns min, ns std, ns drop events, ns recovery speed        |
| Velocity          | speed, acceleration, heading change rate, jerk, path smoothness   |
| Residuals         | code-carrier divergence, pseudorange residual mean/std            |
| Temporal          | epoch gap count, clock jumps, cycle slips per min, lock time      |
| Environment proxy | elevation-weighted SNR, sky visibility score, multipath indicator |

**How to run:**

```powershell
# Batch mode — processes all .pos files under data/processed/
& ".venv\Scripts\python.exe" src/features/feature_extractor.py --batch data/processed/
```

Or per-file:

```powershell
& ".venv\Scripts\python.exe" src/features/feature_extractor.py \
  --input data/processed/our_collection/scenario_A_Run_1_solution.pos \
  --output data/processed/our_collection/scenario_A_Run_1_features.csv \
  --source our_collection_A
```

**Expected result:** For each `.pos` file you get a `.features.csv` with one row per epoch (1 Hz) and 35 feature columns plus source, timestamp, lat, lon.

---

### STEP 8 — Label All Feature CSVs

**Why:** The ML model is supervised — it needs to know the correct class (A/B/C/D/E) for each row. For our own collection, we know the label from the scenario we recorded. For NCLT, the label comes from the `gps_rtk_err.csv` error magnitude. For Oxford, from the INS status.

**Labelling strategy per dataset:**

| Dataset                        | How label is assigned                                                            |
| ------------------------------ | -------------------------------------------------------------------------------- |
| Our collection (scenarios A–E) | Directly from folder name (scenario_A → label A)                                 |
| Supervisor vehicle             | Manually or by matching route segment to known scenario type                     |
| Supervisor drone               | From flight phase / base distance / altitude profile                             |
| NCLT                           | From `gps_rtk_err.csv`: error < 0.1 m → D, 0.1–0.5 m → C, 0.5–2 m → B, > 2 m → A |
| Oxford                         | From `num_satellites` + `sigma` in gps.csv: satellites < 5 or sigma > 5 m → B/C  |
| UrbanNav                       | From dataset metadata (HK-Tunnel-1 → A, HK-Medium-Urban → B, Tokyo Odaiba → C/D) |

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/labeling/labeler.py --batch data/processed/
```

**Output:** `data/labelled/` — one file per source dataset, each with `label` column added.

---

### STEP 9 — Assemble the Final ML Dataset

**Why:** We need to combine all labelled CSVs from all datasets into one master dataset, then split into train/validation/test sets. The split must be **time-based**, not random — mixing time points from the same session across train and test would leak information.

**What you get:** Three files: `data/labelled/train.csv`, `val.csv`, `test.csv`.

**Time-based split logic:**

- For each source session, take: first 70% of epochs → train, next 15% → val, last 15% → test
- Never shuffle: the temporal structure is preserved

**How to run:**

```powershell
& ".venv\Scripts\python.exe" src/features/dataset_assembler.py --split temporal
```

**Verify class balance:**

```powershell
& ".venv\Scripts\python.exe" -c "
import pandas as pd
train = pd.read_csv('data/labelled/train.csv')
print('Train class distribution:')
print(train['label'].value_counts())
print(f'Total rows: {len(train)}')
"
```

You want roughly 1000+ examples per class (5000+ total) for a reliable model. If any class is under-represented, consider collecting more data for that scenario.

---

### STEP 10 — Train the ML Classifier

**Why:** This is the core deliverable — a model that, given GNSS features, predicts the environment scenario class.

**Recommended model progression:**

1. **Baseline: Random Forest** — easy to interpret, fast to train, handles 35 features well
2. **Gradient Boosting (XGBoost/LightGBM)** — often best for tabular GNSS data
3. **LSTM** — if you want to exploit the temporal sequence (sliding window of 10–30 epochs)
4. **1D CNN** — alternative temporal model, less memory than LSTM

**Start with Random Forest:**

```python
# Install if needed: pip install scikit-learn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import pandas as pd

train = pd.read_csv('data/labelled/train.csv')
val   = pd.read_csv('data/labelled/val.csv')
test  = pd.read_csv('data/labelled/test.csv')

FEATURE_COLS = [c for c in train.columns if c not in
                ('label','timestamp','source','lat','lon')]

X_train, y_train = train[FEATURE_COLS], train['label']
X_val,   y_val   = val[FEATURE_COLS],   val['label']
X_test,  y_test  = test[FEATURE_COLS],  test['label']

rf = RandomForestClassifier(n_estimators=200, max_depth=15,
                             class_weight='balanced', random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

print("Validation results:")
print(classification_report(y_val, rf.predict(X_val)))
print("Test results:")
print(classification_report(y_test, rf.predict(X_test)))
```

**Expected accuracy targets (realistic for this problem):**

- Scenario D (open sky) vs A (total blockage): should be ~99% separable — these are extreme opposites
- Scenario B vs C vs E: harder, these overlap in some features
- Overall macro-F1 > 0.80 is achievable with good labelling

**Saving the model:**

```python
import joblib
joblib.dump(rf, 'models/random_forest_v1.pkl')
```

---

### STEP 11 — Evaluate and Iterate

**Evaluation metrics to use:**

- **Confusion matrix** — see which scenarios get confused with each other
- **Per-class F1 score** — check if any class is consistently missed
- **Feature importance** — which of the 35 features drive the predictions?
- **Temporal accuracy** — does the model correctly identify transitions between scenarios?

**If accuracy is poor:**

- Check label quality first — are the labels actually correct?
- Check class balance — is one class dominating?
- Try extending the feature window (10 s, 30 s, 60 s sliding windows)
- Add more training data for weak classes (collect more runs)

---

## Data Sufficiency Check

| Dataset                                 | Estimated labelled epochs | Scenarios covered           | Notes                                   |
| --------------------------------------- | ------------------------- | --------------------------- | --------------------------------------- |
| Our collection A runs (Run_1 + A2 + A3) | ~180                      | A                           | Short runs; consider collecting more    |
| Our collection B runs (Run_1 + B2)      | ~1600                     | B                           | Good                                    |
| Our collection C runs (Run_1 + C2)      | ~2700                     | C                           | Good                                    |
| Our collection D (Run_1)                | ~600                      | D                           | Adequate                                |
| Our collection E (E2 + E3)              | ~1000                     | E                           | Adequate                                |
| Supervisor vehicle (exp1–exp4)          | ~5000+                    | B, C, D, E likely           | Need to verify scenario types           |
| Supervisor drone                        | ~2000+                    | D, E (airborne)             | Note: drone sky view ≠ vehicle          |
| NCLT (2 dates × ~2 hr each)             | ~14400                    | B (campus), D (open)        | Error label from gps_rtk_err.csv        |
| Oxford (4 traversals × ~45 min)         | ~10800                    | B, C, D                     | Oxford city route covers multiple types |
| UrbanNav HK + Tokyo                     | ~5000+                    | A (tunnel), B (urban), C, D | Well-characterised scenarios            |

**Total estimated:** ~40,000–50,000 labelled epochs — sufficient for a robust model.

---

## Script Inventory — What Each Script Does

| Script                                       | Purpose                                    | Run command                    | Output                                           |
| -------------------------------------------- | ------------------------------------------ | ------------------------------ | ------------------------------------------------ |
| `src/processing/our_collection_processor.py` | RTKLIB on our scenarios A–E                | `--all` or `--scenario A`      | `.pos` files in `data/processed/our_collection/` |
| `src/rtklib/rtklib_pipeline.py`              | RTKLIB on supervisor data                  | `--dataset vehicle` or `drone` | `.pos` files in `data/processed/supervisor/`     |
| `src/processing/nclt_processor.py`           | Standardise NCLT CSVs                      | (no args needed)               | `data/processed/nclt/nclt_*.csv`                 |
| `src/processing/oxford_processor.py`         | Standardise Oxford CSVs                    | (no args needed)               | `data/processed/oxford/oxford_*.csv`             |
| `src/extraction/urbannav_extractor.py`       | UrbanNav RINEX → RTKLIB → features         | (no args needed)               | `.pos` + features in `data/processed/urbannav/`  |
| `src/extraction/nclt_extractor.py`           | Extract features from NCLT processed CSV   | (no args needed)               | Feature CSVs                                     |
| `src/extraction/oxford_extractor.py`         | Extract features from Oxford processed CSV | (no args needed)               | Feature CSVs                                     |
| `src/features/feature_extractor.py`          | Extract 35 features from `.pos` files      | `--batch data/processed/`      | `.features.csv` per `.pos`                       |
| `src/features/dataset_assembler.py`          | Combine + temporal split                   | `--split temporal`             | `train.csv`, `val.csv`, `test.csv`               |
| `src/labeling/labeler.py`                    | Assign scenario labels                     | `--batch data/processed/`      | labelled CSVs in `data/labelled/`                |
| `src/processing/pipeline.py`                 | Master orchestrator                        | `--all`                        | Runs all of the above in order                   |
| `src/utils/analyze_collected_data.py`        | Signal quality charts for our scenarios    | `--all`                        | PNGs in `results/scenario_analysis/`             |

---

## Known Issues to Fix Before Running

| Issue                                                        | File                               | Fix needed                        |
| ------------------------------------------------------------ | ---------------------------------- | --------------------------------- |
| `our_collection_processor.py` path was `our_collection/`     | ✅ Fixed — now `scenarios/`        | Done                              |
| `scenario_e/` folder is empty — E data in `scenario_a_to_e/` | ✅ `find_obs_files()` handles this | Done                              |
| `our_collection_processor.py` uses `.25O` extension glob     | ⚠️ Our files are `.26O`            | Fixed in updated version          |
| UrbanNav `HK-Tunnel-1` extraction                            | ✅ Done                            | —                                 |
| No base station for our collection → Q=5 only                | ℹ️ Expected, not an error          | Acceptable — features still valid |

---

## Immediate Action List (Today / This Week)

1. **Right now:** Run RTKLIB on our own scenarios:

   ```powershell
   cd "c:\Users\Joel\Desktop\Beihang University\Team-Pilot-Project"
   & ".venv\Scripts\python.exe" src/processing/our_collection_processor.py --all
   ```

2. **Check if supervisor vehicle has pre-existing .pos files:**

   ```powershell
   Get-ChildItem data/raw/supervisor -Recurse -Filter "*.pos"
   ```

3. **Run NCLT and Oxford standardisation** (these don't need RTKLIB, fast):

   ```powershell
   & ".venv\Scripts\python.exe" src/processing/nclt_processor.py
   & ".venv\Scripts\python.exe" src/processing/oxford_processor.py
   ```

4. **Feature extraction on whatever .pos files you have** — don't wait for everything:

   ```powershell
   & ".venv\Scripts\python.exe" src/features/feature_extractor.py --batch data/processed/
   ```

5. **Label and assemble a first small dataset** with just our collection + NCLT:

   ```powershell
   & ".venv\Scripts\python.exe" src/labeling/labeler.py --batch data/processed/
   & ".venv\Scripts\python.exe" src/features/dataset_assembler.py --split temporal
   ```

6. **Train a first Random Forest baseline** using the code in Step 10 above — even if the dataset is small (1000 rows) you'll get initial accuracy numbers to iterate on.

---

## FAQ

**Q: Why do we have both NCLT/Oxford AND our own collection? Can't we just use one?**
A: Our own collection is the ground truth for our _specific_ scenarios (A–E at Beihang). NCLT/Oxford give us geographic diversity and more total data. The model trained on mixed data will generalise better than one trained only on our campus data.

**Q: We don't have a base station. Does that ruin our RTKLIB results?**
A: No. Without a base station, RTKLIB runs in Single mode (Q=5, ~3–5 m accuracy). The _pattern_ of Q codes, satellite counts, and uncertainty values is still what the model learns — it doesn't need centimetre accuracy to classify the environment type.

**Q: Should we get more NCLT/Oxford dates?**
A: What we have (2 NCLT dates, 4 Oxford traversals) is sufficient to start. If the model is weak on urban-canyon classification, downloading 1–2 more dates of each could help.

**Q: The `gps_rtk_err.csv` in NCLT — what does it actually measure?**
A: It is the difference (in metres) between each RTK GPS epoch and the high-accuracy wheel+IMU ground truth (from `groundtruth_*.csv`). If the error is 0.03 m, GNSS is excellent (Scenario D). If it is 2.5 m, something is wrong (Scenario A or B). This is the closest thing to a perfect automatic label we have.

**Q: The Oxford INS status says `INS_ALIGNING` for some epochs — use them or skip?**
A: Skip them. `INS_ALIGNING` means the INS hasn't converged yet (typically first 2 minutes of a run). The position uncertainty is too high to be useful. The oxford_processor.py should filter these out automatically.

**Q: What accuracy do we need from the model to call it successful?**
A: For a proof-of-concept: macro-F1 > 0.75 on the test set. For a publishable result: macro-F1 > 0.85, with confusion matrix showing that no scenario is completely misidentified as its opposite (e.g., D misclassified as A should be < 1%).
