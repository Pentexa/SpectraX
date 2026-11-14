# Planet X × SPHEREx Backend

FastAPI service for comparing public SPHEREx observations on a common celestial grid and sampling a calibrated DR1 spectral cube. The manifest includes DR1 and QR3 observations of a small field near Barnard's Star and tracks the publication status of DR2 and DR3.

## Local setup

Use Python 3.11 or later. From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
.\.venv\Scripts\planet-x-data.exe --include-cubes
.\.venv\Scripts\planet-x-api.exe
```

The last command starts the server at [localhost:8765](http://127.0.0.1:8765/docs). Configure `PLANET_X_PORT`, `PLANET_X_CORS_ORIGINS`, `PLANET_X_MANIFEST` and `PLANET_X_DATA_DIR` in `.env` when needed. The download command verifies file sizes and SHA-256 before publishing files into `data/samples`. `--include-cubes` adds a 321 MB download. With cached files, the API serves results offline.

## API

| Route | Parameters and result |
| --- | --- |
| `GET /api/health` | Service status and local FITS count. |
| `GET /api/releases` | Release status, archive reference, planned month when announced, and counts for the configured manifest. |
| `GET /api/datasets` | Observation IDs, dates, bands, quality policy, and provenance. Optional `release` filters by ID, case-insensitively. Unpublished releases return empty product lists. |
| `GET /api/compare` | `ra`, `dec`, `fov`, `epoch_a`, `epoch_b`, and `mode` (`difference`, `side_by_side`, `sum`, or `stack`). Returns aligned A and B, arithmetic result where supported, WCS, validity fractions, flags, and variance-derived values when available. |
| `GET /api/spectrum` | `ra`, `dec`, and `epoch`. Returns 102 ordered channel slots for a supported cube, with `null` flux for invalid or uncovered channels. |
| `GET /api/photometry` | `ra`, `dec`, and one image `epoch`. Fits a point source at the supplied position and returns flux density and statistical error in µJy, observation and bandpass metadata, and quality flags. |
| `GET /api/layers` | `epoch`. Returns the six detector groups and their channel ranges. |
| `GET /api/layers/{detector}` | `ra`, `dec`, `fov`, `epoch`, and optional `channel` (1–17, default 9). Returns a cutout of one calibrated channel and its flags. |

Coordinates use ICRS decimal degrees. `fov` is the square cutout width in degrees, with a maximum of 1°. Grid width is capped at 255 pixels. Rows follow FITS Y and columns follow FITS X, starting at index 0. Use the returned WCS to place images on the sky. Data errors return an `error` object with a machine-readable `code`. Validation errors also list the affected fields.

```powershell
curl.exe 'http://127.0.0.1:8765/api/compare?ra=269.45&dec=4.7&fov=0.04&epoch_a=dr1-2025-10-01-d1&epoch_b=dr1-2026-03-11-d1&mode=difference'
curl.exe 'http://127.0.0.1:8765/api/spectrum?ra=269.45&dec=4.7&epoch=dr1-coadd'
curl.exe 'http://127.0.0.1:8765/api/photometry?ra=269.448214&dec=4.695946&epoch=dr1-2025-10-01-d1'
curl.exe 'http://127.0.0.1:8765/api/releases'
curl.exe 'http://127.0.0.1:8765/api/datasets?release=QR3'
curl.exe 'http://127.0.0.1:8765/api/compare?ra=269.45&dec=4.7&fov=0.04&epoch_a=dr1-2025-10-01-d1&epoch_b=qr3-2026-08-25-d1&mode=side_by_side'
```

Use `planet-x-data --release QR3` to download just the QR3 cutout. The default manifest supports side-by-side viewing of the DR1 and QR3 example cutouts. Their local passbands are too far apart for a difference image under the comparison tolerance.

Difference is `B − A`, and stack is the two-sample mean. Arithmetic requires compatible calibration and units plus at least 10% usable common coverage. Spectral images also require matching local bandpasses. The `alignment.registration` report gives the median sky offset and RMS scatter from at least five shared sources when enough are present. Arithmetic returns `alignment_failed` if those measurements disagree with the WCS. Sparse fields return `insufficient_matches` and retain the WCS-based result with a warning. Difference returns a symmetric display range and a center-pixel measurement. The API surfaces limitations from the local PSF, WCS registration, background, and available variance. The cube provides multi-epoch pixel brightness with per-channel flags and counts. Its format supplies no channel uncertainties.

Photometry uses the local FITS ePSF through Photutils and fits its amplitude and a constant background on the native exposure pixels. It estimates pixel solid angle from the local WCS. Wavelength and bandwidth come from the FITS wavelength lookup. The error includes statistical variance. Crowding, pointing error, and calibration systematics can affect the estimate. `quality_flags` includes `low_snr` below SNR 5, `high_residual` above reduced χ² 5, and `masked_fit_pixels` when pixels were excluded. Signed flux estimates at low SNR are available for statistical analysis. `photometry_unavailable` (HTTP 409) covers missing calibration, clipped fit windows and masked source cores. [IRSA ePSF format](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) · [IRSA photometry method](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html)

## Tests and data

Run `.\.venv\Scripts\python.exe -m pytest -q`. The real-data test runs when the FITS files are present and covers comparison, spectrum, and all six detector layers. The remaining tests use synthetic fixtures. See the [data inventory and citations](docs/DATA_SOURCES.md) and the [versioned manifest](data/manifests/spherex-dr1.json) for exact files. Switch `PLANET_X_MANIFEST` to load a new release with the same schema and supported FITS layouts, then run `planet-x-data` before restarting the API.

Run `.\.venv\Scripts\python.exe -m pipeline.benchmark_barnard` to check target coverage and quality at the expected coordinates of Barnard's Star. See the [benchmark report](docs/benchmarks/BARNARDS_STAR.md) for results and full-exposure commands.

## Backend CI/CD

[GitHub Actions](https://github.com/Pentexa/SkyHunter/actions/workflows/backend.yml) runs the Python 3.11 test suite on pull requests targeting `main` and on each push to `main`. After tests pass on `main`, the workflow builds the container, verifies the public DR1 and QR3 files against the manifest, and mounts them read-only for HTTP tests of the release catalog, real difference image, spectrum, detector layers and QR3 cutout. Successful runs publish `ghcr.io/pentexa/skyhunter-api:main` and `ghcr.io/pentexa/skyhunter-api:sha-<full-commit-sha>` using GitHub's workflow token. The FITS files are cached by manifest hash and stay outside the published image.

Run the published image locally. Authenticate with GHCR first if the package is private.

```powershell
docker run --rm -p 127.0.0.1:8765:8765 ghcr.io/pentexa/skyhunter-api:main
```

For FITS-backed endpoints, download the samples using the local setup above, then mount them read-only. A hosting service can use the same image and provide a volume for the data.

```powershell
$Samples = (Resolve-Path 'data/samples').Path
docker run --rm -p 127.0.0.1:8765:8765 --mount "type=bind,source=$Samples,target=/data,readonly" ghcr.io/pentexa/skyhunter-api:main
```

With the sample data mounted, run `python scripts/smoke_backend.py` from another terminal to repeat the release smoke test.
