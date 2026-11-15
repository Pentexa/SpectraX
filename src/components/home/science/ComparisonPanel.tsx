"use client";

import { useEffect, useState } from "react";
import type { Astrometry, Comparison, ComparisonMode } from "@/lib/api/science";
import { observationDate } from "./ArchivePanel";
import { FitsImage, imageRange, type SkyMark } from "./FitsImage";
import { controlClass, Panel, Status } from "./Panel";

function contamination(value: boolean | null | undefined) {
  return value == null ? "unreported" : value ? "flagged" : "clear";
}

export function ComparisonPanel({ comparison, astrometry, loading, error, mode, onMode, marks }: {
  comparison: Comparison | null;
  astrometry: Astrometry | null;
  loading: boolean;
  error: string | null;
  mode: ComparisonMode;
  onMode: (mode: ComparisonMode) => void;
  marks: SkyMark[];
}) {
  const [blink, setBlink] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [showFlags, setShowFlags] = useState(false);
  const [opacity, setOpacity] = useState(50);
  const [epoch, setEpoch] = useState<"a" | "b">("a");
  useEffect(() => {
    if (!blink) return;
    const interval = window.setInterval(() => setEpoch((current) => current === "a" ? "b" : "a"), 850);
    return () => window.clearInterval(interval);
  }, [blink]);

  const cursor = (key: "a" | "b"): SkyMark[] => {
    const sample = astrometry?.samples.find((item) => item.epoch === comparison?.epochs[key].epoch);
    if (!sample || (!sample.centroid && !astrometry?.predicted_catalog_offset_arcsec)) return [];
    const position = sample.centroid ?? sample.input_position;
    return [{
      id: `centroid-${key}`, ...position, color: sample.centroid ? "#ffffff" : "#e5c37b",
      label: sample.centroid?.method === "saturated_wings" ? "Centroid fitted to the unmasked wings"
        : sample.centroid ? "Measured source center" : "Catalog position at the observation time",
    }];
  };
  const displacement = astrometry?.measured_offset_arcsec;
  const prediction = astrometry?.predicted_catalog_offset_arcsec;
  const overlay = showOverlay && comparison?.units.a === comparison?.units.b;
  const range = comparison ? imageRange(comparison.images.a, comparison.images.b) : [0, 1] as const;
  const originalLabel = (key: "a" | "b") => {
    const record = comparison?.epochs[key];
    return record ? `${key.toUpperCase()} · ${observationDate(record.observation_start_mjd)} · ${record.release} D${record.detector}` : "";
  };

  return (
    <Panel title="Epoch comparison" actions={
      <select aria-label="Comparison mode" className={controlClass} value={mode}
        onChange={(event) => { setBlink(false); onMode(event.target.value as ComparisonMode); }}>
        <option value="side_by_side">Side by side</option>
        <option value="difference">Difference (B − A)</option>
        <option value="sum">Sum</option>
        <option value="stack">Mean stack</option>
      </select>
    }>
      {loading && <Status>Aligning SPHEREx images…</Status>}
      {error && <Status error>{error}</Status>}
      {!comparison && !loading && !error && <Status>Choose two observations from the archive to compare this field.</Status>}
      {comparison && (
        <div className="grid gap-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-[10px] text-[#a5b8ca]">
              {(comparison.alignment.overlap_fraction * 100).toFixed(0)}% common coverage · {comparison.units.a}
            </span>
            <div className="flex flex-wrap gap-2">
              {comparison.units.a === comparison.units.b && (
                <button type="button" aria-pressed={overlay} className={controlClass}
                  onClick={() => { setBlink(false); setShowOverlay((value) => !value); }}>Overlay A/B</button>
              )}
              <button type="button" aria-pressed={blink} className={controlClass}
                onClick={() => { setShowOverlay(false); setBlink((value) => !value); }}>
                {blink ? "Pause blink" : "Blink A/B"}
              </button>
            </div>
          </div>
          {(comparison.flags?.a || comparison.flags?.b) && (
            <label className="flex items-center gap-1 text-[10px] text-[#ec91c6]">
              <input type="checkbox" checked={showFlags} onChange={(event) => setShowFlags(event.target.checked)} />
              Highlight flagged pixels
            </label>
          )}
          {overlay ? (
            <div className="mx-auto grid w-full max-w-md gap-2">
              <label className="grid gap-1 font-mono text-[10px] text-[#a5b8ca]">
                Epoch B weight in overlap · {opacity}%
                <input type="range" min={0} max={100} value={opacity} className="accent-[#6bb9e5]"
                  onChange={(event) => setOpacity(Number(event.target.value))} />
              </label>
              <FitsImage pixels={comparison.images.a} overlay={comparison.images.b} opacity={opacity / 100}
                grid={comparison.grid} range={range} marks={[...marks, ...cursor("a"), ...cursor("b")]}
                flags={showFlags ? [opacity < 100 ? comparison.flags?.a : null, opacity > 0 ? comparison.flags?.b : null] : undefined}
                label={`${originalLabel("a")} / ${originalLabel("b")}`} />
            </div>
          ) : (
            <div className={blink ? "mx-auto w-full max-w-md" : "grid grid-cols-2 gap-2"}>
              {(blink ? [epoch] : ["a", "b"] as const).map((key) => (
                <FitsImage key={key} pixels={comparison.images[key]} grid={comparison.grid}
                  range={range} marks={[...marks, ...cursor(key)]} label={originalLabel(key)}
                  flags={showFlags ? [comparison.flags?.[key]] : undefined} />
              ))}
            </div>
          )}
          {comparison.images.result && (
            <div className="mx-auto w-full max-w-[280px]">
              <FitsImage pixels={comparison.images.result} grid={comparison.grid} range={imageRange(comparison.images.result)}
                signed={mode === "difference"} marks={marks}
                flags={showFlags ? [comparison.flags?.a, comparison.flags?.b] : undefined}
                label={mode === "difference" ? "B − A · blue decrease / orange increase" : mode === "sum" ? "A + B" : "Mean of A and B"} />
            </div>
          )}
          {comparison.measurement && <Status>
            {comparison.measurement.difference === null ? "Center pixel masked or outside the common bandpass."
              : `Center-pixel difference ${comparison.measurement.difference.toPrecision(3)} ${comparison.units.result}.`}
          </Status>}
          {displacement && astrometry && <p className="border-t border-border-subtle pt-2 font-mono text-[11px] text-cyan-bright">
            {Math.abs(displacement.east).toFixed(2)}″ {displacement.east < 0 ? "W" : "E"} · {Math.abs(displacement.north).toFixed(2)}″ {displacement.north < 0 ? "S" : "N"}
            {" · "}{astrometry.elapsed_days.toFixed(1)} days · {astrometry.registration?.used_sources ?? 0} reference stars
            {astrometry.samples.some((sample) => sample.centroid?.method === "saturated_wings") && " · unmasked wing fit"}
          </p>}
          {astrometry && !displacement && (
            <Status>{astrometry.samples.map((sample) => sample.error?.details
              ? `${sample.error.details.core_pixels_usable}/${sample.error.details.core_pixels_total} usable core pixels (${sample.error.details.core_flags.join(", ")})`
              : sample.error?.message).filter(Boolean).join(" · ") || "Relative astrometry could not be independently registered."}</Status>
          )}
          {astrometry && !displacement && prediction && (
            <p className="font-mono text-[10px] text-[#e5c37b]">
              Catalog prediction over {astrometry.elapsed_days.toFixed(1)} days ·
              {" "}{prediction.east.toFixed(2)}″ east · {prediction.north.toFixed(2)}″ north
            </p>
          )}
          <details className="text-[10px] text-text-muted">
            <summary className="cursor-pointer">Image quality and provenance</summary>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              {(["a", "b"] as const).map((key) => {
                const record = comparison.epochs[key];
                const fits = record.fits;
                const counts = comparison.flag_counts?.[key];
                const labels = Object.entries(counts ?? {});
                return <li key={key}>
                  {key.toUpperCase()} · {record.observation_id}
                  {fits && <div>Aurora {contamination(fits.aurora_contamination)} · helium airglow {contamination(fits.helium_airglow_contamination)}
                    {" · "}shuttle glow {contamination(fits.shuttle_glow_contamination)}</div>}
                  {fits?.quality_hdus.length ? <div>FITS extensions · {fits.quality_hdus.join(", ")}</div> : null}
                  <div className="break-words">{labels.length
                    ? labels.map(([label, count]) => `${label} ${count}`).join(" · ")
                    : counts ? "No flagged pixels in this field." : "Pixel flag counts unavailable."}</div>
                </li>;
              })}
              {comparison.warnings.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          </details>
        </div>
      )}
    </Panel>
  );
}
