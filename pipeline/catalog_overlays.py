from functools import lru_cache
from io import BytesIO
from math import isfinite
from typing import Literal

from astropy.io.votable import parse
from numpy.ma import is_masked
from requests import get

from pipeline.archive import irsa_timeouts, retry_irsa
from pipeline.catalog import DataError

Overlay = Literal["gaia", "wise"]
VIZIER = "https://vizier.cfa.harvard.edu/viz-bin/votable"
TABLES = {
    "gaia": ("I/355/gaiadr3", "Gaia DR3", {
        "id": "Source", "ra": "RA_ICRS", "dec": "DE_ICRS", "g_mag": "Gmag",
        "pm_ra_cosdec_mas_yr": "pmRA", "pm_dec_mas_yr": "pmDE", "parallax_mas": "Plx",
    }),
    "wise": ("II/328/allwise", "AllWISE", {
        "id": "AllWISE", "ra": "RAJ2000", "dec": "DEJ2000", "w1_mag": "W1mag", "w2_mag": "W2mag",
    }),
}


def _value(value):
    if is_masked(value):
        return None
    numeric = float(value)
    return numeric if isfinite(numeric) else None


@lru_cache(maxsize=64)
def query_overlay(catalog: Overlay, ra: float, dec: float, radius_deg: float, limit: int) -> dict:
    table_id, name, fields = TABLES[catalog]
    params = {"-source": table_id, "-c": f"{ra} {dec:+f}", "-c.rd": radius_deg,
              "-out.max": limit + 1, "-out": ",".join(fields.values()), "-sort": "_r"}

    def fetch(deadline):
        with get(VIZIER, params=params, timeout=irsa_timeouts(deadline, 15), stream=True) as response:
            response.raise_for_status()
            payload = BytesIO()
            for chunk in response.iter_content(65536):
                payload.write(chunk)
                if payload.tell() > 2 * 1024**2:
                    raise DataError("invalid_catalog_response", "VizieR returned too much catalog data", 502)
            payload.seek(0)
            return payload

    try:
        payload = retry_irsa(fetch, budget=30)
    except DataError as exc:
        if exc.code == "archive_timeout":
            raise DataError("catalog_timeout", "VizieR took too long to respond", 504) from exc
        if exc.code == "archive_unavailable":
            raise DataError("catalog_unavailable", "VizieR catalog is temporarily unavailable", 502) from exc
        raise

    try:
        document = parse(payload)
        infos = [*document.infos, *(info for resource in document.resources for info in resource.infos)]
        if any((info.name or "").lower() == "error" or (info.value or "").upper() == "ERROR" for info in infos):
            raise ValueError("VizieR reported a query failure")
        tables = list(document.iter_tables())
        if not tables:
            table = []
        else:
            table = next(item.to_table(use_names_over_ids=True) for item in tables if item.name == table_id)
            if not set(fields.values()).issubset(table.colnames):
                raise ValueError("Missing catalog columns")
        sources = []
        for row in table[:limit]:
            if is_masked(row[fields["id"]]):
                continue
            source = {key: str(row[column]) if key == "id" else _value(row[column])
                      for key, column in fields.items()}
            if source["ra"] is not None and source["dec"] is not None:
                sources.append(source)
    except (KeyError, StopIteration, ValueError, TypeError) as exc:
        raise DataError("invalid_catalog_response", "VizieR returned an unexpected catalog table", 502) from exc
    return {"catalog": name, "source": f"https://cdsarc.cds.unistra.fr/viz-bin/cat/{table_id}",
            "coordinate_frame": "ICRS", "reference_epoch_jyear": 2016.0 if catalog == "gaia" else None,
            "has_more": len(table) > limit, "sources": sources}
