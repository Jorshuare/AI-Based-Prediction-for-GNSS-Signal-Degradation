"use client";

/**
 * SENTINEL-GNSS Dashboard Main Component
 * Real-time GNSS degradation prediction visualization
 *
 * Features:
 * - Live prediction streams (P(DEGRADED) at +5/15/30s)
 * - Interactive signal quality indicators
 * - EKF trajectory map
 * - Confidence metrics & analytics
 * - Alarm/notification system
 * - Publication-ready design (Beihang colors)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';

// Components (will be created separately)
// import MapComponent from '@/components/MapComponent';
// import PredictionCard from '@/components/PredictionCard';
// import MetricsPanel from '@/components/MetricsPanel';
// import AlarmCenter from '@/components/AlarmCenter';

// Beihang color palette
const COLORS = {
  primaryBlue: '#003360',
  secondaryBlue: '#344E7F',
  accentYellow: '#BCB245',
  warningOrange: '#FF6B35',
  successGreen: '#2ECC71',
  darkGray: '#2C3E50',
  lightGray: '#ECF0F1',
  white: '#FFFFFF',
};

interface Prediction {
  timestamp: string;
  lat: number;
  lon: number;
  p_clean_5s: number;
  p_warning_5s: number;
  p_degraded_5s: number;
  p_clean_15s: number;
  p_warning_15s: number;
  p_degraded_15s: number;
  p_clean_30s: number;
  p_warning_30s: number;
  p_degraded_30s: number;
  predicted_class_5s: 'CLEAN' | 'WARNING' | 'DEGRADED';
  predicted_class_15s: 'CLEAN' | 'WARNING' | 'DEGRADED';
  predicted_class_30s: 'CLEAN' | 'WARNING' | 'DEGRADED';
  confidence_5s: number;
  confidence_15s: number;
  confidence_30s: number;
}

interface Metrics {
  n_epochs: number;
  mean_p_degraded_5s: number;
  max_p_degraded_5s: number;
  degraded_count_5s: number;
  clean_count_5s: number;
  warning_count_5s: number;
  model_latency_ms: number;
  ekf_status: string;
  last_update: string;
}

export default function Dashboard() {
  // State
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [selectedHorizon, setSelectedHorizon] = useState<5 | 15 | 30>(5);
  const [alarms, setAlarms] = useState<Array<{id: string; type: string; message: string}>>([]);
  const metricsUpdateInterval = useRef<NodeJS.Timeout | null>(null);

  // WebSocket connection
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const websocket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'prediction') {
        setPredictions((prev) => [...prev.slice(-999), message.data]); // Keep last 1000
        checkForAlarms(message.data);
      } else if (message.type === 'metrics') {
        setMetrics(message.data);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  // Poll metrics periodically
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        setMetrics(data);
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
      }
    };

    metricsUpdateInterval.current = setInterval(fetchMetrics, 1000);

    return () => {
      if (metricsUpdateInterval.current) {
        clearInterval(metricsUpdateInterval.current);
      }
    };
  }, []);

  // Alarm logic
  const checkForAlarms = useCallback((prediction: Prediction) => {
    const newAlarms: typeof alarms = [];

    if (
      prediction.predicted_class_5s === 'DEGRADED' &&
      prediction.p_degraded_5s > 0.8
    ) {
      newAlarms.push({
        id: `${prediction.timestamp}-critical`,
        type: 'CRITICAL',
        message: `⚠️ CRITICAL: GNSS degradation predicted in 5 seconds (P=${(prediction.p_degraded_5s * 100).toFixed(1)}%)`,
      });
    } else if (
      prediction.predicted_class_5s === 'WARNING' &&
      prediction.p_degraded_5s > 0.5
    ) {
      newAlarms.push({
        id: `${prediction.timestamp}-warning`,
        type: 'WARNING',
        message: `⚠️ WARNING: GNSS signal degradation expected in 5 seconds`,
      });
    }

    setAlarms((prev) => {
      const updated = [...newAlarms, ...prev];
      return updated.slice(0, 5); // Keep last 5 alarms
    });
  }, []);

  // Get current prediction
  const currentPrediction = predictions.length > 0 ? predictions[predictions.length - 1] : null;

  // Get color based on signal quality
  const getSignalColor = (pDegraded: number) => {
    if (pDegraded < 0.3) return COLORS.successGreen;
    if (pDegraded < 0.7) return COLORS.warningOrange;
    return COLORS.warningOrange;
  };

  const getSignalLabel = (pDegraded: number) => {
    if (pDegraded < 0.3) return 'CLEAN';
    if (pDegraded < 0.7) return 'WARNING';
    return 'DEGRADED';
  };

  // Get relevant prediction data for selected horizon
  const getHorizonData = (pred: Prediction, horizon: 5 | 15 | 30) => {
    switch (horizon) {
      case 5:
        return {
          pDegraded: pred.p_degraded_5s,
          pClean: pred.p_clean_5s,
          pWarning: pred.p_warning_5s,
          predictedClass: pred.predicted_class_5s,
          confidence: pred.confidence_5s,
        };
      case 15:
        return {
          pDegraded: pred.p_degraded_15s,
          pClean: pred.p_clean_15s,
          pWarning: pred.p_warning_15s,
          predictedClass: pred.predicted_class_15s,
          confidence: pred.confidence_15s,
        };
      case 30:
        return {
          pDegraded: pred.p_degraded_30s,
          pClean: pred.p_clean_30s,
          pWarning: pred.p_warning_30s,
          predictedClass: pred.predicted_class_30s,
          confidence: pred.confidence_30s,
        };
    }
  };

  const horizonData = currentPrediction ? getHorizonData(currentPrediction, selectedHorizon) : null;

  return (
    <div style={{ backgroundColor: COLORS.lightGray, minHeight: '100vh' }}>
      {/* Header */}
      <header
        style={{
          backgroundColor: COLORS.primaryBlue,
          color: COLORS.white,
          padding: '20px 40px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <h1 style={{ margin: '0 0 10px 0', fontSize: '28px', fontWeight: 'bold' }}>
            🛰️ SENTINEL-GNSS Dashboard
          </h1>
          <p style={{ margin: '0', fontSize: '14px', opacity: 0.9 }}>
            Real-time GNSS signal degradation prediction for autonomous vehicles
          </p>

          {/* Connection Status */}
          <div style={{ marginTop: '15px', display: 'flex', gap: '20px', alignItems: 'center' }}>
            <span
              style={{
                display: 'inline-block',
                width: '12px',
                height: '12px',
                backgroundColor: isConnected ? COLORS.successGreen : '#E74C3C',
                borderRadius: '50%',
                animation: isConnected ? 'pulse 2s infinite' : 'none',
              }}
            ></span>
            <span style={{ fontSize: '13px' }}>
              {isConnected ? '✓ Connected' : '✗ Disconnected'}
            </span>

            {metrics && (
              <span style={{ fontSize: '13px', marginLeft: 'auto' }}>
                Status: <strong>{metrics.ekf_status}</strong> | Last update:{' '}
                {new Date(metrics.last_update).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1400px', margin: '30px auto', padding: '0 20px' }}>
        {/* Alarms */}
        {alarms.length > 0 && (
          <div
            style={{
              backgroundColor: '#FDE8E8',
              border: `2px solid ${COLORS.warningOrange}`,
              borderRadius: '8px',
              padding: '15px',
              marginBottom: '20px',
            }}
          >
            {alarms.map((alarm) => (
              <div
                key={alarm.id}
                style={{
                  color: COLORS.warningOrange,
                  fontSize: '14px',
                  fontWeight: 'bold',
                  marginBottom: '8px',
                }}
              >
                {alarm.message}
              </div>
            ))}
          </div>
        )}

        {/* Current Prediction Card */}
        {currentPrediction && horizonData && (
          <div
            style={{
              backgroundColor: COLORS.white,
              borderRadius: '12px',
              padding: '30px',
              marginBottom: '30px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: '0', color: COLORS.primaryBlue, fontSize: '22px', fontWeight: 'bold' }}>
                Current Signal Quality
              </h2>

              {/* Horizon Selector */}
              <div style={{ display: 'flex', gap: '10px' }}>
                {[5, 15, 30].map((h) => (
                  <button
                    key={h}
                    onClick={() => setSelectedHorizon(h as 5 | 15 | 30)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor:
                        selectedHorizon === h ? COLORS.accentYellow : COLORS.lightGray,
                      color: selectedHorizon === h ? COLORS.white : COLORS.darkGray,
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      fontSize: '13px',
                      transition: 'all 0.3s ease',
                    }}
                  >
                    +{h}s
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px' }}>
              {/* Large Gauge */}
              <div style={{ textAlign: 'center' }}>
                <div
                  style={{
                    width: '200px',
                    height: '200px',
                    borderRadius: '50%',
                    backgroundColor: getSignalColor(horizonData.pDegraded),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 20px',
                    boxShadow: `0 0 30px ${getSignalColor(horizonData.pDegraded)}`,
                  }}
                >
                  <div style={{ textAlign: 'center', color: COLORS.white }}>
                    <div style={{ fontSize: '48px', fontWeight: 'bold' }}>
                      {(horizonData.pDegraded * 100).toFixed(1)}%
                    </div>
                    <div style={{ fontSize: '14px', opacity: 0.9 }}>P(DEGRADED)</div>
                  </div>
                </div>
                <div style={{ marginTop: '20px' }}>
                  <div
                    style={{
                      fontSize: '24px',
                      fontWeight: 'bold',
                      color: COLORS.primaryBlue,
                      marginBottom: '10px',
                    }}
                  >
                    {getSignalLabel(horizonData.pDegraded)}
                  </div>
                  <div style={{ fontSize: '13px', color: COLORS.darkGray }}>
                    Confidence: {(horizonData.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Probability Breakdown */}
              <div>
                <h3
                  style={{
                    margin: '0 0 20px 0',
                    color: COLORS.primaryBlue,
                    fontSize: '16px',
                    fontWeight: 'bold',
                  }}
                >
                  Prediction Breakdown
                </h3>

                {[
                  { label: 'CLEAN', prob: horizonData.pClean, color: COLORS.successGreen },
                  { label: 'WARNING', prob: horizonData.pWarning, color: COLORS.warningOrange },
                  { label: 'DEGRADED', prob: horizonData.pDegraded, color: '#E74C3C' },
                ].map(({ label, prob, color }) => (
                  <div key={label} style={{ marginBottom: '15px' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '5px',
                        fontSize: '13px',
                        fontWeight: 'bold',
                      }}
                    >
                      <span>{label}</span>
                      <span style={{ color }}>{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div
                      style={{
                        width: '100%',
                        height: '8px',
                        backgroundColor: COLORS.lightGray,
                        borderRadius: '4px',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${prob * 100}%`,
                          height: '100%',
                          backgroundColor: color,
                          transition: 'width 0.3s ease',
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Metrics Panel */}
        {metrics && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: '20px',
              marginBottom: '30px',
            }}
          >
            {[
              {
                label: 'Total Epochs',
                value: metrics.n_epochs,
                icon: '📊',
              },
              {
                label: 'Mean P(Degraded)',
                value: `${(metrics.mean_p_degraded_5s * 100).toFixed(1)}%`,
                icon: '📈',
              },
              {
                label: 'Max P(Degraded)',
                value: `${(metrics.max_p_degraded_5s * 100).toFixed(1)}%`,
                icon: '⚠️',
              },
              {
                label: 'Model Latency',
                value: `${metrics.model_latency_ms.toFixed(2)}ms`,
                icon: '⚡',
              },
              {
                label: 'CLEAN Epochs',
                value: metrics.clean_count_5s,
                icon: '✅',
                color: COLORS.successGreen,
              },
              {
                label: 'DEGRADED Epochs',
                value: metrics.degraded_count_5s,
                icon: '❌',
                color: COLORS.warningOrange,
              },
            ].map((metric) => (
              <div
                key={metric.label}
                style={{
                  backgroundColor: COLORS.white,
                  borderRadius: '12px',
                  padding: '20px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  borderLeft: `4px solid ${metric.color || COLORS.accentYellow}`,
                }}
              >
                <div style={{ fontSize: '20px', marginBottom: '10px' }}>
                  {metric.icon}
                </div>
                <div
                  style={{
                    fontSize: '13px',
                    color: COLORS.darkGray,
                    marginBottom: '8px',
                  }}
                >
                  {metric.label}
                </div>
                <div
                  style={{
                    fontSize: '24px',
                    fontWeight: 'bold',
                    color: COLORS.primaryBlue,
                  }}
                >
                  {metric.value}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Prediction History */}
        {predictions.length > 0 && (
          <div
            style={{
              backgroundColor: COLORS.white,
              borderRadius: '12px',
              padding: '30px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <h2
              style={{
                margin: '0 0 20px 0',
                color: COLORS.primaryBlue,
                fontSize: '18px',
                fontWeight: 'bold',
              }}
            >
              Prediction History (Last 10)
            </h2>

            <div
              style={{
                maxHeight: '300px',
                overflowY: 'auto',
              }}
            >
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '12px',
                }}
              >
                <thead>
                  <tr
                    style={{
                      backgroundColor: COLORS.lightGray,
                      borderBottom: `2px solid ${COLORS.secondaryBlue}`,
                    }}
                  >
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold' }}>
                      Timestamp
                    </th>
                    <th style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>
                      Lat / Lon
                    </th>
                    <th style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>
                      P(D) +5s
                    </th>
                    <th style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>
                      Class +5s
                    </th>
                    <th style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>
                      Confidence
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.slice(-10).reverse().map((pred, idx) => {
                    const horizData = getHorizonData(pred, 5);
                    return (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: `1px solid ${COLORS.lightGray}`,
                          backgroundColor: idx % 2 === 0 ? COLORS.white : '#F9FAFB',
                        }}
                      >
                        <td style={{ padding: '10px' }}>
                          {new Date(pred.timestamp).toLocaleTimeString()}
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center', fontSize: '11px' }}>
                          {pred.lat.toFixed(4)} / {pred.lon.toFixed(4)}
                        </td>
                        <td
                          style={{
                            padding: '10px',
                            textAlign: 'center',
                            fontWeight: 'bold',
                            color: getSignalColor(horizData.pDegraded),
                          }}
                        >
                          {(horizData.pDegraded * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>
                          {horizData.predictedClass}
                        </td>
                        <td style={{ padding: '10px', textAlign: 'center' }}>
                          {(horizData.confidence * 100).toFixed(0)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer
        style={{
          backgroundColor: COLORS.primaryBlue,
          color: COLORS.white,
          padding: '20px',
          textAlign: 'center',
          marginTop: '50px',
          fontSize: '12px',
        }}
      >
        <p style={{ margin: '0' }}>
          SENTINEL-GNSS © 2026 | Beihang University | Real-time GNSS Degradation Prediction
        </p>
      </footer>

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
}
