import json
import os
import socket
import subprocess
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from threading import Barrier, Event, Thread
from time import monotonic, sleep
from urllib.parse import parse_qs, urlsplit

import httpx
import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from fastapi.testclient import TestClient

from apps.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/spherex-dr1.json"
CENTER = {"ra": 269.45, "dec": 4.7}
CUTOUT = {**CENTER, "fov": 0.05}


def synthetic_exposure(product, index, *, motion=(0, 0), references=False):
    """Build a small FITS with a wavelength table, known PSF and variance."""
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = list(CENTER.values())
    wcs.wcs.crpix = [15, 15]
    wcs.wcs.cdelt = [-6.15 / 3600, 6.15 / 3600]
    header = wcs.to_header()
    header.update({"OBSID": product["observation_id"], "DETECTOR": 1, "BUNIT": "MJy/sr",
                   "MJD-BEG": product["observation_start_mjd"], "MJD-END": product["observation_end_mjd"]})
    for axis, label in ((1, "X"), (2, "Y")):
        header.update({
            f"CRPIX{axis}A": 1,
            f"CRPIX{axis}W": 1, f"CRVAL{axis}W": 1, f"CDELT{axis}W": 1,
            f"CUNIT{axis}W": "um", f"CTYPE{axis}W": "WAVE-TAB", f"PV{axis}_3W": axis,
            f"PS{axis}_0W": "WCS-WAVE", f"PS{axis}_1W": "VALUES", f"PS{axis}_2W": label,
        })
    indices = [[1, 29]]
    lookup = fits.BinTableHDU.from_columns([
        fits.Column(name="X", format="2J", array=indices),
        fits.Column(name="Y", format="2J", array=indices),
        fits.Column(name="VALUES", format="8E", dim="(2,2,2)", array=np.tile([1.024, 0.030], (1, 2, 2, 1))),
    ], name="WCS-WAVE")

    py, px = np.mgrid[-16:17, -16:17] / 4
    profile = np.exp(-(px**2 + py**2) / 2)
    psf = fits.BinTableHDU.from_columns([
        fits.Column(name="XCENTER", format="E", array=[14]),
        fits.Column(name="YCENTER", format="E", array=[14]),
        fits.Column(name="EPSF", format="1089D", dim="(33,33)", array=[profile]),
    ], name="EPSF")
    psf.header.update({"DETCOORD": "sky", "DETECTOR": 1, "OVSMPX": 4, "OVSMPY": 4})
    y, x = np.mgrid[-14:15, -14:15]
    dx, dy = motion
    signal = 0.2 + (1 + index) * np.exp(-((x - dx)**2 + (y - dy)**2) / 2)
    if references:
        for ref_x, ref_y in [(-9, -9), (9, -9), (-9, 0), (9, 0), (-9, 9), (9, 9)]:
            signal += 2 * np.exp(-((x - ref_x)**2 + (y - ref_y)**2) / 2)
    stream = BytesIO()
    fits.HDUList([
        fits.PrimaryHDU(),
        fits.ImageHDU(signal, header=header, name="IMAGE"),
        fits.ImageHDU(np.zeros(signal.shape, dtype=np.int32), name="FLAGS"),
        fits.ImageHDU(np.full(signal.shape, 0.01), name="VARIANCE"),
        psf,
        lookup,
    ]).writeto(stream)
    return stream.getvalue()


