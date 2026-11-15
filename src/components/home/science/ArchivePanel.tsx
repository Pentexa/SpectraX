"use client";

import { useEffect, useRef, useState } from "react";
import { errorMessage } from "@/hooks/useScienceRequest";
import { scienceApi, type ArchiveObservation, type ArchivePair, type EpochPair, type ScienceTarget, type SkyField } from "@/lib/api/science";
import { Panel, controlClass, inputClass, Status } from "./Panel";

export function observationDate(mjd: number | null) {
  return mjd === null ? "Date unavailable" : new Date((mjd - 40587) * 86_400_000).toISOString().slice(0, 10);
}

export function ArchivePanel({ target, field, onPair, openExample }: {
  target: ScienceTarget | null;
  field: SkyField;
  onPair: (pair: EpochPair, observations: ArchivePair) => void;
  openExample: () => void;
}) {
  const [release, setRelease] = useState("both");
  const [wavelength, setWavelength] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [records, setRecords] = useState<ArchiveObservation[] | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"search" | "import" | null>(null);
  const revision = useRef(0);
  useEffect(() => () => { revision.current += 1; }, []);

  async function search() {
    const request = ++revision.current;
    setError(null);
    setChosen([]);
    setRecords(null);
    setBusy("search");
    try {
      const start = startDate ? Date.parse(startDate) / 86_400_000 + 40587 : undefined;
      const end = endDate ? Date.parse(endDate) / 86_400_000 + 40588 : undefined;
      const releases = release === "both" ? ["DR1", "QR3"] : [release];
      const results = await Promise.allSettled(releases.map((item) => scienceApi.observations(
        target?.id ?? null, field, item, wavelength ? Number(wavelength) : undefined, start, end,
      )));
      if (revision.current !== request) return;
      const available = results.filter((result) => result.status === "fulfilled");
      setRecords(available.length
        ? available.flatMap((result) => result.value.observations)
            .sort((a, b) => (a.observation_start_mjd ?? 0) - (b.observation_start_mjd ?? 0))
        : null);
      const unavailable = results.flatMap((result, index) => result.status === "rejected"
        ? [`${releases[index]} · ${errorMessage(result.reason)}`] : []);
      if (unavailable.length) setError(unavailable.join(" / "));
    } catch (err) {
      if (revision.current === request) setError(errorMessage(err));
    } finally {
      if (revision.current === request) setBusy(null);
    }
  }

  async function compare() {
    const selected = records?.filter((record) => chosen.includes(record.archive_id))
      .sort((a, b) => (a.observation_start_mjd ?? 0) - (b.observation_start_mjd ?? 0));
    if (selected?.length !== 2) return;
    const request = ++revision.current;
    setError(null);
    setBusy("import");
    try {
      const observations = [selected[0], selected[1]] as const;
      const epochs = await scienceApi.importPair(observations, field);
      if (revision.current === request) onPair(epochs, observations);
    } catch (err) {
      if (revision.current === request) setError(errorMessage(err));
    } finally {
      if (revision.current === request) setBusy(null);
    }
  }

  return (
    <Panel title="Observation archive">
      <form className="space-y-2" onSubmit={(event) => { event.preventDefault(); void search(); }}>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-[10px] text-text-muted">Release
            <select className={inputClass} value={release} onChange={(event) => setRelease(event.target.value)}>
              <option value="both">DR1 + QR3</option><option>DR1</option><option>QR3</option>
            </select>
          </label>
          <label className="grid gap-1 text-[10px] text-text-muted">Wavelength (µm)
            <input className={inputClass} type="number" min="0.75" max="5" step="any"
              placeholder={target?.recommended_wavelength_um.toFixed(2) ?? "Any"} value={wavelength}
              onChange={(event) => setWavelength(event.target.value)} />
          </label>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <label className="grid min-w-0 gap-1 text-[10px] text-text-muted">Start date
            <input type="date" className={inputClass} value={startDate} max={endDate || undefined} onChange={(event) => setStartDate(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-[10px] text-text-muted">End date
            <input type="date" className={inputClass} value={endDate} min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className={controlClass} disabled={busy !== null}>{busy === "search" ? "Searching IRSA…" : "Find observations"}</button>
          <button type="button" className={controlClass} onClick={openExample}>Open DR1 difference</button>
        </div>
      </form>
      {records && (
        <div className="mt-2 grid gap-2">
          {records.length === 0 ? <Status>No exposures for this search.</Status> : (
            <>
              <fieldset className="max-h-48 overflow-y-auto border border-border-subtle px-2 pb-1">
                <legend className="px-1 text-[10px] text-text-muted">Choose two epochs</legend>
                {records.map((record) => (
                  <label key={record.archive_id} className="flex items-start gap-2 border-b border-border-subtle py-1.5 text-[10px] text-[#b9c9d8] last:border-0">
                    <input type="checkbox" className="accent-[#6bb9e5]" checked={chosen.includes(record.archive_id)}
                      disabled={busy !== null || (chosen.length === 2 && !chosen.includes(record.archive_id))}
                      onChange={() => setChosen((values) => values.includes(record.archive_id)
                        ? values.filter((value) => value !== record.archive_id) : [...values, record.archive_id])} />
                    <span title={record.observation_id}>{observationDate(record.observation_start_mjd)} · {record.band}<br />
                      <span className="font-mono text-text-muted">{record.observation_id}</span></span>
                  </label>
                ))}
              </fieldset>
              <button type="button" className={controlClass} disabled={chosen.length !== 2 || busy !== null}
                onClick={() => void compare()}>{busy === "import" ? "Downloading real FITS…" : "Compare selected epochs"}</button>
            </>
          )}
        </div>
      )}
      {error && <div className="mt-2"><Status error>{error}</Status></div>}
    </Panel>
  );
}
