# SENTINEL-GNSS — Team Update & Decision Needed

**Date:** May 27, 2026

---

### What the numbers mean (quickly)

Our model predicts GNSS signal quality **5, 15, and 30 seconds ahead** into one of three states:

- **CLEAN** — signal is fine
- **WARNING** — signal is starting to degrade, act soon
- **DEGRADED** — signal is lost or unreliable

We measure performance using **F1-score** (0 = useless, 1 = perfect).

---

## Current Results

| Class    | F1 Score | Status                    |
| -------- | -------- | ------------------------- |
| CLEAN    | 0.91     | ✅ Excellent              |
| WARNING  | **0.85** | ✅ Strong                 |
| DEGRADED | 0.31     | ⚠️ Weak — needs attention |

---

## The DEGRADED Problem — What It Is Exactly

To be precise, the issue is **not** that the model has no DEGRADED training data.

Here is the actual breakdown:

| Data Split     | DEGRADED Windows                           |
| -------------- | ------------------------------------------ |
| Training set   | **11,996** real + 37,295 synthetic (SMOTE) |
| Validation set | **917**                                    |
| **Test set**   | **55** ← the problem                       |

The 55 is only in the **test set** — the final evaluation the paper reports on.

Why so few? By design. Our test set is restricted to **Beihang campus supervisor vehicle sessions only**, to prove the model generalises across cities (trained on Hong Kong, tested on Beihang). Those campus sessions naturally have very few complete signal-loss events.

There is a second issue on top of the small count: the **55 Beihang DEGRADED windows look physically different** from our training DEGRADED data. Training DEGRADED mostly came from Hong Kong urban canyon routes — gradual satellite occlusion as buildings block the sky. Beihang campus DEGRADED tends to be more sudden — walking behind a building and losing signal abruptly. The model learned HK canyon physics well but that does not transfer perfectly to Beihang campus blockage. This is why DEGRADED F1 is 0.31 despite having almost 12,000 training examples.

**In short:**

- We have enough DEGRADED training data ✅
- We do NOT have enough DEGRADED test data ❌
- The test DEGRADED data is from a different physical environment than training ❌

---

## How Collecting More Data Would Help

If we collect **new Beihang tunnel/blockage sessions after freezing the model**:

- Model stays unchanged — this is purely for testing, not retraining
- We add Beihang-specific DEGRADED data to the test set
- Test DEGRADED goes from **55 → ~150+ windows** (10 round trips through a tunnel)
- Our uncertainty on DEGRADED F1 drops from **±10%** to **±5%**
- We can also feed some of the approach/transition data into training next run to close the HK-Beihang physics gap

The collection procedure is the same as our previous Scenario A–E field work:

- Cart + Septentrio, same setup as before
- Walk toward tunnel entrance (start ~50m away)
- Enter tunnel until no satellites visible
- U-turn inside, walk back out
- Return to start, repeat
- **10 round trips, ~1 hour total, save 10 separate files**

---

## The Decision

We have two options. Both are defensible for the paper.

---

### Option A — Go Out Tomorrow Morning (10am)

Collect 1 hour of dedicated Beihang blockage data.

**What we gain:**

- Stronger DEGRADED evaluation (F1 confidence interval halved)
- Beihang-specific approach physics added to future training
- Cleaner paper narrative: "we validated with a dedicated post-training test set"

---

### Option B — Submit With Current Numbers

Skip collection. Write the paper around what we already have.

**What this looks like in the paper:**

> _"WARNING prediction F1 = 0.85 at 5 seconds ahead — the primary actionable signal for autonomous navigation. DEGRADED F1 = 0.31 (test n=55, CI ±0.10) — limited by the small Beihang campus test set and acknowledged as future work."_

**What we gain:**

- The WARNING result (0.85) is already strong and publishable

**What we accept:**

- DEGRADED result reported with wide confidence interval
- Reviewers may ask for more test data (we disclose this proactively)

---
