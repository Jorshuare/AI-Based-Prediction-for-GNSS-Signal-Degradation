"use client";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { FiPlay, FiSquare } from "@/lib/icons";
import { useT } from "@/lib/i18n";
import type { Horizon, Scenario } from "@/lib/types";

/** Dataset picker + horizon + replay controls. */
export default function ControlBar({
  scenarios, scenario, onScenario, horizon, onHorizon,
  playing, onPlay, onStop, speed, onSpeed, progress,
}: {
  scenarios: Scenario[];
  scenario: string;
  onScenario: (s: string) => void;
  horizon: Horizon;
  onHorizon: (h: Horizon) => void;
  playing: boolean;
  onPlay: () => void;
  onStop: () => void;
  speed: number;
  onSpeed: (s: number) => void;
  progress: number;
}) {
  const { t } = useT();
  return (
    <div className="flex flex-wrap items-center gap-5 rounded-2xl bg-white p-4 shadow-[0_2px_16px_rgba(16,40,80,0.07)] ring-1 ring-black/[0.04]">
      <div className="flex items-center gap-2.5">
        <span className="text-sm font-bold" style={{ color: BEIHANG.slate }}>{t("dataset")}</span>
        <select
          value={scenario}
          onChange={(e) => onScenario(e.target.value)}
          className="rounded-xl border bg-white px-3 py-2 text-sm font-bold outline-none transition focus:ring-2"
          style={{ borderColor: BEIHANG.line, color: BEIHANG.ink }}
        >
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>{s.id}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="mr-1 text-sm font-bold" style={{ color: BEIHANG.slate }}>{t("horizon")}</span>
        {([5, 15, 30] as Horizon[]).map((h) => (
          <button key={h} onClick={() => onHorizon(h)}
            className="rounded-xl px-4 py-2 text-sm font-extrabold transition"
            style={{ background: horizon === h ? BEIHANG.primary : BEIHANG.mist, color: horizon === h ? "#fff" : BEIHANG.slate }}>
            +{h}s
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-3">
        <span className="text-sm font-bold" style={{ color: BEIHANG.slate }}>{t("speed")}</span>
        <input type="range" min={2} max={500} value={speed} onChange={(e) => onSpeed(Number(e.target.value))}
          className="w-28 accent-[#003360]" />
        <span className="w-16 text-sm font-bold tabular-nums" style={{ color: BEIHANG.slate }}>{speed} {t("eps")}</span>
        {!playing ? (
          <motion.button whileTap={{ scale: 0.95 }} onClick={onPlay}
            className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-extrabold text-white shadow-md" style={{ background: BEIHANG.primary }}>
            <FiPlay size={15} /> {t("play")}
          </motion.button>
        ) : (
          <motion.button whileTap={{ scale: 0.95 }} onClick={onStop}
            className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-extrabold text-white shadow-md" style={{ background: "#C0392B" }}>
            <FiSquare size={14} /> {t("stop")}
          </motion.button>
        )}
      </div>

      {/* progress bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: BEIHANG.mist }}>
        <motion.div className="h-full rounded-full" style={{ background: BEIHANG.accent }}
          animate={{ width: `${progress * 100}%` }} transition={{ duration: 0.2 }} />
      </div>
    </div>
  );
}
