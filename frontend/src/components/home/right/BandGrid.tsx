"use client";

import { BAND_COLS, BAND_COUNT, bandWavelength } from "@/lib/constants/bands";
import { useDashboardStore } from "@/store/dashboardStore";

/** Background color for a band cell, mirroring the original visual design. */
function bandCellColor(row: number, col: number): string {
  if (row < 4) {
    const lum = 18 + col * 3.8 + row * 2;
    return `rgb(${Math.round(lum)}, ${Math.round(lum + 8)}, ${Math.round(lum + 16)})`;
  }
  if (row === 4) {
    const lum = 20 + col * 1.4;
    return `rgb(${Math.round(lum)}, ${Math.round(lum + 7)}, ${Math.round(lum + 14)})`;
  }
  // Bottom row: cyan/sky-blue highlights
  if (col < 12) {
    const blue = 135 + col * 7;
    return `rgb(${Math.round(55 + col * 4)}, ${Math.round(105 + col * 5)}, ${Math.min(240, blue)})`;
  }
  return "#1b2633";
}

/** Band multi-selector grid (17 × 6 = 102 cells). */
export function BandGrid() {
  const activeBands = useDashboardStore((s) => s.activeBands);
  const selectedBand = useDashboardStore((s) => s.selectedBand);
  const toggleBand = useDashboardStore((s) => s.toggleBand);

  const cells: React.ReactNode[] = [];
  for (let band = 1; band <= BAND_COUNT; band++) {
    const row = Math.floor((band - 1) / BAND_COLS);
    const col = (band - 1) % BAND_COLS;
    const selected = activeBands.includes(band) || band === selectedBand;

    cells.push(
      <button
        key={band}
        type="button"
        title={`Band ${band} (${bandWavelength(band).toFixed(2)} μm)`}
        aria-label={`Band ${band}, ${bandWavelength(band).toFixed(2)} μm`}
        aria-pressed={selected}
        className={`aspect-square cursor-pointer rounded-[1.5px] border border-white/[0.05] transition-[transform,border-color,box-shadow] duration-100 hover:z-[2] hover:scale-[1.16] hover:border-white focus:outline-none focus-visible:z-[2] focus-visible:scale-[1.16] focus-visible:border-cyan-bright focus-visible:shadow-[0_0_6px_var(--color-cyan-bright)] ${
          selected ? "border-white shadow-[0_0_6px_var(--color-cyan-bright)]" : ""
        }`}
        style={{ background: bandCellColor(row, col) }}
        onClick={() => toggleBand(band)}
      />,
    );
  }

  return (
    <section className="overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
      <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
        <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
          BAND MULTI-SELECTOR (1–102)
        </span>
      </div>
      <div className="px-3 py-2.5">
        <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${BAND_COLS}, 1fr)` }}>
          {cells}
        </div>
      </div>
    </section>
  );
}