def test_astrometry_measures_subpixel_motion_and_requires_reference_stars(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    observations = manifest["observations"][:2]
    for index, observation in enumerate(observations):
        payload = synthetic_exposure(observation, index, motion=(index * 0.6, -index * 0.25), references=True)
        (tmp_path / observation["filename"]).write_bytes(payload)
        observation.update(size_bytes=len(payload), sha256=sha256(payload).hexdigest())
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    body = CENTER | {"epochs": [item["epoch"] for item in reversed(observations)]}
    with TestClient(create_app(manifest_path, tmp_path)) as client:
        response = client.post("/api/astrometry", json=body)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "measured"
        assert result["registration"]["used_sources"] == 6
        offset = result["measured_offset_arcsec"]
        assert offset["east"] == pytest.approx(-0.6 * 6.15, abs=0.02)
        assert offset["north"] == pytest.approx(-0.25 * 6.15, abs=0.02)
        assert offset["significance"] > 3
        sparse = client.post("/api/astrometry", json=body | {"fov": 0.02}).json()
        assert sparse["status"] == "registration_unverified"
        assert sparse["measured_offset_arcsec"] is None
        assert all(item["centroid"] for item in sparse["samples"])


@pytest.fixture
def irsa(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    products = manifest["observations"]
    manifest["observations"] = []
    manifest["cubes"] = []
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    samples = os.environ.get("PLANET_X_E2E_SAMPLES")
    payloads = {}
    records = []
    for index, product in enumerate(products):
        collection = f"spherex_{product['release'].lower()}"
        archive_id = f"ivo://irsa.ipac/{collection}?{product['observation_id']}/D1"
        url = product["access"].partition("?")[0]
        path = urlsplit(url).path
        payload = ((Path(samples) / product["filename"]).read_bytes()
                   if samples else synthetic_exposure(product, index))
        if samples:
            assert sha256(payload).hexdigest() == product["sha256"]
        payloads[path] = payload
        records.append((product["observation_id"], archive_id, collection, url, product["band"],
                        product["observation_start_mjd"], product["observation_end_mjd"], 0.75e-6, 1.10e-6))
    table = Table(rows=records, names=("obs_id", "obs_publisher_did", "obs_collection", "access_url",
                                      "energy_bandpassname", "t_min", "t_max", "em_min", "em_max"))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            self.server.calls.append((url.path, query))
            if url.path == "/SIA" and query.get("COLLECTION"):
                if self.server.catalog_failures:
                    status, retry_after = self.server.catalog_failures.popleft()
                    self.send_status(status, retry_after)
                    return
                catalog = table[table["obs_collection"] == query["COLLECTION"][0]]
                ids = query.get("ID")
                if ids:
                    if query.get("POS") != ["CIRCLE 269.45 4.7 0.001"]:
                        self.send_error(400)
                        return
                    catalog = catalog[catalog["obs_publisher_did"] == ids[0]]
                if self.server.untrusted_url and len(catalog):
                    catalog = catalog.copy()
                    catalog["access_url"][0] = "https://untrusted.invalid/cutout.fits"
                stream = BytesIO()
                catalog.write(stream, format="votable", tabledata_format="binary2")
                self.send_payload(stream.getvalue(), "application/x-votable+xml")
            elif url.path in payloads and query == {"center": ["269.45,4.7"], "size": ["0.05"]}:
                indexes = list(payloads)
                payload = payloads[indexes[1]] if self.server.wrong_fits else payloads[url.path]
                if self.server.cutout_failures:
                    status = self.server.cutout_failures.popleft()
                    if status == "disconnect":
                        prefix = payload[:65536].ljust(65536, b"\0")
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(prefix) + 1))
                        self.end_headers()
                        self.wfile.write(prefix)
                    else:
                        self.send_status(status)
                    return
                if self.server.cutout_barrier is not None:
                    self.server.cutout_barrier.wait(timeout=10)
                stalled = self.server.stalled_cutout
                if stalled is not None and url.path == stalled[0]:
                    _, length, release = stalled
                    self.send_response(200)
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    self.wfile.write(payload[:65536].ljust(65536, b"\0"))
                    release.wait(timeout=20)
                    return
                self.send_payload(payload, "application/fits")
            else:
                self.send_error(404)

        def send_status(self, status, retry_after=None):
            self.send_response(status)
            self.send_header("Content-Length", "0")
            if retry_after is not None:
                self.send_header("Retry-After", retry_after)
            self.end_headers()

        def send_payload(self, payload, content_type):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            if content_type != "application/fits" or not self.server.omit_fits_length:
                self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        server.calls = []
        server.payloads = payloads
        server.catalog_failures = deque()
        server.cutout_failures = deque()
        server.cutout_barrier = None
        server.stalled_cutout = None
        server.omit_fits_length = False
        server.wrong_fits = False
        server.untrusted_url = False
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server, manifest_path, bool(samples)
        finally:
            server.shutdown()
            thread.join()


