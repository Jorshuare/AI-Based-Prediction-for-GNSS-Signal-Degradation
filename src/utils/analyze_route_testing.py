"""
Analyze GNSS Logger route testing data and identify scenarios
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from pathlib import Path

# Create output directory
output_dir = Path("route_planning/analysis")
output_dir.mkdir(exist_ok=True)


def parse_gnss_log(filepath):
    """Parse Geo++ GNSS Logger file and extract Fix records"""
    fixes = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('Fix,'):
                parts = line.split(',')
                try:
                    # Handle empty fields: skip records with missing critical data
                    if len(parts) < 15:
                        continue

                    # Only process records with valid accuracy (not empty)
                    if not parts[6] or not parts[8]:  # accuracy or unix_time_ms missing
                        continue

                    accuracy = float(parts[6])
                    unix_time = int(parts[8])

                    fix_data = {
                        'provider': parts[1],
                        'latitude': float(parts[2]),
                        'longitude': float(parts[3]),
                        'altitude': float(parts[4]) if parts[4] else 0,
                        'speed_mps': float(parts[5]) if parts[5] else 0,
                        'accuracy_meters': accuracy,
                        'bearing': float(parts[7]) if parts[7] else 0,
                        'unix_time_ms': unix_time,
                        'speed_accuracy': float(parts[9]) if (len(parts) > 9 and parts[9]) else 0,
                        'bearing_accuracy': float(parts[10]) if (len(parts) > 10 and parts[10]) else 0,
                        'num_used_signals': int(float(parts[14])) if (len(parts) > 14 and parts[14]) else 0,
                        'vertical_accuracy': float(parts[12]) if (len(parts) > 12 and parts[12]) else accuracy,
                    }
                    fixes.append(fix_data)
                except (ValueError, IndexError):
                    # Silently skip parse errors
                    continue

    return pd.DataFrame(fixes) if fixes else pd.DataFrame()


def parse_status_records(filepath):
    """Parse Status records from GNSS Logger file to get C/N0 values"""
    status_records = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('Status,'):
                parts = line.split(',')
                try:
                    status_data = {
                        'unix_time_ms': int(parts[1]),
                        'signal_count': int(parts[2]),
                        'constellation': parts[4],
                        'svid': int(parts[5]),
                        'cn0_dbhz': float(parts[7]),
                        'azimuth': float(parts[8]),
                        'elevation': float(parts[9]),
                        'used_in_fix': parts[10].lower() == 'true' if len(parts) > 10 else False,
                    }
                    status_records.append(status_data)
                except (ValueError, IndexError):
                    continue

    return pd.DataFrame(status_records) if status_records else pd.DataFrame()


def analyze_file(filepath, filename):
    """Analyze a single GNSS log file"""
    print(f"\n{'='*60}")
    print(f"Analyzing: {filename}")
    print(f"{'='*60}")

    # Parse data
    fixes_df = parse_gnss_log(filepath)
    status_df = parse_status_records(filepath)

    if fixes_df.empty:
        print("No Fix records found!")
        return None

    print(f"Number of Fix records: {len(fixes_df)}")
    print(
        f"Duration: {(fixes_df['unix_time_ms'].max() - fixes_df['unix_time_ms'].min()) / 1000:.1f} seconds")

    # Calculate statistics
    stats = {
        'filename': filename,
        'start_time': datetime.fromtimestamp(fixes_df['unix_time_ms'].min() / 1000),
        'end_time': datetime.fromtimestamp(fixes_df['unix_time_ms'].max() / 1000),
        'duration_sec': (fixes_df['unix_time_ms'].max() - fixes_df['unix_time_ms'].min()) / 1000,
        'num_fixes': len(fixes_df),
        'avg_accuracy': fixes_df['accuracy_meters'].mean(),
        'min_accuracy': fixes_df['accuracy_meters'].min(),
        'max_accuracy': fixes_df['accuracy_meters'].max(),
        'avg_satellites': fixes_df['num_used_signals'].mean(),
        'min_satellites': fixes_df['num_used_signals'].min(),
        'max_satellites': fixes_df['num_used_signals'].max(),
        'latitude_range': fixes_df['latitude'].max() - fixes_df['latitude'].min(),
        'longitude_range': fixes_df['longitude'].max() - fixes_df['longitude'].min(),
        'position_std': np.sqrt(
            (fixes_df['latitude'] - fixes_df['latitude'].mean())**2 +
            (fixes_df['longitude'] - fixes_df['longitude'].mean())**2
        ).mean(),
    }

    # Get C/N0 statistics from Status records
    if not status_df.empty:
        stats['avg_cn0'] = status_df['cn0_dbhz'].mean()
        stats['min_cn0'] = status_df['cn0_dbhz'].min()
        stats['max_cn0'] = status_df['cn0_dbhz'].max()
        stats['total_signals'] = len(status_df)
    else:
        stats['avg_cn0'] = None
        stats['min_cn0'] = None
        stats['max_cn0'] = None
        stats['total_signals'] = 0

    # Print statistics
    print(f"\nGPS Position Statistics:")
    print(
        f"  Lat range: {fixes_df['latitude'].min():.6f} to {fixes_df['latitude'].max():.6f}")
    print(
        f"  Lon range: {fixes_df['longitude'].min():.6f} to {fixes_df['longitude'].max():.6f}")
    print(f"  Position std dev: {stats['position_std']:.6f} degrees")

    print(f"\nAccuracy Statistics:")
    print(f"  Average: {stats['avg_accuracy']:.2f}m")
    print(f"  Min: {stats['min_accuracy']:.2f}m")
    print(f"  Max: {stats['max_accuracy']:.2f}m")

    print(f"\nSatellite Count:")
    print(f"  Average: {stats['avg_satellites']:.1f}")
    print(f"  Min: {int(stats['min_satellites'])}")
    print(f"  Max: {int(stats['max_satellites'])}")

    if stats['avg_cn0']:
        print(f"\nSignal Strength (C/N0):")
        print(f"  Average: {stats['avg_cn0']:.1f} dB-Hz")
        print(f"  Min: {stats['min_cn0']:.1f} dB-Hz")
        print(f"  Max: {stats['max_cn0']:.1f} dB-Hz")
        print(f"  Total signals tracked: {stats['total_signals']}")

    # Identify scenario characteristics
    print(f"\nScenario Characteristics:")
    accuracy_variance = stats['max_accuracy'] - stats['min_accuracy']
    sat_variance = stats['max_satellites'] - stats['min_satellites']

    if stats['avg_cn0']:
        print(
            f"  Accuracy variance: {accuracy_variance:.2f}m (range: {stats['min_accuracy']:.1f}-{stats['max_accuracy']:.1f}m)")
        print(
            f"  Satellite variance: {sat_variance} (range: {int(stats['min_satellites'])}-{int(stats['max_satellites'])})")
        print(
            f"  Position movement: {stats['position_std']:.6f} degrees (~{stats['position_std']*111000:.0f}m)")
        print(
            f"  Signal strength: {stats['avg_cn0']:.1f} dB-Hz (suggests CLEAN={stats['avg_cn0'] > 35}, WARNING={30 < stats['avg_cn0'] <= 35})")

    return {
        'fixes': fixes_df,
        'status': status_df,
        'stats': stats
    }


def identify_scenario(stats):
    """Identify which scenario a test represents based on characteristics"""
    avg_acc = stats['avg_accuracy']
    max_acc = stats['max_accuracy']
    min_sat = stats['min_satellites']
    avg_sat = stats['avg_satellites']
    avg_cn0 = stats['avg_cn0']
    duration = stats['duration_sec']
    pos_std = stats['position_std']

    if not avg_cn0:  # Not enough C/N0 data
        return "UNKNOWN"

    # Scenario A: Instant Blockage - Quick drop to 0 satellites, high accuracy before
    if min_sat == 0 and avg_sat < 2 and duration < 60:
        return "SCENARIO_A_INSTANT_BLOCKAGE"

    # Scenario D: Open Sky - High satellites, good accuracy, high signal strength
    if avg_sat >= 10 and avg_acc < 10 and avg_cn0 > 38:
        return "SCENARIO_D_OPEN_SKY"

    # Scenario B: Urban Canyon - Gradual degradation, multiple position changes
    if 5 < avg_sat < 10 and 10 < avg_acc < 30 and avg_cn0 > 28 and pos_std > 0.0001:
        return "SCENARIO_B_URBAN_CANYON"

    # Scenario C: Partial Blockage - Consistent moderate performance
    if 5 < avg_sat < 9 and 5 < avg_acc < 15 and 30 < avg_cn0 < 36 and pos_std < 0.00005:
        return "SCENARIO_C_PARTIAL_BLOCKAGE"

    # Scenario E: Approaching Blockage - Smooth degradation, moving position
    if 5 < avg_sat < 11 and 10 < avg_acc < 25 and 25 < avg_cn0 < 35 and pos_std > 0.00008:
        return "SCENARIO_E_APPROACHING_BLOCKAGE"

    # Fallback classifications
    if max_acc > 50:
        return "SCENARIO_A_or_E (HIGH_ACCURACY_VARIANCE)"
    if avg_sat < 5:
        return "SCENARIO_A_or_C (LOW_SATELLITES)"
    if avg_acc < 5:
        return "SCENARIO_D_or_C (GOOD_ACCURACY)"

    return "UNKNOWN"


def create_visualizations(data_dict):
    """Create comprehensive visualizations for all scenarios"""

    # Figure 1: Time series of all metrics
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))
    fig.suptitle('GNSS Route Testing - All Scenarios Time Series',
                 fontsize=14, fontweight='bold')

    for idx, (filename, data) in enumerate(data_dict.items()):
        if data is None:
            continue
        fixes = data['fixes']
        status = data['status']
        stats = data['stats']

        # Normalize time to seconds from start
        time_sec = (fixes['unix_time_ms'] - fixes['unix_time_ms'].min()) / 1000

        # Plot 1: Accuracy over time
        axes[0].plot(time_sec, fixes['accuracy_meters'], marker='o', markersize=3,
                     label=f"{filename.replace('gnss_log_', '').replace('.txt', '')}", alpha=0.7)

        # Plot 2: Satellite count over time
        axes[1].plot(time_sec, fixes['num_used_signals'],
                     marker='s', markersize=3, alpha=0.7)

        # Plot 3: C/N0 (signal strength) over time
        if not status.empty:
            status_time = (status['unix_time_ms'] -
                           fixes['unix_time_ms'].min()) / 1000
            axes[2].scatter(status_time, status['cn0_dbhz'], s=10, alpha=0.5)

        # Plot 4: Position drift (lat/lon)
        axes[3].scatter(fixes['longitude'], fixes['latitude'],
                        s=20, alpha=0.5, label=filename)

    axes[0].set_ylabel('Accuracy (meters)', fontweight='bold')
    axes[0].set_ylim([0, axes[0].get_ylim()[1]])
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].set_ylabel('# Satellites Used', fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel('C/N0 (dB-Hz)', fontweight='bold')
    axes[2].axhline(y=35, color='r', linestyle='--',
                    alpha=0.5, label='CLEAN threshold')
    axes[2].axhline(y=30, color='orange', linestyle='--',
                    alpha=0.5, label='WARNING threshold')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8)

    axes[3].set_xlabel('Longitude', fontweight='bold')
    axes[3].set_ylabel('Latitude', fontweight='bold')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'route_testing_timeseries.png',
                dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: route_testing_timeseries.png")
    plt.close()

    # Figure 2: Summary comparison bar chart
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('GNSS Route Testing - Scenario Comparison',
                 fontsize=14, fontweight='bold')

    filenames = []
    avg_accuracies = []
    avg_satellites = []
    avg_cn0s = []
    scenarios = []

    for filename, data in data_dict.items():
        if data is None:
            continue
        filenames.append(filename.replace(
            'gnss_log_2026_04_30_', '').replace('.txt', ''))
        stats = data['stats']
        avg_accuracies.append(stats['avg_accuracy'])
        avg_satellites.append(stats['avg_satellites'])
        if stats['avg_cn0']:
            avg_cn0s.append(stats['avg_cn0'])
        else:
            avg_cn0s.append(0)
        scenario = identify_scenario(stats)
        scenarios.append(scenario)

    x = np.arange(len(filenames))
    width = 0.6

    # Accuracy comparison
    colors = ['red' if 'OPEN_SKY' in s else 'green' if s !=
              'UNKNOWN' else 'gray' for s in scenarios]
    axes[0, 0].bar(x, avg_accuracies, width, color=colors, alpha=0.7)
    axes[0, 0].set_ylabel('Accuracy (meters)', fontweight='bold')
    axes[0, 0].set_title('Average Position Accuracy')
    axes[0, 0].axhline(y=5, color='g', linestyle='--',
                       alpha=0.5, label='Good (<5m)')
    axes[0, 0].axhline(y=10, color='orange', linestyle='--',
                       alpha=0.5, label='Fair (<10m)')
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(True, alpha=0.3, axis='y')

    # Satellite count comparison
    axes[0, 1].bar(x, avg_satellites, width, color=colors, alpha=0.7)
    axes[0, 1].set_ylabel('# Satellites', fontweight='bold')
    axes[0, 1].set_title('Average Satellite Count')
    axes[0, 1].axhline(y=10, color='g', linestyle='--',
                       alpha=0.5, label='Good (≥10)')
    axes[0, 1].axhline(y=4, color='r', linestyle='--',
                       alpha=0.5, label='Poor (<4)')
    axes[0, 1].legend(fontsize=8)
    axes[0, 1].grid(True, alpha=0.3, axis='y')

    # C/N0 comparison
    axes[1, 0].bar(x, avg_cn0s, width, color=colors, alpha=0.7)
    axes[1, 0].set_ylabel('C/N0 (dB-Hz)', fontweight='bold')
    axes[1, 0].set_title('Average Signal Strength')
    axes[1, 0].axhline(y=35, color='g', linestyle='--',
                       alpha=0.5, label='CLEAN (≥35)')
    axes[1, 0].axhline(y=30, color='orange', linestyle='--',
                       alpha=0.5, label='WARNING (30-35)')
    axes[1, 0].axhline(y=20, color='r', linestyle='--',
                       alpha=0.5, label='DEGRADED (<30)')
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(True, alpha=0.3, axis='y')

    # Scenario identification
    axes[1, 1].axis('off')
    scenario_text = "Scenario Identification:\n" + "\n".join([
        f"{fn}: {sc.replace('_', ' ')}"
        for fn, sc in zip(filenames, scenarios)
    ])
    axes[1, 1].text(0.1, 0.5, scenario_text, fontsize=10, family='monospace',
                    verticalalignment='center', bbox=dict(boxstyle='round',
                                                          facecolor='wheat', alpha=0.5))

    plt.xticks(x, filenames, rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'route_testing_comparison.png',
                dpi=300, bbox_inches='tight')
    print(f"[OK] Saved: route_testing_comparison.png")
    plt.close()


# Main analysis
# Set UTF-8 encoding for output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("\n" + "="*60)
print("GNSS ROUTE TESTING DATA ANALYSIS")
print("="*60)

# Find all GNSS log files
log_dir = Path("route_planning/phone_a")
log_files = sorted(log_dir.glob("gnss_log_*.txt"))

print(f"\nFound {len(log_files)} GNSS log files")

data_dict = {}
all_stats = []

for log_file in log_files:
    result = analyze_file(str(log_file), log_file.name)
    if result:
        data_dict[log_file.name] = result
        scenario = identify_scenario(result['stats'])
        result['stats']['identified_scenario'] = scenario
        all_stats.append(result['stats'])

# Create summary report
print("\n" + "="*60)
print("SCENARIO IDENTIFICATION SUMMARY")
print("="*60)

scenarios_found = {}
for stats in all_stats:
    scenario = stats['identified_scenario']
    if scenario not in scenarios_found:
        scenarios_found[scenario] = []
    scenarios_found[scenario].append(stats['filename'])

for scenario, files in sorted(scenarios_found.items()):
    print(f"\n{scenario}:")
    for f in files:
        print(f"  - {f}")

# Check if all 5 scenarios are covered
expected_scenarios = {
    'SCENARIO_A_INSTANT_BLOCKAGE',
    'SCENARIO_B_URBAN_CANYON',
    'SCENARIO_C_PARTIAL_BLOCKAGE',
    'SCENARIO_D_OPEN_SKY',
    'SCENARIO_E_APPROACHING_BLOCKAGE'
}

found_scenarios = set(scenarios_found.keys())
print("\n" + "="*60)
print("COVERAGE ANALYSIS")
print("="*60)

missing = expected_scenarios - found_scenarios
if missing:
    print(f"\n[WARNING] MISSING SCENARIOS ({len(missing)}):")
    for s in missing:
        print(f"  - {s}")
else:
    print("\n[SUCCESS] ALL 5 SCENARIOS COVERED!")

# Create visualizations
print("\n" + "="*60)
print("GENERATING VISUALIZATIONS")
print("="*60)

create_visualizations(data_dict)

print(f"\n[OK] All visualizations saved to: {output_dir}")
print(f"\nNext step: Review visualizations and prepare for real receiver data collection")
