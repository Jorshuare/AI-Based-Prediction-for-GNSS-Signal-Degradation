"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, WS_URL, type WsMessage } from "@/lib/api";
import { BEIHANG } from "@/lib/colors";
import { horizonProbs, type Horizon, type Prediction, type Scenario } from "@/lib/types";
import { Card, ChartCard, SectionTitle, useMounted } from "@/lib/ui";
import { I18nProvider, useT } from "@/lib/i18n";
import { playBuzzer, primeAudio } from "@/lib/buzzer";
import { FiRadio, FiNavigation, FiBarChart2 } from "@/lib/icons";
import Header from "@/components/Header";
import Tabs, { type TabDef } from "@/components/Tabs";
import ControlBar from "@/components/ControlBar";
import SignalGauge from "@/components/SignalGauge";
import ProbabilityBars from "@/components/ProbabilityBars";
import TimeSeriesChart from "@/components/TimeSeriesChart";
import TrajectoryMap from "@/components/TrajectoryMap";
import MetricsGrid from "@/components/MetricsGrid";
import AlarmCenter, { type AlertEpisode } from "@/components/AlarmCenter";
import EkfPanel from "@/components/EkfPanel";
import FusionView from "@/components/FusionView";
import PlainStatus from "@/components/PlainStatus";
import LeadTimeCard from "@/components/LeadTimeCard";

const MAX_POINTS = 400;

export default function Dashboard() {
  return (
    <I18nProvider>
      <DashboardInner />
    </I18nProvider>
  );
}

function DashboardInner() {
  const { t } = useT();
  const mounted = useMounted();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState<string>("");
  const [horizon, setHorizon] = useState<Horizon>(5);
  const [tab, setTab] = useState("live");
  const [minimal, setMinimal] = useState(false);
  const [muted, setMuted] = useState(false);
  const [connected, setConnected] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(15);
  const [stream, setStream] = useState<Prediction[]>([]);
  const [total, setTotal] = useState(0);
  const [activeEp, setActiveEp] = useState<AlertEpisode | null>(null);
  const [history, setHistory] = useState<AlertEpisode[]>([]);
  const [warnEpoch, setWarnEpoch] = useState<number | null>(null);
  const [onsetEpoch, setOnsetEpoch] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const speedRef = useRef(speed); speedRef.current = speed;
  const mutedRef = useRef(muted); mutedRef.current = muted;
  const epRef = useRef<AlertEpisode | null>(null);

  const TABS: TabDef[] = [
    { id: "live", label: t("nav_live"), icon: <FiRadio size={16} /> },
    { id: "fusion", label: t("nav_fusion"), icon: <FiNavigation size={16} /> },
    { id: "analytics", label: t("nav_analytics"), icon: <FiBarChart2 size={16} /> },
  ];

  useEffect(() => {
    api.scenarios().then((s) => {
      setScenarios(s);
      if (s.length) setScenario(s[0].id);
    }).catch(() => {});
  }, []);

  const onEpoch = useCallback((p: Prediction) => {
    if (p.pred_30s === "DEGRADED") setWarnEpoch((w) => (w == null ? p.window : w));
    if (p.pred_5s === "DEGRADED") setOnsetEpoch((o) => (o == null ? p.window : o));

    // Coalesce consecutive same-level epochs into ONE episode (seamless, no flooding).
    const level: AlertEpisode["level"] | null =
      p.p_degraded_5s > 0.8 ? "CRITICAL" : p.p_degraded_15s > 0.6 ? "WARNING" : null;
    const pVal = level === "CRITICAL" ? p.p_degraded_5s : p.p_degraded_15s;
    const cur = epRef.current;

    if (level === null) {
      if (cur) { setHistory((h) => [{ ...cur, endEpoch: p.window }, ...h].slice(0, 30)); epRef.current = null; setActiveEp(null); }
      return;
    }
    if (cur && cur.level === level) {
      const upd = { ...cur, endEpoch: p.window, count: cur.count + 1, peakP: Math.max(cur.peakP, pVal) };
      epRef.current = upd; setActiveEp(upd);
    } else {
      if (cur) setHistory((h) => [{ ...cur, endEpoch: p.window }, ...h].slice(0, 30));
      const ep: AlertEpisode = { id: `${p.window}-${level}`, level, startEpoch: p.window, endEpoch: p.window,
        startTime: new Date().toLocaleTimeString(), count: 1, peakP: pVal };
      epRef.current = ep; setActiveEp(ep);
      if (level === "CRITICAL" && !mutedRef.current) playBuzzer();   // once per episode
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
        setActiveEp(null); setHistory([]); epRef.current = null;
        setWarnEpoch(null); setOnsetEpoch(null);
      } else if (msg.type === "epoch") {
        setStream((prev) => [...prev.slice(-(MAX_POINTS - 1)), msg.data]); onEpoch(msg.data);
      } else if (msg.type === "replay_end" || msg.type === "replay_stopped") setPlaying(false);
    };
    return () => ws.close();
  }, [onEpoch]);

  const play = useCallback(() => {
    primeAudio();   // unlock audio inside the user gesture
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
      <Header minimal={minimal} onToggle={() => setMinimal((m) => !m)} connected={connected}
        muted={muted} onToggleMute={() => setMuted((m) => !m)} />

      <main className="mx-auto w-full max-w-[1640px] flex-1 px-4 py-6 md:px-6">
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
                  <SectionTitle hint="The dial shows the chance that GPS will become unreliable within the selected look-ahead time. Green is safe, red is danger.">{t("signal_quality")} (+{horizon}s)</SectionTitle>
                  <div className="flex justify-center py-2"><SignalGauge pDegraded={pDeg} confidence={conf} /></div>
                </Card>
                <Card delay={0.1}>
                  <SectionTitle hint="The three possible states and how likely each is right now. CLEAN = good, WARNING = patchy, DEGRADED = unreliable.">{t("class_probs")} (+{horizon}s)</SectionTitle>
                  {probs ? <div className="py-3"><ProbabilityBars probs={probs} /></div> : <Empty text={t("press_play")} />}
                </Card>
                <Card delay={0.15}><AlarmCenter active={activeEp} history={history} /></Card>
              </div>

              {!minimal && (
                <>
                  <Card><LeadTimeCard warnEpoch={warnEpoch} onsetEpoch={onsetEpoch} /></Card>
                  <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                    <ChartCard title={t("trajectory")} hint="The route driven so far. Each dot is coloured by how risky the GPS signal was at that spot.">
                      <TrajectoryMap data={stream} />
                    </ChartCard>
                    <ChartCard title={t("timeline")}
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
                <SectionTitle hint="A study on real Tokyo data: which positioning filter best survives GPS blackouts, and when it pays to distrust the satellites.">{t("analytics_title")}</SectionTitle>
                <EkfPanel />
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="px-6 py-5 text-center text-xs font-medium text-white" style={{ background: BEIHANG.primary }}>
        SENTINEL-GNSS © 2026 · Beihang University · RCSSTEAP
      </footer>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="flex h-44 items-center justify-center text-sm" style={{ color: BEIHANG.slate }}>{text}</div>;
}
