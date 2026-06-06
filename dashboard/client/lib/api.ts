/** REST + WebSocket client for the SENTINEL backend. */
import type { EkfResult, FusionResult, Prediction, Scenario, Summary } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<{ status: string; scenarios: number; ekf_available: boolean }>("/api/health"),
  scenarios: () => getJSON<Scenario[]>("/api/scenarios"),
  predictions: (id: string) => getJSON<Prediction[]>(`/api/predictions/${id}`),
  summary: (id: string) => getJSON<Summary>(`/api/summary/${id}`),
  ekf: () => getJSON<EkfResult>("/api/ekf"),
  fusionSources: () => getJSON<{ id: string; label: string }[]>("/api/fusion/sources"),
  fusion: (source = "trimble") => getJSON<FusionResult>(`/api/fusion?source=${source}`),
};

/** Typed WebSocket message envelope from the replay stream. */
export type WsMessage =
  | { type: "replay_start"; scenario: string; total: number }
  | { type: "epoch"; index: number; total: number; data: Prediction }
  | { type: "replay_end"; scenario: string }
  | { type: "replay_stopped" }
  | { type: "pong" }
  | { type: "error"; message: string };
