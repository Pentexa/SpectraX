import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Path as RoutePath, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipeline.archive import ArchiveRelease, ArchiveSearch, search_images
from pipeline.catalog import Cube, DataError, Position, data_path, load_manifest
from pipeline.compare import Mode, compare
from pipeline.exposures import ImportRequest, get_import, import_exposure, list_imports
from pipeline.images import read_image
from pipeline.import_storage import DEFAULT_IMPORT_QUOTA_BYTES, ImportQuota
from pipeline.ingest import ROOT, configured_path
from pipeline.photometry import Photometry, measure_source
from pipeline.spectra import detector_layer, layers, spectrum

Epoch = Annotated[str, Query(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")]
RightAscension = Annotated[float, Query(ge=0, lt=360, description="ICRS right ascension in degrees")]
Declination = Annotated[float, Query(ge=-90, le=90, description="ICRS declination in degrees")]
Fov = Annotated[float, Query(gt=0, le=1, description="Square cutout width in degrees")]
ReleaseFilter = Annotated[str, Query(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")]
ArchiveDate = Annotated[float, Query(ge=0, le=100_000, description="UTC Modified Julian Date")]


def create_app(manifest_path: Path | None = None, data_dir: Path | None = None,
               import_dir: Path | None = None) -> FastAPI:
    load_dotenv(ROOT / '.env')
    manifest_path = manifest_path or configured_path('PLANET_X_MANIFEST', 'data/manifests/spherex-dr1.json')
    data_dir = data_dir or configured_path('PLANET_X_DATA_DIR', 'data/samples')
    import_dir = import_dir or Path(os.environ.get('PLANET_X_IMPORT_DIR', data_dir / 'imports'))
    try:
        quota_bytes = int(os.environ.get('PLANET_X_IMPORT_QUOTA_BYTES', DEFAULT_IMPORT_QUOTA_BYTES))
        if quota_bytes <= 0:
            raise ValueError
    except ValueError as exc:
        raise ValueError('PLANET_X_IMPORT_QUOTA_BYTES must be a positive integer') from exc
    import_quota = ImportQuota(import_dir, quota_bytes)

    @asynccontextmanager
    async def lifespan(api: FastAPI):
        manifest = load_manifest(manifest_path)
        api.state.manifest = manifest
        api.state.observations = {record.epoch: record for record in manifest.observations}
        api.state.cubes = {record.epoch: record for record in manifest.cubes}
        yield

    api = FastAPI(title='Planet X SPHEREx API', version='0.1.0', lifespan=lifespan)
    origins = os.environ.get('PLANET_X_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    api.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in origins.split(',') if origin.strip()],
                       allow_methods=['GET', 'POST'], allow_headers=['Accept', 'Content-Type'])

    @api.exception_handler(DataError)
    async def data_error(_: Request, error: DataError):
        payload = {'code': error.code, 'message': str(error)}
        if error.details is not None:
            payload['details'] = error.details
        return JSONResponse(status_code=error.status, content={'error': payload})

    @api.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError):
        fields = [{'field': '.'.join(map(str, issue['loc'])), 'message': issue['msg']} for issue in error.errors()]
        return JSONResponse(status_code=422, content={'error': {'code': 'invalid_request', 'fields': fields}})

    def lookup_observation(epoch: str):
        observation = api.state.observations.get(epoch)
        return (observation, data_dir) if observation else get_import(import_dir, epoch)

    def require_observation(epoch: str):
        located = lookup_observation(epoch)
        if located is None:
            raise DataError('unknown_epoch', f"No image epoch '{epoch}'", 404)
        return located

    @api.get('/api/health')
    def health():
        products = [(item, data_dir) for item in [*api.state.observations.values(), *api.state.cubes.values()]]
        products.extend(list_imports(import_dir))
        return {'status': 'ok', 'products': len(products),
                'available_locally': sum((directory / item.filename).is_file() for item, directory in products)}

    @api.get('/api/releases')
    def releases():
        manifest = api.state.manifest
        imported = list_imports(import_dir)
        result = []
        for release in manifest.releases:
            observations, cubes = manifest.select_release(release.id)
            exposures = [(item, data_dir) for item in observations]
            exposures.extend((item, directory) for item, directory in imported if item.release == release.id)
            result.append(release.model_dump(mode='json') | {
                'observations': len(exposures), 'cubes': len(cubes),
                'available_locally': (sum((directory / item.filename).is_file() for item, directory in exposures)
                                      + sum((data_dir / item.filename).is_file() for item in cubes)),
            })
        return {'releases': result}

    @api.get('/api/datasets')
    def datasets(release: ReleaseFilter | None = None):
        manifest = api.state.manifest
        observations, cubes = manifest.select_release(release) if release else (manifest.observations, manifest.cubes)
        exposures = [(item, data_dir) for item in observations]
        exposures.extend((item, directory) for item, directory in list_imports(import_dir)
                         if release is None or item.release == release.upper())
        return {'observations': [item.metadata(directory) for item, directory in exposures],
                'cubes': [entry.metadata(data_dir) for entry in cubes]}

    @api.get('/api/archive/search')
    def archive_search(
        ra: RightAscension,
        dec: Declination,
        release: ArchiveRelease = 'DR1',
        radius_deg: Annotated[float, Query(gt=0, le=1)] = 0.01,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        wavelength_um: Annotated[float, Query(gt=0, le=10)] | None = None,
        start_mjd: ArchiveDate | None = None,
        end_mjd: ArchiveDate | None = None,
    ) -> ArchiveSearch:
        return search_images(
            release=release, ra=ra, dec=dec, radius_deg=radius_deg, limit=limit, wavelength_um=wavelength_um,
            start_mjd=start_mjd, end_mjd=end_mjd,
            local_observations=[*((item, data_dir) for item in api.state.manifest.observations),
                                *list_imports(import_dir)],
        )

    @api.post('/api/archive/import', status_code=201, responses={
        200: {'description': 'Existing cutout'}, 507: {'description': 'Imported exposure storage quota exceeded'},
    })
    def archive_import(request: ImportRequest, response: Response):
        observation, directory, created = import_exposure(import_quota, request)
        response.status_code = 201 if created else 200
        return observation.metadata(directory)

    @api.get('/api/compare')
    def compare_epochs(ra: RightAscension, dec: Declination, fov: Fov, epoch_a: Epoch, epoch_b: Epoch,
                       mode: Mode = 'difference'):
        a, directory_a = require_observation(epoch_a)
        b, directory_b = require_observation(epoch_b)
        image_a, image_b = read_image(directory_a, a), read_image(directory_b, b)
        result = compare(Position(ra=ra, dec=dec, fov=fov), mode, a, b, image_a, image_b)
        result['epochs'] = {'a': a.metadata(directory_a) | {'fits': image_a.metadata},
                            'b': b.metadata(directory_b) | {'fits': image_b.metadata}}
        return result

    def get_cube(epoch: str) -> Cube:
        cube = api.state.cubes.get(epoch)
        if cube is None:
            if lookup_observation(epoch) is not None:
                raise DataError('spectrum_unavailable', 'This exposure has no calibrated channel cube. See /api/datasets.', 409)
            raise DataError('unknown_epoch', f"No cube epoch '{epoch}'", 404)
        return cube

    @api.get('/api/photometry')
    def photometry_at(ra: RightAscension, dec: Declination, epoch: Epoch) -> Photometry:
        if epoch in api.state.cubes:
            raise DataError('photometry_unavailable', 'Source photometry requires a single exposure epoch', 409)
        observation, directory = require_observation(epoch)
        return measure_source(directory, observation, ra, dec)

    def cube_revision(cube: Cube) -> tuple[int, int]:
        stat = data_path(data_dir, cube).stat()
        return stat.st_mtime_ns, stat.st_size

    @lru_cache(maxsize=32)
    def cached_spectrum(epoch: str, ra: float, dec: float, revision: tuple[int, int]):
        return spectrum(data_dir, api.state.cubes[epoch], ra, dec)

    @lru_cache(maxsize=16)
    def cached_layer(epoch: str, ra: float, dec: float, fov: float, detector: int, channel: int,
                     revision: tuple[int, int]):
        return detector_layer(data_dir, api.state.cubes[epoch], Position(ra=ra, dec=dec, fov=fov), detector, channel)

    @api.get('/api/spectrum')
    def spectrum_at(ra: RightAscension, dec: Declination, epoch: Epoch):
        cube = get_cube(epoch)
        return cached_spectrum(epoch, ra, dec, cube_revision(cube))

    @api.get('/api/layers')
    def list_layers(epoch: Epoch):
        return layers(data_dir, get_cube(epoch))

    @api.get('/api/layers/{detector}')
    def layer_at(detector: Annotated[int, RoutePath(ge=1, le=6)], ra: RightAscension, dec: Declination,
                 fov: Fov, epoch: Epoch, channel: Annotated[int, Query(ge=1, le=17)] = 9):
        cube = get_cube(epoch)
        return cached_layer(epoch, ra, dec, fov, detector, channel, cube_revision(cube))

    return api


app = create_app()


def run():
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('PLANET_X_PORT', '8765')))
