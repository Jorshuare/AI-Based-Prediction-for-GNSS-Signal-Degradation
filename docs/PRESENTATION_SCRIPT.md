# SENTINEL-GNSS: Presentation Script
# Defence / Demo Day — Beihang University RCSSTEAP

> **How to use this script:** Each section maps to a slide or slide group. The script gives you both a **Layman version** (for non-technical audience or opening) and a **Technical version** (for professors, reviewers). In the actual presentation, blend both — open with the story, anchor with the number.

---

## OPENING (Before slide 1 appears)

*Stand up, pause, make eye contact, then say:*

> "I want to start with a simple question. You are in a self-driving taxi in Tokyo, going through Shinjuku — one of the densest urban canyons in the world. Forty-storey glass buildings on both sides. And your vehicle's GPS says you are in the middle of a building. The car has to decide: do I trust GPS right now, or don't I? And it has to decide in a fraction of a second, before the wrong turn is made. That is the problem we are solving."

---

## Slide 1: Title

> "The project is called SENTINEL-GNSS. The name comes from a sentinel — a guard posted to give advance warning before the enemy arrives. Our system is a guard for your GPS signal. It warns the navigation system that signal quality is about to drop — five seconds before it actually happens — so the car can prepare."

---

## Slides 4–5: Problem Statement

### Layman version
> "GPS works by timing signals from satellites 20,000 kilometres above us. In open sky, that works perfectly — the signal travels straight down to your receiver. But in a city, those signals bounce off buildings. The receiver gets a reflected signal that travelled a longer path, and it thinks the satellite is farther away than it is. It computes the wrong position. Sometimes 30 metres wrong. Sometimes 100 metres wrong. And it doesn't tell you. It just gives you a confident-looking reading with a 100-metre error."

> "For a self-driving car, 100 metres is the difference between your lane and a bus stop. For a drone delivery, it is the difference between landing on your roof and landing on your neighbour's car. For an ambulance using GPS for routing, it is the difference between taking the right street and the wrong one. Current systems find out something is wrong AFTER the error has already entered the navigation filter. We wanted to find out BEFORE."

### Technical version
> "The formal problem: multipath and NLOS errors in urban GPS produce a heavy-tailed, non-Gaussian, positively-biased measurement error distribution. The standard EKF measurement model assumes zero-mean Gaussian noise. When a 100-metre bias enters an EKF calibrated for 4-metre noise, the Kalman gain — which should be small — is too large, and the filter aggressively jumps toward the wrong position. We want to predict, from historical signal quality features, that this is about to happen — 5 to 30 seconds before it does."

---

## Slides 6–7: Data

> "We used the UrbanNav public dataset — real GPS, IMU, and centimetre-accurate RTK ground truth from drives through Hong Kong. 149,662 one-second labelled epochs. Three classes: CLEAN — signal is good, trust it. WARNING — signal is degrading, be careful. DEGRADED — signal is bad, the filter should not trust it."

> "A quick sense of scale: imagine driving in Hong Kong for about 40 hours total, stopping and starting, going through tunnels, alongside 30-storey buildings, over flyovers. That is the dataset."

---

## Slides 8–9: Method — System Pipeline

> "Our system has three layers. Think of them as a doctor, a pharmacist, and a nurse."

> "The **doctor** — SENTINEL, our AI model — looks at the patient (the GPS signal quality features) and gives a diagnosis: 'signal will be bad in 5 seconds.' This is the prediction."

> "The **pharmacist** — the Extended Kalman Filter — receives the prescription (the P(DEGRADED) probability) and adjusts the dose: how much should we trust GPS right now? High P means inflate R, trust GPS less. Low P means keep R small, trust GPS fully."

> "The **nurse** — wheel odometry, non-holonomic constraint, zero-velocity updates — keeps the patient alive during the GPS blackout. Even when we cannot trust GPS at all, wheel speed tells us how fast we are going, NHC tells us we are not sliding sideways, and ZUPT tells us we are stopped at a red light. Together they hold the position estimate steady until GPS recovers."

---

## Slides 10–12: Architecture Details

> "The AI model uses a Transformer + LSTM architecture. Here is why two components instead of one:"

> "The Transformer is like a panoramic camera — it can see the entire 30-second history at once, in all directions. It spots patterns like: 'satellite count dropped at second 1, and PDOP started rising at second 15 — this pattern precedes a blockage.'"

