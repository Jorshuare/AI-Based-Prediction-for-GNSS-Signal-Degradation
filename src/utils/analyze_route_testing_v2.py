"""
Analyze GNSS Logger route testing data and generate clear charts per dataset.
"""

import argparse
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("route_planning/analysis")
DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)

# Set UTF-8 encoding for console output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


def parse_gnss_log(filepath):
    """Parse GNSS Logger file and extract Fix and Status records"""
    fixes = []
    status_records = []

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()

            # Parse Fix records
            if line.startswith('Fix,'):
                parts = line.split(',')
                try:
                    if len(parts) < 15:
                        continue
                    if not parts[6] or not parts[8]:
                        continue

                    accuracy = float(parts[6])
                    unix_time = int(parts[8])

                    fix_data = {
                        'provider': parts[1],
                        'latitude': float(parts[2]),
                        'longitude': float(parts[3]),
                        'accuracy_meters': accuracy,
                        'unix_time_ms': unix_time,
                        'num_used_signals': int(float(parts[14])) if (len(parts) > 14 and parts[14]) else 0,
                    }
                    fixes.append(fix_data)
                except (ValueError, IndexError):
                    continue

            # Parse Status records (for C/N0 data)
            elif line.startswith('Status,'):
                parts = line.split(',')
                try:
                    status_data = {
                        'unix_time_ms': int(parts[1]),
                        'cn0_dbhz': float(parts[7]),
                    }
                    status_records.append(status_data)
                except (ValueError, IndexError):
                    continue

    return pd.DataFrame(fixes), pd.DataFrame(status_records)


def describe_log_file(log_file):
    """Return a readable label and time token from a GNSS log file name."""

    stem = log_file.stem
    if "gnss_log_" in stem:
        prefix, suffix = stem.split("gnss_log_", 1)
        label = prefix.strip("_ -").replace("_", " ").replace("-", " ")
        time_token = suffix.split("_")[-3:]
        time_str = "_".join(time_token) if len(
            time_token) == 3 else suffix.replace("_", " ")
        return label, time_str

    return "", stem