@contextmanager
def running_api(irsa, tmp_path, *, quota_bytes=1024**3, with_process=False):
    archive, manifest_path, _ = irsa
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with (tmp_path / f"uvicorn-{port}.log").open("w+b") as log:
        with subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(port),
                               str(archive.server_port), str(manifest_path), str(tmp_path)],
                              cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              env=os.environ | {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                                                "PLANET_X_IMPORT_QUOTA_BYTES": str(quota_bytes)}) as process:
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=20, trust_env=False) as client:
                    deadline = monotonic() + 45
                    while process.poll() is None and monotonic() < deadline:
                        try:
                            if client.get("/api/health", timeout=0.5).status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        sleep(0.1)
                    else:
                        log.seek(0)
                        pytest.fail(log.read().decode(errors="replace") or "Uvicorn did not start")
                    yield (client, process) if with_process else client
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)


def test_archive_import_from_discovery_through_science_and_restart(irsa, tmp_path):
    server, _, real_samples = irsa
    with running_api(irsa, tmp_path) as client:
        response = client.get("/api/archive/search", params=CENTER)
        assert response.status_code == 200, response.text
        records = response.json()["observations"]
        assert len(records) == 2 and all(item["epoch"] is None for item in records)
        preflight = client.options("/api/archive/import", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        })
        assert preflight.status_code == 200
        payload = {**CUTOUT, "archive_id": records[0]["archive_id"]}

        # Duplicate requests publish one product, even if both fetch the same bytes.
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda _: client.post("/api/archive/import", json=payload), range(2)))
        assert sorted(result.status_code for result in responses) == [200, 201], [r.text for r in responses]
        first, duplicate = [response.json() for response in responses]
        assert first == duplicate
        assert first["available_locally"] is True
        assert first["sha256"] == sha256((tmp_path / "imports" / first["epoch"] / "cutout.fits").read_bytes()).hexdigest()

        response = client.post("/api/archive/import", json={**CUTOUT, "archive_id": records[1]["archive_id"]})
        assert response.status_code == 201, response.text
        second = response.json()
        comparison = client.get("/api/compare", params={
            **CENTER, "fov": 0.04, "epoch_a": first["epoch"], "epoch_b": second["epoch"],
        })
        assert comparison.status_code == 200, comparison.text
        result = comparison.json()
        assert result["alignment"]["arithmetic_valid_fraction"] > 0.8
        assert result["measurement"]["difference"] == pytest.approx(0.024914 if real_samples else 1.0, abs=1e-4)
        assert result["measurement"]["uncertainty"] > 0

        automatic = client.post("/api/compare/auto", json={
            **CENTER, "fov": 0.04, "epochs": [second["epoch"], first["epoch"]],
        })
        assert automatic.status_code == 200, automatic.text
        assert automatic.json()["epochs"]["a"]["epoch"] == first["epoch"]
        assert automatic.json()["epochs"]["b"]["epoch"] == second["epoch"]
        assert automatic.json()["measurement"] == result["measurement"]
        assert automatic.json()["selection"]["elapsed_days"] > 160

        coordinates = {"ra": 269.448214, "dec": 4.695946} if real_samples else CENTER
        series = client.post("/api/source-series", json={**coordinates, "epochs": [second["epoch"], first["epoch"]]})
        assert series.status_code == 200, series.text
        samples = series.json()["samples"]
        assert [sample["epoch"] for sample in samples] == [first["epoch"], second["epoch"]]
        assert len(series.json()["visits"]) == 2
        assert samples[0]["photometry"]["statistical_error_ujy"] > 0
        if not real_samples:
            curve = series.json()["light_curves"][0]
            assert curve["change"]["flux_change_ujy"] > 0
            assert curve["weighted_mean"]["statistical_error_ujy"] < samples[0]["photometry"]["statistical_error_ujy"]

    calls_before_restart = len(server.calls)
    with running_api(irsa, tmp_path) as client:
        repeated = client.post("/api/archive/import", json=payload)
        assert repeated.status_code == 200 and repeated.json() == first
        assert len(server.calls) == calls_before_restart
        result = client.get("/api/datasets", params={"release": "DR1"}).json()
        assert {item["epoch"] for item in result["observations"]} == {first["epoch"], second["epoch"]}
        assert client.get("/api/health").json()["available_locally"] == 2
        releases = client.get("/api/releases").json()["releases"]
        assert next(item for item in releases if item["id"] == "DR1")["observations"] == 2
        records = client.get("/api/archive/search", params=CENTER).json()["observations"]
        assert records[0]["epoch"] == first["epoch"] and records[0]["available_locally"]
        coordinates = {"ra": 269.448214, "dec": 4.695946} if real_samples else CENTER
        response = client.get("/api/photometry", params={**coordinates, "epoch": first["epoch"]})
        assert response.status_code == 200, response.text
        photometry = response.json()
        assert photometry["flux_density_ujy"] == pytest.approx(1428.9 if real_samples else 5585.6, rel=0.02)
        assert photometry["statistical_error_ujy"] > 0
        assert client.get("/api/spectrum", params={**CENTER, "epoch": first["epoch"]}).status_code == 409

        qr3 = client.get("/api/archive/search", params={**CENTER, "release": "QR3"}).json()["observations"][0]
        imported = client.post("/api/archive/import", json={**CUTOUT, "archive_id": qr3["archive_id"]})
        assert imported.status_code == 201, imported.text
        assert imported.json()["release"] == "QR3"
        assert client.get("/api/datasets", params={"release": "QR3"}).json()["observations"] == [imported.json()]


