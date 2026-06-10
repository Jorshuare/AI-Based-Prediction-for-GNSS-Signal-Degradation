"use client";
import { AnimatePresence, motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { FiAlertOctagon, FiAlertTriangle, FiCheckCircle } from "@/lib/icons";
import { AnimatedNumber } from "@/lib/ui";
import { useT } from "@/lib/i18n";

/** A coalesced alert episode (a contiguous run of same-level epochs), not one-per-epoch. */
export interface AlertEpisode {
  id: string;
  level: "CRITICAL" | "WARNING";
  startEpoch: number;
  endEpoch: number;
  startTime: string;
  count: number;   // epochs in the episode (~seconds at 1 Hz)
  peakP: number;   // worst probability seen
}

const STYLE = {
  CRITICAL: { bg: "#FDECEA", border: "#C0392B", text: "#8E2418", Icon: FiAlertOctagon, key: "degraded" },
  WARNING: { bg: "#FEF6E7", border: "#E1A100", text: "#8A6400", Icon: FiAlertTriangle, key: "warning" },
} as const;

export default function AlarmCenter({ active, history }: {
  active: AlertEpisode | null;
  history: AlertEpisode[];
}) {
  const { t } = useT();

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>{t("alerts")}</h3>
        {history.length > 0 && (
          <span className="flex h-6 min-w-6 items-center justify-center rounded-full px-2 text-xs font-bold text-white" style={{ background: BEIHANG.slate }}>
            {history.length}
          </span>
        )}
      </div>

      {/* Active episode — updates in place (seamless), keyed by level so it morphs not flickers */}
      <AnimatePresence mode="wait">
        {active ? (
          <motion.div
            key={active.level}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 320, damping: 26 }}
            className="rounded-xl border-l-4 p-4 shadow-sm"
            style={{ background: STYLE[active.level].bg, borderColor: STYLE[active.level].border }}
          >
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm font-extrabold" style={{ color: STYLE[active.level].text }}>
                <motion.span animate={{ scale: [1, 1.25, 1] }} transition={{ repeat: Infinity, duration: 1.2 }} className="flex">
                  {(() => { const I = STYLE[active.level].Icon; return <I size={18} />; })()}
                </motion.span>
                {t(STYLE[active.level].key)}
                <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide" style={{ background: STYLE[active.level].border, color: "#fff" }}>
                  {t("alert_ongoing")}
                </span>
              </span>
              <span className="text-xs font-medium opacity-60" style={{ color: STYLE[active.level].text }}>{active.startTime}</span>
            </div>
            <div className="mt-2 text-sm font-medium leading-snug" style={{ color: STYLE[active.level].text }}>
              {active.level === "CRITICAL" ? t("alert_crit_msg") : t("alert_warn_msg")}
            </div>
            <div className="mt-2 flex gap-4 text-xs font-bold" style={{ color: STYLE[active.level].text }}>
              <span>{t("alert_peak")} <AnimatedNumber value={active.peakP * 100} decimals={0} suffix="%" /></span>
              <span><AnimatedNumber value={active.count} decimals={0} />{t("secs")}</span>
            </div>
          </motion.div>
        ) : (
          <motion.div key="ok" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2.5 rounded-xl p-4 text-sm font-semibold" style={{ background: "#ECFDF3", color: "#127A3E" }}>
            <FiCheckCircle size={18} /> {t("nominal")}
          </motion.div>
        )}
      </AnimatePresence>

      {/* History — one entry per episode, accrues smoothly */}
      <div className="mt-3 text-xs font-bold" style={{ color: BEIHANG.slate }}>{t("alert_history")}</div>
      <div className="mt-2 flex flex-1 flex-col gap-1.5 overflow-y-auto pr-1" style={{ maxHeight: 190 }}>
        <AnimatePresence initial={false}>
          {history.length === 0 && (
            <motion.div key="none" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="rounded-lg px-3 py-2 text-xs" style={{ background: BEIHANG.mist, color: BEIHANG.slate }}>
              {t("alert_no_history")}
            </motion.div>
          )}
          {history.map((e) => (
            <motion.div key={e.id} layout
              initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
              transition={{ type: "spring", stiffness: 400, damping: 32 }}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs" style={{ background: BEIHANG.mist }}>
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: STYLE[e.level].border }} />
              <span className="font-bold" style={{ color: STYLE[e.level].text }}>{t(STYLE[e.level].key)}</span>
              <span className="opacity-60" style={{ color: BEIHANG.ink }}>{e.startTime}</span>
              <span className="ml-auto font-bold tabular-nums" style={{ color: BEIHANG.slate }}>
                {e.count}{t("secs")} · {t("alert_peak")} {(e.peakP * 100).toFixed(0)}%
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
