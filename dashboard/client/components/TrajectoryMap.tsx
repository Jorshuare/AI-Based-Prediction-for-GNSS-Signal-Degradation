"use client";
import { useMemo } from "react";
import { BEIHANG, riskColor } from "@/lib/colors";
import { useElementWidth } from "@/lib/ui";
import type { Prediction } from "@/lib/types";

/** Responsive, self-contained risk-coloured trajectory (SVG, viewBox-scaled). */
export default function TrajectoryMap({ data, height = 420 }: {
  data: Prediction[];
  height?: number;
}) {
  const [wrapRef, W] = useElementWidth<HTMLDivElement>();
  const width = Math.max(W, 280);

  const { pts, head } = useMemo(() => {
    if (!data.length) return { pts: [] as { px: number; py: number; p: number }[], head: null as null | { px: number; py: number } };
    const xs = data.map((d) => d.x), ys = data.map((d) => d.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const pad = 34;
    const sx = (maxX - minX) || 1, sy = (maxY - minY) || 1;
    const s = Math.min((width - 2 * pad) / sx, (height - 2 * pad) / sy);
    const ox = (width - s * sx) / 2, oy = (height - s * sy) / 2;
    const proj = (x: number, y: number) => ({ px: ox + (x - minX) * s, py: height - (oy + (y - minY) * s) });
    const pts = data.map((d) => ({ ...proj(d.x, d.y), p: d.p_degraded_5s }));
    const last = data[data.length - 1];
    return { pts, head: proj(last.x, last.y) };
  }, [data, width, height]);

  return (
    <div ref={wrapRef} className="w-full">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} className="rounded-xl">
        <rect width={width} height={height} fill="#0A1A2F" rx={12} />
        {Array.from({ length: 10 }).map((_, i) => (
          <line key={`v${i}`} x1={(width / 9) * i} x2={(width / 9) * i} y1={0} y2={height} stroke="#12294A" strokeWidth={1} />
        ))}
        {Array.from({ length: 6 }).map((_, i) => (
          <line key={`h${i}`} x1={0} x2={width} y1={(height / 5) * i} y2={(height / 5) * i} stroke="#12294A" strokeWidth={1} />
        ))}

        {pts.length > 1 && (
          <path d={pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.px.toFixed(1)},${p.py.toFixed(1)}`).join(" ")}
            fill="none" stroke="#2B4A7A" strokeWidth={2.5} opacity={0.55} />
        )}
        {pts.filter((_, i) => i % 2 === 0).map((p, i) => (
          <circle key={i} cx={p.px} cy={p.py} r={3} fill={riskColor(p.p)} opacity={0.92}>
            <title>{`P(degraded) ${(p.p * 100).toFixed(0)}%`}</title>
          </circle>
        ))}

        {head && (
          <g>
            <circle cx={head.px} cy={head.py} r={10} fill="none" stroke={BEIHANG.accent} strokeWidth={2}>
              <animate attributeName="r" values="10;16;10" dur="1.6s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite" />
            </circle>
            <circle cx={head.px} cy={head.py} r={5.5} fill={BEIHANG.accent} />
          </g>
        )}

        {!pts.length && (
          <text x={width / 2} y={height / 2} textAnchor="middle" fontSize={15} fontWeight={700} fill="#5B7BA6">
            Press Play to stream the trajectory
          </text>
        )}

        <g transform="translate(16,16)">
          {[
            { c: "#2E7D32", l: "CLEAN" },
            { c: "#E1A100", l: "WARNING" },
            { c: "#C0392B", l: "DEGRADED" },
          ].map((it, i) => (
            <g key={it.l} transform={`translate(0, ${i * 22})`}>
              <circle cx={6} cy={6} r={6} fill={it.c} />
              <text x={18} y={11} fontSize={13} fontWeight={700} fill="#DCE6F2">{it.l}</text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
