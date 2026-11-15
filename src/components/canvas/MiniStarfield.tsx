"use client";

import { useEffect, useRef } from "react";
import { useAnimationClock, type AnimationClock } from "@/hooks/useAnimationClock";
import { prepareCanvas } from "@/lib/utils/canvas";
import { mulberry32 } from "@/lib/utils/random";

interface MiniStarfieldProps {
  /** Canvas seed — pair two canvases with different seeds for the A/B frames. */
  seed: number;
  /** Target star offset when static, or the starting offset when animating. */
  shiftX?: number;
  /**
   * When set together with `clock`, the target star oscillates between
   * `shiftX` and this value — an animated time-lapse on the card.
   */
  shiftTo?: number;
  clock?: AnimationClock;
  /**
   * When the animation stops while this prop is true (i.e. playback was
   * paused, not the card deselected), the canvas holds the last animated
   * position instead of snapping back to `shiftX`.
   */
  holdOnPause?: boolean;
  className?: string;
}

/** Design-space size; the canvas is stretched to its CSS box. */
const W = 160;
const H = 92;
const TARGET_Y = 46;

function drawStarfield(canvas: HTMLCanvasElement, seed: number, shiftX: number) {
  const dims = prepareCanvas(canvas);
  if (!dims) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Draw in the W×H design space; the non-uniform scale reproduces the
  // CSS-stretch of the fixed-size backing store, just DPR-sharp.
  ctx.scale(dims.width / W, dims.height / H);

  ctx.fillStyle = "#070b10";
  ctx.fillRect(0, 0, W, H);

  const rand = mulberry32(seed);
  for (let i = 0; i < 65; i++) {
    const x = rand() * W;
    const y = rand() * H;
    const r = rand() * 1.1 + 0.3;
    const alpha = rand() * 0.75 + 0.2;
    ctx.fillStyle = `rgba(210, 228, 248, ${alpha})`;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }

  // Moving target star
  ctx.fillStyle = "rgba(125, 206, 245, 0.95)";
  ctx.beginPath();
  ctx.arc(80 + shiftX, TARGET_Y, 1.8, 0, Math.PI * 2);
  ctx.fill();
}

/**
 * Deterministic starfield for epoch comparison cards. When animated, the
 * target star slides back and forth between the A and B frame positions.
 */
export function MiniStarfield({
  seed,
  shiftX = 0,
  shiftTo,
  clock,
  holdOnPause = false,
  className,
}: MiniStarfieldProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  /** Most recent animated position; null until the card has animated. */
  const lastShiftRef = useRef<number | null>(null);
  const animating = typeof shiftTo === "number" && clock != null;

  // Static drawing (non-animated cards)
  useEffect(() => {
    if (animating) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const hold = holdOnPause && lastShiftRef.current !== null;
    drawStarfield(canvas, seed, hold ? (lastShiftRef.current as number) : shiftX);
  }, [seed, shiftX, animating, holdOnPause]);

  // Animated drawing (active, playing card)
  useAnimationClock(clock, (time) => {
    if (!animating || !clock || shiftTo === undefined) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const t = (Math.sin(time * 1.8) + 1) / 2;
    const shift = shiftX + (shiftTo - shiftX) * t;
    lastShiftRef.current = shift;
    drawStarfield(canvas, seed, shift);
  });

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
