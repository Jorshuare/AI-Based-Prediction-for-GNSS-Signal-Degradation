# Paper B — The Benchmark / Dataset Descriptor (Full Section Plan)

> **Paper B** in the 2-paper + conference plan. A dataset descriptor is a *different
> contribution type* from the method paper (Paper A), so it is legitimately separate — not
> salami-slicing.

**Working title:**
**"SENTINEL-GNSS: A Multi-City, Multi-Receiver Benchmark for Proactive GNSS
Signal-Degradation Prediction"**

**Target venue:** *Scientific Data* (Nature portfolio, open access) — dataset descriptors.
Alternative: *Data in Brief* (Elsevier), or IEEE ITSC dataset track.
> Review criterion is *reusability and rigour of the data*, not model novelty — so this paper
> stands on the benchmark's completeness and the reproducible pipeline.

---

## Abstract (draft — uses confirmed dataset figures)

> We release SENTINEL-GNSS, a labelled benchmark for *predicting* GNSS signal-quality
> degradation. It unifies field collections and public datasets across four cities (Beijing,
> Hong Kong, Tokyo, plus excluded-but-documented legacy sources) and 9+ receiver types —
> from survey-grade Septentrio/NovAtel to consumer smartphones — under a single 3-class
> quality schema (CLEAN / WARNING / DEGRADED) with three prediction horizons (5/15/30 s).
> The release comprises 149,662 labelled epochs, a documented 37-feature representation
> derived from RINEX and NMEA, the complete raw→feature→label pipeline, train/val/test
> splits with leakage controls, and baseline results for trivial, rule-based, classical-ML,
> and deep-learning models. ⚠️ Verify final per-source epoch counts against committed CSVs.

---

## 1. Background & Motivation
- Why a *prediction* benchmark (not just classification): the field lacks a shared,
  multi-city, multi-receiver dataset with future-horizon labels.
- Reuse value: any future GNSS-quality method can train/evaluate and compare to our baselines.

## 2. Data Sources (the benchmark composition)
| Source | City / Country | Receiver(s) | Role | Notes |
|--------|----------------|-------------|------|-------|
| Field Scenarios A–E | Beijing, CN | Septentrio Mosaic-X5C | train/test | A=instant blockage (13 runs), B=urban canyon, C=partial, D=open-sky, E=approaching |
| Supervisor vehicle exp1–4 | Beijing, CN | Septentrio | train | route diversity |
| Supervisor drone | Beijing, CN | Unicore UB4B0 | excluded | open-sky only, 100% CLEAN |
| UrbanNav HK-Medium | Hong Kong | 9+ receivers | val/test | moderate canyon |
| UrbanNav HK-Tunnel | Hong Kong | 9+ receivers | train | complete signal loss |
| UrbanNav HK-Deep (Whampoa) | Hong Kong | 10 receivers | train | dense canyon |
| UrbanNav HK-Harsh (Mong Kok) | Hong Kong | 10 receivers | train | extreme canyon |
| Tokyo Shinjuku | Tokyo, JP | Trimble + u-blox | held-out city | cross-city eval (Paper 3) |
| Tokyo Odaiba | Tokyo, JP | Trimble + u-blox | val/test | waterfront mixed |
| NCLT | Michigan, US | 2012 GPS module | excluded | sat-count logging bug |
| Oxford RobotCar | Oxford, UK | 2014 NovAtel | excluded | position-sigma labels only |

> ⚠️ Regenerate exact per-source epoch counts from the final committed CSVs for the paper's
> composition table. Current total labelled: **149,662 rows × 41 columns**.

## 3. Feature Representation (37 features)
- Reproduce the 7-group feature table (see Paper 1 §3.2).
- Document each feature's source sentence/field and computation.
- Document NaN-handling per feature group (session-median imputation, proxies, flags).

## 4. Labelling Schema
- 3 classes with literature-grounded thresholds (IS-GPS-200, RTCM SC-104).
- 5 scenario types (A–E) mapped onto the quality classes.
- No-fix epochs retained as DEGRADED.
- Multi-horizon label construction (t+5/15/30 s).

## 5. Data Records (what the release contains)
- `data/labelled/sentinel_gnss_labelled.csv` (149,662 × 41).
- Per-source processed feature CSVs.
- Windowed `.npz` tensors (SMOTE and no-SMOTE) + fitted scaler.
- Train/val/test split definitions with session-level reassignment map.

## 6. Technical Validation (baseline results)
- Report the full Run-14 comparison table (RESULTS_REFERENCE §7) as the official baselines:
  MajorityClass, CNR rule, RF/XGBoost (±SMOTE), LSTM-only, Transformer-only, full model.
- Multi-horizon, per-class, bootstrap CIs.
- Cross-city transfer (E6) as a benchmark-level generalisation reference.

## 7. Reproducible Pipeline
- `process_all_datasets.py` (raw RINEX/NMEA → features), `feature_prep.py` (windows + split
  + scaler + SMOTE), `train.py`, `evaluate.py`, `baselines.py`.
- Kaggle notebook reproduces every number end-to-end on a free T4.
- Exact dependency versions; fixed seeds.

## 8. Usage Notes & Known Limitations
- Excluded sources and *why* (drones, NCLT, Oxford) — so users are not misled.
- Within-site overlap for scenario_a (r4–r11 train, r13 test) documented.
- Tokyo class imbalance.
- Receiver-tier conventions (GR vs GRJ across sub-datasets).

## 9. Code & Data Availability
- GitHub repo, license, DOI (mint via Zenodo on release).

---

## Status & Dependencies
- **Mostly documentation** of work already done; depends on finalised CSVs and Paper-1
  baselines (have).
- **Before submission:** regenerate per-source epoch counts; mint Zenodo DOI; write the
  data descriptor in the target journal's structured format.
- **Highest long-term citation potential** (benchmark papers accrue citations from every
  follow-on method).
