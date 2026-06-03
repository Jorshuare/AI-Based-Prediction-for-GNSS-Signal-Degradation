# SENTINEL-GNSS — Papers Folder

This folder holds the publication plan, full section outlines for all four papers, and the
single source of truth for every confirmed result. **Start with `TEAM_BRIEF.md`.**

## Contents

**Publication plan: 2 papers + 1 conference paper** (consolidated from the original 4 to
avoid salami-slicing and maximise impact).

| File | What it is | Read if you are… |
|------|-----------|------------------|
| **TEAM_BRIEF.md** | Project orientation: novelties, validation, status, next steps, reviewer Q&A | …new to the project or sharing with a colleague |
| **RESULTS_REFERENCE.md** | Single source of truth — every confirmed number (Run 14) + E1–E7 | …writing any paper or citing any figure |
| **PAPER_A_Flagship.md** | **Paper A** — flagship method paper (proactive multi-horizon Transformer-LSTM + ablations + cross-receiver + cross-city) | …writing the main method paper |
| **PAPER_B_Comparison_EKF.md** | **Paper B** — systems paper: model-family comparison → select best → **adaptive EKF** → navigation RMSE | …writing the systems/application paper |
| **PAPER_CONFERENCE_CrossCity.md** | **Conference paper** — cross-city short paper for ION GNSS+ 2026 | …writing the conference submission |

> **Final structure (team decision): 2 papers + 1 conference.**
> - **Paper A (method):** how we predict — the novelty, multi-horizon, interpretability,
>   robustness. → *GPS Solutions*.
> - **Paper B (systems):** does it *work* — compare models, pick the deployable one, wire it
>   into an adaptive EKF, show the position-accuracy gain. → *IEEE T-ITS* / *J. Navigation*.
> - **Conference:** the cross-city transfer result, short paper. → ION GNSS+ 2026.
>
> The former **benchmark/dataset paper was dropped**; the dataset is still released alongside
> Paper A (GitHub/Zenodo) for reproducibility, just not as its own paper.

## Ground rules for everyone writing

1. **Cite only from `RESULTS_REFERENCE.md` or `reviewer_experiments.json`.** If a number
   isn't in one of those, it isn't confirmed — mark it ⏳ PENDING, don't invent it.
2. **Status tags** are used throughout: ✅ CONFIRMED, ⏳ PENDING, ⚠️ VERIFY/FIX. Respect them.
3. **The honest narrative is the strong narrative.** In-domain, trees beat us; out-of-domain,
   we win on the safety-critical class. We lead with generalisation, not leaderboard score.
4. **Wording that would fail review** (already fixed here): "receiver-agnostic" (we are
   hardware-aware), "35 features" (it's 37), "SMOTE on training set" for the DL model (the DL
   model uses no-SMOTE + focal loss), and any unqualified "first/only/zero prior work."

## Current run

All numbers reflect **Run 14** (2026-05-31 18:06 UTC). Source artefacts:
- `results/RUN_SUMMARY.json` / `.md` — main metrics
- `results/reviewer_experiments.json` — E1–E7
- `results/figures/*.pdf` + `*.png` — 13 figures
- `results/models/checkpoints/checkpoint_best.pt` — the model (for inference/app)

> Download the whole `results/` folder from the Kaggle notebook (Save Version → Save & Run
> All, then download). That folder is what every paper and the app will be built from.

## Immediate to-dos (see TEAM_BRIEF §8 for the full list)
1. Re-run E7 with temperature T=0.40 (calibration claim).
2. Read lead-time median from `lead_time_histogram`.
3. Add Tokyo per-class support counts to the E6 cross-city result.
