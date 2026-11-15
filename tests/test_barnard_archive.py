from types import SimpleNamespace

from astropy.time import Time
import pytest

from pipeline import benchmark_barnard
from pipeline.catalog import DataError
from pipeline.import_storage import ImportQuota


def archive_observation(observation_id, start):
    return SimpleNamespace(archive_id=f"ivo://irsa.ipac/spherex_dr1?{observation_id}/D6", band="SPHEREx-D6",
                           observation_id=observation_id, observation_start_mjd=start,
                           observation_end_mjd=start + 0.001)


def test_archive_audit_rejects_duplicate_visits_and_preserves_failed_lookups(tmp_path, monkeypatch):
    earliest = archive_observation("2025W33_2C_0321_1", 60902.865)
    duplicate = archive_observation("2025W33_2C_0321_2", 60902.866)
    later_visit = archive_observation("2025W40_1A_0471_1", 60949.13)
    second_window = archive_observation("2026W12_1A_0598_1", 61118.31)
    attempted = []

    def search(**kwargs):
        if kwargs["release"] == "QR3":
            raise DataError("archive_timeout", "Archive request timed out", 504)
        observations = [later_visit, duplicate, earliest] if kwargs["start_mjd"] == 60895 else [second_window]
        return SimpleNamespace(observations=observations, has_more=False)

    def fetch(quota, request):
        attempted.append(request)
        if request.archive_id == later_visit.archive_id:
            raise DataError("archive_unavailable", "Archive cutout unavailable", 502)
        return SimpleNamespace(access="https://irsa.ipac.caltech.edu/image.fits", sha256="f" * 64), tmp_path, True

    def inspect(*args):
        return None, None, {"status": "core_masked", "core_pixels_valid": 0}

    monkeypatch.setattr(benchmark_barnard, "search_images", search)
    monkeypatch.setattr(benchmark_barnard, "import_exposure", fetch)
    monkeypatch.setattr(benchmark_barnard, "_inspect_observation", inspect)
    report = benchmark_barnard.audit_archive(ImportQuota(tmp_path, 1024), per_window=3)
    assert [request.archive_id for request in attempted] == [
        earliest.archive_id, later_visit.archive_id, second_window.archive_id,
    ]
    expected = benchmark_barnard._predicted_position(Time(60902.8655, format="mjd", scale="utc"))
    assert attempted[0].ra == pytest.approx(expected.ra.deg, abs=1e-9)
    assert attempted[0].dec == pytest.approx(expected.dec.deg, abs=1e-9)
    assert report["status"] == "inconclusive" and report["measured_offset_arcsec"] is None
    first, second, third = report["windows"]
    assert first["distinct_visits"] == 2
    assert first["observations"][0]["core_pixels_valid"] == 0
    assert first["observations"][1]["error"] == "archive_unavailable"
    assert second["observations"][0]["status"] == "core_masked"
    assert third["search_error"] == "archive_timeout"
