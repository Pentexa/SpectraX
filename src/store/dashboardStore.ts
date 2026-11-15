import { create } from "zustand";
import { getObservatorySnapshot } from "@/lib/api/endpoints";
import { fetchMockSnapshot } from "@/lib/api/mock";
import type { DataSource, DiffMode, ObservatorySnapshot } from "@/lib/api/types";

interface DashboardState {
  /* --- data --- */
  data: ObservatorySnapshot | null;
  source: DataSource;
  loadError: string | null;

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

  selectedStarId: "barnard",
  selectedBand: 18,
  activeBands: Array.from({ length: 12 }, (_, i) => 86 + i),
  activeEpoch: 0,
  diffMode: "diff",
  selectedCandidateIdx: 0,

  loadData: async () => {
    set({ source: "loading", loadError: null });
    try {
      const data = await getObservatorySnapshot();
      const current = get();
      const starExists = data.stars.some((s) => s.id === current.selectedStarId);
      set({
        data,
        source: "api",
        selectedStarId: starExists ? current.selectedStarId : data.stars[0]?.id,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const data = await fetchMockSnapshot();
      const current = get();
      const starExists = data.stars.some((s) => s.id === current.selectedStarId);
      set({
        data,
        source: "mock",
        loadError: message,
        selectedStarId: starExists ? current.selectedStarId : data.stars[0]?.id,
      });
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
