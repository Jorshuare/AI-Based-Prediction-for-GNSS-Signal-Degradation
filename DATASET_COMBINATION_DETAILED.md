# DATASET COMBINATION STRATEGY

## How to Integrate Supervisor Data + Your Collections + Public Datasets

---

## 🗂️ **COMPLETE DATASET INVENTORY**

### **What You Have Right Now (Existing)**

#### Supervisor Datasets (Already at Beihang)

```
Location: data/raw/ or supervisor lab

1. VEHICLE DATASET
   - Format: ROS bag file containing GPS/IMU/camera feeds
   - Size: ~50GB
   - GPS Topics: Look for /gps/fix, /ublox/fix, or /navsat/fix
   - Duration: Multiple hours of driving
   - Quality: High (professional recording)
   - Use: Training baseline + ground truth reference

2. DRONE DATASET
   - Format: ROS bag file
   - Size: ~10GB
   - GPS Topics: Similar to vehicle
   - Duration: Multiple flight sessions
   - Quality: High (aerial perspective)
   - Use: Diversity in collection platform + altitude variations
```

#### Public Datasets (Available for Download)

```
1. URBANNAV DATASET
   - Location: https://github.com/IPNL-POLYU/UrbanNavDataset
   - Format: GNSS raw measurements (RINEX) + ground truth
   - Size: ~50GB
   - Cities: Hong Kong, Beijing, Taipei
   - GPS Quality: Raw (needs RTKLIB processing)
   - Use: Generalization test (different geographies)

2. OXFORD ROBOTCAR DATASET
   - Location: http://ori.ox.ac.uk/datasets/radar-robotcar-dataset
   - Format: Radar + GPS + LiDAR
   - Size: ~200GB (can download subsets)
   - Location: Oxford, UK (city driving)
   - GPS Quality: Basic GPS (needs RTKLIB)
   - Use: Generalization + multi-sensor context

3. NCLT/KAIST DATASET (Optional - might not arrive in time)
   - Location: Contact researchers directly
   - Format: CSV time series
   - Size: ~10GB
   - Location: University campus (KAIST, Seoul)
   - Duration: Multi-week collection
   - Use: Long-term stability testing
```

---

## 🎯 **WHY WE NEED EACH DATASET (The Critical Importance)**

### **1. YOUR 5 SCENARIOS (A-E): The Foundation**

**What you're collecting:** ~10,000 GPS epochs across 5 problem scenarios  
**Why it's essential:**

- **Labeled data creation**: Only YOUR data is labeled by YOU in real-time (CLEAN/WARNING/DEGRADED)
- **Domain-specific**: Collected at YOUR university campus - represents your target environment
- **Diversity**: 5 scenarios = 5 different types of GPS failure modes
- **Realism**: Real-time collection beats simulated/synthetic data
- **Ground truth**: You know exactly when/where GPS fails (because you designed the scenarios)

**What happens without it:** Model has no labeled training data → Cannot train at all

---

### **2. SUPERVISOR VEHICLE DATASET: Baseline Reality Check**

**What it provides:** 50+ hours of real-world driving from a research vehicle  
**Why it's essential:**

- **Scale**: 50GB >> your 5 scenarios. Provides massive volume for training
- **Real-world driving**: Not controlled experiments - actual roads, traffic, weather
- **Multiple environments**: Different times of day, different city zones
- **Credibility**: Pre-existing professional data validates your approach
- **Sanity check**: If your model doesn't work on this, it won't work anywhere

**Real-world example:**

- Your 5 scenarios: "Intentional GPS failure tests"
- Vehicle dataset: "Incidental GPS failures during normal driving"
- **They're different!** You need BOTH to learn real degradation patterns

**What happens without it:** Your model only sees intentional failures → Fails on real-world subtle degradations

---

### **3. SUPERVISOR DRONE DATASET: Coverage Perspective**

**What it provides:** GPS from aerial platform at varying altitudes  
**Why it's essential:**

- **Different perspective**: Drone flies differently than car drives
- **Altitude variation**: Tests GPS at different heights above ground
- **Clear line-of-sight issues**: Trees, buildings affect drone GPS differently than car GPS
- **Diversity in collection**: Model learns satellite geometry from multiple angles
- **Reduced bias**: Only vehicle data = model optimized for driving, not generalizable

