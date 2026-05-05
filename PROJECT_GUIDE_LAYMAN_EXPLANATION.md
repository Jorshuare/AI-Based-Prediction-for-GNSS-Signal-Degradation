# SENTINEL-GNSS MASTER FIELD GUIDE

This is the single root guide for the project. It combines the previous app guide, field checklist, route planning notes, layman explanation, dataset combination notes, and the latest phone A plus phone B route analysis for today's real-equipment collection.

## Project Goal

The project goal is to predict GNSS degradation 5 to 30 seconds before failure so an autonomous platform can switch to backup localization safely.

The five target scenarios are:

| Scenario | Meaning              | Desired behavior                                                  |
| -------- | -------------------- | ----------------------------------------------------------------- |
| A        | Instant blockage     | Fast transition from usable signal to very weak or no signal      |
| B        | Urban canyon         | Strong multipath and gradual degradation between tall buildings   |
| C        | Partial blockage     | Stable but reduced signal under trees, overhang, or partial cover |
| D        | Open sky             | Clean reference baseline with strongest signal and best geometry  |
| E        | Approaching blockage | Smooth degradation while moving toward a blocking structure       |

## What We Have From Route Testing

### Phone A Summary

Phone A gave the strongest instant-blockage evidence and still provides the best fallback for severe degradation.

| Source              | Best use                     | Notes                                                          |
| ------------------- | ---------------------------- | -------------------------------------------------------------- |
| Phone A Location #3 | Scenario A primary candidate | Short but sharp transition, best for clean instant blockage    |
| Phone A Location #4 | Scenario E backup            | Long degrading route, useful if phone B route is blocked today |
| Phone A Location #6 | Scenario A backup            | Repeated blockage and recovery cycles                          |
| Phone A Location #7 | Severe mixed route backup    | Strong A plus E behavior, highest variance                     |

Phone A charts remain in `route_planning/analysis/`.

### Phone B Summary

Phone B adds labeled routes and gives the clearest candidates for Scenarios B, C, and E.

| Phone B File             | Duration | Avg C/N0   | Best interpretation                                                   |
| ------------------------ | -------- | ---------- | --------------------------------------------------------------------- |
| Approaching blockage     | 377s     | 25.4 dB-Hz | Strong Scenario E                                                     |
| Open Scenario            | 300s     | 33.1 dB-Hz | Best current Scenario D candidate, but still needs field verification |
| Partial Blockage (Trees) | 326s     | 30.1 dB-Hz | Strong Scenario C                                                     |
| Urban Canyon             | 392s     | 27.0 dB-Hz | Strong Scenario B                                                     |

### Combined Coverage Decision

Using both phones together, the best route choices for today are:

| Scenario | Primary route for today                    | Backup route                                                      |
| -------- | ------------------------------------------ | ----------------------------------------------------------------- |
| A        | Phone A Location #3 instant blockage route | Phone A Location #6                                               |
| B        | Phone B Urban Canyon route                 | Phone A Location #4                                               |
| C        | Phone B Partial Blockage (Trees) route     | Find nearby tree canopy or overhang if occupied                   |
| D        | Phone B Open Scenario route                | Any larger sports field or open plaza with verified strong signal |
| E        | Phone B Approaching blockage route         | Phone A Location #4 or #7                                         |

## Today's Equipment Recommendation

Use the professional receiver as the main logger. Use one phone with GNSS Status for live signal sanity checking and one phone with GNSS Logger for backup trace logging.

Minimum field stack:

1. Professional GNSS receiver and antenna
2. Power bank and spare cable
3. One phone running GNSS Status
4. One phone running GNSS Logger
5. Notebook or shared note sheet for route start and stop times
6. Camera or phone photos of each environment

If you are running rover plus base:

1. Put the base in the cleanest open-sky location available first
2. Record antenna height exactly
3. Start base logging before any rover route begins
4. Keep base running for the full session

If you are running only one receiver:

