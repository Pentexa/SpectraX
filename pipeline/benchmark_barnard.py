import argparse
import json
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time
from dotenv import load_dotenv

from pipeline.archive import ArchiveRelease, search_images
from pipeline.catalog import DataError, Observation, load_manifest
from pipeline.exposures import ImportRequest, import_exposure
from pipeline.images import Image, read_image
from pipeline.import_storage import DEFAULT_IMPORT_QUOTA_BYTES, ImportQuota
from pipeline.ingest import ROOT, configured_path

REFERENCE_URL = "https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=barnard+star&submit=SIMBAD+search"
SOURCE_ID = "4472832130942575872"
DEMO_EPOCHS = ("dr1-2025-10-01-d1", "dr1-2026-03-11-d1")
ARCHIVE_WINDOWS: tuple[tuple[ArchiveRelease, int, int], ...] = (
    ("DR1", 60895, 61020),
    ("DR1", 61080, 61185),
    ("QR3", 61200, 61359),
)
ARCHIVE_WAVELENGTH_UM = 4.65


def _predicted_position(time: Time) -> SkyCoord:
    reference = SkyCoord("17h57m48.498470s", "+04d41m36.11388s", frame="icrs",
                         obstime=Time(2000, format="jyear", scale="tt"),
                         pm_ra_cosdec=-801.551 * u.mas / u.yr, pm_dec=10362.394 * u.mas / u.yr,
                         distance=(546.9759 * u.mas).to(u.pc, equivalencies=u.parallax()),
                         radial_velocity=-110.11 * u.km / u.s)
    barycentric = reference.apply_space_motion(time).cartesian.without_differentials()
    return SkyCoord(barycentric - get_body_barycentric("earth", time, ephemeris="builtin"), frame="icrs")


def _coverage(image: Image, position: SkyCoord) -> dict:
    x, y = map(float, image.wcs.world_to_pixel(position))
    result = {"ra_deg": float(position.ra.deg), "dec_deg": float(position.dec.deg), "covered": False,
              "core_pixels_valid": None, "core_flag_union": None, "status": "outside_image"}
    h, w = image.signal.shape
    if not (-0.5 <= x < w - 0.5 and -0.5 <= y < h - 0.5):
        return result
    ix, iy = int(np.floor(x + 0.5)), int(np.floor(y + 0.5))
    result["covered"] = True
    if not (1 <= ix < w - 1 and 1 <= iy < h - 1):
        return result | {"status": "at_image_edge"}
    core = np.s_[iy - 1:iy + 2, ix - 1:ix + 2]
    count = int(image.valid[core].sum())
    flags = int(np.bitwise_or.reduce(image.flags[core].ravel())) if image.flags is not None else None
    return result | {"core_pixels_valid": count, "core_flag_union": flags,
                     "status": "core_available" if count == 9 else "core_masked"}


def _observation_midpoint(start_mjd: float, end_mjd: float) -> Time:
    return Time((start_mjd + end_mjd) / 2, format="mjd", scale="utc")


def _inspect_observation(data_dir: Path, observation: Observation):
    time = _observation_midpoint(observation.observation_start_mjd, observation.observation_end_mjd)
    position = _predicted_position(time)
    coverage = _coverage(read_image(data_dir, observation), position)
    return time, position, {"epoch": observation.epoch, "midpoint_utc": time.isot + "Z",
                            "observation_id": observation.observation_id, **coverage}


def benchmark(data_dir: Path, observations: list[Observation]) -> dict:
    epochs = []
    positions = []
    times = []
    for observation in sorted(observations, key=lambda item: item.observation_start_mjd):
        time, position, inspected = _inspect_observation(data_dir, observation)
        epochs.append(inspected)
        times.append(time)
        positions.append(position)
    west_east, south_north = positions[0].spherical_offsets_to(positions[1])
    core_available = all(epoch["status"] == "core_available" for epoch in epochs)
    return {"target": "Barnard's Star", "gaia_dr3_source_id": SOURCE_ID, "source": REFERENCE_URL,
            "status": "not_measured" if core_available else "not_testable",
            "testable": None if core_available else False, "detected": None, "uncertainty_arcsec": None,
            "elapsed_days": float((times[1] - times[0]).to_value(u.day)),
            "predicted_apparent_offset_arcsec": {"east": float(west_east.arcsec), "north": float(south_north.arcsec)},
            "measured_offset_arcsec": None, "epochs": epochs}


