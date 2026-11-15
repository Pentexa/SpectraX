import argparse
import json
import math
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

POSITION = {"ra": 269.45, "dec": 4.7}
EPOCH_A = "dr1-2025-10-01-d1"
EPOCH_B = "dr1-2026-03-11-d1"
CUBE = "dr1-coadd"
QR3_EPOCH = "qr3-2026-08-25-d1"
PHOTOMETRY_TARGET = {"ra": 269.448214, "dec": 4.695946}
MANIFEST = Path(__file__).resolve().parents[1] / "data/manifests/spherex-dr1.json"
WIDE_SKY_POSITION = {"ra": 60.8109955, "dec": 51.3404038}
WIDE_SKY_SHA256 = "f098a04d2fed64a051eaf56444c2f18fad84bd9bd1e15b1f964337a9a4139f31"
CYGNUS_POSITION = {"ra": 305.59875, "dec": 41.14888889}
CYGNUS_ARCHIVE_ID = "ivo://irsa.ipac/spherex_dr1?2025W18_1B_0023_2/D1"
CYGNUS_SHA256 = "16b3cb39f2b5b90f6567d4e29a18c2d292820dd8a86fb3cdc80a2d0d82012247"


def request_json(request: Request, timeout: int) -> tuple[int, dict]:
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        body = error.read(1024).decode(errors="replace")
        raise RuntimeError(f"{request.get_method()} {request.selector} returned {error.code}: {body}") from error


def get_json(base_url: str, path: str, *, timeout: int = 20, **params):
    query = "?" + urlencode(params) if params else ""
    return request_json(Request(base_url + "/api/" + path + query), timeout)[1]


def require(condition: bool, message: str):
    if not condition:
        raise RuntimeError(message)


