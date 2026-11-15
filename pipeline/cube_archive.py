import hashlib
import re
import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from time import monotonic

from astropy import units as u
from astropy.io import fits
from astropy_healpix import HEALPix
from requests import get

from pipeline.archive import irsa_timeouts, retry_irsa
from pipeline.catalog import Cube, DataError, Position
from pipeline.import_storage import QUOTA_ERROR, ImportQuota, file_write_lock
from pipeline.spectra import open_cube

HEALPIX = HEALPix(nside=32, order="nested", frame="icrs")
DR1_ROOT = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/dr1/hips5_cube"
DEFAULT_DR1_REVISION = "hips_20261026"
TILE_EPOCH = re.compile(r"dr1-npix(0|[1-9][0-9]{0,4})")
FILENAME = "cube.fits"
METADATA = "cube.json"
DEFAULT_CACHE_BYTES = 2 * 1024**3
MAX_CUBE_BYTES = 512 * 1024**2


def tile_at(ra: float, dec: float) -> int:
    return int(HEALPIX.lonlat_to_healpix(ra * u.deg, dec * u.deg))


def tile_from_epoch(epoch: str) -> int | None:
    match = TILE_EPOCH.fullmatch(epoch)
    if match is None:
        return None
    tile = int(match[1])
    return tile if tile < HEALPIX.npix else None


class CubeCache:
    def __init__(self, directory: Path, limit_bytes: int, revision: str = DEFAULT_DR1_REVISION):
        if not re.fullmatch(r"hips_[0-9]{8}", revision):
            raise ValueError("PLANET_X_DR1_CUBE_REVISION must have format hips_YYYYMMDD")
        self.directory = directory if revision == DEFAULT_DR1_REVISION else directory / revision
        self.revision = revision
        self.quota = ImportQuota(self.directory, limit_bytes, epoch_pattern=TILE_EPOCH, filenames=(FILENAME, METADATA))

    def _lock_path(self, epoch: str) -> Path:
        return self.directory / ".locks" / f"{epoch}.sqlite3"

    def _make_space(self, additional_bytes: int):
        """Reserve room while the cache quota lock is held."""
        if additional_bytes > self.quota.limit_bytes:
            raise DataError("cube_cache_full", "The archive cube exceeds the configured cache size", 507)
        candidates = sorted(
            (path for path in self.directory.resolve().iterdir()
             if TILE_EPOCH.fullmatch(path.name) and path.is_dir() and path.resolve() == path),
            key=lambda path: path.stat().st_mtime_ns,
        )
        for candidate in [*candidates, None]:
            try:
                self.quota.check_space(additional_bytes)
                return
            except DataError as exc:
                if exc.code != QUOTA_ERROR:
                    raise
                if candidate is None:
                    raise DataError("cube_cache_full", "No space is available for the archive cube", 507,
                                    details=exc.details) from exc
            try:
                with file_write_lock(self._lock_path(candidate.name), timeout=0):
                    shutil.rmtree(candidate)
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                    raise

    def _fetch(self, tile: int, pending: Path) -> Cube:
        url = f"{DR1_ROOT}/{self.revision}/Norder5/Dir{tile // 10000 * 10000}/Npix{tile}_cube.fits"

        def download(deadline):
            digest = hashlib.sha256()
            received = 0
            with get(url, stream=True, allow_redirects=False, timeout=irsa_timeouts(deadline, 25),
                     headers={"Accept-Encoding": "identity"}) as response:
                if response.status_code == 404:
                    raise DataError("outside_coverage", "IRSA has no DR1 cube for this tile", 404)
                response.raise_for_status()
                try:
                    size = int(response.headers.get("Content-Length", "0"))
                except ValueError:
                    size = 0
                if response.status_code != 200 or not 0 < size <= MAX_CUBE_BYTES or size % 2880:
                    raise DataError("invalid_archive_fits", "IRSA returned an invalid FITS cube size", 502)
                with (pending / FILENAME).open("wb") as output:
                    with self.quota.write_lock():
                        self._make_space(size)
                        output.truncate(size)
                    for chunk in response.iter_content(chunk_size=1024**2):
                        if monotonic() > deadline:
                            raise DataError("archive_timeout", "IRSA took too long to deliver the cube", 504)
                        received += len(chunk)
                        if received > size:
                            raise DataError("invalid_archive_fits", "IRSA cube exceeded its declared size", 502)
                        output.write(chunk)
                        digest.update(chunk)
            if received != size:
                raise DataError("invalid_archive_fits", "IRSA returned an incomplete FITS cube", 502)
            return size, digest.hexdigest()

        size, digest = retry_irsa(download, budget=240)
        center = HEALPIX.healpix_to_skycoord(tile)
        try:
            with fits.open(pending / FILENAME, memmap=True) as hdus:
                if hdus["IMAGE"].header.get("NPIX") != tile:
                    raise ValueError("FITS tile number does not match the requested HEALPix index")
                start = hdus[0].header["MJD-BEG"]
                end = hdus[0].header["MJD-END"]
            cube = Cube(
                epoch=pending.name, source="NASA/IPAC IRSA SPHEREx", release="DR1",
                observation_id=f"Npix{tile}_cube", observation_start_mjd=start, observation_end_mjd=end, access=url,
                size_bytes=size, sha256=digest, filename=FILENAME, calibration="SPHEREx DR1 All-Sky Cube",
                processing_history=["SPHEREx DR1 cross-epoch mosaic", f"Order 5 HEALPix tile {tile}"],
                coverage=Position(ra=center.ra.deg, dec=center.dec.deg, fov=HEALPIX.pixel_area.to_value(u.deg**2)**0.5),
                flags="NHITS and FLAGS extensions. Zero hits or non-finite brightness masks a channel. Other flags are reported.",
            )
            with open_cube(pending, cube):
                pass
        except (DataError, KeyError, OSError, ValueError) as exc:
            raise DataError("invalid_archive_fits", "IRSA returned an invalid DR1 cube", 502) from exc
        return cube

    @contextmanager
    def open(self, tile: int):
        epoch = f"dr1-npix{tile}"
        target = self.directory / epoch
        try:
            self._lock_path(epoch).parent.mkdir(parents=True, exist_ok=True)
            with file_write_lock(self._lock_path(epoch), timeout=1):
                try:
                    cube = Cube.model_validate_json((target / METADATA).read_bytes())
                except FileNotFoundError:
                    # One cold download can reserve disk space at a time across workers.
                    with file_write_lock(self.directory / ".fetch.sqlite3", timeout=0):
                        with self.quota.staging(minimum_bytes=0) as stage:
                            pending = stage / epoch
                            pending.mkdir()
                            cube = self._fetch(tile, pending)
                            metadata = cube.model_dump_json().encode()
                            with self.quota.write_lock():
                                self._make_space(len(metadata))
                                (pending / METADATA).write_bytes(metadata)
                                pending.rename(target)
                if cube.filename != FILENAME or cube.epoch != epoch:
                    raise ValueError("Cube cache entry does not match its index")
                target.touch()
                yield target, cube
        except sqlite3.OperationalError as exc:
            if exc.sqlite_errorcode == sqlite3.SQLITE_BUSY:
                raise DataError("cube_busy", "Another request is preparing an archive cube. Retry shortly.", 503) from exc
            raise DataError("cube_cache_unavailable", "Could not lock the archive cube cache", 503) from exc
        except (OSError, ValueError) as exc:
            raise DataError("cube_cache_unavailable", "Could not access the archive cube cache", 503) from exc
