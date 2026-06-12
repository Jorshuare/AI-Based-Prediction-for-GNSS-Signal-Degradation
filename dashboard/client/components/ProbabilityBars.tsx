"use client";
import { motion } from "framer-motion";
import { BEIHANG, SIGNAL } from "@/lib/colors";
import { useT } from "@/lib/i18n";
import type { HorizonProbs } from "@/lib/types";

/** Larger, animated CLEAN/WARNING/DEGRADED probability bars. */
export default function ProbabilityBars({ probs }: { probs: HorizonProbs }) {
  const { t } = useT();
  const rows = [
    { label: t("clean"), v: probs.clean, c: SIGNAL.CLEAN },
    { label: t("warning"), v: probs.warning, c: SIGNAL.WARNING },
    { label: t("degraded"), v: probs.degraded, c: SIGNAL.DEGRADED },
  ];
  return (
    <div className="flex w-full flex-col gap-5">
      {rows.map((r) => {
        const pct = Math.min(100, Math.max(0, (r.v ?? 0) * 100));
        return (
          <div key={r.label}>
            <div className="mb-1.5 flex items-center justify-between text-sm font-bold">
              <span style={{ color: BEIHANG.ink }}>{r.label}</span>
              <span style={{ color: r.c }} className="tabular-nums text-base">
                {pct.toFixed(1)}%
              </span>
            </div>
            <div className="h-3.5 w-full overflow-hidden rounded-full" style={{ background: BEIHANG.mist }}>
              <motion.div
                className="h-full rounded-full"
                style={{ background: r.c }}
                initial={false}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
