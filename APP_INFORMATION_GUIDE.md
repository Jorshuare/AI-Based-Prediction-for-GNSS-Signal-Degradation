# 📱 APP COMPARISON & INFORMATION GUIDE

## Which App for What Purpose?

---

## 🏆 **BEST APPS FOR TODAY'S TESTING**

### **#1 PRIORITY: GNSS Status**

**Download:** Google Play Store - "GNSS Status" (by Android Dev)

**Purpose:** Real-time satellite visibility and signal monitoring

**Information Provided:**

| Feature                    | What You See                       | Why It Matters                             |
| -------------------------- | ---------------------------------- | ------------------------------------------ |
| **C/N0 (Signal Strength)** | Shows dB-Hz per satellite          | Tells you GPS signal quality (40+ is good) |
| **Satellite Count**        | "Using X satellites"               | More satellites = better accuracy          |
| **Sky Plot**               | Circle showing satellite positions | Shows which directions are blocked         |
| **PDOP/HDOP/VDOP**         | Precision dilution of precision    | Geometry quality (lower is better)         |
| **Accuracy Estimate**      | ~X meters                          | What accuracy the phone can achieve        |
| **GPS Status**             | "GPS OK", "GPS Weak", "No Fix"     | Overall GPS health                         |
| **Elevation Angle**        | Degrees above horizon              | Only satellites >20° are useful            |

**How to Use It:**

```
1. Open app
2. Wait 30 seconds for "GPS OK"
3. Screenshot the main screen (shows all key metrics)
4. Tap "C/N0" tab to see signal per satellite
5. Tap "Sats" tab to see satellite list
6. Tap "Sky" tab to see where satellites are
7. Take screenshot of each tab
```

**What to Look For in Each Scenario:**

```
SCENARIO D (OPEN SKY):
✅ C/N0 should be HIGH (40-50 dB-Hz)
✅ Satellite count HIGH (10-12)
✅ Sky plot CLEAR (all directions)

SCENARIO A (INSTANT BLOCKAGE):
✅ C/N0 drops QUICKLY (in <10 seconds)
✅ Satellite count drops to 0
✅ Sky plot shows all satellites disappearing

SCENARIO B (URBAN CANYON):
✅ C/N0 drops GRADUALLY (over 30-60 seconds)
✅ Satellite count goes from 10 to 3-5
✅ Sky plot shows satellites disappearing from sides

SCENARIO C (PARTIAL BLOCKAGE):
✅ C/N0 is MEDIUM (30-38 dB-Hz) and STABLE
✅ Satellite count is 6-8 and doesn't change
✅ Sky plot shows some blockage, but many satellites

SCENARIO E (APPROACHING BLOCKAGE):
✅ C/N0 drops SMOOTHLY as you walk (40 → 20 dB-Hz)
✅ Satellite count decreases smoothly
✅ Sky plot shows satellites disappearing overhead
```

**Advantages:**

- ✅ Real-time updates (every 1 second)
- ✅ All key metrics in one view
- ✅ Free and simple
- ✅ No export needed (just screenshots)

**Limitations:**

