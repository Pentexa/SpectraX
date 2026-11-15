import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import numpy as np
from astropy.io import fits
from fastapi.testclient import TestClient
from requests import Response

from apps.api.main import create_app
from pipeline import cube_archive
from pipeline.catalog import DataError

TARGETS = (
    ({"ra": 60.8109955, "dec": 51.3404038}, 445),
    ({"ra": 269.45, "dec": 4.7}, 7945),
)


def cube_fixture(tile, position):
    header = fits.Header({
        "NPIX": tile, "BUNIT": "MJy/sr", "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
        "CRPIX1": 8, "CRPIX2": 8, "CDELT1": -0.004, "CDELT2": 0.004,
        "CRVAL1": position["ra"], "CRVAL2": position["dec"],
    })
    shape = (102, 15, 15)
    hits = np.ones(shape, dtype=np.int32)
    hits[51] = 0
    channels = fits.BinTableHDU.from_columns([
        fits.Column(name="DETECTOR", format="J", array=np.repeat(np.arange(1, 7), 17)),
        fits.Column(name="SUBCHAN", format="J", array=np.tile(np.arange(1, 18), 6)),
        fits.Column(name="WAVELENGTH", format="D", unit="um", array=np.linspace(0.75, 5, 102)),
    ], name="SPECTRAL_CHANNELS")
    output = BytesIO()
    fits.HDUList([
        fits.PrimaryHDU(header=fits.Header({"MJD-BEG": 60900.0, "MJD-END": 61169.0})),
        fits.ImageHDU(np.full(shape, tile, dtype=np.float32), header=header, name="IMAGE"),
        fits.ImageHDU(hits, name="NHITS"),
        fits.ImageHDU(np.zeros(shape, dtype=np.int32), name="FLAGS"),
        channels,
    ]).writeto(output)
    return output.getvalue()


def test_coordinate_spectrum_downloads_persists_and_evicts_tiles(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version": 1, "observations": []}', encoding="utf-8")
    cubes = {tile: cube_fixture(tile, position) for position, tile in TARGETS}
    monkeypatch.setenv("PLANET_X_CUBE_CACHE_DIR", str(tmp_path / "cubes"))
    monkeypatch.setenv("PLANET_X_CUBE_CACHE_BYTES", str(max(map(len, cubes.values())) + 2048))
    calls = []

    def serve_cube(url, **kwargs):
        calls.append(url)
        tile = int(url.rsplit("/Npix", 1)[1].split("_", 1)[0])
        payload = cubes[tile]
        response = Response()
        response.status_code = 200
        response.raw = BytesIO(payload)
        response.headers["Content-Length"] = str(len(payload))
        return response

    monkeypatch.setattr(cube_archive, "get", serve_cube)
    first_position, first_tile = TARGETS[0]
    second_position, second_tile = TARGETS[1]
    with TestClient(create_app(manifest, tmp_path)) as client:
        response = client.get("/api/spectrum", params=first_position)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["epoch"] == "dr1-npix445"
        assert result["dataset"]["sha256"] == sha256(cubes[first_tile]).hexdigest()
        assert result["channels"][0]["flux"] == first_tile
        assert result["channels"][51]["flux"] is None
        assert result["available_channels"] == 101
        assert len(calls) == 1 and calls[0].endswith("/Norder5/Dir0/Npix445_cube.fits")

    with TestClient(create_app(manifest, tmp_path)) as client:
        response = client.get("/api/spectrum", params={**first_position, "epoch": result["epoch"]})
        assert response.json() == result and len(calls) == 1
        layer = client.get("/api/layers/1", params={**first_position, "fov": 0.025})
        assert layer.status_code == 200 and len(calls) == 1
        combined = client.get("/api/layers/4", params={**first_position, "fov": 0.025, "combine": True})
        assert combined.status_code == 200 and len(calls) == 1
        mosaic = combined.json()
        center = mosaic["grid"]["width"] // 2
        assert mosaic["channel_count"][center][center] == 16
        assert mosaic["nhits"][center][center] == 16
        assert mosaic["image"][center][center] == first_tile
        response = client.get("/api/spectrum", params=second_position)
        assert response.status_code == 200, response.text
        assert response.json()["channels"][0]["flux"] == second_tile
        assert len(calls) == 2
        assert not (tmp_path / "cubes" / result["epoch"]).exists()
        assert (tmp_path / "cubes" / "dr1-npix7945" / "cube.fits").is_file()


def test_live_spectrum_tries_archive_before_prepared_cube(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    source = Path(__file__).resolve().parents[1] / "data/manifests/spherex-dr1.json"
    inventory = json.loads(source.read_text(encoding="utf-8"))
    inventory["observations"] = []
    position, tile = TARGETS[1]
    payload = cube_fixture(tile, position)
    prepared = inventory["cubes"][0]
    prepared.update(size_bytes=len(payload), sha256=sha256(payload).hexdigest())
    (tmp_path / prepared["filename"]).write_bytes(payload)
    manifest.write_text(json.dumps(inventory), encoding="utf-8")
    attempts = []

    def serve_cube(url, **kwargs):
        attempts.append(url)
        if len(attempts) == 1:
            raise DataError("archive_unavailable", "Unavailable", 502)
        response = Response()
        response.status_code = 200
        response.raw = BytesIO(payload)
        response.headers["Content-Length"] = str(len(payload))
        return response

    monkeypatch.setattr(cube_archive, "get", serve_cube)
    with TestClient(create_app(manifest, tmp_path)) as client:
        params = position | {"live": True}
        offline = client.get("/api/spectrum", params=params)
        assert offline.status_code == 200, offline.text
        assert offline.json()["epoch"] == prepared["epoch"]
        assert offline.json()["delivery"] == "downloaded_fallback"
        online = client.get("/api/spectrum", params=params)
        assert online.status_code == 200, online.text
        assert online.json()["epoch"] == "dr1-npix7945"
        assert online.json()["delivery"] == "archive_cube"
        assert attempts == [prepared["access"], prepared["access"]]


def test_cube_identity_mismatch_cannot_publish(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version": 1, "observations": []}', encoding="utf-8")
    position, _ = TARGETS[0]
    payload = cube_fixture(1, position)
    monkeypatch.setenv("PLANET_X_CUBE_CACHE_DIR", str(tmp_path / "cubes"))

    def serve_wrong_tile(*args, **kwargs):
        response = Response()
        response.status_code = 200
        response.raw = BytesIO(payload)
        response.headers["Content-Length"] = str(len(payload))
        return response

    monkeypatch.setattr(cube_archive, "get", serve_wrong_tile)
    with TestClient(create_app(manifest, tmp_path)) as client:
        response = client.get("/api/spectrum", params=position)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_archive_fits"
    assert not (tmp_path / "cubes" / "dr1-npix445").exists()
