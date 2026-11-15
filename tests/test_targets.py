from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from requests import Response

from apps.api import main
from apps.api.main import create_app
from pipeline import catalog_overlays, targets
from pipeline.archive import ArchiveObservation, ArchiveSearch
from pipeline.catalog import load_manifest

MANIFEST = Path(__file__).resolve().parents[1] / "data/manifests/spherex-dr1.json"


def test_challenge_targets_have_epoch_positions_and_catalog_references(tmp_path):
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        first = client.get("/api/targets", params={"mjd": 60902}).json()["targets"]
        second = client.get("/api/targets", params={"mjd": 61267}).json()["targets"]
        assert client.get("/api/targets/unknown/observations").status_code == 404
        assert client.get("/api/targets", params={"mjd": "NaN"}).status_code == 422
    earlier = {target["id"]: target for target in first}
    later = {target["id"]: target for target in second}
    assert set(earlier) == {"barnard", "epsilon-indi-b", "wise-0855", "rw-aurigae", "r-draconis"}
    assert all(item["source"].startswith("https://simbad.") for item in later.values())
    assert 7 < (earlier["wise-0855"]["ra"] - later["wise-0855"]["ra"]) * 3600 < 10
    assert 9 < (later["barnard"]["dec"] - earlier["barnard"]["dec"]) * 3600 < 12


def test_target_search_checks_the_local_fits_footprint(tmp_path, monkeypatch):
    observation = load_manifest(MANIFEST).observations[0]
    (tmp_path / observation.filename).touch()
    archive = ArchiveSearch(
        release="DR1", collection="spherex_dr1", has_more=False,
        observations=[ArchiveObservation(
            archive_id="ivo://irsa.ipac/spherex_dr1?2025W40_1A_0471_1/D1",
            observation_id=observation.observation_id, band=observation.band, fits_url=str(observation.access),
            observation_start_mjd=observation.observation_start_mjd, observation_end_mjd=observation.observation_end_mjd,
            wavelength_min_um=0.75, wavelength_max_um=1.09, epoch=None, available_locally=False,
        )],
    )
    monkeypatch.setattr(main, "search_images", lambda **kwargs: archive)
    image = SimpleNamespace(wcs=SimpleNamespace(world_to_pixel=lambda position: (20, 70)),
                            signal=SimpleNamespace(shape=(50, 50)))
    monkeypatch.setattr(targets, "read_image", lambda directory, observation: image)

    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        url = "/api/targets/barnard/observations"
        outside = client.get(url).json()["observations"][0]
        assert outside["predicted_position"]["dec"] > 4.76
        assert outside["epoch"] is None and not outside["available_locally"]
        monkeypatch.setattr(image.wcs, "world_to_pixel", lambda position: (20, 30))
        inside = client.get(url).json()["observations"][0]
        assert inside["epoch"] == observation.epoch and inside["available_locally"]


def test_gaia_overlay_preserves_large_ids_and_missing_values(tmp_path, monkeypatch):
    response = Response()
    response.status_code = 200
    payload = b"""<?xml version="1.0"?>
    <VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
      <RESOURCE><TABLE name="I/355/gaiadr3">
        <FIELD name="Source" datatype="long"/>
        <FIELD name="RA_ICRS" datatype="double"/>
        <FIELD name="DE_ICRS" datatype="double"/>
        <FIELD name="Gmag" datatype="double"/>
        <FIELD name="pmRA" datatype="double"/>
        <FIELD name="pmDE" datatype="double"/>
        <FIELD name="Plx" datatype="double"/>
        <DATA><TABLEDATA>
          <TR><TD>4472832130942575872</TD><TD>269.45</TD><TD>4.7</TD><TD>14.2</TD><TD></TD><TD></TD><TD></TD></TR>
          <TR><TD>4472832130942575873</TD><TD>269.45</TD><TD>4.71</TD><TD>16.1</TD><TD></TD><TD></TD><TD></TD></TR>
        </TABLEDATA></DATA>
      </TABLE></RESOURCE>
    </VOTABLE>"""
    monkeypatch.setattr(response, "iter_content", lambda _: iter([payload]))
    monkeypatch.setattr(response, "close", lambda: None)

    def remote(url, *, params, **kwargs):
        assert url == catalog_overlays.VIZIER
        assert params["-source"] == "I/355/gaiadr3"
        assert params["-out.max"] == 2
        return response

    monkeypatch.setattr(catalog_overlays, "get", remote)
    catalog_overlays.query_overlay.cache_clear()
    try:
        with TestClient(create_app(MANIFEST, tmp_path)) as client:
            result = client.get("/api/catalog/gaia", params={"ra": 269.45, "dec": 4.7, "limit": 1})
        assert result.status_code == 200
        body = result.json()
        assert body["has_more"]
        assert body["reference_epoch_jyear"] == 2016.0
        assert body["sources"] == [{"id": "4472832130942575872", "ra": 269.45, "dec": 4.7, "g_mag": 14.2,
                                    "pm_ra_cosdec_mas_yr": None, "pm_dec_mas_yr": None, "parallax_mas": None}]
    finally:
        catalog_overlays.query_overlay.cache_clear()
