"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useAnimationClock, type AnimationClock } from "@/hooks/useAnimationClock";
import type { SkyField } from "@/lib/api/science";
import type { SkyMark } from "../science/FitsImage";
import { parseDecDMS, parseRAhms } from "@/lib/astronomy/coords";
import { useDashboardStore } from "@/store/dashboardStore";
import type { AladinInstance, AladinModule } from "@/types/aladin";

const ALADIN_ESM_LOCAL = "/vendor/aladin/aladin.esm.js";
const DSS_ALL_SKY = "/hips/dss2/Norder3/Allsky.jpg";

async function loadAladinRuntime(): Promise<AladinModule> {
  // The local bundle avoids depending on an external CDN at startup.
  const mod = await import(/* webpackIgnore: true */ ALADIN_ESM_LOCAL);
  const aladin = mod.default as AladinModule;
  await aladin.init;
  return aladin;
}

async function verifySurvey(signal: AbortSignal) {
  const preview = await fetch(DSS_ALL_SKY, { signal });
  if (!preview.ok) throw new Error("The DSS2 sky survey is temporarily unavailable.");
  const image = await createImageBitmap(await preview.blob());
  image.close();
}

function createViewer(
  aladin: AladinModule, element: HTMLElement, field: SkyField, signal: AbortSignal,
): Promise<AladinInstance> {
  return new Promise((resolve, reject) => {
    let viewer: AladinInstance;
    const timeout = window.setTimeout(() => finish(new Error("Aladin timed out loading the DSS2 layer.")), 12_000);
    const abort = () => finish(signal.reason);
    function finish(error?: unknown) {
      window.clearTimeout(timeout);
      signal.removeEventListener("abort", abort);
      if (error) reject(error);
      else resolve(viewer);
    }
    signal.addEventListener("abort", abort, { once: true });
    try {
      // This metadata matches the DSS2 color HiPS. The absolute same-origin
      // URL ensures Aladin uses our tile route, including on embedded pages.
      const layer = aladin.HiPS(new URL("/hips/dss2", window.location.origin).href, {
        name: "DSS2 color",
        cooFrame: "ICRS",
        maxOrder: 9,
        tileSize: 512,
        imgFormat: "jpeg",
        successCallback: () => finish(),
        errorCallback: (error: unknown) => finish(error || new Error("The DSS2 layer could not be opened.")),
      });
      viewer = aladin.aladin(element, {
        survey: layer, target: `${field.ra.toFixed(9)} ${field.dec.toFixed(9)}`, fov: field.fov,
        projection: "SIN", mode: "dark", log: false,
        showCooGrid: false, showGotoControl: false, showLayersControl: false, showShareControl: false,
        showFullscreenControl: false, showFrame: true,
      });
    } catch (error) {
      finish(error);
    }
  });
}

interface SkyMarker {
  id: string;
  ra: number;
  dec: number;
  el: HTMLDivElement;
}

const MARKER_SELECT_DISTANCE_PX = 80;

/**
 * The target and catalog markers are projected on the DSS2 viewer with
 * Aladin's world-to-pixel transform.
 */
