from collections.abc import Callable
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import NoConvergence
from pydantic import Field, FiniteFloat
from scipy.optimize import least_squares

from pipeline.catalog import DataError, Observation, Position
from pipeline.compare import output_grid
from pipeline.photometry import _fit_window
from pipeline.registration import assess_registration
from pipeline.source_series import EpochId, SourceSeriesRequest
from pipeline.targets import get_target

MAX_OFFSET_PIXELS = 1.25


class AstrometryRequest(SourceSeriesRequest):
    epochs: list[EpochId] = Field(min_length=2, max_length=2)
    fov: FiniteFloat = Field(default=0.05, ge=0.02, le=0.2)


def _unavailable(reason: str) -> DataError:
    return DataError("centroid_unavailable", reason, 409)


def _centroid(directory: Path, observation: Observation, expected: SkyCoord):
    image, model, (x, y), _, _, xx, yy, signal, weights = _fit_window(
        directory, observation, expected.ra.deg, expected.dec.deg,
    )
    root_weights = np.sqrt(weights)
    profile = model(xx, yy)
    design = np.column_stack((profile, np.ones_like(profile))) * root_weights[:, None]

    def residual(parameters):
        amplitude, background, dx, dy = parameters
        return (model.evaluate(xx, yy, amplitude, x + dx, y + dy) + background - signal) * root_weights

    try:
        (amplitude, background), _, rank, _ = np.linalg.lstsq(design, root_weights * signal, rcond=None)
        if rank < 2 or amplitude <= 0:
            raise _unavailable("No positive source amplitude at the supplied position")
        fit = least_squares(
            residual, [amplitude, background, 0, 0], x_scale="jac", max_nfev=80,
            bounds=([0, -np.inf, -MAX_OFFSET_PIXELS, -MAX_OFFSET_PIXELS],
                    [np.inf, np.inf, MAX_OFFSET_PIXELS, MAX_OFFSET_PIXELS]),
        )
        reduced_chi_square = float(fit.fun @ fit.fun / (len(signal) - 4))
        if not fit.success or np.max(np.abs(fit.x[2:])) >= 0.99 * MAX_OFFSET_PIXELS or reduced_chi_square > 5:
            raise _unavailable("The centroid failed the fit, residual or position checks")
        if np.linalg.matrix_rank(fit.jac) < 4:
            raise _unavailable("The image does not constrain the centroid")
        covariance = np.linalg.inv(fit.jac.T @ fit.jac) * max(1, reduced_chi_square)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise _unavailable("The local ePSF fit could not constrain the centroid") from exc

    snr = fit.x[0] / np.sqrt(covariance[0, 0])
    if not np.isfinite(snr) or snr < 5:
        raise _unavailable("The fitted source has signal-to-noise below 5")

    x, y = x + fit.x[2], y + fit.x[3]
    measured = image.wcs.pixel_to_world(x, y).icrs
    neighbors = image.wcs.pixel_to_world([x - 0.5, x + 0.5, x, x], [y, y, y - 0.5, y + 0.5]).icrs
    east, north = measured.spherical_offsets_to(neighbors)
    sky_jacobian = np.stack((east.arcsec, north.arcsec), axis=0)
    sky_jacobian = sky_jacobian[:, [1, 3]] - sky_jacobian[:, [0, 2]]
    sky_covariance = sky_jacobian @ covariance[2:, 2:] @ sky_jacobian.T
    if not np.isfinite(sky_covariance).all() or np.linalg.eigvalsh(sky_covariance)[0] <= 0:
        raise _unavailable("The fitted sky position has no usable statistical covariance")
    metrics = {"ra": float(measured.ra.deg), "dec": float(measured.dec.deg), "snr": float(snr),
               "reduced_chi_square": reduced_chi_square, "statistical_covariance_arcsec2": sky_covariance.tolist()}
    return image, measured, sky_covariance, metrics


def astrometry(request: AstrometryRequest, locate: Callable[[str], tuple[Observation, Path]]) -> dict:
    selected = sorted((locate(epoch) for epoch in request.epochs), key=lambda item: item[0].observation_start_mjd)
    a, b = [record for record, _ in selected]
    if a.observation_id == b.observation_id or a.observation_end_mjd >= b.observation_start_mjd:
        raise DataError("duplicate_observation", "Astrometry requires two observations at distinct times")
    if (a.detector, a.band, a.source) != (b.detector, b.band, b.source):
        raise DataError("incompatible_epochs", "Astrometry requires matching source and detector bands")
    target = get_target(request.target_id) if request.target_id else None
    fits, samples, positions = [], [], []
    for record, directory in selected:
        mjd = (record.observation_start_mjd + record.observation_end_mjd) / 2
        position = (target.position(mjd) if target else
                    SkyCoord(request.ra, request.dec, unit="deg", frame="icrs"))
        positions.append(position)
        sample = {"epoch": record.epoch, "mjd": mjd,
                  "input_position": {"ra": float(position.ra.deg), "dec": float(position.dec.deg)},
                  "centroid": None, "error": None}
        try:
            result = _centroid(directory, record, position)
        except DataError as exc:
            sample["error"] = {"code": exc.code, "message": str(exc)}
        else:
            fits.append(result)
            sample["centroid"] = result[3]
        samples.append(sample)

    predicted = None
    if target:
        east, north = positions[0].spherical_offsets_to(positions[1])
        predicted = {"east": float(east.arcsec), "north": float(north.arcsec)}
    report = {"target_id": request.target_id, "samples": samples, "status": "centroid_unavailable",
              "predicted_catalog_offset_arcsec": predicted, "registration": None, "measured_offset_arcsec": None,
              "elapsed_days": samples[1]["mjd"] - samples[0]["mjd"]}
    if len(fits) < 2:
        return report

    (image_a, center_a, covariance_a, _), (image_b, center_b, covariance_b, _) = fits
    midpoint = positions[0].directional_offset_by(positions[0].position_angle(positions[1]),
                                                  positions[0].separation(positions[1]) / 2)
    grid, shape = output_grid(Position(ra=midpoint.ra.deg, dec=midpoint.dec.deg, fov=request.fov),
                              max(image_a.pixel_scale, image_b.pixel_scale))
    report["status"] = "registration_unverified"
    try:
        registration = assess_registration(image_a, image_b, grid, shape, exclude=(center_a, center_b))
    except (ValueError, NoConvergence, RuntimeError):
        return report
    report["registration"] = registration
    if registration["status"] != "passed":
        return report

    frame = midpoint.skyoffset_frame()
    first, second = center_a.transform_to(frame), center_b.transform_to(frame)
    raw = np.array([(second.lon - first.lon).to_value(u.arcsec), (second.lat - first.lat).to_value(u.arcsec)])
    offset = registration["median_offset_arcsec"]
    corrected = raw - [offset["east"], offset["north"]]
    # Treat the full field RMS as a systematic floor on each axis.
    covariance = covariance_a + covariance_b + np.eye(2) * registration["scatter_rms_arcsec"]**2
    return report | {"status": "measured", "measured_offset_arcsec": {
        "east": float(corrected[0]), "north": float(corrected[1]),
        "uncertainty_covariance_arcsec2": covariance.tolist(),
        "significance": float(np.sqrt(corrected @ np.linalg.solve(covariance, corrected))),
        "significance_kind": "mahalanobis_distance",
    }}
