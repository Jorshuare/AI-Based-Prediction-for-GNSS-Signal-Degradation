# SENTINEL-GNSS — Publication Roadmap

> **Authoritative plans live in `papers/`.** This file is the short, accurate index.
> Detailed section-by-section plans: `papers/PAPER_A_Flagship.md`,
> `papers/PAPER_B_Comparison_EKF.md`, `papers/PAPER_CONFERENCE_CrossCity.md`. Confirmed
> numbers: `papers/RESULTS_REFERENCE.md`. Team orientation: `papers/TEAM_BRIEF.md`.

**Project core (never lose sight of this):**

> A Transformer–LSTM that predicts GNSS signal degradation **5, 15 and 30 seconds before it
> happens**, so an autonomous vehicle can proactively switch to backup localisation *before*
> signal loss — not after.

---

## The plan: 2 journal papers + 1 conference paper

Consolidated from an earlier 4-paper idea (four papers from one model/dataset risks
salami-slicing). The three outputs target three distinct communities and do not overlap.

| Output | Type | Scope | Venue | Status |
|--------|------|-------|-------|--------|
| **Paper A** | Method (flagship) | Proactive multi-horizon Transformer–LSTM; ablations; interpretability; cross-receiver + cross-city robustness | *GPS Solutions* (Q1) | core ✅, receiver ⏳ |
| **Paper B** | Systems / application | Fair **model-family comparison** → select deployable model → **prediction-informed adaptive EKF** → navigation RMSE | *IEEE T-ITS* / *J. Navigation* | EKF ✅ (sim), comparison ✅, real-data RMSE ⏳ |
| **Conference** | Short paper | **Cross-city generalisation** (Beihang/Beijing + HK → unseen Tokyo); the headline transfer result | **ION GNSS+ 2026** | core ✅ (E6) |

> The cross-city result appears in both the conference paper and (extended) in Paper A §5.5 —
> a standard, accepted conference→journal extension.
> **The earlier benchmark/dataset paper was dropped**; the dataset still ships with Paper A
> (GitHub/Zenodo) for reproducibility, just not as its own paper.

---

## Why each paper stands on its own

- **Paper A** is the learning contribution: the *first* proactive multi-horizon GNSS
  degradation predictor (to our knowledge — ⚠️ verify the literature claim before submission).
  Its robustness sections (cross-receiver, cross-city) are analyses of the *same* model, which
  is exactly how strong applied-GNSS papers are structured.
- **Paper B** is the systems contribution: it proves prediction *matters* by closing the loop
  (predict → adapt the filter → measurably better position). It uses the model comparison as
  the *selection rationale* for the EKF, so the comparison is not a thin standalone paper.
- **Conference** gives the team a presentation and early feedback on the strongest, most
  defensible single result (cross-city transfer).

---

## Headline confirmed results (Run 14 — see `papers/RESULTS_REFERENCE.md`)

- +5 s Macro-F1 = **0.821** [95% CI 0.800–0.843], MCC 0.773; +30 s Macro-F1 = 0.783.
- DEGRADED recall 0.85 at +5 s; DEGRADED F1 0.274 → **0.718** across runs (2.6×).
- **Cross-city (unseen Tokyo): DL retains DEGRADED F1 0.75 while RandomForest collapses to
  0.15** — the deciding result for deployment.
- Inference 0.039 ms/sample, **10.5× faster** than three per-horizon tree models.
- Adaptive EKF (controlled simulation): **−33.8%** position RMSE during blockage vs raw GNSS.

---

## Honest framing rules (apply to every paper)

1. Lead with **generalisation + efficiency**, not in-domain leaderboard score (trees beat the
   network in-domain; disclose it openly).
2. Do **not** claim the win comes from "temporal memory" — E1/E2 show temporal order
   contributes ~3%; the value is representation transfer.
3. Only claim "well-calibrated" after the corrected ECE (E7 re-run in the notebooks).
4. Frame the adaptive EKF real-data RMSE as ongoing until the aligned reference trajectory is
   processed; the simulation result is reported as a simulation.
5. Soften any "first / only / zero prior work" to "to our knowledge after a systematic search."
6. Data site = **Beihang University campus, Beijing, China** (Beihang is the university; the
   city for cross-city claims is Beijing).

---

## Phase 2/3 (open, not yet run)
- DL multi-head **+60 s** horizon (needs retrain; `feature_prep --extra_horizons 60` ready).
- **Raw per-satellite C/N₀** streams (new extractor + retrain).
- Real-data EKF RMSE with an aligned reference/RTK trajectory.
- Per-receiver evaluation table (inference only) for Paper A's cross-receiver section.
