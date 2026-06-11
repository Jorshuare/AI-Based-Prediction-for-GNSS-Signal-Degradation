"use client";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { BEIHANG } from "@/lib/colors";
import { InfoDot } from "@/lib/ui";
import { useT } from "@/lib/i18n";
import type { EkfResult } from "@/lib/types";

/* ── per-filter colour + description ───────────────────────────────────── */
const META: Record<string, { label: string; color: string; desc: string }> = {
  gnss_raw:            { label: "GNSS Raw",            color: "#C0392B", desc: "No filter. Raw GNSS position jumps during blockage." },
  cv_kf_fixed:         { label: "CV Kalman (fixed-R)",  color: "#E67E22", desc: "Constant-velocity Kalman filter, fixed measurement noise." },
  ekf9_fixed:          { label: "EKF 9-state (fixed-R)",color: "#F39C12", desc: "9-state EKF with IMU, fixed measurement trust." },
  ekf9_adaptive:       { label: "EKF 9-state (adapt-R)",color: "#D4AC0D", desc: "9-state EKF with SENTINEL-driven adaptive R." },
  ekf9_aided_fixed:    { label: "Aided EKF (fixed-R)",  color: "#1B873A", desc: "Best: EKF + wheel odometry + NHC + ZUPT with fixed R." },
  ekf9_aided_adaptive: { label: "Aided EKF (adapt-R)",  color: "#1565C0", desc: "EKF + full aiding + SENTINEL adaptive R." },
};

const ORDER = ["gnss_raw", "cv_kf_fixed", "ekf9_fixed", "ekf9_adaptive", "ekf9_aided_fixed", "ekf9_aided_adaptive"];

/* ── tiny hook: container pixel width ──────────────────────────────────── */
function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T | null>(null);
  const [w, setW] = useState(500);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

/* ── y-axis nice ticks ──────────────────────────────────────────────────── */
function niceTicks(max: number, n = 5): number[] {
  const step = Math.ceil(max / n / 5) * 5 || 1;
  const ticks: number[] = [];
  for (let v = 0; v <= max + step; v += step) ticks.push(v);
  return ticks;
}

