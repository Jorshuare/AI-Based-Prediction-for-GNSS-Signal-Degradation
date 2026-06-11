"use client";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { BEIHANG } from "@/lib/colors";
import { Card, SectionTitle, InfoDot, ExportPng, useElementWidth } from "@/lib/ui";
import { FiNavigation, FiRadio, FiTarget, FiMap, FiGrid } from "@/lib/icons";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import SatelliteStrip from "@/components/SatelliteStrip";
import type { FusionResult } from "@/lib/types";

const EKF_FIXED_COLOR = "#00BFA5";
const TILE_SIZE = 256;
const MAP_ZOOM = 17;

const SERIES = [
  { key: "truth" as const, color: "#43A047", labelKey: "series_truth", w: 7 },
  { key: "gnss" as const, color: "#EF5350", labelKey: "series_gnss", w: 3.5, dash: "6 5" },
  { key: "aided_fixed" as const, color: EKF_FIXED_COLOR, labelKey: "series_fixed", w: 7 },
  { key: "aided_adapt" as const, color: "#FFB300", labelKey: "series_adapt", w: 5, dash: "10 5" },
];
type SeriesKey = (typeof SERIES)[number]["key"];

// ── OSM tile helpers ──────────────────────────────────────────────────────────

/** Convert lat/lon to global Web Mercator pixel at given zoom. */
function llToGlobalPx(lat: number, lon: number, z: number): [number, number] {
  const n = 2 ** z * TILE_SIZE;
  const gx = ((lon + 180) / 360) * n;
  const sinLat = Math.sin((lat * Math.PI) / 180);
  const gy = (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * n;
  return [gx, gy];
}

/** Convert ENU (metres from origin) to lat/lon. */
function enuToLL(ex: number, ey: number, originLat: number, originLon: number): [number, number] {
  const R = 6371000;
  const lat = originLat + (ey / R) * (180 / Math.PI);
  const lon = originLon + (ex / (R * Math.cos((originLat * Math.PI) / 180))) * (180 / Math.PI);
  return [lat, lon];
}

/** Tile indices covering a global pixel bbox. */
function tilesForBbox(minGx: number, minGy: number, maxGx: number, maxGy: number) {
  const txMin = Math.floor(minGx / TILE_SIZE);
  const tyMin = Math.floor(minGy / TILE_SIZE);
  const txMax = Math.floor(maxGx / TILE_SIZE);
  const tyMax = Math.floor(maxGy / TILE_SIZE);
  const tiles: { tx: number; ty: number }[] = [];
  for (let ty = tyMin; ty <= tyMax; ty++)
    for (let tx = txMin; tx <= txMax; tx++)
      tiles.push({ tx, ty });
  return { tiles, txMin, tyMin, txMax, tyMax };
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function FusionView({ minimal }: { minimal: boolean }) {
  const { t } = useT();
  const [sources, setSources] = useState<{ id: string; label: string }[]>([]);
  const [source, setSource] = useState("trimble");
  const [f, setF] = useState<FusionResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [show, setShow] = useState<Record<string, boolean>>({
    truth: true, gnss: true, aided_fixed: true, aided_adapt: true,
  });
  const [viewMode, setViewMode] = useState<"svg" | "map">("svg");
  const [mapRef, mapW] = useElementWidth<HTMLDivElement>();

  useEffect(() => { api.fusionSources().then(setSources).catch(() => {}); }, []);
  useEffect(() => {
    setF(null); setErr(null);
    api.fusion(source).then(setF).catch((e) => setErr(String(e)));
  }, [source]);

  // ── ENU projection geometry (for SVG mode) ──────────────────────────────────
  const svgGeom = useMemo(() => {
    if (!f) return null;
    const all = [...f.truth, ...f.aided_fixed];
    const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const sx = (maxX - minX) || 1, sy = (maxY - minY) || 1;
    const rotate = sy > sx * 1.1;
    const dispSx = rotate ? sy : sx, dispSy = rotate ? sx : sy;
    const W = Math.max(mapW, 400);
    const dispAspect = dispSy / dispSx;
    const H = Math.round(W * dispAspect * 1.5);
    const s = Math.max(W / dispSx, H / dispSy);
    const ox = (W - s * dispSx) / 2, oy = (H - s * dispSy) / 2;
    const proj = (p: number[]): [number, number] => {
      const ex = p[0] - minX, ey = p[1] - minY;
      return rotate
        ? [ox + ey * s, H - (oy + ex * s)]
        : [ox + ex * s, H - (oy + ey * s)];
    };
    return { W, H, proj };
  }, [f, mapW]);

  // ── OSM map geometry ─────────────────────────────────────────────────────────
  const mapGeom = useMemo(() => {
    if (!f || !f.origin_lat) return null;
    const originLat = f.origin_lat, originLon = f.origin_lon;
    const allEnu = [...f.truth, ...f.aided_fixed, ...f.gnss];

    // Convert all points to global pixels
    const globalPts = allEnu.map(([ex, ey]) => {
      const [lat, lon] = enuToLL(ex, ey, originLat, originLon);
      return llToGlobalPx(lat, lon, MAP_ZOOM);
    });

    const gxs = globalPts.map((p) => p[0]);
    const gys = globalPts.map((p) => p[1]);
    const pad = 80; // pixel padding around tracks
    const minGx = Math.min(...gxs) - pad, maxGx = Math.max(...gxs) + pad;
    const minGy = Math.min(...gys) - pad, maxGy = Math.max(...gys) + pad;

    const { tiles, txMin, tyMin } = tilesForBbox(minGx, minGy, maxGx, maxGy);

    const W = Math.max(mapW, 400);
    const trackW = maxGx - minGx;
    const trackH = maxGy - minGy;
    const scale = Math.min(W / trackW, W * 1.5 / trackH);
    const H = Math.round(trackH * scale);

    // Project a global pixel to SVG canvas pixel
    const toSvg = (gx: number, gy: number): [number, number] => [
      (gx - minGx) * scale,
      (gy - minGy) * scale,
    ];

    // Tile rect in SVG canvas coords
    const tileRects = tiles.map(({ tx, ty }) => {
      const [x0, y0] = toSvg(tx * TILE_SIZE, ty * TILE_SIZE);
      return { tx, ty, x: x0, y: y0, w: TILE_SIZE * scale, h: TILE_SIZE * scale };
    });

    // Track projections
    const projectTrack = (track: [number, number][]) =>
      track.map(([ex, ey]) => {
        const [lat, lon] = enuToLL(ex, ey, originLat, originLon);
        const [gx, gy] = llToGlobalPx(lat, lon, MAP_ZOOM);
        return toSvg(gx, gy);
      });

    return { W, H, tileRects, tileZ: MAP_ZOOM, tileCount: tiles.length, projectTrack, txMin, tyMin };
  }, [f, mapW]);

  const SourcePicker = (
    <div className="flex items-center gap-2">
      <FiRadio size={16} color={BEIHANG.secondary} />
      <span className="text-sm font-bold" style={{ color: BEIHANG.slate }}>{t("gnss_source")}</span>
      <select value={source} onChange={(e) => setSource(e.target.value)}
        className="rounded-xl border bg-white px-3 py-2 text-sm font-bold outline-none"
        style={{ borderColor: BEIHANG.line, color: BEIHANG.ink }}>
        {sources.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
      </select>
    </div>
  );

  if (err) return <Card>{SourcePicker}<p className="mt-3 text-sm" style={{ color: BEIHANG.slate }}>Fusion data unavailable. Run <code>python -m src.models.ekf_urbannav_runner --real --both</code> ({err}).</p></Card>;
  if (!f || (!svgGeom && viewMode === "svg") || (!mapGeom && viewMode === "map" && f))
    return <Card>{SourcePicker}<p className="mt-3 text-sm" style={{ color: BEIHANG.slate }}>Loading real fusion…</p></Card>;

  const s = f!.summary;
  const rmseOrder = ["gnss_raw", "cv_kf", "aided_ekf_fixed", "aided_ekf_adaptive"];
  const rmseLabel: Record<string, string> = {
    gnss_raw: t("rmse_raw"), cv_kf: t("rmse_simplekf"),
    aided_ekf_fixed: t("rmse_fixed"), aided_ekf_adaptive: t("rmse_adapt"),
  };
  const maxR = Math.max(...rmseOrder.map((k) => s.rmse_degraded_segment[k] ?? 0));
  const bestGain = s.degraded_gain_vs_raw["aided_ekf_fixed"];

  const pathOf = (key: SeriesKey) => {
    if (!svgGeom) return "";
    return f![key].map((p, i) => {
      const q = svgGeom.proj(p);
      return `${i === 0 ? "M" : "L"}${q[0].toFixed(1)},${q[1].toFixed(1)}`;
    }).join(" ");
  };

  const mapPathOf = (key: SeriesKey) => {
    if (!mapGeom) return "";
    const pts = mapGeom.projectTrack(f![key] as [number, number][]);
    return pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Banner */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4 text-white"
        style={{ background: `linear-gradient(100deg, ${BEIHANG.primary}, ${BEIHANG.secondary})` }}>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm font-semibold">
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold tracking-wide">{t("real_data")}</span>
          <span className="flex items-center gap-1.5"><FiNavigation size={15} /> {t("fusion_real_fixes", { n: s.n_real_fixes.toLocaleString() })}</span>
          <span className="flex items-center gap-1.5"><FiRadio size={15} /> {t("fusion_mean_sats", { n: s.mean_sats })}</span>
          <span className="opacity-85">{s.engine}</span>
        </div>
        {SourcePicker && <div className="rounded-xl bg-white/95 p-1">{SourcePicker}</div>}
      </motion.div>

      {/* Map + Accuracy panel */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[4fr_2fr]">

        {/* Trajectory map */}
        <Card pad={false}>
          <div className="flex items-center gap-2 px-6 pt-6 pb-3">
            <h3 className="text-lg font-bold tracking-tight" style={{ color: BEIHANG.primary }}>{t("where_car")}</h3>
            <InfoDot text="Green = ground truth (SPAN-INS cm-level). Teal = Aided EKF fixed-R (recommended). Red dashed = raw GNSS. Yellow dashed = adaptive EKF. Closer to green = better." />
            {/* View mode toggle */}
            <div className="ml-auto flex items-center gap-1 rounded-xl border p-1" style={{ borderColor: BEIHANG.line }}>
              <button onClick={() => setViewMode("svg")}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition"
                style={{ background: viewMode === "svg" ? BEIHANG.primary : "transparent", color: viewMode === "svg" ? "#fff" : BEIHANG.slate }}>
                <FiGrid size={13} /> ENU
              </button>
              <button onClick={() => setViewMode("map")}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition"
                style={{ background: viewMode === "map" ? BEIHANG.primary : "transparent", color: viewMode === "map" ? "#fff" : BEIHANG.slate }}>
                <FiMap size={13} /> Map
              </button>
            </div>
            <div><ExportPng targetRef={mapRef} filename="fusion_trajectory.png" /></div>
          </div>

          <div className="w-full px-4 py-4">
            <div ref={mapRef} className="w-full">

              {/* ── SVG mode (ENU projection) ── */}
              {viewMode === "svg" && svgGeom && (
                <svg viewBox={`0 0 ${svgGeom.W} ${svgGeom.H}`} width="100%" height={svgGeom.H}
                  style={{ display: "block" }}>
                  {SERIES.filter((ss) => show[ss.key]).map((ss) => (
                    <path key={ss.key} d={pathOf(ss.key)} fill="none" stroke={ss.color}
                      strokeWidth={ss.w} strokeDasharray={ss.dash ?? ""} strokeLinejoin="round" strokeLinecap="round" opacity={0.95} />
                  ))}
                </svg>
              )}

              {/* ── Map mode (OSM tiles + lat/lon overlay) ── */}
              {viewMode === "map" && mapGeom && (
                <div style={{ position: "relative", width: "100%", height: mapGeom.H }}>
                  {/* OSM tile background */}
                  <svg viewBox={`0 0 ${mapGeom.W} ${mapGeom.H}`} width="100%" height={mapGeom.H}
                    style={{ display: "block", position: "absolute", top: 0, left: 0 }}>
                    {mapGeom.tileRects.map(({ tx, ty, x, y, w, h }) => (
                      <image key={`${tx}-${ty}`}
                        href={`https://tile.openstreetmap.org/${mapGeom.tileZ}/${tx}/${ty}.png`}
                        x={x} y={y} width={w} height={h}
                        preserveAspectRatio="none" />
                    ))}
                    {/* Track overlays */}
                    {SERIES.filter((ss) => show[ss.key]).map((ss) => (
                      <path key={ss.key} d={mapPathOf(ss.key)} fill="none" stroke={ss.color}
                        strokeWidth={ss.w * 0.7} strokeDasharray={ss.dash ?? ""}
                        strokeLinejoin="round" strokeLinecap="round" opacity={0.9} />
                    ))}
                    {/* Attribution */}
                    <text x={mapGeom.W - 6} y={mapGeom.H - 4} textAnchor="end"
                      fontSize={9} fill="#333" fontFamily="sans-serif">
                      © OpenStreetMap contributors
                    </text>
                  </svg>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 px-6 pb-5">
            {SERIES.map((ss) => (
              <button key={ss.key} onClick={() => setShow((p) => ({ ...p, [ss.key]: !p[ss.key] }))}
                className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold transition"
                style={{ background: show[ss.key] ? "#fff" : BEIHANG.mist, color: BEIHANG.ink, opacity: show[ss.key] ? 1 : 0.5, borderColor: BEIHANG.line }}>
                <span className="h-1.5 w-5 rounded" style={{ background: ss.color }} /> {t(ss.labelKey)}
              </button>
            ))}
          </div>
        </Card>

        {/* Accuracy panel */}
        <Card>
          <SectionTitle hint="Average position error (metres) during GPS blackout segments. Shorter bar = more accurate.">
            {t("accuracy_blocked")}
          </SectionTitle>
          <div className="flex flex-col gap-3.5">
            {rmseOrder.map((k, i) => {
              const v = s.rmse_degraded_segment[k] ?? 0;
              const best = k === "aided_ekf_fixed";
              const gain = s.degraded_gain_vs_raw[k];
              return (
                <div key={k}>
                  <div className="mb-1 flex items-center justify-between text-[13px] font-bold">
                    <span className="flex items-center gap-1.5" style={{ color: BEIHANG.ink }}>
                      {best && <FiTarget size={14} color={EKF_FIXED_COLOR} />}{rmseLabel[k]}
                    </span>
                    <span style={{ color: best ? EKF_FIXED_COLOR : BEIHANG.slate }}>
                      {v.toFixed(1)} m {k !== "gnss_raw" && <span className="opacity-70">({gain > 0 ? "+" : ""}{gain}%)</span>}
                    </span>
                  </div>
                  <div className="h-5 w-full overflow-hidden rounded-md" style={{ background: BEIHANG.mist }}>
                    <motion.div className="h-full rounded-md" initial={{ width: 0 }}
                      animate={{ width: `${(v / maxR) * 100}%` }} transition={{ delay: i * 0.06, duration: 0.5 }}
                      style={{ background: best ? EKF_FIXED_COLOR : BEIHANG.secondary }} />
                  </div>
                </div>
              );
            })}
          </div>

          <p className="mt-4 text-sm leading-relaxed" style={{ color: BEIHANG.slate }}>
            {t("fusion_caption", { g: bestGain })}
          </p>

          {/* GNSS-only platform context note */}
          <div className="mt-4 rounded-xl border-l-4 px-4 py-3 text-xs leading-relaxed"
            style={{ background: "#FFF8E1", borderColor: "#F57F17", color: "#5D4037" }}>
            <strong>Why adaptive-R ranks lower here:</strong> Wheel odometry + NHC + ZUPT already dead-reckon
            accurately through GPS outages. Inflating R reduces GPS heading updates — unnecessary with
            aiding in place. <strong>Adaptive-R wins on GNSS-only platforms</strong> (drones, ships,
            phones — no wheel encoder), where SENTINEL&apos;s prediction is the only way to avoid trusting
            corrupted GPS. Crossover with full aiding: ~80 m multipath bias.
          </div>
        </Card>
      </div>

      {/* Satellite count */}
      <Card>
        <SatelliteStrip nsat={f.nsat} />
      </Card>
    </div>
  );
}
