# NotebookLM Extraction Prompts

## How to use: Upload up to 50 PDFs into a NotebookLM notebook, then paste each prompt below

---

## HOW TO SET UP NOTEBOOKLM

1. Go to notebooklm.google.com → New notebook
2. Upload all your downloaded PDFs (can upload up to 50 per notebook)
3. Split into two notebooks: one for Paper A references, one for Paper B references
4. Paste each prompt below into the chat box
5. NotebookLM will extract the specific fact from every uploaded paper
6. Copy the results into a spreadsheet, then update the .tex files

---

## BATCH 1 — CITATION KEY & METADATA

_Use this first to build your reference list_

**Prompt 1.1 — Basic metadata extraction:**

```
For each paper in this notebook, extract in a numbered table:
(1) First author surname + year (e.g., Smith2021)
(2) Full title
(3) Journal/conference name
(4) Year
(5) DOI if visible

Format: | Key | Title | Venue | Year | DOI |
```

---

## BATCH 2 — PAPER A SPECIFIC EXTRACTIONS

_Run these in the Paper A references notebook_

**Prompt 2.1 — GNSS degradation methods summary:**

```
For each paper that describes a method to detect or classify GNSS signal degradation or NLOS:
(1) What input features does the method use?
(2) What classification approach (threshold, SVM, RF, DL, etc.)?
(3) What dataset was used (location, receiver type, duration)?
(4) What metric was reported (accuracy, F1, recall)?
(5) What is the best reported number for DEGRADED/NLOS class detection?

Table format: | Author | Method | Features | Dataset | Best metric | Value |
```

**Prompt 2.2 — Baseline comparison numbers:**

```
For each paper that compares multiple machine learning models on GNSS data:
(1) Which models were compared?
(2) What was the primary metric?
(3) What were the top-3 model scores on that metric?
(4) Did they report per-class results (especially the degraded/fault class)?
(5) What class imbalance ratio did they have?

I need this to position SENTINEL's 0.847 DEGRADED recall vs. RF 0.727 / XGB 0.722.
```

**Prompt 2.3 — Transformer architecture in navigation:**

```
For each paper using Transformer or self-attention for navigation / positioning / GNSS:
(1) What is the input sequence length and feature dimension?
(2) How many Transformer layers and attention heads?
(3) Is there an LSTM component? If so, what configuration?
(4) What prediction task (classification, regression)?
(5) What performance improvement did they show vs. an RNN baseline?

I need comparisons for our architecture: 30-step, 37-feature, 2 Transformer layers, 8 heads, 2-layer LSTM.
```

**Prompt 2.4 — Cross-city / domain generalisation:**

```
For each paper that evaluates a trained model on a dataset from a different city or receiver:
(1) What was the training domain (city, receiver)?
(2) What was the test domain (city, receiver)?
(3) How much did performance drop (e.g., F1 from X to Y)?
(4) What technique did they use to mitigate domain shift?
(5) Did they use an ensemble to recover performance?

I need to contextualise our Tokyo cross-city drop (0.821 → 0.649) and ensemble recovery to 0.892.
```

**Prompt 2.5 — SMOTE and class imbalance handling:**

```
For each paper that uses SMOTE or other oversampling/undersampling for GNSS or navigation data:
(1) What was the imbalance ratio (minority class %)?
(2) Which oversampling method was used?
(3) Did SMOTE improve minority class recall specifically?
(4) By how much vs. no oversampling?

We found SMOTE gives negligible gain (RF: 0.910 with or without SMOTE).
I need papers that confirm or contradict this finding.
```

**Prompt 2.6 — Persistence baseline:**

```
For each paper that uses a "persistence" or "naive" baseline (predict current state as future state):
(1) What is the prediction horizon?
(2) What is the label change rate at that horizon?
(3) What Macro-F1 / accuracy does persistence achieve?
(4) How does the proposed method beat persistence specifically on transition windows?

Our persistence Macro-F1 = 0.908 at 5s (label change rate = 5.6%).
I need citations that explain why persistence is not a valid comparison despite high accuracy.
```

---

## BATCH 3 — PAPER B SPECIFIC EXTRACTIONS

_Run these in the Paper B references notebook_

**Prompt 3.1 — EKF GNSS/INS results comparison:**

```
For each paper that reports GNSS/INS EKF results on urban data:
(1) What EKF variant (9-state, 15-state, loose/tight coupling)?
(2) What dataset / location / duration?
(3) What overall RMSE was achieved?
(4) What RMSE was achieved during GNSS degradation or outage?
(5) What percentage improvement over raw GNSS was reported?

I need to compare our 9-state EKF: 48.8% reduction during degraded epochs (Tokyo Shinjuku).
```

**Prompt 3.2 — Adaptive Kalman filter performance:**

```
For each paper that proposes an adaptive Kalman filter for GNSS/INS:
(1) What adaptation mechanism was used (Sage-Husa, IMM, innovation-based, ML-based)?
(2) Was the adaptation reactive (triggered after degradation) or predictive (before)?
(3) What was the improvement over fixed-noise EKF during degraded epochs (% RMSE)?
(4) What dataset / environment?

Our key claim: calibrated SENTINEL achieves ~38.7% vs. 48.8% for fixed-R.
I need papers that show adaptive filtering performance range for urban GNSS.
```

**Prompt 3.3 — Tunnel / GNSS outage navigation:**

```
For each paper reporting vehicle navigation through a tunnel or GNSS outage:
(1) How long was the GNSS outage (seconds / metres)?
(2) What navigation method was used during outage (dead reckoning, map matching, WiFi)?
(3) What position error accumulated at the end of the outage?
(4) What improvement vs. hold-last or simple dead reckoning was shown?

Our tunnel: 151-second outage, hold-last 1081 m, CV-EKF 912 m, SENTINEL-EKF 751 m (+30.6%).
I need context for how typical tunnel results look in the literature.
```