1. Still begin in open sky for a clean baseline segment
2. Log raw data continuously through each route
3. Note exact time boundaries between scenarios

## Step-by-Step Field Procedure

<div style="color:red">

### Before Leaving

1. Charge the receiver, both phones, and power bank to full.
2. Prepare a route sheet with five rows: D, E, C, A, B.
3. Confirm enough storage exists on the receiver and both phones.
4. Set one phone to GNSS Status and one phone to GNSS Logger.
5. If using base plus rover, pack tripod, mount, antenna, and note antenna height tools.
6. Before moving to the first scenario, start a 2-minute static open-sky receiver log for equipment sanity checking.

### Collection Order For Today

Use this order unless weather, crowds, or access constraints force a change:

1. Scenario D first
2. Scenario E second
3. Scenario C third
4. Scenario A fourth
5. Scenario B last

This order is best because it starts with the clean baseline, then moves into gradual degradation, then partial cover, then sharp blockage, and finishes in the densest built area.

</div>

## Exact Route Plan For The 5 Scenarios

<div style="color:red">

### Scenario D: Open Sky

Primary route: `route_planning/Phone_b/20260430-112247 - OPEN Scenario D.gpx`

Execution:

1. Go to the most open field, parking area, or plaza you have already used for the phone B open scenario.
2. Place the receiver in the center of the open area.
3. Stand still for 10 minutes minimum.
4. Check GNSS Status after 30 seconds and again at 5 minutes.
5. If average C/N0 is below about 38 dB-Hz or the sky view is clearly blocked, move immediately to a more open location and repeat.

Use criteria:

1. This route is acceptable only if the real receiver gives your cleanest baseline of the day.
2. If it does not, do not force this route; move to a larger open field and recollect Scenario D there.

### Scenario E: Approaching Blockage

Primary route: `route_planning/Phone_b/Aproaching_blockage_gnss_log_2026_04_30_12_16_14.txt`

Execution:

1. Start 80 to 100 meters away from the target building or blocking structure.
2. Hold the receiver still for 60 seconds at the starting point.
3. Walk directly toward the structure at a slow and steady speed.
4. Do one full pass from open sky into degraded conditions over about 2 to 3 minutes.
5. Repeat the same pass a minimum of 3 times. 3 is the minimum acceptable; add a 4th if any pass was interrupted.
6. Keep headings and walking speed consistent between repeats.
7. **Minimum total time on this site: 15 minutes.** If you finish 3 clean passes in under 10 minutes, wait 2 minutes then do a 4th.

Use criteria:

1. You want a smooth downward trend, not a sudden collapse.
2. If the trend is too jumpy, widen the starting distance and try again.

### Scenario C: Partial Blockage

Primary route: `route_planning/Phone_b/Partial_Blockage_(Trees)_gnss_log_2026_04_30_12_45_19.txt`

Execution:

1. Go to the tree canopy or partial-cover area used in phone B.
2. Put the receiver under the canopy but not fully enclosed.
3. Record 10 minutes stationary.
4. If possible, do one short 20 to 30 meter walk within the same partially covered zone.
5. Stay in the zone where the signal is reduced but still stable.

Use criteria:

1. This is good only if signal stays consistently weaker than open sky but does not collapse fully.
2. If signal keeps dropping toward full loss, it is turning into Scenario A or E and should not be used as Scenario C.

### Scenario A: Instant Blockage

Primary route: Phone A Location #3

Backup route: Phone A Location #6

Execution:

1. Start 15 to 20 meters before the blockage boundary, for example an underground entrance, basement entrance, or hard roof transition.
2. Record 60 seconds in the clear area first.
3. Walk directly across the boundary into the blocked area.
4. Hold for 10 to 20 seconds inside.
5. Walk back out.
6. Repeat 5 to 8 times so you capture multiple clean transitions.

Use criteria:

1. This route is good only if the transition is fast and obvious.
2. If the transition is gradual instead of sharp, switch to the backup route.

### Scenario B: Urban Canyon

