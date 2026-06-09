"use client";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { FiClock, FiTarget, FiCheckCircle } from "@/lib/icons";
import { InfoDot } from "@/lib/ui";

/**
 * Prediction lead-time tracker. Demonstrates the value of multi-horizon forecasting:
 * the long-range (+30 s) head raises the EARLY warning; the near-term (+5 s) head later
 * confirms degradation is IMMINENT. The gap between them is the realised early-warning lead.
 */
export default function LeadTimeCard({ warnEpoch, onsetEpoch, epochDt = 1 }: {
  warnEpoch: number | null;   // first +30 s DEGRADED forecast
  onsetEpoch: number | null;  // first +5 s DEGRADED forecast (imminent)
  epochDt?: number;           // seconds per epoch (NMEA ~1 Hz)
}) {
  const lead = warnEpoch != null && onsetEpoch != null ? Math.max(0, (onsetEpoch - warnEpoch) * epochDt) : null;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>Early-warning lead time</h3>
        <InfoDot text="How many seconds before degradation became imminent did the long-range (+30 s) forecast first raise the alarm? This is the head-start the driver/vehicle gets." />
      </div>

      <div className="flex items-center justify-between gap-3">
        <Step Icon={FiTarget} color={BEIHANG.accent} label="Early warning" sub="+30 s forecast"
          value={warnEpoch != null ? `epoch ${warnEpoch}` : "—"} active={warnEpoch != null} />
        <div className="flex flex-1 flex-col items-center">
          <motion.div
            className="h-0.5 w-full rounded-full"
            style={{ background: lead != null ? BEIHANG.primary : BEIHANG.line }}
            initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.6 }}
          />
          <span className="mt-1 text-xs font-bold" style={{ color: BEIHANG.slate }}>
            {lead != null ? `${lead.toFixed(0)} s head-start` : "monitoring"}
          </span>
        </div>
        <Step Icon={FiCheckCircle} color="#C0392B" label="Imminent" sub="+5 s forecast"
          value={onsetEpoch != null ? `epoch ${onsetEpoch}` : "—"} active={onsetEpoch != null} />
      </div>

      <div className="mt-4 flex items-center gap-2 rounded-xl px-4 py-3" style={{ background: BEIHANG.mist }}>
        <FiClock size={18} color={BEIHANG.secondary} />
        <span className="text-sm font-medium" style={{ color: BEIHANG.ink }}>
          {lead != null
            ? `The model foresaw this degradation ${lead.toFixed(0)} seconds early — enough time to hand off to backup sensors.`
            : "No degradation forecast yet. The +30 s head is watching for the earliest sign."}
        </span>
      </div>
    </div>
  );
}

function Step({ Icon, color, label, sub, value, active }: {
  Icon: React.ComponentType<{ size?: number; color?: string }>;
  color: string; label: string; sub: string; value: string; active: boolean;
}) {
  return (
    <div className="flex w-24 flex-col items-center text-center">
      <motion.span
        animate={active ? { scale: [1, 1.12, 1] } : {}} transition={{ repeat: active ? Infinity : 0, duration: 2 }}
        className="flex h-12 w-12 items-center justify-center rounded-full text-white"
        style={{ background: active ? color : "#C7D0DC" }}
      >
        <Icon size={22} />
      </motion.span>
      <span className="mt-2 text-xs font-extrabold" style={{ color: BEIHANG.ink }}>{label}</span>
      <span className="text-[11px] font-medium" style={{ color: BEIHANG.slate }}>{sub}</span>
      <span className="mt-0.5 text-[11px] font-bold tabular-nums" style={{ color: active ? color : BEIHANG.slate }}>{value}</span>
    </div>
  );
}