def test_archive_import_rejects_untrusted_and_invalid_fits(irsa, tmp_path):
    server, _, _ = irsa
    with running_api(irsa, tmp_path) as client:
        discovery = client.get("/api/archive/search", params=CENTER).json()
        archive_id = discovery["observations"][0]["archive_id"]
        payload = {**CUTOUT, "archive_id": archive_id}
        invalid = client.post("/api/archive/import", json={**payload, "archive_id": "http://127.0.0.1/x"})
        assert invalid.status_code == 422
        assert client.post("/api/archive/import", json={**payload, "fov": 0.25}).status_code == 422
        unknown = client.post("/api/archive/import", json={**payload, "archive_id": archive_id.replace("/D1", "/D2")})
        assert unknown.status_code == 404, unknown.text
        server.untrusted_url = True
        invalid = client.post("/api/archive/import", json=payload)
        assert invalid.status_code == 502
        assert invalid.json()["error"]["code"] == "invalid_archive_response"
        assert all(path == "/SIA" for path, _ in server.calls)

        server.untrusted_url = False
        server.wrong_fits = True
        start = len(server.calls)
        invalid = client.post("/api/archive/import", json=payload)
        assert invalid.status_code == 502
        assert invalid.json()["error"]["code"] == "invalid_archive_fits"
        assert len(server.calls) == start + 2
        assert not any(path.is_dir() for path in (tmp_path / "imports").iterdir())
        assert client.get("/api/datasets").json()["observations"] == []
        server.wrong_fits = False
        assert client.post("/api/archive/import", json=payload).status_code == 201


