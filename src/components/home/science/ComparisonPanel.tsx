"use client";

import { useEffect, useState } from "react";
import type { Astrometry, Comparison, ComparisonMode } from "@/lib/api/science";
import { observationDate } from "./ArchivePanel";
import { FitsImage, imageRange, type SkyMark } from "./FitsImage";
import { controlClass, Panel, Status } from "./Panel";

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
  const [epoch, setEpoch] = useState<"a" | "b">("a");
  useEffect(() => {
    if (!blink) return;
    const interval = window.setInterval(() => setEpoch((current) => current === "a" ? "b" : "a"), 850);
    return () => window.clearInterval(interval);
  }, [blink]);

  const cursor = (key: "a" | "b"): SkyMark[] => {
    const sample = astrometry?.samples.find((item) => item.epoch === comparison?.epochs[key].epoch);
    return sample?.centroid ? [{
      id: `centroid-${key}`, ...sample.centroid, color: "#ffffff", label: "Measured source center",
    }] : [];
  };
  const displacement = astrometry?.measured_offset_arcsec;
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
            <button type="button" aria-pressed={blink} className={controlClass} onClick={() => setBlink((value) => !value)}>
              {blink ? "Pause blink" : "Blink A/B"}
            </button>
          </div>
          <div className={blink ? "mx-auto w-full max-w-md" : "grid grid-cols-2 gap-2"}>
            {(blink ? [epoch] : ["a", "b"] as const).map((key) => (
              <FitsImage key={key} pixels={comparison.images[key]} grid={comparison.grid}
                range={range} marks={[...marks, ...cursor(key)]} label={originalLabel(key)} />
            ))}
          </div>
          {comparison.images.result && (
            <div className="mx-auto w-full max-w-[280px]">
              <FitsImage pixels={comparison.images.result} grid={comparison.grid} range={imageRange(comparison.images.result)}
                signed={mode === "difference"} marks={marks}
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
          </p>}
          {astrometry && !displacement && (
            <Status>{astrometry.samples.map((sample) => sample.error?.details
              ? `${sample.error.details.core_pixels_usable}/${sample.error.details.core_pixels_total} usable core pixels (${sample.error.details.core_flags.join(", ")})`
              : sample.error?.message).filter(Boolean).join(" · ") || "Relative astrometry could not be independently registered."}</Status>
          )}
          <details className="text-[10px] text-text-muted">
            <summary className="cursor-pointer">Image quality and provenance</summary>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              <li>{comparison.epochs.a.observation_id} · {comparison.epochs.b.observation_id}</li>
              {comparison.warnings.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          </details>
        </div>
      )}
    </Panel>
  );
}
