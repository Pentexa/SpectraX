/** Canvas helpers: DPR-aware setup shared by every canvas widget. */

export interface CanvasSize {
  width: number;
  height: number;
}

/**
 * Resize the canvas backing store to match its CSS box (times DPR)
 * and return the CSS pixel size for drawing. Returns null when the
 * element has no measurable size or the context cannot be created.
 */
export function prepareCanvas(
  canvas: HTMLCanvasElement,
  maxDpr = 2,
): CanvasSize | null {
  const rect = canvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;
  if (width <= 0 || height <= 0) return null;

  const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
  const pw = Math.floor(width * dpr);
  const ph = Math.floor(height * dpr);

  if (canvas.width !== pw || canvas.height !== ph) {
    canvas.width = pw;
    canvas.height = ph;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  return { width, height };
}
