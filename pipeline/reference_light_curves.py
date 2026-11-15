from csv import DictReader
from functools import lru_cache
from io import StringIO
from math import isfinite
from time import monotonic
from typing import Literal
from xml.etree import ElementTree

from requests import get

from pipeline.archive import irsa_timeouts, retry_irsa
from pipeline.catalog import DataError

ReferenceBand = Literal["V", "Vis."]
VSX_URL = "https://vsx.aavso.org/index.php"
VARIABLES = {"r-draconis": "000-BBX-660", "rw-aurigae": "000-BBH-936"}
JD_OFFSET = 2_400_000.5
MAX_BYTES = 1024 * 1024
EXPECTED_COLUMNS = {"JD", "mag", "uncert", "band", "by", "fainterThan", "obsType"}


def _points(payload: bytes, auid: str, band: ReferenceBand, start_mjd: float, end_mjd: float) -> list[dict]:
    root = ElementTree.fromstring(payload)
    if root.tag != "VSXObject" or root.findtext("AUID") != auid:
        raise ValueError("Unexpected VSX object")
    data = (root.findtext("Data") or "").strip()
    if not data:
        return []
    rows = DictReader(StringIO(data))
    if not EXPECTED_COLUMNS.issubset(rows.fieldnames or []):
        raise ValueError("Missing photometry columns")
    points = []
    for row in rows:
        mjd = float(row["JD"]) - JD_OFFSET
        magnitude = float(row["mag"])
        uncertainty = float(row["uncert"]) if row["uncert"] else None
        if (row["band"] != band or not start_mjd - 1e-8 <= mjd <= end_mjd + 1e-8
                or not isfinite(magnitude) or row["fainterThan"] not in {"0", "1"}
                or (uncertainty is not None and (not isfinite(uncertainty) or uncertainty < 0))):
            raise ValueError("Unexpected reference photometry record")
        points.append({"mjd": mjd, "magnitude": magnitude, "uncertainty_mag": uncertainty,
                       "fainter_than": row["fainterThan"] == "1", "observer_code": row["by"] or None,
                       "observation_type": row["obsType"] or None})
    return sorted(points, key=lambda point: point["mjd"])


@lru_cache(maxsize=64)
def _query(auid: str, band: ReferenceBand, start_mjd: float, end_mjd: float, limit: int, cache_period: int):
    params = {"view": "api.object", "ident": auid, "data": limit + 1,
              "fromjd": start_mjd + JD_OFFSET, "tojd": end_mjd + JD_OFFSET,
              "band": band, "mtype": "std", "minfields": "", "csv": ""}

    def fetch(deadline):
        with get(VSX_URL, params=params, timeout=irsa_timeouts(deadline, 12),
                 stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise DataError("reference_unavailable", "AAVSO returned an unexpected HTTP status", 502)
            buffer = bytearray()
            for chunk in response.iter_content(16384):
                irsa_timeouts(deadline, 12)
                buffer.extend(chunk)
                if len(buffer) > MAX_BYTES:
                    raise DataError("invalid_reference_response", "AAVSO reported too much data", 502)
        return bytes(buffer)

    try:
        payload = retry_irsa(fetch, budget=20)
    except DataError as exc:
        if exc.code == "archive_timeout":
            raise DataError("reference_timeout", "AAVSO took too long to respond", 504) from exc
        if exc.code == "archive_unavailable":
            raise DataError("reference_unavailable", "AAVSO photometry is temporarily unavailable", 502) from exc
        raise
    try:
        return _points(payload, auid, band, start_mjd, end_mjd)
    except (ElementTree.ParseError, TypeError, ValueError) as exc:
        raise DataError("invalid_reference_response", "AAVSO returned unexpected reference photometry", 502) from exc


def reference_light_curve(target_id: str, band: ReferenceBand, start_mjd: float, end_mjd: float, limit: int) -> dict:
    auid = VARIABLES.get(target_id)
    if auid is None:
        raise DataError("reference_unavailable", f"No optical reference curve configured for '{target_id}'", 404)
    if not 0 < end_mjd - start_mjd <= 730:
        raise DataError("invalid_time_range", "Choose a positive date range of at most 730 days")
    points = _query(auid, band, start_mjd, end_mjd, limit, int(monotonic() // 600))
    return {
        "target_id": target_id, "source": "AAVSO International Database", "auid": auid,
        "source_url": f"{VSX_URL}?view=api.object&ident={auid}", "band": band,
        "quantity": "apparent_optical_magnitude", "time_reference": "AAVSO observation JD converted to MJD",
        "acknowledgment": "Photometric observations contributed by AAVSO observers to the AAVSO International Database.",
        "start_mjd": start_mjd, "end_mjd": end_mjd, "has_more": len(points) > limit, "points": points[:limit],
    }
