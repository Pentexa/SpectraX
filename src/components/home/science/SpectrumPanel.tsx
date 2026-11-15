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
  const [combinedDetector, setCombinedDetector] = useState(0);
  const [showFlags, setShowFlags] = useState(false);
  const spectrumRequest = useCallback((signal: AbortSignal) => scienceApi.spectrum(field, signal), [field]);
  const spectrum = useScienceRequest(requested ? spectrumRequest : null, requested);
  const channels = spectrum.data?.channels ?? [];
  const channel = channels[selected];
  const epoch = spectrum.data?.epoch;
  const detector = combinedDetector || channel?.detector;
  const subchannel = combinedDetector ? undefined : channel?.channel;
  const bandRequest = useCallback((signal: AbortSignal) => {
    if (!detector || !epoch) throw new Error("Select a calibrated detector first.");
    return scienceApi.layer(field, detector, subchannel, epoch, signal);
  }, [field, detector, subchannel, epoch]);
  const band = useScienceRequest(showBand && detector && epoch ? bandRequest : null);
  const image = band.data;
  const center = image ? Math.floor(image.grid.width / 2) : 0;

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
            {spectrum.data.delivery && <Status>{spectrum.data.delivery === "archive_cube"
              ? "Official DR1 archive cube" : "Downloaded FITS fallback"}</Status>}
            <SciencePlot points={channels.map((point) => ({ x: point.wavelength_um, y: point.flux }))} label="SPHEREx spectral surface brightness" xLabel="Wavelength (µm)" />
            <div className="grid grid-cols-[repeat(17,1fr)] gap-0.5" aria-label="102 detector channels">
              {channels.map((point, index) => (
                <button key={`${point.detector}-${point.channel}`} type="button" title={`D${point.detector} · ${point.wavelength_um.toFixed(3)} µm${point.masked ? " · masked" : ""}`}
                  aria-label={`Channel ${index + 1}, ${point.wavelength_um.toFixed(3)} micrometers`}
                  aria-pressed={index === selected} onClick={() => { setSelected(index); setCombinedDetector(0); }}
                  className={`aspect-square rounded-[1.5px] border outline-offset-1 hover:border-cyan-bright ${index === selected ? "border-white bg-cyan shadow-[0_0_5px_var(--color-cyan)]" : point.masked ? "border-[#25313e] bg-[#101820]" : "border-[#34485e] bg-[#3f6684]"}`} />
              ))}
            </div>
            {channel && <Status>
              D{channel.detector} · {channel.wavelength_um.toFixed(3)} µm · {channel.flux === null ? "Masked here" : `${channel.flux.toPrecision(4)} ${spectrum.data.unit}`}
              {" · "}{channel.nhits} input pixels{channel.flag_names?.length ? ` · ${channel.flag_names.join(", ")}` : ""}
            </Status>}
            <div className="flex flex-wrap gap-2">
              <select aria-label="Spectral image" className={controlClass} value={combinedDetector}
                onChange={(event) => { setCombinedDetector(Number(event.target.value)); setShowBand(true); }}>
                <option value={0}>Selected channel</option>
                {[1, 2, 3, 4, 5, 6].map((id) => <option key={id} value={id}>D{id} · 17-channel mean</option>)}
              </select>
              <button type="button" className={controlClass} aria-pressed={showBand} onClick={() => setShowBand((value) => !value)}>
                {showBand ? "Hide image" : "Show image"}
              </button>
            </div>
            {band.loading && <Status>Loading spectral image…</Status>}
            {band.error && <Status error>{band.error}</Status>}
            {image && (
              <>
                <label className="flex items-center gap-1 text-[10px] text-[#ec91c6]">
                  <input type="checkbox" checked={showFlags} onChange={(event) => setShowFlags(event.target.checked)} /> Highlight flagged pixels
                </label>
                <FitsImage pixels={image.image} grid={image.grid} range={imageRange(image.image)}
                  flags={showFlags ? [image.flags] : undefined}
                  label={image.aggregation
                    ? `D${combinedDetector} · ${image.min_wavelength_um.toFixed(3)}–${image.max_wavelength_um.toFixed(3)} µm · ${image.unit}`
                    : `${image.wavelength_um.toFixed(3)} µm · ${image.unit}`} />
                {image.aggregation && <Status>
                  Mean weighted by input pixel count. Center: {image.channel_count[center]?.[center] ?? 0}/{image.channels_combined} channels · {image.nhits[center]?.[center] ?? 0} input pixels.
                </Status>}
              </>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}
