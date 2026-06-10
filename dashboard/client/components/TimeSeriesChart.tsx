"use client";
import { useRef, useState } from "react";
import { BEIHANG } from "@/lib/colors";
import { useElementWidth } from "@/lib/ui";
import type { Prediction } from "@/lib/types";

/** Responsive, interactive P(DEGRADED) timeline across the three horizons. */
export default function TimeSeriesChart({ data, height = 420 }: {
  data: Prediction[];
  height?: number;
}) {
  const [wrapRef, W] = useElementWidth<HTMLDivElement>();
  const svgRef = useRef<SVGSVGElement>(null);
  const [hi, setHi] = useState<number | null>(null);
  const width = Math.max(W, 280);

  const pad = { l: 52, r: 20, t: 24, b: 48 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const n = Math.max(data.length, 1);
  const x = (i: number) => pad.l + (innerW * i) / Math.max(n - 1, 1);
  const y = (v: number) => pad.t + innerH * (1 - Math.min(Math.max(v, 0), 1));

  const series = [
    { key: "p_degraded_5s" as const,  color: "#C0392B", label: "+5 s",  dash: "" },
    { key: "p_degraded_15s" as const, color: BEIHANG.primary, label: "+15 s", dash: "" },
    { key: "p_degraded_30s" as const, color: "#B7A93B", label: "+30 s", dash: "6 3" },
  ];

  const line = (key: keyof Prediction) =>
    data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(Number(d[key])).toFixed(1)}`).join(" ");

  const area = (key: keyof Prediction) =>
    `${line(key)} L${x(n - 1).toFixed(1)},${y(0).toFixed(1)} L${x(0).toFixed(1)},${y(0).toFixed(1)} Z`;

  const onMove = (e: React.MouseEvent) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = ((e.clientX - rect.left) / rect.width) * width;
    const i = Math.round(((px - pad.l) / innerW) * (n - 1));
    setHi(Math.max(0, Math.min(n - 1, i)));
  };

  const cur = hi != null ? data[hi] : null;

  // Y-axis ticks at 0, 0.25, 0.5, 0.75, 1.0
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  return (
    <div ref={wrapRef} className="relative w-full">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        preserveAspectRatio="none"
        onMouseMove={onMove}
        onMouseLeave={() => setHi(null)}
        role="img"
        aria-label="P(degraded) over time"
      >
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key} id={`g-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.22} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        {/* Background */}
        <rect width={width} height={height} fill="white" />

        {/* Coloured zone bands — DEGRADED (>0.7) red tint, WARNING (0.3-0.7) amber tint */}
        <rect x={pad.l} y={y(1.0)} width={innerW} height={y(0.7) - y(1.0)}
          fill="#C0392B" opacity={0.04} />
        <rect x={pad.l} y={y(0.7)} width={innerW} height={y(0.3) - y(0.7)}
          fill="#E1A100" opacity={0.05} />

        {/* Gridlines + Y axis ticks */}
        {yTicks.map((g) => (
          <g key={g}>
            <line x1={pad.l} x2={width - pad.r} y1={y(g)} y2={y(g)}
              stroke={BEIHANG.line} strokeWidth={g === 0 ? 1.5 : 0.9}
              strokeDasharray={g === 0 ? "" : "4 3"} />
            <text x={pad.l - 9} y={y(g) + 4} textAnchor="end"
              fontSize={13} fontWeight={700} fill={BEIHANG.slate}>
              {g.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Y-axis label */}
        <text transform={`translate(16, ${pad.t + innerH / 2}) rotate(-90)`}
          textAnchor="middle" fontSize={12} fontWeight={700} fill={BEIHANG.slate}>
          P(DEGRADED)
        </text>

        {/* Threshold lines */}
        <line x1={pad.l} x2={width - pad.r} y1={y(0.7)} y2={y(0.7)}
          stroke="#C0392B" strokeWidth={1.8} strokeDasharray="6 4" opacity={0.55} />
        <text x={width - pad.r - 4} y={y(0.7) - 5}
          textAnchor="end" fontSize={11} fontWeight={700} fill="#C0392B" opacity={0.8}>
          CRITICAL 0.70
        </text>

        <line x1={pad.l} x2={width - pad.r} y1={y(0.3)} y2={y(0.3)}
          stroke="#E1A100" strokeWidth={1.8} strokeDasharray="6 4" opacity={0.55} />
        <text x={width - pad.r - 4} y={y(0.3) - 5}
          textAnchor="end" fontSize={11} fontWeight={700} fill="#E1A100" opacity={0.8}>
          WARNING 0.30
        </text>

        {/* Area fills + lines */}
        {data.length > 1 && series.map((s) => (
          <g key={s.key}>
            <path d={area(s.key)} fill={`url(#g-${s.key})`} />
            <path d={line(s.key)} fill="none" stroke={s.color}
              strokeWidth={3.2} strokeLinejoin="round" strokeLinecap="round"
              strokeDasharray={s.dash} />
          </g>
        ))}

        {/* Hover crosshair */}
        {hi != null && cur && (
          <g>
            <line x1={x(hi)} x2={x(hi)} y1={pad.t} y2={pad.t + innerH}
              stroke={BEIHANG.slate} strokeWidth={1.2} strokeDasharray="3 3" />
            {series.map((s) => (
              <circle key={s.key} cx={x(hi)} cy={y(Number(cur[s.key]))}
                r={6} fill="#fff" stroke={s.color} strokeWidth={3} />
            ))}
          </g>
        )}

        {/* X-axis: epoch labels every ~20% */}
        {data.length > 1 && [0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const idx = Math.round(frac * (n - 1));
          return (
            <text key={frac} x={x(idx)} y={height - pad.b + 18}
              textAnchor="middle" fontSize={12} fontWeight={600} fill={BEIHANG.slate}>
              {idx}
            </text>
          );
        })}
        <text x={pad.l + innerW / 2} y={height - 4}
          textAnchor="middle" fontSize={12} fontWeight={600} fill={BEIHANG.slate}>
          epoch
        </text>
      </svg>

      {/* Legend */}
      <div className="mt-2 flex flex-wrap gap-5 px-2">
        {series.map((s) => (
          <span key={s.key} className="flex items-center gap-2 text-sm font-bold"
            style={{ color: BEIHANG.ink }}>
            <svg width={32} height={12}>
              <line x1={0} y1={6} x2={32} y2={6}
                stroke={s.color} strokeWidth={3.5} strokeDasharray={s.dash} />
            </svg>
            {s.label}
          </span>
        ))}
      </div>

      {/* Hover tooltip */}
      {hi != null && cur && (
        <div
          className="pointer-events-none absolute top-2 z-30 rounded-xl px-3 py-2.5 text-sm font-bold text-white shadow-xl"
          style={{
            background: "#0B1F3A",
            left: `clamp(8px, ${(x(hi) / width) * 100}%, calc(100% - 160px))`,
          }}
        >
          <div className="mb-1.5 text-xs opacity-60">epoch {hi}</div>
          {series.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-4">
              <span style={{ color: s.color }}>{s.label}</span>
              <span className="tabular-nums">{(Number(cur[s.key]) * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
