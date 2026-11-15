"use client";

import { useEffect, useRef } from "react";
import { prepareCanvas } from "@/lib/utils/canvas";

interface SparklineProps {
  spectralSeed: number;
}

/** Design-space size; the canvas is stretched to its CSS box. */
const W = 360;
const H = 56;

/** Small proper-motion / flux sparkline. */
export function Sparkline({ spectralSeed }: SparklineProps) {
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

    ctx.strokeStyle = "#243445";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, 44);
    ctx.lineTo(W, 44);
    ctx.stroke();

    ctx.strokeStyle = "#76bfe8";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    for (let i = 0; i <= 60; i++) {
      const x = (i / 60) * W;
      const y = 30 - Math.sin(i * 0.35 + spectralSeed) * 11 - Math.cos(i * 0.8) * 5;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }, [spectralSeed]);

  return <canvas ref={canvasRef} className="h-[28px] flex-1" aria-hidden="true" />;
}