> "The LSTM is like a tracker — it follows the sequence step by step, capturing how the signal is changing moment to moment. It catches rapid transitions that the big-picture Transformer might smooth over."

> "Together, Macro-F1 = 0.8206 at +5 seconds. Either alone gives 0.767 — a 5.3 point improvement from combining them. That is the architecture justification."

### If asked about temperature scaling:
> "We apply temperature scaling as a post-processing step to convert raw logits into calibrated probabilities. This matters because P(DEGRADED) is used as a risk score for the EKF — it needs to mean what it says. Uncalibrated, the model might output P=0.9 for something that is only 60% likely to be degraded. Temperature scaling fits a single scalar T so that P(DEGRADED)=0.8 truly happens 80% of the time in the validation data. This is the standard calibration technique from Guo et al. (2017)."

---

## Slide 14: In-Domain Results (Macro-F1 = 0.821)

> "In Hong Kong — where the model was trained — Macro-F1 is 0.821 at the +5 second horizon. To put that in context: a random classifier guessing uniformly would get 0.33. A 'always predict CLEAN' model would get about 0.31. Our model achieves 0.821. In absolute terms, that means 82 out of every 100 predictions about signal quality are correct."

> "The most important single number is DEGRADED Recall = 0.847. In safety systems, recall on the dangerous class is what matters — it tells you 'of all the times GPS was actually about to fail, how often did we warn?' The answer is: 84.7% of the time. We miss only 15% of real degradation events."

---

## Slides 15: DEGRADED Recall

> "To be concrete about what this means in practice: in our validation drives, there were a certain number of GNSS degradation events. SENTINEL caught 84.7% of them before they became position errors. The 15.3% it missed — those are the cases where the GPS degradation appeared very suddenly with no advance features, or where the satellite geometry changed too fast to predict. Those are the hard cases. The 84.7% it caught are cases where the filter was already protected when the bad GPS arrived."

---

## Slides 16–17: Ablation (XGBoost vs DL)

> "We compared against XGBoost — a classical machine learning method that works extremely well on structured data like ours. In-domain (Hong Kong), XGBoost actually achieves 0.919 Macro-F1 — higher than our 0.821. That is an honest result, and we report it."

> "The reason we use the deep learning model despite XGBoost winning in-domain: cross-city generalization. When we move from Hong Kong to Tokyo — a city the model has never seen, with a different building geometry, different satellite visibility, and a different GPS receiver — XGBoost degrades severely while the Transformer-LSTM model maintains its performance. That is the cross-city slide."

---

## Slide 18–19: Cross-City Generalisation

> "This is the key result. We trained in Hong Kong. We test in Tokyo. The model has never seen Tokyo data — different city, different buildings, different satellite constellations, different receiver hardware (u-blox vs. Leica)."

> "SENTINEL still identifies 75% of DEGRADED episodes in Tokyo that were severe enough to cause position errors. The Random Forest drops to 15% — it essentially fails in a new city. That 5× gap in cross-city DEGRADED detection is the reason SENTINEL works as a real system and not just a lab benchmark."

> "The real-life implication: you build this system once, in one city, and deploy it globally. You do not need to retrain it every time you enter a new urban environment."

---

## Slide 23–26: EKF Section

### Opening the EKF section
> "Now we get to what the prediction is actually for. Predicting that GPS is about to fail is only useful if someone acts on that prediction. That is the EKF's job."

> "The Extended Kalman Filter has been used in aviation and aerospace since the 1960s — it is the core algorithm behind NASA Apollo navigation and modern aircraft autopilots. We use it for urban car navigation."

> "The filter's most important parameter is **R** — how much it trusts the GPS reading. Small R: 'I trust GPS, follow it closely.' Large R: 'I am sceptical, stay close to my own calculation.'"

> "**Fixed-R**: R never changes. The filter is equally trusting of GPS whether the signal is clean or dirty."

> "**SENTINEL Adaptive-R**: R changes every second based on SENTINEL's prediction. When P(DEGRADED) is high, R inflates — the filter starts trusting its own motion model more, and GPS less. When P(DEGRADED) drops back to zero, R returns to its baseline and GPS is trusted fully again."