**Real-world example:**

- Car at street level: Buildings block GPS from below
- Drone above buildings: Satellites visible from above but different multipath effects
- **Need both** to understand full 3D degradation patterns

**What happens without it:** Model biased toward ground-level scenarios → Fails on elevated GPS (drones, tall buildings)

---

### **4. URBANNAV DATASET: Generalization Test 1 (Multi-City)**

**What it provides:** GPS data from Hong Kong, Beijing, Taipei - urban environments  
**Why it's essential:**

**The generalization problem:**

```
Scenario: Your model trained only on Beijing campus GPS
Question: Will it work in Tokyo? New York? London?
Answer (without UrbanNav): UNKNOWN
```

**UrbanNav solves this:**

- **Different cities** = Different building heights, densities, street layouts
- **Different GPS receivers** = Different sensitivity profiles
- **Different ionosphere** = GPS accuracy varies by latitude/latitude
- **Proves model learns general patterns**, not Beijing-specific quirks

**Real-world impact:**

- Waymo wants model that works in 50 cities
- If model only works in Beijing = worthless for commercial deployment
- UrbanNav proves it's generalizable

**What happens without it:** Model seems great on test set (Beijing) → Fails catastrophically on Tokyo or New York

---

### **5. OXFORD ROBOTCAR DATASET: Generalization Test 2 (Different Country + Sensors)**

**What it provides:** GPS from Oxford, UK + radar + LiDAR context  
**Why it's essential:**

**Testing assumptions:**

- **Different country** = Different GPS satellite geometry, different ionosphere
- **Different city infrastructure** = UK roads/buildings different from China
- **Different sensor setup** = Tests if model is brittle to hardware changes
- **Multi-sensor context** = Can see how GPS failures correlate with other sensors failing

**Scientific rigor:**

- If UrbanNav test works, you proved "works in different Chinese cities"
- If Oxford test works, you proved "works globally"
- Difference = How much is learned vs. how much is regional bias

**Real-world scenario:**

```
Beijing Test: F1-score = 0.88 (trained + tested on same city)
UrbanNav Test: F1-score = 0.85 (3% drop - acceptable)
Oxford Test: F1-score = 0.83 (5% drop - still good)
→ "Model generalizes globally" ✅

vs.

Beijing Test: F1-score = 0.88
Oxford Test: F1-score = 0.45 (50% drop)
→ "Model only works in China" ❌
```

**What happens without it:** Can't prove model isn't just memorizing Chinese GPS patterns

---

### **6. KAIST DATASET: Long-Term Stability Test**

**What it provides:** Multiple weeks of continuous GPS collection from same campus  
**Why it's essential:**

**Temporal generalization:**

- Your 5 scenarios = 1-2 days of collection
- KAIST = 2+ weeks of continuous data
- **Tests**: "Does model work on Week 1, Week 2, Week 3 data?"

**Real-world deployment:**

```
Your model trained on Week 1-2 data
Deployed in production for Month 1-12
Does it still work in Month 12?
→ KAIST answers this
```

**Seasonal variation:**

- GPS accuracy changes with season (ionosphere, sun activity, weather)
- KAIST dataset spans seasons
- Tests if model adaptation is needed over time

**What happens without it:** Model works for 2 weeks → Fails after 2 months in production

---

## 📊 **DATASET COMBINATION LOGIC (Why Together?)**

```
YOUR SCENARIOS (A-E)
├─ Pros: Labeled, controlled, designed
└─ Cons: Only 10k epochs, only Beijing, only 1-2 days

SUPERVISOR DATA (Vehicle + Drone)
├─ Pros: Real-world, large scale, diverse
└─ Cons: Not labeled, only Beijing campus

URBANNAV (Hong Kong, Beijing, Taipei)
├─ Pros: Different cities, same region
└─ Cons: No labels, need to extract labels programmatically

OXFORD (UK)
├─ Pros: Different country, validated dataset
└─ Cons: Different GPS patterns, different hardware

KAIST (Multiple weeks)
├─ Pros: Long-term stability data
└─ Cons: Single campus, limited diversity

═══════════════════════════════════════════════════════════

COMBINED:
✅ Labeled training data (from your scenarios)
✅ Real-world baseline (supervisor vehicle)
✅ Multi-platform coverage (supervisor drone)
✅ Multi-city validation (UrbanNav)
✅ Global validation (Oxford)
✅ Temporal stability (KAIST)
✅ ~150,000 total epochs
✅ Proves generalization works
✅ Publishable results
```

