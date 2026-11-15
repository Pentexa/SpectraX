from collections.abc import Callable
from math import hypot, sqrt
from pathlib import Path
from typing import Annotated

from astropy.coordinates import SkyCoord
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from pipeline.catalog import DataError, Observation
from pipeline.photometry import measure_source
from pipeline.targets import get_target

EpochId = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")]


class SourceSeriesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epochs: list[EpochId] = Field(min_length=1, max_length=24)
    ra: FiniteFloat | None = Field(default=None, ge=0, lt=360)
    dec: FiniteFloat | None = Field(default=None, ge=-90, le=90)
    target_id: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_inputs(self):
        if len(set(self.epochs)) != len(self.epochs):
            raise ValueError("Each epoch must be specified once")
        if self.target_id is None and (self.ra is None or self.dec is None):
            raise ValueError("Provide both ra and dec or a target_id")
        if self.target_id is not None and (self.ra is not None or self.dec is not None):
            raise ValueError("Provide coordinates or a target_id")
        return self


def _same_bandpass(a: dict, b: dict) -> bool:
    return (a["detector"], a["photometry"]["calibration"]) == (b["detector"], b["photometry"]["calibration"]) and (
        abs(a["photometry"]["wavelength_um"] - b["photometry"]["wavelength_um"])
        <= 0.25 * min(a["photometry"]["bandwidth_um"], b["photometry"]["bandwidth_um"])
    )


def _light_curves(samples: list[dict]) -> list[dict]:
    groups: list[list[dict]] = []
    for sample in samples:
        if sample["photometry"] is None:
            continue
        for group in groups:
            if all(_same_bandpass(sample, point) for point in group):
                group.append(sample)
                break
        else:
            groups.append([sample])
    result = []
    for group in groups:
        stackable = [point for point in group if "high_residual" not in point["photometry"]["quality_flags"]]
        usable = [point for point in stackable if "low_snr" not in point["photometry"]["quality_flags"]]
        stack = None
        if len(stackable) >= 2:
            weights = [1 / point["photometry"]["statistical_error_ujy"]**2 for point in stackable]
            total_weight = sum(weights)
            flux = sum(weight * point["photometry"]["flux_density_ujy"] for weight, point in zip(weights, stackable))
            stack = {"flux_density_ujy": flux / total_weight, "statistical_error_ujy": 1 / sqrt(total_weight),
                     "epochs": [point["epoch"] for point in stackable]}
        change = None
        if len(usable) >= 2 and usable[-1]["mjd"] > usable[0]["mjd"]:
            first, last = usable[0], usable[-1]
            fit_a, fit_b = first["photometry"], last["photometry"]
            difference = fit_b["flux_density_ujy"] - fit_a["flux_density_ujy"]
            error = hypot(fit_a["statistical_error_ujy"], fit_b["statistical_error_ujy"])
            change = {"epoch_a": first["epoch"], "epoch_b": last["epoch"], "elapsed_days": last["mjd"] - first["mjd"],
                      "flux_change_ujy": difference, "statistical_error_ujy": error, "snr": difference / error}
        result.append({
            "detector": group[0]["detector"], "wavelength_um": group[0]["photometry"]["wavelength_um"],
            "epochs": [point["epoch"] for point in group], "change": change, "weighted_mean": stack,
        })
    return result


def source_series(request: SourceSeriesRequest, locate: Callable[[str], tuple[Observation, Path]]) -> dict:
    target = get_target(request.target_id) if request.target_id else None
    selected = sorted((locate(epoch) for epoch in request.epochs),
                      key=lambda item: (item[0].observation_start_mjd, item[0].detector or 0, item[0].epoch))
    samples = []
    visits: dict[tuple[str, str], dict] = {}
    seen = set()
    for observation, directory in selected:
        identity = (observation.release, observation.observation_id, observation.detector, observation.band)
        if identity in seen:
            raise DataError("duplicate_observation", "Multiple epochs identify the same physical exposure and detector")
        seen.add(identity)
        mjd = (observation.observation_start_mjd + observation.observation_end_mjd) / 2
        ra, dec = request.ra, request.dec
        if target:
            position = target.position(mjd)
            ra, dec = position.ra.deg, position.dec.deg
        sample = {"epoch": observation.epoch, "release": observation.release, "observation_id": observation.observation_id,
                  "detector": observation.detector, "mjd": mjd, "ra": ra, "dec": dec,
                  "photometry": None, "error": None}
        try:
            sample["photometry"] = measure_source(directory, observation, ra, dec).model_dump()
        except DataError as exc:
            sample["error"] = {"code": exc.code, "message": str(exc)}
        samples.append(sample)
        key = (observation.release, observation.observation_id)
        visit = visits.setdefault(key, {"release": key[0], "observation_id": key[1], "mjd": mjd, "epochs": []})
        visit["epochs"].append(observation.epoch)
    predicted = None
    if target and samples[-1]["mjd"] > samples[0]["mjd"]:
        first, last = samples[0], samples[-1]
        start = SkyCoord(first["ra"], first["dec"], unit="deg", frame="icrs")
        end = SkyCoord(last["ra"], last["dec"], unit="deg", frame="icrs")
        east, north = start.spherical_offsets_to(end)
        predicted = {"epoch_a": first["epoch"], "epoch_b": last["epoch"], "elapsed_days": last["mjd"] - first["mjd"],
                     "east_arcsec": east.arcsec, "north_arcsec": north.arcsec}
    return {
        "target_id": request.target_id, "quantity": "source_flux_density",
        "predicted_catalog_offset_arcsec": predicted,
        "samples": samples, "visits": list(visits.values()), "light_curves": _light_curves(samples),
        "warnings": [
            "Visit spectra contain only measured detector samples.",
            "Changes and weighted means use independent statistical errors. Agreement in calibration and wavelength is required.",
        ],
    }
