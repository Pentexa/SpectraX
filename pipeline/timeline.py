import numpy as np
from astropy.wcs import NoConvergence
from pydantic import ConfigDict, Field, FiniteFloat, field_validator

from pipeline.catalog import DataError, Position
from pipeline.compare import _aligned, _bandpass, nullable_flags, nullable_pixels, output_grid
from pipeline.images import read_image
from pipeline.source_series import EpochId


class TimelineRequest(Position):
    model_config = ConfigDict(extra="forbid")
    fov: FiniteFloat = Field(ge=0.01, le=0.2)
    epochs: list[EpochId] = Field(min_length=3, max_length=8)

    @field_validator("epochs")
    @classmethod
    def distinct_epochs(cls, epochs):
        if len(set(epochs)) != len(epochs):
            raise ValueError("Each epoch must be specified once")
        return epochs


def build_timeline(request: TimelineRequest, locate):
    selected = sorted((locate(epoch) for epoch in request.epochs),
                      key=lambda item: (item[0].observation_start_mjd, item[0].epoch))
    identities = {(record.source, record.observation_id, record.detector) for record, _ in selected}
    if len(identities) != len(selected):
        raise DataError("duplicate_observation", "Select each physical exposure and detector once")
    if len({record.observation_start_mjd for record, _ in selected}) < 3:
        raise DataError("insufficient_epochs", "Timeline needs observations from at least three distinct times")
    native_scale = max(read_image(directory, record).pixel_scale for record, directory in selected)
    grid, shape = output_grid(request, native_scale)
    center = grid.pixel_to_world(shape[1] // 2, shape[0] // 2)
    first = None
    frames = []
    for record, directory in selected:
        image = read_image(directory, record)
        if first is None:
            first = image.unit
        if not image.unit.is_equivalent(first):
            raise DataError("incompatible_units", "Timeline exposures need compatible brightness units")
        try:
            pixels, _, flags = _aligned(image, grid, shape)
            wavelength, bandwidth = _bandpass(image, center) if image.spectral is not None else (np.nan, np.nan)
        except (ValueError, NoConvergence, RuntimeError) as exc:
            raise DataError("alignment_failed", f"Timeline reprojection failed for {record.epoch}") from exc
        frames.append({
            "epoch": record.epoch, "observation_id": record.observation_id,
            "mjd": record.observation_start_mjd, "release": record.release, "detector": record.detector,
            "wavelength_um": float(wavelength) if np.isfinite(wavelength) else None,
            "bandwidth_um": float(bandwidth) if np.isfinite(bandwidth) else None,
            "coverage": float(np.isfinite(pixels).mean()), "pixels": nullable_pixels(pixels * image.unit.to(first)),
            "flags": nullable_flags(flags),
        })
    if len({frame["mjd"] for frame in frames if frame["coverage"] > 0}) < 3:
        raise DataError("insufficient_coverage", "At least three selected images must cover the requested field", 404)
    matching = len({record.comparison_key for record, _ in selected}) == 1 and all(
        a["wavelength_um"] is not None and b["wavelength_um"] is not None
        and a["bandwidth_um"] is not None and b["bandwidth_um"] is not None
        and abs(a["wavelength_um"] - b["wavelength_um"]) <= 0.25 * min(a["bandwidth_um"], b["bandwidth_um"])
        for a in frames for b in frames
    )
    return {"grid": {"width": shape[1], "height": shape[0], "wcs": dict(grid.to_header())},
            "unit": first.to_string(), "matching_bandpasses": matching, "frames": frames}
