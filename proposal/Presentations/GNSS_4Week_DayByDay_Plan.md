# SENTINEL-GNSS — 4-Week Day-by-Day Task Breakdown

**Project:** AI-Based Prediction of GNSS Signal Degradation for Autonomous Driving: A Pilot Study
**Team:** Ogunlade Joshua (LS2525237) · Mustapha Ibrahim (LS2525238) · Ojerinde Joel (LS2525253) · Ingeriyinkindi Claudine (LS2525236) · Rashid Md Harun Or (LS2525219)
**Institution:** Beihang University H3I · 2025
**Note:** 2 concurrent coursework modules. Weekend days (Days 7, 14, 21, 28) are used for integration, review, and buffer — not left empty.

---

## WEEK 1 — Setup & Data Extraction (Days 1–7)

**Goal by end of week:** All software working on every laptop, supervisor datasets through RTKLIB, Scenarios A and D collected and processed.

---

### Day 1 — Environment Setup (All members)

**All members — individually on their own machines:**
- Install RTKLIB (RTKCONV, RTKPOST, RTKPLOT). Verify using the RTKLIB sample dataset — you must see a position track in RTKPLOT before moving on.
- Install Anaconda/Miniconda. Create a project environment: `conda create -n gnss python=3.9`
- Install Python packages: `pip install pandas numpy scipy scikit-learn torch torchvision imbalanced-learn dash plotly folium pyserial`
- Install Git. Clone the shared GitHub repository (Joel creates it; others clone).

**Joel — GitHub repository:**
- Create the repo: `sentinel-gnss`
- Add folder structure: `data/raw/`, `data/rinex/`, `data/processed/`, `data/labelled/`, `src/extraction/`, `src/processing/`, `src/features/`, `src/models/`, `src/interface/`, `notebooks/`, `results/`
- Push initial commit with a `README.md` describing the project

**Deliverable by end of Day 1:** Every member has RTKLIB running and has cloned the GitHub repo.

---

### Day 2 — Room 3058 Visit + ROSBAG Inspection (All + Joshua)

**All members — visit Room 3058 together:**
- Record the receiver model number and firmware version
- Read the computer instructions posted near the receiver
- Learn how to start and stop a recording
- Identify the output file format (UBX binary, NMEA, or RINEX)
- Photograph the receiver, antenna, and setup configuration
- Ask the lab manager which port and baud rate the receiver uses

**Joshua — ROSBAG inspection (supervisor datasets):**
- Run `rosbag info vehicle_dataset.bag` — list all recorded topics
- Identify GNSS topics: look for `/fix`, `/gps/raw`, `/ublox/fix`, `/gnss`, `/navsat`
- Record all topic names, message types, and approximate epoch counts in a shared doc
- Do the same for the drone dataset

**Deliverable by end of Day 2:** GNSS topic names confirmed. Room 3058 setup fully documented with photos. Lab manager contact saved.

---

### Day 3 — ROSBAG Extraction Script (Joshua + Joel)

**Joshua — write `src/extraction/extract_gnss.py`:**
- Extract identified GNSS topics from the vehicle ROSBAG to CSV
- Each row: timestamp, latitude, longitude, altitude, SNR per satellite, pseudorange (where available)
- Run on the full vehicle dataset. Verify output row count matches expected epoch count.
- Commit script with a clear docstring