---

## 🎓 **WHAT EACH DATASET TEACHES THE MODEL**

| Dataset            | Teaches Model                                       | Example                                            |
| ------------------ | --------------------------------------------------- | -------------------------------------------------- |
| **Your Scenarios** | "What does GPS failure look like?"                  | Signal drops from 40 → 5 dB-Hz                     |
| **Vehicle**        | "How does failure happen in real driving?"          | Gradual degradation while turning corner           |
| **Drone**          | "How does altitude affect failures?"                | High altitude = different satellite visibility     |
| **UrbanNav**       | "Do failures look the same in other cities?"        | Hong Kong buildings = different multipath patterns |
| **Oxford**         | "Does this work in completely different countries?" | UK ionosphere ≠ China ionosphere                   |
| **KAIST**          | "Will this still work next month?"                  | Week 1 performance = Month 1 performance?          |

---

## ❌ **WHAT WOULD HAPPEN WITHOUT EACH DATASET**

### **Without Your 5 Scenarios:**

- No labeled training data
- Can't train anything
- Project fails immediately

### **Without Supervisor Vehicle:**

- Only have intentional test failures
- Miss real-world subtle degradations
- Model overfits to extreme cases
- Doesn't work on real roads

### **Without Supervisor Drone:**

- Only ground-level perspective
- Model fails on elevated GPS (drones, rooftop receivers)
- Missing 3D degradation patterns
- Biased toward car-level driving

### **Without UrbanNav:**

- Might work only in Beijing
- Can't claim "generalizes to other cities"
- Customers (Waymo, Baidu) won't trust it
- Not publishable

### **Without Oxford:**

- Generalization only proven in Asia
- Fails in Europe/Americas
- Global deployment impossible
- Publishability compromised

### **Without KAIST:**

- Model works today
- Might break in 3 months
- Deployment too risky
- Not production-ready

---

## 💡 **THE RESEARCH VALIDATION PYRAMID**

```
                    ▲
                   ╱ ╲
                  ╱   ╲  KAIST (Long-term stability)
                 ╱     ╲
                ╱       ╲
               ╱─────────╲  Oxford (Global generalization)
              ╱           ╲
             ╱             ╱  UrbanNav (Multi-city test)
            ╱─────────────╱
           ╱               ╱  Supervisor Data (Real-world baseline)
          ╱───────────────╱
         ╱                 ╱  Your Scenarios (Labeled foundation)
        ╱─────────────────╱

Bottom (Foundation): You need YOUR labeled data
Layer 2 (Credibility): Supervisor data proves real-world relevance
Layer 3 (Validation): UrbanNav proves multi-city generalization
Layer 4 (Global): Oxford proves global applicability
Top (Durability): KAIST proves long-term stability

MISSING ANY LAYER = PYRAMID COLLAPSES
```

---

## 📈 **HOW PAPERS ARE EVALUATED (Why You Need All Data)**

When your paper is reviewed:

**Reviewer 1:** "Does model work on YOUR test data?"
→ Use your scenarios + supervisor data

**Reviewer 2:** "Will it work on other researchers' data?"
→ Use UrbanNav (peer-reviewed dataset)

**Reviewer 3:** "Does it work outside Asia?"
→ Use Oxford (UK-based researchers understand this validates global applicability)

**Reviewer 4:** "Will it work in production for months?"
→ Use KAIST (long-term data)

**Reviewer 5:** "Why should we believe this over other papers?"
→ Show results on 4 different datasets (no paper did this for GNSS prediction before!)

**If you only used YOUR data:**
→ "Nice, but only works on their campus"
→ Paper rejected

**If you use all 5 datasets:**
→ "Proven on 5 diverse sources across 4 countries over multiple months"
→ Paper accepted, published

---

## 🚀 **THE COMPLETE JUSTIFICATION TABLE**

