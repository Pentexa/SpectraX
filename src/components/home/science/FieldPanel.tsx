"use client";

import { useState } from "react";
import type { SkyField } from "@/lib/api/science";
import { controlClass, inputClass, Panel, Status } from "./Panel";

export function FieldPanel({ field, onCoordinates, onFov, onShare }: {
  field: SkyField;
  onCoordinates: (coordinates: Pick<SkyField, "ra" | "dec">) => void;
  onFov: (fov: number) => void;
  onShare: (embed: boolean) => string;
}) {
  const [message, setMessage] = useState("");
  const [shareText, setShareText] = useState("");
  const widths = [...new Set([0.02, 0.04, 0.05, 0.1, 0.2, field.fov])].sort((a, b) => a - b);
  async function share(embed: boolean) {
    const value = onShare(embed);
    setShareText(value);
    try {
      await navigator.clipboard.writeText(value);
      setMessage(embed ? "Embed code copied." : "Share link copied.");
    } catch {
      setMessage("Select and copy the text below.");
    }
  }
  return (
    <Panel title="Sky coordinates">
      <form className="grid gap-2" key={`${field.ra}:${field.dec}`} onSubmit={(event) => {
        event.preventDefault();
        const values = new FormData(event.currentTarget);
        onCoordinates({ ra: Number(values.get("ra")), dec: Number(values.get("dec")) });
      }}>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-[10px] text-text-muted">RA (°)
            <input name="ra" required type="number" className={inputClass} min="0" max="359.99999999" step="any" defaultValue={field.ra.toFixed(6)} />
          </label>
          <label className="grid gap-1 text-[10px] text-text-muted">Dec (°)
            <input name="dec" required type="number" className={inputClass} min="-90" max="90" step="any" defaultValue={field.dec.toFixed(6)} />
          </label>
        </div>
        <div className="flex items-end gap-2">
          <label className="grid flex-1 gap-1 text-[10px] text-text-muted">Field of view
            <select className={inputClass} value={field.fov} onChange={(event) => onFov(Number(event.target.value))}>
              {widths.map((fov) => <option key={fov} value={fov}>{fov.toFixed(3)}°</option>)}
            </select>
          </label>
          <button className={controlClass}>Go to coordinates</button>
        </div>
      </form>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <button type="button" className={controlClass} onClick={() => void share(false)}>Copy link</button>
        <button type="button" className={controlClass} onClick={() => void share(true)}>Copy embed</button>
      </div>
      {message && <div className="mt-2"><Status>{message}</Status></div>}
      {shareText && <textarea aria-label="Shareable link or embed code" className={`mt-1 w-full break-all ${inputClass}`}
        readOnly rows={2} value={shareText} onFocus={(event) => event.currentTarget.select()} />}
    </Panel>
  );
}
