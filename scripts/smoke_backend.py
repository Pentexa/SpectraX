import argparse
import json
import math
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

POSITION = {"ra": 269.45, "dec": 4.7}
EPOCH_A = "dr1-2025-10-01-d1"
EPOCH_B = "dr1-2026-03-11-d1"
CUBE = "dr1-coadd"


def get_json(base_url: str, path: str, **params):
    query = "?" + urlencode(params) if params else ""
    try:
        with urlopen(base_url + "/api/" + path + query, timeout=20) as response:
            return json.load(response)
    except HTTPError as error:
        body = error.read(1024).decode(errors="replace")
        raise RuntimeError(f"GET /api/{path}{query} returned {error.code}: {body}") from error


def require(condition: bool, message: str):
    if not condition:
        raise RuntimeError(message)


def verify(base_url: str):
    health = get_json(base_url, "health")
    require(health["status"] == "ok" and health["available_locally"] == 3, "Expected all three DR1 FITS files")

    comparison = get_json(base_url, "compare", **POSITION, fov=0.04, epoch_a=EPOCH_A, epoch_b=EPOCH_B,
                          mode="difference")
    alignment = comparison["alignment"]
    require(alignment["astrometric_offset_verified"], "DR1 registration did not pass")
    require(alignment["arithmetic_valid_fraction"] > 0.8, "Too few valid pixels in the DR1 difference")
    measurement = comparison["measurement"]
    require(math.isclose(measurement["difference"], 0.024914, abs_tol=0.0001), "Unexpected DR1 center-pixel difference")
    require(math.isclose(measurement["uncertainty"], 0.031968, abs_tol=0.0001), "Unexpected DR1 center-pixel uncertainty")
    grid = comparison["grid"]
    center = comparison["images"]["result"][grid["height"] // 2][grid["width"] // 2]
    require(math.isclose(center, measurement["difference"], abs_tol=1e-10), "Difference image and measurement disagree")

    spectrum = get_json(base_url, "spectrum", **POSITION, epoch=CUBE)
    channels = spectrum["channels"]
    wavelengths = [item["wavelength_um"] for item in channels]
    valid = [item for item in channels if item["flux"] is not None and math.isfinite(item["flux"])]
    missing = [item for item in channels if item["masked"] and item["flux"] is None]
    require(spectrum["time_mode"] == "multi_epoch_coadd", "Unexpected spectrum time mode")
    require(len(channels) == spectrum["expected_channels"] == 102, "Unexpected DR1 channel count")
    require(len(valid) == spectrum["available_channels"] == 100 and len(missing) == 2 and not spectrum["complete"],
            "Unexpected DR1 channel coverage")
    require(all(a < b for a, b in zip(wavelengths, wavelengths[1:])), "DR1 channels are out of order")

    groups = get_json(base_url, "layers", epoch=CUBE)["layers"]
    require([group["detector"] for group in groups] == list(range(1, 7)), "Expected six detector groups")
    for group in groups:
        detector = group["detector"]
        layer = get_json(base_url, f"layers/{detector}", **POSITION, fov=0.025, epoch=CUBE)
        require(layer["detector"] == detector and layer["channel"] == group["representative_channel"],
                f"Unexpected channel for detector {detector}")
        require(any(value is not None for row in layer["image"] for value in row), f"Empty layer for detector {detector}")
    print(f"DR1 API verified: {alignment['arithmetic_valid_fraction']:.1%} valid difference pixels, "
          f"{len(valid)}/{len(channels)} available channels, {len(groups)} detector layers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify the API against the manifest's real SPHEREx DR1 samples")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    verify(parser.parse_args().base_url.rstrip("/"))
