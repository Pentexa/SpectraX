"use client";

import { useEffect, useRef } from "react";

type Point = { x: number; y: number | null };

export function SciencePlot({ points, label, xLabel, magnitude = false }: {
  points: Point[]; label: string; xLabel: string; magnitude?: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    const values = points.flatMap((point) => point.y === null ? [] : [point.y]);
    ctx.clearRect(0, 0, 600, 210);
    if (values.length === 0) return;
    const x0 = Math.min(...points.map((point) => point.x));
    const x1 = Math.max(x0 + 1e-6, ...points.map((point) => point.x));
    const y0 = Math.min(...values);
    const y1 = Math.max(y0 + 1e-6, ...values);
    const left = 76, right = 582, top = 16, bottom = 169;
    const x = (value: number) => left + (value - x0) / (x1 - x0) * (right - left);
    const y = (value: number) => (magnitude ? top : bottom) + (value - y0) / (y1 - y0) * (bottom - top) * (magnitude ? 1 : -1);
    ctx.font = "16px monospace";
    ctx.fillStyle = "#a5b8ca";
    ctx.strokeStyle = "#293c50";
    for (let i = 0; i <= 3; i++) {
      const value = y0 + (y1 - y0) * i / 3;
      const py = y(value);
      ctx.fillText(value.toPrecision(3), 5, py + 5);
      ctx.beginPath();
      ctx.moveTo(left, py);
      ctx.lineTo(right, py);
      ctx.stroke();
    }
    ctx.fillText(x0.toFixed(magnitude ? 0 : 2), left, 192);
    ctx.textAlign = "right";
    ctx.fillText(x1.toFixed(magnitude ? 0 : 2), right, 192);
    ctx.textAlign = "center";
    ctx.fillText(xLabel, (left + right) / 2, 206);
    ctx.textAlign = "left";
    ctx.strokeStyle = "#74c9f2";
    ctx.fillStyle = "#88d5fd";
    ctx.lineWidth = 2.4;
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
  }, [points, xLabel, magnitude]);
  return <canvas className="h-auto w-full" width="600" height="210" ref={canvas} role="img" aria-label={label} />;
}
