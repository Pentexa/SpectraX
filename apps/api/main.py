import os
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Path as RoutePath, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import Field, FiniteFloat

from pipeline.archive import ArchiveRelease, ArchiveSearch, search_images
from pipeline.catalog import Cube, DataError, Position, data_path, load_manifest
from pipeline.catalog_overlays import Overlay, query_overlay
from pipeline.compare import Mode, compare
from pipeline.cube_archive import DEFAULT_CACHE_BYTES, DEFAULT_DR1_REVISION, CubeCache, tile_at, tile_from_epoch
from pipeline.exposures import ImportRequest, get_import, import_exposure, list_imports
from pipeline.images import read_image
from pipeline.import_storage import DEFAULT_IMPORT_QUOTA_BYTES, ImportQuota
from pipeline.ingest import ROOT, configured_path
from pipeline.photometry import Photometry, measure_source
from pipeline.source_series import EpochId, SourceSeriesRequest, source_series
from pipeline.spectra import detector_layer, layers, spectrum
from pipeline.targets import DEFAULT_TARGET_MJD, TARGETS, covered_target_epoch, get_target

Epoch = Annotated[str, Query(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")]
RightAscension = Annotated[float, Query(ge=0, lt=360, description="ICRS right ascension in degrees")]
Declination = Annotated[float, Query(ge=-90, le=90, description="ICRS declination in degrees")]
Fov = Annotated[float, Query(gt=0, le=1, description="Square cutout width in degrees")]
ReleaseFilter = Annotated[str, Query(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")]
ArchiveDate = Annotated[float, Query(ge=0, le=100_000, description="UTC Modified Julian Date")]
TargetDate = Annotated[float, Query(ge=60_000, le=70_000, description="UTC Modified Julian Date")]


class AutoCompareRequest(Position):
    fov: FiniteFloat = Field(gt=0, le=1)
    epochs: list[EpochId] = Field(min_length=2, max_length=8)
    min_gap_days: FiniteFloat = Field(default=1, gt=0, le=3650)


def positive_setting(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
        if value <= 0:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f'{name} must be a positive integer') from exc
    return value


def create_app(manifest_path: Path | None = None, data_dir: Path | None = None,
               import_dir: Path | None = None) -> FastAPI:
    load_dotenv(ROOT / '.env')
    manifest_path = manifest_path or configured_path('PLANET_X_MANIFEST', 'data/manifests/spherex-dr1.json')
    data_dir = data_dir or configured_path('PLANET_X_DATA_DIR', 'data/samples')
    import_dir = import_dir or Path(os.environ.get('PLANET_X_IMPORT_DIR', data_dir / 'imports'))
    import_quota = ImportQuota(import_dir, positive_setting('PLANET_X_IMPORT_QUOTA_BYTES', DEFAULT_IMPORT_QUOTA_BYTES))
    cube_dir = Path(os.environ.get('PLANET_X_CUBE_CACHE_DIR', import_dir / 'cubes'))
    cube_revision_name = os.environ.get('PLANET_X_DR1_CUBE_REVISION', DEFAULT_DR1_REVISION)
    cube_cache = CubeCache(cube_dir, positive_setting('PLANET_X_CUBE_CACHE_BYTES', DEFAULT_CACHE_BYTES), cube_revision_name)

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

    @api.get('/api/ready')
    def ready():
        manifest = api.state.manifest
        products = [*manifest.observations, *manifest.cubes]
        missing = [item.epoch for item in products if not (data_dir / item.filename).is_file()]
        if missing:
            raise DataError('data_unavailable', 'Manifest data has not been prepared', 503, details={'epochs': missing})
        return {'status': 'ready', 'products': len(products)}

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

    @api.get('/api/targets')
    def targets(mjd: TargetDate = DEFAULT_TARGET_MJD):
        return {'targets': [target.metadata(mjd) for target in TARGETS.values()]}

    @api.get('/api/catalog/{catalog}')
    def catalog_overlay(catalog: Overlay, ra: RightAscension, dec: Declination,
                        radius_deg: Annotated[float, Query(gt=0, le=1)] = 0.05,
                        limit: Annotated[int, Query(ge=1, le=200)] = 100):
        return query_overlay(catalog, ra, dec, radius_deg, limit)

    @api.get('/api/targets/{target_id}/observations')
    def target_observations(target_id: str, release: ArchiveRelease = 'DR1',
                            start_mjd: TargetDate | None = None, end_mjd: TargetDate | None = None,
                            wavelength_um: Annotated[float, Query(gt=0, le=10)] | None = None,
                            limit: Annotated[int, Query(ge=1, le=100)] = 30):
        target = get_target(target_id)
        supplied_times = [time for time in (start_mjd, end_mjd) if time is not None]
        center_mjd = sum(supplied_times) / len(supplied_times) if supplied_times else DEFAULT_TARGET_MJD
        center = target.position(center_mjd)
        archive = search_images(
            release=release, ra=center.ra.deg, dec=center.dec.deg, radius_deg=0.015, limit=limit,
            wavelength_um=wavelength_um, start_mjd=start_mjd, end_mjd=end_mjd,
            local_observations=[],
        )
        local = defaultdict(list)
        for observation, directory in [*((item, data_dir) for item in api.state.manifest.observations),
                                       *list_imports(import_dir)]:
            if observation.release == release and (directory / observation.filename).is_file():
                local[observation.observation_id, observation.band].append((observation, directory))
        observations = []
        for item in sorted(archive.observations, key=lambda item: item.observation_start_mjd or float('inf')):
            record = item.model_dump(mode='json')
            if item.observation_start_mjd is not None and item.observation_end_mjd is not None:
                mjd = (item.observation_start_mjd + item.observation_end_mjd) / 2
                position = target.position(mjd)
                record['predicted_position'] = {'ra': position.ra.deg, 'dec': position.dec.deg, 'mjd': mjd}
                record['epoch'] = covered_target_epoch(position, local.get((item.observation_id, item.band), []))
                record['available_locally'] = record['epoch'] is not None
            else:
                record['predicted_position'] = None
            observations.append(record)
        return {'target': target.metadata(center_mjd), 'archive': archive.model_dump(exclude={'observations'}),
                'observations': observations}

    @api.post('/api/archive/import', status_code=201, responses={
        200: {'description': 'Existing cutout'}, 507: {'description': 'Imported exposure storage quota exceeded'},
    })
    def archive_import(request: ImportRequest, response: Response):
        observation, directory, created = import_exposure(import_quota, request)
        response.status_code = 201 if created else 200
        return observation.metadata(directory)

    def compare_observations(position: Position, mode: Mode, first, second):
        a, directory_a = first
        b, directory_b = second
        image_a, image_b = read_image(directory_a, a), read_image(directory_b, b)
        result = compare(position, mode, a, b, image_a, image_b)
        result['epochs'] = {'a': a.metadata(directory_a) | {'fits': image_a.metadata},
                            'b': b.metadata(directory_b) | {'fits': image_b.metadata}}
        return result

    @api.get('/api/compare')
    def compare_epochs(ra: RightAscension, dec: Declination, fov: Fov, epoch_a: Epoch, epoch_b: Epoch,
                       mode: Mode = 'difference'):
        return compare_observations(Position(ra=ra, dec=dec, fov=fov), mode,
                                    require_observation(epoch_a), require_observation(epoch_b))

    @api.post('/api/compare/auto')
    def compare_automatically(request: AutoCompareRequest):
        if len(set(request.epochs)) != len(request.epochs):
            raise DataError('invalid_request', 'Each epoch must be specified once')
        observations = sorted((require_observation(epoch) for epoch in request.epochs),
                              key=lambda item: item[0].observation_start_mjd)
        pairs = []
        for first, second in combinations(observations, 2):
            a, b = first[0], second[0]
            gap = b.observation_start_mjd - a.observation_start_mjd
            if (gap >= request.min_gap_days and a.observation_id != b.observation_id
                    and (a.source, a.band, a.detector, a.calibration) == (b.source, b.band, b.detector, b.calibration)):
                pairs.append((gap, first, second))
        attempts = []
        for gap, first, second in sorted(pairs, key=lambda item: item[0], reverse=True)[:6]:
            try:
                result = compare_observations(request, 'difference', first, second)
            except DataError as exc:
                attempts.append({'epoch_a': first[0].epoch, 'epoch_b': second[0].epoch, 'error': exc.code})
                continue
            result['selection'] = {'elapsed_days': gap, 'candidate_pairs': len(pairs), 'rejected_pairs': attempts}
            return result
        raise DataError('no_compatible_pair', 'No pair passed the time, calibration, and image compatibility checks', 422,
                        details={'candidate_pairs': len(pairs), 'attempts': attempts})

    def get_cube(epoch: str) -> Cube:
        cube = api.state.cubes.get(epoch)
        if cube is None:
            if lookup_observation(epoch) is not None:
                raise DataError('spectrum_unavailable', 'This exposure has no calibrated channel cube. See /api/datasets.', 409)
            raise DataError('unknown_epoch', f"No cube epoch '{epoch}'", 404)
        return cube

    @contextmanager
    def resolve_cube(epoch: str | None, ra: float, dec: float):
        if epoch is None:
            tile = tile_at(ra, dec)
            for cube in api.state.cubes.values():
                if (cube.release == 'DR1' and cube.observation_id == f'Npix{tile}_cube'
                        and f'/{cube_revision_name}/' in str(cube.access)
                        and (data_dir / cube.filename).is_file()):
                    yield data_dir, cube
                    return
        elif epoch in api.state.cubes:
            yield data_dir, get_cube(epoch)
            return
        else:
            tile = tile_from_epoch(epoch)
            if tile is None:
                yield data_dir, get_cube(epoch)
                return
        with cube_cache.open(tile) as resolved:
            yield resolved

    @api.get('/api/photometry')
    def photometry_at(ra: RightAscension, dec: Declination, epoch: Epoch) -> Photometry:
        if epoch in api.state.cubes:
            raise DataError('photometry_unavailable', 'Source photometry requires a single exposure epoch', 409)
        observation, directory = require_observation(epoch)
        return measure_source(directory, observation, ra, dec)

    @api.post('/api/source-series')
    def get_source_series(request: SourceSeriesRequest):
        return source_series(request, require_observation)

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
    def spectrum_at(ra: RightAscension, dec: Declination, epoch: Epoch | None = None):
        with resolve_cube(epoch, ra, dec) as (directory, cube):
            if directory == data_dir:
                return cached_spectrum(cube.epoch, ra, dec, cube_revision(cube))
            return spectrum(directory, cube, ra, dec)

    @api.get('/api/layers')
    def list_layers(epoch: Epoch):
        with resolve_cube(epoch, 0, 0) as (directory, cube):
            return layers(directory, cube)

    @api.get('/api/layers/{detector}')
    def layer_at(detector: Annotated[int, RoutePath(ge=1, le=6)], ra: RightAscension, dec: Declination,
                 fov: Fov, epoch: Epoch | None = None, channel: Annotated[int, Query(ge=1, le=17)] = 9):
        with resolve_cube(epoch, ra, dec) as (directory, cube):
            if directory == data_dir:
                return cached_layer(cube.epoch, ra, dec, fov, detector, channel, cube_revision(cube))
            return detector_layer(directory, cube, Position(ra=ra, dec=dec, fov=fov), detector, channel)

    return api


app = create_app()


def run():
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('PLANET_X_PORT', '8765')))
