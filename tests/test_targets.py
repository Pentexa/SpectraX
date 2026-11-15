from pathlib import Path
from shutil import copyfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from requests import Response

from apps.api import main
from apps.api.main import create_app
from pipeline import catalog_overlays, exposures, reference_light_curves, targets
from pipeline.archive import ArchiveObservation, ArchiveSearch
from pipeline.catalog import DataError, load_manifest

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
    assert all(not item["benchmark_available"] for item in later.values())
    assert 7 < (earlier["wise-0855"]["ra"] - later["wise-0855"]["ra"]) * 3600 < 10
    assert 9 < (later["barnard"]["dec"] - earlier["barnard"]["dec"]) * 3600 < 12


def test_benchmark_reports_missing_files_for_each_challenge_target(tmp_path):
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        for target in client.get("/api/targets").json()["targets"]:
            target_id = target["id"]
            response = client.get(f"/api/targets/{target_id}/benchmark")
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "benchmark_not_prepared"
            assert response.json()["error"]["details"]["epochs"] == [f"{target_id}-a", f"{target_id}-b"]
        assert client.get("/api/targets/unknown/benchmark").status_code == 404
        assert client.get("/api/targets/wise-0855/benchmark", params={"fov": 1}).status_code == 422


def test_existing_benchmark_manifest_directory_can_load_a_subset(tmp_path, monkeypatch):
    filename = "spherex-wise-0855.json"
    (tmp_path / filename).write_bytes((MANIFEST.parent / filename).read_bytes())
    monkeypatch.setenv("PLANET_X_BENCHMARK_MANIFEST_DIR", str(tmp_path))
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        assert client.get("/api/targets/wise-0855/benchmark").status_code == 503
        assert client.get("/api/targets/barnard/benchmark").status_code == 404


def test_archive_outage_serves_real_prepared_timeline_when_downloaded(monkeypatch):
    directory = MANIFEST.parents[1] / "samples"
    records = load_manifest(MANIFEST.with_name("spherex-rw-aurigae.json")).observations
    if not all((directory / "rw-aurigae" / item.filename).is_file() for item in records):
        pytest.skip("Run planet-x-data --include-benchmarks to prepare real FITS")

    def unavailable(**_):
        raise DataError("archive_unavailable", "IRSA archive request failed", 502)

    monkeypatch.setattr(main, "search_images", unavailable)
    with TestClient(create_app(MANIFEST, directory)) as client:
        target = next(item for item in client.get("/api/targets").json()["targets"] if item["id"] == "rw-aurigae")
        local_epochs = []
        for release in ("DR1", "QR3"):
            result = client.get("/api/targets/rw-aurigae/observations", params={"release": release})
            assert result.status_code == 200
            assert result.json()["archive"]["scope"] == "local"
            assert all(item["available_locally"] for item in result.json()["observations"])
            local_epochs.extend(item["epoch"] for item in result.json()["observations"])
        assert set(local_epochs) == set(target["timeline_epochs"])
        request = {key: target[key] for key in ("ra", "dec", "fov")}
        result = client.post("/api/timeline", json=request | {"epochs": local_epochs[::-1]})
        assert result.status_code == 200
        dates = [item["mjd"] for item in result.json()["frames"]]
        assert len(dates) == 3 and dates == sorted(set(dates))
        assert client.post("/api/timeline", json=request | {"epochs": [local_epochs[0]] * 3}).status_code == 422
        assert client.get("/api/archive/search", params={"ra": 0, "dec": 0}).status_code == 502


def test_local_only_search_does_not_call_irsa(tmp_path, monkeypatch):
    def unexpected(**_):
        pytest.fail("A local-only search made a live IRSA request")

    monkeypatch.setattr(main, "search_images", unexpected)
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        params = {"ra": 0, "dec": 0, "local_only": True}
        response = client.get("/api/archive/search", params=params)
        assert response.status_code == 200
        assert response.json()["scope"] == "local"
        assert response.json()["observations"] == []
        invalid = client.get("/api/archive/search", params=params | {"start_mjd": 61200, "end_mjd": 61000})
        assert invalid.status_code == 422
        target = client.get("/api/targets/rw-aurigae/observations", params={"local_only": True})
        assert target.status_code == 200
        assert target.json()["archive"]["scope"] == "local"


def test_known_archive_cutout_can_import_during_catalog_outage(tmp_path, monkeypatch):
    record = load_manifest(MANIFEST).observations[0]
    sample = MANIFEST.parents[1] / "samples" / record.filename
    if not sample.is_file():
        pytest.skip("Run planet-x-data to prepare a verified IRSA cutout")

    def unavailable(*_):
        raise DataError("archive_unavailable", "IRSA catalog request failed", 502)

    attempted = []

    def download(url, path, quota):
        attempted.append(url)
        copyfile(sample, path)
        return record.size_bytes, record.sha256

    monkeypatch.setattr(exposures, "find_image", unavailable)
    monkeypatch.setattr(exposures, "_download_cutout", download)
    archive_id = f"ivo://irsa.ipac/spherex_dr1?{record.observation_id}/D1"
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        payload = record.coverage.model_dump() | {"archive_id": archive_id}
        created = client.post("/api/archive/import", json=payload)
        assert created.status_code == 201, created.text
        assert created.json()["sha256"] == record.sha256
        cached = client.post("/api/archive/import", json=payload)
        assert cached.status_code == 200
        assert cached.json()["epoch"] == created.json()["epoch"]
        assert client.post("/api/archive/import", json=payload | {"ra": 0}).status_code == 502
        assert attempted == [str(record.access)]


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


def test_reference_light_curve_keeps_band_provenance_and_limits(tmp_path, monkeypatch):
    payload = b"""<VSXObject><Name>R Dra</Name><AUID>000-BBX-660</AUID><Data>
JD,mag,uncert,band,by,fainterThan,obsType
2461182.5,12.6,,Vis.,MOW,0,Visual
2461181.5,12.8,0.1,Vis.,PUJ,1,Visual
</Data></VSXObject>"""
    response = Response()
    response.status_code = 200
    monkeypatch.setattr(response, "iter_content", lambda _: iter([payload[:60], payload[60:]]))
    monkeypatch.setattr(response, "close", lambda: None)

    def remote(url, *, params, **kwargs):
        assert url == reference_light_curves.VSX_URL
        assert params["ident"] == "000-BBX-660" and params["band"] == "Vis."
        assert (params["fromjd"], params["tojd"], params["data"]) == (2461180.5, 2461185.5, 2)
        return response

    monkeypatch.setattr(reference_light_curves, "get", remote)
    try:
        with TestClient(create_app(MANIFEST, tmp_path)) as client:
            url = "/api/targets/r-draconis/reference-light-curve"
            result = client.get(url, params={"start_mjd": 61180, "end_mjd": 61185, "limit": 1})
            assert client.get(url, params={"start_mjd": 61181, "end_mjd": 61180}).status_code == 422
        assert result.status_code == 200, result.text
        curve = result.json()
        assert curve["source"] == "AAVSO International Database" and curve["has_more"]
        assert curve["points"] == [{"mjd": 61181, "magnitude": 12.8, "uncertainty_mag": 0.1, "fainter_than": True,
                                    "observer_code": "PUJ", "observation_type": "Visual"}]
    finally:
        reference_light_curves._query.cache_clear()
