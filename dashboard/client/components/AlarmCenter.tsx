"use client";
import { AnimatePresence, motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { FiAlertOctagon, FiAlertTriangle, FiInfo, FiCheckCircle } from "@/lib/icons";

export interface Alarm {
  id: string;
  level: "CRITICAL" | "WARNING" | "INFO";
  message: string;
  time: string;
}

const STYLE = {
  CRITICAL: { bg: "#FDECEA", border: "#C0392B", text: "#8E2418", Icon: FiAlertOctagon },
  WARNING: { bg: "#FEF6E7", border: "#E1A100", text: "#8A6400", Icon: FiAlertTriangle },
  INFO: { bg: "#EAF1F8", border: BEIHANG.secondary, text: BEIHANG.primary, Icon: FiInfo },
} as const;

export default function AlarmCenter({ alarms }: { alarms: Alarm[] }) {
  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>
          Alerts &amp; Notifications
        </h3>
        {alarms.length > 0 && (
          <motion.span
            initial={{ scale: 0 }} animate={{ scale: 1 }}
            className="flex h-6 min-w-6 items-center justify-center rounded-full px-2 text-xs font-bold text-white"
            style={{ background: "#C0392B" }}
          >
            {alarms.length}
          </motion.span>
        )}
      </div>

      <div className="flex flex-col gap-2.5 overflow-hidden">
        <AnimatePresence initial={false} mode="popLayout">
          {alarms.length === 0 && (
            <motion.div
              key="ok" layout
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2.5 rounded-xl p-4 text-sm font-semibold"
              style={{ background: "#ECFDF3", color: "#127A3E" }}
            >
              <FiCheckCircle size={18} /> All systems nominal. Signal is healthy.
            </motion.div>
          )}
          {alarms.map((a) => {
            const s = STYLE[a.level];
            const Icon = s.Icon;
            return (
              <motion.div
                key={a.id}
                layout
                initial={{ opacity: 0, x: 48, scale: 0.94, filter: "blur(4px)" }}
                animate={{ opacity: 1, x: 0, scale: 1, filter: "blur(0px)" }}
                exit={{ opacity: 0, height: 0, marginBottom: 0, scale: 0.96 }}
                transition={{ type: "spring", stiffness: 360, damping: 26 }}
                className="overflow-hidden rounded-xl border-l-4 p-3.5 shadow-sm"
                style={{ background: s.bg, borderColor: s.border }}
              >
                <div className="flex items-center justify-between text-xs font-extrabold" style={{ color: s.text }}>
                  <span className="flex items-center gap-1.5">
                    <motion.span
                      animate={a.level === "CRITICAL" ? { scale: [1, 1.3, 1], opacity: [1, 0.6, 1] } : {}}
                      transition={{ repeat: Infinity, duration: 1.2 }}
                      className="flex"
                    >
                      <Icon size={15} />
                    </motion.span>
                    {a.level}
                  </span>
                  <span className="font-medium opacity-60">{a.time}</span>
                </div>
                <div className="mt-1 text-sm font-medium leading-snug" style={{ color: s.text }}>
                  {a.message}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
