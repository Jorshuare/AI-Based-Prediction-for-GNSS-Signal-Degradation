"use client";
import { motion } from "framer-motion";
import { BEIHANG, riskColor, classify } from "@/lib/colors";
import { AnimatedNumber } from "@/lib/ui";

/** Circular risk gauge — properly centred, animated arc, large legible type. */
export default function SignalGauge({ pDegraded, confidence, size = 240 }: {
  pDegraded: number;
  confidence?: number;
  size?: number;
}) {
  const stroke = 20;
  const r = (size - stroke) / 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, pDegraded));
  const color = riskColor(pDegraded);
  const cls = classify(pDegraded);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={c} cy={c} r={r} fill="none" stroke={BEIHANG.mist} strokeWidth={stroke} />
          <motion.circle
            cx={c} cy={c} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={circ}
            initial={false}
            animate={{ strokeDashoffset: circ * (1 - pct), stroke: color }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-extrabold tabular-nums" style={{ color: BEIHANG.primary }}>
            <AnimatedNumber value={pct * 100} decimals={0} suffix="%" />
          </span>
          <span className="text-xs font-bold tracking-wide" style={{ color: BEIHANG.slate }}>
            P(DEGRADED)
          </span>
        </div>
      </div>

      <motion.span
        key={cls}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="mt-4 rounded-full px-5 py-1.5 text-sm font-extrabold tracking-wide text-white shadow-md"
        style={{ background: color }}
      >
        {cls}
      </motion.span>
      {confidence !== undefined && (
        <span className="mt-1.5 text-xs font-medium" style={{ color: BEIHANG.slate }}>
          confidence {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
}