def test_archive_retries_transient_errors_and_cleans_up_after_exhaustion(irsa, tmp_path):
    server, _, _ = irsa
    with running_api(irsa, tmp_path) as client:
        server.catalog_failures.append((429, "60"))
        limited = client.get("/api/archive/search", params=CENTER)
        assert limited.status_code == 502
        assert limited.json()["error"]["code"] == "archive_unavailable"
        assert len(server.calls) == 1

        server.catalog_failures.append((503, "5"))
        started = monotonic()
        search = client.get("/api/archive/search", params=CENTER)
        assert search.status_code == 200, search.text
        assert monotonic() - started >= 5
        assert len(server.calls) == 3
        first, second = search.json()["observations"]
        payload = {**CUTOUT, "archive_id": first["archive_id"]}
        server.catalog_failures.append((502, None))
        server.cutout_failures.extend([503, "disconnect"])
        response = client.post("/api/archive/import", json=payload)
        assert response.status_code == 201, response.text
        path = urlsplit(first["fits_url"]).path
        assert [requested for requested, _ in server.calls[3:]] == ["/SIA", "/SIA", path, path, path]
        first_epoch = response.json()["epoch"]
        file = tmp_path / "imports" / first_epoch / "cutout.fits"
        assert file.read_bytes() == server.payloads[path]
        assert sha256(server.payloads[path]).hexdigest() == response.json()["sha256"]

        path = urlsplit(second["fits_url"]).path
        payload = {**CUTOUT, "archive_id": second["archive_id"]}
        start = len(server.calls)
        server.cutout_failures.extend(["disconnect", 503, 504])
        failed = client.post("/api/archive/import", json=payload)
        assert failed.status_code == 504, failed.text
        assert failed.json()["error"]["code"] == "archive_timeout"
        assert [requested for requested, _ in server.calls[start:]] == ["/SIA", path, path, path]
        assert [entry.name for entry in (tmp_path / "imports").iterdir() if entry.is_dir()] == [first_epoch]

        start = len(server.calls)
        server.cutout_failures.append(404)
        invalid = client.post("/api/archive/import", json=payload)
        assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "cutout_unavailable"
        assert [requested for requested, _ in server.calls[start:]] == ["/SIA", path]
        assert client.post("/api/archive/import", json=payload).status_code == 201


def test_import_quota_across_processes_and_restart(irsa, tmp_path):
    server, _, real_samples = irsa
    directory = tmp_path / "imports"
    quota = max(map(len, server.payloads.values())) + 2048
    with running_api(irsa, tmp_path, quota_bytes=quota) as first, running_api(irsa, tmp_path, quota_bytes=quota) as second:
        records = first.get("/api/archive/search", params=CENTER).json()["observations"]
        payloads = [{**CUTOUT, "archive_id": item["archive_id"]} for item in records]
        server.cutout_barrier = Barrier(2)
        try:
            with ThreadPoolExecutor(2) as pool:
                pending = [pool.submit(client.post, "/api/archive/import", json=payload)
                           for client, payload in zip((first, second), payloads)]
                responses = [future.result() for future in pending]
        finally:
            server.cutout_barrier = None
        assert sorted(result.status_code for result in responses) == [201, 507], [r.text for r in responses]
        winner = next(index for index, result in enumerate(responses) if result.status_code == 201)
        stored = responses[winner].json()
        epoch = stored["epoch"]
        error = responses[1 - winner].json()["error"]
        assert error["code"] == "import_quota_exceeded"
        assert error["details"]["limit_bytes"] == quota
        assert [entry.name for entry in directory.iterdir() if entry.is_dir()] == [epoch]
        stored_bytes = sum(path.stat().st_size for path in (directory / epoch).iterdir())
        assert stored["size_bytes"] < stored_bytes <= quota

        coords = {"ra": 269.448214, "dec": 4.695946} if real_samples else CENTER
        cases = [
            ("POST", "/api/archive/import", {"json": payloads[winner]}, 200),
            ("POST", "/api/archive/import", {"json": payloads[1 - winner]}, 507),
            ("GET", "/api/datasets", {}, 200),
            ("GET", "/api/photometry", {"params": {**coords, "epoch": epoch}}, 200),
        ]
        # Mix reads and writes on both workers while only one cutout fits.
        with ThreadPoolExecutor(12) as pool:
            jobs = [
                (pool.submit(client.request, method, path, **kwargs), path, status)
                for _ in range(4)
                for client in (first, second)
                for method, path, kwargs, status in cases
            ]
            for future, path, status in jobs:
                response = future.result()
                assert response.status_code == status, response.text
                if status == 507:
                    assert response.json()["error"]["code"] == "import_quota_exceeded"
                elif path == "/api/datasets":
                    assert response.json()["observations"] == [stored]
                else:
                    assert response.json()["epoch"] == epoch
        assert [entry.name for entry in directory.iterdir() if entry.is_dir()] == [epoch]

    with running_api(irsa, tmp_path, quota_bytes=stored_bytes + 1) as client:
        start = len(server.calls)
        hit = client.post("/api/archive/import", json=payloads[winner])
        assert hit.status_code == 200 and hit.json() == stored
        assert len(server.calls) == start
        server.omit_fits_length = True
        blocked = client.post("/api/archive/import", json=payloads[1 - winner])
        assert blocked.status_code == 507, blocked.text
        assert blocked.json()["error"]["details"]["used_bytes"] == stored_bytes
        assert client.get("/api/datasets").json()["observations"] == [stored]
        flux = client.get("/api/photometry", params={**coords, "epoch": epoch})
        assert flux.status_code == 200, flux.text
        assert [entry.name for entry in directory.iterdir() if entry.is_dir()] == [epoch]


