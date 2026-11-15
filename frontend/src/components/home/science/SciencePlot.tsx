"use client";

import { useEffect, useRef } from "react";
import { useElementSize } from "@/hooks/useElementSize";
import { prepareCanvas } from "@/lib/utils/canvas";

type Point = { x: number; y: number | null };

export function SciencePlot({ points, label, xLabel, magnitude = false, activeX }: {
  points: Point[]; label: string; xLabel: string; magnitude?: boolean; activeX?: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { ref, size: { width: observedWidth, height: observedHeight } } = useElementSize<HTMLDivElement>();
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const size = prepareCanvas(element);
    const ctx = element.getContext("2d");
    if (!size || !ctx) return;
    const { width, height } = size;
    const values = points.flatMap((point) => point.y === null ? [] : [point.y]);
    if (values.length === 0) return;
    const x0 = Math.min(...points.map((point) => point.x));
    const x1 = Math.max(x0 + 1e-6, ...points.map((point) => point.x));
    const y0 = Math.min(...values);
    const y1 = Math.max(y0 + 1e-6, ...values);
    const left = 60, right = width - 16, top = 16, bottom = height - 44;
    const x = (value: number) => left + (value - x0) / (x1 - x0) * (right - left);
    const y = (value: number) => (magnitude ? top : bottom) + (value - y0) / (y1 - y0) * (bottom - top) * (magnitude ? 1 : -1);
    ctx.font = "11px monospace";
    ctx.fillStyle = "#a5b8ca";
    ctx.strokeStyle = "#293c50";
    ctx.lineWidth = 1;
    ctx.textAlign = "left";
    for (let i = 0; i <= 3; i++) {
      const value = y0 + (y1 - y0) * i / 3;
      const py = y(value);
      ctx.fillText(value.toPrecision(3), 5, py + 5);
      ctx.beginPath();
      ctx.moveTo(left, py);
      ctx.lineTo(right, py);
      ctx.stroke();
    }
    ctx.fillText(x0.toFixed(magnitude ? 0 : 2), left, height - 26);
    ctx.textAlign = "right";
    ctx.fillText(x1.toFixed(magnitude ? 0 : 2), right, height - 26);
    ctx.textAlign = "center";
    ctx.fillText(xLabel, (left + right) / 2, height - 8);
    ctx.textAlign = "left";
    ctx.strokeStyle = "#74c9f2";
    ctx.fillStyle = "#88d5fd";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    let connected = false;
    for (const point of points) {
      if (point.y === null) { connected = false; continue; }
      if (magnitude) {
        ctx.moveTo(x(point.x) + 2.5, y(point.y));
        ctx.arc(x(point.x), y(point.y), 2.5, 0, Math.PI * 2);
      } else {
        if (connected) ctx.lineTo(x(point.x), y(point.y));
        else ctx.moveTo(x(point.x), y(point.y));
        connected = true;
      }
    }
    if (magnitude) ctx.fill();
    else ctx.stroke();
    if (activeX !== undefined) {
      const marker = points.find((point) => point.x === activeX);
      ctx.strokeStyle = "#b5d7ee";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x(activeX), top);
      ctx.lineTo(x(activeX), bottom);
      ctx.stroke();
      ctx.setLineDash([]);
      if (marker?.y != null) {
        ctx.beginPath();
        ctx.arc(x(activeX), y(marker.y), 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }, [points, xLabel, magnitude, activeX, observedWidth, observedHeight]);
  return (
    <div ref={ref} className="relative h-[clamp(160px,32vw,260px)] min-w-0">
      <canvas className="absolute inset-0 h-full w-full" ref={canvas} role="img" aria-label={label} />
    </div>
  );
}