### Kalman Gain intuition
> "The Kalman Gain K tells the filter how to split trust between its prediction and the measurement. Think of it as a confidence dial: K=1 means 'believe GPS completely, ignore my prediction'; K=0 means 'ignore GPS completely, trust my dead-reckoning.' SENTINEL pushing R up is the same as pushing K toward zero — we are turning down GPS trust before the bad measurement arrives."

### Predict → Update cycle
> "Every tenth of a second, the filter does two things: Predict — it integrates the IMU to project forward in time. Update — when GPS arrives, it blends the GPS fix with the prediction based on the Kalman gain. SENTINEL's job is to ensure the Update step uses the right gain — not too trusting during a bad GPS epoch, not too sceptical during a good one."

---

## Slide 27–28: Real Tokyo EKF Results

> "On real Shinjuku data with a Trimble dual-frequency receiver — the best commercial GPS you can buy for a car — raw GPS during blocked segments gives 47.4 metres average error. That is the starting point. After running through our 9-state EKF with wheel odometry, NHC, and ZUPT aiding: 24.3 metres. A 48.8% improvement. Nearly cutting the error in half, in the worst parts of Tokyo's urban canyon."

> "To be concrete: 47 metres of error means the car thinks it is on the pavement when it is in the middle of the road. 24 metres means the car knows it is on the road but is uncertain about which lane. The RMSE bar chart (fig07) shows this across all three scenarios and methods."

### When asked: "But your EKF is worse than raw GPS on Odaiba"
> "Correct observation. Odaiba is a waterfront district — more open sky, random (not persistent) GPS errors. In that environment, our EKF occasionally over-corrects by trusting its motion model too much after incorporating a single bad GPS fix. The Student-t Particle Filter handles Odaiba best (+40.1%) because it assigns lower probability weight to outlier GPS measurements without the full incorporation the EKF does. This tells us no single fusion method dominates every environment — which is itself a valuable insight about the diversity of urban navigation challenges."

---

## Slide 29: When Adaptive-R Wins (Severity Sweep)

> "This graph answers a critical question: under what conditions is adaptive-R actually better than fixed-R?"

> "The horizontal axis is multipath bias — how wrong GPS is during blocked segments. The vertical axis is RMSE during those blocked segments."

> "At low-to-moderate bias (5–60 m): our wheel odometry + NHC + ZUPT aiding is so effective that fixed-R actually wins. The aiding handles the short outage better than inflating R does. Both strategies are competitive."

> "At high bias (100 m — deep canyons, tunnels, heavily reflective buildings): fixed-R tries to fuse a GPS fix that is 100 metres wrong. The Kalman gain pulls the estimate significantly off-track. Adaptive-R inflates R to 10,000 m², effectively dead-reckoning on IMU + wheels, and achieves 30.4 m vs. 36.0 m for fixed-R — a 15.6% improvement. The crossover is in the 80–100 m bias range."

> "The message: for routine urban driving, our system is robust in either mode. For the most extreme environments — tunnels and deep canyons — SENTINEL's prediction and adaptive-R provide clear additional benefit."

---

## Slides 30, 33: Dashboard

> "This is the operational system — a real-time web dashboard built with FastAPI backend and Next.js frontend. It runs entirely locally on the vehicle's computer."

> "The map shows three things simultaneously: the raw GPS trace in grey, the SENTINEL-fused EKF trajectory in blue, and ground truth when available in black. The alarm panel on the right shows the current P(DEGRADED) for each horizon. The sensor fusion panel shows the EKF covariance ellipse — a visual representation of how uncertain the filter is about position at this moment."

> "In a real deployment, an autonomous vehicle controller subscribes to this feed via WebSocket and receives updated position estimates and alarm states at 10 Hz. The dashboard is the human-facing interface; the API is the machine-facing interface."

---

## Slide 34–35: Novelty — Proactive vs. Reactive

> "Let me be very specific about what is new here. Reactive systems — including commercial GPS units, Apple Maps, Google Maps — detect degradation by checking 'is my GPS reading accurate right now?' That requires looking at the current fix and comparing it to expected behaviour. But to detect something going wrong, it has to already be going wrong."

> "Our system is proactive. It looks at a 30-second window of satellite features — signal strengths, geometry quality, Doppler trends, carrier phase continuity — and says 'based on these patterns, the signal will become unreliable 5 seconds from now.' The EKF is already protected when the bad measurement arrives. The first bad GPS epoch sees a filter that is already dead-reckoning, not a filter that is about to snap to the wrong position."

