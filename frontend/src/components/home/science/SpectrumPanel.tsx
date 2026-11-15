"use client";

import { useCallback, useState } from "react";
import { useScienceRequest } from "@/hooks/useScienceRequest";
import { scienceApi, type SkyField } from "@/lib/api/science";
import { FitsImage, imageRange } from "./FitsImage";
import { controlClass, Panel, Status } from "./Panel";
import { SciencePlot } from "./SciencePlot";

const detectors = [1, 2, 3, 4, 5, 6];

export function SpectrumPanel({ field, explorer = false }: { field: SkyField; explorer?: boolean }) {
  const { ra, dec } = field;
  const [requested, setRequested] = useState(explorer ? 1 : 0);
  const [selected, setSelected] = useState<number | null>(null);
  const [showBand, setShowBand] = useState(explorer);
  const [combinedDetector, setCombinedDetector] = useState(0);
  const [showFlags, setShowFlags] = useState(false);
  const [pixelView, setPixelView] = useState(false);
  const spectrumRequest = useCallback((signal: AbortSignal) => scienceApi.spectrum({ ra, dec }, signal), [ra, dec]);
  const spectrum = useScienceRequest(requested ? spectrumRequest : null, requested);
  const channels = spectrum.data?.channels ?? [];
  const defaultChannel = channels.findIndex((point) => !point.masked && point.flux !== null);
  const activeChannel = selected ?? Math.max(0, defaultChannel);
  const channel = channels[activeChannel];
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
  const imageLabel = image && (image.aggregation
    ? `D${image.detector} · ${image.min_wavelength_um.toFixed(3)}–${image.max_wavelength_um.toFixed(3)} µm · ${image.unit}`
    : `D${image.detector} · ${image.wavelength_um.toFixed(3)} µm · ${image.unit}`);

  return (
    <Panel title="Spectral analysis · 102 bands">
      <div className={`grid ${explorer ? "gap-4 sm:p-2" : "gap-2.5"}`}>
        {!spectrum.data && !spectrum.loading && (
          <button type="button" className={controlClass} onClick={() => setRequested((value) => value + 1)}>
            {requested ? "Retry spectrum" : "Load DR1 spectrum"}
          </button>
        )}
        {spectrum.loading && (
          <div className={explorer ? "rounded-sm border border-border-subtle bg-void/40 p-4" : undefined}>
            <Status>Opening the DR1 spectrum at this position. A tile’s first download can take a few minutes.</Status>
            {explorer && <div aria-hidden="true" className="mt-3 h-1 w-24 rounded bg-cyan/70 motion-safe:animate-pulse" />}
          </div>
        )}
        {spectrum.error && <Status error>{spectrum.error}</Status>}
        {spectrum.data && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
              <Status>{spectrum.data.available_channels}/102 available · multi-epoch surface brightness · {spectrum.data.unit}</Status>
              {spectrum.data.delivery && <Status>{spectrum.data.delivery === "archive_cube"
                ? "Official DR1 archive cube" : "Downloaded FITS fallback"}</Status>}
            </div>
            <SciencePlot points={channels.map((point) => ({ x: point.wavelength_um, y: point.flux }))}
              label="SPHEREx spectral surface brightness" xLabel="Wavelength (µm)" activeX={channel?.wavelength_um} />
            <div className="grid gap-1" aria-label="102 detector channels">
              {detectors.map((id) => (
                <div key={id} className="grid grid-cols-[2em_repeat(17,minmax(0,1fr))] items-center gap-0.5 sm:gap-1">
                  <span className="font-mono text-[10px] text-[#a5b8ca]">D{id}</span>
                  {channels.map((point, index) => point.detector === id && (
                    <button key={point.channel} type="button"
                      title={`D${id} · ${point.wavelength_um.toFixed(3)} µm${point.masked ? " · masked" : ""}`}
                      aria-label={`Channel ${index + 1}, ${point.wavelength_um.toFixed(3)} micrometers${point.masked ? ", masked" : ""}`}
                      aria-pressed={index === activeChannel && !combinedDetector}
                      onClick={() => { setSelected(index); setCombinedDetector(0); if (explorer) setShowBand(true); }}
                      className={`h-5 rounded-[2px] border outline-offset-1 hover:border-cyan-bright focus-visible:outline-2 focus-visible:outline-cyan-bright ${index === activeChannel && !combinedDetector
                        ? "border-white bg-cyan" : point.masked ? "border-[#25313e] bg-[#101820]" : "border-[#34485e] bg-[#355775]"}`} />
                  ))}
                </div>
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
                {detectors.map((id) => <option key={id} value={id}>D{id} · 17-channel mean</option>)}
              </select>
              <button type="button" className={controlClass} aria-pressed={showBand} onClick={() => setShowBand((value) => !value)}>
                {showBand ? "Hide image" : "Show image"}
              </button>
            </div>
            {band.loading && <Status>Loading spectral image…</Status>}
            {band.error && <Status error>{band.error}</Status>}
            {image && imageLabel && (
              <div className={explorer ? "mx-auto grid w-full max-w-[420px] gap-2" : "grid gap-2"}>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <label className="flex items-center gap-1 text-[11px] text-[#ec91c6]">
                    <input type="checkbox" checked={showFlags} onChange={(event) => setShowFlags(event.target.checked)} /> Highlight flagged pixels
                  </label>
                  {explorer && (
                    <label className="flex items-center gap-1 text-[11px] text-[#a5b8ca]">
                      <input type="checkbox" checked={pixelView} onChange={(event) => setPixelView(event.target.checked)} /> Show individual pixels
                    </label>
                  )}
                </div>
                <FitsImage pixels={image.image} grid={image.grid} range={imageRange(image.image)}
                  flags={showFlags ? [image.flags] : undefined}
                  smooth={explorer && !pixelView && !showFlags}
                  label={explorer ? `${imageLabel} · ${image.grid.width} × ${image.grid.height} pixel cutout` : imageLabel} />
                {image.aggregation && <Status>
                  Mean weighted by input pixel count. Center: {image.channel_count[center]?.[center] ?? 0}/{image.channels_combined} channels · {image.nhits[center]?.[center] ?? 0} input pixels.
                </Status>}
              </div>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}
