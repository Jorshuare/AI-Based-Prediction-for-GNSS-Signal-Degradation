# 🗺️ GNSS Route Planning & Testing Guide

## Before You Collect: Test Your 5 Scenarios Route Using Smartphone Apps

---

## 📱 **SMARTPHONE APPS FOR ROUTE TESTING (Pre-Collection)**

### **Tier 1: Essential Apps (Install These First)**

| App                    | Purpose                   | Gives You                                        | Download    |
| ---------------------- | ------------------------- | ------------------------------------------------ | ----------- |
| **GNSS Status**        | Real-time satellite info  | Sat count, signal strength (C/N0), sky plot      | Google Play |
| **GNSS Logger**        | Raw GPS data in CSV       | CSV with position, satellites, timestamps        | Google Play |
| **Geo++ RINEX Logger** | Professional RINEX format | RINEX observation files (need RTKLIB to process) | Google Play |

### **Tier 2: Supporting Apps (Helpful for Validation)**

| App                   | Purpose                 | Gives You                                       |
| --------------------- | ----------------------- | ----------------------------------------------- |
| **GPXLogger**         | Track route on map      | KML/GPX file showing your walking path          |
| **GPS Test**          | Detailed satellite data | Signal strength graph, satellite elevation plot |
| **Maps.me** (offline) | Navigation without data | Offline map to verify locations                 |

---

## 🎯 **IMPORTANT: Smartphone vs Professional Receiver**

### **Smartphone Testing (TODAY) - Good for Route Validation**

- ✅ Quick route scouting
- ✅ See satellite visibility patterns
- ✅ Verify signal degradation at each location
- ❌ **Lower accuracy** (5-10 meters typical)
- ❌ **Not suitable for training data** (too noisy)

### **Professional Receiver (ACTUAL DATA COLLECTION) - Required for Training**

- ✅ **High accuracy** (centimeter-level after RTKLIB processing)
- ✅ Suitable for AI model training
- ✅ Better signal tracking
- ❌ Requires manual setup at each location
- ❌ Takes longer to collect

**YOUR PLAN: Perfect!**

1. **Today (smartphone)**: Test routes, verify scenarios exist
2. **Later (professional receiver)**: Collect actual high-quality training data

---

## 📋 **INFORMATION TO COLLECT FOR EACH SCENARIO (Pre-Collection)**

### **Scenario D: Open Sky (Baseline) - COLLECT TODAY**

**Location**: Empty parking lot or sports field (away from buildings)

**What to Check with Smartphone Apps:**

```
GNSS Status:
✓ Number of satellites: Should be 8-12
✓ Signal strength (C/N0): Should be 40-50 dB-Hz
✓ Sky plot: Clear overhead, no obstacles
✓ Position dilution (DOP): Should be <2.5
✓ GPS status: "GPS OK" or similar

GNSS Logger (Export CSV):
✓ Record 5 minutes of data
✓ Check position consistency: All points should cluster
✓ Export and verify CSV readable
```

**Decision Point:**

- ❌ If sat count < 8 or signal < 35 dB-Hz → **WRONG LOCATION** (too many buildings)
- ✅ If sat count > 8 and signal > 40 dB-Hz → **GOOD LOCATION** for Scenario D

**Example "Open Sky" Locations at Beihang:**

- Empty parking lots
- Rooftop (if accessible)
- Sports field away from buildings
- Empty plaza/courtyard

---

### **Scenario A: Instant Blockage - COLLECT TODAY**

**Location**: Underground entrance to parking garage or building basement

**What to Check:**

```
GNSS Status (Standing outside before entering):
✓ Record satellite config: 10+ satellites, 40+ dB-Hz
✓ Take screenshot of sky plot

Then WALK INTO UNDERGROUND AREA:
✓ Watch as satellite count drops: 10 → 5 → 0
✓ Signal strength drops: 40 → 20 → 5 dB-Hz
✓ Should see GPS "signal lost" message
✓ Record video showing this transition

GNSS Logger:
✓ Start logging outside
✓ Walk inside
✓ Stop logging (once signal completely lost)
✓ Export CSV showing position freeze
```

**Decision Point:**

- ❌ If signal drops gradually → WRONG LOCATION (need instant blockage)
- ✅ If signal drops within 5-10 steps → **GOOD LOCATION** for Scenario A

**Example "Instant Blockage" Locations:**

- Underground parking entrance
- Basement door/entrance
- Covered bridge with sharp transition
- Building tunnel with overhead concrete

---

### **Scenario B: Urban Canyon - COLLECT TODAY**

