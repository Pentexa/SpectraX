"use client";

import { AstrometryGauge } from "@/components/canvas/AstrometryGauge";
import { Sparkline } from "@/components/canvas/Sparkline";
import { useDashboardStore } from "@/store/dashboardStore";

/** Dynamic anomaly tracker: telemetry rows + astrometry + sparkline. */
export function DataTracker() {
  const star = useDashboardStore((s) =>
    s.data?.stars.find((st) => st.id === s.selectedStarId) ?? null,
  );

  if (!star) return null;

  const telemetry: { label: string; value: string; cyan?: boolean }[] = [
    { label: "RA DRIFT:", value: star.raDrift, cyan: true },
    { label: "DEC DRIFT:", value: star.decDrift },
    { label: "PROPER MOTION:", value: star.properMotion, cyan: true },
    { label: "PARALLAX:", value: star.parallax },
  ];

  return (
    <>
      <div className="rounded-[3px] border border-border-panel bg-[#131c26] px-3 py-1.5 text-[11px] font-medium tracking-[0.06em] text-[#bccad8]">
        DYNAMIC DATA TRACKER
      </div>

      <section className="flex flex-1 flex-col overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
        <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
          <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
            DYNAMIC ANOMALY TRACKER
          </span>
        </div>
        <div className="px-3 py-2.5">
          <div className="grid items-center gap-2.5" style={{ gridTemplateColumns: "1fr 112px" }}>
            <div className="flex flex-col gap-1.5">
              {telemetry.map((row) => (
                <div key={row.label} className="flex items-center justify-between text-[10px]">
                  <span className="tracking-[0.03em] text-[#8295a8]">{row.label}</span>
                  <span
                    className={`font-mono text-[10px] text-[#d0dde9] ${
                      row.cyan ? "text-cyan-bright" : ""
                    }`}
                  >
                    {row.value}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex flex-col items-center gap-1.5">
              <AstrometryGauge spectralSeed={star.spectralSeed} />
              <div className="w-full text-right font-mono text-[9px] leading-[1.35] text-cyan">
                <div>{star.delta13}</div>
                <div>{star.mas}</div>
              </div>
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between gap-2.5 border-t border-border-subtle pt-2">
            <Sparkline spectralSeed={star.spectralSeed} />
            <div className="flex items-center gap-2 text-[#7d92a7]">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M4 8l11-4 3 7-11 4z" />
                <path d="M11 13l-2 7M13 13l3 7" />
              </svg>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <circle cx="12" cy="12" r="3" />
                <circle cx="5" cy="6" r="2" />
                <circle cx="19" cy="18" r="2" />
                <path d="M6.5 7.5L10 10.5M14 13.5l3.5 3" />
              </svg>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
