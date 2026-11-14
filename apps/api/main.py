import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Path as RoutePath, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipeline.catalog import Cube, DataError, Position, data_path, load_manifest
from pipeline.compare import Mode, compare
from pipeline.images import read_image
from pipeline.ingest import ROOT, configured_path
from pipeline.spectra import detector_layer, layers, spectrum

Epoch = Annotated[str, Query(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")]
RightAscension = Annotated[float, Query(ge=0, lt=360, description="ICRS right ascension in degrees")]
Declination = Annotated[float, Query(ge=-90, le=90, description="ICRS declination in degrees")]
Fov = Annotated[float, Query(gt=0, le=1, description="Square cutout width in degrees")]


def create_app(manifest_path: Path | None = None, data_dir: Path | None = None) -> FastAPI:
    load_dotenv(ROOT / '.env')
    manifest_path = manifest_path or configured_path('PLANET_X_MANIFEST', 'data/manifests/spherex-dr1.json')
    data_dir = data_dir or configured_path('PLANET_X_DATA_DIR', 'data/samples')

    @asynccontextmanager
    async def lifespan(api: FastAPI):
        manifest = load_manifest(manifest_path)
        api.state.observations = {record.epoch: record for record in manifest.observations}
        api.state.cubes = {record.epoch: record for record in manifest.cubes}
        yield

    api = FastAPI(title='Planet X SPHEREx API', version='0.1.0', lifespan=lifespan)
    origins = os.environ.get('PLANET_X_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    api.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in origins.split(',') if origin.strip()],
                       allow_methods=['GET'], allow_headers=['Accept', 'Content-Type'])

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

    @api.get('/api/health')
    def health():
        products = [*api.state.observations.values(), *api.state.cubes.values()]
        return {'status': 'ok', 'products': len(products),
                'available_locally': sum((data_dir / product.filename).is_file() for product in products)}

    @api.get('/api/datasets')
    def datasets():
        return {'observations': [entry.metadata(data_dir) for entry in api.state.observations.values()],
                'cubes': [entry.metadata(data_dir) for entry in api.state.cubes.values()]}

    @api.get('/api/compare')
    def compare_epochs(ra: RightAscension, dec: Declination, fov: Fov, epoch_a: Epoch, epoch_b: Epoch,
                       mode: Mode = 'difference'):
        try:
            a = api.state.observations[epoch_a]
            b = api.state.observations[epoch_b]
        except KeyError as exc:
            raise DataError('unknown_epoch', f"No image epoch '{exc.args[0]}'", 404) from exc
        image_a, image_b = read_image(data_dir, a), read_image(data_dir, b)
        result = compare(Position(ra=ra, dec=dec, fov=fov), mode, a, b, image_a, image_b)
        result['epochs'] = {'a': a.metadata(data_dir) | {'fits': image_a.metadata},
                            'b': b.metadata(data_dir) | {'fits': image_b.metadata}}
        return result

    def get_cube(epoch: str) -> Cube:
        cube = api.state.cubes.get(epoch)
        if cube is None:
            if epoch in api.state.observations:
                raise DataError('spectrum_unavailable', 'This exposure has no calibrated channel cube. See /api/datasets.', 409)
            raise DataError('unknown_epoch', f"No cube epoch '{epoch}'", 404)
        return cube

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
