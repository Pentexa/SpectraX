import { apiClient } from "./client";
import type { ObservatorySnapshot } from "./types";

/**
 * FastAPI endpoint registry.
 *
 * Keep endpoint paths here so components never hardcode URLs —
 * the contract with the backend stays in one place.
 */
export const endpoints = {
  snapshot: "/api/v1/snapshot",
} as const;

export async function getObservatorySnapshot(): Promise<ObservatorySnapshot> {
  return apiClient.get<ObservatorySnapshot>(endpoints.snapshot);
}