def audit_archive(quota: ImportQuota, per_window: int) -> dict:
    """Inspect a bounded sample from distinct survey visits."""
    windows = []
    for release, start, end in ARCHIVE_WINDOWS:
        center = _predicted_position(_observation_midpoint(start, end))
        window = {"release": release, "start_mjd": start, "end_mjd": end, "observations": []}
        windows.append(window)
        try:
            matches = search_images(
                release=release, ra=center.ra.deg, dec=center.dec.deg, radius_deg=0.007, limit=100,
                wavelength_um=ARCHIVE_WAVELENGTH_UM, start_mjd=start, end_mjd=end, local_observations=[],
            )
        except DataError as exc:
            window["search_error"] = exc.code
            continue
        visits = {}
        timed = [item for item in matches.observations
                 if item.observation_start_mjd is not None and item.observation_end_mjd is not None]
        for item in sorted(timed, key=lambda item: item.observation_start_mjd):
            visits.setdefault(item.observation_id.rsplit("_", 1)[0], item)
        candidates = list(visits.values())
        window["returned_matches"] = len(matches.observations)
        window["distinct_visits"] = len(candidates)
        window["catalog_truncated"] = matches.has_more
        indices = np.linspace(0, max(0, len(candidates) - 1), min(per_window, len(candidates)), dtype=int)
        for index in indices:
            selected = candidates[index]
            midpoint = _observation_midpoint(selected.observation_start_mjd, selected.observation_end_mjd)
            position = _predicted_position(midpoint)
            inspected = {"archive_id": selected.archive_id, "band": selected.band}
            try:
                request = ImportRequest(archive_id=selected.archive_id, ra=position.ra.deg, dec=position.dec.deg,
                                        fov=0.05)
                observation, directory, _ = import_exposure(quota, request)
                _, _, quality = _inspect_observation(directory, observation)
                inspected.update(quality, access=str(observation.access), sha256=observation.sha256)
            except DataError as exc:
                inspected.update(status="unavailable", error=exc.code, midpoint_utc=midpoint.isot + "Z")
            window["observations"].append(inspected)
    usable_windows = sum(any(item["status"] == "core_available" for item in window["observations"])
                         for window in windows)
    if usable_windows >= 2:
        status = "candidate_pair_found"
    elif any("search_error" in window or any(item["status"] == "unavailable" for item in window["observations"])
             for window in windows):
        status = "inconclusive"
    else:
        status = "no_pair_in_sample"
    return {"target": "Barnard's Star", "gaia_dr3_source_id": SOURCE_ID, "source": REFERENCE_URL,
            "status": status, "catalog_wavelength_um": ARCHIVE_WAVELENGTH_UM, "usable_windows": usable_windows,
            "measured_offset_arcsec": None, "windows": windows}


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Check SPHEREx coverage and pixel quality for Barnard's Star")
    parser.add_argument("--manifest", type=Path, default=configured_path("PLANET_X_MANIFEST", "data/manifests/spherex-dr1.json"))
    parser.add_argument("--data-dir", type=Path, default=configured_path("PLANET_X_DATA_DIR", "data/samples"))
    parser.add_argument("--archive", action="store_true", help="Audit additional real DR1 and QR3 survey visits")
    parser.add_argument("--per-window", type=int, default=3, choices=range(1, 7),
                        help="Maximum distinct visits to inspect in each archive time window")
    parser.add_argument("--audit-dir", type=Path, default=configured_path(
        "PLANET_X_BARNARD_AUDIT_DIR", "data/samples/benchmark/barnard"), help="Directory for the verified audit cutouts")
    args = parser.parse_args()
    if args.archive:
        result = audit_archive(ImportQuota(args.audit_dir, DEFAULT_IMPORT_QUOTA_BYTES), args.per_window)
        print(json.dumps(result, indent=2))
        return
    observations = {record.epoch: record for record in load_manifest(args.manifest).observations}
    try:
        result = benchmark(args.data_dir, [observations[epoch] for epoch in DEMO_EPOCHS])
    except (DataError, KeyError) as exc:
        parser.exit(1, f"Could not check the Barnard benchmark: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
