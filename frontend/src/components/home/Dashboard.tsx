"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { createAnimationClock } from "@/hooks/useAnimationClock";
import { useScienceRequest } from "@/hooks/useScienceRequest";
import { archiveCutoutWidth, MAX_TIMELINE_EPOCHS, scienceApi, type ArchiveCutout, type ComparisonMode, type EpochPair, type SkyField } from "@/lib/api/science";
import { useDashboardStore } from "@/store/dashboardStore";
import { StarList } from "./left/StarList";
import { AllSkyAtlas } from "./center/AllSkyAtlas";
import { ArchivePanel } from "./science/ArchivePanel";
import { ComparisonPanel } from "./science/ComparisonPanel";
import { FieldPanel } from "./science/FieldPanel";
import { controlClass, Panel, Status } from "./science/Panel";
import { ReferencePanel } from "./science/ReferencePanel";
import { SourcePanel } from "./science/SourcePanel";
import { ReleasePanel } from "./science/ReleasePanel";
import { SpectrumPanel } from "./science/SpectrumPanel";
import { TimelinePanel } from "./science/TimelinePanel";

const modes = new Set<ComparisonMode>(["side_by_side", "difference", "sum", "stack"]);
const isEpoch = (value: string | null): value is string => /^[A-Za-z0-9_.-]{1,80}$/.test(value ?? "");
const archiveId = /^ivo:\/\/irsa\.ipac\/spherex_(dr1|qr3)\?[A-Za-z0-9_]{1,50}\/D[1-6]$/;
const archiveKeys = "abcdefgh".slice(0, MAX_TIMELINE_EPOCHS).split("");

function readCutout(params: URLSearchParams, epoch: string): ArchiveCutout | null {
  const id = params.get(`archive_${epoch}`);
  const ra = params.get(`ra_${epoch}`);
  const dec = params.get(`dec_${epoch}`);
  if (!id || !archiveId.test(id) || !ra || !dec ||
    !(Number(ra) >= 0 && Number(ra) < 360 && Math.abs(Number(dec)) <= 90)) return null;
  const local = params.get(`local_${epoch}`);
  return { archive_id: id, predicted_position: { ra: Number(ra), dec: Number(dec) },
    local_epoch: isEpoch(local) ? local : undefined };
}

