"use client";
import { useMemo } from "react";
import { BEIHANG, riskColor } from "@/lib/colors";
import { useElementWidth } from "@/lib/ui";
import type { Prediction } from "@/lib/types";

/**
 * Risk-coloured trajectory map with progressive reveal.
 *
 * Props
 * -----
 * path        – complete pre-loaded predictions for the scenario
 * currentIdx  – how many epochs have been streamed so far; if provided,
 *               only path[0..currentIdx] is rendered (real-time discovery effect).
 *               If undefined, renders the full path (static / post-run view).
 * liveHead    – the latest streamed prediction (pulsing current-position indicator)
 * height      – SVG pixel height (default 420)
 */
export default function TrajectoryMap({
  path,
  currentIdx,
  liveHead,
  height = 420,
  data,
}: {
  path?: Prediction[];
  currentIdx?: number;
  liveHead?: Prediction | null;
  height?: number;
  data?: Prediction[];   // deprecated – use path
}) {
  const full_src = path ?? data ?? [];
  // Slice to revealed portion; if no currentIdx show everything (e.g. post-run)
  const pts_src = currentIdx !== undefined
    ? full_src.slice(0, currentIdx + 1)
    : full_src;
  const [wrapRef, W] = useElementWidth<HTMLDivElement>();
  const width = Math.max(W, 280);

  const { pts, headPx } = useMemo(() => {
    const valid = pts_src.filter((d) => d.x != null && d.y != null && isFinite(d.x) && isFinite(d.y));
    if (!valid.length) return { pts: [] as { px: number; py: number; p: number }[], headPx: null as null | { px: number; py: number } };

    // Use current visible points for bounding box so the path fills the map
    // as it is revealed. The scale will gently grow as more route is discovered.
    const bbox = valid;
    const xs = bbox.map((d) => d.x);
    const ys = bbox.map((d) => d.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const pad = 40;
    const sx = (maxX - minX) || 1;
    const sy = (maxY - minY) || 1;
    const s  = Math.min((width - 2 * pad) / sx, (height - 2 * pad) / sy);
    const ox = (width - s * sx) / 2;
    const oy = (height - s * sy) / 2;

    const proj = (x: number, y: number) => ({
      px: ox + (x - minX) * s,
      py: height - (oy + (y - minY) * s),
    });

    const pts = valid.map((d) => ({ ...proj(d.x, d.y), p: d.p_degraded_5s }));

    // Current position: use liveHead if provided, else last point in path
    const headSrc = liveHead ?? valid[valid.length - 1];
    const headPx = headSrc && isFinite(headSrc.x) && isFinite(headSrc.y)
      ? proj(headSrc.x, headSrc.y)
      : null;

    return { pts, headPx };
  }, [pts_src, liveHead, width, height]);

  // Thin connecting polyline (drawn below the coloured dots so dots are on top)
  const polyline = pts.length > 1
    ? pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.px.toFixed(1)},${p.py.toFixed(1)}`).join(" ")
    : "";

  // Downsample dots for performance: render every 3rd point when > 3000 pts
  const step = pts.length > 3000 ? 3 : pts.length > 1000 ? 2 : 1;

  return (
    <div ref={wrapRef} className="w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        className="rounded-xl"
        style={{ display: "block" }}
      >
        {/* Dark background */}
        <rect width={width} height={height} fill="#0A1A2F" rx={12} />

        {/* Subtle grid */}
        {Array.from({ length: 10 }).map((_, i) => (
          <line key={`v${i}`} x1={(width / 9) * i} x2={(width / 9) * i}
            y1={0} y2={height} stroke="#12294A" strokeWidth={1} />
        ))}
        {Array.from({ length: 7 }).map((_, i) => (
          <line key={`h${i}`} x1={0} x2={width}
            y1={(height / 6) * i} y2={(height / 6) * i} stroke="#12294A" strokeWidth={1} />
        ))}

        {/* Connecting polyline (road) */}
        {polyline && (
          <path d={polyline} fill="none" stroke="#1E3D6B" strokeWidth={3} opacity={0.6} />
        )}

        {/* Risk-coloured dots */}
        {pts
          .filter((_, i) => i % step === 0)
          .map((p, i) => (
            <circle key={i} cx={p.px} cy={p.py} r={4}
              fill={riskColor(p.p)} opacity={0.88}>
              <title>{`P(degraded) ${(p.p * 100).toFixed(0)}%`}</title>
            </circle>
          ))}

        {/* Pulsing current-position indicator */}
        {headPx && (
          <g>
            <circle cx={headPx.px} cy={headPx.py} r={14} fill="none"
              stroke={BEIHANG.accent} strokeWidth={2.5} opacity={0.5}>
              <animate attributeName="r" values="12;20;12" dur="1.6s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.5;0.1;0.5" dur="1.6s" repeatCount="indefinite" />
            </circle>
            <circle cx={headPx.px} cy={headPx.py} r={7}
              fill={BEIHANG.accent} stroke="white" strokeWidth={2} />
          </g>
        )}

        {/* Empty state */}
        {!pts.length && (
          <text x={width / 2} y={height / 2} textAnchor="middle"
            fontSize={15} fontWeight={700} fill="#5B7BA6">
            Press Play, route reveals epoch by epoch as data streams
          </text>
        )}

        {/* Legend */}
        <g transform="translate(16, 16)">
          {[
            { c: "#2E7D32", l: "CLEAN" },
            { c: "#E1A100", l: "WARNING" },
            { c: "#C0392B", l: "DEGRADED" },
          ].map((it, i) => (
            <g key={it.l} transform={`translate(0, ${i * 26})`}>
              <circle cx={8} cy={8} r={7} fill={it.c} />
              <text x={22} y={13} fontSize={14} fontWeight={700} fill="#DCE6F2">{it.l}</text>
            </g>
          ))}
        </g>

        {/* Point count / progress label */}
        {full_src.length > 0 && (
          <text x={width - 12} y={height - 10} textAnchor="end"
            fontSize={11} fill="#3A5A7A" fontWeight={600}>
            {pts.length.toLocaleString()} / {full_src.length.toLocaleString()} pts
          </text>
        )}
      </svg>
    </div>
  );
}
