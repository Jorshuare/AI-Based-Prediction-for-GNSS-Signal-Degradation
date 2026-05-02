# 📱 Quick Field Checklist - Today's Route Testing

Print this page. Take it with you when testing routes.

---

## ✅ BEFORE YOU GO OUT

- [ ] Phone fully charged (will need GPS for 30-45 min)
- [ ] Apps installed: GNSS Status, GNSS Logger, GPXLogger
- [ ] Comfortable shoes (will be walking)
- [ ] Weather-appropriate clothing
- [ ] Camera or phone for photos
- [ ] Notepad for quick notes
- [ ] Umbrella (if rainy)

---

## 🎯 SCENARIO D: OPEN SKY - \_\_\_/10 mins

**Location:** ******\_\_\_\_******  
**Coordinates:** ******\_\_\_\_******

### GNSS Status Check:

```
Satellites visible: ___ (need 8+) ✓ ✗
Mean C/N0: ___ dB-Hz (need 40+) ✓ ✗
PDOP: ___ (need <3) ✓ ✓ ✗
Status: _____________
Sky plot clear: Yes ✓ / No ✗
```

### GNSS Logger Check:

```
Recording duration: ___ minutes
Position cluster tight: Yes ✓ / No ✗
Satellite count stable: Yes ✓ / No ✗
CSV exported: Yes ✓ / No ✗
```

### Decision:

- ✅ VALIDATED - Ready for collection
- ⚠️ NEEDS ADJUSTMENT - Try different location
- ❌ NOT SUITABLE - Find new location

**Notes:** ****************\_\_\_****************

---

## 🎯 SCENARIO A: INSTANT BLOCKAGE - \_\_\_/10 mins

**Location:** ******\_\_\_\_******  
**Coordinates:** ******\_\_\_\_******

### GNSS Status Check (BEFORE entering blockage):

```
Satellites: ___ (baseline)
C/N0: ___ dB-Hz (baseline)
```

### GNSS Status Check (AFTER entering blockage):

```
Satellites: ___ (should drop to 0-2)
C/N0: ___ dB-Hz (should drop to <10)
Time to no signal: ___ seconds (need <15 sec)
```

### Signal Drop Characteristics:

```
Before: ______ dB-Hz
After: ______ dB-Hz
Drop: ______ dB-Hz (should be >30)
Instant: Yes ✓ / Gradual ✗
```

### GNSS Logger Check:

```
Recording duration: ___ minutes
Position freeze visible: Yes ✓ / No ✗
CSV shows clear transition: Yes ✓ / No ✗
```

### Decision:

- ✅ VALIDATED - Instant blockage confirmed
- ⚠️ NEEDS ADJUSTMENT - Blockage too gradual
- ❌ NOT SUITABLE - Find location with sharp boundary

**Notes:** ****************\_\_\_****************

---

## 🎯 SCENARIO B: URBAN CANYON - \_\_\_/15 mins

**Location:** ******\_\_\_\_******  
**Building heights:** **\_** stories  
**Street distance:** **\_** meters

### Starting Point (Open area):

```
Satellites: ___
C/N0: ___ dB-Hz
Time: ___
```

### Middle of street (between buildings):

```
Satellites: ___ (should drop to 3-5)
C/N0: ___ dB-Hz (should drop to 25-35)
Time: ___
```

### Degradation Profile:

```
Type: Gradual ✓ / Instant ✗
Duration: ___ seconds (should be 30-60s)
Total drop: ______ dB-Hz
Pattern smooth: Yes ✓ / Jumpy ✗
```

### GNSS Logger Check:

```
Walking speed: ___ meters/minute
Total walk time: ___ minutes
Satellite count progression recorded: Yes ✓ / No ✗
```

### Decision:

- ✅ VALIDATED - Good urban canyon
- ⚠️ NEEDS ADJUSTMENT - Not gradual enough / too gradual
- ❌ NOT SUITABLE - Signal too stable or drops too fast

**Notes:** ****************\_\_\_****************

---

