"use client";

import { useCallback, useState } from "react";
import { useScienceRequest } from "@/hooks/useScienceRequest";
import { scienceApi, type EpochPair, type SkyField } from "@/lib/api/science";
import { observationDate } from "./ArchivePanel";
import { controlClass, Panel, Status } from "./Panel";

export function SourcePanel({ epochs, targetId, field, autoMeasure = false }: {
  epochs: EpochPair; targetId: string | null; field: SkyField; autoMeasure?: boolean;
}) {
  const [requested, setRequested] = useState(0);
  const load = useCallback((signal: AbortSignal) => scienceApi.sourceSeries(targetId, field, epochs, signal),
    [targetId, field, epochs]);
  const measuring = autoMeasure || requested > 0;
  const series = useScienceRequest(measuring ? load : null, requested);
  return (
    <Panel title="Source photometry" actions={<button type="button" className={controlClass}
      disabled={series.loading} onClick={() => setRequested((value) => value + 1)}>Measure epochs</button>}>
      {series.loading && <Status>Fitting the SPHEREx source…</Status>}
      {series.error && <Status error>{series.error}</Status>}
      {!measuring && <Status>Fit the source flux at each observation’s wavelength.</Status>}
      {series.data?.samples.map((sample) => (
        <div className="border-b border-border-subtle py-1.5 last:border-0" key={sample.epoch}>
          <p className="font-mono text-[11px] text-[#cad6e2]">{observationDate(sample.mjd)}</p>
          {sample.photometry ? <Status>
            {sample.photometry.wavelength_um.toFixed(3)} µm · {sample.photometry.flux_density_ujy.toFixed(1)} ± {sample.photometry.statistical_error_ujy.toFixed(1)} µJy
            {sample.photometry.quality_flags.length > 0 && ` · ${sample.photometry.quality_flags.join(", ").replaceAll("_", " ")}`}
          </Status> : <Status>{sample.error?.message}{sample.error?.details?.core_flags.length ? ` · ${sample.error.details.core_flags.join(", ")}` : ""}</Status>}
        </div>
      ))}
      {series.data?.light_curves.map((curve, index) => curve.change && (
        <p className="mt-2 font-mono text-[11px] text-cyan-bright" key={index}>
          {curve.wavelength_um.toFixed(3)} µm · Δ {curve.change.flux_change_ujy.toFixed(1)} ± {curve.change.statistical_error_ujy.toFixed(1)} µJy
        </p>
      ))}
      {series.data && !series.data.light_curves.some((curve) => curve.change) && <Status>No qualified same-band flux change in this pair.</Status>}
    </Panel>
  );
}
