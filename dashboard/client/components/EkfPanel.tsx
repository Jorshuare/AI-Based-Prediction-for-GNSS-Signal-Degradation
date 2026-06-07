"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { BEIHANG } from "@/lib/colors";
import { useElementWidth, InfoDot } from "@/lib/ui";
import { useT } from "@/lib/i18n";
import type { EkfResult } from "@/lib/types";

const LABELS: Record<string, string> = {
  gnss_raw: "GNSS raw",
  cv_kf_fixed: "CV-KF",
  ekf9_fixed: "EKF",
  ekf9_adaptive: "EKF adapt",
  ekf9_aided_fixed: "Aided EKF (fixed-R)",
  ekf9_aided_adaptive: "Aided EKF (adaptive-R)",
};

export default function EkfPanel() {
  const { t } = useT();
  const [ekf, setEkf] = useState<EkfResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sweepRef, sweepW] = useElementWidth<HTMLDivElement>();

  useEffect(() => { api.ekf().then(setEkf).catch((e) => setErr(String(e))); }, []);

  if (err) return <p className="text-sm" style={{ color: BEIHANG.slate }}>EKF analytics unavailable ({err}).</p>;
  if (!ekf) return <p className="text-sm" style={{ color: BEIHANG.slate }}>Loading EKF analytics…</p>;

  const order = Object.keys(LABELS).filter((k) => k in ekf.rmse_blocked_segment);
  const maxV = Math.max(...order.map((k) => ekf.rmse_blocked_segment[k]));
  const sweep = ekf.severity_sweep ?? [];
  const W = Math.max(sweepW, 280), H = 380, pad = 40;
  const sMax = Math.max(...sweep.flatMap((r) => [r.raw, r.fixed_R, r.adaptive_R]), 1);
  const sx = (i: number) => pad + ((W - 2 * pad) * i) / Math.max(sweep.length - 1, 1);
  const sy = (v: number) => H - pad - ((H - 2 * pad) * v) / sMax;
  const path = (key: "raw" | "fixed_R" | "adaptive_R") =>
    sweep.map((r, i) => `${i === 0 ? "M" : "L"}${sx(i).toFixed(1)},${sy(r[key]).toFixed(1)}`).join(" ");

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
      {/* Bars */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <h4 className="text-base font-bold" style={{ color: BEIHANG.primary }}>{t("ekf_blocked_title")}</h4>
          <InfoDot text="Position error (metres) measured only during GNSS-blockage windows, vs cm-level truth. Lower is better." />
        </div>
        <div className="flex flex-col gap-2.5">
          {order.map((k, idx) => {
            const v = ekf.rmse_blocked_segment[k];
            const best = k === "ekf9_aided_fixed";
            return (
              <div key={k} className="flex items-center gap-3">
                <span className="w-36 shrink-0 text-right text-sm font-bold" style={{ color: BEIHANG.ink }}>{LABELS[k]}</span>
                <div className="h-9 flex-1 overflow-hidden rounded-lg" style={{ background: BEIHANG.mist }}>
                  <motion.div className="h-full rounded-lg"
                    initial={{ width: 0 }} animate={{ width: `${(v / maxV) * 100}%` }}
                    transition={{ delay: idx * 0.06, duration: 0.5 }}
                    style={{ background: best ? BEIHANG.primary : BEIHANG.secondary }} />
                </div>
                <span className="w-16 text-base font-extrabold tabular-nums" style={{ color: best ? BEIHANG.primary : BEIHANG.slate }}>
                  {v.toFixed(1)}m
                </span>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-sm leading-relaxed" style={{ color: BEIHANG.slate }}>
          {t("ekf_caption", {
            v: ekf.rmse_blocked_segment["ekf9_aided_fixed"]?.toFixed(1) ?? "—",
            g: ekf.gains_vs_raw_blocked["ekf9_aided_fixed"],
          })}
        </p>
      </div>

      {/* Sweep */}
      <div ref={sweepRef}>
        <div className="mb-3 flex items-center gap-2">
          <h4 className="text-base font-bold" style={{ color: BEIHANG.primary }}>{t("ekf_when_title")}</h4>
          <InfoDot text="Sweeps how severe the GNSS multipath is. With aiding, keeping GNSS (fixed-R) stays best — inflating R throws away heading observability." />
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
          {[
            { k: "raw" as const, c: BEIHANG.slate, d: "5 4" },
            { k: "fixed_R" as const, c: BEIHANG.primary, d: "" },
            { k: "adaptive_R" as const, c: BEIHANG.accent, d: "" },
          ].map((s) => (
            <path key={s.k} d={path(s.k)} fill="none" stroke={s.c} strokeWidth={2.6} strokeDasharray={s.d} strokeLinejoin="round" />
          ))}
          {sweep.map((r, i) => (
            <text key={i} x={sx(i)} y={H - 8} fontSize={11} textAnchor="middle" fill={BEIHANG.slate}>{r.bias_max_m}</text>
          ))}
        </svg>
        <div className="mt-1 flex flex-wrap gap-4 text-xs font-bold">
          <span style={{ color: BEIHANG.slate }}>— {t("ekf_raw")}</span>
          <span style={{ color: BEIHANG.primary }}>— {t("ekf_fixed_ours")}</span>
          <span style={{ color: BEIHANG.accent }}>— {t("ekf_adaptive")}</span>
          <span className="ml-auto" style={{ color: BEIHANG.slate }}>{t("ekf_xaxis")}</span>
        </div>
      </div>
    </div>
  );
}