**Joel — RTKLIB familiarisation:**
- Run RTKCONV on a sample RINEX file from the RTKLIB docs
- Run RTKPOST: configure IGS precise orbit and clock files (download SP3 and CLK files for the relevant date from https://cddis.nasa.gov)
- Verify that RTKPOST produces a `.pos` solution file and that RTKPLOT shows a clean position track
- Document the exact RTKPOST settings (positioning mode, frequency, satellite systems) in the shared repo under `docs/rtklib_settings.md`

**Harun — begin literature search:**
- Search Google Scholar for: "GNSS signal degradation prediction", "GNSS quality prediction deep learning", "autonomous vehicle GNSS integrity"
- Target: identify 30 papers. Create a shared spreadsheet: columns = title, year, venue, method, dataset, key result, relevance to our work
- Aim to fill 10–15 entries today

**Deliverable by end of Day 3:** Vehicle GNSS CSV extracted and committed. RTKLIB settings documented.

---

### Day 4 — RTKLIB Pipeline on Supervisor Datasets (Joshua)

**Joshua — `src/processing/run_rtklib.py`:**
- Write a Python script that automates RTKCONV + RTKPOST for a given input file
- Run on the vehicle CSV (convert to RINEX first using RTKCONV, then RTKPOST)
- Run on the drone dataset
- Output: `.pos` files for both datasets with timestamps, corrected positions, and quality flags
- Visually inspect results in RTKPLOT — confirm position tracks match expected routes

**Claudine — data collection route planning:**
- Walk the campus. Identify exact locations for Scenarios A–E:
  - Scenario A: identify an underground entrance or enclosed building lobby with ≥100 m of open sky approach
  - Scenario B: identify a narrow building corridor with tall walls on both sides
  - Scenario C: identify a tree canopy path or covered walkway
  - Scenario D: identify an open sports ground or carpark with unobstructed 360° sky
  - Scenario E: identify a large building face you can walk toward with gradual obstruction
- Record GPS coordinates of each start/end point. Take photos. Create a route map sketch.
- Share map with team by end of day

**Mustapha — EKF background reading:**
- Read the Wikipedia article on Extended Kalman Filters and the RTKLIB manual section on Kalman filtering
- Find one published paper on GNSS/INS EKF fusion (search "GNSS IMU EKF tight coupling")
- Take notes: what are the state vector components, what is the observation model for GNSS

**Deliverable by end of Day 4:** RTKLIB `.pos` files generated for both supervisor datasets. Campus data collection routes confirmed and mapped.

---

### Day 5 — Scenario A & D Collection Session 1 (Claudine + Joshua + all available)

**Claudine — lead data collection:**
- Collect Scenario D (open sky baseline) first — minimum 30 minutes continuous recording
- Then collect Scenario A (open sky → complete blockage) — minimum 5 complete runs
- For each run: start recording before moving, walk at steady pace, complete the full approach and entry, stop recording after exiting
- Label each file immediately: `ScenarioA_run01.ubx`, `ScenarioA_run02.ubx`, etc.
- Note exact times of each blockage event in a logbook

**Joshua — real-time support and RTKLIB processing:**
- Bring a laptop to the field
- After each run, convert to RINEX and run RTKPOST immediately to verify the data is usable
- If a run produces no valid GNSS epochs, re-run that scenario before leaving the site

**Joel — begin feature extraction planning:**
- Write `src/features/feature_list.py` — a Python dict defining all 35 feature names, their source columns, and computation formulas
- This becomes the shared specification that Joshua's feature extraction code implements

**Deliverable by end of Day 5:** Scenario D (30+ min) and at least 3 Scenario A runs collected and RTKLIB-verified.

---

### Day 6 — Scenario A Completion + Processing Begins (Joshua + Claudine)

**Claudine + Joshua — Scenario A completion:**
- Collect remaining Scenario A runs (target: 10 total)
- Optionally begin Scenario E if time permits (gradual transition — only needs 3–5 reps)

**Joshua — RTKLIB processing of all collected data:**
- Run RTKPOST on all Scenario A and D files collected so far
- Verify position tracks are sensible. Flag any corrupted runs.
- Begin writing `src/features/extract_features.py` — compute all 35 features per epoch from RTKLIB `.pos` output

**Harun — literature review continuation:**
- Continue filling the literature spreadsheet. Target 25 papers by end of Day 6.
- Group papers into categories: (1) GNSS quality monitoring, (2) AI-based approaches, (3) sensor fusion, (4) public datasets used
- Draft 2–3 sentence summaries for each paper

**Deliverable by end of Day 6:** 10 Scenario A runs collected. Feature extraction script skeleton committed.

---

### Day 7 — Week 1 Review & Buffer (All members)

**Shared Saturday meeting (4 pm):**
- Each member gives a 3-minute update on their Day 1–6 work
- Joshua: demo RTKLIB pipeline running on supervisor data
- Claudine: present route map and data collection log
- Joel: walk through repo structure and feature list spec
- Harun: present literature spreadsheet progress
- Mustapha: share EKF reading notes

**Joshua — feature extraction script:**
- Complete `extract_features.py` and run it on Scenario A and D processed data
- Verify outputs: CSV with 35 columns + epoch timestamp + class label column (not yet filled)

**All members — Week 2 coordination:**
- Confirm availability for Scenarios B, C, E collection (Days 8–10)
- Confirm Harun will have baseline model environment ready by Day 10

**Deliverable by end of Day 7:** Feature CSV produced for Scenario A and D data. Week 2 schedule confirmed. Repo has clean commit history.

---

## WEEK 2 — Full Data Collection & Feature Engineering (Days 8–14)

**Goal by end of week:** All 5 scenarios collected and processed, feature dataset assembled and labelled, all baseline models trained, literature review drafted.

---

### Day 8 — Scenarios B & C Collection (Claudine + Joshua + available members)

**Claudine — lead:**
- Scenario B (urban canyon): 5 complete traversals of the narrow building corridor. Each traversal 300–500 m.
- Scenario C (partial obstruction): 3 sessions under tree canopy / covered walkway, 15–20 minutes each

**Joshua — real-time RTKLIB verification on laptop**

**Joel — model architecture design:**
- Write `src/models/transformer_lstm.py` — skeleton class with `__init__` and `forward` methods
- Define: input shape `(batch, 30, 35)`, Transformer encoder block (4 heads, d=64, 2 layers), LSTM decoder (hidden=128, 2 layers), 3 output heads
- Do not train yet — just get the architecture instantiating without errors and print parameter count

**Mustapha — dashboard planning:**
- Sketch the 5-panel layout on paper (map, signal quality, AI gauges, sky plot, fusion status)
- Research Dash components needed: `dcc.Graph` (Plotly), `dcc.Interval`, `dcc.Store`
- Create `src/interface/dashboard.py` skeleton with placeholder panels

**Deliverable by end of Day 8:** Scenarios B and C collected and RTKLIB-verified. Model architecture skeleton committed.

---

### Day 9 — Scenario E Collection + Feature Extraction (Claudine + Joshua)

**Claudine — lead:**
- Scenario E (gradual degradation transition): approach 3 different building faces from open sky, stopping at intervals. Repeat 5 times per building face.

**Joshua — feature extraction:**
- Run `extract_features.py` on all Scenario B, C, E data
- Check output: verify that each scenario produces the expected class distribution (B/C should have WARNING epochs; A should have DEGRADED; D should be all CLEAN)
- Fix any bugs in the feature computation

**Harun — begin baseline model implementations:**
- Write `src/models/baseline_threshold.py`: SNR threshold classifier — if mean C/N0 < 30 dB-Hz, class = DEGRADED; if 30–35, WARNING; else CLEAN
- Write `src/models/baseline_rf.py`: Random Forest using scikit-learn on the full 35-feature set (no temporal modelling)
- Do not train yet — just get the inference logic working on a dummy input

**Deliverable by end of Day 9:** All 5 scenarios collected. Feature CSVs ready for all scenarios.

---

### Day 10 — Dataset Assembly + Labelling (Joshua + Joel)

**Joshua — `src/features/assemble_dataset.py`:**
- Merge all scenario feature CSVs into one master dataset
- Add ground truth labels per epoch: CLEAN (positioning error <2 m, mean C/N0 >35 dB-Hz), WARNING (error 2–5 m or C/N0 30–35 dB-Hz), DEGRADED (error >5 m, C/N0 <30 dB-Hz, or SV count <4)
- Compute class distribution and print it. If DEGRADED class is <3% of data, revisit Scenario A collection.
- Apply sliding window segmentation: 30-second input window, predict at 5s, 15s, 30s ahead
- Apply temporal train/val/test split (70/15/15 — by time, not random)

**Joel — training loop:**
- Write `src/models/train.py`: data loader, training loop with Adam optimiser, early stopping on validation F1-score, model checkpoint saving
- Implement Focal Loss in `src/models/losses.py`
- Implement SMOTE call from `imbalanced-learn` — apply to training set only

**Mustapha — EKF implementation begins:**
- Write `src/models/ekf.py`: 9-state EKF (position 3D, velocity 3D, attitude 3D)
- Implement the adaptive R formula: `R = R_base × (1 + 10 × P_degraded)`
- Test with dummy inputs: when `P_degraded=0`, output should equal standard EKF; when `P_degraded=0.9`, GNSS weight should drop to ~10% of standard

**Deliverable by end of Day 10:** Master labelled dataset assembled. Training loop committed. EKF skeleton functional.

---

### Day 11 — Baseline Model Training (Harun + Joel)

**Harun — train and evaluate all baselines:**
- Threshold classifier: run on test set. Record precision, recall, F1, AUC-ROC per class.
- Random Forest: train on training set, evaluate on test set. Record same metrics.
- Fill in the baseline results table in `results/baseline_results.csv`

**Joel — Single LSTM baseline:**
- Write `src/models/baseline_lstm.py`: standard 2-layer LSTM on the 30-second window, no Transformer
- Train and evaluate on same splits. Record metrics in results table.
- This is the ablation that proves the Transformer attention adds value

**Claudine — UrbanNav and Oxford RobotCar processing:**
- Download UrbanNav dataset from https://github.com/IPNL-POLYU/UrbanNavDataset (follow their instructions — the data requires registration)
- Download Oxford RobotCar GNSS files
- Run RTKLIB on both. Extract the same 35 features using `extract_features.py`. Do NOT add these to the training set — store them separately in `data/processed/public/`

**Deliverable by end of Day 11:** All baselines trained. Results table partially filled. Public dataset feature files generated.

---

### Day 12 — Baseline Evaluation + Literature Review Draft (Harun + all)

**Harun — complete literature review draft:**
- Write Section 2 (Related Work) of Paper 1: minimum 600 words, 25 citations
- Structure: (1) GNSS quality monitoring methods, (2) ML/DL approaches to GNSS prediction, (3) sensor fusion for GNSS-degraded navigation, (4) gap this work fills
- Share draft in GitHub under `paper/related_work_draft.md`

**Joel — RAIM baseline:**
- Implement a simplified RAIM (Receiver Autonomous Integrity Monitoring) consistency check using pseudorange residuals
- Record prediction lead time vs. your threshold and LSTM baselines — this is the key comparison the examiners will ask about

**Mustapha — dashboard Panel 2 (signal quality):**
- Implement Panel 2: three scrolling Plotly time-series (mean C/N0, SV count, PDOP) updating from a data file playback loop
- Verify the dashboard runs locally and updates at 1 Hz

**Deliverable by end of Day 12:** RAIM baseline complete. Literature draft committed. Dashboard Panel 2 rendering.

---

### Day 13 — Dataset QA + Model Preparation (Joshua + Joel)

**Joshua — dataset quality check:**
- Plot histograms of all 35 features — check for obviously wrong values (e.g., C/N0 of 0 when SV count >0, negative DOPs)
- Check for NaN rows — impute or drop as appropriate
- Verify temporal split: confirm there is no data leakage between train/val/test
- Run z-score normalisation on training set. Apply same mean/std to val and test sets. Save normalisation parameters.

**Joel — full model first training run:**
- Run `train.py` on the full labelled dataset for the Transformer-LSTM
- Use: Adam lr=1e-4, weight decay 1e-5, cosine annealing scheduler, max 200 epochs, early stopping patience 20
- Let it run. Monitor training loss and validation F1 every 10 epochs.
- This run may not finish today — leave it running overnight if needed

**Claudine — KAIST status check:**
- Check email for KAIST dataset delivery
- If received: run RTKLIB, extract features, store in `data/processed/public/kaist/`
- If not received: confirm UrbanNav and RobotCar files are fully processed and ready

**Deliverable by end of Day 13:** Normalised dataset committed. Transformer-LSTM training started.

---

### Day 14 — Week 2 Review + Buffer (All members)

**Shared Saturday meeting (4 pm):**
- Harun: present baseline results table. Compare threshold vs RF vs LSTM.
- Joshua: demo the full dataset pipeline from raw ROSBAG → labelled windows
- Joel: show training loss curves so far (even if training is still running)
- Claudine: show UrbanNav/RobotCar feature files are ready
- Mustapha: demo Panel 2 dashboard

**All — Week 3 planning:**
- Joel: estimate when Transformer-LSTM training will complete. Set target: first test results by Day 17.
- Mustapha: confirm EKF and remaining 4 dashboard panels for Week 3.
- Assign paper section drafting responsibilities for Week 4.

**Deliverable by end of Day 14:** All baseline results recorded. Dataset pipeline fully documented. Week 3 assignments confirmed.

---

## WEEK 3 — Model Training & System Build (Days 15–21)

**Goal by end of week:** Transformer-LSTM fully trained and evaluated, all ablation studies done, generalisation tests complete, EKF working, dashboard fully functional with recorded data.

---

### Day 15 — Model Results + Ablation Setup (Joel + Mustapha)

**Joel — evaluate Transformer-LSTM first results:**
- If training completed overnight: evaluate on test set. Record precision, recall, F1, AUC-ROC, prediction lead time for all 3 horizons.
- Compare against baseline results. Identify which metric the model most clearly improves.
- If results are weak: diagnose — check learning curves for overfitting, check class balance in training batch, verify Focal Loss is applying correctly.

**Joel — set up ablation experiments:**
- Create configs for 5 ablations (see Section 5.4 of the framework document)
- Start training: (1) No attention / LSTM-only and (2) Single-horizon (5s only)

**Mustapha — EKF testing:**
- Run the EKF on a simulated degradation scenario: feed in a recorded position sequence, inject a degradation event, verify that R adapts as expected
- Plot GNSS weight vs time — it should drop when `P_degraded` rises and recover when signal clears

**Deliverable by end of Day 15:** First Transformer-LSTM test results in results table. Two ablations training.

---

### Day 16 — Ablation Studies (Joel + Claudine)

**Joel — ablation training continues:**
- Start ablations (3) Geometry features only, (4) Vehicle data only, (5) No SMOTE / focal loss
- Evaluate completed ablations as they finish. Fill in ablation results table.

**Claudine — generalisation testing setup:**
- Load UrbanNav feature files. Apply the SAME normalisation parameters from training (do NOT refit).
- Run the trained Transformer-LSTM on UrbanNav data. Record F1-score.
- Repeat for Oxford RobotCar.
- Compare cross-geography F1 against in-distribution test F1. Target: within 10%.

**Harun — Introduction section draft:**
- Write Section 1 (Introduction) of Paper 1: 500–700 words
- Structure: (1) GNSS importance for AVs, (2) limitations of current systems, (3) proposed proactive prediction approach, (4) numbered contributions list
- Share in GitHub under `paper/introduction_draft.md`

**Mustapha — Dashboard Panels 1 and 3:**
- Panel 1 (map): implement Leaflet/Folium map with colour-coded GPS track (green/amber/red by class label from a recorded playback file)
- Panel 3 (prediction gauges): implement three semicircular Plotly gauges for 5s/15s/30s degradation probability, with NOMINAL/CAUTION/ALERT banner

**Deliverable by end of Day 16:** Generalisation test results recorded. Panels 1 and 3 rendering.

---

### Day 17 — Full Results Assembly (Joel + Claudine + all)

**Joel — complete ablation results table:**
- All 5 ablations evaluated. Table complete: rows = models, columns = Macro F1, AUC-ROC, prediction lead time.
- Colour-code best result in each column.
- Write brief interpretation (2–3 sentences per ablation) explaining what the result proves.

**Claudine — KAIST (if received) and results summary:**
- If KAIST arrived: run generalisation test, add to the table
- Write a 1-paragraph summary of generalisation findings: what F1 drop (if any) occurred, what it means for the cross-geography claim

**Joel — navigation RMSE analysis:**
- Connect EKF to the Transformer-LSTM output on recorded test data
- Measure position RMSE: (a) GNSS-only, (b) standard EKF (fixed R), (c) adaptive EKF with model predictions
- This becomes the "Navigation Impact" bar chart (Slide 17 equivalent)

**Deliverable by end of Day 17:** All results tables fully populated. RMSE comparison computed.

---

### Day 18 — Dashboard Panels 4 & 5 + System Integration (Mustapha + Joel)

**Mustapha — Dashboard Panels 4 and 5:**
- Panel 4 (sky plot): implement azimuth/elevation circular plot, satellites as coloured dots (green/amber/red by C/N0), updating from playback
- Panel 5 (fusion status): stacked horizontal bar showing GNSS%/IMU% updating as `P_degraded` changes from model output

**Mustapha — full dashboard integration:**
- Connect all 5 panels to a single data playback loop reading from a recorded test session file
- Verify all panels update simultaneously at 1 Hz
- Measure end-to-end latency: time from data read to panel update. Target <100 ms.

**Joel — model packaging:**
- Save trained Transformer-LSTM as `results/transformer_lstm_best.pt`
- Write `src/models/inference.py`: loads checkpoint, takes a 30-second feature window, returns 3 probability vectors
- Test inference time: time 1000 forward passes, compute mean and std

**Deliverable by end of Day 18:** Full 5-panel dashboard running with recorded data at 1 Hz.

---

### Day 19 — Live System Test Preparation (All)

**Mustapha — connect to Room 3058 receiver:**
- Connect receiver to laptop via USB. Identify port: `ls /dev/ttyUSB*` on Linux or Device Manager on Windows
- Open serial connection with pyserial: `serial.Serial('/dev/ttyUSB0', 115200)`
- Parse incoming NMEA or UBX messages. Verify timestamps, positions, and C/N0 values are appearing correctly
- Log 10 minutes of live data to a file. Verify it can be run through `extract_features.py`.

**Joel — connect model to live feed:**
- Write `src/interface/live_inference.py`: reads from the pyserial queue, builds 30-second feature windows, calls `inference.py` every second, pushes probability output to the dashboard
- Test with 5-minute live recording from the receiver in the lab (not yet outdoors)

**All — campus route rehearsal:**
- Walk Scenario A route together without collecting data — confirm the blockage point is clearly identifiable and the path is safe for a live demo with a laptop

**Deliverable by end of Day 19:** Live receiver connection working. Model running on live feed in the lab.

---

### Day 20 — Live Campus Test + Video Recording (All members)

**The single most important day of the project.**

**All members — attend the live test:**
- One member pushes the cart with the receiver
- One member carries the laptop running the full dashboard
- One member records screen capture video (OBS Studio or similar)
- One member monitors the dashboard and narrates for the video
- One member photographs the setup

**Sequence of the demo:**
1. Start in open sky (Scenario D location). Show NOMINAL status. Record 2 minutes.
2. Walk toward building entrance (Scenario E route). Show prediction probability rising.
3. Enter blockage zone (Scenario A). Show ALERT status, gauge hitting red, GNSS weight dropping.
4. Exit back to open sky. Show system recovering.

**The video should be 60–90 seconds** for the final presentation (Slide 19 equivalent). Edit immediately after collection.

**Deliverable by end of Day 20:** Screen capture video recorded and saved. Full live test log saved.

---

### Day 21 — Week 3 Review + Paper Preparation (All members)

**Shared Saturday meeting (4 pm):**
- Joel: present final results tables (baseline comparison, ablation, generalisation)
- Mustapha: demo the full 5-panel dashboard with live or playback data
- All: watch the demo video together. Agree on the final cut to use in the presentation.

**All — paper section assignments for Week 4:**
- Joel: Sections 4 (Methodology) + 5 (Experiments) — most technical, largest word count
- Harun: Section 2 (Related Work) — already drafted; expand and refine
- Joshua: Section 3 (Dataset & Features) — documents everything from Weeks 1–2
- Claudine: Section 5 results tables and figures — format and number-fill
- Mustapha: Section 6 (System Demonstration) — documents dashboard and live test

**Deliverable by end of Day 21:** All quantitative results finalised. Paper section assignments agreed.

---

## WEEK 4 — Integration, Demo & Paper Draft (Days 22–28)

**Goal by end of week:** Paper 1 first draft complete and reviewed by all members. Presentation rehearsed and ready.

---

### Day 22 — Paper Writing Begins (All — parallel)

**Joel — Sections 4 & 5 (Methodology + Experiments):**
- Section 4: Transformer-LSTM architecture, training protocol, class imbalance handling, EKF formulation — target 1,200 words
- Section 5: results tables (already complete), narrative interpretation of each table, ablation commentary

**Harun — Section 2 (Related Work):**
- Expand draft to final length (~800 words, 25–30 citations)
- Ensure every cited paper is accurately described and its limitation relative to this work is stated

**Joshua — Section 3 (Dataset & Features):**
- Describe collection methodology, scenarios, RTKLIB pipeline, feature list, labelling criteria, class distribution — target 800 words

**Claudine — Section 5 figures:**
- Format baseline comparison table in LaTeX or Word
- Create: (1) training loss/F1 curves, (2) generalisation bar chart, (3) prediction lead time histogram

**Mustapha — Section 6 (System Demonstration):**
- Describe dashboard panels, technology stack, live test results, measured latency — target 500 words

**Deliverable by end of Day 22:** All sections in first-draft state (even rough).

---

### Day 23 — Paper Draft Assembly + Abstract (Joel)

**Joel — assemble full paper draft:**
- Merge all section drafts into a single document
- Write Abstract (250 words): Problem → Why it matters → What you did → Key results (specific numbers) → Conclusion. Write this using the actual numbers from the results tables.
- Write Section 1 (Introduction): 600 words, numbered contributions list
- Write Section 7 (Conclusion): 300 words — summary, limitations, future work

**All — review assigned sections of other members:**
- Each member reads one other member's section and adds comments

**Deliverable by end of Day 23:** Complete first draft of Paper 1 assembled and shared with team.

---

### Day 24 — Team Paper Review (All)

**All members — read the full draft:**
- Check: is every table correctly interpreted in the narrative? Are the numbers consistent between the abstract and Section 5? Are all 4 novelty claims explicitly stated in the Introduction?
- Each member writes 3–5 specific comments in the shared document
- Flag any results that look unexpectedly weak — these need a sentence of explanation or an additional analysis

**Joel — address comments and revise:**
- Incorporate team feedback into revised draft by end of day

**Deliverable by end of Day 24:** Revised second draft of Paper 1.

---

### Day 25 — Presentation Polish (All)

**All members — review the proposal PPTX:**
- Verify slide 19 (timeline) matches what was actually done
- Verify slide 14 (baseline table) and slide 16 (generalisation) have the actual numbers from the results
- Verify slide 18 (team responsibilities) accurately reflects each member's work

**Each member — rehearse their own slides:**
- Practice presenting your 4 slides aloud. Time yourself. Target: 4–5 minutes per member.
- Prepare 2 answers to anticipated examiner questions relevant to your slides (see Section 12 of the framework document)

**Deliverable by end of Day 25:** PPTX updated with real numbers. Each member has rehearsed their section once.

---

### Day 26 — Full Rehearsal (All members)

**Full team — complete run-through of the 20-slide presentation:**
- Present end-to-end, timed. Target: 20–22 minutes.
- After each member's section, other members ask 1–2 questions as if they are examiners
- Note: which slides generate the most questions? Those are the ones to refine.

**Identified weak points — fix same day:**
- If a slide is confusing, revise it immediately after the rehearsal
- If the demo video is too long, edit it down to 60 seconds

**Deliverable by end of Day 26:** One full timed rehearsal completed. All slides finalised.

---

### Day 27 — Final Paper Checks + Submission Prep

**Joel — final paper check:**
- Proofread the full paper for typos, inconsistent notation, missing citations
- Verify: every figure has a caption, every table has a title, all abbreviations are defined on first use
- Format references correctly (IEEE citation style)

**All — open issues:**
- If KAIST data arrived late: add results to the paper and update the generalisation slide
- Confirm supplementary materials list: labelled dataset, ROSBAG extraction pipeline, model code + weights, interface code — all committed to GitHub

**Deliverable by end of Day 27:** Paper draft submission-ready. Supplementary materials committed.

---

### Day 28 — Final Buffer + Submission (All)

**Shared meeting (morning):**
- Final decisions: is the paper ready to submit? Are the presentation slides final?
- Any last-minute data quality issues to address?

**All:**
- Submit paper to target venue (or submit to supervisor for review, per course requirement)
- Archive the full project: backup GitHub repo, results CSVs, trained model checkpoint, and demo video

**Deliverable by end of Day 28:** Paper submitted. Presentation finalised. Project archived.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Room 3058 receiver unavailable | Medium | High | Book in advance. Have a backup date by Day 3. |
| KAIST dataset never arrives | Medium | Low | UrbanNav + RobotCar alone prove cross-geography generalisation. |
| Transformer-LSTM training underperforms baselines | Low | High | Diagnose by Day 16. Most likely fix: class weights or focal loss tuning. |
| Dashboard latency >100 ms | Low | Medium | Profile with cProfile. Most likely bottleneck: feature computation, not model inference. |
| Team member unavailable for data collection | Medium | Medium | All collection sessions: minimum 3 members. Reschedule within 24 hours. |
| ROSBAG extraction produces corrupted data | Low | Medium | Validate row count and timestamp continuity before RTKLIB. Re-extract if anomalous. |

---

## Key Numbers to Track

Record these after each milestone and update the results table in the shared repo:

- Class distribution in final labelled dataset (% CLEAN / WARNING / DEGRADED)
- Baseline Macro F1: Threshold / Random Forest / Single LSTM / RAIM
- Transformer-LSTM Macro F1: in-distribution test set
- Prediction lead time: seconds before event that the model first raises ALERT
- Cross-geography Macro F1: UrbanNav / KAIST (if available) / RobotCar
- Navigation RMSE: GNSS-only vs standard EKF vs adaptive EKF (% reduction)
- Dashboard end-to-end latency: ms

---

*— SENTINEL-GNSS Team · Beihang University H3I · 2025 —*
