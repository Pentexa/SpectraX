import { apiClient } from "./client";

export interface SkyField {
  ra: number;
  dec: number;
  fov: number;
}

export type ScienceTarget = SkyField & {
  id: string;
  name: string;
  kind: "proper_motion" | "binary" | "variability";
  benchmark_available: boolean;
  timeline_epochs?: string[];
  recommended_wavelength_um: number;
  pm_ra_cosdec_mas_yr: number;
  pm_dec_mas_yr: number;
  parallax_mas: number;
  source: string;
  note: string | null;
};

export type Pixels = (number | null)[][];
export interface SkyGrid {
  width: number;
  height: number;
  wcs: Record<string, number | string>;
}

export interface Exposure {
  epoch: string;
  observation_id: string;
  observation_start_mjd: number;
  release: string;
  detector: number;
  fits?: {
    aurora_contamination: boolean | null;
    helium_airglow_contamination?: boolean | null;
    shuttle_glow_contamination?: boolean | null;
    quality_hdus: string[];
  };
}

export interface Astrometry {
  status: "measured" | "centroid_unavailable" | "registration_unverified";
  elapsed_days: number;
  predicted_catalog_offset_arcsec: { east: number; north: number } | null;
  measured_offset_arcsec: {
    east: number;
    north: number;
    significance: number;
    uncertainty_covariance_arcsec2: number[][];
  } | null;
  registration: { used_sources: number } | null;
  samples: { epoch: string; input_position: SkyField | Omit<SkyField, "fov">;
    centroid: { ra: number; dec: number; snr: number | null; method?: "saturated_wings" } | null;
    error: { message: string; details?: { core_pixels_usable: number; core_pixels_total: number; core_flags: string[] } } | null }[];
}

export type ComparisonMode = "side_by_side" | "difference" | "sum" | "stack";
export interface Comparison {
  mode: ComparisonMode;
  grid: SkyGrid;
  images: { a: Pixels; b: Pixels; result: Pixels | null };
  units: { a: string; b: string; result: string | null };
  epochs: { a: Exposure; b: Exposure };
  alignment: { overlap_fraction: number; arithmetic_valid_fraction: number | null };
  measurement: { difference: number | null; uncertainty: number | null } | null;
  warnings: string[];
  flags?: { a: Pixels | null; b: Pixels | null };
  flag_counts?: { a: Record<string, number> | null; b: Record<string, number> | null };
}

export interface Benchmark {
  comparison: Comparison;
  astrometry: Astrometry;
}

export interface ArchiveObservation {
  archive_id: string;
  observation_id: string;
  observation_start_mjd: number | null;
  band: string;
  epoch: string | null;
  predicted_position?: { ra: number; dec: number };
}

export type ArchiveCutout = Pick<ArchiveObservation, "archive_id" | "predicted_position"> & { local_epoch?: string };
export type EpochPair = readonly [string, string];
export const MAX_TIMELINE_EPOCHS = 8;

export interface Timeline {
  grid: SkyGrid;
  unit: string;
  matching_bandpasses: boolean;
  frames: {
    epoch: string;
    observation_id: string;
    mjd: number;
    release: string;
    detector: number | null;
    wavelength_um: number | null;
    coverage: number;
    pixels: Pixels;
    flags: Pixels | null;
  }[];
}

export function archiveCutoutWidth(fov: number) {
  return Math.max(0.02, Math.min(fov, 0.2));
}

export interface SpectrumChannel {
  detector: number;
  channel: number;
  wavelength_um: number;
  flux: number | null;
  masked: boolean;
  nhits: number;
  flag_names?: string[];
}

export interface Spectrum {
  epoch: string;
  unit: string;
  available_channels: number;
  channels: SpectrumChannel[];
}

export type SpectralImage = {
  image: Pixels;
  grid: SkyGrid;
  flags: Pixels;
  unit: string;
} & ({
  aggregation?: undefined;
  wavelength_um: number;
} | {
  aggregation: "nhits_weighted_mean";
  min_wavelength_um: number;
  max_wavelength_um: number;
  channels_combined: number;
  channel_count: Pixels;
  nhits: Pixels;
});

export interface CatalogOverlay {
  catalog: string;
  reference_epoch_jyear: number | null;
  sources: { id: string; ra: number; dec: number }[];
}

export interface ReferenceCurve {
  source: string;
  band: string;
  acknowledgment: string;
  has_more: boolean;
  points: { mjd: number; magnitude: number; fainter_than: boolean }[];
}

export interface SourceSeries {
  samples: {
    epoch: string; mjd: number;
    photometry: { wavelength_um: number; flux_density_ujy: number; statistical_error_ujy: number; quality_flags: string[] } | null;
    error: { message: string; details?: { core_flags: string[] } } | null;
  }[];
  light_curves: { wavelength_um: number; change: { flux_change_ujy: number; statistical_error_ujy: number } | null }[];
  aperture_change?: {
    wavelength_a_um: number;
    wavelength_b_um: number;
    elapsed_days: number;
    fractional_systematic_per_epoch: number;
    measurement: {
      a: { flux_ujy: number };
      b: { flux_ujy: number };
      change_ujy: number;
      uncertainty_ujy: number;
      snr: number;
    };
  } | null;
  wing_change?: {
    wavelength_a_um: number;
    wavelength_b_um: number;
    elapsed_days: number;
    rings: {
      inner_arcsec: number;
      outer_arcsec: number;
      common_pixels: number;
      a_mjy_sr: number;
      b_mjy_sr: number;
      change_mjy_sr: number;
    }[];
  } | null;
}