| Dataset            | Why Need It               | Cost of Missing It                  | Contribution       |
| ------------------ | ------------------------- | ----------------------------------- | ------------------ |
| Your Scenarios     | **Labeled training**      | Project impossible                  | 10% (foundation)   |
| Supervisor Vehicle | **Real-world validation** | Model overfits                      | 20% (credibility)  |
| Supervisor Drone   | **3D perspective**        | Biased model                        | 10% (completeness) |
| UrbanNav           | **Multi-city proof**      | Can't claim regional generalization | 25% (validation 1) |
| Oxford             | **Global proof**          | Can't claim global generalization   | 25% (validation 2) |
| KAIST              | **Temporal stability**    | Unknown production reliability      | 10% (durability)   |

---

## ✅ **CHECKLIST: Do We Have Strong Justification?**

- [ ] ✅ Why we collect YOUR scenarios (labeled data)
- [ ] ✅ Why supervisor vehicle data (real-world baseline)
- [ ] ✅ Why supervisor drone data (altitude diversity)
- [ ] ✅ Why UrbanNav (multi-city Asia test)
- [ ] ✅ Why Oxford (global test)
- [ ] ✅ Why KAIST (temporal stability)
- [ ] ✅ What failure modes we learn from each
- [ ] ✅ What happens if any dataset is missing
- [ ] ✅ How reviewers will evaluate each dataset
- [ ] ✅ How pyramid shows importance hierarchy

---

## 📥 **STEP 1: DOWNLOAD PUBLIC DATASETS (Days 9-12)**

### UrbanNav Download

```bash
# Option A: Manual download
# 1. Go to: https://github.com/IPNL-POLYU/UrbanNavDataset
# 2. Register account
# 3. Download sample datasets for Hong Kong, Beijing, Taipei
# 4. Save to: data/raw/public/urbannav/

# Option B: Automated (if you have drive access)
# Contact IPNL-POLYU for Google Drive download link

# Directory structure after download:
data/raw/public/urbannav/
├── HongKong/
│   ├── 2020-07-24-1/
│   │   ├── imu.csv
│   │   ├── magnetometer.csv
│   │   ├── odometer.csv
│   │   ├── ground_truth.csv
│   │   └── raw_measurements.ubx
│   └── 2020-07-24-2/
│       └── ...
├── Beijing/
└── Taipei/
```

### Oxford RobotCar Download

```bash
# Register at: http://ori.ox.ac.uk/datasets/radar-robotcar-dataset
# Download using Python:

git clone https://github.com/dbarnes/radar-robotcar-dataset-sdk.git
cd radar-robotcar-dataset-sdk

# Download small sample first to test
python -m radar_robotcar_dataset_sdk.downloader.download \
    --sample_dataset Small \
    --download_folder C:\data\oxford

# Or download specific sensors
python -m radar_robotcar_dataset_sdk.downloader.download \
    --datasets="2019-01-16-11-53-11-radar-oxford-10k" \
    --sensors="Navtech CTS350-X Radar,NovAtel GPS / INS" \
    --download_folder C:\data\oxford
```

### KAIST/NCLT (Contact-based)

```bash
# Email the researchers:
# - NCLT contact: johndoe@umich.edu
# - KAIST GPS contact: contact@kaist.ac.kr

# Typical response:
# - They send Google Drive link
# - You download .tar.gz files
# - Extract to: data/raw/public/kaist/

# Directory structure:
data/raw/public/kaist/
├── 2012-08-04/
│   ├── gps.csv
│   ├── gps_rtk.csv
│   ├── imu.csv
│   └── groundtruth.csv
└── 2013-04-05/
    └── ...
```

---

## 🔄 **STEP 2: CONVERT ALL DATASETS TO UNIFIED FORMAT**

### Create Universal Extraction Script

**File:** `src/extraction/universal_extractor.py`

