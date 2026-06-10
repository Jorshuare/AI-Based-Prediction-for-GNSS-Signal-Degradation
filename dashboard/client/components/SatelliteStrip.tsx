"use client";
import { BEIHANG } from "@/lib/colors";
import { useElementWidth, InfoDot } from "@/lib/ui";
import { FiRadio } from "@/lib/icons";
import { useT } from "@/lib/i18n";

/**
 * Satellite-count strip across the whole drive. Fewer satellites = worse geometry =
 * higher chance of a bad fix. The shaded band below 5 marks the "degraded" regime.
 */
export default function SatelliteStrip({ nsat, height = 130 }: { nsat: number[]; height?: number }) {
  const { t } = useT();
  const [ref, W] = useElementWidth<HTMLDivElement>();
  const width = Math.max(W, 280);
  const pad = { l: 30, r: 12, t: 12, b: 20 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const n = Math.max(nsat.length, 1);
  const maxS = Math.max(12, ...nsat);
  const x = (i: number) => pad.l + (innerW * i) / Math.max(n - 1, 1);
  const y = (v: number) => pad.t + innerH * (1 - v / maxS);

  const area = nsat.map((s, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(s).toFixed(1)}`).join(" ") +
    ` L${x(n - 1).toFixed(1)},${y(0).toFixed(1)} L${x(0).toFixed(1)},${y(0).toFixed(1)} Z`;
  const avg = nsat.reduce((a, b) => a + b, 0) / n;

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <FiRadio size={16} color={BEIHANG.secondary} />
        <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>{t("sats_in_view")}</h3>
        <InfoDot text="How many satellites the receiver could use at each moment. Below about five, the geometry is poor and the position can jump. The pink band marks those degraded stretches." />
        <span className="ml-auto text-sm font-bold" style={{ color: BEIHANG.slate }}>{t("sat_avg")} {avg.toFixed(1)}</span>
      </div>
      <div ref={ref}>
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
          {/* degraded band (<=5 sats) */}
          <rect x={pad.l} y={y(5)} width={innerW} height={pad.t + innerH - y(5)} fill="#C0392B" opacity={0.08} />
          <line x1={pad.l} x2={width - pad.r} y1={y(5)} y2={y(5)} stroke="#C0392B" strokeWidth={1} strokeDasharray="4 3" opacity={0.5} />
          {[4, 8, 12].map((g) => (
            <text key={g} x={pad.l - 6} y={y(g) + 4} textAnchor="end" fontSize={10} fontWeight={600} fill={BEIHANG.slate}>{g}</text>
          ))}
          <path d={area} fill={BEIHANG.secondary} fillOpacity={0.18} />
          <path d={nsat.map((s, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(s).toFixed(1)}`).join(" ")}
            fill="none" stroke={BEIHANG.primary} strokeWidth={1.8} />
        </svg>
      </div>
    </div>
  );
}
