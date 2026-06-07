"use client";
import { motion } from "framer-motion";
import { FiShield, FiAlertTriangle, FiAlertOctagon } from "@/lib/icons";
import { useT } from "@/lib/i18n";
import type { Horizon } from "@/lib/types";

/**
 * Plain-language status for non-expert users: what the numbers MEAN and what the
 * vehicle is doing about it. No jargon.
 */
export default function PlainStatus({ pDeg, horizon }: { pDeg: number; horizon: Horizon }) {
  const { t } = useT();
  const state =
    pDeg < 0.3
      ? {
          bg: "#ECFDF3", fg: "#127A3E", ring: "#86E0AC", Icon: FiShield,
          title: t("status_healthy_t"),
          body: t("status_healthy_b", { h: horizon }),
        }
      : pDeg < 0.7
      ? {
          bg: "#FEF6E7", fg: "#8A6400", ring: "#F3D78A", Icon: FiAlertTriangle,
          title: t("status_dropping_t"),
          body: t("status_dropping_b", { h: horizon }),
        }
      : {
          bg: "#FDECEA", fg: "#8E2418", ring: "#F2B3AB", Icon: FiAlertOctagon,
          title: t("status_unreliable_t"),
          body: t("status_unreliable_b", { h: horizon }),
        };

  const { Icon } = state;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-4 rounded-2xl p-5 ring-1"
      style={{ background: state.bg, borderColor: state.ring }}
    >
      <motion.span
        key={state.title}
        initial={{ scale: 0.6, rotate: -8 }} animate={{ scale: 1, rotate: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 18 }}
        className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white"
        style={{ background: state.fg }}
      >
        <Icon size={22} />
      </motion.span>
      <div>
        <div className="text-lg font-extrabold" style={{ color: state.fg }}>{state.title}</div>
        <p className="mt-1 text-sm font-medium leading-relaxed" style={{ color: state.fg }}>
          {state.body}
        </p>
      </div>
    </motion.div>
  );
}