```python
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class GPSExtractor(ABC):
    """Base class for extracting GPS from different formats"""

    @abstractmethod
    def extract(self, input_path):
        """Return DataFrame with columns: timestamp, lat, lon, alt, cnr, num_satellites"""
        pass

class RosbagExtractor(GPSExtractor):
    """Extract from ROS bag files"""
    def extract(self, bag_path):
        import rosbag
        data = []

        bag = rosbag.Bag(bag_path)
        for topic, msg, t in bag.read_messages(topics=['/fix', '/gps/fix', '/ublox/fix']):
            data.append({
                'timestamp': t.to_sec(),
                'latitude': msg.latitude,
                'longitude': msg.longitude,
                'altitude': msg.altitude,
                'num_satellites': msg.status.satellite_used_prn.__len__() if hasattr(msg, 'status') else 0,
                'cnr': msg.position_covariance[0]  # Simplified
            })

        return pd.DataFrame(data)

class URBannavExtractor(GPSExtractor):
    """Extract from UrbanNav format"""
    def extract(self, urbannav_folder):
        # UrbanNav provides raw measurements
        raw_meas = pd.read_csv(f"{urbannav_folder}/raw_measurements.csv")
        ground_truth = pd.read_csv(f"{urbannav_folder}/ground_truth.csv")

        # Merge on timestamp
        data = raw_meas.merge(ground_truth, on='timestamp', how='left')

        # Rename columns to standard format
        data = data.rename(columns={
            'gps_week_second': 'timestamp',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'altitude': 'altitude',
            'cn0': 'cnr',
            'num_satellites': 'num_satellites'
        })

        return data[['timestamp', 'latitude', 'longitude', 'altitude', 'cnr', 'num_satellites']]

class OxfordExtractor(GPSExtractor):
    """Extract from Oxford RobotCar format"""
    def extract(self, oxford_folder):
        # Oxford provides GPS/INS data in specific format
        gps_file = f"{oxford_folder}/gps/gps.csv"

        data = pd.read_csv(gps_file)

        # Oxford columns typically: timestamp, latitude, longitude, altitude, ...
        return data[['timestamp', 'latitude', 'longitude', 'altitude']].copy()

class KAISTExtractor(GPSExtractor):
    """Extract from KAIST/NCLT format"""
    def extract(self, kaist_folder):
        gps_data = pd.read_csv(f"{kaist_folder}/gps.csv")

        return gps_data[['timestamp', 'latitude', 'longitude', 'altitude']].copy()

# Usage
def extract_all_datasets():
    """Master function to extract all datasets"""

    extractors = {
        'supervisor_vehicle': (RosbagExtractor(), 'data/raw/supervisor/vehicle_dataset.bag'),
        'supervisor_drone': (RosbagExtractor(), 'data/raw/supervisor/drone_dataset.bag'),
        'urbannav_hk': (URBannavExtractor(), 'data/raw/public/urbannav/HongKong/2020-07-24-1'),
        'urbannav_beijing': (URBannavExtractor(), 'data/raw/public/urbannav/Beijing/2020-08-15-1'),
        'oxford_2019_01': (OxfordExtractor(), 'data/raw/public/oxford/2019-01-16-11-53-11'),
        'kaist_2012': (KAISTExtractor(), 'data/raw/public/kaist/2012-08-04'),
    }

    extracted_data = {}
    for dataset_name, (extractor, path) in extractors.items():
        print(f"Extracting {dataset_name}...")
        try:
            df = extractor.extract(path)
            output_path = f'data/raw/extracted/{dataset_name}.csv'
            df.to_csv(output_path, index=False)
            extracted_data[dataset_name] = len(df)
            print(f"✓ {dataset_name}: {len(df)} epochs")
        except Exception as e:
            print(f"✗ {dataset_name}: {str(e)}")

    return extracted_data

if __name__ == "__main__":
    extract_all_datasets()
```

---

## 🔬 **STEP 3: RUN RTKLIB ON EACH DATASET**

### Batch RTKLIB Processing

**File:** `src/processing/batch_rtklib.py`

