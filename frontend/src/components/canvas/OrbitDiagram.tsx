"use client";

import { useRef } from "react";
import { useAnimationClock, type AnimationClock } from "@/hooks/useAnimationClock";
import { useElementSize } from "@/hooks/useElementSize";
import { prepareCanvas } from "@/lib/utils/canvas";

interface OrbitDiagramProps {
  clock: AnimationClock;
  /** Orbit ring to highlight, taken from the selected candidate's `orbitIdx`. */
  selectedOrbitIdx: number;
}

const ORBITS = [
  { rx: 56, ry: 15, rot: -0.08, speed: 1.0, phase: 0.4 },
  { rx: 92, ry: 23, rot: 0.05, speed: 0.65, phase: 2.1 },
  { rx: 132, ry: 31, rot: -0.04, speed: 0.42, phase: 4.0 },
];

/**
 * Bottom Planet-X orbit diagram: three inclined orbits with a moving body
 * on each; the selected candidate's orbit (its `orbitIdx`) is highlighted.
 */
export function OrbitDiagram({ clock, selectedOrbitIdx }: OrbitDiagramProps) {
  const { ref } = useElementSize<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useAnimationClock(clock, () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dims = prepareCanvas(canvas);
    if (!dims) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width: w, height: h } = dims;
    const cx = w * 0.34;
    const cy = h * 0.54;

    ORBITS.forEach((orb, idx) => {
      const isSel = idx === selectedOrbitIdx;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(orb.rot);

      ctx.strokeStyle = isSel
        ? "rgba(138, 212, 245, 0.72)"
        : "rgba(84, 118, 150, 0.45)";
      ctx.lineWidth = isSel ? 1.3 : 0.9;
      ctx.beginPath();
      ctx.ellipse(0, 0, orb.rx, orb.ry, 0, 0, Math.PI * 2);
      ctx.stroke();

      const ang = orb.phase + clock.current * orb.speed;
      const bx = Math.cos(ang) * orb.rx;
      const by = Math.sin(ang) * orb.ry;
      ctx.fillStyle = isSel ? "#9de2ff" : "#7398ba";
      ctx.beginPath();
      ctx.arc(bx, by, isSel ? 3.4 : 2.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    // Central glowing star
    const starGrad = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14);
    starGrad.addColorStop(0, "#c8f0ff");
    starGrad.addColorStop(0.35, "rgba(94, 169, 209, 0.65)");
    starGrad.addColorStop(1, "rgba(94, 169, 209, 0)");
    ctx.fillStyle = starGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#e8f7ff";
    ctx.beginPath();
    ctx.arc(cx, cy, 4.2, 0, Math.PI * 2);
    ctx.fill();
  });

  return (
    <div ref={ref} className="flex h-[104px] w-full items-center justify-center">
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  );
}
