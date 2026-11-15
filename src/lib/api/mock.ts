import type { ObservatorySnapshot } from "./types";

/**
 * Built-in demo dataset. This is the contract for the FastAPI backend:
 * `GET /api/v1/snapshot` must return the same shape, and the frontend will
 * transparently switch from mock to live data once the backend is reachable.
 */
export const MOCK_SNAPSHOT: ObservatorySnapshot = {
  mission: {
    name: "SPHEREx",
    agency: "SPHEREx / Caltech",
    instrument: "SPECTRO-PHOTOMETER",
    bandCount: 102,
    wavelengthRange: [0.75, 5.0],
    epochIntervalMonths: 6,
    currentYear: 2026,
  },
  stars: [
    {
      id: "barnard",
      name: "Barnard's Star",
      deltaMag: "+0.003 Δmag",
      ra: "17h 57m",
      dec: "+04° 41\"",
      distance: "5.96 LY",
      magnitude: "+9.54",
      delta: "Δ -0.78 — 5.0 ma",
      raDrift: "+0.0012\"/yr",
      decDrift: "-0.012\"/yr",
      properMotion: "10.3\"/yr",
      parallax: "547\"/yr",
      delta13: "+0.082 Δ13\"Δ1",
      mas: "+0.023 mas",
      spectralSeed: 1.0,
    },
    {
      id: "wise0855",
      name: "WISE 0855",
      deltaMag: "+0.001 Δmag",
      ra: "08h 55m",
      dec: "-07° 14\"",
      distance: "7.27 LY",
      magnitude: "+13.89",
      delta: "Δ -0.42 — 3.8 ma",
      raDrift: "-0.0041\"/yr",
      decDrift: "+0.008\"/yr",
      properMotion: "8.1\"/yr",
      parallax: "439\"/yr",
      delta13: "+0.045 Δ13\"Δ1",
      mas: "+0.019 mas",
      spectralSeed: 1.35,
    },
    {
      id: "epsilon",
      name: "Epsilon Indi B",
      deltaMag: "+0.007 Δmag",
      ra: "22h 03m",
      dec: "-56° 47\"",
      distance: "11.87 LY",
      magnitude: "+11.20",
      delta: "Δ -0.91 — 6.2 ma",
      raDrift: "+0.0039\"/yr",
      decDrift: "-0.021\"/yr",
      properMotion: "4.7\"/yr",
      parallax: "275\"/yr",
      delta13: "+0.104 Δ13\"Δ1",
      mas: "+0.031 mas",
      spectralSeed: 0.82,
    },
    {
      id: "rwaurigae",
      name: "RW Aurigae",
      deltaMag: "+0.012 Δmag",
      ra: "05h 07m",
      dec: "+30° 24\"",
      distance: "456 LY",
      magnitude: "+10.45",
      delta: "Δ -1.14 — 7.1 ma",
      raDrift: "+0.0008\"/yr",
      decDrift: "-0.003\"/yr",
      properMotion: "1.9\"/yr",
      parallax: "7.1\"/yr",
      delta13: "+0.142 Δ13\"Δ1",
      mas: "+0.044 mas",
      spectralSeed: 1.58,
    },
    {
      id: "rdraconis",
      name: "R Draconis",
      deltaMag: "+0.005 Δmag",
      ra: "16h 32m",
      dec: "+66° 45\"",
      distance: "1850 LY",
      magnitude: "+7.60",
      delta: "Δ -0.63 — 4.4 ma",
      raDrift: "+0.0021\"/yr",
      decDrift: "+0.006\"/yr",
      properMotion: "2.4\"/yr",
      parallax: "12.5\"/yr",
      delta13: "+0.068 Δ13\"Δ1",
      mas: "+0.017 mas",
      spectralSeed: 1.18,
    },
  ],
  candidates: [
    {
      id: "CANDIDATE-01",
      label: "CANDIDATE-01",
      ra: "RA 03h 42m",
      dec: "DEC -24° 17\"",
      au: "102 AU",
      color: "#8f98f7",
      orbitIdx: 0,
    },
    {
      id: "CANDIDATE-02",
      label: "CANDIDATE-02",
      ra: "RA 19h 11m",
      dec: "DEC +12° 08\"",
      au: "118 AU",
      color: "#7ea8e8",
      orbitIdx: 1,
    },
    {
      id: "CANDIDATE-03",
      label: "CANDIDATE-03",
      ra: "RA 07h 55m",
      dec: "DEC -08° 33\"",
      au: "95 AU",
      color: "#6fd3d3",
      orbitIdx: 2,
    },
  ],
};

/** Simulated network latency (ms) so the UI loading state is visible. */
export const MOCK_LATENCY_MS = 350;

export function fetchMockSnapshot(): Promise<ObservatorySnapshot> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(structuredClone(MOCK_SNAPSHOT)), MOCK_LATENCY_MS);
  });
}