**Location**: Street between tall buildings (Beihang campus)

**What to Check:**

```
GNSS Status (Start in open area):
✓ Initial: 10+ satellites, 40+ dB-Hz
✓ Take screenshot

WALK DOWN STREET BETWEEN BUILDINGS:
✓ Watch satellite count: 10 → 8 → 5 → 3
✓ Watch signal: 40 → 35 → 28 → 20 dB-Hz
✓ GRADUAL DEGRADATION (not instant)
✓ Sky plot shows satellites disappearing on sides
✓ Should see multipath effect (signal bouncing)

Measurement Timing:
✓ Spend 30-60 seconds between buildings
✓ Record GPS position as you walk
```

**Decision Point:**

- ❌ If signal stable at 35+ dB-Hz → NOT URBAN CANYON (too open)
- ❌ If signal drops instantly → WRONG LOCATION (that's Scenario A)
- ✅ If signal gradually drops from 40→20 over 30-60s → **GOOD LOCATION** for Scenario B

**Example "Urban Canyon" Locations at Beihang:**

- Streets between 10+ story buildings
- Academic building corridors (outdoor between buildings)
- Campus roads in dense building areas

---

### **Scenario C: Partial Blockage - COLLECT TODAY**

**Location**: Under tree canopy or covered structure (not fully enclosed)

**What to Check:**

```
GNSS Status (Positioning):
✓ Satellite count: 6-8 (some blocked, some visible)
✓ Signal strength: 30-38 dB-Hz (medium)
✓ Sky plot shows some directions blocked
✓ Solution still valid (GPS position updates)

Key Difference from Scenario B:
✓ Signal is STABLE (not continuously degrading)
✓ Part of sky blocked, part open
✓ GPS still works, just weaker
```

**Decision Point:**

- ❌ If signal < 25 dB-Hz → TOO DEGRADED (that's Scenario DEGRADED)
- ❌ If signal > 38 dB-Hz → TOO GOOD (that's Scenario CLEAN)
- ✅ If signal 30-38 dB-Hz AND 6-8 satellites → **GOOD LOCATION** for Scenario C

**Example "Partial Blockage" Locations:**

- Under tree canopy (dense leaves)
- Under covered bridge (semi-enclosed)
- Under building overhang
- Dense vegetation area

---

### **Scenario E: Approaching Blockage - COLLECT TODAY**

**Location**: Open area with building at distance (walk toward building)

**What to Check:**

```
STARTING POSITION (100m away from building):
✓ Position yourself in open area
✓ Check GNSS Status: 10+ satellites, 40+ dB-Hz
✓ Take initial screenshot

WALK TOWARD BUILDING (slow, take 2-3 minutes):
✓ Every 20m, check GNSS Status
✓ Watch gradual progression:
  - 100m away: 40 dB-Hz, 10 satellites
  - 75m away: 38 dB-Hz, 9 satellites
  - 50m away: 35 dB-Hz, 8 satellites
  - 25m away: 30 dB-Hz, 6 satellites
  - At building: 15 dB-Hz, 3 satellites

Timing:
✓ 2-3 minute walk showing continuous degradation
✓ NOT SUDDEN (that's Scenario A)
```

**Decision Point:**

- ❌ If signal stays flat → WRONG LOCATION
- ✅ If signal shows smooth degradation curve → **GOOD LOCATION** for Scenario E

**Example "Approaching Blockage" Locations:**

- Open plaza with tall buildings at edges
- Campus square walking toward building
- Open field walking toward tree line/buildings

---

## 📊 **SUMMARY: Pre-Collection Testing Checklist**

```
BEFORE YOU COLLECT DATA WITH THE RECEIVER:

Scenario D (Open Sky):
☐ Located empty parking lot / sports field
☐ GNSS Status shows 8+ satellites, 40+ dB-Hz
☐ Confirmed 5-minute stable GPS signal
☐ Export CSV from GNSS Logger - data looks good
☐ Ready for professional receiver collection

Scenario A (Instant Blockage):
☐ Found underground entrance with clear boundary
☐ Verified signal drops from 40→5 dB-Hz within 10 steps
☐ Confirmed GPS signal lost when inside
☐ Exit location identified for safe data collection
☐ Ready for professional receiver collection

Scenario B (Urban Canyon):
☐ Found street between buildings (minimum 4-story)
☐ Verified gradual signal degradation (40→20 dB-Hz over 30s)
☐ Satellite count drops from 10→3 visibly
☐ Measured walk distance (~50-100m)
☐ Ready for professional receiver collection

Scenario C (Partial Blockage):
☐ Found tree canopy / semi-enclosed area
☐ Verified stable signal 30-38 dB-Hz, 6-8 satellites
☐ GPS position still updates (not frozen)
☐ Can safely stand for 5 minutes
☐ Ready for professional receiver collection

Scenario E (Approaching Blockage):
☐ Found open area with building 100+ meters away
☐ Verified ability to walk slowly toward building
☐ Signal shows smooth degradation (not jumpy)
☐ Walking path safe and unobstructed
☐ Ready for professional receiver collection
```

---

## 🚀 **TODAY'S TESTING WORKFLOW (Smartphone Phase)**

### **Step 1: Install Apps (5 minutes)**

```
Google Play Store:
1. Download "GNSS Status" by Android Dev
2. Download "GNSS Logger" by Google Research
3. Download "Geo++ RINEX Logger" (optional, for future)
4. Download "GPXLogger" (for mapping route)
```

### **Step 2: Test Each Scenario (30-45 minutes total)**

**Time breakdown:**

- Scenario D (Open Sky): 5-10 min
- Scenario A (Instant Blockage): 5-10 min
- Scenario B (Urban Canyon): 10-15 min
- Scenario C (Partial Blockage): 5-10 min
- Scenario E (Approaching Blockage): 10-15 min

### **Step 3: For Each Scenario:**

```bash
# Open GNSS Status
→ Stand at location
→ Wait 30 seconds for GPS fix
→ Record screenshot of satellite info
→ Note down:
   - Number of satellites
   - Mean signal strength (C/N0)
   - PDOP value
   - GPS status (OK, Weak, No Fix, etc.)

# Open GNSS Logger
→ Hit "Start Recording"
→ Perform scenario action (walk, wait, enter building)
→ Hit "Stop Recording"
→ Email yourself the CSV file
→ Review CSV:
   - Check position changes (or freezing)
   - Check satellite count progression
   - Check accuracy values
```

### **Step 4: Evaluate & Document**

For each scenario, create notes:

```
SCENARIO D: Open Sky
Location: [Exact location on campus]
Coordinates: [GPS coordinates]
Satellite Info: 11 satellites, 42.5 dB-Hz mean, PDOP 2.1
Result: ✅ VALIDATED - Ready for collection
Best Time: [Morning/afternoon/whenever GPS is strongest]
Notes: Clearest GPS on campus, good for baseline

SCENARIO A: Instant Blockage
Location: [Building/parking garage entrance]
Transition: [Describe the boundary]
Signal Drop: 42 dB-Hz → 3 dB-Hz over [X meters]
Result: ✅ VALIDATED - Instant blockage confirmed
Best Time: [Suggest time]
Notes: Sharp transition visible in GNSS Status

... (repeat for B, C, E)
```

---

## ⚠️ **IMPORTANT DIFFERENCES: Smartphone vs Professional Receiver**

### **What Smartphone Apps Show (Real-Time)**

- ✅ Satellite visibility patterns (real)
- ✅ Signal strength trends (real)
- ✅ Position accuracy limits (real)
- ❌ Raw GPS measurements (not available)
- ❌ Carrier phase data (not available)
- ❌ True position error (you don't have reference)

### **What Professional Receiver Shows (RTKLIB Processing)**

- ✅ **Precise positions** (2-5cm after RTKLIB)
- ✅ Raw measurements (pseudorange, Doppler, carrier phase)
- ✅ RINEX format (processable by RTKLIB)
- ✅ True position error (vs reference station)
- ✅ Multipath indicators
- ✅ Integer ambiguity resolution (RTK)

**Bottom Line:**

- **Smartphone testing (today)**: Validates route validity ✓
- **Professional receiver (later)**: Provides actual training data ✓

---

## 📸 **DOCUMENTATION TEMPLATE: What to Take**

For each scenario location, capture:

### **Photos**

```
1. Wide view (showing geography)
2. Close-up of phone screen (GNSS Status)
3. View toward sky (to show obstacles)
4. Safety considerations (traffic, obstacles)
```

### **Data Files**

```
1. CSV from GNSS Logger (exported)
2. Screenshot of GNSS Status
3. Screenshot of sky plot (which satellites visible)
4. Route map from GPXLogger
```

### **Written Notes**

```
Date: [YYYY-MM-DD]
Time: [HH:MM]
Scenario: [A/B/C/D/E]
Location: [Exact location + coordinates]
Weather: [Sunny/Cloudy/Rainy]
GPS Signal Quality: [Good/Medium/Poor]
Satellite Count: [X satellites]
Mean C/N0: [X dB-Hz]
PDOP: [X]
Observations: [Any special notes]
Result: [Validated ✓ / Needs Adjustment ✗]
Recommended Time for Collection: [Morning/Afternoon/Evening]
```

---

## 📱 **APP-BY-APP GUIDE**

### **1. GNSS Status (Primary App)**

**How to Use:**

1. Open app
2. Wait 30 seconds for "GPS OK" status
3. Look at "C/N0" tab for signal strength
4. Look at "Sats" tab for satellite list
5. Look at "Sky" tab for where satellites are

**What Each Metric Means:**

| Metric                   | Good      | Warning     | Bad       |
| ------------------------ | --------- | ----------- | --------- |
| C/N0 (Signal Strength)   | >40 dB-Hz | 30-40 dB-Hz | <30 dB-Hz |
| Satellite Count          | 8+        | 5-8         | <5        |
| PDOP (Position Dilution) | <3        | 3-6         | >6        |
| Accuracy (Est.)          | <5m       | 5-15m       | >15m      |
| Status                   | "GPS OK"  | "GPS Weak"  | "No Fix"  |

**Screenshots to Take:**

- C/N0 list (showing signal per satellite)
- Sky plot (showing which satellites visible)
- Status summary (showing PDOP, accuracy, sat count)

---

### **2. GNSS Logger (Data Collection App)**

**How to Use:**

1. Open app
2. Press red "Start" button
3. Perform your scenario action
4. Press red "Stop" button
5. Go to saved files, select session
6. Email CSV to yourself

**CSV Columns You Get:**

```
UtcTimeInMs - timestamp
LatitudeDegrees - latitude
LongitudeDegrees - longitude
AltitudeMeters - altitude
HorizontalAccuracyMeters - position uncertainty
VerticalAccuracyMeters - altitude uncertainty
SpeedMps - speed
BearingDegrees - heading
NumSatellitesUsedInFix - number of satellites (KEY METRIC!)
Svid - satellite ID
TimeOffsetNs - receiver clock offset
State - measurement state
CN0DbHz - signal strength (C/N0) (KEY METRIC!)
```

**What to Look For:**

- `NumSatellitesUsedInFix`: Should decrease in degraded scenarios
- `CN0DbHz`: Should decrease in degraded scenarios
- `HorizontalAccuracyMeters`: Should increase (worse) as GPS degrades
- `Lat/Lon/Alt`: Position should freeze in blockage scenarios

---

### **3. Geo++ RINEX Logger (Optional, Professional)**

**How to Use:**

1. Open app
2. Press record button
3. Perform scenario
4. Stop recording
5. Files saved as RINEX format

**Note:** RINEX files need RTKLIB to process and extract positions. Not immediately useful for pre-collection validation, but good to have raw data.

---

## 🗺️ **MAPPING YOUR ROUTE: GPXLogger**

**How to Use:**

1. Open GPXLogger
2. Press "Start Recording"
3. Walk your scenario paths
4. Press "Stop Recording"
5. Export as KML/GPX

**Result:** Shows your actual walking path on map, useful for:

- Confirming you visited all 5 scenarios
- Measuring distances
- Planning safer routes for professional collection
- Showing supervisors what you tested

---

## 📋 **SAMPLE PRE-COLLECTION REPORT TEMPLATE**

Create a document after testing:

```markdown
# Pre-Collection Route Validation Report

Date: April 30, 2026
Tester: [Your Name]
Weather: Sunny/Partly Cloudy/Rainy
Average Temperature: [°C]

## Scenario D: Open Sky (Baseline)

Location: Beihang Campus North Parking Lot
Coordinates: 40.0589°N, 116.3243°E
Validation Status: ✅ VALIDATED

GNSS Status Results:

- Mean Satellite Count: 11
- Mean C/N0: 42.3 dB-Hz
- PDOP: 2.1
- GPS Status: GPS OK
- Estimated Accuracy: 3.5 meters

GNSS Logger CSV Summary:

- Epoch Count: 300 (5 minutes @ 1 Hz)
- Position Deviation: <2 meters (cluster very tight)
- No signal drops
- Consistent satellite count

Recommendation: READY FOR COLLECTION
Best Time: Morning (8-10 AM) for clearest signal
Notes: Excellent baseline reference location

---

## Scenario A: Instant Blockage

Location: Building 15 Underground Entrance
Coordinates: 40.0565°N, 116.3218°E
Validation Status: ✅ VALIDATED

Blockage Characteristics:

- Transition Distance: 8 meters
- Signal Drop: 42 → 4 dB-Hz (38 dB drop!)
- Satellite Loss: 11 → 0 satellites
- Time to No Fix: ~12 seconds

GNSS Logger Results:

- Before Blockage: 11 satellites, 42 dB-Hz
- After Blockage: 0 satellites, position frozen
- Very clear signal drop in CSV

Recommendation: READY FOR COLLECTION
Best Time: Anytime (underground, time-independent)
Notes: Most dramatic scenario - excellent for testing

---

## Scenario B: Urban Canyon

Location: Academic Building Street (Buildings 3-4)
Coordinates: 40.0578°N, 116.3256°E
Validation Status: ✅ VALIDATED

Signal Degradation:

- Start (in open): 42 dB-Hz, 11 satellites
- Middle (between buildings): 28 dB-Hz, 5 satellites
- Distance: 65 meters

Time Profile:

- t=0s: CLEAN (42 dB-Hz)
- t=20s: WARNING (35 dB-Hz)
- t=40s: WARNING (28 dB-Hz)
- Gradual degradation confirmed

Recommendation: READY FOR COLLECTION
Best Time: Morning-midday (satellite geometry best)
Notes: Perfect multi-minute degradation scenario

---

## Scenario C: Partial Blockage

Location: Library Courtyard (tree canopy)
Coordinates: 40.0591°N, 116.3234°E
Validation Status: ✅ VALIDATED

Signal Characteristics:

- Signal Strength: 33.5 dB-Hz (stable)
- Satellite Count: 7 satellites
- Solution Status: GPS OK (but weak)
- Position Updates: Every 1-2 seconds

Recommendation: READY FOR COLLECTION
Best Time: Afternoon (when trees cast canopy)
Notes: Consistent partial blockage scenario

---

## Scenario E: Approaching Blockage

Location: Open Plaza → Building 12 Approach
Coordinates: 40.0584°N, 116.3224°E
Validation Status: ✅ VALIDATED

Degradation Profile (walking toward building):

- 100m away: 40.2 dB-Hz, 11 satellites
- 75m away: 37.5 dB-Hz, 10 satellites
- 50m away: 34.8 dB-Hz, 8 satellites
- 25m away: 28.3 dB-Hz, 5 satellites
- At building: 15.2 dB-Hz, 2 satellites

Walking Time: 2 minutes 30 seconds

Recommendation: READY FOR COLLECTION
Best Time: Morning (clear satellite geometry)
Notes: Smooth degradation curve - excellent for training

---

## Overall Assessment

✅ All 5 scenarios VALIDATED
✅ Satellite visibility patterns confirmed
✅ Signal degradation patterns confirmed
✅ Safe walking routes identified
✅ Optimal times identified

READY FOR PROFESSIONAL RECEIVER DATA COLLECTION

Next Steps:

1. Review High-Precision Receiver Manual
2. Charge receiver battery
3. Calibrate/setup receiver
4. Collect data for each scenario (follow same route)
5. Export RINEX files
6. Process with RTKLIB
```

---

## 🔍 **RED FLAGS: When to Find Different Location**

| Problem                                             | Signal                 | What to Do                                       |
| --------------------------------------------------- | ---------------------- | ------------------------------------------------ |
| Scenario doesn't exist (signal too good everywhere) | Always >38 dB-Hz       | Move to more urban area / different campus       |
| Blockage is gradual instead of instant              | Drops over 60s not 10s | Find location with abrupt boundary               |
| Signal bounces around too much (multipath)          | Noisy, inconsistent    | Move away from metal structures/buildings        |
| Location requires dangerous crossing                | N/A                    | Find safer alternative with same characteristics |
| GPS never gets full fix                             | Always "No Fix"        | This location is too degraded - find compromise  |

---

## 📌 **KEY TAKEAWAY**

**Today (Smartphone Testing):**

- ✅ Validates that your 5 scenarios actually exist at the locations you chose
- ✅ Shows you the signal patterns you'll see with professional receiver
- ✅ Identifies the safest, best times to collect data
- ✅ Provides baseline data for comparison later

**Tomorrow/Next Week (Professional Receiver):**

- ✅ Uses the same routes you tested today
- ✅ Collects high-quality data suitable for AI training
- ✅ Follows the signal patterns you observed

The smartphone test **saves you time** - you won't waste hours with professional receiver at wrong locations!

---

**Good luck with your pre-collection testing! Take lots of screenshots and notes.** 📱📍
