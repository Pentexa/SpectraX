import hashlib
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.parse import urlsplit

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.wcs import NoConvergence
from pydantic import ConfigDict, Field, FiniteFloat, ValidationError
from requests import get

from pipeline.archive import find_image, irsa_timeouts, retry_irsa
from pipeline.catalog import DataError, Observation, Position
from pipeline.images import read_fits_image

ARCHIVE_ID = re.compile(r"^ivo://irsa\.ipac/spherex_(dr1|qr3)\?([A-Za-z0-9_]{1,50})/D([1-6])$")
IMPORTED_EPOCH = re.compile(r"^irsa-[a-f0-9]{64}$")
IRSA_HOST = "irsa.ipac.caltech.edu"
MAX_SIZE = 32 * 1024**2
REJECT_FLAG_BITS = 0xFFFFFFFF ^ (1 << 21)
METADATA = "observation.json"
FILENAME = "cutout.fits"


class ImportRequest(Position):
    model_config = ConfigDict(extra="forbid")

    archive_id: str = Field(pattern=ARCHIVE_ID.pattern)
    fov: FiniteFloat = Field(ge=0.02, le=0.2, description="Square cutout width in degrees")


def get_import(directory: Path, epoch: str) -> tuple[Observation, Path] | None:
    if not IMPORTED_EPOCH.fullmatch(epoch):
        return None
    target = directory / epoch
    try:
        observation = Observation.model_validate_json((target / METADATA).read_bytes())
    except FileNotFoundError:
        return None
    except (OSError, ValidationError) as exc:
        raise DataError("import_storage_unavailable", "Could not read the imported exposure catalog", 503) from exc
    if observation.epoch != epoch or observation.filename != FILENAME:
        raise DataError("import_storage_unavailable", "Imported exposure catalog entry is inconsistent", 503)
    return observation, target


def list_imports(directory: Path) -> list[tuple[Observation, Path]]:
    try:
        return [item for path in sorted(directory.iterdir()) if (item := get_import(directory, path.name))]
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise DataError("import_storage_unavailable", "Could not list imported exposures", 503) from exc


def _cutout_url(row, release: str, obs_id: str, detector: int, request: ImportRequest) -> tuple[str, str]:
    # Limit downloads to the canonical IRSA Level 2 path for this observation.
    try:
        url = urlsplit(str(row["access_url"]))
    except ValueError as exc:
        raise DataError("invalid_archive_response", "IRSA returned an invalid image URL", 502) from exc
    pattern = (rf"/ibe/data/spherex/{release}/level2/[A-Za-z0-9_]+/"
               rf"(l2b-v(\d+)-\d{{4}}-\d{{3}})/{detector}/level2_{obs_id}D{detector}_spx_\1\.fits")
    match = re.fullmatch(pattern, url.path)
    if url.scheme != "https" or url.netloc != IRSA_HOST or match is None or url.query or url.fragment:
        raise DataError("invalid_archive_response", "IRSA returned an unexpected image URL", 502)
    return f"https://{IRSA_HOST}{url.path}?center={request.ra},{request.dec}&size={request.fov}", match[2]


def _download_cutout(url: str, path: Path) -> tuple[int, str]:
    def download(deadline):
        digest = hashlib.sha256()
        size = 0
        with get(url, timeout=irsa_timeouts(deadline, 25), stream=True, allow_redirects=False,
                 headers={"Accept-Encoding": "identity"}) as response:
            if response.status_code in (400, 404, 416, 422):
                raise DataError("cutout_unavailable", "IRSA could not cut out this position from the exposure", 422)
            response.raise_for_status()
            if response.status_code != 200:
                raise DataError("archive_unavailable", "IRSA could not deliver the cutout", 502)
            with path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=65536):
                    if monotonic() > deadline:
                        raise DataError("archive_timeout", "IRSA took too long to deliver the cutout", 504)
                    size += len(chunk)
                    if size > MAX_SIZE:
                        raise DataError("invalid_archive_fits", "IRSA cutout exceeds the file size limit", 502)
                    output.write(chunk)
                    digest.update(chunk)
        return size, digest.hexdigest()

    return retry_irsa(download, budget=60)


