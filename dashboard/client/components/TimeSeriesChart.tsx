"use client";
import { useRef, useState } from "react";
import { BEIHANG } from "@/lib/colors";
import { useElementWidth } from "@/lib/ui";
import type { Prediction } from "@/lib/types";

/** Responsive, interactive P(DEGRADED) timeline across the three horizons. */
export default function TimeSeriesChart({ data, height = 260 }: {
  data: Prediction[];
  height?: number;
}) {
  const [wrapRef, W] = useElementWidth<HTMLDivElement>();
  const svgRef = useRef<SVGSVGElement>(null);
  const [hi, setHi] = useState<number | null>(null);
  const width = Math.max(W, 280);

  const pad = { l: 44, r: 16, t: 18, b: 30 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const n = Math.max(data.length, 1);
  const x = (i: number) => pad.l + (innerW * i) / Math.max(n - 1, 1);
  const y = (v: number) => pad.t + innerH * (1 - v);

  const series = [
    { key: "p_degraded_5s" as const, color: "#C0392B", label: "+5 s" },
    { key: "p_degraded_15s" as const, color: BEIHANG.secondary, label: "+15 s" },
    { key: "p_degraded_30s" as const, color: "#B7A93B", label: "+30 s" },
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
              <stop offset="0%" stopColor={s.color} stopOpacity={0.18} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <g key={g}>
            <line x1={pad.l} x2={width - pad.r} y1={y(g)} y2={y(g)} stroke={BEIHANG.line} strokeWidth={1} />
            <text x={pad.l - 8} y={y(g) + 4} textAnchor="end" fontSize={11} fontWeight={600} fill={BEIHANG.slate}>
              {g.toFixed(2)}
            </text>
          </g>
        ))}
        {/* threshold guides */}
        <line x1={pad.l} x2={width - pad.r} y1={y(0.7)} y2={y(0.7)} stroke="#C0392B" strokeWidth={1.2} strokeDasharray="5 4" opacity={0.45} />
        <line x1={pad.l} x2={width - pad.r} y1={y(0.3)} y2={y(0.3)} stroke="#E1A100" strokeWidth={1.2} strokeDasharray="5 4" opacity={0.45} />

        {data.length > 1 && series.map((s) => (
          <g key={s.key}>
            <path d={area(s.key)} fill={`url(#g-${s.key})`} />
            <path d={line(s.key)} fill="none" stroke={s.color} strokeWidth={2.4} strokeLinejoin="round" />
          </g>
        ))}

        {/* hover crosshair + markers */}
        {hi != null && cur && (
          <g>
            <line x1={x(hi)} x2={x(hi)} y1={pad.t} y2={pad.t + innerH} stroke={BEIHANG.slate} strokeWidth={1} strokeDasharray="3 3" />
            {series.map((s) => (
              <circle key={s.key} cx={x(hi)} cy={y(Number(cur[s.key]))} r={4.5} fill="#fff" stroke={s.color} strokeWidth={2.5} />
            ))}
          </g>
        )}
      </svg>

      {/* legend */}
      <div className="mt-1 flex flex-wrap gap-4 px-2">
        {series.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5 text-xs font-bold" style={{ color: BEIHANG.ink }}>
            <span className="h-1 w-4 rounded" style={{ background: s.color }} /> {s.label}
          </span>
        ))}
      </div>

      {/* hover tooltip */}
      {hi != null && cur && (
        <div
          className="pointer-events-none absolute top-2 z-30 rounded-xl px-3 py-2 text-[11px] font-semibold text-white shadow-xl"
          style={{
            background: "#0B1F3A",
            left: `clamp(8px, ${(x(hi) / width) * 100}%, calc(100% - 150px))`,
          }}
        >
          <div className="mb-1 opacity-70">epoch {hi}</div>
          {series.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-3">
              <span style={{ color: s.color }}>{s.label}</span>
              <span>{(Number(cur[s.key]) * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
