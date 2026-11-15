/**
 * Coordinate parsing helpers.
 * Converts the display strings from the API ("17h 57m", "+04° 41\"")
 * into J2000 degrees usable with Aladin Lite.
 */

/** Parse right ascension "Xh Ym Zs" → degrees (0..360). */
export function parseRAhms(ra: string): number {
  if (ra.trim() && Number.isFinite(Number(ra))) return Number(ra);
  const match = ra.match(/(\d+(?:\.\d+)?)h\s*(\d+(?:\.\d+)?)m(?:\s*(\d+(?:\.\d+)?)s)?/i);
  if (!match) return NaN;
  const hours = parseFloat(match[1]);
  const minutes = parseFloat(match[2]);
  const seconds = match[3] ? parseFloat(match[3]) : 0;
  return (hours + minutes / 60 + seconds / 3600) * 15;
}

/** Parse declination "+04° 41\"" or "-56° 47\"" → degrees (-90..90). */
export function parseDecDMS(dec: string): number {
  if (dec.trim() && Number.isFinite(Number(dec))) return Number(dec);
  const match = dec.match(/([+-]?)(\d+(?:\.\d+)?)°\s*(\d+(?:\.\d+)?)(?:\s*(\d+(?:\.\d+)?)")?/);
  if (!match) return NaN;
  const sign = match[1] === "-" ? -1 : 1;
  const degrees = parseFloat(match[2]);
  const minutes = parseFloat(match[3]);
  const seconds = match[4] ? parseFloat(match[4]) : 0;
  return sign * (degrees + minutes / 60 + seconds / 3600);
}
