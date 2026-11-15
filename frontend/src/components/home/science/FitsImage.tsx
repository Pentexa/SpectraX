"use client";

import { useEffect, useRef } from "react";
import type { Pixels, SkyGrid } from "@/lib/api/science";

export type SkyMark = { id: string; ra: number; dec: number; color: string; label: string };

export function imageRange(...images: Pixels[]) {
  const values = images.flat(2).filter((value): value is number => value !== null && Number.isFinite(value));
  values.sort((a, b) => a - b);
  if (values.length === 0) return [0, 1] as const;
  const low = values[Math.floor((values.length - 1) * 0.02)];
  const high = values[Math.ceil((values.length - 1) * 0.98)];
  return [low, high > low ? high : low + 1] as const;
}

function project(grid: SkyGrid, ra: number, dec: number) {
  const rad = Math.PI / 180;
  const deltaRa = (ra - Number(grid.wcs.CRVAL1)) * rad;
  const dec0 = Number(grid.wcs.CRVAL2) * rad;
  const latitude = dec * rad;
  const scale = Math.sin(dec0) * Math.sin(latitude) + Math.cos(dec0) * Math.cos(latitude) * Math.cos(deltaRa);
  if (scale <= 0) return null;
  const east = Math.cos(latitude) * Math.sin(deltaRa) / scale / rad;
  const north = (Math.cos(dec0) * Math.sin(latitude) - Math.sin(dec0) * Math.cos(latitude) * Math.cos(deltaRa)) / scale / rad;
  const x = (Number(grid.wcs.CRPIX1) - 0.5 + east / Number(grid.wcs.CDELT1)) / grid.width;
  const y = 1 - (Number(grid.wcs.CRPIX2) - 0.5 + north / Number(grid.wcs.CDELT2)) / grid.height;
  return x >= 0 && x <= 1 && y >= 0 && y <= 1 ? { x, y } : null;
}

export function FitsImage({ pixels, grid, range, marks = [], signed = false, label,
  flags, overlay, opacity = 0.5 }: {
  pixels: Pixels;
  grid: SkyGrid;
  range: readonly [number, number];
  marks?: SkyMark[];
  signed?: boolean;
  label: string;
  flags?: readonly (Pixels | null | undefined)[];
  overlay?: Pixels;
  opacity?: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [low, high] = range;
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    const raster = ctx.createImageData(grid.width, grid.height);
    const absolute = Math.max(Math.abs(low), Math.abs(high), 1e-12);
    for (let row = 0; row < grid.height; row++) {
      const sourceRow = grid.height - row - 1;
      for (let column = 0; column < grid.width; column++) {
        const base = pixels[sourceRow]?.[column];
        const other = overlay?.[sourceRow]?.[column];
        const value = opacity === 0 ? base : opacity === 1 ? other
          : base == null ? other : other == null ? base : base * (1 - opacity) + other * opacity;
        const offset = (row * grid.width + column) * 4;
        const intensity = value == null ? 0 : signed ? Math.sqrt(Math.min(1, Math.abs(value) / absolute))
          : Math.asinh(8 * Math.max(0, Math.min(1, (value - low) / (high - low)))) / Math.asinh(8);
        const warm = signed && value != null && value > 0;
        // The SOURCE bit marks a detected source rather than a pixel defect.
        const flagged = flags?.some((map) => ((map?.[sourceRow]?.[column] ?? 0) & ~(1 << 21)) !== 0);
        raster.data[offset] = flagged ? 164 + intensity * 85 : 8 + intensity * (warm ? 244 : 146);
        raster.data[offset + 1] = flagged ? 49 + intensity * 95 : 15 + intensity * (warm ? 128 : 181);
        raster.data[offset + 2] = flagged ? 128 + intensity * 115 : 23 + intensity * (warm ? 62 : 226);
        raster.data[offset + 3] = 255;
      }
    }
    ctx.putImageData(raster, 0, 0);
  }, [grid, pixels, low, high, signed, flags, overlay, opacity]);

  return (
    <figure className="min-w-0">
      <div className="relative overflow-hidden rounded-[2px] border border-[#2b3b4d] bg-[#080f17]" style={{ aspectRatio: `${grid.width}/${grid.height}` }}>
        <canvas ref={canvas} width={grid.width} height={grid.height} role="img" aria-label={label}
          className="absolute inset-0 h-full w-full [image-rendering:pixelated]" />
        {marks.map((mark) => {
          const point = project(grid, mark.ra, mark.dec);
          if (!point) return null;
          return <span key={mark.id} title={mark.label} aria-label={mark.label} className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border shadow-sm"
            style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%`, borderColor: mark.color }} />;
        })}
      </div>
      <figcaption className="mt-1 break-words font-mono text-[10px] text-[#a5b8ca]">{label}</figcaption>
    </figure>
  );
}
