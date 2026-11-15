"use client";

import { useCallback, useState } from "react";
import { useScienceRequest } from "@/hooks/useScienceRequest";
import { scienceApi, type SkyField } from "@/lib/api/science";
import { FitsImage, imageRange } from "./FitsImage";
import { controlClass, Panel, Status } from "./Panel";
import { SciencePlot } from "./SciencePlot";

export function SpectrumPanel({ field }: { field: SkyField }) {
  const [requested, setRequested] = useState(0);
  const [selected, setSelected] = useState(0);
  const [showBand, setShowBand] = useState(false);
  const spectrumRequest = useCallback((signal: AbortSignal) => scienceApi.spectrum(field, signal), [field]);
  const spectrum = useScienceRequest(requested ? spectrumRequest : null, requested);
  const channels = spectrum.data?.channels ?? [];
  const channel = channels[selected];
  const epoch = spectrum.data?.epoch;
  const bandRequest = useCallback((signal: AbortSignal) => {
    if (!channel || !epoch) throw new Error("Select a calibrated channel first.");
    return scienceApi.layer(field, channel, epoch, signal);
  }, [field, channel, epoch]);
  const band = useScienceRequest(showBand && channel && epoch ? bandRequest : null);

  return (
    <Panel title="Spectral analysis · 102 bands">
      <div className="grid gap-2.5">
        {!spectrum.data && !spectrum.loading && (
          <button type="button" className={controlClass} onClick={() => setRequested((value) => value + 1)}>
            {requested ? "Retry spectrum" : "Load DR1 spectrum"}
          </button>
        )}
        {spectrum.loading && <Status>Loading DR1 cube. A new sky tile can take a few minutes.</Status>}
        {spectrum.error && <Status error>{spectrum.error}</Status>}
        {spectrum.data && (
          <>
            <Status>{spectrum.data.available_channels}/102 available · multi-epoch surface brightness · {spectrum.data.unit}</Status>
            <SciencePlot points={channels.map((point) => ({ x: point.wavelength_um, y: point.flux }))} label="SPHEREx spectral surface brightness" xLabel="Wavelength (µm)" />
            <div className="grid grid-cols-[repeat(17,1fr)] gap-0.5" aria-label="102 detector channels">
              {channels.map((point, index) => (
                <button key={`${point.detector}-${point.channel}`} type="button" title={`D${point.detector} · ${point.wavelength_um.toFixed(3)} µm${point.masked ? " · masked" : ""}`}
                  aria-label={`Channel ${index + 1}, ${point.wavelength_um.toFixed(3)} micrometers`}
                  aria-pressed={index === selected} onClick={() => setSelected(index)}
                  className={`aspect-square rounded-[1.5px] border outline-offset-1 hover:border-cyan-bright ${index === selected ? "border-white bg-cyan shadow-[0_0_5px_var(--color-cyan)]" : point.masked ? "border-[#25313e] bg-[#101820]" : "border-[#34485e] bg-[#3f6684]"}`} />
              ))}
            </div>
            {channel && <Status>D{channel.detector} · {channel.wavelength_um.toFixed(3)} µm · {channel.flux === null ? "Masked here" : `${channel.flux.toPrecision(4)} ${spectrum.data.unit}`}</Status>}
            <button type="button" className={controlClass} aria-pressed={showBand} onClick={() => setShowBand((value) => !value)}>
              {showBand ? "Hide band image" : "Show band image"}
            </button>
            {band.loading && <Status>Loading selected channel…</Status>}
            {band.error && <Status error>{band.error}</Status>}
            {band.data && (
              <FitsImage pixels={band.data.image} grid={band.data.grid} range={imageRange(band.data.image)}
                label={`${band.data.wavelength_um.toFixed(3)} µm · ${band.data.unit}`} />
            )}
          </>
        )}
      </div>
    </Panel>
  );
}
