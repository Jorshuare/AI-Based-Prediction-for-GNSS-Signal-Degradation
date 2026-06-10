"use client";
import { motion } from "framer-motion";
import type { IconType } from "react-icons";
import { BEIHANG, SIGNAL } from "@/lib/colors";
import { Tooltip } from "@/lib/ui";
import { useT } from "@/lib/i18n";
import { FiActivity, FiTrendingUp, FiAlertOctagon, FiCheckCircle, FiClock, FiBarChart2, FiInfo } from "@/lib/icons";
import type { Prediction } from "@/lib/types";

function Card({ label, value, accent, Icon, hint, i }: {
  label: string; value: string; accent: string; Icon: IconType; hint: string; i: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04, duration: 0.35 }}
      whileHover={{ y: -3 }}
      className="rounded-2xl bg-white p-4 shadow-[0_2px_16px_rgba(16,40,80,0.07)] ring-1 ring-black/[0.04]"
      style={{ borderTop: `3px solid ${accent}` }}
    >
      <div className="flex items-center justify-between">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl" style={{ background: `${accent}1A`, color: accent }}>
          <Icon size={18} />
        </span>
        <Tooltip text={hint}>
          <span className="flex cursor-help text-slate-300"><FiInfo size={14} /></span>
        </Tooltip>
      </div>
      <div className="mt-2.5 text-[13px] font-semibold" style={{ color: BEIHANG.slate }}>{label}</div>
      <div className="mt-0.5 text-[26px] font-extrabold leading-tight tabular-nums" style={{ color: BEIHANG.primary }}>
        {value}
      </div>
    </motion.div>
  );
}

export default function MetricsGrid({ data, total, currentIdx }: { data: Prediction[]; total: number; currentIdx?: number }) {
  const { t } = useT();
  const n = data.length;
  const pdeg = data.map((d) => d.p_degraded_5s);
  const mean = n ? pdeg.reduce((a, b) => a + b, 0) / n : 0;
  const max = n ? Math.max(...pdeg) : 0;
  const degraded = pdeg.filter((p) => p >= 0.7).length;
  const clean = pdeg.filter((p) => p < 0.3).length;
  const firstDeg = data.findIndex((d) => d.pred_5s === "DEGRADED");
  const epochDisplay = total ? `${(currentIdx ?? n).toLocaleString()} / ${total.toLocaleString()}` : `${n}`;

  const cards = [
    { label: t("kpi_epochs"), value: epochDisplay, accent: BEIHANG.secondary, Icon: FiBarChart2, hint: "Epochs streamed so far out of the full scenario. The trajectory map shows the complete route from the start." },
    { label: t("kpi_mean"), value: `${(mean * 100).toFixed(1)}%`, accent: BEIHANG.accent, Icon: FiActivity, hint: "Average predicted degradation probability at the +5 s horizon." },
    { label: t("kpi_peak"), value: `${(max * 100).toFixed(1)}%`, accent: SIGNAL.DEGRADED, Icon: FiTrendingUp, hint: "Worst-case degradation probability seen in the stream." },
    { label: t("kpi_clean"), value: `${clean}`, accent: SIGNAL.CLEAN, Icon: FiCheckCircle, hint: "Epochs predicted CLEAN (P(degraded) below 30%)." },
    { label: t("kpi_degraded"), value: `${degraded}`, accent: SIGNAL.DEGRADED, Icon: FiAlertOctagon, hint: "Epochs predicted DEGRADED (P(degraded) at or above 70%): the safety-critical ones." },
    { label: t("kpi_first"), value: firstDeg >= 0 ? `#${firstDeg}` : "—", accent: BEIHANG.primary, Icon: FiClock, hint: "Index of the first epoch flagged DEGRADED: the earliest warning." },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
      {cards.map((c, i) => <Card key={c.label} {...c} i={i} />)}
    </div>
  );
}
