"use client";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";

import type { ReactNode } from "react";

export interface TabDef {
  id: string;
  label: string;
  icon: ReactNode;
}

export default function Tabs({ tabs, active, onChange }: {
  tabs: TabDef[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-2xl bg-white p-1.5 shadow-[0_2px_16px_rgba(16,40,80,0.07)] ring-1 ring-black/[0.04]">
      {tabs.map((t) => {
        const on = t.id === active;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className="relative flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition"
            style={{ color: on ? "#fff" : BEIHANG.slate }}
          >
            {on && (
              <motion.span
                layoutId="tab-pill"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
                className="absolute inset-0 rounded-xl"
                style={{ background: BEIHANG.primary }}
              />
            )}
            <span className="relative z-10">{t.icon}</span>
            <span className="relative z-10">{t.label}</span>
          </button>
        );
      })}
    </div>
  );
}