export function Dashboard({ embedded = false }: { embedded?: boolean }) {
  const clock = useMemo(() => createAnimationClock(), []);
  const targets = useDashboardStore((state) => state.targets);
  const source = useDashboardStore((state) => state.source);
  const loadError = useDashboardStore((state) => state.loadError);
  const loadData = useDashboardStore((state) => state.loadData);
  const selectTarget = useDashboardStore((state) => state.selectStar);
  const selectedId = useDashboardStore((state) => state.selectedStarId);
  const [coordinates, setCoordinates] = useState<Pick<SkyField, "ra" | "dec"> | null>(null);
  const [fov, setFov] = useState(0.05);
  const [mode, setMode] = useState<ComparisonMode>("side_by_side");
  const [fixedPair, setFixedPair] = useState<EpochPair | null>(null);
  const [archiveSelection, setArchiveSelection] = useState<{
    localOnly?: boolean;
    observations: ArchiveCutout[];
    original?: { fov: number; epochs: string[] };
  } | null>(null);
  const [importAttempt, setImportAttempt] = useState(0);
  const [showAtlas, setShowAtlas] = useState(true);
  const [showTimeline, setShowTimeline] = useState(false);
  const [showGaia, setShowGaia] = useState(false);
  const [showWise, setShowWise] = useState(false);

  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    const targetId = params.get("target");
    if (targetId) selectTarget(targetId);
    const ra = params.get("ra"), dec = params.get("dec");
    if (!targetId && ra && dec && Number(ra) >= 0 && Number(ra) < 360 && Math.abs(Number(dec)) <= 90) {
      setCoordinates({ ra: Number(ra), dec: Number(dec) });
    }
    const width = Number(params.get("fov"));
    if (width >= 0.01 && width <= 0.2) setFov(width);
    const requestedMode = params.get("mode") as ComparisonMode | null;
    if (requestedMode && modes.has(requestedMode)) setMode(requestedMode);
    const first = params.get("epoch_a"), second = params.get("epoch_b");
    const cutouts = archiveKeys.map((key) => readCutout(params, key)).filter((value) => value !== null);
    const view = params.get("view");
    const hasArchiveSelection = cutouts.length >= 2
      && new Set(cutouts.map((item) => item.archive_id)).size === cutouts.length;
    const hasFixedPair = isEpoch(first) && isEpoch(second) && first !== second;
    if (hasArchiveSelection) {
      setArchiveSelection({ observations: cutouts });
    } else if (hasFixedPair) {
      setFixedPair([first, second]);
    }
    setShowGaia(params.get("gaia") === "1");
    setShowWise(params.get("wise") === "1");
    if (view === "atlas" || view === "images" || view === "timeline") {
      setShowAtlas(view === "atlas");
      setShowTimeline(view === "timeline");
    } else {
      setShowAtlas(!hasArchiveSelection && !hasFixedPair && !(requestedMode && modes.has(requestedMode)));
      setShowTimeline(hasArchiveSelection && cutouts.length > 2);
    }
    void loadData();
  }, [loadData, selectTarget]);

  const activeTarget = coordinates ? null : targets.find((target) => target.id === selectedId) ?? null;
  const ra = coordinates?.ra ?? activeTarget?.ra ?? 269.45;
  const dec = coordinates?.dec ?? activeTarget?.dec ?? 4.7;
  const field = useMemo(() => ({ ra, dec, fov }), [ra, dec, fov]);
  const targetId = activeTarget?.id ?? null;
  const clearSelection = useCallback(() => {
    setFixedPair(null);
    setArchiveSelection(null);
    setMode("side_by_side");
    setShowTimeline(false);
  }, []);
  const handleTarget = useCallback((id: string) => {
    selectTarget(id);
    setCoordinates(null);
    clearSelection();
  }, [clearSelection, selectTarget]);

  const loadArchive = useCallback((signal: AbortSignal) => scienceApi.importExposures(archiveSelection!.observations, field, signal), [archiveSelection, field]);
  const needsImport = archiveSelection && (!archiveSelection.original || archiveCutoutWidth(fov) > archiveSelection.original.fov);
  const imported = useScienceRequest(source === "api" && needsImport ? loadArchive : null, importAttempt);
  const selected = archiveSelection ? needsImport ? imported.data : archiveSelection.original?.epochs ?? null : fixedPair;
  const pair = useMemo<EpochPair | null>(() => selected && selected.length >= 2
    ? [selected[0], selected[selected.length - 1]] : null, [selected]);
  const hasBenchmark = activeTarget?.benchmark_archive_available ?? activeTarget?.benchmark_available;
  const preferArchive = !archiveSelection?.localOnly;
  const loadBenchmark = useCallback((signal: AbortSignal) => scienceApi.benchmark(targetId!, fov, signal), [targetId, fov]);
  const benchmark = useScienceRequest(hasBenchmark && !showAtlas && !fixedPair && !archiveSelection ? loadBenchmark : null);
  const epochs = useMemo<EpochPair | null>(() => pair ?? (benchmark.data
    ? [benchmark.data.comparison.epochs.a.epoch, benchmark.data.comparison.epochs.b.epoch] : null), [benchmark.data, pair]);
  const timelineEpochs = selected && selected.length > 2 ? selected
    : !fixedPair && !archiveSelection ? activeTarget?.archive_timeline_epochs ?? activeTarget?.timeline_epochs : undefined;
  const timelineAvailable = Boolean(timelineEpochs && timelineEpochs.length >= 3);
  const showTimelinePanel = showTimeline && (timelineAvailable || Boolean(archiveSelection && archiveSelection.observations.length > 2));
  const loadTimeline = useCallback((signal: AbortSignal) => scienceApi.timeline(field, timelineEpochs!, signal, preferArchive),
    [field, timelineEpochs, preferArchive]);
  const timeline = useScienceRequest(showTimelinePanel && !showAtlas && timelineAvailable ? loadTimeline : null);
  const loadComparison = useCallback((signal: AbortSignal) => scienceApi.compare(field, epochs!, mode, signal, preferArchive),
    [field, epochs, mode, preferArchive]);
  const comparison = useScienceRequest(epochs && !showAtlas && !showTimelinePanel && (pair || mode !== "side_by_side") ? loadComparison : null);
  const loadAstrometry = useCallback((signal: AbortSignal) => scienceApi.astrometry(targetId, field, pair!, signal), [targetId, field, pair]);
  const astrometry = useScienceRequest(pair && !showTimelinePanel ? loadAstrometry : null);

  const loadGaia = useCallback((signal: AbortSignal) => scienceApi.overlay("gaia", field, signal), [field]);
  const loadWise = useCallback((signal: AbortSignal) => scienceApi.overlay("wise", field, signal), [field]);
  const gaia = useScienceRequest(showGaia ? loadGaia : null);
  const wise = useScienceRequest(showWise ? loadWise : null);
  const marks = useMemo(() => [
    ...(gaia.data?.sources ?? []).map((point) => ({ ...point, id: `gaia-${point.id}`, color: "#70e9ad", label: `Gaia DR3 ${point.id}` })),
    ...(wise.data?.sources ?? []).map((point) => ({ ...point, id: `wise-${point.id}`, color: "#ffc982", label: `AllWISE ${point.id}` })),
  ], [gaia.data, wise.data]);

  function share(embed: boolean) {
    const url = new URL(embed ? "/embed" : "/atlas", window.location.origin);
    if (targetId) url.searchParams.set("target", targetId);
    url.searchParams.set("ra", field.ra.toFixed(7));
    url.searchParams.set("dec", field.dec.toFixed(7));
    url.searchParams.set("fov", String(fov));
    url.searchParams.set("mode", mode);
    if (archiveSelection) {
      archiveSelection.observations.forEach((observation, index) => {
        const key = archiveKeys[index];
        const position = observation.predicted_position ?? field;
        url.searchParams.set(`archive_${key}`, observation.archive_id);
        url.searchParams.set(`ra_${key}`, String(position.ra));
        url.searchParams.set(`dec_${key}`, String(position.dec));
        if (observation.local_epoch) url.searchParams.set(`local_${key}`, observation.local_epoch);
      });
    } else if (fixedPair) {
      url.searchParams.set("epoch_a", fixedPair[0]);
      url.searchParams.set("epoch_b", fixedPair[1]);
    }
    if (showGaia) url.searchParams.set("gaia", "1");
    if (showWise) url.searchParams.set("wise", "1");
    url.searchParams.set("view", showAtlas ? "atlas" : showTimelinePanel ? "timeline" : "images");
    const src = url.toString();
    return embed
      ? `<iframe src="${src.replaceAll("&", "&amp;")}" title="SpectraX SPHEREx explorer" width="100%" height="760" loading="lazy"></iframe>`
      : src;
  }

  const displayed = comparison.data ?? benchmark.data?.comparison ?? null;
  const measurement = astrometry.data ?? benchmark.data?.astrometry ?? null;

  return (
    <div className="flex min-h-screen flex-col" style={{ background: "radial-gradient(ellipse at 50% 0%, rgba(30,52,74,0.22) 0%, transparent 65%), linear-gradient(#0b1017, #090d12)" }}>
      {!embedded && <SiteHeader activeSection="map" dataSource={source} onOpenAtlas={() => setShowAtlas(true)}
        spectralHref={`/spectral?ra=${ra}&dec=${dec}`} />}
      {source !== "api" ? (
        <main className="mx-auto w-full max-w-md p-6">
          <Panel title="SPHEREx data">
            <Status error={source === "offline"}>{source === "offline" ? loadError ?? "Backend unavailable." : "Loading the target catalog…"}</Status>
            {source === "offline" && <button type="button" className={`mt-2 ${controlClass}`} onClick={() => void loadData()}>Retry connection</button>}
          </Panel>
        </main>
      ) : (
        <main className={`grid flex-1 items-start gap-2.5 px-3 pb-2 pt-2.5 ${embedded
          ? "grid-cols-1 md:grid-cols-[230px_minmax(0,1fr)]"
          : "grid-cols-1 md:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[280px_minmax(0,1fr)_310px]"}`}>
          <aside className="grid min-w-0 gap-2">
            <StarList onSelect={handleTarget} />
            <FieldPanel field={field} onFov={setFov} onShare={share} onCoordinates={(value) => {
              setCoordinates(value);
              clearSelection();
            }} />
            {(!embedded || (!pair && !hasBenchmark)) && <ArchivePanel key={`${targetId ?? "field"}:${ra}:${dec}:${fov}`} field={field} target={activeTarget}
              openExample={() => {
                setCoordinates({ ra: 269.45, dec: 4.7 });
                setFov(0.04);
                setArchiveSelection(null);
                setFixedPair(["dr1-2025-10-01-d1", "dr1-2026-03-11-d1"]);
                setMode("difference");
                setShowAtlas(false);
                setShowTimeline(false);
              }}
              onSelection={(epochs, observations, localOnly) => {
                setFixedPair(null);
                setArchiveSelection({ observations, localOnly, original: { fov: archiveCutoutWidth(fov), epochs } });
                setMode("side_by_side");
                setShowAtlas(false);
                setShowTimeline(epochs.length > 2);
              }} />}
          </aside>
          <div className="order-first grid min-w-0 gap-2 md:order-none">
            <Panel title={activeTarget?.name ?? "Custom sky field"} actions={
              <div className="flex gap-1">
                <button type="button" aria-pressed={!showAtlas && !showTimelinePanel} className={controlClass}
                  onClick={() => { setShowAtlas(false); setShowTimeline(false); }}>Images</button>
                {timelineAvailable && <button type="button" aria-pressed={!showAtlas && showTimelinePanel} className={controlClass}
                  onClick={() => { setShowAtlas(false); setShowTimeline(true); }}>Timeline</button>}
                <button type="button" aria-pressed={showAtlas} className={controlClass} onClick={() => setShowAtlas(true)}>Sky atlas</button>
              </div>
            }>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 font-mono text-[10px] text-[#a5b8ca]">
                <span>{field.ra.toFixed(5)}° RA · {field.dec.toFixed(5)}° Dec</span>
                <label className="flex items-center gap-1 text-[#70e9ad]">
                  <input type="checkbox" checked={showGaia} onChange={(event) => setShowGaia(event.target.checked)} /> Gaia DR3
                </label>
                <label className="flex items-center gap-1 text-[#ffc982]">
                  <input type="checkbox" checked={showWise} onChange={(event) => setShowWise(event.target.checked)} /> AllWISE
                </label>
                {(fixedPair || archiveSelection) && hasBenchmark && <button type="button" className={controlClass} onClick={clearSelection}>Restore benchmark pair</button>}
              </div>
              {(gaia.loading || wise.loading) && <Status>Loading catalog overlays…</Status>}
              {(gaia.error || wise.error) && <Status error>{gaia.error ?? wise.error}</Status>}
              {gaia.data && <Status>{gaia.data.sources.length} Gaia reference positions · epoch {gaia.data.reference_epoch_jyear ?? "unknown"}</Status>}
              {wise.data && <Status>{wise.data.sources.length} AllWISE reference positions</Status>}
              {imported.loading && <Status>Fetching the selected FITS cutouts from IRSA…</Status>}
              {imported.error && <div className="flex flex-wrap items-center gap-2">
                <Status error>{imported.error}</Status>
                <button type="button" className={controlClass} onClick={() => setImportAttempt((value) => value + 1)}>Retry cutouts</button>
              </div>}
            </Panel>
            {showAtlas ? <AllSkyAtlas clock={clock} onTarget={handleTarget} field={field} catalogMarks={marks} />
              : showTimelinePanel ? <TimelinePanel key={timelineEpochs?.join(":") ?? "loading"} timeline={timeline.data}
                  loading={imported.loading || timeline.loading} error={timeline.error ?? imported.error} marks={marks} />
              : <ComparisonPanel key={targetId ?? `${ra}:${dec}`} comparison={displayed} astrometry={measurement}
                  loading={benchmark.loading || comparison.loading || imported.loading}
                  error={comparison.error ?? benchmark.error ?? astrometry.error} mode={mode} onMode={setMode} marks={marks} />}
          </div>
          {!embedded && <aside className="grid min-w-0 gap-2 md:col-span-2 xl:col-span-1">
            <SpectrumPanel key={`${ra}:${dec}`} field={field} />
            {epochs && <SourcePanel key={epochs.join(":")} epochs={epochs} targetId={targetId} field={field}
              autoMeasure={Boolean(benchmark.data && activeTarget?.kind === "variability")} />}
            <ReleasePanel />
            {(targetId === "r-draconis" || targetId === "rw-aurigae") && <ReferencePanel key={targetId} targetId={targetId} />}
            {activeTarget && (
              <Panel title="Catalog astrometry">
                <Status>Proper motion {Math.hypot(activeTarget.pm_ra_cosdec_mas_yr, activeTarget.pm_dec_mas_yr).toFixed(1)} mas/yr · parallax {activeTarget.parallax_mas.toFixed(1)} mas</Status>
                {activeTarget.note && <p className="mt-1 text-[10px] leading-relaxed text-text-muted">{activeTarget.note}</p>}
                <a className="mt-1 inline-block text-[11px] text-cyan-bright underline" href={activeTarget.source} target="_blank" rel="noreferrer">SIMBAD source</a>
              </Panel>
            )}
          </aside>}
        </main>
      )}
      {!embedded && <SiteFooter />}
    </div>
  );
}
