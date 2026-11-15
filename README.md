# Planet X × SPHEREx Backend

Nisanur Çakır

FastAPI service for comparing public SPHEREx observations on a common celestial grid and sampling a calibrated DR1 spectral cube. The manifest includes DR1 and QR3 observations of a small field near Barnard's Star and tracks the publication status of DR2 and DR3.

## Local setup

Use Python 3.11 or later. From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\planet-x-data.exe --include-cubes --include-benchmarks
.\.venv\Scripts\planet-x-api.exe
```

The last command starts the server at [localhost:8765](http://127.0.0.1:8765/docs). Configure `PLANET_X_PORT`, `PLANET_X_CORS_ORIGINS`, `PLANET_X_MANIFEST`, `PLANET_X_DATA_DIR`, and `PLANET_X_IMPORT_DIR` in `.env` when needed. The download command verifies file sizes and SHA-256 before publishing files into `data/samples`. `--include-cubes` adds a 321 MB download. Processing works offline for downloaded files.

## API

| Route | Parameters and result |
| --- | --- |
| `GET /api/health` | Service status and local FITS count. |
| `GET /api/ready` | Returns 200 once all manifest samples are present, or 503 with the missing epochs. |
| `GET /api/releases` | Release status, archive reference, planned month when announced, and counts for manifest and imported products. |
| `GET /api/datasets` | Observation IDs, dates, bands, quality policy, and provenance. Optional `release` filters by ID, case-insensitively. Unpublished releases return empty product lists. |
| `GET /api/archive/search` | Find IRSA spectral images in the DR1 or QR3 wide survey. Accepts `ra`, `dec`, `release`, `radius_deg`, `limit`, `wavelength_um`, `start_mjd`, and `end_mjd`. |
| `POST /api/archive/import` | Download and register a calibrated DR1 or QR3 exposure cutout. The JSON body contains `archive_id`, `ra`, `dec`, and `fov`. |
| `GET /api/targets` | Return the five challenge targets with catalog references and predicted ICRS positions at optional UTC `mjd`. |
| `GET /api/targets/{target_id}/benchmark` | Return both prepared, aligned benchmark images with WCS and the measured astrometry in a single response. Supported targets are `wise-0855` and `epsilon-indi-b`. Optional `fov` is the displayed width in degrees. |
| `GET /api/targets/{target_id}/observations` | Find real IRSA exposures for a target and return a predicted position for each exposure midpoint. Supports the release, date, and wavelength search filters. |
| `GET /api/targets/{target_id}/reference-light-curve` | Return one AAVSO optical magnitude band for `r-draconis` or `rw-aurigae`. Requires `start_mjd` and `end_mjd`. Optional `band` (`V` or `Vis.`) and `limit` control the results. |
| `GET /api/catalog/{catalog}` | Query real Gaia DR3 (`gaia`) or AllWISE (`wise`) sources by `ra`, `dec`, `radius_deg`, and `limit`. |
| `GET /api/compare` | `ra`, `dec`, `fov`, `epoch_a`, `epoch_b`, and `mode` (`difference`, `side_by_side`, `sum`, or `stack`). Returns aligned A and B, arithmetic result where supported, WCS, validity fractions, flags, and variance-derived values when available. |
| `POST /api/compare/auto` | Choose a compatible difference pair from 2–8 imported `epochs`, `ra`, `dec`, `fov`, and optional `min_gap_days`. Tries up to six pairs in descending time separation. |
| `GET /api/spectrum` | `ra`, `dec`, and optional `epoch`. Omitting `epoch` locates the DR1 tile at the coordinate. Returns 102 ordered channel slots, with `null` flux for invalid or uncovered channels. |
| `GET /api/photometry` | `ra`, `dec`, and one image `epoch`. Fits a point source at the supplied position and returns flux density and statistical error in µJy, observation and bandpass metadata, and quality flags. |
| `POST /api/source-series` | Measure 1–24 image `epochs` at `ra` and `dec` or a catalog `target_id`. Returns detector samples by visit, compatible light curves, and per-exposure errors. |
| `POST /api/astrometry` | Fit the source centroid in two `epochs` at `ra` and `dec` or at the date-dependent position for `target_id`. Optional `fov` sets the reference-star search width. Returns the relative offset and its covariance when the independent registration passes. |
| `GET /api/layers` | `epoch`. Returns the six detector groups and their channel ranges. |
| `GET /api/layers/{detector}` | `ra`, `dec`, `fov`, optional `epoch`, and optional `channel` (1–17, default 9). Set `combine=true` to use all 17 channels from the detector. The composite returns an NHITS-weighted mean, contributing channel and input pixel counts, and the combined flags within the selected tile. |

Coordinates use ICRS decimal degrees. `fov` is the square cutout width in degrees, with a maximum of 1°. Grid width is capped at 255 pixels. Rows follow FITS Y and columns follow FITS X, starting at index 0. Use the returned WCS to place images on the sky. Data errors return an `error` object with a machine-readable `code`. Validation errors also list the affected fields.

```powershell
curl.exe 'http://127.0.0.1:8765/api/compare?ra=269.45&dec=4.7&fov=0.04&epoch_a=dr1-2025-10-01-d1&epoch_b=dr1-2026-03-11-d1&mode=difference'
curl.exe 'http://127.0.0.1:8765/api/spectrum?ra=269.45&dec=4.7&epoch=dr1-coadd'
curl.exe 'http://127.0.0.1:8765/api/photometry?ra=269.448214&dec=4.695946&epoch=dr1-2025-10-01-d1'
curl.exe 'http://127.0.0.1:8765/api/releases'
curl.exe 'http://127.0.0.1:8765/api/datasets?release=QR3'
curl.exe 'http://127.0.0.1:8765/api/archive/search?ra=269.45&dec=4.7&release=DR1&radius_deg=0.01&wavelength_um=1.024&limit=10'
curl.exe 'http://127.0.0.1:8765/api/compare?ra=269.45&dec=4.7&fov=0.04&epoch_a=dr1-2025-10-01-d1&epoch_b=qr3-2026-08-25-d1&mode=side_by_side'
```

Use `planet-x-data --release QR3` to download just the QR3 cutout. The default manifest supports side-by-side viewing of the DR1 and QR3 example cutouts. Their local passbands are too far apart for a difference image under the comparison tolerance.

Archive search uses Astroquery with IRSA SIA2. The radius defaults to 0.01° and accepts up to 1°. The result limit defaults to 20 and accepts up to 100. Optional wavelength and UTC MJD filters match overlapping archive ranges. `has_more` indicates that the search reached the result limit with additional matches. Each result includes the detector band, archive ID, FITS URL, and a matching local `epoch` when available. The processing endpoints use the FITS WCS to check coverage. [IRSA archive access](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/)

Send the `archive_id` from search together with a cutout center and width between 0.02° and 0.2°. The API resolves the ID at IRSA, downloads a cutout up to 32 MiB, validates the FITS, and returns the observation metadata and an `epoch` for `/api/compare` and `/api/photometry`. A new cutout returns HTTP 201. The same ID, center, and width return HTTP 200 with the stored epoch. Imports appear in `/api/datasets` and survive restarts in `PLANET_X_IMPORT_DIR`, which defaults to `imports` under the local data directory and to `/imports` in the container. Remote failures return `archive_unavailable` (502) or `archive_timeout` (504).

Archive queries and downloads retry temporary IRSA errors and interrupted transfers up to twice. The API honors `Retry-After` delays up to five seconds and returns the upstream failure for longer delays. A download retry starts from byte zero. The API publishes the FITS and its metadata together after validation.

`PLANET_X_IMPORT_QUOTA_BYTES` defaults to 1 GiB (1073741824 bytes) per import directory. It covers imported FITS, their metadata, and staging reservations. Use the same limit for workers sharing a local volume. A new cutout that would exceed it returns HTTP 507 with `import_quota_exceeded` and byte counts. Cached imports and processing stay available at capacity.

After a worker exits unexpectedly, the next new import reclaims abandoned staging reservations before checking the quota. Active downloads keep their reservations and published observations stay available. For older abandoned staging directories without an ownership lock, or to remove unwanted published observations, stop the workers using the volume and remove the corresponding directories manually.

```powershell
$Cutout = @{ archive_id = 'ivo://irsa.ipac/spherex_dr1?2025W40_1A_0471_1/D1'; ra = 269.45; dec = 4.7; fov = 0.05 }
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8765/api/archive/import' -ContentType 'application/json' -Body ($Cutout | ConvertTo-Json -Compress)
```

Difference is `B − A`, and stack is the two-sample mean. Arithmetic requires compatible calibration and units plus at least 10% usable common coverage. Spectral images also require matching local bandpasses. The `alignment.registration` report gives the median sky offset and RMS scatter from at least five shared sources when enough are present. Arithmetic returns `alignment_failed` if those measurements disagree with the WCS. Sparse fields return `insufficient_matches` and retain the WCS-based result with a warning. Difference returns a symmetric display range and a center-pixel measurement. The API surfaces limitations from the local PSF, WCS registration, background, and available variance. The cube provides multi-epoch pixel brightness with per-channel flags and counts. Its format supplies no channel uncertainties.

NASA/IPAC IRSA Level 2B v27 observations from DR1 and QR3 share the same pipeline and calibration. The API can compare them when the FITS units, detector, footprint, and local wavelength checks pass. Each response retains the original release and processing metadata. [IRSA release notes](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/)

Photometry uses the local FITS ePSF through Photutils and fits its amplitude and a constant background on the native exposure pixels. It estimates pixel solid angle from the local WCS. Wavelength and bandwidth come from the FITS wavelength lookup. The error includes statistical variance. Crowding, pointing error, and calibration systematics can affect the estimate. `quality_flags` includes `low_snr` below SNR 5, `high_residual` above reduced χ² 5, and `masked_fit_pixels` when pixels were excluded. Signed flux estimates at low SNR are available for statistical analysis. `photometry_unavailable` (HTTP 409) covers missing calibration, clipped fit windows and masked source cores. [IRSA ePSF format](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) · [IRSA photometry method](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html)

When the source core or fit window fails the pixel checks, `error.details` reports usable pixel counts, missing core variance, and the original FITS bitmask with decoded flag names. Both source series and astrometry report these details per exposure.

Display the AAVSO optical reference on its own apparent magnitude axis with the returned attribution. The endpoint preserves observer codes, reported error, and fainter-than estimates. For intervals that reach the result cap, `has_more` signals that a narrower date query can retrieve more points. For example, R Draconis has visual observations at `/api/targets/r-draconis/reference-light-curve?start_mjd=61180&end_mjd=61308&limit=129`. [AAVSO archival photometry](https://aavso.org/search-and-download-data/) · [AAVSO attribution guidance](https://aavso.org/data-usage-guidelines-2026-07/)

Coordinate-only spectrum and layer requests select an ICRS HEALPix tile in the official DR1 archive. The first request for a tile can download about 321 MB. It verifies the tile identifier and FITS structure and records the SHA-256 of the received file. Later calls can use the returned epoch or the coordinate. `PLANET_X_CUBE_CACHE_DIR` defaults to `cubes` under the import directory. `PLANET_X_CUBE_CACHE_BYTES` defaults to 2 GiB, with older idle tiles evicted as needed. An uncached request can receive `cube_busy` (503) while another tile is downloading. [IRSA FITS cube tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/)

Set `PLANET_X_DR1_CUBE_REVISION` to a newer supported IRSA `hips_YYYYMMDD` directory when IRSA republishes the DR1 tiles with the same layout. The new revision uses a separate cache directory. Newly indexed exposures appear in DR1 and QR3 searches directly from IRSA.

The frontend share and embed links carry `ra`, `dec`, and `fov`. If the user selected an archive pair, the links also carry both upstream IDs and cutout centers so a fresh backend can fetch the pair directly from IRSA. The frontend requests larger cutouts when the field exceeds the imported width. The spectrum endpoint works with coordinates alone. Catalog overlays report their native reference frame and Gaia's epoch. Target positions are geocentric catalog predictions and are evaluated at each image's observation midpoint.

Target searches return a local epoch only when its FITS footprint contains the predicted source position. The source series groups measured detector samples by exposure visit. Light curves use matching detector, calibration, and local wavelength. A change is provided when two compatible samples pass the SNR and residual checks. Weighted means can include signed low-SNR samples and exclude high-residual fits. The [challenge target report](docs/benchmarks/CHALLENGE_TARGETS.md) records the data and quality outcomes from real observations.

Astrometry fits position, ePSF amplitude, and local background in each observation. It excludes the target from the independent reference-star match. `measured_offset_arcsec` contains chronological east and north offsets corrected for the median registration shift. A two-dimensional Mahalanobis distance estimates displacement relative to the centroid covariance and reference field scatter. Failed fits or registration leave the relative offset empty. Use `scripts/smoke_backend.py --wise-0855` on a running API to verify the benchmark using checksum-pinned IRSA cutouts.

Once the two pairs are prepared with `--include-benchmarks`, `GET /api/targets` advertises `benchmark_available` for those targets. The frontend can call `GET /api/targets/wise-0855/benchmark` and render `comparison.images.a` and `comparison.images.b` on `comparison.grid.wcs`. The fitted sky coordinates are in `astrometry.samples[].centroid`. The registered displacement and covariance are in `astrometry.measured_offset_arcsec`. The same request works for `epsilon-indi-b`. Changing `fov` resizes the displayed image cutouts. The reference-star search retains its validated field width.

## Tests and data

Run `.\.venv\Scripts\python.exe -m pytest -q`. The archive tests run Uvicorn and a local HTTP archive server to test discovery, import, comparison, photometry, a process restart, duplicate requests, and rejected FITS files. They use generated FITS by default. To use verified DR1 FITS, set `$env:PLANET_X_E2E_SAMPLES = (Resolve-Path data/samples).Path` before running `python -m pytest -q tests/test_archive_e2e.py`. Additional real-data tests cover comparison, spectrum, and all six detector layers when the FITS files are present. See the [data inventory and citations](docs/DATA_SOURCES.md) and the [versioned manifest](data/manifests/spherex-dr1.json) for exact files. Switch `PLANET_X_MANIFEST` to load a new release with the same schema and supported FITS layouts, then run `planet-x-data` before restarting the API.

Run `python -m pytest -q tests/test_archive_e2e.py -k quota` to check shared storage. The tests cover 32 mixed requests against two workers near capacity and reclaiming space after a worker is killed mid-download.

Run `.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard` to check target coverage and quality in the local samples. Add `--archive` to inspect a sample of distinct DR1 and QR3 visits from the live IRSA catalog. See the [Barnard benchmark](docs/benchmarks/BARNARDS_STAR.md) for results and commands.

## Backend CI/CD

[GitHub Actions](https://github.com/Pentexa/SpectraX/actions/workflows/backend.yml) runs the Python 3.11 test suite on pull requests targeting `main` and on each push to `main`. After tests pass on `main`, the workflow builds the container and verifies the public DR1 and QR3 files against the manifest. It then runs the archive import tests against the verified DR1 files and HTTP tests for the release catalog, comparison, spectrum, detector layers, and QR3 cutout. Successful runs publish `ghcr.io/pentexa/spectrax-api:main` and `ghcr.io/pentexa/spectrax-api:sha-<full-commit-sha>`. The FITS files are cached by manifest hash and stay outside the published image.

A release tag such as `v0.1.0` must match the package and API versions. The release workflow reruns those checks and uses the live IRSA catalog to download fresh DR1 and QR3 cutouts and verify the low-SNR Cygnus reference. Their sizes and SHA-256 hashes must match the expected products before the versioned image and GitHub release are published.

Run the published image locally. Authenticate with GHCR first if the package is private.

```powershell
docker run --rm -p 127.0.0.1:8765:8765 ghcr.io/pentexa/spectrax-api:main
```

For FITS-backed endpoints, download the samples using the local setup above and mount them read-only. Mount a writable volume at `/imports` to keep imported cutouts across container replacement.

```powershell
$Samples = (Resolve-Path 'data/samples').Path
docker run --rm -p 127.0.0.1:8765:8765 --mount "type=bind,source=$Samples,target=/data,readonly" --mount "type=volume,source=spherex-imports,target=/imports" ghcr.io/pentexa/spectrax-api:main
```

With the sample data mounted, run `python scripts/smoke_backend.py` from another terminal to repeat the release smoke test.
Add `--live-archive` and use a fresh import directory to repeat the live IRSA check.
Add `--wide-sky` to verify an additional IRSA tile outside the manifest region.

## Server deployment

On a Docker host, run `docker compose -f deploy/compose.yaml up -d --wait`. Set `SPECTRAX_IMAGE` to the desired image tag or digest. Compose prepares the verified sample files, mounts them read-only in the API, and keeps imported FITS and cached cubes in a writable volume. The gateway on `127.0.0.1:8080` applies a request limit and returns HTTP 429 when the limit is exceeded. Set `PLANET_X_CORS_ORIGINS` to the frontend origin when it is known.

Point the host's HTTPS reverse proxy at the gateway and use `/api/ready` for uptime checks. The gateway keeps a shared rate limit for archive and cube routes. `docker compose -f deploy/compose.yaml logs api gateway` shows request and service logs. Keep the `samples` and `imports` volumes across upgrades.