- ❌ No data export (can't save raw data)
- ❌ Phone-level accuracy only (5-10 meters)
- ❌ No professional RINEX format

---

### **#2 PRIORITY: GNSS Logger**

**Download:** Google Play Store - "GNSS Logger" (by Google Research)

**Purpose:** Record GPS data in CSV format for analysis

**Information Provided:**

```csv
UtcTimeInMs,LatitudeDegrees,LongitudeDegrees,AltitudeMeters,
HorizontalAccuracyMeters,VerticalAccuracyMeters,SpeedMps,
BearingDegrees,NumSatellitesUsedInFix,Svid,
TimeOffsetNs,State,CN0DbHz,AgcDb,ReceiverRollDeg,
ReceiverPitchDeg,ReceiverYawDeg,SerialNumber
```

**Key Columns You Care About:**

| Column                     | Meaning              | What to Look For                            |
| -------------------------- | -------------------- | ------------------------------------------- |
| `UtcTimeInMs`              | Timestamp            | Shows progression over time                 |
| `LatitudeDegrees`          | Latitude             | Should FREEZE in blockage scenarios         |
| `LongitudeDegrees`         | Longitude            | Should FREEZE in blockage scenarios         |
| `NumSatellitesUsedInFix`   | Satellite count      | Should DROP in degraded scenarios           |
| `CN0DbHz`                  | Signal strength      | Should DROP in degraded scenarios           |
| `HorizontalAccuracyMeters` | Position uncertainty | Should INCREASE (get worse) as GPS degrades |
| `State`                    | Measurement state    | Should go to "0" (no fix) in blockage       |

**How to Use It:**

```
1. Open GNSS Logger app
2. Press red "Start Recording" button
3. Perform your scenario (walk, wait, enter building)
4. Press red "Stop Recording" button
5. Scroll down to find your recording session
6. Tap on session → "Share" or "Send"
7. Email CSV to yourself
8. Download and open in Excel or Python
```

**Sample CSV Output (First Few Rows):**

```
1619802640000, 40.0589, 116.3243, 45.2, 3.5, 4.2, 0.0, 0.0, 11, 1, 0, 1, 42.3, 0, 0.0, 0.0, 0.0, SN123
1619802641000, 40.0589, 116.3243, 45.3, 3.4, 4.1, 0.2, 45.0, 11, 1, 1, 1, 42.2, 0, 0.0, 0.0, 0.0, SN123
1619802642000, 40.0589, 116.3243, 45.1, 3.6, 4.3, 0.1, 30.0, 11, 1, 2, 1, 42.4, 0, 0.0, 0.0, 0.0, SN123
```

**What Good Data Looks Like for Each Scenario:**

**SCENARIO D (Open Sky):**

```
Expected CSV Pattern:
- NumSatellitesUsedInFix: consistently 10-12
- CN0DbHz: consistently 40-50
- HorizontalAccuracyMeters: consistently 3-5
- Lat/Lon: small variations (±0.00002°), NOT frozen
```

**SCENARIO A (Instant Blockage):**

```
Expected CSV Pattern:
Row 1-50: NumSatellitesUsedInFix = 11-12, CN0DbHz = 40+
Row 51-60: NumSatellitesUsedInFix drops 11→5→0
Row 61+: NumSatellitesUsedInFix = 0, Lat/Lon FROZEN, CN0DbHz = 0
```

**SCENARIO B (Urban Canyon):**

```
Expected CSV Pattern:
- NumSatellitesUsedInFix: 11 → 10 → 8 → 5 → 3 (gradual decrease)
- CN0DbHz: 42 → 38 → 32 → 28 → 22 (gradual decrease)
- HorizontalAccuracyMeters: 3 → 5 → 8 → 12 → 18 (gets worse)
- Lat/Lon: continuously updating, moving position
```

**SCENARIO C (Partial Blockage):**

```
Expected CSV Pattern:
- NumSatellitesUsedInFix: consistently 6-8
- CN0DbHz: consistently 30-38 (stable, doesn't drop)
- HorizontalAccuracyMeters: consistently 5-10 meters
- Lat/Lon: normal updates, position moves
```

**SCENARIO E (Approaching Blockage):**

```
Expected CSV Pattern:
- First 50 rows: NumSatellitesUsedInFix = 11, CN0DbHz = 40
- Middle rows: gradual decrease as you walk
- Last 50 rows: NumSatellitesUsedInFix = 2-3, CN0DbHz = 20-25
- Overall: smooth curve down (not jumpy)
```

**Advantages:**

- ✅ Provides raw data for analysis
- ✅ Can export to Excel / Python / RTKLIB
- ✅ Shows exact progression over time
- ✅ Can calculate statistics

**Limitations:**

- ❌ Phone accuracy only (not suitable for AI training)
- ❌ Takes time to review CSV
- ❌ No professional features

---

### **#3 OPTIONAL: Geo++ RINEX Logger**

**Download:** Google Play Store - "Geo++ RINEX Logger"

**Purpose:** Record raw GPS measurements in professional RINEX format

**Information Provided:**

```
RINEX (Receiver Independent Exchange Format) File:
- Observation file (.??o)
- Raw pseudorange measurements
- Carrier phase measurements
- Doppler measurements
- Signal strength (C/N0) per satellite
```

**When to Use:**

- If you want professional format from day 1
- Good for direct RTKLIB processing later
- More complex to use

**When NOT to Use (Today's Pre-testing):**

- For route validation (overkill)
- If you're not familiar with RINEX format yet
- If you don't have RTKLIB installed

**Advantages:**

- ✅ Professional format (like your receiver will produce)
- ✅ Can be processed with RTKLIB immediately
- ✅ Contains more information than CSV

**Limitations:**

- ❌ Harder to interpret raw data
- ❌ Requires RTKLIB knowledge
- ❌ Smartphone phone-level accuracy anyway

---

## 🎯 **TODAY'S RECOMMENDATION**

### **For Route Validation (Today's Activity):**

**Primary Tool:** GNSS Status

- Takes quick screenshots
- See all metrics instantly
- No export/processing needed
- Fast validation of route

**Secondary Tool:** GNSS Logger

- Records CSV backup data
- Can verify patterns later
- Optional but recommended

**Skip:** Geo++ RINEX Logger

- Not needed for validation
- Professional receiver will do this later
- Too complex for quick scouting

---

## 📊 **COMPARISON TABLE: All GPS Apps**

| Feature                         | GNSS Status          | GNSS Logger   | Geo++ RINEX   | GPS Test         |
| ------------------------------- | -------------------- | ------------- | ------------- | ---------------- |
| **Real-time signal monitoring** | ✅ Excellent         | ⚠️ Delayed    | ❌ No         | ✅ Good          |
| **Satellite sky plot**          | ✅ Yes               | ❌ No         | ❌ No         | ✅ Yes           |
| **C/N0 (signal strength)**      | ✅ Real-time         | ✅ CSV export | ✅ RINEX      | ✅ Graph         |
| **Satellite count**             | ✅ Real-time         | ✅ CSV export | ✅ RINEX      | ✅ Real-time     |
| **Position display**            | ✅ Shows Lat/Lon     | ✅ CSV export | ⚠️ In RINEX   | ✅ Shows Lat/Lon |
| **Data export**                 | ❌ Screenshots only  | ✅ CSV        | ✅ RINEX      | ⚠️ Limited       |
| **RTKLIB compatible**           | ❌ No                | ⚠️ Not ideal  | ✅ Yes        | ❌ No            |
| **Phone accuracy**              | Phone-level          | Phone-level   | Phone-level   | Phone-level      |
| **Ease of use**                 | ⭐⭐⭐⭐⭐ Very Easy | ⭐⭐⭐⭐ Easy | ⭐⭐⭐ Medium | ⭐⭐⭐⭐ Easy    |
| **Cost**                        | Free                 | Free          | Free          | Free             |

---

## 🔍 **WHAT INFORMATION DO YOU ACTUALLY NEED TODAY?**

### **To Validate Scenario D (Open Sky):**

- C/N0 value (screenshot from GNSS Status)
- Satellite count (screenshot from GNSS Status)
- GPS status (screenshot from GNSS Status)
- ✓ GNSS Status only needed

### **To Validate Scenario A (Instant Blockage):**

- Before: C/N0 and satellite count (screenshot)
- After: C/N0 and satellite count (screenshot)
- Time taken to lose signal (GNSS Status observation)
- CSV showing position freeze (GNSS Logger - optional)
- ✓ GNSS Status required, GNSS Logger optional

### **To Validate Scenario B (Urban Canyon):**

- Progression: C/N0 dropping (screenshot multiple times)
- Progression: Satellite count dropping (screenshot multiple times)
- Duration of walk (timed observation)
- CSV showing gradual degradation (GNSS Logger recommended)
- ✓ GNSS Status required, GNSS Logger recommended

### **To Validate Scenario C (Partial Blockage):**

- Stable C/N0 value (screenshot from GNSS Status)
- Stable satellite count (screenshot from GNSS Status)
- Position still updating (observation or GNSS Logger)
- ✓ GNSS Status required, GNSS Logger optional

### **To Validate Scenario E (Approaching Blockage):**

- Progression: C/N0 smoothly dropping (multiple screenshots)
- Progression: Satellite count dropping (multiple screenshots)
- Walk distance and time (measurement + observation)
- CSV showing smooth curve (GNSS Logger recommended)
- ✓ GNSS Status required, GNSS Logger recommended

---

## 📋 **RECOMMENDED APP INSTALLATION ORDER**

**Step 1:** Install GNSS Status (must-have)
**Step 2:** Install GNSS Logger (very helpful)
**Step 3:** Install GPXLogger (optional, for route mapping)
**Step 4:** Install GPS Test (bonus, for extra data)

**Total apps:** 2-4, total size: ~50 MB, takes 5 minutes

---

## ⚡ **QUICK TIPS**

### **Make GNSS Status Useful:**

1. Hold phone vertically (doesn't matter, but convenient)
2. Let it stabilize 30 seconds after opening
3. Screenshot before you start walking (baseline)
4. Screenshot at each key location
5. Screenshot when signal changes noticeably

### **Make GNSS Logger Useful:**

1. Start recording BEFORE you start scenario action
2. Continue recording for entire scenario (5-10 min)
3. Stop recording when scenario is complete
4. Label your recordings: "ScenarioB_UrbanCanyon_LocationXY"
5. Export immediately (don't let phone run out of battery)

### **Make Data Export Work:**

1. Email CSVs to yourself immediately (backup)
2. Open on computer later to review
3. Save with clear naming: "20260430_ScenarioD_CSV.csv"

---

## ❓ **COMMON QUESTIONS**

**Q: Do I need all 3 apps today?**
A: No. Minimum = GNSS Status only. Recommended = GNSS Status + GNSS Logger. Professional = All 3 + more.

**Q: The phone seems to work, but smartphone data won't train my AI model?**
A: Correct! Phone data (~5-10m accuracy) is too noisy. Professional receiver (~5cm accuracy after RTKLIB) is required for training.

**Q: Can I use phone data at all?**
A: Yes! For:

- Today's route validation (what you're doing)
- Verifying patterns (signal does drop as expected)
- Comparing with professional receiver later
  But NOT for: Training the AI model

**Q: What if phone signal is bad in one scenario?**
A: That's okay! It proves that scenario location works (if smartphone can barely see signal, professional receiver will show it more clearly). Find a different location only if phone signal is COMPLETELY absent (0 satellites) in all scenarios except A.

**Q: How long should I test each scenario?**
A: 5-10 minutes each. Enough to see patterns, not so long you drain battery. Total testing time: 30-45 minutes.

**Q: What time of day is best to test?**
A: Morning (8-10 AM) or midday (11 AM-1 PM) when satellite geometry is best. Avoid evening (fewer satellites due to orbital geometry).

---

**You're ready! Download the apps and go test your routes.** 📱✅
