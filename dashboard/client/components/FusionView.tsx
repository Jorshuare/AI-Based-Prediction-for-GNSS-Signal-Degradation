"use client";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { Card, SectionTitle, InfoDot, ExportPng, useElementWidth } from "@/lib/ui";
import { FiNavigation, FiRadio, FiTarget } from "@/lib/icons";
import { api } from "@/lib/api";
import SatelliteStrip from "@/components/SatelliteStrip";
import type { FusionResult } from "@/lib/types";

const SERIES = [
  { key: "truth" as const, color: "#2E7D32", label: "Ground truth (SPAN-INS)", w: 3 },
  { key: "gnss" as const, color: "#C0392B", label: "Raw GNSS receiver", w: 1.4, dash: "3 3" },
  { key: "aided_fixed" as const, color: BEIHANG.primary, label: "Aided EKF (ours)", w: 2.8 },
];

export default function FusionView({ minimal }: { minimal: boolean }) {
  const [sources, setSources] = useState<{ id: string; label: string }[]>([]);
  const [source, setSource] = useState("trimble");
  const [f, setF] = useState<FusionResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [show, setShow] = useState<Record<string, boolean>>({ truth: true, gnss: true, aided_fixed: true });
  const [mapRef, mapW] = useElementWidth<HTMLDivElement>();

  useEffect(() => { api.fusionSources().then(setSources).catch(() => {}); }, []);
  useEffect(() => {
    setF(null); setErr(null);
    api.fusion(source).then(setF).catch((e) => setErr(String(e)));
  }, [source]);

  const geom = useMemo(() => {
    if (!f) return null;
    const all = [...f.truth, ...f.aided_fixed];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const W = Math.max(mapW, 300), H = minimal ? 360 : 520, pad = 32;
    const sx = (maxX - minX) || 1, sy = (maxY - minY) || 1;
    const s = Math.min((W - 2 * pad) / sx, (H - 2 * pad) / sy);
    const ox = (W - s * sx) / 2, oy = (H - s * sy) / 2;
    const proj = (p: number[]) => [ox + (p[0] - minX) * s, H - (oy + (p[1] - minY) * s)] as [number, number];
    return { W, H, proj };
  }, [f, mapW, minimal]);

  const SourcePicker = (
    <div className="flex items-center gap-2">
      <FiRadio size={16} color={BEIHANG.secondary} />
      <span className="text-sm font-bold" style={{ color: BEIHANG.slate }}>GNSS source</span>
      <select value={source} onChange={(e) => setSource(e.target.value)}
        className="rounded-xl border bg-white px-3 py-2 text-sm font-bold outline-none"
        style={{ borderColor: BEIHANG.line, color: BEIHANG.ink }}>
        {sources.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
      </select>
    </div>
  );

  if (err) return <Card>{SourcePicker}<p className="mt-3 text-sm" style={{ color: BEIHANG.slate }}>Fusion data unavailable. Run <code>python -m src.models.ekf_urbannav_runner --real --both</code> ({err}).</p></Card>;
  if (!f || !geom) return <Card>{SourcePicker}<p className="mt-3 text-sm" style={{ color: BEIHANG.slate }}>Loading real fusion…</p></Card>;

  const s = f.summary;
  const pathOf = (key: "truth" | "gnss" | "aided_fixed") =>
    f[key].map((p, i) => { const q = geom.proj(p); return `${i === 0 ? "M" : "L"}${q[0].toFixed(1)},${q[1].toFixed(1)}`; }).join(" ");

  const rmseOrder = ["gnss_raw", "cv_kf", "aided_ekf_fixed", "aided_ekf_adaptive"];
  const rmseLabel: Record<string, string> = { gnss_raw: "Raw GNSS", cv_kf: "Simple KF", aided_ekf_fixed: "Aided EKF (ours)", aided_ekf_adaptive: "Aided EKF (adaptive)" };
  const maxR = Math.max(...rmseOrder.map((k) => s.rmse_degraded_segment[k] ?? 0));
  const bestGain = s.degraded_gain_vs_raw["aided_ekf_fixed"];

  return (
    <div className="flex flex-col gap-5">
      {/* real-data banner */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4 text-white"
        style={{ background: `linear-gradient(100deg, ${BEIHANG.primary}, ${BEIHANG.secondary})` }}>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm font-semibold">
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold tracking-wide">100% REAL DATA</span>
          <span className="flex items-center gap-1.5"><FiNavigation size={15} /> {s.n_real_fixes.toLocaleString()} real fixes</span>
          <span className="flex items-center gap-1.5"><FiRadio size={15} /> mean {s.mean_sats} satellites</span>
          <span className="opacity-85">{s.engine}</span>
        </div>
        {SourcePicker && <div className="rounded-xl bg-white/95 p-1">{SourcePicker}</div>}
      </motion.div>

      <div className={`grid grid-cols-1 gap-5 ${minimal ? "" : "lg:grid-cols-[1.55fr_1fr]"}`}>
        <Card>
          <div className="mb-4 flex items-center gap-2">
            <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>Where is the car, really?</h3>
            <InfoDot text="The red line is what the raw satellite receiver reported (it jumps wildly in the urban canyon). The blue line is our fused estimate using the car's motion sensors. Green is the true path. Closer to green = better." />
            <div className="ml-auto"><ExportPng targetRef={mapRef} filename="fusion_trajectory.png" /></div>
          </div>
          <div ref={mapRef}>
            <svg viewBox={`0 0 ${geom.W} ${geom.H}`} width="100%" height={geom.H} className="rounded-xl">
              <rect width={geom.W} height={geom.H} fill="#0A1A2F" rx={12} />
              {SERIES.filter((ss) => show[ss.key]).map((ss) => (
                <path key={ss.key} d={pathOf(ss.key)} fill="none" stroke={ss.color}
                  strokeWidth={ss.w} strokeDasharray={ss.dash ?? ""} strokeLinejoin="round" opacity={0.95} />
              ))}
            </svg>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SERIES.map((ss) => (
              <button key={ss.key} onClick={() => setShow((p) => ({ ...p, [ss.key]: !p[ss.key] }))}
                className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold transition"
                style={{ background: show[ss.key] ? "#fff" : BEIHANG.mist, color: BEIHANG.ink, opacity: show[ss.key] ? 1 : 0.5, borderColor: BEIHANG.line }}>
                <span className="h-1.5 w-5 rounded" style={{ background: ss.color }} /> {ss.label}
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <SectionTitle hint="Average position error (in metres) during the hard moments when the sky was blocked. Shorter bar = more accurate. Our aided filter is the shortest.">
            Accuracy when the sky is blocked
          </SectionTitle>
          <div className="flex flex-col gap-3.5">
            {rmseOrder.map((k, i) => {
              const v = s.rmse_degraded_segment[k] ?? 0;
              const best = k === "aided_ekf_fixed";
              const gain = s.degraded_gain_vs_raw[k];
              return (
                <div key={k}>
                  <div className="mb-1 flex items-center justify-between text-[13px] font-bold">
                    <span className="flex items-center gap-1.5" style={{ color: BEIHANG.ink }}>
                      {best && <FiTarget size={14} color={BEIHANG.primary} />}{rmseLabel[k]}
                    </span>
                    <span style={{ color: best ? BEIHANG.primary : BEIHANG.slate }}>
                      {v.toFixed(1)} m {k !== "gnss_raw" && <span className="opacity-70">({gain > 0 ? "+" : ""}{gain}%)</span>}
                    </span>
                  </div>
                  <div className="h-5 w-full overflow-hidden rounded-md" style={{ background: BEIHANG.mist }}>
                    <motion.div className="h-full rounded-md" initial={{ width: 0 }}
                      animate={{ width: `${(v / maxR) * 100}%` }} transition={{ delay: i * 0.06, duration: 0.5 }}
                      style={{ background: best ? BEIHANG.primary : BEIHANG.secondary }} />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: BEIHANG.slate }}>
            On <b>real</b> Shinjuku-canyon data, fusing the satellite signal with the car&apos;s motion sensors
            (wheel speed + inertial) cuts the error during blockages by{" "}
            <b style={{ color: BEIHANG.primary }}>{bestGain}%</b> — keeping the vehicle located even when GPS
            alone would be lost.
          </p>
        </Card>
      </div>

      {!minimal && (
        <Card>
          <SatelliteStrip nsat={f.nsat} />
        </Card>
      )}
    </div>
  );
}
