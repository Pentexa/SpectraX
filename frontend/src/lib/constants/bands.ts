/** Spectral band constants shared across the dashboard. */

export const BAND_COUNT = 102;

export const BAND_COLS = 17;

/** Wavelength (μm) for a given band index (1-based). */
export function bandWavelength(band: number): number {
  return 0.75 + (band - 1) * 0.042;
}

/** Approximate flux (Jy) for a given band+star seed (demo formula). */
export function bandFlux(band: number, spectralSeed: number): number {
  return (
    12 +
    Math.sin(band * 0.14 * spectralSeed) * 14 +
    band * 0.48
  );
}
