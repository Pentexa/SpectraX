import { create } from "zustand";
import { scienceApi, type ScienceTarget } from "@/lib/api/science";
import type { DataSource, DiffMode, ObservatorySnapshot } from "@/lib/api/types";

interface DashboardState {
  /* --- data --- */
  data: ObservatorySnapshot | null;
  source: DataSource;
  loadError: string | null;
  targets: ScienceTarget[];

  /* --- UI state --- */
  selectedStarId: string;
  selectedBand: number;
  activeBands: number[];
  activeEpoch: number;
  diffMode: DiffMode;
  selectedCandidateIdx: number;

  /* --- actions --- */
  loadData: () => Promise<void>;
  selectStar: (id: string) => void;
  setSelectedBand: (band: number) => void;
  toggleBand: (band: number) => void;
  setEpoch: (epoch: number) => void;
  setDiffMode: (mode: DiffMode) => void;
  selectCandidate: (index: number) => void;
}

export const useDashboardStore = create<DashboardState>()((set, get) => ({
  data: null,
  source: "loading",
  loadError: null,
  targets: [],

  selectedStarId: "wise-0855",
  selectedBand: 18,
  activeBands: Array.from({ length: 12 }, (_, i) => 86 + i),
  activeEpoch: 0,
  diffMode: "diff",
  selectedCandidateIdx: 0,

  loadData: async () => {
    set({ source: "loading", loadError: null });
    try {
      const { targets } = await scienceApi.targets();
      const current = get();
      const starExists = targets.some((target) => target.id === current.selectedStarId);
      set({
        targets,
        data: {
          stars: targets.map((target) => ({
            id: target.id, name: target.name, ra: target.ra.toFixed(6), dec: target.dec.toFixed(6),
            deltaMag: target.benchmark_available ? "Measured" : "Archive",
            distance: "—", magnitude: "—", delta: "—", raDrift: "—", decDrift: "—",
            properMotion: `${Math.hypot(target.pm_ra_cosdec_mas_yr, target.pm_dec_mas_yr).toFixed(1)} mas/yr`,
            parallax: `${target.parallax_mas.toFixed(1)} mas`, delta13: "—", mas: "—", spectralSeed: 1,
          })),
          candidates: [],
          mission: {
            name: "SPHEREx", agency: "NASA", instrument: "SPHEREx", bandCount: 102,
            wavelengthRange: [0.75, 5], epochIntervalMonths: 6, currentYear: 2026,
          },
        },
        source: "api",
        selectedStarId: starExists ? current.selectedStarId : targets[0]?.id ?? "",
      });
    } catch (error) {
      const message = error && typeof error === "object" && "message" in error ? String(error.message) : String(error);
      set({ source: "offline", loadError: message });
    }
  },

  selectStar: (id) => set({ selectedStarId: id }),

  setSelectedBand: (band) => set({ selectedBand: band }),

  toggleBand: (band) =>
    set((state) => {
      const has = state.activeBands.includes(band);
      return {
        selectedBand: band,
        activeBands: has
          ? state.activeBands.filter((b) => b !== band)
          : [...state.activeBands, band],
      };
    }),

  setEpoch: (epoch) => set({ activeEpoch: epoch }),

  setDiffMode: (mode) => set({ diffMode: mode }),

  selectCandidate: (index) => set({ selectedCandidateIdx: index }),
}));
