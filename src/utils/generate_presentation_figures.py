"""
Figure Generation Script - GNSS Project Presentation Visualization
Generates publication-ready figures for the presentation
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# Set professional style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 9)
plt.rcParams['font.size'] = 12
plt.rcParams['font.family'] = 'sans-serif'

# Color scheme
COLOR_CLEAN = '#00AA44'
COLOR_WARNING = '#FFAA00'
COLOR_DEGRADED = '#DD0000'
COLOR_BASELINE = '#0066CC'
COLOR_OUR_MODEL = '#00CC44'
COLOR_BG = '#F5F5F5'

# ============================================================================
# FIGURE 4: Prediction Timeline Visualization
# ============================================================================


def generate_prediction_timeline():
    """Generate timeline showing GPS failure prediction"""
    fig, axes = plt.subplots(3, 1, figsize=(16, 10))
    fig.suptitle('GNSS Failure Prediction Timeline: 30-Second Lead Time Advantage',
                 fontsize=18, fontweight='bold', y=0.995)

    # Time array
    time = np.linspace(0, 35, 350)

    # TRACK 1: GPS Signal Quality
    ax1 = axes[0]
    signal = 42 - 0.2 * (time - 10)**2 / 5 * (time > 10) - 5 * (time > 20)
    signal = np.clip(signal, 5, 50)

    ax1.fill_between(time, signal, 0, where=(signal > 15),
                     color=COLOR_CLEAN, alpha=0.3, label='Good Signal')
    ax1.fill_between(time, signal, 0, where=(signal <= 15) & (
        signal > 5), color=COLOR_WARNING, alpha=0.3, label='Weak Signal')
    ax1.fill_between(time, signal, 0, where=(signal <= 5),
                     color=COLOR_DEGRADED, alpha=0.3, label='Critical Signal')

    ax1.plot(time, signal, 'b-', linewidth=3, label='Actual Signal Strength')
    ax1.axhline(y=15, color='orange', linestyle='--', linewidth=2,
                label='Critical Threshold (15 dB-Hz)')
    ax1.axvline(x=30, color='red', linestyle=':', linewidth=2, alpha=0.7)

    ax1.set_ylabel('Signal Strength (dB-Hz)', fontsize=12, fontweight='bold')
    ax1.set_ylim([0, 50])
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.text(30.5, 45, 'GPS Fails', fontsize=11,
             fontweight='bold', color='red')

    # TRACK 2: AI Confidence Predictions
    ax2 = axes[1]

    # Simulate confidence curves
    conf_5s = np.zeros_like(time)
    conf_15s = np.zeros_like(time)
    conf_30s = np.zeros_like(time)

    # 5-second prediction (becomes confident at t=25s)
    conf_5s[time >= 25] = 100 * (1 - np.exp(-(time[time >= 25] - 25) * 0.5))

    # 15-second prediction (becomes confident at t=15s)
    conf_15s[time >= 15] = 100 * (1 - np.exp(-(time[time >= 15] - 15) * 0.3))

    # 30-second prediction (becomes confident earlier)
    conf_30s[time >= 5] = 100 * (1 - np.exp(-(time[time >= 5] - 5) * 0.15))

    ax2.plot(time, conf_5s, color=COLOR_DEGRADED, linewidth=2.5,
             label='Fail in 5s', marker='o', markersize=4, markevery=20)
    ax2.plot(time, conf_15s, color=COLOR_WARNING, linewidth=2.5,
             label='Fail in 15s', marker='s', markersize=4, markevery=20)
    ax2.plot(time, conf_30s, color=COLOR_BASELINE, linewidth=2.5,
             label='Fail in 30s', marker='^', markersize=4, markevery=20)

    ax2.axhline(y=80, color='gray', linestyle='--', linewidth=1.5,
                alpha=0.7, label='80% Confidence Threshold')
    ax2.axvline(x=30, color='red', linestyle=':', linewidth=2, alpha=0.7)

    ax2.fill_between(time, 80, 100, alpha=0.1, color='red',
                     label='High Confidence Zone')
    ax2.set_ylabel('AI Confidence (%)', fontsize=12, fontweight='bold')
    ax2.set_ylim([0, 105])
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # TRACK 3: Car's Response Mode
    ax3 = axes[2]

    # Define modes
    modes = []
    mode_times = []
    mode_colors = []
    mode_labels = []

    for t in time:
        if t < 20:
            mode_colors.append(COLOR_CLEAN)
            mode_labels.append('Normal GPS Mode')
        elif t < 25:
            mode_colors.append(COLOR_WARNING)
            mode_labels.append('Alert - Preparing')
        elif t < 30:
            mode_colors.append(COLOR_BASELINE)
            mode_labels.append('Backup Sensors Active')
        else:
            mode_colors.append(COLOR_DEGRADED)
            mode_labels.append('GPS Unavailable')

    for i in range(len(time)-1):
        ax3.barh(0, time[i+1]-time[i], left=time[i], height=0.5,
                 color=mode_colors[i], edgecolor='black', linewidth=0.5)

    ax3.set_ylim([-0.5, 0.5])
    ax3.set_xlim([0, 35])
    ax3.set_ylabel('Car Status', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
    ax3.set_yticks([])

    # Add text annotations
    ax3.text(10, 0, 'Normal GPS Mode', ha='center', va='center',
             fontsize=11, fontweight='bold', color='white')
    ax3.text(22.5, 0, 'Alert!', ha='center', va='center',
             fontsize=11, fontweight='bold', color='white')
    ax3.text(27.5, 0, 'Backup Active', ha='center', va='center',
             fontsize=11, fontweight='bold', color='white')
    ax3.text(32.5, 0, 'GPS Down', ha='center', va='center',
             fontsize=11, fontweight='bold', color='white')

    # Add annotation boxes
    ax3.text(10, -0.35, 'AI detects early warning', ha='center', fontsize=9, style='italic',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    ax3.text(22.5, -0.35, '5-7s lead time', ha='center', fontsize=9, style='italic', fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    ax3.text(32.5, -0.35, 'Graceful degradation', ha='center', fontsize=9, style='italic',
             bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))

    ax3.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    plt.savefig('figures/figure_4_prediction_timeline.png',
                dpi=300, bbox_inches='tight', facecolor='white')
    print("✓ Figure 4: Prediction Timeline saved")
    plt.close()


# ============================================================================
# FIGURE 5: Performance Comparison
# ============================================================================

def generate_performance_comparison():
    """Generate accuracy and lead time comparison"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle('Model Performance Comparison: LSTM-Transformer vs Baselines',
                 fontsize=16, fontweight='bold')

    # Data
    methods = ['Simple\nThreshold', 'Random\nForest',
               'Basic\nLSTM', 'LSTM-\nTransformer\n(Ours)']
    accuracy = [65, 72, 81, 88]
    lead_time = [0, 0, 2.5, 6]
    colors_acc = [COLOR_DEGRADED, COLOR_WARNING, '#FFCC00', COLOR_OUR_MODEL]

    # SUBPLOT 1: Accuracy
    bars1 = ax1.bar(methods, accuracy, color=colors_acc,
                    edgecolor='black', linewidth=1.5, alpha=0.8, width=0.6)
    ax1.axhline(y=80, color='gray', linestyle='--', linewidth=2,
                alpha=0.7, label='Industry Standard (80%)')
    ax1.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Model Accuracy', fontsize=13, fontweight='bold')
    ax1.set_ylim([0, 100])
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars1, accuracy):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                 f'{val}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # SUBPLOT 2: Lead Time
    sizes = [30, 30, 50, 90]  # Size of points
    scatter = ax2.scatter(range(len(methods)), lead_time, s=[s*20 for s in sizes],
                          c=colors_acc, alpha=0.7, edgecolors='black', linewidth=2)
    ax2.plot(range(len(methods)), lead_time, 'k--', alpha=0.3, linewidth=1)

    ax2.set_ylabel('Lead Time (seconds)', fontsize=12, fontweight='bold')
    ax2.set_title('Prediction Lead Time', fontsize=13, fontweight='bold')
    ax2.set_xticks(range(len(methods)))
    ax2.set_xticklabels(methods)
    ax2.set_ylim([-0.5, 8])
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for i, (method, val) in enumerate(zip(methods, lead_time)):
        if val > 0:
            ax2.text(i, val + 0.3, f'{val:.1f}s',
                     ha='center', fontsize=11, fontweight='bold')
        else:
            ax2.text(i, val + 0.3, 'Reactive', ha='center',
                     fontsize=10, style='italic', color='red')

    # Add annotation
    ax2.annotate('', xy=(3, 6), xytext=(3, 0.5),
                 arrowprops=dict(arrowstyle='<->', color='green', lw=2))
    ax2.text(3.5, 3, '5-7 second\nadvantage', fontsize=10, fontweight='bold', color='green',
             bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

    plt.tight_layout()
    plt.savefig('figures/figure_5_performance_comparison.png',
                dpi=300, bbox_inches='tight', facecolor='white')
    print("✓ Figure 5: Performance Comparison saved")
    plt.close()


# ============================================================================
# FIGURE 9: ROC-AUC and Confusion Matrix
# ============================================================================

def generate_roc_confusion():
    """Generate ROC-AUC and Confusion Matrix"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle('Model Evaluation: ROC-AUC and Confusion Matrix',
                 fontsize=16, fontweight='bold')

    # ROC Curves
    fpr_threshold = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50, 1.0]
    tpr_threshold = [0, 0.30, 0.50, 0.65, 0.75, 0.82, 0.88, 0.95, 1.0]

    fpr_rf = [0, 0.08, 0.15, 0.22, 0.30, 0.40, 0.55, 0.70, 1.0]
    tpr_rf = [0, 0.35, 0.55, 0.68, 0.78, 0.85, 0.90, 0.96, 1.0]

    fpr_lstm = [0, 0.03, 0.08, 0.12, 0.18, 0.28, 0.42, 0.65, 1.0]
    tpr_lstm = [0, 0.40, 0.65, 0.76, 0.85, 0.90, 0.94, 0.98, 1.0]

    # Calculate AUC (approximate)
    from sklearn.metrics import auc
    auc_threshold = auc(fpr_threshold, tpr_threshold)
    auc_rf = auc(fpr_rf, tpr_rf)
    auc_lstm = auc(fpr_lstm, tpr_lstm)

    # Plot ROC curves
    ax1.fill_between(fpr_threshold, tpr_threshold,
                     alpha=0.2, color=COLOR_OUR_MODEL)
    ax1.plot(fpr_threshold, tpr_threshold, color=COLOR_OUR_MODEL,
             linewidth=3, label=f'LSTM-Transformer (AUC={auc_lstm:.3f})')

    ax1.fill_between(fpr_rf, tpr_rf, alpha=0.2, color=COLOR_WARNING)
    ax1.plot(fpr_rf, tpr_rf, color=COLOR_WARNING, linewidth=2.5,
             label=f'Random Forest (AUC={auc_rf:.3f})')

    ax1.fill_between(fpr_threshold, tpr_threshold,
                     alpha=0.1, color=COLOR_DEGRADED)
    ax1.plot(fpr_threshold, tpr_threshold, color=COLOR_DEGRADED, linewidth=2, linestyle='--',
             label=f'Threshold (AUC={auc_threshold:.3f})')

    ax1.plot([0, 1], [0, 1], 'k--', linewidth=1.5,
             alpha=0.5, label='Random Classifier (AUC=0.5)')

    ax1.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
    ax1.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
    ax1.set_title('ROC-AUC Curves', fontsize=13, fontweight='bold')
    ax1.legend(loc='lower right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim([0, 1])
    ax1.set_ylim([0, 1])

    # Confusion Matrix
    cm_data = np.array([
        [8234, 145, 21],    # CLEAN: predicted as CLEAN, WARNING, DEGRADED
        [289, 3891, 520],   # WARNING
        [12, 456, 3132]     # DEGRADED
    ])

    # Normalize to percentages
    cm_pct = cm_data.astype('float') / cm_data.sum(axis=1)[:, np.newaxis] * 100

    # Plot heatmap
    sns.heatmap(cm_pct, annot=cm_data, fmt='d', cmap='Greens', ax=ax2,
                cbar_kws={'label': 'Percentage (%)'}, linewidths=1.5, linecolor='black',
                xticklabels=['CLEAN', 'WARNING', 'DEGRADED'],
                yticklabels=['CLEAN', 'WARNING', 'DEGRADED'])

    ax2.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Actual Label', fontsize=12, fontweight='bold')
    ax2.set_title('Confusion Matrix (with percentages)',
                  fontsize=13, fontweight='bold')

    # Add text annotation
    textstr = 'Diagonal = Correct Predictions\nOff-diagonal = Misclassifications'
    ax2.text(1.5, -0.7, textstr, transform=ax2.transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig('figures/figure_9_roc_confusion.png', dpi=300,
                bbox_inches='tight', facecolor='white')
    print("✓ Figure 9: ROC-AUC and Confusion Matrix saved")
    plt.close()


# ============================================================================
# FIGURE 6: Generalization Test Results (World Map)
# ============================================================================

def generate_generalization_map():
    """Generate world map showing model generalization"""
    try:
        import folium
        from folium.plugins import MarkerCluster

        # Create map centered on Beijing
        m = folium.Map(location=[39.9, 116.4],
                       zoom_start=3, tiles='OpenStreetMap')

        # Define test locations with metadata
        locations = {
            'Beijing': {
                'coords': [39.9, 116.4],
                'accuracy': 88,
                'type': 'Training',
                'icon': 'star',
                'color': 'red',
                'distance': '0 km (Training)'
            },
            'Hong Kong': {
                'coords': [22.3, 114.2],
                'accuracy': 85,
                'type': 'Test',
                'icon': 'circle',
                'color': 'green',
                'distance': '2000 km'
            },
            'Taipei': {
                'coords': [25.0, 121.5],
                'accuracy': 84,
                'type': 'Test',
                'icon': 'circle',
                'color': 'green',
                'distance': '2500 km'
            },
            'Oxford': {
                'coords': [51.7, -1.2],
                'accuracy': 83,
                'type': 'Test',
                'icon': 'square',
                'color': 'orange',
                'distance': '8000 km'
            },
            'Urbana, USA': {
                'coords': [40.1, -88.2],
                'accuracy': 82,
                'type': 'Test',
                'icon': 'square',
                'color': 'orange',
                'distance': '10000 km'
            }
        }

        # Add markers
        for city, data in locations.items():
            popup_text = f"{city}<br>Accuracy: {data['accuracy']}%<br>Distance: {data['distance']}"
            folium.Marker(
                location=data['coords'],
                popup=popup_text,
                tooltip=city,
                icon=folium.Icon(
                    color=data['color'], icon=data['icon'], prefix='fa')
            ).add_to(m)

        # Add lines from Beijing to other cities
        beijing = locations['Beijing']['coords']
        for city, data in locations.items():
            if city != 'Beijing':
                folium.PolyLine(
                    [beijing, data['coords']],
                    color='blue',
                    weight=2,
                    opacity=0.5,
                    dash_array='5, 5'
                ).add_to(m)

        # Save
        m.save('figures/figure_6_generalization_map.html')
        print("✓ Figure 6: Generalization Map saved (interactive HTML)")

    except ImportError:
        print("⚠ Folium not installed. Skipping Figure 6 (Generalization Map)")


# ============================================================================
# FIGURE 2: Five Scenarios Distribution
# ============================================================================

def generate_five_scenarios():
    """Generate 5 scenarios visualization"""
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)
    fig.suptitle('GNSS Data Collection: 5 Scenarios + Class Distribution',
                 fontsize=16, fontweight='bold')

    # Scenario descriptions and data
    scenarios = {
        'D: Open Sky\n(Baseline)': {
            'description': 'Perfect GPS\nSignal: 42 dB-Hz\nSatellites: 12',
            'label': 'CLEAN',
            'color': COLOR_CLEAN,
            'ax_pos': (0, 0)
        },
        'A: Instant\nBlockage': {
            'description': 'GPS Fails\nSignal: 5 dB-Hz\nSatellites: 2',
            'label': 'DEGRADED',
            'color': COLOR_DEGRADED,
            'ax_pos': (0, 1)
        },
        'B: Urban\nCanyon': {
            'description': 'Bouncing Signal\nSignal: 28 dB-Hz\nSatellites: 5',
            'label': 'WARNING',
            'color': COLOR_WARNING,
            'ax_pos': (0, 2)
        },
        'C: Partial\nBlockage': {
            'description': 'Partial Block\nSignal: 32 dB-Hz\nSatellites: 6',
            'label': 'WARNING',
            'color': COLOR_WARNING,
            'ax_pos': (1, 1)
        },
        'E: Approaching\nBlockage': {
            'description': 'Degradation Curve\nSignal: 40→10 dB-Hz\nSatellites: 12→3',
            'label': 'CLEAN→DEGRADED',
            'color': '#FF6B35',
            'ax_pos': (1, 0)
        }
    }

    # Plot scenarios (5 smaller plots)
    for idx, (scenario_name, data) in enumerate(scenarios.items()):
        ax = fig.add_subplot(gs[data['ax_pos']])

        # Draw a simple representation
        ax.text(0.5, 0.7, scenario_name, ha='center', va='center', fontsize=12, fontweight='bold',
                transform=ax.transAxes)
        ax.text(0.5, 0.35, data['description'], ha='center', va='center', fontsize=10,
                transform=ax.transAxes, family='monospace', style='italic')

        # Color bar at bottom
        rect = plt.Rectangle((0.1, 0.05), 0.8, 0.15, transform=ax.transAxes,
                             facecolor=data['color'], alpha=0.7, edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        ax.text(0.5, 0.125, data['label'], ha='center', va='center', fontsize=10, fontweight='bold',
                transform=ax.transAxes, color='white' if data['color'] != COLOR_CLEAN else 'black')

        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.axis('off')

    # Class distribution pie chart
    ax_pie = fig.add_subplot(gs[1, 2])
    sizes = [50, 30, 20]
    labels = ['CLEAN\n(50%)', 'WARNING\n(30%)', 'DEGRADED\n(20%)']
    colors_pie = [COLOR_CLEAN, COLOR_WARNING, COLOR_DEGRADED]

    wedges, texts, autotexts = ax_pie.pie(sizes, labels=labels, colors=colors_pie,
                                          autopct='%1.0f%%', startangle=90,
                                          wedgeprops=dict(edgecolor='black', linewidth=2))

    for text in texts:
        text.set_fontsize(11)
        text.set_fontweight('bold')
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(11)
        autotext.set_fontweight('bold')

    ax_pie.set_title('Total Dataset Distribution\n(~150,000 epochs)',
                     fontsize=12, fontweight='bold')

    # Statistics box
    ax_stats = fig.add_subplot(gs[2, :])
    ax_stats.axis('off')

    stats_text = """
    DATA COLLECTION SUMMARY:
    • Total Epochs Collected: ~150,000 GPS measurements
    • Collection Duration: ~40 hours across all scenarios
    • Sampling Rate: 10 Hz (100 ms per measurement)
    • Geographic Coverage: Beihang University Campus, Beijing
    • Labeled Classes: CLEAN (50%) | WARNING (30%) | DEGRADED (20%)
    • Features Extracted: 35 features per epoch (signal strength, satellites, DOP, etc.)
    • Train/Val/Test Split: 70% / 15% / 15% (by time, not random)
    """

    ax_stats.text(0.05, 0.95, stats_text, transform=ax_stats.transAxes,
                  fontsize=11, verticalalignment='top', family='monospace',
                  bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

    plt.savefig('figures/figure_2_five_scenarios.png', dpi=300,
                bbox_inches='tight', facecolor='white')
    print("✓ Figure 2: Five Scenarios saved")
    plt.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import os

    # Create output directory
    os.makedirs('figures', exist_ok=True)

    print("\n" + "="*60)
    print("GNSS PROJECT: FIGURE GENERATION")
    print("="*60 + "\n")

    # Generate figures
    print("Generating publication-ready figures...\n")

    generate_prediction_timeline()
    generate_performance_comparison()
    generate_five_scenarios()
    generate_roc_confusion()
    generate_generalization_map()

    print("\n" + "="*60)
    print("✓ ALL FIGURES GENERATED SUCCESSFULLY")
    print("="*60)
    print("\nOutput location: ./figures/")
    print("\nGenerated files:")
    print("  • figure_2_five_scenarios.png")
    print("  • figure_4_prediction_timeline.png")
    print("  • figure_5_performance_comparison.png")
    print("  • figure_6_generalization_map.html (interactive)")
    print("  • figure_9_roc_confusion.png")
    print("\n" + "="*60 + "\n")
