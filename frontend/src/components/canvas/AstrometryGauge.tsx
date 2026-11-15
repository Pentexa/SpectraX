"use client";

import { useEffect, useRef } from "react";
import { prepareCanvas } from "@/lib/utils/canvas";

interface AstrometryGaugeProps {
  /** Seeded variation used to animate the bar fill. */
  spectralSeed: number;
}

/** Design-space size; the canvas is stretched to its CSS box. */
const W = 216;
const H = 108;

/**
 * Astrometry widget: a polar drift circle plus a vertical flux/parallax bar.
 */
export function AstrometryGauge({ spectralSeed }: AstrometryGaugeProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dims = prepareCanvas(canvas);
    if (!dims) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dims.width / W, dims.height / H);
    ctx.clearRect(0, 0, W, H);

    // Left polar circle
    const cx = 64;
    const cy = 54;
    const r = 36;
    ctx.strokeStyle = "#2d4156";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = "#5ea9d1";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, r - 6, -Math.PI * 0.7, Math.PI * 0.25);
    ctx.stroke();

    // Vector arrow
    ctx.strokeStyle = "#9ad8f7";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + 22, cy - 18);
    ctx.stroke();

    // Right vertical bar gauge
    ctx.fillStyle = "#192430";
    ctx.fillRect(145, 16, 16, 76);
    ctx.fillStyle = "#5ea9d1";
    const fillH = 38 + ((spectralSeed * 12) % 30);
    ctx.fillRect(145, 92 - fillH, 16, fillH);
    ctx.strokeStyle = "#364d63";
    ctx.strokeRect(145, 16, 16, 76);
  }, [spectralSeed]);

  return <canvas ref={canvasRef} className="h-[54px] w-[108px]" aria-hidden="true" />;
}
