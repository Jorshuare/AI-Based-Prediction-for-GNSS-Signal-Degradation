"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, WS_URL, type WsMessage } from "@/lib/api";
import { BEIHANG } from "@/lib/colors";
import { horizonProbs, type Horizon, type Prediction, type Scenario } from "@/lib/types";
import { Card, ChartCard, SectionTitle, useMounted } from "@/lib/ui";
import { FiRadio, FiNavigation, FiBarChart2 } from "@/lib/icons";
import Header from "@/components/Header";
import Tabs, { type TabDef } from "@/components/Tabs";
import ControlBar from "@/components/ControlBar";
import SignalGauge from "@/components/SignalGauge";
import ProbabilityBars from "@/components/ProbabilityBars";
import TimeSeriesChart from "@/components/TimeSeriesChart";
import TrajectoryMap from "@/components/TrajectoryMap";
import MetricsGrid from "@/components/MetricsGrid";
import AlarmCenter, { type Alarm } from "@/components/AlarmCenter";
import EkfPanel from "@/components/EkfPanel";
import FusionView from "@/components/FusionView";
import PlainStatus from "@/components/PlainStatus";
import LeadTimeCard from "@/components/LeadTimeCard";

const MAX_POINTS = 400;

const TABS: TabDef[] = [
  { id: "live", label: "Live Prediction", icon: <FiRadio size={16} /> },
  { id: "fusion", label: "Sensor Fusion", icon: <FiNavigation size={16} /> },
  { id: "analytics", label: "Analytics", icon: <FiBarChart2 size={16} /> },
];