export function AllSkyAtlas({ clock, onTarget, field, catalogMarks }: {
  clock: AnimationClock;
  onTarget?: (id: string) => void;
  field: SkyField;
  catalogMarks: SkyMark[];
}) {
  const aladinElRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const imRef = useRef<AladinInstance | null>(null);
  const markersRef = useRef<SkyMarker[]>([]);

  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [initError, setInitError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const latestField = useRef(field);
  latestField.current = field;

  const stars = useDashboardStore((s) => s.data?.stars ?? []);
  const selectedStarId = useDashboardStore((s) => s.selectedStarId);
  const storeSelect = useDashboardStore((s) => s.selectStar);
  const selectStar = onTarget ?? storeSelect;

  /** Resolve each catalog star to J2000 degrees once. */
  const coords = useMemo(() => {
    const map = new Map<string, { ra: number; dec: number }>();
    for (const star of stars) {
      const ra = parseRAhms(star.ra);
      const dec = parseDecDMS(star.dec);
      if (Number.isFinite(ra) && Number.isFinite(dec)) {
        map.set(star.id, { ra, dec });
      }
    }
    return map;
  }, [stars]);

  useEffect(() => {
    const host = aladinElRef.current;
    if (!host) return;
    const controller = new AbortController();
    const { signal } = controller;
    // Each startup owns its own element, including Strict Mode retries.
    const element = document.createElement("div");
    element.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
    host.appendChild(element);

    void (async () => {
      try {
        const aladin = await loadAladinRuntime();
        if (signal.aborted) return;
        await verifySurvey(AbortSignal.any([signal, AbortSignal.timeout(14_000)]));
        if (signal.aborted) return;
        imRef.current = await createViewer(aladin, element, latestField.current, signal);
        if (!signal.aborted) setStatus("ready");
      } catch (error) {
        if (signal.aborted) return;
        element.remove();
        setInitError(error instanceof Error ? error.message : String(error));
        setStatus("error");
      }
    })();

    return () => {
      controller.abort();
      imRef.current = null;
      element.remove();
    };
  }, [retryToken]);

  useEffect(() => {
    if (status !== "ready") return;
    const viewer = imRef.current;
    viewer?.setProjection("SIN");
    viewer?.gotoRaDec(field.ra, field.dec);
    viewer?.setFoV(field.fov);
  }, [status, field]);

  /* ---- Marker DOM nodes ---- */
  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;

    for (const marker of markersRef.current) marker.el.remove();
    markersRef.current = [];

    const nodes: SkyMarker[] = [];
    for (const star of stars) {
      const coord = coords.get(star.id);
      if (!coord) continue;

      const el = document.createElement("div");
      el.dataset.starId = star.id;
      el.className =
        "pointer-events-none absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full " +
        "border border-cyan-bright/80 bg-cyan-bright/35 " +
        "shadow-[0_0_6px_var(--color-cyan-bright)] transition-opacity duration-100";
      overlay.appendChild(el);
      nodes.push({ id: star.id, ra: coord.ra, dec: coord.dec, el });
    }
    for (const mark of catalogMarks) {
      const el = document.createElement("div");
      el.className = "pointer-events-none absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full border";
      el.style.borderColor = mark.color;
      el.title = mark.label;
      overlay.appendChild(el);
      nodes.push({ id: mark.id, ra: mark.ra, dec: mark.dec, el });
    }
    markersRef.current = nodes;

    return () => {
      for (const marker of nodes) marker.el.remove();
    };
  }, [stars, coords, catalogMarks]);

  /* ---- Selected / diff-mode styling ---- */
  useEffect(() => {
    for (const marker of markersRef.current) {
      const isSelected = marker.id === selectedStarId;
      marker.el.classList.toggle("!h-4", isSelected);
      marker.el.classList.toggle("!w-4", isSelected);
      marker.el.classList.toggle("!bg-cyan-bright/60", isSelected);
      marker.el.classList.toggle("!border-white/90", isSelected);
    }
  }, [selectedStarId, catalogMarks]);

  /* ---- Per-frame projection: catalog markers ---- */
  useAnimationClock(clock, () => {
    const im = imRef.current;
    const overlay = overlayRef.current;
    if (!im || !overlay) return;

    const vw = overlay.clientWidth;
    const vh = overlay.clientHeight;

    for (const marker of markersRef.current) {
      let visible = false;
      try {
        const point = im.world2pix(marker.ra, marker.dec);
        if (point) {
          const x = Number(point[0]);
          const y = Number(point[1]);
          if (
            Number.isFinite(x) &&
            Number.isFinite(y) &&
            x >= -24 &&
            x <= vw + 24 &&
            y >= -24 &&
            y <= vh + 24
          ) {
            marker.el.style.transform = `translate(${x}px, ${y}px)`;
            marker.el.style.opacity = "1";
            visible = true;
          }
        }
      } catch {
        // projection not ready yet
      }
      if (!visible) marker.el.style.opacity = "0";
    }
  });

  /* ---- Click-to-select using last projected positions ---- */
  const handleAtlasClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    let best: { id: string; distance: number } | null = null;
    for (const marker of markersRef.current) {
      if (!marker.el.dataset.starId || marker.el.style.opacity !== "1") continue;
      const markerRect = marker.el.getBoundingClientRect();
      const mx = markerRect.left - rect.left + markerRect.width / 2;
      const my = markerRect.top - rect.top + markerRect.height / 2;
      const distance = Math.hypot(x - mx, y - my);
      if (distance < MARKER_SELECT_DISTANCE_PX && (!best || distance < best.distance)) {
        best = { id: marker.id, distance };
      }
    }
    if (best) selectStar(best.id);
  };

  function recenter(allSky: boolean) {
    const viewer = imRef.current;
    viewer?.setProjection(allSky ? "MOL" : "SIN");
    viewer?.gotoRaDec(field.ra, field.dec);
    viewer?.setFoV(allSky ? 360 : field.fov);
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
      <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
        <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
          ALADIN LITE — ALL-SKY ATLAS
        </span>
        <span className="font-mono text-[9px] tracking-wider text-text-muted">
          {status === "ready" ? "DSS2 COLOR" : status.toUpperCase()}
        </span>
      </div>

      <div
        className="relative flex min-h-[410px] flex-1 items-center justify-center overflow-hidden bg-[#0a0f16]"
        onClick={handleAtlasClick}
      >
        <div
          ref={aladinElRef}
          id="aladin-viewport"
          className="absolute inset-0"
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
        />

        {/* Overlay: catalog markers */}
        <div
          ref={overlayRef}
          className="pointer-events-none absolute inset-0 z-[3]"
        />

        {/* Loading / error state */}
        {status === "loading" && (
          <div className="absolute inset-0 z-[2] flex flex-col items-center justify-center gap-3 text-[#94a5b8]">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan border-t-transparent" />
            <span className="text-[11px] tracking-[0.08em]">Loading Aladin Lite…</span>
          </div>
        )}
        {status === "error" && (
          <div className="absolute inset-0 z-[2] flex flex-col items-center justify-center gap-2 px-6 text-center">
            <span className="text-[11px] font-medium tracking-[0.08em] text-[#e8a2a2]">
              All-sky atlas unavailable
            </span>
            <span className="max-w-[280px] text-[10px] text-text-muted">{initError}</span>
            <button
              className="mt-1 cursor-pointer rounded-[3px] border border-[#364e66] bg-[rgba(19,28,38,0.9)] px-3 py-1 text-[10px] tracking-[0.08em] text-[#c7d6e6] transition-colors hover:border-cyan-bright hover:text-cyan-bright"
              onClick={(e) => {
                e.stopPropagation();
                setStatus("loading");
                setInitError(null);
                setRetryToken((token) => token + 1);
              }}
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border-subtle bg-[#0e141c] px-3.5 py-2.5 text-[11px] text-[#8597aa]">
        <p>DSS background via Aladin Lite. Drag to pan, scroll to zoom.</p>
        <div className="flex gap-2">
          <button type="button" className="rounded border border-[#364e66] px-2 py-1 disabled:opacity-50"
            disabled={status !== "ready"} onClick={() => recenter(false)}>Center target</button>
          <button type="button" className="rounded border border-[#364e66] px-2 py-1 disabled:opacity-50"
            disabled={status !== "ready"} onClick={() => recenter(true)}>All sky</button>
        </div>
      </div>
    </section>
  );
}