Primary route: `route_planning/Phone_b/Urban_Canyon_gnss_log_2026_04_30_13_10_10.txt`

Execution:

1. Start at one end of the street or corridor between tall buildings.
2. Hold the receiver still for 60 seconds before walking.
3. Walk 120 to 150 meters through the canyon section.
4. Keep a steady pace and do not stop unless safety requires it.
5. At the far end, hold for 30 seconds.
6. Walk back along the same path.
7. Target 3 loops. **2 loops is the minimum acceptable — do not stop at 1.** If time is critically short, do 2 full loops rather than 3 partial ones.

Use criteria:

1. This should show degraded and noisy performance with continued movement.
2. If the route feels too open, move deeper into the denser building section.

</div>

## What To Record At Every Scenario

At every route, collect the following operational notes:

1. Start time and stop time
2. File name on the receiver
3. If applicable, base station file name
4. Antenna height
5. Weather and crowd conditions
6. Whether the route matched the expected scenario behavior
7. Any interruptions, stops, or access issues

Also capture:

1. One wide photo of the environment
2. One photo or screenshot of GNSS Status at the start
3. One photo or screenshot near the strongest degradation point

## Quick Decision Rules In The Field

Use these rules so you do not waste time collecting unusable runs.

| Scenario | Accept if                                                 | Reject if                                              |
| -------- | --------------------------------------------------------- | ------------------------------------------------------ |
| A        | Signal drops sharply across a boundary                    | Degradation is slow and continuous                     |
| B        | Buildings clearly create noisy degraded corridor behavior | Route is too open and stable                           |
| C        | Signal is reduced but stable                              | Signal collapses or varies wildly                      |
| D        | This is the cleanest, most open baseline of the day       | C/N0 remains clearly mediocre relative to other routes |
| E        | Signal degrades smoothly while approaching                | Drop is instant or too erratic                         |

## Recommended Session Timeline

**Can you finish by 1:00 PM today? Yes, but only if you start collection by 10:30 AM.** The minimum field session with no repeats is about 2 hours 30 minutes including travel between sites. If you want even one repeat pass on the best scenario, start by 10:00 AM.

### Timed Plan — Start 10:30 AM, Finish 1:00 PM

| Clock time | Duration | Step                                                         |
| ---------- | -------- | ------------------------------------------------------------ |
| 10:30      | 15 min   | Equipment setup and mandatory open-sky sanity check          |
| 10:45      | 15 min   | **Scenario D collection** — 10 min stationary minimum        |
| 11:00      | 7 min    | Travel to Scenario E site                                    |
| 11:07      | 25 min   | **Scenario E collection** — 3 full passes minimum            |
| 11:32      | 7 min    | Travel to Scenario C site                                    |
| 11:39      | 18 min   | **Scenario C collection** — 10 min stationary + 1 short walk |
| 11:57      | 7 min    | Travel to Scenario A site                                    |
| 12:04      | 22 min   | **Scenario A collection** — 5 transitions minimum, 8 target  |
| 12:26      | 7 min    | Travel to Scenario B site                                    |
| 12:33      | 20 min   | **Scenario B collection** — 2 loops minimum, 3 target        |
| 12:53      | 7 min    | Wrap-up, notes, backup check                                 |
| **13:00**  | —        | **Done — right at the deadline, no buffer for repeats**      |

If you start at 10:00 AM instead, the same plan completes at 12:30 PM and you have 30 minutes to repeat Scenario A or E.

### Minimum Passes and Duration Per Scenario

| Scenario | Minimum time on site       | Minimum passes               | Retry the full set if                                                       |
| -------- | -------------------------- | ---------------------------- | --------------------------------------------------------------------------- |
| D        | 10 min stationary          | 1 static hold                | C/N0 stays below 35 dB-Hz — move location and restart                       |
| E        | 3 passes × ~3 min          | 3 walking passes             | Any pass was heavily interrupted — do the full 3 again                      |
| C        | 10 min stationary + 1 walk | 1 stationary + 1 walk        | Signal collapses rather than staying reduced — find better partial cover    |
| A        | 5 transitions, 8 target    | 5 cross-boundary transitions | First 2 transitions look gradual rather than sharp — switch to backup route |
| B        | 2 full loops, 3 target     | 2 corridor loops             | First loop was interrupted — start over from the same entry point           |