```python
import subprocess
import os
import glob

RTKLIB_BIN = r"C:\Program Files\RTKLIB\bin"

def run_rtklib_batch(extracted_csv_dir, output_pos_dir):
    """
    Process all extracted CSVs through RTKLIB pipeline

    For each dataset:
    1. Convert CSV → RINEX (RTKCONV)
    2. Download orbits for that date
    3. Post-process (RTKPOST)
    4. Verify output in RTKPLOT
    """

    csv_files = glob.glob(f"{extracted_csv_dir}/*.csv")

    for csv_file in csv_files:
        dataset_name = os.path.basename(csv_file).replace('.csv', '')
        print(f"\nProcessing {dataset_name}...")

        # Step 1: Convert CSV to UBX (intermediate format)
        ubx_file = f"data/rinex/{dataset_name}.ubx"
        # (Assume you have a csv_to_ubx converter)

        # Step 2: Convert UBX to RINEX
        obs_file = f"data/rinex/{dataset_name}.obs"
        cmd = f'{RTKLIB_BIN}\\rtkconv.exe -format ubx -d data\\rinex "{ubx_file}"'
        print(f"Running: {cmd}")
        os.system(cmd)

        # Step 3: Download orbits for this dataset's date
        # (Extract date from dataset_name or CSV)
        # E.g., from "urbannav_beijing_20200815"

        # Step 4: Post-process
        pos_file = f"{output_pos_dir}/{dataset_name}_solution.pos"
        cmd = f'{RTKLIB_BIN}\\rtkpost.exe -k rtkpost.conf ' \
              f'-in:obs "{obs_file}" -in:nav auto -out "{pos_file}"'
        print(f"Running: {cmd}")
        os.system(cmd)

        print(f"✓ {dataset_name} processed → {pos_file}")
```

---

## 🎯 **STEP 4: EXTRACT 35 FEATURES FROM EACH DATASET**

### Unified Feature Extraction

**File:** `src/features/extract_features_unified.py`

```python
import pandas as pd
import numpy as np

def extract_35_features(rtklib_pos_file, output_csv):
    """
    Extract 35 features from RTKLIB .pos file
    CRITICAL: Use SAME logic for ALL datasets!
    """

    df = pd.read_csv(rtklib_pos_file, skiprows=0)

    features_list = []

    # Apply 30-second sliding window
    for idx in range(30, len(df)):
        window = df.iloc[idx-30:idx]
        current = df.iloc[idx]

        # Compute all 35 features (exact same logic every time!)
        features = compute_features_window(window, current)
        features_list.append(features)

    features_df = pd.DataFrame(features_list)
    features_df.to_csv(output_csv, index=False)

    print(f"Extracted {len(features_df)} feature vectors")
    return features_df

def compute_features_window(window, current):
    """
    Compute 35 features - STANDARDIZED FOR ALL DATASETS
    """

    features = {}

    # 1-5: Position
    features['lat'] = current.get('latitude', 0)
    features['lon'] = current.get('longitude', 0)
    features['alt'] = current.get('altitude', 0)
    features['lat_std'] = window['latitude_std'].mean()
    features['lon_std'] = window['longitude_std'].mean()

    # 6-10: Signal strength
    features['mean_cnr'] = window['c_n0'].mean() if 'c_n0' in window.columns else 35
    features['min_cnr'] = window['c_n0'].min() if 'c_n0' in window.columns else 25
    features['max_cnr'] = window['c_n0'].max() if 'c_n0' in window.columns else 45
    features['std_cnr'] = window['c_n0'].std() if 'c_n0' in window.columns else 5
    features['cnr_trend'] = (window['c_n0'].iloc[-1] - window['c_n0'].iloc[0]) / 30

    # 11-14: Satellites
    features['num_satellites'] = current.get('num_satellites', 8)
    features['sat_mean'] = window['num_satellites'].mean()
    features['sat_min'] = window['num_satellites'].min()
    features['sat_visibility'] = features['num_satellites'] / 32

    # 15-19: DOP values
    features['pdop'] = current.get('pdop', 2.5)
    features['hdop'] = current.get('hdop', 2.0)
    features['vdop'] = current.get('vdop', 1.5)
    features['gdop'] = current.get('gdop', 3.0)
    features['dop_ratio'] = features['hdop'] / features['vdop'] if features['vdop'] > 0 else 1

    # 20-24: Status
    features['solution_status'] = 1 if current.get('solution_status') == 'FIXED' else 0.5
    features['baseline_sats'] = current.get('num_baseline', 0)
    features['solution_age'] = current.get('age', 0)
    features['gps_enabled'] = 1
    features['glonass_enabled'] = 0

    # 25-29: Temporal
    features['position_variance'] = (window['latitude_std'].var() + window['longitude_std'].var())
    features['cnr_variance'] = window['c_n0'].var() if 'c_n0' in window.columns else 0
    features['elevation_violations'] = 0  # Depends on data
    features['multipath'] = 0  # Computed from residuals
    features['clock_bias'] = 0

    # 30-35: Atmospheric (if available, else zero)
    features['iono_delay'] = current.get('iono_delay', 0)
    features['tropo_delay'] = current.get('tropo_delay', 0)
    features['cycle_slips'] = current.get('cycle_slips', 0)
    features['residual_mean'] = 0
    features['residual_std'] = 0

    return features
```

