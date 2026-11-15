"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useAnimationClock, type AnimationClock } from "@/hooks/useAnimationClock";
import type { SkyField } from "@/lib/api/science";
import type { SkyMark } from "../science/FitsImage";
import { parseDecDMS, parseRAhms } from "@/lib/astronomy/coords";
import { useDashboardStore } from "@/store/dashboardStore";
import type { AladinInstance } from "@/types/aladin";

/**
 * Aladin Lite runtimes, tried in order. All are ESM builds loaded at runtime:
 *
 * 1. Vendored copy — same-origin, pinned to the app version, and the one
 *    place where vendor fixes are tracked (e.g. telemetry endpoints CDS
 *    retired in Nov 2026).
 * 2. Bundled npm package — same version, fallback if /vendor fails.
 * 3. Official CDN copy on jsDelivr — last resort.
 *
 * v3 injects its own stylesheet, so no external CSS is loaded.
 */
const ALADIN_ESM_LOCAL = "/vendor/aladin/aladin.esm.js";
const ALADIN_ESM_CDN =
  "https://cdn.jsdelivr.net/npm/aladin-lite@3.9.2-beta/dist/aladin.js";

/**
 * HiPS tile sources, tried in order.
 *
 * CDS decommissioned its legacy alasky/alaskybis DSS hosting in Nov 2026
 * (see https://cds.unistra.fr/hips_available_20261109.html), so the survey
 * now streams from official mirrors listed there. Both mirrors serve the
 * `Norder{k}/Dir{d}/Npix{n}.jpg` layout that Aladin Lite v3 expects and
 * ship `Access-Control-Allow-Origin: *`.
 */
const SURVEY_URLS = [
  "https://skies.esac.esa.int/DSSColor", // ESA ESAC
  "https://hips.china-vo.org/m/CDS_P_DSS2_color", // China-VO
] as const;

/** Runtime options are identical for every survey; only the tile source moves. */
const aladinInitOptions = (survey: string) => ({
  fov: 70,
  projection: "MOL", // Mollweide all-sky view
  // Absolute HiPS URL — required with the local runtime, which has no
  // CDN base URL to resolve relative survey ids against.
  survey,
  showCooGrid: false,
  showGotoControl: false,
  showLayersControl: false,
  showShareControl: false,
  showFullscreenControl: false,
  showFrame: true,
});

/** Max CDN script load attempts before giving up. */
const CDN_MAX_ATTEMPTS = 2;
const CDN_RETRY_DELAY_MS = 800;

type AladinModule = NonNullable<Window["A"]>;

/**
 * Creates the Aladin viewer from whichever runtime flavor was loaded.
 *
 * The factory may be synchronous or async — the bundled v3 build performs
 * network fetches while creating the view and can reject with
 * `TypeError: Failed to fetch` when the survey server is unreachable.
 * Awaiting the result turns that into a normal, catchable error instead of
 * an unhandled promise rejection.
 */
async function createAladinViewer(
  module: AladinModule,
  target: HTMLElement,
  survey: string,
): Promise<AladinInstance> {
  const factory = module.aladin ?? window.A?.aladin;
  if (typeof factory !== "function") {
    throw new Error(
      "Aladin runtime is loaded but exposes no `aladin` factory " +
        "(unexpected module shape).",
    );
  }

  let instance: AladinInstance;
  try {
    instance = await factory(target, aladinInitOptions(survey));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (/failed to fetch|networkerror|load failed|fetch failed/i.test(message)) {
      throw new Error(
        `Could not stream sky tiles from ${new URL(survey).host}.`,
      );
    }
    throw error;
  }

  if (!instance || typeof instance.world2pix !== "function") {
    throw new Error(
      "Aladin viewer was created but is missing its projection API.",
    );
  }
  return instance;
}

/**
 * Loads the Aladin Lite runtime.
 *
 * 1. Vendored ESM copy (same-origin, carries our vendor fixes).
 * 2. Bundled npm package.
 * 3. Official CDN ESM as a last resort (with retries).
 *
 * Every source is validated for the expected module shape; the first one
 * that exposes the `init` promise wins.
 */