### Best Repeat Priorities If Time Allows

1. Scenario A — transition sharpness is critical for model training
2. Scenario E — need enough gradual slope samples
3. Scenario B — more loops adds diversity in the corridor

## App Use During Real Collection

Use the apps only as support tools during the real receiver session.

| App                | Use today                                              | Do not use it for           |
| ------------------ | ------------------------------------------------------ | --------------------------- |
| GNSS Status        | Real-time check of C/N0, satellite count, sky blockage | Final training data         |
| GNSS Logger        | Backup phone trace, timestamps, rough cross-check      | High-precision ground truth |
| Geo++ RINEX Logger | Optional if you want a phone-side raw backup           | Replacing the real receiver |

Minimum app workflow:

1. GNSS Status open before each route starts
2. Screenshot at route start
3. Screenshot at strongest degradation point
4. GNSS Logger running during at least one representative pass per scenario

## Public Dataset Notes For Later

These notes replace the older root dataset note and correct the earlier city list.

### UrbanNav

UrbanNav currently provides Hong Kong and Tokyo data, not Beijing and Taipei.

Recommended downloads later:

1. `UrbanNav-HK-Tunnel-1` for complete signal loss patterns
2. `UrbanNav-HK-Medium-Urban-1` for balanced urban canyon data
3. `UrbanNav-TK-20181219` for cross-country generalization with a smaller download size

### KAIST

Recommended request list instead of downloading everything:

1. `Sample_Data`
2. `Campus00`
3. `Urban07`
4. `Urban08`
5. `Urban21`
6. `Urban22`

## Processing Plan After Collection

### What the Septentrio Receiver Gives You

When you stop recording, the receiver has written these files to its SD card or internal storage:

| File            | What it is                                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `SEPT????.sbf`  | Septentrio Binary Format — the raw binary recording of everything the receiver heard                                                |
| `SEPT????.25O`  | RINEX 3 Observation file — the measurement log in open standard format (pseudorange + carrier phase + C/N0 per satellite per epoch) |
| `SEPT????.25N`  | RINEX Navigation — GPS satellite orbital parameters                                                                                 |
| `SEPT????.25G`  | RINEX Navigation — GLONASS satellite orbital parameters                                                                             |
| `SEPT????.25P`  | RINEX Navigation — mixed constellation orbital parameters                                                                           |
| `log_0000.nmea` | NMEA 0183 stream — human-readable position sentences ($GPGGA, $GPRMC etc.)                                                          |

The `.25O` file is the most important one. Everything else supports it.

### What RTKLIB Does With These Files

RTKLIB is a free open-source GNSS post-processing toolkit. It takes the RINEX files and computes a much more accurate position solution than what the receiver reported live.

**Input:**

- Rover `.25O` — the moving receiver that collected the scenario
- Base `.25O` — the stationary receiver left in open sky (if you ran rover + base mode)
- Navigation files `.25N`, `.25G`, `.25P`

**Output: a `.pos` file** — plain text, one line per second, looks like this:

```
%  GPST               latitude(deg)  longitude(deg)  height(m)  Q  ns  sdn(m)  sde(m)  sdu(m)  age  ratio
2025/05/05 09:12:00  39.921234      116.402987       52.341     1  14  0.002   0.002   0.004   1.0  5.2
2025/05/05 09:12:01  39.921256      116.402994       52.339     1  14  0.002   0.002   0.004   1.0  5.3
2025/05/05 09:12:15  39.921301      116.403010       52.302     2  11  0.042   0.038   0.091   1.2  2.1
2025/05/05 09:12:30  39.921399      116.403088       52.198     5   8  1.250   1.100   2.300   0.0  0.0
```