def test_import_recovers_quota_when_a_worker_is_killed(irsa, tmp_path):
    server, _, _ = irsa
    storage = tmp_path / "imports"
    reserved = max(131072, max(map(len, server.payloads.values())))
    quota = reserved + 2048
    with (
        running_api(irsa, tmp_path, quota_bytes=quota, with_process=True) as (interrupted, process),
        running_api(irsa, tmp_path, quota_bytes=quota) as surviving,
        ThreadPoolExecutor(1) as pool,
    ):
        records = surviving.get("/api/archive/search", params=CENTER).json()["observations"]
        first, second = [{**CUTOUT, "archive_id": record["archive_id"]} for record in records]
        release = Event()
        server.stalled_cutout = (urlsplit(records[0]["fits_url"]).path, reserved, release)
        try:
            request = pool.submit(interrupted.post, "/api/archive/import", json=first)
            deadline = monotonic() + 10
            while monotonic() < deadline:
                partial = next(storage.glob(".download-*/*/cutout.fits"), None)
                if partial is not None and partial.stat().st_size == reserved:
                    break
                sleep(0.025)
            else:
                pytest.fail("The interrupted worker did not reserve space")

            rejected = surviving.post("/api/archive/import", json=second)
            assert rejected.status_code == 507, rejected.text
            assert rejected.json()["error"]["details"]["used_bytes"] == reserved
            assert partial.stat().st_size == reserved

            process.kill()
            process.wait(timeout=10)
            with pytest.raises(httpx.TransportError):
                request.result(timeout=10)
            assert partial.is_file()

            accepted = surviving.post("/api/archive/import", json=second)
            assert accepted.status_code == 201, accepted.text
            assert not list(storage.glob(".download-*"))
            assert surviving.get("/api/datasets").json()["observations"] == [accepted.json()]
        finally:
            release.set()


if __name__ == "__main__":
    import uvicorn
    from astroquery.ipac.irsa import conf
    from requests import get

    from apps.api.main import create_app
    from pipeline import exposures

    _, port, archive_port, manifest, state = sys.argv
    base_url = f"http://127.0.0.1:{archive_port}"
    conf.sia_url = f"{base_url}/SIA"

    # Only replace the network destination after the application approves the IRSA URL.
    def local_cutout(url, **kwargs):
        return get(url.replace("https://irsa.ipac.caltech.edu", base_url, 1), **kwargs)

    exposures.get = local_cutout
    data_dir = Path(state)
    uvicorn.run(create_app(Path(manifest), data_dir, data_dir / "imports"), host="127.0.0.1", port=int(port))