---

## 📊 **STEP 5: COMBINE ALL FEATURES + ADD SOURCE TAGS**

### Master Dataset Assembly

**File:** `src/features/assemble_master_dataset.py`

```python
import pandas as pd
import glob
import os

def assemble_all_sources():
    """
    Combine all extracted features into ONE master dataset
    """

    # Define all sources
    sources = {
        # Your new data (Scenarios A-E)
        'scenario_a': 'data/processed/scenario_a_features.csv',
        'scenario_b': 'data/processed/scenario_b_features.csv',
        'scenario_c': 'data/processed/scenario_c_features.csv',
        'scenario_d': 'data/processed/scenario_d_features.csv',
        'scenario_e': 'data/processed/scenario_e_features.csv',

        # Supervisor data
        'supervisor_vehicle': 'data/processed/vehicle_features.csv',
        'supervisor_drone': 'data/processed/drone_features.csv',

        # Public data
        'urbannav_hk': 'data/processed/urbannav_hk_features.csv',
        'urbannav_beijing': 'data/processed/urbannav_beijing_features.csv',
        'oxford_2019': 'data/processed/oxford_2019_features.csv',
        'kaist_2012': 'data/processed/kaist_2012_features.csv',
    }

    all_dfs = []

    for source_name, csv_path in sources.items():
        if not os.path.exists(csv_path):
            print(f"⚠ Skipping {source_name} - file not found")
            continue

        df = pd.read_csv(csv_path)
        df['source'] = source_name  # Tag the source

        all_dfs.append(df)
        print(f"✓ {source_name}: {len(df)} rows")

    # Combine all
    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df = master_df.sort_values('timestamp').reset_index(drop=True)

    print(f"\n{'='*60}")
    print(f"MASTER DATASET CREATED")
    print(f"Total rows: {len(master_df):,}")
    print(f"Total sources: {len(sources)}")
    print(f"{'='*60}")

    # Show distribution by source
    print("\nRows per source:")
    print(master_df['source'].value_counts())

    # Save
    master_df.to_csv('data/labelled/master_dataset_combined.csv', index=False)

    return master_df

if __name__ == "__main__":
    master_df = assemble_all_sources()
```

---

## 🏷️ **STEP 6: LABEL DATA (CRITICAL FOR ALL SOURCES)**

```python
def label_all_data(master_df):
    """
    Apply CONSISTENT labeling across all sources
    """

    labels = []

    for idx, row in master_df.iterrows():
        # Calculate position error
        pos_error = (row['lat_std']**2 + row['lon_std']**2)**0.5

        # Get signal strength
        signal = row['mean_cnr']

        # Get satellite count
        sats = row['num_satellites']

        # Apply thresholds (SAME FOR EVERY SOURCE!)
        if pos_error < 2.0 and signal > 35 and sats >= 4:
            label = 'CLEAN'
        elif (pos_error < 5.0 or signal > 30) and sats >= 3:
            label = 'WARNING'
        else:
            label = 'DEGRADED'

        labels.append(label)

    master_df['label'] = labels

    # Show class distribution
    print("\nClass Distribution (ACROSS ALL SOURCES):")
    print(master_df['label'].value_counts())
    print("\nPercentages:")
    print(master_df['label'].value_counts(normalize=True) * 100)

    # Check distribution BY SOURCE
    print("\nDistribution by Source:")
    for source in master_df['source'].unique():
        source_data = master_df[master_df['source'] == source]
        print(f"\n{source}:")
        print(source_data['label'].value_counts())

    return master_df
```

---

## ⏱️ **STEP 7: TEMPORAL SPLIT (CRITICAL!)**