> "The analogy: a weather forecaster is proactive — they tell you tomorrow's weather today. A reactive 'system' would be a window — it tells you it is raining by getting wet. SENTINEL is the forecaster."

---

## Slide 38: Deliverables / Papers

> "Three papers are in preparation from this work. Paper A is the core classification paper — SENTINEL's multi-horizon prediction, ablation, and cross-city generalization. Paper B is the EKF integration paper — how the prediction is wired into the filter and what improvement it achieves. Paper C is a position paper on methodology and deployment considerations."

---

## Slide 39: Thank You

> "To close: GNSS degradation is one of the last unsolved safety problems in urban autonomous navigation. Every system that relies on GPS — self-driving cars, drones, delivery robots, emergency services — is vulnerable to the same urban canyon problem. SENTINEL is our attempt at a principled, data-driven, deployable solution. Not just 'GPS failed, sound the alarm' — but 'GPS will fail in 5 seconds, and here is a smooth, accurate position estimate to carry us through.'"

> "Thank you. I am happy to take any questions."

---

## COMMON QUESTIONS AND SHORT ANSWERS

**"Your trajectories look messy / swirling. Is the filter diverging?"**
> "What you are seeing is the GPS multipath being partially corrected. GPS pulls the estimate one direction; IMU + odometry pull it back. The loops are small and short in the SENTINEL EKF trace. The RMSE numbers (24.3 m vs. 47.4 m raw) tell the quantitative story. The swirling in raw GPS is much larger — that is exactly the problem we are solving."

**"Adaptive-R is sometimes worse than fixed-R. Why?"**
> "At modest multipath (under 60 m), our wheel odometry + NHC + ZUPT aiding already handles the outage — inflating R unnecessarily discards valid GPS information. At extreme multipath (100 m), adaptive-R wins by 15.6%. Both are our system. The contribution is the architecture — SENTINEL's prediction — not claiming adaptive always beats fixed."

**"Why not just use more IMU states — 15, 18, or 21?"**
> "This is a 2D filter. Adding 3D IMU bias states without 3D motion and sensors adds unobservable states. The dominant error is GPS multipath (30–100 m), not IMU drift (1–3 m over 15 seconds). More states with consumer MEMS IMU causes divergence, not improvement. Our wheel odometry + NHC + ZUPT already constrains the IMU errors effectively."

**"XGBoost beats your deep learning model in-domain. Why use the harder model?"**
> "For cross-city deployment, which is the practical use case. XGBoost degrades to ~15% DEGRADED F1 in Tokyo; our Transformer-LSTM maintains 75%. In-domain performance is the laboratory; cross-city is the real world."

**"Why does temperature scaling matter?"**
> "P(DEGRADED) is used as a risk score. If the model is over-confident — outputs P=0.9 for things that are only 60% likely to be degraded — the EKF inflates R too aggressively and discards valid GPS. Calibration ensures the probability means what it says, making the EKF threshold interpretable."

**"How would this work in a real AV?"**
> "The SENTINEL model runs at 10 Hz, processing 30-second GNSS feature windows. The EKF receives P(DEGRADED) via the same message bus as IMU and wheel speed. Inference latency is 0.039 ms — 25× faster than needed for real-time operation. The dashboard WebSocket API serves position, alarms, and covariance to the vehicle controller at 10 Hz."

**"What happens if SENTINEL makes a false positive — predicts degradation when GPS is fine?"**
> "The filter inflates R for one second and relies more on dead-reckoning. The IMU + wheel odometry + NHC keep the estimate stable during this brief over-protection. When P drops back to zero, the filter immediately resumes trusting GPS. The cost of a false positive is a 1-second dead-reckoning period with ~1–3 m drift — much less harmful than incorrectly trusting a 100-metre biased GPS fix."

---

## SLIDE REMOVAL GUIDE

Remove before tomorrow's presentation:
| Slide | Title | Why remove |
|-------|-------|-----------|
| 21 | Interpretability — Attention & Feature Saliency | Technical detail; handle in Q&A if asked |
| 22 | Temperature Scaling | Can be explained in one sentence verbally |
| 31 | Dashboard screenshot (duplicate) | Redundant with slides 30 and 33 |
| 32 | Dashboard screenshot (duplicate) | Redundant with slides 30 and 33 |

Slides 3 (Table of Contents) can be kept if time allows; remove if tight.

**Result: 40 → 36 slides.**