async function loadAladinRuntime(): Promise<AladinModule> {
  const asAladinModule = (maybe: unknown): AladinModule | null => {
    const candidate = maybe as Partial<AladinModule> | undefined;
    if (candidate && typeof candidate.init?.then === "function") {
      return candidate as AladinModule;
    }
    return null;
  };

  let lastError: unknown = null;

  // 1) Vendored local ESM copy.
  try {
    // webpackIgnore keeps this a real browser dynamic import of the
    // same-origin URL instead of a webpack-resolved chunk.
    const mod = await import(/* webpackIgnore: true */ ALADIN_ESM_LOCAL);
    const AladinModule = asAladinModule(mod.default ?? mod);
    if (AladinModule) return AladinModule;
    lastError = new Error(
      "Vendored Aladin Lite is loaded but has an unexpected module shape.",
    );
  } catch (error) {
    lastError = error;
  }

  // 2) Bundled npm package.
  try {
    const mod = await import("aladin-lite");
    const AladinModule = asAladinModule(mod.default ?? mod);
    if (AladinModule) return AladinModule;
    lastError = new Error(
      "Bundled Aladin Lite is loaded but has an unexpected module shape.",
    );
  } catch (error) {
    lastError = error;
  }

  // 3) Official CDN ESM (with retries).
  for (let attempt = 1; attempt <= CDN_MAX_ATTEMPTS; attempt++) {
    try {
      const mod = await import(/* webpackIgnore: true */ ALADIN_ESM_CDN);
      const AladinModule = asAladinModule(mod.default ?? mod);
      if (AladinModule) return AladinModule;
      throw new Error(
        "CDN Aladin Lite is loaded but has an unexpected module shape.",
      );
    } catch (error) {
      lastError = error;
      if (attempt < CDN_MAX_ATTEMPTS) {
        await new Promise((resolve) => setTimeout(resolve, CDN_RETRY_DELAY_MS));
      }
    }
  }
  throw lastError instanceof Error
    ? lastError
    : new Error("Aladin Lite failed to load from every source");
}

interface SkyMarker {
  id: string;
  ra: number;
  dec: number;
  el: HTMLDivElement;
}

const MARKER_SELECT_DISTANCE_PX = 80;

/**
 * All-sky atlas powered by Aladin Lite (CDS). The five catalog markers and
 * their selection/diff-mode styling are drawn as a lightweight HTML overlay
 * projected with `world2pix` — no Aladin object churn.
 */
