"use client";

import { useDashboardStore } from "@/store/dashboardStore";
import type { DiffMode } from "@/lib/api/types";

const MODES: { mode: DiffMode; label: string }[] = [
  { mode: "diff", label: "DIFFERENCE (A-B)" },
  { mode: "movers", label: "HIGHLIGHT MOVERS" },
];

/** Detection & anomalies controls: diff / mover / anomaly highlight modes. */
export function DetectionPanel() {
  const diffMode = useDashboardStore((s) => s.diffMode);
  const setDiffMode = useDashboardStore((s) => s.setDiffMode);

  return (
    <section className="overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
      <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
        <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
          DETECTION &amp; ANOMALIES
        </span>
      </div>
      <div className="px-3 py-2.5">
        <p className="mb-2.5 text-[10px] leading-[1.35] text-text-muted">
          Play the previews to find moving objects, or flag anomalies.
        </p>
        <div className="mb-1.5 grid grid-cols-2 gap-1.5">
          {MODES.map(({ mode, label }) => (
            <button
              key={mode}
              type="button"
              aria-pressed={diffMode === mode}
              className={`cursor-pointer rounded-[3px] border px-1.5 py-1.5 text-center text-[10px] font-medium tracking-[0.04em] transition-all duration-200 ${
                diffMode === mode
                  ? "border-cyan bg-[#192b3c] text-cyan-bright shadow-[inset_0_0_8px_rgba(94,169,209,0.18)]"
                  : "border-[#2e4054] bg-[#15202b] text-[#c2d1e0] hover:border-[#4d789c] hover:bg-[#1b2938] hover:text-white"
              }`}
              onClick={() => setDiffMode(mode)}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          type="button"
          aria-pressed={diffMode === "anomalies"}
          className={`flex w-full cursor-pointer items-center justify-between rounded-[3px] border px-2.5 py-1.5 text-[10px] tracking-[0.04em] transition-all duration-200 ${
            diffMode === "anomalies"
              ? "border-cyan bg-[#1b2c3d] text-cyan-bright"
              : "border-[#2c3b4c] bg-[#18222e] text-[#b4c4d4] hover:border-cyan hover:text-white"
          }`}
          onClick={() => setDiffMode("anomalies")}
        >
          <span>HIGHLIGHT MOVING ANOMALIES</span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <polyline points="21 3 21 9 15 9" />
          </svg>
        </button>
      </div>
    </section>
  );
}
