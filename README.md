# Planet X × SPHEREx Backend

FastAPI service for comparing two public SPHEREx DR1 observations on a common celestial grid and sampling a calibrated DR1 spectral cube. The example covers a small field near Barnard's Star.

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
| `GET /api/datasets` | Observation IDs, dates, bands, quality policy, and provenance. |
| `GET /api/compare` | `ra`, `dec`, `fov`, `epoch_a`, `epoch_b`, and `mode` (`difference`, `side_by_side`, `sum`, or `stack`). Returns aligned A and B, arithmetic result where supported, WCS, validity fractions, flags, and variance-derived values when available. |
| `GET /api/spectrum` | `ra`, `dec`, and `epoch`. Returns 102 ordered channel slots for a supported cube, with `null` flux for invalid or uncovered channels. |
| `GET /api/layers` | `epoch`. Returns the six detector groups and their channel ranges. |
| `GET /api/layers/{detector}` | `ra`, `dec`, `fov`, `epoch`, and optional `channel` (1–17, default 9). Returns a cutout of one calibrated channel and its flags. |

Coordinates use ICRS decimal degrees. `fov` is the square cutout width in degrees, with a maximum of 1°. Grid width is capped at 255 pixels. Rows follow FITS Y and columns follow FITS X, starting at index 0. Use the returned WCS to place images on the sky. Data errors return an `error` object with a machine-readable `code`. Validation errors also list the affected fields.

```powershell
curl.exe 'http://127.0.0.1:8765/api/compare?ra=269.45&dec=4.7&fov=0.04&epoch_a=dr1-2025-10-01-d1&epoch_b=dr1-2026-03-11-d1&mode=difference'
curl.exe 'http://127.0.0.1:8765/api/spectrum?ra=269.45&dec=4.7&epoch=dr1-coadd'
```

Difference is `B − A`, and stack is the two-sample mean. Arithmetic requires compatible calibration and units plus at least 10% usable common coverage. Spectral images also require matching local bandpasses. Difference returns a symmetric display range and a center-pixel measurement. The API surfaces limitations from the local PSF, WCS registration, background, and available variance. The cube provides multi-epoch pixel brightness with per-channel flags and counts. Its format supplies no channel uncertainties.

## Tests and data

Run `.\.venv\Scripts\python.exe -m pytest -q`. The real-data test runs when the FITS files are present and covers comparison, spectrum, and all six detector layers. The remaining tests use synthetic fixtures. See the [data inventory and citations](docs/DATA_SOURCES.md) and the [versioned manifest](data/manifests/spherex-dr1.json) for exact files. Switch `PLANET_X_MANIFEST` to load a new release with the same schema and supported FITS layouts, then run `planet-x-data` before restarting the API.
