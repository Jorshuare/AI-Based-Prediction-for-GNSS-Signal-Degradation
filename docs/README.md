# SENTINEL-GNSS — Documentation Index

Start here. The project documentation is consolidated into **three rigorous references** plus a few
focused companions. Older, overlapping write-ups were archived to **`/bnks`** (nothing deleted).

## The three core references

| Doc | What it covers |
|---|---|
| **[01_APPLICATION_AND_DASHBOARD.md](01_APPLICATION_AND_DASHBOARD.md)** | The web application: backend + frontend, the scenario/input files (what they are, how we got them, what each contains, with layman examples), every chart explained, and full deployment instructions. |
| **[02_DATA_AND_MODELING.md](02_DATA_AND_MODELING.md)** | The science: data collection, datasets, the 37 features, the Transformer-LSTM, training, ablations, the ensemble, and **all the results we obtained** — each in plain language with justification. |
| **[03_RUNBOOK_AND_ARCHITECTURE.md](03_RUNBOOK_AND_ARCHITECTURE.md)** | Operations: every pipeline step with its exact command and options, the dashboard run, the RTKLIB command, and an appendix of **all the formulas**. |

## Focused companions (kept)

| Doc | What it is |
|---|---|
| [EKF_KALMAN_EXPLAINED.md](EKF_KALMAN_EXPLAINED.md) | A from-scratch, plain-language tutorial on the Kalman filter, our 9-state EKF, and what every metric means. |
| [dataset_references/](dataset_references/) | Upstream READMEs for the public datasets (UrbanNav, Oxford RobotCar, …). |
| [receiver_guide/](receiver_guide/) | Receiver/hardware notes. |

## Papers (drafts, in `/papers`)

| Doc | What it is |
|---|---|
| [../papers/RESULTS_REFERENCE.md](../papers/RESULTS_REFERENCE.md) | The traceable master table of every reported number. |
| [../papers/PAPER_A_Flagship.md](../papers/PAPER_A_Flagship.md) | Flagship paper (prediction model + cross-city). |
| [../papers/PAPER_B_Comparison_EKF.md](../papers/PAPER_B_Comparison_EKF.md) | Model comparison + adaptive-EKF paper. |
| [../papers/PAPER_CONFERENCE_CrossCity.md](../papers/PAPER_CONFERENCE_CrossCity.md) | Conference paper (cross-city generalisation). |
| [../papers/TEAM_BRIEF.md](../papers/TEAM_BRIEF.md) · [../papers/README.md](../papers/README.md) | Team brief and papers index. |

## Other current docs

| Doc | What it is |
|---|---|
| [../README.md](../README.md) | Repository top-level overview. |
| [../dashboard/README.md](../dashboard/README.md) | Quick dashboard run guide. |
| [../results/paper_figures/README.md](../results/paper_figures/README.md) | Figure index (which figure goes where). |
| [../results/RUN_SUMMARY.md](../results/RUN_SUMMARY.md) | Auto-generated metrics summary of the latest run. |

## Archived (`/bnks`)

Superseded write-ups whose content is now folded into the three core references — kept for history,
not maintained: `ARCHITECTURE_COMPLETE_EXPLANATION.md`, `HOWTO_RUN.md`,
`PROJECT_GUIDE_LAYMAN_EXPLANATION.md`, `DATASET_PROCESSING_REPORT.md`, `PRESENTATION_SCRIPT.md`,
`PAPER_TOPICS.md`, and earlier dashboard/EKF scratch notes.