export default function EkfPanel() {
  const { t } = useT();
  const [ekf, setEkf] = useState<EkfResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sweepRef, sweepW] = useWidth<HTMLDivElement>();
  const [hoveredBar, setHoveredBar] = useState<string | null>(null);
  const [hoveredPt, setHoveredPt] = useState<{ x: number; y: number; label: string } | null>(null);

  useEffect(() => { api.ekf().then(setEkf).catch((e) => setErr(String(e))); }, []);

  if (err) return <p className="text-sm" style={{ color: BEIHANG.slate }}>EKF analytics unavailable ({err}).</p>;
  if (!ekf) return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="h-12 animate-pulse rounded-xl" style={{ background: BEIHANG.mist }} />
      ))}
    </div>
  );

  const order = ORDER.filter((k) => k in ekf.rmse_blocked_segment);
  const maxV = Math.max(...order.map((k) => ekf.rmse_blocked_segment[k]));
  const sweep = ekf.severity_sweep ?? [];

  /* ── sweep chart geometry ─────────────────────────────────────────────── */
  const W = Math.max(sweepW, 320);
  const H = 340;
  const padL = 52, padR = 20, padT = 24, padB = 48;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const sMax = Math.ceil(Math.max(...sweep.flatMap((r) => [r.raw, r.fixed_R, r.adaptive_R]), 1) / 10) * 10;
  const sx = (i: number) => padL + (chartW * i) / Math.max(sweep.length - 1, 1);
  const sy = (v: number) => padT + chartH - (chartH * Math.min(v, sMax)) / sMax;

  const ticks = niceTicks(sMax, 6);

  const linePath = (key: "raw" | "fixed_R" | "adaptive_R") =>
    sweep.map((r, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(r[key]).toFixed(1)}`).join(" ");

  const areaPath = (key: "raw" | "fixed_R" | "adaptive_R") => {
    const pts = sweep.map((r, i) => `${sx(i).toFixed(1)},${sy(r[key]).toFixed(1)}`).join(" L ");
    const base = sy(0);
    return `M${sx(0).toFixed(1)},${base} L ${pts} L${sx(sweep.length - 1).toFixed(1)},${base} Z`;
  };

  const SWEEP_LINES = [
    { key: "raw" as const,        color: "#C0392B", dash: "6 4", label: "Raw GNSS",        fill: "#C0392B10" },
    { key: "fixed_R" as const,    color: "#003360", dash: "",    label: "Fixed-R (best)",  fill: "#00336015" },
    { key: "adaptive_R" as const, color: "#BCB245", dash: "4 3", label: "Adaptive-R",      fill: "#BCB24510" },
  ];

  /* best bar = ekf9_aided_fixed */
  return (
    <div className="flex flex-col gap-8">

      {/* ══ SECTION HEADER ══════════════════════════════════════════════════ */}
      <div className="flex items-center gap-3 border-b pb-3" style={{ borderColor: BEIHANG.line }}>
        <div className="h-1 w-8 rounded" style={{ background: BEIHANG.primary }} />
        <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>
          {t("analytics_title")}
        </h3>
        <InfoDot text="How much does each filter improve GNSS positioning during satellite blockage? Compare raw GNSS against progressively smarter fusion strategies." />
      </div>

      {/* ══ TWO COLUMNS ════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">

        {/* ── LEFT: BAR CHART ──────────────────────────────────────────── */}
        <div>
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <h4 className="text-base font-bold" style={{ color: BEIHANG.ink }}>
                {t("ekf_blocked_title") ?? "Blocked-segment RMSE by filter"}
                <InfoDot text="Position error (metres) measured ONLY during GNSS-blockage windows vs SPAN-INS cm-level truth. Lower = better." />
              </h4>
              <p className="mt-0.5 text-xs" style={{ color: BEIHANG.slate }}>
                Blockage only · cm-level SPAN-INS ground truth · Tokyo Shinjuku
              </p>
            </div>
            <span className="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold text-white"
              style={{ background: "#1B873A" }}>
              Best: 6.4 m
            </span>
          </div>

          <div className="flex flex-col gap-1.5">
            {order.map((k, idx) => {
              const v = ekf.rmse_blocked_segment[k];
              const gain = ekf.gains_vs_raw_blocked[k];
              const m = META[k] ?? { label: k, color: BEIHANG.secondary, desc: "" };
              const best = k === "ekf9_aided_fixed";
              const pct = (v / maxV) * 100;
              const hovered = hoveredBar === k;

              return (
                <motion.div key={k}
                  className="group relative cursor-default rounded-xl p-3 transition-colors"
                  style={{ background: hovered ? BEIHANG.mist : "transparent" }}
                  onMouseEnter={() => setHoveredBar(k)}
                  onMouseLeave={() => setHoveredBar(null)}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.07 }}>

                  {/* row: label + bar + value */}
                  <div className="flex items-center gap-3">
                    {/* label */}
                    <div className="w-40 shrink-0">
                      <div className="flex items-center gap-1.5">
                        {best && <span className="text-base">★</span>}
                        <span className={`text-sm font-bold ${best ? "text-[#1B873A]" : ""}`}
                          style={{ color: best ? "#1B873A" : BEIHANG.ink }}>
                          {m.label}
                        </span>
                      </div>
                      {gain !== undefined && k !== "gnss_raw" && (
                        <span className="text-[11px] font-semibold"
                          style={{ color: gain > 50 ? "#1B873A" : gain > 0 ? BEIHANG.slate : "#C0392B" }}>
                          {gain > 0 ? "+" : ""}{gain}% vs raw
                        </span>
                      )}
                    </div>

                    {/* bar track */}
                    <div className="relative h-11 flex-1 overflow-hidden rounded-lg"
                      style={{ background: `${m.color}18` }}>
                      <motion.div className="absolute inset-y-0 left-0 rounded-lg"
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ delay: idx * 0.07 + 0.1, duration: 0.55, ease: "easeOut" }}
                        style={{
                          background: best
                            ? `linear-gradient(90deg, #1B873A, #2ECC71)`
                            : `linear-gradient(90deg, ${m.color}CC, ${m.color}88)`,
                        }} />
                      {/* value label inside bar */}
                      <div className="absolute inset-0 flex items-center px-3">
                        <span className="text-base font-extrabold tabular-nums text-white drop-shadow-sm">
                          {v.toFixed(1)} m
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* expanded description on hover */}
                  {hovered && m.desc && (
                    <p className="mt-1.5 pl-[168px] text-[11px] leading-tight" style={{ color: BEIHANG.slate }}>
                      {m.desc}
                    </p>
                  )}
                </motion.div>
              );
            })}
          </div>

          {/* caption */}
          <p className="mt-4 rounded-xl px-4 py-3 text-sm leading-relaxed"
            style={{ background: "#E8F5E9", color: "#1B5E20", borderLeft: "3px solid #1B873A" }}>
            <strong>Aided EKF (fixed-R)</strong> cuts blocked RMSE from 36.3 m → 6.4 m (<strong>+82.5%</strong>).
            Wheel-odometry + NHC + ZUPT provide dead-reckoning continuity during full signal loss.
          </p>
        </div>

        {/* ── RIGHT: SWEEP CHART ───────────────────────────────────────── */}
        <div ref={sweepRef}>
          <div className="mb-5">
            <h4 className="text-base font-bold" style={{ color: BEIHANG.ink }}>
              {t("ekf_when_title") ?? "When does adaptive-R help?"}
              <InfoDot text="Sweeps GNSS multipath severity. With wheel-odometry aiding, fixed-R stays best: inflating R discards heading observability." />
            </h4>
            <p className="mt-0.5 text-xs" style={{ color: BEIHANG.slate }}>
              Blocked-segment RMSE vs injected multipath bias · aided platform
            </p>
          </div>

          <div className="relative rounded-2xl border p-4"
            style={{ background: "#FAFBFF", borderColor: BEIHANG.line }}>
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}
              style={{ display: "block", overflow: "visible" }}>

              {/* ── gridlines + Y axis ─────────────────────────────────── */}
              {ticks.map((t) => (
                <g key={t}>
                  <line x1={padL} y1={sy(t)} x2={W - padR} y2={sy(t)}
                    stroke={BEIHANG.line} strokeWidth={t === 0 ? 1.5 : 0.8} strokeDasharray={t === 0 ? "" : "4 3"} />
                  <text x={padL - 7} y={sy(t) + 4} textAnchor="end" fontSize={11}
                    fill={BEIHANG.slate} fontFamily="system-ui">{t}</text>
                </g>
              ))}

              {/* Y axis label */}
              <text transform={`translate(14, ${padT + chartH / 2}) rotate(-90)`}
                textAnchor="middle" fontSize={11} fill={BEIHANG.slate} fontFamily="system-ui">
                RMSE (m)
              </text>

              {/* ── area fills ─────────────────────────────────────────── */}
              {SWEEP_LINES.map((s) => (
                <path key={`area-${s.key}`} d={areaPath(s.key)} fill={s.fill} />
              ))}

              {/* ── lines ──────────────────────────────────────────────── */}
              {SWEEP_LINES.map((s) => (
                <path key={s.key} d={linePath(s.key)} fill="none"
                  stroke={s.color} strokeWidth={s.key === "fixed_R" ? 3.5 : 2.5}
                  strokeDasharray={s.dash} strokeLinejoin="round" strokeLinecap="round" />
              ))}

              {/* ── data point dots + hover targets ────────────────────── */}
              {SWEEP_LINES.map((s) =>
                sweep.map((r, i) => {
                  const cx = sx(i), cy = sy(r[s.key]);
                  return (
                    <g key={`${s.key}-${i}`}
                      onMouseEnter={() => setHoveredPt({
                        x: cx, y: cy,
                        label: `${s.label}: ${r[s.key].toFixed(1)} m  (bias ${r.bias_max_m} m)`
                      })}
                      onMouseLeave={() => setHoveredPt(null)}>
                      <circle cx={cx} cy={cy} r={8} fill="transparent" />
                      <circle cx={cx} cy={cy} r={s.key === "fixed_R" ? 5 : 3.5}
                        fill="white" stroke={s.color} strokeWidth={2} />
                    </g>
                  );
                })
              )}

              {/* ── X axis tick labels ─────────────────────────────────── */}
              {sweep.map((r, i) => (
                <text key={i} x={sx(i)} y={H - padB + 18} fontSize={11}
                  textAnchor="middle" fill={BEIHANG.slate} fontFamily="system-ui">
                  {r.bias_max_m}
                </text>
              ))}

              {/* X axis label */}
              <text x={padL + chartW / 2} y={H - 2} textAnchor="middle"
                fontSize={11} fill={BEIHANG.slate} fontFamily="system-ui">
                Multipath bias injected during blockage (m)
              </text>

              {/* ── Hover tooltip ──────────────────────────────────────── */}
              {hoveredPt && (() => {
                const bx = hoveredPt.x + 8;
                const by = hoveredPt.y - 16;
                const tw = 200;
                return (
                  <g>
                    <rect x={Math.min(bx, W - tw - 8)} y={by - 16} width={tw} height={22}
                      rx={5} fill="white" stroke={BEIHANG.line} strokeWidth={1} filter="url(#shadow)" />
                    <text x={Math.min(bx, W - tw - 8) + 7} y={by} fontSize={10.5}
                      fill={BEIHANG.ink} fontFamily="system-ui">{hoveredPt.label}</text>
                  </g>
                );
              })()}

              {/* ── crossover annotation ───────────────────────────────── */}
              {(() => {
                const lastI = sweep.length - 1;
                if (lastI < 0) return null;
                const lx = sx(lastI);
                const ly = sy(sweep[lastI].fixed_R);
                return (
                  <g>
                    <circle cx={lx} cy={ly} r={7} fill="#1B873A" opacity={0.15} />
                    <text x={lx - 6} y={ly - 12} fontSize={10} fill="#1B873A"
                      fontFamily="system-ui" fontWeight="600">≈cross</text>
                  </g>
                );
              })()}

              <defs>
                <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
                  <feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.12" />
                </filter>
              </defs>
            </svg>
          </div>

          {/* Legend */}
          <div className="mt-3 flex flex-wrap gap-4">
            {SWEEP_LINES.map((s) => (
              <div key={s.key} className="flex items-center gap-2 text-xs font-bold"
                style={{ color: s.color }}>
                <svg width={28} height={10}>
                  <line x1={0} y1={5} x2={28} y2={5} stroke={s.color}
                    strokeWidth={s.key === "fixed_R" ? 3 : 2}
                    strokeDasharray={s.dash} />
                </svg>
                {s.label}
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-xl border-l-4 px-4 py-3 text-sm leading-relaxed"
            style={{ background: "#EEF2FF", color: "#1E3A5F", borderColor: BEIHANG.primary }}>
            With wheel-odometry + NHC + ZUPT aiding, <strong>fixed-R wins across the entire range</strong>.
            Inflating R discards heading observability: the aiding already dead-reckons through the gap.
            Adaptive-R is better on <em>GNSS-only platforms</em> (no IMU, no odometry).
          </div>

        </div>
      </div>
    </div>
  );
}