The `Q` column (quality) tells the whole story:

| Q   | Name      | Accuracy | What it means physically                                             |
| --- | --------- | -------- | -------------------------------------------------------------------- |
| 1   | Fixed RTK | 1–3 cm   | Full satellite geometry, no multipath, ambiguity resolved            |
| 2   | Float RTK | 10–30 cm | Partial blockage or moderate multipath, ambiguity not fully resolved |
| 3   | SBAS      | ~1 m     | Satellite-based augmentation only                                    |
| 4   | DGPS      | 1–3 m    | Differential correction without carrier phase                        |
| 5   | Single    | 3–10 m   | No correction, raw pseudorange only — signal significantly degraded  |

A transition from Q=1 through Q=2 to Q=5 is exactly the degradation event the model must learn to predict. The `sdn`, `sde`, `sdu` columns (standard deviation north, east, up in metres) and the `ns` column (satellite count) are the numerical features that lead the transition.

### How to Run RTKLIB on Our Data

**Option A — GUI (easiest for first use):**

1. Open `C:\Program Files\RTKLIB\bin\rtkpost.exe`
2. Set RINEX OBS (rover) to your `.25O` file
3. Set RINEX OBS (base) to base `.25O` if available
4. Set RINEX NAV to `.25N` and `.25G`
5. Set Output to `data/processed/our_collection/scenario_A_solution.pos`
6. Options → Positioning: Kinematic | L1+L2 | Ionosphere-free LC | Saastamoinen troposphere
7. Click Execute

**Option B — Automated pipeline (preferred for batch processing):**

```powershell
# After placing .25O files under data/raw/our_collection/scenario_A/ etc.:
python src/processing/our_collection_processor.py --scenario A
python src/processing/our_collection_processor.py --all
```

**Option C — Direct command line:**

```powershell
& "C:\Program Files\RTKLIB\bin\rnx2rtkp.exe" -p 2 -o solution.pos nav.25N nav.25G rover.25O base.25O
# -p 2 = kinematic mode (moving receiver)
# Omit base.25O if no base station was used
```

### Complete Post-Collection Pipeline

```
Step 1 — Copy files immediately
  Copy all receiver files to data/raw/our_collection/scenario_A/ etc.
  Back up to a second location (external drive or cloud).

Step 2 — Run RTKLIB
  python src/processing/our_collection_processor.py --all
  → Output: data/processed/our_collection/scenario_A_solution.pos etc.

Step 3 — Extract features from .pos files
  python src/features/feature_extractor.py \
    --input data/processed/our_collection/scenario_A_solution.pos \
    --output data/processed/our_collection/scenario_A.features.csv \
    --source our_collection_A
  → Output: CSV with 35 features per epoch

Step 4 — Label the features
  python src/labeling/labeler.py
  → Output: data/labelled/scenario_A_labelled.csv

Step 5 — Process public datasets (NCLT, Oxford, UrbanNav)
  python src/extraction/urbannav_extractor.py
  python src/processing/nclt_processor.py      # after downloading NCLT
  python src/processing/oxford_processor.py    # after downloading Oxford

Step 6 — Assemble final dataset with train/val/test split
  python src/features/dataset_assembler.py --split temporal
  → Output: data/labelled/ train.csv, val.csv, test.csv

Step 7 — Train the model
  See models/ and notebooks/ for model code.
```

**Critical rule for step 6:** Always use a time-based split, never random. GNSS data is a time series. Random shuffling leaks future data into training and will make the model look better than it really is. The split must go: past → train, near-future → val, far-future → test.

## Final Decision Summary For Today

The strongest combined plan is:

1. Use phone B routes for Scenarios B, C, and E
2. Use phone A Location #3 for Scenario A, with Location #6 as backup
3. Use phone B open route for Scenario D only if the real receiver confirms it is your cleanest baseline
4. If the open route is still weak, relocate Scenario D to a larger sports field or open plaza and recollect

That gives you the best practical coverage today without relying on a single phone's reconnaissance alone.
