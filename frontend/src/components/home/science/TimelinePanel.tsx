"use client";

import { useEffect, useMemo, useState } from "react";
import { archiveDeliveryLabel, type Timeline } from "@/lib/api/science";
import { FitsImage, imageRange, type SkyMark } from "./FitsImage";
import { controlClass, Panel, Status } from "./Panel";

export function TimelinePanel({ timeline, loading, error, marks }: {
  timeline: Timeline | null;
  loading: boolean;
  error: string | null;
  marks: SkyMark[];
}) {
  const [playing, setPlaying] = useState(false);
  const [index, setIndex] = useState(0);
  const [showFlags, setShowFlags] = useState(false);
  const count = timeline?.frames.length ?? 0;
  const frame = timeline?.frames[Math.min(index, count - 1)];
  const delivery = frame && timeline?.delivery?.[frame.epoch];
  const range = useMemo(() => imageRange(...(timeline?.frames.map((item) => item.pixels) ?? [])), [timeline]);

  useEffect(() => {
    if (!playing || count < 2) return;
    const timer = window.setInterval(() => setIndex((value) => (value + 1) % count), 850);
    return () => window.clearInterval(timer);
  }, [count, playing]);

  function seek(value: number) {
    setPlaying(false);
    setIndex((value + count) % count);
  }

  return (
    <Panel title="Observation timeline">
      {loading && <Status>Aligning observation frames…</Status>}
      {error && <Status error>{error}</Status>}
      {timeline && frame && (
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className={controlClass} onClick={() => seek(index - 1)}>Previous</button>
            <button type="button" className={controlClass} aria-pressed={playing}
              onClick={() => setPlaying((value) => !value)}>{playing ? "Pause timeline" : "Play timeline"}</button>
            <button type="button" className={controlClass} onClick={() => seek(index + 1)}>Next</button>
            <span className="font-mono text-[10px] text-[#a5b8ca]">{index + 1}/{count} · {timeline.unit}</span>
          </div>
          <input type="range" aria-label="Timeline frame" min={1} max={count} value={index + 1}
            className="accent-[#6bb9e5]" onChange={(event) => seek(Number(event.target.value) - 1)} />
          {!timeline.matching_bandpasses && <Status>Some frames use different wavelengths or calibrations. Compare position across the series.</Status>}
          {delivery && <Status>{archiveDeliveryLabel[delivery]}</Status>}
          {frame.coverage < 0.8 && <Status>{Math.round(frame.coverage * 100)}% usable coverage in this frame.</Status>}
          {frame.flags && (
            <label className="flex items-center gap-1 text-[10px] text-[#ec91c6]">
              <input type="checkbox" checked={showFlags} onChange={(event) => setShowFlags(event.target.checked)} />
              Highlight flagged pixels
            </label>
          )}
          <div className="mx-auto w-full max-w-md">
            <FitsImage pixels={frame.pixels} grid={timeline.grid} range={range} marks={marks}
              flags={showFlags ? [frame.flags] : undefined}
              label={`${new Date((frame.mjd - 40587) * 86_400_000).toISOString().slice(0, 16).replace("T", " ")} UTC · ${frame.release} D${frame.detector ?? "?"}${frame.wavelength_um === null ? "" : ` · ${frame.wavelength_um.toFixed(3)} µm`}`} />
          </div>
        </div>
      )}
    </Panel>
  );
}
