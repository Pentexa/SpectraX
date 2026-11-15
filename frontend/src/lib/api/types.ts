/**
 * UI view models and shared HTTP error types. The science API contract is
 * defined in `science.ts` and served by `apps/api/` at the repository root.
 */

export interface StarCatalogEntry {
  id: string;
  name: string;
  deltaMag: string;
  ra: string;
  dec: string;
  distance: string;
  magnitude: string;
  delta: string;
  raDrift: string;
  decDrift: string;
  properMotion: string;
  parallax: string;
  delta13: string;
  mas: string;
  /** Seeded spectral curve variation (0.5..2) */
  spectralSeed: number;
}

export interface PlanetXCandidate {
  id: string;
  label: string;
  ra: string;
  dec: string;
  au: string;
  color: string;
  orbitIdx: number;
}

export interface MissionInfo {
  name: string;
  agency: string;
  instrument: string;
  bandCount: number;
  wavelengthRange: [number, number];
  epochIntervalMonths: number;
  currentYear: number;
}

export interface ObservatorySnapshot {
  stars: StarCatalogEntry[];
  candidates: PlanetXCandidate[];
  mission: MissionInfo;
}

export type DataSource = "loading" | "api" | "mock" | "offline";

export type DiffMode = "diff" | "movers" | "anomalies";

export interface ApiError {
  status?: number;
  code?: string;
  message: string;
  cause?: unknown;
}
