"use client";

import { useDashboardStore } from "@/store/dashboardStore";

/** Photometric anomaly candidate list (click to select a star). */
export function StarList({ onSelect }: { onSelect?: (id: string) => void }) {
  const stars = useDashboardStore((s) => s.data?.stars ?? []);
  const selectedStarId = useDashboardStore((s) => s.selectedStarId);
  const selectStar = useDashboardStore((s) => s.selectStar);

  return (
    <section className="overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
      <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
        <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
          CHALLENGE TARGETS
        </span>
      </div>
      <div className="flex flex-col">
        {stars.map((star) => {
          const active = star.id === selectedStarId;
          return (
            <button
              key={star.id}
              type="button"
              aria-pressed={active}
              className={`flex cursor-pointer items-center justify-between border-b border-[rgba(36,49,64,0.65)] px-3 py-[7.5px] text-left transition-colors duration-150 last:border-b-0 ${
                active
                  ? "border-l-2 border-l-cyan-bright bg-[rgba(58,108,146,0.25)] pl-2.5"
                  : "hover:bg-[rgba(40,62,84,0.35)]"
              }`}
              onClick={() => (onSelect ?? selectStar)(star.id)}
            >
              <span className="flex items-center gap-1.5 text-[11px] text-[#d6e2ee]">
                <span className="h-[5px] w-[5px] rounded-full bg-[#7ab9e8] shadow-[0_0_6px_#7ab9e8]" />
                {star.name}
              </span>
              <span className="font-mono text-[10.5px] text-[#93a7bc]">{star.deltaMag}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