export default function Dashboard() {
  const mounted = useMounted();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState<string>("");
  const [horizon, setHorizon] = useState<Horizon>(5);
  const [tab, setTab] = useState("live");
  const [minimal, setMinimal] = useState(false);
  const [connected, setConnected] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(15);
  const [stream, setStream] = useState<Prediction[]>([]);
  const [total, setTotal] = useState(0);
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [warnEpoch, setWarnEpoch] = useState<number | null>(null);
  const [onsetEpoch, setOnsetEpoch] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const speedRef = useRef(speed); speedRef.current = speed;

  useEffect(() => {
    api.scenarios().then((s) => {
      setScenarios(s);
      if (s.length) setScenario(s[0].id);
    }).catch(() => {});
  }, []);

  const onEpoch = useCallback((p: Prediction) => {
    const t = new Date().toLocaleTimeString();
    // lead-time bookkeeping (set once): +30 s head warns early, +5 s head = imminent
    if (p.pred_30s === "DEGRADED") setWarnEpoch((w) => (w == null ? p.window : w));
    if (p.pred_5s === "DEGRADED") setOnsetEpoch((o) => (o == null ? p.window : o));
    // natural-language alerts (no dashes)
    if (p.p_degraded_5s > 0.8) {
      const a: Alarm = { id: `${p.window}-c`, level: "CRITICAL", time: t,
        message: `GNSS degradation is imminent within 5 seconds (P=${(p.p_degraded_5s * 100).toFixed(0)}%). The system is handing off to inertial backup.` };
      setAlarms((prev) => [a, ...prev].slice(0, 6));
    } else if (p.p_degraded_15s > 0.6) {
      const a: Alarm = { id: `${p.window}-w`, level: "WARNING", time: t,
        message: `Signal degradation is likely within 15 seconds (P=${(p.p_degraded_15s * 100).toFixed(0)}%). Preparing backup sensors.` };
      setAlarms((prev) => [a, ...prev].slice(0, 6));
    }
  }, []);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => { setConnected(false); setPlaying(false); };
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      const msg: WsMessage = JSON.parse(ev.data);
      if (msg.type === "replay_start") {
        setStream([]); setTotal(msg.total); setPlaying(true);
        setAlarms([]); setWarnEpoch(null); setOnsetEpoch(null);
      } else if (msg.type === "epoch") {
        setStream((prev) => [...prev.slice(-(MAX_POINTS - 1)), msg.data]); onEpoch(msg.data);
      } else if (msg.type === "replay_end" || msg.type === "replay_stopped") setPlaying(false);
    };
    return () => ws.close();
  }, [onEpoch]);

  const play = useCallback(() => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN && scenario)
      ws.send(JSON.stringify({ type: "start_replay", scenario, speed: speedRef.current }));
  }, [scenario]);
  const stop = useCallback(() => { wsRef.current?.send(JSON.stringify({ type: "stop_replay" })); }, []);

  const current = stream.length ? stream[stream.length - 1] : null;
  const probs = current ? horizonProbs(current, horizon) : null;
  const pDeg = probs ? probs.degraded : 0;
  const conf = probs ? Math.max(probs.clean, probs.warning, probs.degraded) : undefined;
  const progress = total ? stream.length / total : 0;

  if (!mounted) return <div style={{ minHeight: "100vh", background: BEIHANG.mist }} />;

  return (
    <div style={{ background: BEIHANG.mist, minHeight: "100vh" }} className="flex flex-col">
      <Header minimal={minimal} onToggle={() => setMinimal((m) => !m)} connected={connected} />

      <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 md:px-6">
        <div className="mb-5"><Tabs tabs={TABS} active={tab} onChange={setTab} /></div>

        <AnimatePresence mode="wait">
          {tab === "live" && (
            <motion.div key="live" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }} className="flex flex-col gap-5">
              <ControlBar scenarios={scenarios} scenario={scenario} onScenario={setScenario}
                horizon={horizon} onHorizon={setHorizon} playing={playing} onPlay={play} onStop={stop}
                speed={speed} onSpeed={setSpeed} progress={progress} />

              {current && <PlainStatus pDeg={pDeg} horizon={horizon} />}

              {!minimal && <MetricsGrid data={stream} total={total} />}

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                <Card delay={0.05}>
                  <SectionTitle hint="The dial shows the chance that GPS will become unreliable within the selected look-ahead time. Green is safe, red is danger.">Live signal quality (+{horizon}s)</SectionTitle>
                  <div className="flex justify-center py-2"><SignalGauge pDegraded={pDeg} confidence={conf} /></div>
                </Card>
                <Card delay={0.1}>
                  <SectionTitle hint="The three possible states and how likely each is right now. CLEAN = good, WARNING = patchy, DEGRADED = unreliable.">Class probabilities (+{horizon}s)</SectionTitle>
                  {probs ? <div className="py-3"><ProbabilityBars probs={probs} /></div> : <Empty />}
                </Card>
                <Card delay={0.15}><AlarmCenter alarms={alarms} /></Card>
              </div>

              {!minimal && (
                <>
                  <Card><LeadTimeCard warnEpoch={warnEpoch} onsetEpoch={onsetEpoch} /></Card>
                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                    <ChartCard title="Vehicle trajectory (risk-coloured)" hint="The route driven so far. Each dot is coloured by how risky the GPS signal was at that spot.">
                      <TrajectoryMap data={stream} />
                    </ChartCard>
                    <ChartCard title="P(DEGRADED) timeline"
                      hint="History of the degradation probability for all three look-ahead times. Hover anywhere to read the exact values. The dashed lines are the warning thresholds."
                      csvRows={stream as unknown as Record<string, unknown>[]} csvName="sentinel_predictions.csv">
                      <TimeSeriesChart data={stream} />
                    </ChartCard>
                  </div>
                </>
              )}
            </motion.div>
          )}

          {tab === "fusion" && (
            <motion.div key="fusion" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}>
              <FusionView minimal={minimal} />
            </motion.div>
          )}

          {tab === "analytics" && (
            <motion.div key="analytics" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }} className="flex flex-col gap-5">
              <Card>
                <SectionTitle hint="A study on real Tokyo data: which positioning filter best survives GPS blackouts, and when it pays to distrust the satellites.">Adaptive sensor-fusion analytics</SectionTitle>
                <EkfPanel />
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="px-6 py-5 text-center text-xs font-medium text-white" style={{ background: BEIHANG.primary }}>
        SENTINEL-GNSS © 2026 · Beihang University · RCSSTEAP · Predictive GNSS degradation &amp; adaptive sensor fusion
      </footer>
    </div>
  );
}

function Empty() {
  return <div className="flex h-44 items-center justify-center text-sm" style={{ color: BEIHANG.slate }}>Press Play to start the live stream.</div>;
}
