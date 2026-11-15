"use client";

import { OrbitDiagram } from "@/components/canvas/OrbitDiagram";
import type { AnimationClock } from "@/hooks/useAnimationClock";
import { useDashboardStore } from "@/store/dashboardStore";

interface PlanetXPanelProps {
  clock: AnimationClock;
}

/** Bottom Planet-X candidate list + orbit diagram. */
export function PlanetXPanel({ clock }: PlanetXPanelProps) {
  const candidates = useDashboardStore((s) => s.data?.candidates ?? []);
  const selectedCandidateIdx = useDashboardStore((s) => s.selectedCandidateIdx);
  const selectCandidate = useDashboardStore((s) => s.selectCandidate);
  const star = useDashboardStore((s) =>
    s.data?.stars.find((st) => st.id === s.selectedStarId) ?? null,
  );

  // The API contract says `orbitIdx` identifies which orbit ring to highlight
  // (see src/lib/api/types.ts); never fall back to the list position.
  const selectedCandidate = candidates[selectedCandidateIdx];
  const selectedOrbitIdx = selectedCandidate ? selectedCandidate.orbitIdx : -1;

  return (
    <section
      className="grid items-center gap-5 rounded-[3px] border border-border-panel px-3.5 py-2.5"
      style={{
        gridTemplateColumns: "330px 1fr",
        background:
          "linear-gradient(180deg, rgba(18, 26, 36, 0.95) 0%, rgba(13, 19, 27, 0.98) 100%)",
      }}
    >
      <div>
        <div className="mb-1.5">
          <div className="text-[11.5px] font-medium text-[#dbe6f0]">
            {star ? `${star.name} * X` : "PLANET X"}
          </div>
          <div className="text-[9.5px] text-text-muted">Planet X Candidates</div>
        </div>

        <div className="flex flex-col gap-1">
          {candidates.map((candidate, index) => {
            const active = index === selectedCandidateIdx;
            return (
              <button
                key={candidate.id}
                type="button"
                aria-pressed={active}
                className={`flex cursor-pointer items-center justify-between rounded-[2px] border px-2 py-1 text-[10px] transition-all duration-150 ${
                  active
                    ? "border-cyan bg-[rgba(45,76,106,0.42)]"
                    : "border-[#202d3c] bg-[rgba(20,29,40,0.65)] hover:border-[#3d5b7a] hover:bg-[rgba(34,52,72,0.65)]"
                }`}
                onClick={() => selectCandidate(index)}
              >
                <span className="flex items-center gap-1.5 font-medium text-[#d3e0ec]">
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: candidate.color, boxShadow: `0 0 6px ${candidate.color}` }}
                  />
                  {candidate.label}
                </span>
                <span className="font-mono text-[9.5px] text-[#93a7bc]">
                  {candidate.ra} &nbsp;•&nbsp; {candidate.dec} &nbsp;•&nbsp; {candidate.au}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative flex h-[104px] items-center justify-center">
        <OrbitDiagram clock={clock} selectedOrbitIdx={selectedOrbitIdx} />
      </div>
    </section>
  );
}