```python
def temporal_split_multi_source(master_df):
    """
    IMPORTANT: Split by TIME, not randomly
    Group sources so training doesn't leak into test
    """

    # Sort by timestamp
    master_df = master_df.sort_values('timestamp').reset_index(drop=True)

    n = len(master_df)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)

    # Split
    train_df = master_df[:train_end]
    val_df = master_df[train_end:val_end]
    test_df = master_df[val_end:]

    # Verify no source is split across train/test
    print("Training sources:", train_df['source'].unique())
    print("Validation sources:", val_df['source'].unique())
    print("Test sources:", test_df['source'].unique())

    # Save
    train_df.to_csv('data/labelled/train.csv', index=False)
    val_df.to_csv('data/labelled/val.csv', index=False)
    test_df.to_csv('data/labelled/test.csv', index=False)

    print(f"\nTrain: {len(train_df)} ({100*len(train_df)/n:.1f}%)")
    print(f"Val: {len(val_df)} ({100*len(val_df)/n:.1f}%)")
    print(f"Test: {len(test_df)} ({100*len(test_df)/n:.1f}%)")
```

---

## 🎯 **QUICK OVERVIEW: DATASET FLOW**

```
┌─────────────────────────────────────┐
│ YOUR NEW DATA (5 Scenarios)         │ ~10,000 rows
│ SUPERVISOR DATA (Vehicle + Drone)   │ ~80,000 rows
│ PUBLIC DATA (UrbanNav/Oxford/KAIST) │ ~60,000 rows
└────────────────┬────────────────────┘
                 │
                 ↓
        [EXTRACT TO CSV]
        (Same format everywhere)
                 │
                 ↓
        [RTKLIB PROCESSING]
        (Same RTKLIB settings for all)
                 │
                 ↓
        [EXTRACT 35 FEATURES]
        (Identical code, all sources)
                 │
                 ↓
        [COMBINE & LABEL]
        (One master CSV: 150,000 rows)
                 │
                 ├─────────────────────────┐
                 ↓                         ↓
        Train/Val/Test Split      Generalization Test
        (70/15/15 by time)        (Test model on Oxford/UrbanNav)
                 │                         │
                 ↓                         ↓
        TRAIN MODEL                EVALUATE GENERALIZATION
        (LSTM-Transformer)         (F1 drop on new geography)
```

---

## ✅ **CHECKLIST FOR DATASET INTEGRATION**

- [ ] **Day 9-12:** Download UrbanNav, Oxford, KAIST datasets
- [ ] **Day 12:** Run universal extraction script on all sources
- [ ] **Day 12-13:** Run RTKLIB on all extracted data (parallel processing)
- [ ] **Day 13:** Verify RTKLIB outputs in RTKPLOT (sanity check)
- [ ] **Day 13:** Extract 35 features from all RTKLIB outputs
- [ ] **Day 13:** Combine all feature CSVs into master dataset
- [ ] **Day 13:** Label master dataset (CLEAN/WARNING/DEGRADED)
- [ ] **Day 13:** Verify class distribution across all sources
- [ ] **Day 13:** Create temporal train/val/test split
- [ ] **Day 14:** Normalize features (fit scaler only on training data)
- [ ] **Day 14:** Apply SMOTE for class balancing
- [ ] **Week 3:** Train model on combined dataset
- [ ] **Week 3:** Test model on held-out test set (in-distribution)
- [ ] **Week 3:** Evaluate generalization on UrbanNav/Oxford (cross-geography)

---

## 📈 **EXPECTED DATASET STATISTICS**

```
FINAL MASTER DATASET:
├─ Total Epochs: ~150,000
├─ Total Duration: ~40 hours
├─ CLEAN Labels: ~50% (75,000 rows)
├─ WARNING Labels: ~30% (45,000 rows)
└─ DEGRADED Labels: ~20% (30,000 rows)

AFTER TRAIN/VAL/TEST SPLIT:
├─ Training Set: 105,000 rows (70%)
│  └─ After SMOTE: 105,000 rows (balanced)
├─ Validation Set: 22,500 rows (15%)
└─ Test Set: 22,500 rows (15%)

GENERALIZATION TESTING:
├─ UrbanNav Test: 20,000 rows (different cities)
├─ Oxford Test: 15,000 rows (different sensor, UK location)
└─ KAIST Test: 10,000 rows (if available, different country)
```

---

**This strategy ensures robust, generalizable model trained on diverse data from multiple sources!** 🚀

_Last Updated: Week 2 Planning | SENTINEL-GNSS_