## 🎯 SCENARIO C: PARTIAL BLOCKAGE - \_\_\_/10 mins

**Location:** ******\_\_\_\_******  
**Type of blockage:** Tree/Building/Bridge/Other: **\_\_**

### GNSS Status Check:

```
Satellites: ___ (should be 6-8)
C/N0: ___ dB-Hz (should be 30-38)
Status: "GPS OK" ✓ / "GPS Weak" ✓ / "No Fix" ✗
Signal stable (not dropping): Yes ✓ / No ✗
```

### Key Check - Not Too Good, Not Too Bad:

```
If C/N0 > 38 dB-Hz: TOO CLEAN - find more blockage
If C/N0 < 25 dB-Hz: TOO DEGRADED - find less blockage
If C/N0 = 30-38 dB-Hz: PERFECT ZONE ✓
```

### GNSS Logger Check:

```
Recording duration: ___ minutes
Position continues to update: Yes ✓ / No ✗
Position accuracy: ~___ meters
```

### Decision:

- ✅ VALIDATED - Good partial blockage
- ⚠️ NEEDS ADJUSTMENT - Signal too strong or too weak
- ❌ NOT SUITABLE - Signal too variable

**Notes:** ****************\_\_\_****************

---

## 🎯 SCENARIO E: APPROACHING BLOCKAGE - \_\_\_/15 mins

**Location:** ******\_\_\_\_******  
**Starting distance from building:** **\_ meters  
**Target building:** ******\_\_********

### Distance Check (Walk toward building):

**100m away:**

```
C/N0: ___ dB-Hz
Satellites: ___
```

**75m away:**

```
C/N0: ___ dB-Hz
Satellites: ___
```

**50m away:**

```
C/N0: ___ dB-Hz
Satellites: ___
```

**25m away:**

```
C/N0: ___ dB-Hz
Satellites: ___
```

**At building:**

```
C/N0: ___ dB-Hz
Satellites: ___
```

### Degradation Verification:

```
Pattern: Smooth curve ✓ / Jumpy ✗
Total drop: ______ dB-Hz (should be ~25 dB-Hz)
Total time: _____ minutes (should be 2-3 min)
Predictable: Yes ✓ / No ✗
```

### GNSS Logger Check:

```
Recording shows smooth degradation: Yes ✓ / No ✗
Distance coverage: 100m+ ✓ / <100m ✗
```

### Decision:

- ✅ VALIDATED - Good degradation approach
- ⚠️ NEEDS ADJUSTMENT - Distance too short / degradation not smooth
- ❌ NOT SUITABLE - Too variable or instant

**Notes:** ****************\_\_\_****************

---

## 📊 OVERALL ASSESSMENT

### Scenarios Status:

```
Scenario A (Instant Blockage): ✅ ⚠️ ❌
Scenario B (Urban Canyon): ✅ ⚠️ ❌
Scenario C (Partial Blockage): ✅ ⚠️ ❌
Scenario D (Open Sky): ✅ ⚠️ ❌
Scenario E (Approaching Blockage): ✅ ⚠️ ❌
```

### Overall Result:

```
✅ ALL SCENARIOS VALIDATED - Ready for professional collection
⚠️ MOST SCENARIOS OK - 1-2 need alternate locations
❌ MAJOR ISSUES - Need to find new locations for 3+ scenarios
```

### Next Steps:

1. ***
2. ***
3. ***

---

## 📸 PHOTOS TO TAKE

**For each scenario:**

- [ ] Wide view (geography)
- [ ] GNSS Status screen
- [ ] Sky view (showing obstacles)
- [ ] Safety considerations

**Total photos needed:** 20 (4 per scenario)

---

## 📝 GENERAL OBSERVATIONS

```
Weather: Sunny ☀️ / Cloudy ☁️ / Rainy 🌧️ / Other: ___
Time of day: Morning / Afternoon / Evening
GPS conditions: Excellent / Good / Fair / Poor
Satellite geometry: (Optional note) ________________
Overall impressions: ________________________________
```

---

**Review checklist after testing. Document which locations need adjustment before professional collection!**