export interface Release {
  id: string;
  status: string;
  planned_month: string | null;
}

function query(path: string, values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) params.set(key, String(value));
  }
  return `${path}?${params}`;
}

export const scienceApi = {
  targets: () => apiClient.get<{ targets: ScienceTarget[] }>("/api/targets"),
  releases: (signal: AbortSignal) => apiClient.get<{ releases: Release[] }>("/api/releases", { signal }),
  benchmark: (targetId: string, fov: number, signal: AbortSignal) =>
    apiClient.get<Benchmark>(query(`/api/targets/${encodeURIComponent(targetId)}/benchmark`, { fov }), { signal }),
  observations: (targetId: string | null, field: SkyField, release: string, wavelength?: number,
    start_mjd?: number, end_mjd?: number) =>
    apiClient.get<{ observations: ArchiveObservation[]; scope?: "live" | "local"; archive?: { scope?: "live" | "local" } }>(query(
      targetId ? `/api/targets/${encodeURIComponent(targetId)}/observations` : "/api/archive/search",
      { ...(targetId ? {} : { ra: field.ra, dec: field.dec, radius_deg: field.fov / 2 }),
        release, wavelength_um: wavelength, start_mjd, end_mjd, limit: 40 },
    ), { timeout: 45_000 }),
  importExposure: (observation: ArchiveCutout, field: SkyField, signal?: AbortSignal) =>
    apiClient.post<Exposure>("/api/archive/import", {
      archive_id: observation.archive_id,
      ra: observation.predicted_position?.ra ?? field.ra,
      dec: observation.predicted_position?.dec ?? field.dec,
      fov: archiveCutoutWidth(field.fov),
    }, { signal, timeout: 110_000 }),
  importExposures: async (observations: readonly ArchiveCutout[], field: SkyField, signal?: AbortSignal) => {
    const epochs: string[] = [];
    for (let index = 0; index < observations.length; index += 2) {
      epochs.push(...await Promise.all(observations.slice(index, index + 2).map(async (observation) =>
        observation.local_epoch ?? (await scienceApi.importExposure(observation, field, signal)).epoch)));
    }
    return epochs;
  },
  timeline: (field: SkyField, epochs: readonly string[], signal: AbortSignal) =>
    apiClient.post<Timeline>("/api/timeline", { ...field, epochs }, { signal, timeout: 25_000 }),
  compare: (field: SkyField, epochs: readonly [string, string], mode: ComparisonMode, signal: AbortSignal) =>
    apiClient.get<Comparison>(query("/api/compare", { ...field, epoch_a: epochs[0], epoch_b: epochs[1], mode }), { signal }),
  astrometry: (targetId: string | null, field: SkyField, epochs: readonly [string, string], signal: AbortSignal) =>
    apiClient.post<Astrometry>("/api/astrometry", {
      ...(targetId ? { target_id: targetId } : { ra: field.ra, dec: field.dec }), epochs, fov: Math.max(0.02, field.fov),
    }, { signal }),
  sourceSeries: (targetId: string | null, field: SkyField, epochs: readonly [string, string], signal: AbortSignal) =>
    apiClient.post<SourceSeries>("/api/source-series", {
      ...(targetId ? { target_id: targetId } : { ra: field.ra, dec: field.dec }), epochs,
    }, { signal, timeout: 20_000 }),
  spectrum: (field: SkyField, signal: AbortSignal) =>
    apiClient.get<Spectrum>(query("/api/spectrum", { ra: field.ra, dec: field.dec }), { signal, timeout: 270_000 }),
  layer: (field: SkyField, detector: number, channel: number | undefined, epoch: string, signal: AbortSignal) =>
    apiClient.get<SpectralImage>(query(`/api/layers/${detector}`, {
      ...field, epoch, channel, combine: channel === undefined ? 1 : undefined,
    }),
      { signal, timeout: 270_000 }),
  overlay: (catalog: "gaia" | "wise", field: SkyField, signal: AbortSignal) =>
    apiClient.get<CatalogOverlay>(query(`/api/catalog/${catalog}`, {
      ra: field.ra, dec: field.dec, radius_deg: field.fov * Math.SQRT1_2, limit: 150,
    }), { signal, timeout: 40_000 }),
  reference: (targetId: string, signal: AbortSignal) => apiClient.get<ReferenceCurve>(query(
    `/api/targets/${encodeURIComponent(targetId)}/reference-light-curve`,
    targetId === "r-draconis" ? { start_mjd: 61180, end_mjd: 61308, limit: 129 }
      : { start_mjd: 60925, end_mjd: 61008, limit: 700, band: "V" },
  ), { signal, timeout: 35_000 }),
};