def create_individual_charts(log_dir, chart_output_dir, dataset_name):
    """Create individual detailed charts for each location"""

    log_files = sorted(log_dir.glob("gnss_log_*.txt"))
    if not log_files:
        log_files = sorted(log_dir.glob("*gnss_log_*.txt"))

    for idx, log_file in enumerate(log_files, 1):
        print(f"\nProcessing Location #{idx}: {log_file.name}")

        fixes_df, status_df = parse_gnss_log(str(log_file))

        if fixes_df.empty:
            print(f"  [WARNING] No Fix records found")
            continue

        # Get time info
        label, time_str = describe_log_file(log_file)
        duration_sec = (fixes_df['unix_time_ms'].max() -
                        fixes_df['unix_time_ms'].min()) / 1000
        avg_accuracy = fixes_df['accuracy_meters'].mean()

        # Calculate C/N0 stats
        cn0_stats = ""
        if not status_df.empty:
            avg_cn0 = status_df['cn0_dbhz'].mean()
            min_cn0 = status_df['cn0_dbhz'].min()
            max_cn0 = status_df['cn0_dbhz'].max()
            cn0_stats = f"C/N0: {avg_cn0:.1f} dB-Hz (range: {min_cn0:.1f}-{max_cn0:.1f})"

        # Create figure with 3 subplots
        fig = plt.figure(figsize=(18, 14))
        gs = fig.add_gridspec(3, 1, hspace=0.35, top=0.94, bottom=0.08)

        # Main title
        location_title = f"Location #{idx}: {time_str}"
        if label:
            location_title = f"Location #{idx}: {label} ({time_str})"
        title = f'{location_title}\nDuration: {duration_sec:.1f}s | Accuracy: {avg_accuracy:.2f}m | {cn0_stats}'
        fig.suptitle(title, fontsize=18, fontweight='bold', y=0.98)

        # Normalize time to seconds
        time_sec = (fixes_df['unix_time_ms'] -
                    fixes_df['unix_time_ms'].min()) / 1000

        # ===== SUBPLOT 1: Position Accuracy vs Time =====
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(time_sec, fixes_df['accuracy_meters'], color='#1f77b4', linewidth=2.5,
                 marker='o', markersize=5, label='Position Accuracy', zorder=3)
        ax1.fill_between(
            time_sec, 0, fixes_df['accuracy_meters'], alpha=0.25, color='#1f77b4')

        ax1.axhline(y=2, color='green', linestyle='--',
                    linewidth=2.5, alpha=0.8, label='CLEAN threshold (2m)')
        ax1.axhline(y=5, color='orange', linestyle='--',
                    linewidth=2.5, alpha=0.8, label='WARNING threshold (5m)')
        ax1.axhline(y=10, color='red', linestyle='--', linewidth=2.5,
                    alpha=0.8, label='DEGRADED threshold (10m)')

        ax1.set_ylabel('Position Accuracy (meters)',
                       fontsize=13, fontweight='bold')
        ax1.set_xlim([time_sec.min(), time_sec.max()])
        ax1.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
        ax1.legend(loc='upper left', fontsize=11, framealpha=0.95)
        ax1.set_title('Chart 1: Position Accuracy Over Time',
                      fontsize=13, fontweight='bold', pad=12)
        ax1.tick_params(labelsize=11)

        # ===== SUBPLOT 2: C/N0 (Signal Strength) vs Time =====
        ax2 = fig.add_subplot(gs[1])

        if not status_df.empty:
            status_time = (status_df['unix_time_ms'] -
                           fixes_df['unix_time_ms'].min()) / 1000

            # Color code by signal quality
            colors = []
            for cn0 in status_df['cn0_dbhz']:
                if cn0 >= 35:
                    colors.append('green')
                elif cn0 >= 30:
                    colors.append('orange')
                else:
                    colors.append('red')

            ax2.scatter(status_time, status_df['cn0_dbhz'], c=colors, s=60, alpha=0.6,
                        edgecolors='black', linewidth=0.8, zorder=3, label='C/N0 values')

            # Add trend line if enough data
            if len(status_time) > 2:
                z = np.polyfit(status_time, status_df['cn0_dbhz'], 2)
                p = np.poly1d(z)
                trend_x = np.linspace(
                    status_time.min(), status_time.max(), 100)
                ax2.plot(trend_x, p(trend_x), "b-", linewidth=2.5,
                         alpha=0.7, label='Trend', zorder=2)

            # Add threshold lines
            ax2.axhline(y=35, color='green', linestyle='--',
                        linewidth=2.5, alpha=0.8, label='CLEAN (>=35)')
            ax2.axhline(y=30, color='orange', linestyle='--',
                        linewidth=2.5, alpha=0.8, label='WARNING (30-35)')
            ax2.axhline(y=25, color='red', linestyle='--',
                        linewidth=2.5, alpha=0.8, label='DEGRADED (25-30)')

            ax2.set_ylabel('Signal Strength C/N0 (dB-Hz)',
                           fontsize=13, fontweight='bold')
            ax2.set_xlim([time_sec.min(), time_sec.max()])
            ax2.set_ylim([max(0, status_df['cn0_dbhz'].min() - 5),
                         status_df['cn0_dbhz'].max() + 5])
            ax2.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
            ax2.legend(loc='upper left', fontsize=11, framealpha=0.95)
            ax2.set_title('Chart 2: Signal Strength (C/N0) vs Time - CRITICAL FOR AI MODEL',
                          fontsize=13, fontweight='bold', pad=12, color='darkred')
            ax2.tick_params(labelsize=11)

        # ===== SUBPLOT 3: GPS Position Trajectory =====
        ax3 = fig.add_subplot(gs[2])

        # Create scatter with time coloring
        scatter = ax3.scatter(fixes_df['longitude'], fixes_df['latitude'],
                              c=time_sec, cmap='viridis', s=80, alpha=0.7,
                              edgecolors='black', linewidth=0.8, zorder=3)

        # Draw trajectory line
        ax3.plot(fixes_df['longitude'], fixes_df['latitude'],
                 'k-', alpha=0.2, linewidth=1, zorder=1)

        # Mark start and end points
        ax3.scatter(fixes_df['longitude'].iloc[0], fixes_df['latitude'].iloc[0],
                    color='green', s=300, marker='o', edgecolors='black', linewidth=2.5,
                    label='START', zorder=5)
        ax3.scatter(fixes_df['longitude'].iloc[-1], fixes_df['latitude'].iloc[-1],
                    color='red', s=300, marker='s', edgecolors='black', linewidth=2.5,
                    label='END', zorder=5)

        ax3.set_xlabel('Longitude', fontsize=13, fontweight='bold')
        ax3.set_ylabel('Latitude', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
        ax3.legend(loc='upper left', fontsize=11, framealpha=0.95)
        ax3.set_title('Chart 3: GPS Position Trajectory',
                      fontsize=13, fontweight='bold', pad=12)
        ax3.tick_params(labelsize=11)

        # Add colorbar for time
        cbar = plt.colorbar(scatter, ax=ax3, orientation='vertical', pad=0.02)
        cbar.set_label('Time (seconds)', fontsize=11, fontweight='bold')

        # Save figure
        file_parts = [f"Location_{idx:02d}"]
        if label:
            file_parts.append(label.replace(" ", "_"))
        file_parts.append(time_str)
        output_file = chart_output_dir / f'{"_".join(file_parts)}_DETAILED.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        print(f"  [OK] Saved: {output_file.name}")

        plt.close(fig)

        # Print location summary
        print(f"  Location #{idx} Summary:")
        print(f"    - Duration: {duration_sec:.1f} seconds")
        print(
            f"    - Accuracy: {avg_accuracy:.2f}m (min: {fixes_df['accuracy_meters'].min():.2f}m, max: {fixes_df['accuracy_meters'].max():.2f}m)")
        if not status_df.empty:
            print(
                f"    - Signal (C/N0): {avg_cn0:.1f} dB-Hz (range: {min_cn0:.1f}-{max_cn0:.1f})")
        print(f"    - GPS Fixes: {len(fixes_df)}")
        print(f"    - Position movement: {fixes_df['latitude'].max()-fixes_df['latitude'].min():.6f}° lat, "
              f"{fixes_df['longitude'].max()-fixes_df['longitude'].min():.6f}° lon")


def create_comparison_chart(log_dir, chart_output_dir, dataset_name):
    """Create comparison chart showing all locations' C/N0 trends together"""

    log_files = sorted(log_dir.glob("gnss_log_*.txt"))
    if not log_files:
        log_files = sorted(log_dir.glob("*gnss_log_*.txt"))

    # Colors for each location
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1',
              '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(
        16, 12), gridspec_kw={'height_ratios': [2, 1]})

    location_stats = []

    # Collect data from all locations
    for idx, log_file in enumerate(log_files):
        fixes_df, status_df = parse_gnss_log(str(log_file))

        if fixes_df.empty or status_df.empty:
            continue

        label, time_str = describe_log_file(log_file)
        display_name = time_str if not label else f"{label} ({time_str})"

        # Normalize time within each location
        status_time = (status_df['unix_time_ms'] -
                       fixes_df['unix_time_ms'].min()) / 1000
        cn0_data = status_df['cn0_dbhz'].values

        # Plot trend
        if len(status_time) > 2:
            z = np.polyfit(status_time, cn0_data, 2)
            p = np.poly1d(z)
            trend_x = np.linspace(status_time.min(), status_time.max(), 100)
            ax1.plot(trend_x, p(trend_x), linewidth=2.5, alpha=0.8,
                     color=colors[idx % len(colors)], label=f'Location #{idx+1} ({display_name})', zorder=3)

        # Plot scatter points (lighter)
        ax1.scatter(status_time, cn0_data, color=colors[idx % len(colors)], s=40, alpha=0.4,
                    edgecolors='none', zorder=2)

        # Calculate stats
        avg_cn0 = cn0_data.mean()
        duration = (fixes_df['unix_time_ms'].max() -
                    fixes_df['unix_time_ms'].min()) / 1000
        location_stats.append({
            'location': idx + 1,
            'time': display_name,
            'duration': duration,
            'avg_cn0': avg_cn0,
            'min_cn0': cn0_data.min(),
            'max_cn0': cn0_data.max(),
            'num_fixes': len(fixes_df)
        })

    # Configure first subplot (C/N0 trends)
    ax1.axhline(y=35, color='green', linestyle='--', linewidth=2,
                alpha=0.7, label='CLEAN (>=35 dB-Hz)')
    ax1.axhline(y=30, color='orange', linestyle='--', linewidth=2,
                alpha=0.7, label='WARNING (30-35 dB-Hz)')
    ax1.axhline(y=25, color='red', linestyle='--', linewidth=2,
                alpha=0.7, label='DEGRADED (25-30 dB-Hz)')
    ax1.axhline(y=10, color='darkred', linestyle='--',
                linewidth=2, alpha=0.7, label='SEVERE (<10 dB-Hz)')

    ax1.fill_between([ax1.get_xlim()[0], ax1.get_xlim()[1]],
                     35, 60, alpha=0.1, color='green', label='_nolegend_')
    ax1.fill_between([ax1.get_xlim()[0], ax1.get_xlim()[1]],
                     30, 35, alpha=0.1, color='orange', label='_nolegend_')
    ax1.fill_between([ax1.get_xlim()[0], ax1.get_xlim()[1]],
                     0, 30, alpha=0.1, color='red', label='_nolegend_')

    ax1.set_ylabel('Signal Strength C/N0 (dB-Hz)',
                   fontsize=13, fontweight='bold')
    ax1.set_title(f'COMPARISON: C/N0 Signal Strength Trends - {dataset_name}',
                  fontsize=15, fontweight='bold', pad=15, color='darkblue')
    ax1.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
    ax1.legend(loc='best', fontsize=10, framealpha=0.95, ncol=2)
    ax1.set_ylim([0, 50])
    ax1.tick_params(labelsize=11)

    # Configure second subplot (statistics table)
    ax2.axis('off')

    # Create table data
    table_data = []
    table_data.append(['Loc', 'Time', 'Duration', 'Avg C/N0',
                      'Range', 'Fixes', 'Scenario'])

    scenarios = {
        1: 'Reference',
        2: 'Skipped',
        3: 'Instant Blockage',
        4: 'Degradation',
        5: 'Extreme',
        6: 'Blockage Cycles',
        7: 'Severe+Diverse'
    }

    for stat in location_stats:
        loc_num = stat['location']
        table_data.append([
            f"#{loc_num}",
            stat['time'],
            f"{stat['duration']:.0f}s",
            f"{stat['avg_cn0']:.1f}",
            f"{stat['min_cn0']:.1f}-{stat['max_cn0']:.1f}",
            f"{stat['num_fixes']}",
            scenarios.get(loc_num, 'TBD')
        ])

    # Create table
    table = ax2.table(cellText=table_data, cellLoc='center', loc='center',
                      colWidths=[0.07, 0.22, 0.12, 0.12, 0.15, 0.1, 0.18])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # Style header row
    for i in range(7):
        table[(0, i)].set_facecolor('#4ECDC4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Color code data rows
    for i, stat in enumerate(location_stats, start=1):
        for j in range(7):
            if stat['avg_cn0'] >= 35:
                table[(i, j)].set_facecolor('#E8F8F5')
            elif stat['avg_cn0'] >= 30:
                table[(i, j)].set_facecolor('#FEF5E7')
            else:
                table[(i, j)].set_facecolor('#FADBD8')

    fig.suptitle(f'Route Testing Comparison Analysis - {dataset_name}',
                 fontsize=16, fontweight='bold', y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_file = chart_output_dir / 'ALL_LOCATIONS_COMPARISON.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"[OK] Saved comparison chart: ALL_LOCATIONS_COMPARISON.png")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze GNSS logger route testing data.")
    parser.add_argument("log_dir", nargs="?", default="route_planning/phone_a")
    parser.add_argument("output_dir", nargs="?",
                        default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--dataset-name", dest="dataset_name", default=None)
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    chart_output_dir = Path(args.output_dir)
    chart_output_dir.mkdir(parents=True, exist_ok=True)
    dataset_name = args.dataset_name or log_dir.name

    print("\n" + "="*70)
    print("GNSS ROUTE TESTING - INDIVIDUAL LOCATION ANALYSIS")
    print("="*70)

    if not log_dir.exists():
        print(f"ERROR: Data directory not found: {log_dir}")
        return

    log_files = list(log_dir.glob("gnss_log_*.txt"))
    if not log_files:
        log_files = list(log_dir.glob("*gnss_log_*.txt"))
    print(f"\nFound {len(log_files)} GNSS log files")
    print(f"Input directory: {log_dir}")
    print(f"Output directory: {chart_output_dir}")

    # Create individual charts
    create_individual_charts(log_dir, chart_output_dir, dataset_name)

    # Create comparison chart
    print("\n" + "-"*70)
    print("Generating comparison chart...")
    create_comparison_chart(log_dir, chart_output_dir, dataset_name)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nAll charts saved to: {chart_output_dir}")
    print("\nGenerated files:")
    print("  - Location_01...DETAILED.png through Location_##...DETAILED.png")
    print("  - ALL_LOCATIONS_COMPARISON.png")
    print("\nNext steps:")
    print("1. Review ALL_LOCATIONS_COMPARISON.png to see all C/N0 trends together")
    print("2. Review individual Location charts for detailed analysis")
    print("3. Plan real receiver deployment based on chart patterns")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
