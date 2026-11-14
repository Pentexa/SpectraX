import argparse
import json
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time
from dotenv import load_dotenv

from pipeline.catalog import DataError, Observation, load_manifest
from pipeline.images import Image, read_image
from pipeline.ingest import ROOT, configured_path

REFERENCE_URL = "https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=barnard+star&submit=SIMBAD+search"
SOURCE_ID = "4472832130942575872"
DEMO_EPOCHS = ("dr1-2025-10-01-d1", "dr1-2026-03-11-d1")


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


def benchmark(data_dir: Path, observations: list[Observation]) -> dict:
    epochs = []
    positions = []
    times = []
    for observation in sorted(observations, key=lambda item: item.observation_start_mjd):
        time = Time((observation.observation_start_mjd + observation.observation_end_mjd) / 2,
                    format="mjd", scale="utc")
        position = _predicted_position(time)
        image = read_image(data_dir, observation)
        epochs.append({"epoch": observation.epoch, "midpoint_utc": time.isot + "Z",
                       "observation_id": observation.observation_id, **_coverage(image, position)})
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


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Check whether the two demo exposures can test Barnard's Star motion")
    parser.add_argument("--manifest", type=Path, default=configured_path("PLANET_X_MANIFEST", "data/manifests/spherex-dr1.json"))
    parser.add_argument("--data-dir", type=Path, default=configured_path("PLANET_X_DATA_DIR", "data/samples"))
    args = parser.parse_args()
    observations = {record.epoch: record for record in load_manifest(args.manifest).observations}
    try:
        result = benchmark(args.data_dir, [observations[epoch] for epoch in DEMO_EPOCHS])
    except (DataError, KeyError) as exc:
        parser.exit(1, f"Could not check the Barnard benchmark: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