export function AllSkyAtlas({ clock, onTarget, field, catalogMarks }: {
  clock: AnimationClock;
  onTarget?: (id: string) => void;
  field: SkyField;
  catalogMarks: SkyMark[];
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const aladinElRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const imRef = useRef<AladinInstance | null>(null);
  const markersRef = useRef<SkyMarker[]>([]);

  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [initError, setInitError] = useState<string | null>(null);
  /** True once Aladin leaked a tile-stream failure; the atlas keeps working. */
  const [tilesOffline, setTilesOffline] = useState(false);
  /** Bumped by the Retry button to re-run the whole bootstrap effect. */
  const [retryToken, setRetryToken] = useState(0);

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

  /* ---- Aladin Lite bootstrap ---- */
  useEffect(() => {
    let cancelled = false;
    let im: AladinInstance | null = null;
    let resizeObserver: ResizeObserver | null = null;

    /**
     * Tile-stream failure handling, fed by two sources:
     *
     * 1. `aladin:tile-failure` — dispatched by the early guard script
     *    (public/aladin-rejection-guard.js) after it claims one of Aladin's
     *    leaked network/HiPS rejections. Primary path.
     * 2. A raw `unhandledrejection` fallback — only fires if the guard
     *    script is unavailable (the guard calls stopImmediatePropagation,
     *    so when it is active this listener never sees the same event).
     *
     * Our own API layer always catches its fetch errors, so any *unhandled*
     * network rejection here is Aladin's.
     */
    let tileFailures = 0;
    const applyTileFailure = (message: string, network: boolean) => {
      tileFailures += 1;
      if (cancelled || tileFailures > 1) return;
      setTilesOffline(true);

      // A hard network failure only downgrades a viewer that is not up yet;
      // once the atlas is ready the black canvas + markers keep working.
      if (network) {
        setStatus((current) => (current === "ready" ? current : "error"));
        setInitError(
          "Could not stream sky tiles from the DSS mirrors " +
            "(skies.esac.esa.int). Check your internet connection.",
        );
      }
    };
    const onTileFailure = (event: Event) => {
      const detail = (event as CustomEvent<{ message: string; network: boolean }>)
        .detail;
      applyTileFailure(detail?.message ?? "HiPS tile failure", detail?.network ?? false);
    };
    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const message =
        reason instanceof Error ? reason.message : String(reason ?? "");
      const isNetworkFailure =
        /failed to fetch|networkerror|load failed|fetch failed/i.test(message);
      // Aladin's own leak when a HiPS survey (or its fallback) cannot load.
      const isHiPSFailure = /^HiPS .+error/i.test(message);
      if (!isNetworkFailure && !isHiPSFailure) return;

      event.preventDefault();
      applyTileFailure(message, isNetworkFailure);
    };
    window.addEventListener("aladin:tile-failure", onTileFailure);
    window.addEventListener("unhandledrejection", onUnhandledRejection);

    (async () => {
      try {
        const Aladin = await loadAladinRuntime();
        if (cancelled) return;

        const el = aladinElRef.current;
        if (!el) return;

        window.A = Aladin;

        // Aladin Lite v3: `A.init` is a readiness Promise; the viewer is
        // created with `A.aladin(el, options)`.
        const initPromise = Aladin.init;
        if (initPromise && typeof initPromise.then === "function") {
          await initPromise;
        }

        // Try each survey mirror in turn; a failed attempt can leave partial
        // DOM behind, so reset the viewport element between tries.
        let lastError: unknown = null;
        for (const survey of SURVEY_URLS) {
          try {
            im = await createAladinViewer(Aladin, el, survey);
            lastError = null;
            break;
          } catch (error) {
            lastError = error;
            el.textContent = "";
          }
        }
        if (!im || lastError) {
          throw lastError ?? new Error("Aladin viewer failed to initialize.");
        }
        imRef.current = im;

        // Keep Aladin in sync with the container size (it only listens to
        // window resize events by default).
        const container = el.parentElement;
        if (container && typeof ResizeObserver !== "undefined") {
          resizeObserver = new ResizeObserver(() => {
            window.dispatchEvent(new Event("resize"));
          });
          resizeObserver.observe(container);
        }

        // Aladin may have been initialized before the container settled;
        // nudge it into the correct size on the next frames.
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            window.dispatchEvent(new Event("resize"));
          });
        });

        if (!cancelled) {
          // Aladin's init leaks telemetry fetches to hosts CDS retired in
          // Nov 2026 (its own guard swallows them now). A session that
          // actually came up healthy must not keep that noise, so the
          // failure counter restarts here; the offline badge then reflects
          // only failures that happen while the atlas is running.
          tileFailures = 0;
          setTilesOffline(false);
          setStatus("ready");
        }
      } catch (error) {
        if (!cancelled) {
          setStatus((current) => (current === "ready" ? current : "error"));
          setInitError(error instanceof Error ? error.message : String(error));
        }
      }
    })();

    return () => {
      cancelled = true;
      window.removeEventListener("aladin:tile-failure", onTileFailure);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
      resizeObserver?.disconnect();
      imRef.current = null;
      try {
        im?.remove();
      } catch {
        // ignore teardown errors
      }
    };
  }, [retryToken]);

  useEffect(() => {
    if (status !== "ready") return;
    imRef.current?.gotoRaDec?.(field.ra, field.dec);
    imRef.current?.setFoV?.(field.fov);
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

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)]">
      <div className="flex items-center justify-between border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
        <span className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">
          ALADIN LITE — ALL-SKY ATLAS
        </span>
        <span className="font-mono text-[9px] tracking-wider text-text-muted">
          {status === "ready" ? "DSS / ESA" : status.toUpperCase()}
        </span>
      </div>

      <div
        ref={containerRef}
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

        {/* Tile-stream degraded notice (atlas itself stays usable) */}
        {tilesOffline && status === "ready" && (
          <div className="absolute left-1/2 top-2 z-[6] -translate-x-1/2 rounded-[3px] border border-[#7a5b34] bg-[rgba(46,34,14,0.92)] px-2 py-1 font-mono text-[9px] tracking-wider text-[#e8c07d]">
            SKY TILE STREAM OFFLINE — DSS MIRROR UNREACHABLE
          </div>
        )}

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
            <span className="text-[10px] text-text-muted">
              Sky tiles stream from the ESA DSS mirror (skies.esac.esa.int) —
              check the network connection.
            </span>
            <button
              className="mt-1 cursor-pointer rounded-[3px] border border-[#364e66] bg-[rgba(19,28,38,0.9)] px-3 py-1 text-[10px] tracking-[0.08em] text-[#c7d6e6] transition-colors hover:border-cyan-bright hover:text-cyan-bright"
              onClick={(e) => {
                e.stopPropagation();
                setStatus("loading");
                setInitError(null);
                setTilesOffline(false);
                setRetryToken((token) => token + 1);
              }}
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <p className="border-t border-border-subtle bg-[#0e141c] px-3.5 py-2.5 text-[11px] text-[#8597aa]">
        DSS background via Aladin Lite. Drag to pan, scroll to zoom.
      </p>
    </section>
  );
}
