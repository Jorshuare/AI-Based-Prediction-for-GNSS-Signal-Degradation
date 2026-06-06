"use client";
import { motion } from "framer-motion";
import { BEIHANG, SIGNAL } from "@/lib/colors";
import type { HorizonProbs } from "@/lib/types";

/** Larger, animated CLEAN/WARNING/DEGRADED probability bars. */
export default function ProbabilityBars({ probs }: { probs: HorizonProbs }) {
  const rows = [
    { label: "CLEAN", v: probs.clean, c: SIGNAL.CLEAN },
    { label: "WARNING", v: probs.warning, c: SIGNAL.WARNING },
    { label: "DEGRADED", v: probs.degraded, c: SIGNAL.DEGRADED },
  ];
  return (
    <div className="flex w-full flex-col gap-5">
      {rows.map((r) => (
        <div key={r.label}>
          <div className="mb-1.5 flex items-center justify-between text-sm font-bold">
            <span style={{ color: BEIHANG.ink }}>{r.label}</span>
            <span style={{ color: r.c }} className="tabular-nums text-base">
              {(r.v * 100).toFixed(1)}%
            </span>
          </div>
          <div className="h-3.5 w-full overflow-hidden rounded-full" style={{ background: BEIHANG.mist }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: r.c }}
              initial={false}
              animate={{ width: `${r.v * 100}%` }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