def _observation(request: ImportRequest, epoch: str, path: Path) -> Observation:
    release, obs_id, detector_value = ARCHIVE_ID.fullmatch(request.archive_id).groups()
    detector = int(detector_value)
    band = f"SPHEREx-D{detector}"
    release_id = release.upper()
    row = find_image(release_id, request.archive_id, request.ra, request.dec)
    if row["obs_id"] != obs_id or row["energy_bandpassname"] != band:
        raise DataError("invalid_archive_response", "IRSA returned inconsistent observation metadata", 502)
    url, calibration = _cutout_url(row, release, obs_id, detector, request)
    size, digest = _download_cutout(url, path)
    try:
        image = read_fits_image(path, "spherex-lvf", REJECT_FLAG_BITS)
        start = image.metadata["start_mjd"]
        end = image.metadata["end_mjd"]
        if (image.metadata["product_id"] != obs_id or image.metadata["detector"] != detector
                or np.ma.is_masked(row["t_min"]) or np.ma.is_masked(row["t_max"])
                or end is None or not np.allclose([start, end], [float(row["t_min"]), float(row["t_max"])],
                                                  atol=1 / 86400, rtol=0)
                or image.variance is None or "EPSF" not in image.metadata["quality_hdus"]):
            raise ValueError("The cutout metadata differs from the archive or is incomplete")
        x, y = image.wcs.world_to_pixel(SkyCoord(request.ra, request.dec, unit="deg", frame="icrs"))
    except (DataError, TypeError, ValueError) as exc:
        raise DataError("invalid_archive_fits", "IRSA returned an invalid spectral image cutout", 502) from exc
    except NoConvergence as exc:
        raise DataError("outside_coverage", "The requested center could not be mapped into the cutout", 422) from exc
    height, width = image.signal.shape
    if not (-0.5 <= x < width - 0.5 and -0.5 <= y < height - 0.5) or not image.valid.any():
        raise DataError("outside_coverage", "The cutout has no usable coverage for the requested center", 422)
    return Observation(
        epoch=epoch, source="NASA/IPAC IRSA SPHEREx", release=release_id, observation_id=obs_id,
        access=url, filename=FILENAME, size_bytes=size, sha256=digest, observation_start_mjd=start,
        observation_end_mjd=end, band=band, detector=detector, spectral_wcs="spherex-lvf",
        coverage=Position(ra=request.ra, dec=request.dec, fov=request.fov),
        calibration=f"SPHEREx {release_id} Level 2B v{calibration}",
        processing_history=["SPHEREx Level 2B calibration", "IRSA cutout"],
        flags="FLAGS extension. SOURCE (bit 21) is allowed. All other set bits are masked.",
        reject_flag_bits=REJECT_FLAG_BITS,
    )


def import_exposure(directory: Path, request: ImportRequest) -> tuple[Observation, Path, bool]:
    coordinates = (request.ra + 0.0, request.dec + 0.0, request.fov)
    epoch = "irsa-" + hashlib.sha256(f"{request.archive_id}:{coordinates}".encode()).hexdigest()
    existing = get_import(directory, epoch)
    if existing is not None:
        return existing[0], existing[1], False
    target = directory / epoch
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".download-", dir=directory) as staging:
            # The sibling rename publishes metadata and FITS together, also
            # when two ASGI workers request the same cutout concurrently.
            pending = Path(staging) / epoch
            pending.mkdir()
            observation = _observation(request, epoch, pending / FILENAME)
            (pending / METADATA).write_text(observation.model_dump_json(), encoding="utf-8")
            try:
                pending.rename(target)
            except OSError:
                existing = get_import(directory, epoch)
                if existing is not None:
                    return existing[0], existing[1], False
                raise
    except OSError as exc:
        raise DataError("import_storage_unavailable", "Could not write the imported exposure", 503) from exc
    return observation, target, True
