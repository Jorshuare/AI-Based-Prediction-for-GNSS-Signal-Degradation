"use client";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { Card, SectionTitle, InfoDot, ExportPng, useElementWidth } from "@/lib/ui";
import { FiNavigation, FiRadio, FiTarget } from "@/lib/icons";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import SatelliteStrip from "@/components/SatelliteStrip";
import type { FusionResult } from "@/lib/types";

const EKF_FIXED_COLOR = "#00BFA5";

const SERIES = [
  { key: "truth" as const, color: "#43A047", labelKey: "series_truth", w: 7 },
  { key: "gnss" as const, color: "#EF5350", labelKey: "series_gnss", w: 3.5, dash: "6 5" },
  { key: "aided_fixed" as const, color: EKF_FIXED_COLOR, labelKey: "series_fixed", w: 7 },
  { key: "aided_adapt" as const, color: "#FFB300", labelKey: "series_adapt", w: 5, dash: "10 5" },
];
type SeriesKey = (typeof SERIES)[number]["key"];

export default function FusionView({ minimal }: { minimal: boolean }) {
  const { t } = useT();
  const [sources, setSources] = useState<{ id: string; label: string }[]>([]);
  const [source, setSource] = useState("trimble");
  const [f, setF] = useState<FusionResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [show, setShow] = useState<Record<string, boolean>>({ truth: true, gnss: true, aided_fixed: true, aided_adapt: true });
  const [mapRef, mapW] = useElementWidth<HTMLDivElement>();

  useEffect(() => { api.fusionSources().then(setSources).catch(() => {}); }, []);
  useEffect(() => {
    setF(null); setErr(null);
    api.fusion(source).then(setF).catch((e) => setErr(String(e)));
  }, [source]);

  const geom = useMemo(() => {
    if (!f) return null;
    // Use only stable tracks for bounding box — GNSS outliers would shrink the scale
    const all = [...f.truth, ...f.aided_fixed];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const sx = (maxX - minX) || 1, sy = (maxY - minY) || 1;

    // Auto-rotate: put the long axis of the track along the horizontal so it fills the landscape map
    const rotate = sy > sx * 1.1;
    const dispSx = rotate ? sy : sx;
    const dispSy = rotate ? sx : sy;

    const W = Math.max(mapW, 400);

    // H = 1.5× the auto-fit height → taller map; scale-to-fill so path fills the full height
    const dispAspect = dispSy / dispSx;
    const H = Math.round(W * dispAspect * 1.5);

    // Math.max → height-limited scale: path fills H completely, clips slightly on sides
    const s = Math.max(W / dispSx, H / dispSy);
    const ox = (W - s * dispSx) / 2;
    const oy = (H - s * dispSy) / 2;

    const proj = (p: number[]): [number, number] => {
      const ex = p[0] - minX, ey = p[1] - minY;
      return rotate
        ? [ox + ey * s, H - (oy + ex * s)]
        : [ox + ex * s, H - (oy + ey * s)];
    };

    return { W, H, proj };
  }, [f, mapW, minimal]);

  const SourcePicker = (
    <div className="flex items-center gap-2">
      <FiRadio size={16} color={BEIHANG.secondary} />
      <span className="text-sm font-bold" style={{ color: BEIHANG.slate }}>{t("gnss_source")}</span>
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
  const pathOf = (key: SeriesKey) =>
    f[key].map((p, i) => { const q = geom.proj(p); return `${i === 0 ? "M" : "L"}${q[0].toFixed(1)},${q[1].toFixed(1)}`; }).join(" ");

  const rmseOrder = ["gnss_raw", "cv_kf", "aided_ekf_fixed", "aided_ekf_adaptive"];
  const rmseLabel: Record<string, string> = { gnss_raw: t("rmse_raw"), cv_kf: t("rmse_simplekf"), aided_ekf_fixed: t("rmse_fixed"), aided_ekf_adaptive: t("rmse_adapt") };
  const maxR = Math.max(...rmseOrder.map((k) => s.rmse_degraded_segment[k] ?? 0));
  const bestGain = s.degraded_gain_vs_raw["aided_ekf_fixed"];

  return (
    <div className="flex flex-col gap-5">
      {/* Banner */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4 text-white"
        style={{ background: `linear-gradient(100deg, ${BEIHANG.primary}, ${BEIHANG.secondary})` }}>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm font-semibold">
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold tracking-wide">{t("real_data")}</span>
          <span className="flex items-center gap-1.5"><FiNavigation size={15} /> {t("fusion_real_fixes", { n: s.n_real_fixes.toLocaleString() })}</span>
          <span className="flex items-center gap-1.5"><FiRadio size={15} /> {t("fusion_mean_sats", { n: s.mean_sats })}</span>
          <span className="opacity-85">{s.engine}</span>
        </div>
        {SourcePicker && <div className="rounded-xl bg-white/95 p-1">{SourcePicker}</div>}
      </motion.div>

      {/* Trajectory map (left) + Accuracy panel (right) side by side */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[4fr_2fr]">

        {/* Map — pad=false, SVG fills edge-to-edge */}
        <Card pad={false}>
          <div className="flex items-center gap-2 px-6 pt-6 pb-3">
            <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>{t("where_car")}</h3>
            <InfoDot text="Green = ground truth. Teal = our EKF (recommended). Red dashed = raw GNSS. Yellow dashed = adaptive EKF. Closer to green = better." />
            <div className="ml-auto"><ExportPng targetRef={mapRef} filename="fusion_trajectory.png" /></div>
          </div>
          {/* px-4 py-4: small CSS margin around SVG — keeps scale large */}
          <div className="w-full px-4 py-4">
            <div ref={mapRef} className="w-full">
              <svg viewBox={`0 0 ${geom.W} ${geom.H}`} width="100%" height={geom.H} style={{ display: "block" }}>
                {SERIES.filter((ss) => show[ss.key]).map((ss) => (
                  <path key={ss.key} d={pathOf(ss.key)} fill="none" stroke={ss.color}
                    strokeWidth={ss.w} strokeDasharray={ss.dash ?? ""} strokeLinejoin="round" strokeLinecap="round" opacity={0.95} />
                ))}
              </svg>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 px-6 pb-5">
            {SERIES.map((ss) => (
              <button key={ss.key} onClick={() => setShow((p) => ({ ...p, [ss.key]: !p[ss.key] }))}
                className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold transition"
                style={{ background: show[ss.key] ? "#fff" : BEIHANG.mist, color: BEIHANG.ink, opacity: show[ss.key] ? 1 : 0.5, borderColor: BEIHANG.line }}>
                <span className="h-1.5 w-5 rounded" style={{ background: ss.color }} /> {t(ss.labelKey)}
              </button>
            ))}
          </div>
        </Card>

        {/* Accuracy panel (right) */}
        <Card>
          <SectionTitle hint="Average position error (metres) during GPS blackout segments. Shorter bar = more accurate.">
            {t("accuracy_blocked")}
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
                      {best && <FiTarget size={14} color={EKF_FIXED_COLOR} />}{rmseLabel[k]}
                    </span>
                    <span style={{ color: best ? EKF_FIXED_COLOR : BEIHANG.slate }}>
                      {v.toFixed(1)} m {k !== "gnss_raw" && <span className="opacity-70">({gain > 0 ? "+" : ""}{gain}%)</span>}
                    </span>
                  </div>
                  <div className="h-5 w-full overflow-hidden rounded-md" style={{ background: BEIHANG.mist }}>
                    <motion.div className="h-full rounded-md" initial={{ width: 0 }}
                      animate={{ width: `${(v / maxR) * 100}%` }} transition={{ delay: i * 0.06, duration: 0.5 }}
                      style={{ background: best ? EKF_FIXED_COLOR : BEIHANG.secondary }} />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: BEIHANG.slate }}>
            {t("fusion_caption", { g: bestGain })}
          </p>
        </Card>
      </div>

      {/* Satellite count — full width below */}
      <Card>
        <SatelliteStrip nsat={f.nsat} />
      </Card>
    </div>
  );
}
