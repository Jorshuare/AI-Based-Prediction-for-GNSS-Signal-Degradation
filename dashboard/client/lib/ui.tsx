"use client";
import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { BEIHANG } from "./colors";
import { FiImage, FiFileText } from "./icons";
import { downloadCSV, downloadSvgAsPng } from "./export";

/* ---------------------------------------------------------------- hooks */

/** Measure an element's width so SVG charts can be truly responsive. */
export function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

/** Avoid SSR/CSR mismatch for time strings etc. — render only after mount. */
export function useMounted() {
  const [m, setM] = useState(false);
  useEffect(() => setM(true), []);
  return m;
}

/* ------------------------------------------------------------- primitives */

export function Card({ children, className = "", delay = 0, pad = true }: {
  children: React.ReactNode; className?: string; delay?: number; pad?: boolean;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-2xl bg-white shadow-[0_2px_16px_rgba(16,40,80,0.07)] ring-1 ring-black/[0.04] ${pad ? "p-6" : ""} ${className}`}
    >
      {children}
    </motion.section>
  );
}

export function SectionTitle({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <div className="mb-4 flex items-center gap-2">
      <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>
        {children}
      </h3>
      {hint && <InfoDot text={hint} />}
    </div>
  );
}

/** Hover/focus info dot with an accessible tooltip. */
export function InfoDot({ text }: { text: string }) {
  return (
    <Tooltip text={text}>
      <span
        className="inline-flex h-5 w-5 cursor-help items-center justify-center rounded-full text-[11px] font-bold text-white"
        style={{ background: BEIHANG.secondary }}
        aria-label={text}
      >
        i
      </span>
    </Tooltip>
  );
}

/** Lightweight, dependency-free tooltip that follows the wrapped element. */
export function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <motion.span
          initial={{ opacity: 0, y: 4, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.14 }}
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-xl px-3 py-2 text-xs font-medium leading-relaxed text-white shadow-xl"
          style={{ background: "#0B1F3A" }}
        >
          {text}
          <span
            className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1 rotate-45"
            style={{ background: "#0B1F3A" }}
          />
        </motion.span>
      )}
    </span>
  );
}

/** Animated count-up number. */
export function AnimatedNumber({ value, decimals = 0, suffix = "" }: {
  value: number; decimals?: number; suffix?: string;
}) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);
  useEffect(() => {
    const from = prev.current;
    const to = value;
    const start = performance.now();
    const dur = 450;
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min((t - start) / dur, 1);
      const e = 1 - Math.pow(1 - k, 3);
      setDisplay(from + (to - from) * e);
      if (k < 1) raf = requestAnimationFrame(tick);
      else prev.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{display.toFixed(decimals)}{suffix}</>;
}

/* ----------------------------------------------------------- export buttons */

/** Download the first <svg> found inside `targetRef` as a PNG. */
export function ExportPng({ targetRef, filename }: {
  targetRef: React.RefObject<HTMLElement | null>; filename: string;
}) {
  return (
    <button
      type="button"
      title="Download chart as PNG"
      onClick={async () => {
        const svg = targetRef.current?.querySelector("svg");
        if (svg) await downloadSvgAsPng(svg as SVGSVGElement, filename);
      }}
      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold transition hover:bg-black/5"
      style={{ color: BEIHANG.slate }}
    >
      <FiImage size={14} /> PNG
    </button>
  );
}

/** Download an array of flat rows as CSV. */
export function ExportCsv({ rows, filename, label = "CSV" }: {
  rows: Record<string, unknown>[]; filename: string; label?: string;
}) {
  return (
    <button
      type="button"
      title="Download data as CSV"
      disabled={!rows.length}
      onClick={() => downloadCSV(rows, filename)}
      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold transition hover:bg-black/5 disabled:opacity-40"
      style={{ color: BEIHANG.slate }}
    >
      <FiFileText size={14} /> {label}
    </button>
  );
}

/** A Card with a title row (info-dot + PNG/CSV export) and a ref'd chart body. */
export function ChartCard({ title, hint, csvRows, csvName, children, delay = 0, className = "" }: {
  title: string;
  hint?: string;
  csvRows?: Record<string, unknown>[];
  csvName?: string;
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);
  return (
    <Card delay={delay} className={className}>
      <div className="mb-4 flex items-center gap-2">
        <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>{title}</h3>
        {hint && <InfoDot text={hint} />}
        <div className="ml-auto flex items-center gap-1">
          {csvRows && <ExportCsv rows={csvRows} filename={csvName ?? "data.csv"} />}
          <ExportPng targetRef={bodyRef} filename={`${title.replace(/[^\w]+/g, "_").toLowerCase()}.png`} />
        </div>
      </div>
      <div ref={bodyRef}>{children}</div>
    </Card>
  );
}

/* ------------------------------------------------- SVG chart tooltip layer */

type ChartTip = { x: number; y: number; content: React.ReactNode } | null;
const TipCtx = createContext<{ tip: ChartTip; setTip: (t: ChartTip) => void } | null>(null);

export function ChartTooltipHost({ children }: { children: React.ReactNode }) {
  const [tip, setTip] = useState<ChartTip>(null);
  return (
    <TipCtx.Provider value={{ tip, setTip }}>
      <div className="relative w-full">
        {children}
        {tip && (
          <div
            className="pointer-events-none absolute z-40 -translate-x-1/2 -translate-y-full rounded-lg px-2.5 py-1.5 text-[11px] font-semibold text-white shadow-lg"
            style={{ left: tip.x, top: tip.y - 8, background: "#0B1F3A" }}
          >
            {tip.content}
          </div>
        )}
      </div>
    </TipCtx.Provider>
  );
}

export function useChartTip() {
  const ctx = useContext(TipCtx);
  return ctx ?? { tip: null, setTip: () => {} };
}
