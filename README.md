# SPHEREx Sky Hunter

A citizen science portal for hunting transients and Planet X across NASA SPHEREx
all-sky spectral data. The original single-file prototype has been re-architected
on **Next.js (App Router) + TypeScript + Tailwind CSS v4**.

## Architecture

```
src/
├── app/                    # Next.js App Router (layout, page, globals.css)
│   ├── layout.tsx          # Root layout: fonts (next/font), metadata
│   ├── page.tsx            # Server component → Dashboard
│   └── globals.css         # Tailwind v4 @theme tokens
├── components/
│   ├── layout/             # SiteHeader, SiteFooter, InfoModal
│   ├── canvas/             # Reusable canvas primitives
│   │                       #   (MiniStarfield, AstrometryGauge, Sparkline, OrbitDiagram)
│   └── home/
│       ├── Dashboard.tsx   # 3-column shell + data loading
│       ├── left/           # EpochComparison, DetectionPanel, StarList
│       ├── center/         # AllSkyAtlas (Aladin Lite + HTML overlay markers)
│       ├── right/          # SpectralChart, BandGrid, DataTracker
│       └── bottom/         # PlanetXPanel
├── hooks/
│   ├── useElementSize.ts   # ResizeObserver wrapper
│   └── useAnimationClock.ts# Shared 60fps animation clock (no re-renders)
├── lib/
│   ├── api/                # types.ts, client.ts, endpoints.ts, mock.ts
│   ├── astronomy/          # coords.ts (RA/Dec parsing, angular distance)
│   ├── constants/          # bands.ts, nav.ts, epochs.ts
│   ├── types/              # aladin.d.ts (ambient Aladin Lite types)
│   └── utils/              # random.ts (seeded RNG), canvas.ts (DPR setup),
│                           #   loadExternal.ts (script/stylesheet loader)
└── store/
    └── dashboardStore.ts   # Zustand store (data + UI state + actions)
```

> **All-sky map**: the hand-rolled Mollweide canvas was replaced with
> **Aladin Lite v3** (CDS sky atlas). The runtime is installed as an npm
> dependency (`aladin-lite`) and bundled with the app; a vendored local copy
> (`public/vendor/aladin/aladin.esm.js`) and the official CDN act as
> fallbacks. Catalog stars, selection, diff-mode styling and the orbit
> animation are HTML overlays projected with `world2pix`.

## Getting started

```bash
# From the separate SpectraX backend checkout
planet-x-data --include-cubes --include-benchmarks
planet-x-api

# From this frontend checkout
npm ci
npm run dev
```

## Backend integration

Set `SPECTREX_API_URL` before building and starting Next.js. The default is
`http://127.0.0.1:8765`. The browser calls the same-origin Next.js proxy,
which forwards science requests to the SpectraX FastAPI service.

The dashboard loads the five challenge targets from FastAPI and opens the
prepared WISE 0855 or Epsilon Indi B pair when available. The observation
archive accepts a date range, release and wavelength. The comparison panel
supports side-by-side viewing, blinking, subtraction, summing and stacking
with backend quality checks.

The spectral panel loads calibrated DR1 channels on demand. It displays
missing channels and can show the selected channel as a sky image. Source
photometry from individual visits is displayed separately, as are AAVSO
optical reference curves for the two variable targets. Gaia DR3 and AllWISE
can be projected onto the image grid or the Aladin atlas.

Copy a share link or iframe from the coordinate panel. The `/embed` route
accepts a target or RA/Dec with the field width and optional epoch IDs.
Imported epoch IDs refer to the connected backend. Host the frontend and
configure its backend URL to share an embed outside your local machine.

The active contract is in `src/lib/api/science.ts`. An unavailable API shows
a retry action and measured results include the archive's quality information.

## Code standards

- **One responsibility per component** — no file ever bloats.
- **Canvas rendering** goes through `lib/utils/canvas.ts` (DPR-aware).
- **Animations** use a shared clock (`useAnimationClock`) instead of re-renders.
- **Data access** lives only in `lib/api/*`; components never see URLs.
- **State** is centralized in the Zustand store; components consume via selectors.

## Scripts

```bash
npm run dev        # development
npm run build      # production build
npm run lint       # lint (Next.js)
npm run typecheck  # tsc --noEmit
```