**Prompt 3.4 — Non-holonomic constraint and ZUPT:**

```
For each paper implementing Non-Holonomic Constraint (NHC) or Zero Velocity Update (ZUPT)
in a vehicle navigation filter:
(1) What was the improvement from NHC/ZUPT vs. pure INS during GNSS outage?
(2) At what vehicle speed does ZUPT fire?
(3) Was NHC implemented as a pseudomeasurement or hard constraint?
(4) What is the typical velocity measurement noise std used for NHC?
```

**Prompt 3.5 — V2I / cooperative GNSS reliability:**

```
For each paper on V2I or cooperative vehicle positioning that involves GNSS quality:
(1) What information is exchanged between vehicles or with infrastructure?
(2) How is GNSS reliability / quality shared?
(3) What positioning accuracy improvement was demonstrated?
(4) What communication technology was used (DSRC, C-V2X, 5G)?

I need these to support the section on extending per-vehicle SENTINEL to fleet-level
GNSS reliability maps via V2I.
```

**Prompt 3.6 — Receiver domain shift and calibration:**

```
For each paper that describes receiver-specific or hardware-specific characteristics
affecting machine learning models applied to GNSS signals:
(1) What hardware differences caused the domain shift (single vs. dual frequency, chipset, etc.)?
(2) What calibration or adaptation method was used?
(3) Was the calibration supervised (requires labels) or unsupervised?
(4) How much did the adaptation recover performance?

Our calibration: unsupervised P5-floor subtraction, recovers from 14.3% to ~38.7% improvement.
```

---

## BATCH 4 — QUALITY & RELEVANCE CHECKS

_Run on both notebooks to verify papers are suitable_

**Prompt 4.1 — Identify strongest cite-worthiness:**

```
Review all papers in this notebook and rank the top 10 most relevant to cite in a paper about:
- GNSS signal degradation prediction using Transformer-LSTM neural networks
- Multi-horizon classification at 5, 15, 30 seconds ahead
- Evaluation on Beijing urban field data and cross-city test on Tokyo

For each of the top 10: explain in one sentence WHY it should be cited and WHERE
(Introduction, Related Work, Dataset section, Experimental section, Discussion).
```

**Prompt 4.2 — Find contradicting or challenging results:**

```
Which papers in this notebook report results that CONTRADICT or CHALLENGE these claims:
(a) Deep learning outperforms Random Forest on GNSS quality tasks
(b) Temporal sequence models improve over snapshot classifiers for GNSS
(c) Class weighting / focal loss improves minority-class detection

For each challenging paper: what did they find, and how should I address it in the Discussion?
```

**Prompt 4.3 — Key statistics to fill into the paper:**

```
For each paper, extract any specific numerical results that could fill these placeholders
in my LaTeX draft:

For Paper A:
- "GNSS degradation detection accuracy / F1 in urban environments" (fill [AuthorYear_ML_GNSS_review])
- "NLOS/multipath error magnitude in urban canyons" (fill [AuthorYear_NLOS_multipath_survey])
- "Typical urban GNSS horizontal position error range" (fill multiple)

For Paper B:
- "EKF RMSE improvement during GNSS degradation %" (fill [AuthorYear_adaptive_KF])
- "Tunnel outage duration in typical urban routes" (fill [AuthorYear_tunnel])
- "V2I communication range / latency for positioning" (fill [AuthorYear_V2I])

Return: | Paper | Metric | Value | Which placeholder to fill |
```

**Prompt 4.4 — Introduction gap analysis:**

```
Based on all papers in this notebook, identify what problem or gap in the literature
is NOT addressed by any existing work, such that our SENTINEL contribution is novel.

Focus on:
1. Does any paper predict GNSS degradation AT MULTIPLE FUTURE HORIZONS simultaneously?
2. Does any paper use a Transformer-LSTM hybrid specifically for GNSS quality?
3. Does any paper close the loop from ML prediction → adaptive EKF covariance schedule
   on REAL multi-sensor urban data (not simulation)?
4. Does any paper report cross-city zero-shot transfer for GNSS degradation prediction?

For each gap: "Gap X: [description]. Current best: [paper+result]. Our contribution: [what we add]."
```

---

## BATCH 5 — SPECIFIC MISSING NUMBERS (update paper after reading refs)

After reading your papers, search NotebookLM for these specific facts to fill into the LaTeX:

**For Paper A Introduction:**

```
What is the typical horizontal position error (metres) caused by NLOS signals
in dense urban canyons, according to papers in this notebook?
Give: mean error, max error, and which paper reported it.
```

```
What percentage of urban epochs are typically affected by NLOS / multipath signals?
Give the number and source paper.
```

**For Paper A Related Work:**

```
What is the best NLOS detection recall or F1 reported by any non-deep-learning method
(SVM, RF, threshold) in papers in this notebook?
We need to justify why our 0.847 DEGRADED recall is state-of-the-art.
```

**For Paper B Introduction:**

```
What is the typical GNSS outage duration in urban tunnels on road networks?
How many seconds / metres does a typical cross-harbour or road tunnel cause?
```

```
What position accuracy requirement (in metres) is specified for autonomous vehicle
safety-critical operations according to standards papers in this notebook?
```

**For Paper B Discussion (V2I section):**

```
What is the communication latency of C-V2X / DSRC / 5G that would be relevant
to transmitting GNSS quality predictions between vehicles?
The 5-second prediction horizon means we need latency << 5 seconds.
```
