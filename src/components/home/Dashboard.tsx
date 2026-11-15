"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { InfoModal } from "@/components/layout/InfoModal";
import { createAnimationClock } from "@/hooks/useAnimationClock";
import { useDashboardStore } from "@/store/dashboardStore";
import { EpochComparison } from "./left/EpochComparison";
import { DetectionPanel } from "./left/DetectionPanel";
import { StarList } from "./left/StarList";
import { AllSkyAtlas } from "./center/AllSkyAtlas";
import { SpectralChart } from "./right/SpectralChart";
import { BandGrid } from "./right/BandGrid";
import { DataTracker } from "./right/DataTracker";
import { PlanetXPanel } from "./bottom/PlanetXPanel";

/** 3-column interactive dashboard shell. */
export function Dashboard() {
  const clock = useMemo(() => createAnimationClock(), []);
  const [modalSection, setModalSection] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState("map");
  const data = useDashboardStore((s) => s.data);
  const source = useDashboardStore((s) => s.source);
  const loadData = useDashboardStore((s) => s.loadData);

  // Load the observatory snapshot once on mount (guard against StrictMode
  // double-invocation in dev).
  const loadStarted = useRef(false);
  useEffect(() => {
    if (loadStarted.current) return;
    loadStarted.current = true;
    void loadData();
  }, [loadData]);

  const handleNavigate = (sectionId: string) => {
    setActiveSection(sectionId);
    if (sectionId !== "map") setModalSection(sectionId);
  };

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{
        background:
          "radial-gradient(ellipse at 50% 0%, rgba(30, 52, 74, 0.22) 0%, transparent 65%), linear-gradient(180deg, #0b1017 0%, #090d12 100%)",
      }}
    >
      <SiteHeader
        activeSection={activeSection}
        onNavigate={handleNavigate}
        dataSource={source}
      />

      {!data ? (
        <main className="flex flex-1 items-center justify-center p-10">
          <div className="flex flex-col items-center gap-3 text-[#94a5b8]">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan border-t-transparent" />
            <span className="text-[11px] tracking-[0.08em]">
            Loading SPHEREx data…
          </span>
          </div>
        </main>
      ) : (
        <>
          <main
            className="grid flex-1 gap-2.5 px-3 pb-2 pt-2.5"
            style={{
              gridTemplateColumns: "280px minmax(0,1fr) 310px",
            }}
          >
            {/* LEFT COLUMN */}
            <aside className="flex min-w-0 flex-col gap-2">
              <EpochComparison clock={clock} />
              <DetectionPanel />
              <StarList />
              <section className="mt-auto overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
                <div className="px-3 py-2">
                  <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
                    TESTED TARGETS
                  </span>
                </div>
              </section>
            </aside>

            {/* CENTER COLUMN */}
            <AllSkyAtlas clock={clock} />

            {/* RIGHT COLUMN */}
            <aside className="flex min-w-0 flex-col gap-2">
              <section className="overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
                <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
                  <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
                    SPECTRAL ANALYSIS (102 BANDS)
                  </span>
                </div>
                <div className="px-3 py-2.5">
                  <SpectralChart />
                </div>
              </section>
              <BandGrid />
              <DataTracker />
            </aside>
          </main>

          <div className="flex flex-col gap-2 px-3 pb-2.5">
            <PlanetXPanel clock={clock} />
            <SiteFooter />
          </div>
        </>
      )}

      <InfoModal sectionId={modalSection} onClose={() => setModalSection(null)} />
    </div>
  );
}
