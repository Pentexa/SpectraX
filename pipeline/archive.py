from collections.abc import Callable
from contextlib import ExitStack
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
from pathlib import Path
from time import monotonic, sleep
from typing import Literal, TypeVar

from astroquery.ipac.irsa import IrsaClass
from numpy.ma import is_masked
from pydantic import BaseModel, HttpUrl
from pyvo.dal import DALAccessError, SIA2Service
from requests.exceptions import ChunkedEncodingError, ConnectionError, RequestException, SSLError, Timeout
from urllib3.exceptions import ProtocolError, ReadTimeoutError

from pipeline.catalog import DataError, Observation

ArchiveRelease = Literal["DR1", "QR3"]
REQUIRED_COLUMNS = {"obs_id", "obs_publisher_did", "obs_collection", "access_url", "energy_bandpassname",
                    "t_min", "t_max", "em_min", "em_max"}
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
RETRY_DELAYS = (0.25, 0.5)
MAX_RETRY_AFTER = 5.0
Result = TypeVar("Result")


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


def _retry_after(value: str | None) -> float:
    if value is None:
        return 0
    try:
        if value.isascii() and value.isdecimal():
            return int(value)
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return max(0, (date - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return 0


def irsa_timeouts(deadline: float, read_timeout: float) -> tuple[float, float]:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise DataError("archive_timeout", "The IRSA archive took too long to respond", 504)
    connect = min(5, remaining / 2)
    return connect, min(read_timeout, remaining - connect)


def retry_irsa(operation: Callable[[float], Result], *, budget: float) -> Result:
    """Retry an IRSA GET within its request budget, starting each attempt from scratch."""
    deadline = monotonic() + budget
    for delay in (*RETRY_DELAYS, None):
        try:
            return operation(deadline)
        except (DALAccessError, RequestException, ProtocolError, ReadTimeoutError) as exc:
            cause = getattr(exc, "cause", None) or exc
            response = getattr(cause, "response", None)
            status = response.status_code if response is not None else getattr(exc, "code", None)
            # Requests wraps timeouts during iter_content in ConnectionError.
            timed_out = status in (408, 504) or isinstance(cause, (Timeout, ReadTimeoutError)) or (
                isinstance(cause, ConnectionError) and bool(cause.args)
                and isinstance(cause.args[0], ReadTimeoutError)
            )
            network_failure = isinstance(
                cause, (Timeout, ConnectionError, ChunkedEncodingError, ProtocolError, ReadTimeoutError)
            ) and not isinstance(cause, SSLError)
            retryable = status in RETRYABLE_STATUS or (status in (None, 0) and network_failure)
            wait = _retry_after(response.headers.get("Retry-After")) if response is not None else 0
            if retryable and delay is not None and wait <= MAX_RETRY_AFTER:
                wait = max(delay, wait)
                if wait < deadline - monotonic():
                    sleep(wait)
                    continue
            if timed_out:
                raise DataError("archive_timeout", "The IRSA archive took too long to respond", 504) from exc
            raise DataError("archive_unavailable", "The IRSA archive could not complete the request", 502) from exc


def _number(value, scale: float = 1.0) -> float | None:
    if is_masked(value):
        return None
    number = float(value) * scale
    return number if isfinite(number) else None


def _query_sia(collection: str, *, maxrec: int, position: tuple[float, float, float] | None = None,
               wavelength_um: float | None = None, time_range: str | None = None,
               archive_id: str | None = None):
    constraints = {"TIME": time_range} if time_range is not None else {}
    band = wavelength_um * 1e-6 if wavelength_um is not None else None

    def query(deadline):
        archive = IrsaClass()
        with archive._session as session, ExitStack() as responses:
            timeout = irsa_timeouts(deadline, 15)
            send = session.request

            def request(*args, **kwargs):
                response = responses.enter_context(send(*args, timeout=timeout, **kwargs))
                response.raise_for_status()
                return response

            # Check HTTP status before PyVO reads the VOTable.
            session.request = request
            archive._sia = SIA2Service(archive.sia_url, session=session, check_baseurl=False)
            return archive.query_sia(pos=position, collection=collection, maxrec=maxrec, band=band,
                                     publisher_did=archive_id, **constraints)

    table = retry_irsa(query, budget=30)
    if not REQUIRED_COLUMNS.issubset(table.colnames):
        raise DataError("invalid_archive_response", "IRSA returned an unexpected image catalog", 502)
    return table


def find_image(release: ArchiveRelease, archive_id: str, ra: float, dec: float):
    collection = f"spherex_{release.lower()}"
    # Bound IRSA's catalog lookup to the requested cutout center.
    table = _query_sia(collection, maxrec=2, position=(ra, dec, 0.001), archive_id=archive_id)
    if len(table) == 0:
        raise DataError("unknown_archive_image", "IRSA has no matching image at the requested position", 404)
    if len(table) != 1 or table[0]["obs_publisher_did"] != archive_id or table[0]["obs_collection"] != collection:
        raise DataError("invalid_archive_response", "IRSA did not return a unique matching image", 502)
    return table[0]


def search_images(*, release: ArchiveRelease, ra: float, dec: float, radius_deg: float, limit: int,
                  wavelength_um: float | None, start_mjd: float | None, end_mjd: float | None,
                  local_observations: list[tuple[Observation, Path]]) -> ArchiveSearch:
    if start_mjd is not None and end_mjd is not None and start_mjd > end_mjd:
        raise DataError("invalid_time_range", "start_mjd must be less than or equal to end_mjd")
    time_range = None
    if start_mjd is not None or end_mjd is not None:
        lower = start_mjd if start_mjd is not None else "-Inf"
        upper = end_mjd if end_mjd is not None else "+Inf"
        time_range = f"{lower} {upper}"
    collection = f"spherex_{release.lower()}"
    table = _query_sia(collection, maxrec=limit + 1, position=(ra, dec, radius_deg),
                       wavelength_um=wavelength_um, time_range=time_range)
    local = {}
    for item, directory in local_observations:
        if item.release == release:
            key = (item.observation_id, item.band)
            available = (directory / item.filename).is_file()
            if key not in local or (available and not local[key][1]):
                local[key] = (item.epoch, available)
    observations = []
    for row in table[:limit]:
        try:
            if row["obs_collection"] != collection:
                raise ValueError("Unexpected collection")
            names = [row[name] for name in ("obs_publisher_did", "obs_id", "energy_bandpassname")]
            if any(is_masked(value) or not str(value).strip() for value in names):
                raise ValueError("Missing observation metadata")
            archive_id, observation_id, band = map(str, names)
            epoch, available = local.get((observation_id, band), (None, False))
            observations.append(ArchiveObservation(
                archive_id=archive_id, observation_id=observation_id, band=band, fits_url=row["access_url"],
                observation_start_mjd=_number(row["t_min"]), observation_end_mjd=_number(row["t_max"]),
                wavelength_min_um=_number(row["em_min"], 1e6), wavelength_max_um=_number(row["em_max"], 1e6),
                epoch=epoch, available_locally=available,
            ))
        except (TypeError, ValueError) as exc:
            raise DataError("invalid_archive_response", "IRSA returned invalid observation metadata", 502) from exc
    return ArchiveSearch(release=release, collection=collection, has_more=len(table) > limit, observations=observations)
