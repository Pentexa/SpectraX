from functools import partial
from math import isfinite
from pathlib import Path
from typing import Literal

from astroquery.ipac.irsa import IrsaClass
from numpy.ma import is_masked
from pydantic import BaseModel, HttpUrl
from pyvo.dal import DALAccessError, SIA2Service
from requests.exceptions import RequestException, Timeout

from pipeline.catalog import DataError, Observation

ArchiveRelease = Literal["DR1", "QR3"]
REQUIRED_COLUMNS = {"obs_id", "obs_publisher_did", "obs_collection", "access_url", "energy_bandpassname",
                    "t_min", "t_max", "em_min", "em_max"}


class ArchiveObservation(BaseModel):
    archive_id: str
    observation_id: str
    band: str
    fits_url: HttpUrl
    observation_start_mjd: float | None
    observation_end_mjd: float | None
    wavelength_min_um: float | None
    wavelength_max_um: float | None
    epoch: str | None
    available_locally: bool


class ArchiveSearch(BaseModel):
    source: Literal["NASA/IPAC IRSA"] = "NASA/IPAC IRSA"
    release: ArchiveRelease
    collection: str
    has_more: bool
    observations: list[ArchiveObservation]


def _number(value, scale: float = 1.0) -> float | None:
    if is_masked(value):
        return None
    number = float(value) * scale
    return number if isfinite(number) else None


def _query_sia(collection: str, position: tuple[float, float, float], limit: int,
               wavelength_um: float | None, time_range: str | None):
    archive = IrsaClass()
    with archive._session as session:
        # PyVO submits its own requests. Apply a per-client timeout and use
        # IRSA's published SIA2 query URL directly, without capability discovery.
        session.request = partial(session.request, timeout=(5, 15))
        archive._sia = SIA2Service(archive.sia_url, session=session, check_baseurl=False)
        constraints = {"TIME": time_range} if time_range is not None else {}
        band = wavelength_um * 1e-6 if wavelength_um is not None else None
        return archive.query_sia(pos=position, collection=collection, maxrec=limit + 1, band=band, **constraints)


def search_images(*, release: ArchiveRelease, ra: float, dec: float, radius_deg: float, limit: int,
                  wavelength_um: float | None, start_mjd: float | None, end_mjd: float | None,
                  local_observations: list[Observation], data_dir: Path) -> ArchiveSearch:
    if start_mjd is not None and end_mjd is not None and start_mjd > end_mjd:
        raise DataError("invalid_time_range", "start_mjd must be less than or equal to end_mjd")
    time_range = None
    if start_mjd is not None or end_mjd is not None:
        lower = start_mjd if start_mjd is not None else "-Inf"
        upper = end_mjd if end_mjd is not None else "+Inf"
        time_range = f"{lower} {upper}"
    collection = f"spherex_{release.lower()}"
    try:
        table = _query_sia(collection, (ra, dec, radius_deg), limit, wavelength_um, time_range)
    except (DALAccessError, RequestException) as exc:
        cause = getattr(exc, "cause", None)
        if isinstance(exc, Timeout) or isinstance(cause, Timeout):
            raise DataError("archive_timeout", "The IRSA archive took too long to respond", 504) from exc
        raise DataError("archive_unavailable", "The IRSA archive could not complete the search", 502) from exc

    if not REQUIRED_COLUMNS.issubset(table.colnames):
        raise DataError("invalid_archive_response", "IRSA returned an unexpected image catalog", 502)
    local = {(item.observation_id, item.band): item for item in local_observations if item.release == release}
    observations = []
    for row in table[:limit]:
        try:
            if row["obs_collection"] != collection:
                raise ValueError("Unexpected collection")
            names = [row[name] for name in ("obs_publisher_did", "obs_id", "energy_bandpassname")]
            if any(is_masked(value) or not str(value).strip() for value in names):
                raise ValueError("Missing observation metadata")
            archive_id, observation_id, band = map(str, names)
            product = local.get((observation_id, band))
            observations.append(ArchiveObservation(
                archive_id=archive_id, observation_id=observation_id, band=band, fits_url=row["access_url"],
                observation_start_mjd=_number(row["t_min"]), observation_end_mjd=_number(row["t_max"]),
                wavelength_min_um=_number(row["em_min"], 1e6), wavelength_max_um=_number(row["em_max"], 1e6),
                epoch=product.epoch if product else None,
                available_locally=product is not None and (data_dir / product.filename).is_file(),
            ))
        except (TypeError, ValueError) as exc:
            raise DataError("invalid_archive_response", "IRSA returned invalid observation metadata", 502) from exc
    return ArchiveSearch(release=release, collection=collection, has_more=len(table) > limit, observations=observations)
