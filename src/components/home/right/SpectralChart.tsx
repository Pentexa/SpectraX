"use client";

import { useEffect, useRef, useState } from "react";
import { useElementSize } from "@/hooks/useElementSize";
import { bandFlux, bandWavelength } from "@/lib/constants/bands";
import { clamp, clamp01 } from "@/lib/utils/random";
import { prepareCanvas } from "@/lib/utils/canvas";
import { useDashboardStore } from "@/store/dashboardStore";

const PAD_LEFT = 28;
const PAD_RIGHT = 10;
const PAD_TOP = 12;
const PAD_BOTTOM = 24;

/**
 * Spectral analysis chart: 102-band flux curves with a selectable band cursor.
 * Mouse hover previews a band (tooltip + cursor); clicking or touch-scrubbing
 * selects it (updates the shared store, atlas overlay and BandGrid).
 */
export function SpectralChart() {
  const { ref: wrapRef, size } = useElementSize<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hoverBand, setHoverBand] = useState<number | null>(null);

  const star = useDashboardStore((s) =>
    s.data?.stars.find((st) => st.id === s.selectedStarId) ?? null,
  );
  const selectedBand = useDashboardStore((s) => s.selectedBand);
  const setSelectedBand = useDashboardStore((s) => s.setSelectedBand);

  /** Map a pointer event to the band under the cursor (clamped to 1..102). */
  const bandFromPointer = (e: React.PointerEvent<HTMLCanvasElement>): number => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const ratio = clamp01((x - PAD_LEFT) / (rect.width - PAD_LEFT - PAD_RIGHT));
    return Math.round(1 + ratio * 101);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dims = prepareCanvas(canvas);
    if (!dims) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width: w, height: h } = dims;
    const plotW = w - PAD_LEFT - PAD_RIGHT;
    const plotH = h - PAD_TOP - PAD_BOTTOM;

    // Grid
    ctx.strokeStyle = "rgba(54, 76, 98, 0.35)";
    ctx.lineWidth = 0.7;
    for (let i = 0; i <= 4; i++) {
      const y = PAD_TOP + (plotH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(PAD_LEFT, y);
      ctx.lineTo(w - PAD_RIGHT, y);
      ctx.stroke();
    }
    for (let i = 0; i <= 5; i++) {
      const x = PAD_LEFT + (plotW * i) / 5;
      ctx.beginPath();
      ctx.moveTo(x, PAD_TOP);
      ctx.lineTo(x, h - PAD_BOTTOM);
      ctx.stroke();
    }

    // Y labels
    ctx.fillStyle = "#6f8499";
    ctx.font = '8px "JetBrains Mono", monospace';
    ctx.textAlign = "right";
    ["80", "60", "40", "20", "0"].forEach((label, i) => {
      ctx.fillText(label, PAD_LEFT - 4, PAD_TOP + (plotH * i) / 4 + 3);
    });

    // X labels
    ctx.textAlign = "center";
    ["0", "200", "400", "600", "800", "1004"].forEach((label, i) => {
      ctx.fillText(label, PAD_LEFT + (plotW * i) / 5, h - 10);
    });

    ctx.fillStyle = "#8aa0b5";
    ctx.font = "8px Inter, sans-serif";
    ctx.fillText("PALAX — 5.0 μm", PAD_LEFT + plotW / 2, h - 2);

    if (!star) return;
    const seed = star.spectralSeed;

    // Curves
    const ptsA: { x: number; y: number }[] = [];
    const ptsB: { x: number; y: number }[] = [];
    for (let i = 0; i < 102; i++) {
      const t = i / 101;
      const base =
        6 +
        Math.pow(t, 1.4) * 52 +
        Math.sin(i * 0.45 * seed) * 5 +
        Math.cos(i * 1.1) * 3.5;
      const valA = clamp(base, 3, 76);
      const valB = clamp(base * 0.84 + Math.sin(i * 0.7) * 4, 2, 72);
      ptsA.push({ x: PAD_LEFT + t * plotW, y: PAD_TOP + plotH * (1 - valA / 80) });
      ptsB.push({ x: PAD_LEFT + t * plotW, y: PAD_TOP + plotH * (1 - valB / 80) });
    }

    // Area under curve A
    ctx.beginPath();
    ctx.moveTo(ptsA[0].x, PAD_TOP + plotH);
    for (const p of ptsA) ctx.lineTo(p.x, p.y);
    ctx.lineTo(ptsA[ptsA.length - 1].x, PAD_TOP + plotH);
    ctx.closePath();
    const areaGrad = ctx.createLinearGradient(0, PAD_TOP, 0, PAD_TOP + plotH);
    areaGrad.addColorStop(0, "rgba(94, 169, 209, 0.28)");
    areaGrad.addColorStop(1, "rgba(94, 169, 209, 0.02)");
    ctx.fillStyle = areaGrad;
    ctx.fill();

    // Secondary curve
    ctx.strokeStyle = "rgba(95, 130, 165, 0.8)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ptsB.forEach((p, idx) => (idx === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
    ctx.stroke();

    // Primary curve
    ctx.strokeStyle = "#9cd7f7";
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ptsA.forEach((p, idx) => (idx === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
    ctx.stroke();

    // Band cursor
    const cursorBand = hoverBand ?? selectedBand;
    const curX = PAD_LEFT + ((cursorBand - 1) / 101) * plotW;
    ctx.strokeStyle = "rgba(138, 212, 245, 0.65)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(curX, PAD_TOP);
    ctx.lineTo(curX, PAD_TOP + plotH);
    ctx.stroke();
  }, [size, star, selectedBand, hoverBand]);

  const activeBand = hoverBand ?? selectedBand;

  return (
    <div ref={wrapRef} className="relative h-[155px] overflow-hidden rounded-[2px] border border-[#1e2a38] bg-[#0c1219]">
      <canvas
        ref={canvasRef}
        className="h-full w-full cursor-crosshair touch-none"
        onPointerMove={(e) => {
          if (e.pointerType === "mouse") {
            setHoverBand(bandFromPointer(e));
            return;
          }
          // Touch/pen: scrub-selects while the pointer is down.
          if (e.buttons > 0 || e.pressure > 0) setSelectedBand(bandFromPointer(e));
        }}
        onPointerDown={(e) => setSelectedBand(bandFromPointer(e))}
        onPointerLeave={() => setHoverBand(null)}
      />
      <div className="pointer-events-none absolute top-1.5 right-2 rounded-[2px] border border-[#2b3f54] bg-[rgba(12,18,25,0.85)] px-1.5 py-0.5 font-mono text-[9px] text-cyan-bright">
        BAND {activeBand} • {bandWavelength(activeBand).toFixed(2)} μm •{" "}
        {bandFlux(activeBand, star?.spectralSeed ?? 1).toFixed(1)} Jy
      </div>
    </div>
  );
}
