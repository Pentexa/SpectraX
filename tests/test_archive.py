from io import BytesIO
from pathlib import Path

from astropy.table import MaskedColumn, Table
from fastapi.testclient import TestClient
from requests import Response, Session
from requests.exceptions import ConnectionError, ReadTimeout, SSLError
from urllib3.response import HTTPResponse

from apps.api.main import create_app
from pipeline.catalog import load_manifest

MANIFEST = Path(__file__).resolve().parents[1] / "data/manifests/spherex-dr1.json"
POSITION = {"ra": 269.45, "dec": 4.7}


def test_sia_search_filters_and_matches_local_exposure(monkeypatch, tmp_path):
    observation = load_manifest(MANIFEST).observations[0]
    (tmp_path / observation.filename).touch()
    table = Table({
        "obs_id": [observation.observation_id] * 3,
        "obs_publisher_did": [f"ivo://irsa.ipac/spherex_dr1?exposure/D{i}" for i in (1, 2, 3)],
        "obs_collection": ["spherex_dr1"] * 3,
        "access_url": ["https://irsa.ipac.caltech.edu/archive.fits"] * 3,
        "energy_bandpassname": ["SPHEREx-D1", "SPHEREx-D2", "SPHEREx-D3"],
        "t_min": [60949.13] * 3,
        "t_max": MaskedColumn([60949.14] * 3, mask=[False, True, False]),
        "em_min": [0.75e-6, 1.1e-6, 1.62e-6],
        "em_max": [1.1e-6, 1.62e-6, 2.42e-6],
    })

    def respond(_, method, url, *, params, timeout, **kwargs):
        assert method == "GET"
        assert url.rstrip("/") == "https://irsa.ipac.caltech.edu/SIA"
        assert timeout == (5, 15)
        assert params == {
            "POS": ["CIRCLE 269.45 4.7 0.01"], "COLLECTION": ["spherex_dr1"],
            "BAND": ["1e-06 1e-06"], "TIME": ["60948.0 +Inf"], "MAXREC": "3",
        }
        body = BytesIO()
        table.write(body, format="votable", tabledata_format="binary2")
        body.seek(0)
        response = Response()
        response.status_code = 200
        response.raw = HTTPResponse(body=body, preload_content=False)
        return response

    monkeypatch.setattr(Session, "request", respond)
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        response = client.get("/api/archive/search", params={**POSITION, "limit": 2, "wavelength_um": 1,
                                                              "start_mjd": 60948})
    assert response.status_code == 200
    result = response.json()
    assert result["has_more"] is True
    first, second = result["observations"]
    assert first["epoch"] == observation.epoch and first["available_locally"] is True
    assert first["wavelength_min_um"] == 0.75
    assert second["epoch"] is None and second["available_locally"] is False
    assert second["observation_end_mjd"] is None


def test_sia_search_reports_network_failures(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        attempts.append(1)
        raise failure

    monkeypatch.setattr(Session, "request", fail)
    monkeypatch.setattr("pipeline.archive.sleep", lambda _: None)
    with TestClient(create_app(MANIFEST, tmp_path)) as client:
        for failure, status, code, count in (
            (ReadTimeout(), 504, "archive_timeout", 3),
            (ConnectionError(), 502, "archive_unavailable", 3),
            (SSLError(), 502, "archive_unavailable", 1),
        ):
            attempts = []
            response = client.get("/api/archive/search", params={**POSITION, "release": "QR3"})
            assert response.status_code == status
            assert response.json()["error"]["code"] == code
            assert len(attempts) == count
        response = client.get("/api/archive/search", params={**POSITION, "start_mjd": 61000, "end_mjd": 60900})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_time_range"