def post_json(base_url: str, path: str, *, timeout: int = 20, **payload):
    request = Request(base_url + "/api/" + path, data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    return request_json(request, timeout)


def import_irsa_exposure(base_url: str, archive_id: str, **coverage):
    status, imported = post_json(base_url, "archive/import", timeout=110, archive_id=archive_id, **coverage)
    require(status == 201 and imported["available_locally"], f"Expected a fresh import of {archive_id}")
    return imported


def verify(base_url: str):
    health = get_json(base_url, "health")
    require(health["status"] == "ok" and health["products"] == health["available_locally"] == 4,
            "Expected all four manifest FITS files")
    releases = {item["id"]: item for item in get_json(base_url, "releases")["releases"]}
    require(releases["DR1"]["status"] == releases["QR3"]["status"] == "published", "Expected published DR1 and QR3")
    require(releases["DR2"]["status"] == "planned" and releases["DR3"]["status"] == "unannounced",
            "Unexpected DR2 or DR3 release status")
    qr3 = get_json(base_url, "datasets", release="QR3")
    require([item["epoch"] for item in qr3["observations"]] == [QR3_EPOCH] and not qr3["cubes"],
            "Unexpected QR3 products")
    targets = get_json(base_url, "targets")["targets"]
    require({item["id"] for item in targets} == {"barnard", "epsilon-indi-b", "wise-0855", "rw-aurigae", "r-draconis"},
            "Unexpected challenge target list")

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
    _, automatic = post_json(base_url, "compare/auto", **POSITION, fov=0.04, epochs=[EPOCH_B, EPOCH_A])
    require(automatic["measurement"] == measurement and automatic["selection"]["elapsed_days"] > 160,
            "Automatic pair selection did not reproduce the verified real-data difference")

    cross_release = get_json(base_url, "compare", **POSITION, fov=0.04, epoch_a=EPOCH_A, epoch_b=QR3_EPOCH,
                             mode="side_by_side")
    require(cross_release["epochs"]["b"]["release"] == "QR3" and cross_release["alignment"]["overlap_fraction"] > 0.8,
            "Expected aligned DR1 and QR3 images")
    require(cross_release["images"]["result"] is None, "Side-by-side comparison returned an arithmetic result")

    photometry = get_json(base_url, "photometry", **PHOTOMETRY_TARGET, epoch=EPOCH_A)
    require(photometry["method"] == "forced_epsf" and photometry["epoch"] == EPOCH_A, "Unexpected photometry model")
    require(math.isclose(photometry["flux_density_ujy"], 1428.9, rel_tol=0.02), "Unexpected DR1 ePSF flux")
    require(math.isclose(photometry["statistical_error_ujy"], 53.18, rel_tol=0.02), "Unexpected DR1 ePSF flux error")
    require(photometry["snr"] > 20 and photometry["reduced_chi_square"] < 5, "Unreliable DR1 reference fit")
    _, series = post_json(base_url, "source-series", **PHOTOMETRY_TARGET, epochs=[EPOCH_B, EPOCH_A])
    require([item["epoch"] for item in series["samples"]] == [EPOCH_A, EPOCH_B]
            and series["samples"][0]["photometry"] == photometry, "Unexpected source time series")

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
    print(f"SPHEREx API verified: {alignment['arithmetic_valid_fraction']:.1%} valid DR1 difference pixels, "
          f"{len(valid)}/{len(channels)} available channels, {len(groups)} detector layers, aligned QR3 cutout, "
          f"DR1 ePSF flux {photometry['flux_density_ujy']:.1f} uJy")


def verify_live_archive(base_url: str):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    observations = {item["epoch"]: item for item in manifest["observations"]}
    for epoch in (EPOCH_A, QR3_EPOCH):
        observation = observations[epoch]
        release = observation["release"]
        observation_id = observation["observation_id"]
        archive_id = f"ivo://irsa.ipac/spherex_{release.lower()}?{observation_id}/D{observation['detector']}"
        coverage = observation["coverage"]
        results = get_json(
            base_url, "archive/search", timeout=45, ra=coverage["ra"], dec=coverage["dec"], release=release,
            start_mjd=observation["observation_start_mjd"] - 0.00001,
            end_mjd=observation["observation_end_mjd"] + 0.00001, limit=30,
        )
        require(any(item["archive_id"] == archive_id for item in results["observations"]),
                f"Live IRSA catalog did not return {archive_id}")
        imported = import_irsa_exposure(base_url, archive_id, **coverage)
        require(imported["sha256"] == observation["sha256"] and imported["size_bytes"] == observation["size_bytes"],
                f"Live IRSA FITS differs from the verified manifest for {archive_id}")
        if release == "DR1":
            photometry = get_json(base_url, "photometry", **PHOTOMETRY_TARGET, epoch=imported["epoch"])
            require(math.isclose(photometry["flux_density_ujy"], 1428.9, rel_tol=0.02),
                    "Unexpected ePSF flux for the live DR1 import")
        print(f"Live IRSA verified {release} {observation_id}, {imported['size_bytes']} bytes, SHA-256 matched")


def verify_wide_sky(base_url: str):
    local = get_json(base_url, "spectrum", **POSITION)
    require(local["epoch"] == CUBE, "Coordinate lookup did not reuse the manifest cube")
    remote = get_json(base_url, "spectrum", timeout=260, **WIDE_SKY_POSITION)
    require(remote["epoch"] == "dr1-npix445" and remote["dataset"]["sha256"] == WIDE_SKY_SHA256,
            "Wrong IRSA cube for the second sky field")
    require(remote["available_channels"] == 100 and len(remote["channels"]) == 102,
            "Unexpected channel counts in the second sky field")
    for result, brightness in ((local, 0.06335347), (remote, 3.54918933)):
        channel = min(result["channels"], key=lambda item: abs(item["wavelength_um"] - 4.6))
        require(math.isclose(channel["flux"], brightness, abs_tol=1e-6), "Unexpected 4.6 um surface brightness")
        require(channel["uncertainty"] is None and channel["nhits"] > 0, "Unexpected channel quality metadata")
    layer = get_json(base_url, "layers/6", **WIDE_SKY_POSITION, fov=0.025, epoch=remote["epoch"])
    require(any(pixel is not None for row in layer["image"] for pixel in row), "Empty layer in the second sky field")
    print("Two real DR1 fields verified, including the archived tile selected by coordinate")

    imported = import_irsa_exposure(base_url, CYGNUS_ARCHIVE_ID, **CYGNUS_POSITION, fov=0.05)
    require(imported["sha256"] == CYGNUS_SHA256, "Cygnus FITS differs from the reference")
    fit = get_json(base_url, "photometry", **CYGNUS_POSITION, epoch=imported["epoch"])
    require("low_snr" in fit["quality_flags"] and abs(fit["snr"]) < 1, "Cygnus fit must be flagged as low SNR")
    require(math.isclose(fit["flux_density_ujy"], 19.37, abs_tol=1), "Unexpected Cygnus ePSF flux")
    require(math.isclose(fit["statistical_error_ujy"], 42.57, abs_tol=1), "Unexpected Cygnus statistical uncertainty")
    print(f"Cygnus low-SNR reference verified, {fit['flux_density_ujy']:.2f} ± {fit['statistical_error_ujy']:.2f} uJy")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify the API against the manifest's real SPHEREx DR1 and QR3 samples")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--live-archive", action="store_true", help="Also search IRSA and download into a fresh import directory")
    parser.add_argument("--wide-sky", action="store_true", help="Verify a second DR1 tile from the IRSA cloud archive")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    verify(base_url)
    if args.live_archive:
        verify_live_archive(base_url)
    if args.wide_sky:
        verify_wide_sky(base_url)
