# SENTINEL-GNSS — Team Update & Decision Needed
**Date:** May 27, 2026

---

## Where We Stand After Run 12

### What the numbers mean (quickly)

Our model predicts GNSS signal quality **5, 15, and 30 seconds ahead** into one of three states:
- **CLEAN** — signal is fine
- **WARNING** — signal is starting to degrade, act soon
- **DEGRADED** — signal is lost or unreliable

We measure performance using **F1-score** (0 = useless, 1 = perfect).

---

## Current Results

| Class | F1 Score | Status |
|-------|----------|--------|
| CLEAN | 0.91 | ✅ Excellent |
| WARNING | **0.85** | ✅ Strong — publishable |
| DEGRADED | 0.31 | ⚠️ Weak — needs attention |

**Overall model (MacroF1 at +5s): 0.70** — improved from 0.69 in the previous run.

Val performance jumped significantly: **0.86** (was 0.78). The model is genuinely learning better.

---

## The DEGRADED Problem — What It Is Exactly

To be precise, the issue is **not** that the model has no DEGRADED training data.

Here is the actual breakdown:

| Data Split | DEGRADED Windows |
|-----------|-----------------|
| Training set | **11,996** real + 37,295 synthetic (SMOTE) |
| Validation set | **917** |
| **Test set** | **55** ← the problem |

The 55 is only in the **test set** — the final evaluation the paper reports on.

Why so few? By design. Our test set is restricted to **Beijing campus supervisor vehicle sessions only**, to prove the model generalises across cities (trained on Hong Kong, tested on Beijing). Those campus sessions naturally have very few complete signal-loss events.

There is a second issue on top of the small count: the **55 Beijing DEGRADED windows look physically different** from our training DEGRADED data. Training DEGRADED mostly came from Hong Kong urban canyon routes — gradual satellite occlusion as buildings block the sky. Beijing campus DEGRADED tends to be more sudden — walking behind a building and losing signal abruptly. The model learned HK canyon physics well but that does not transfer perfectly to Beijing campus blockage. This is why DEGRADED F1 is 0.31 despite having almost 12,000 training examples.

**In short:**
- We have enough DEGRADED training data ✅
- We do NOT have enough DEGRADED test data ❌
- The test DEGRADED data is from a different physical environment than training ❌

---

## How Collecting More Data Would Help

If we collect **new Beijing tunnel/blockage sessions after freezing the model**:

- Model stays unchanged — this is purely for testing, not retraining
- We add Beijing-specific DEGRADED data to the test set
- Test DEGRADED goes from **55 → ~150+ windows** (10 round trips through a tunnel)
- Our uncertainty on DEGRADED F1 drops from **±10%** to **±5%**
- We can also feed some of the approach/transition data into training next run to close the HK-Beijing physics gap

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

Collect 1 hour of dedicated Beijing blockage data.

**What we gain:**
- Stronger DEGRADED evaluation (F1 confidence interval halved)
- Beijing-specific approach physics added to future training
- Cleaner paper narrative: "we validated with a dedicated post-training test set"

**What it costs:**
- One morning (roughly 10am–12pm including setup and travel)

---

### Option B — Submit With Current Numbers

Skip collection. Write the paper around what we already have.

**What this looks like in the paper:**
> *"WARNING prediction F1 = 0.85 at 5 seconds ahead — the primary actionable signal for autonomous navigation. DEGRADED F1 = 0.31 (test n=55, CI ±0.10) — limited by the small Beijing campus test set and acknowledged as future work."*

**What we gain:**
- Save the morning, focus entirely on writing
- The WARNING result (0.85) is already strong and publishable

**What we accept:**
- DEGRADED result reported with wide confidence interval
- Reviewers may ask for more test data (we disclose this proactively)

---

## My Recommendation

**Option A if we can spare the morning. Option B if time is truly critical.**

The WARNING F1 = 0.85 is the headline result and it stands on its own. But one morning of collection could meaningfully strengthen the weakest part of the evaluation and reduce reviewer pushback.

**What do you all think? Can we do tomorrow morning?**

---

*For technical questions about the numbers, see `docs/NEXT_STEPS.md` and `docs/PAPER_TOPICS.md`.*
