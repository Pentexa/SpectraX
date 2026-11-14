from pathlib import Path
from typing import Literal

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import NoConvergence
from photutils.psf import ImagePSF
from pydantic import BaseModel, FiniteFloat

from pipeline.catalog import DataError, Observation, data_path
from pipeline.images import read_image

FIT_RADIUS = 4
QualityFlag = Literal["masked_fit_pixels", "low_snr", "high_residual"]


class Photometry(BaseModel):
    epoch: str
    release: str
    observation_id: str
    observation_start_mjd: float
    calibration: str
    ra: float
    dec: float
    method: Literal["forced_epsf"] = "forced_epsf"
    flux_density_ujy: FiniteFloat
    statistical_error_ujy: FiniteFloat
    snr: FiniteFloat
    wavelength_um: float
    bandwidth_um: float
    reduced_chi_square: FiniteFloat
    pixels_used: int
    fit_pixel_flags: int
    quality_flags: list[QualityFlag]
    pixel_solid_angle_sr: float


def _local_epsf(path: Path, x: float, y: float, detector: int | None) -> ImagePSF:
    try:
        with fits.open(path) as hdus:
            header = hdus["IMAGE"].header
            model_hdu = hdus["EPSF"]
            table = model_hdu.data
            if model_hdu.header["DETCOORD"].strip().lower() != "sky":
                raise ValueError("Unexpected ePSF detector orientation")
            if int(model_hdu.header["DETECTOR"]) != detector:
                raise ValueError("ePSF detector differs from the image")
            sample_y, sample_x = (int(model_hdu.header[key]) for key in ("OVSMPY", "OVSMPX"))
            parent_x = x + 1 - float(header["CRPIX1A"])
            parent_y = y + 1 - float(header["CRPIX2A"])
            distances = np.hypot(table["XCENTER"] - parent_x, table["YCENTER"] - parent_y)
            finite = np.isfinite(distances)
            if not finite.any() or min(sample_x, sample_y) <= 0:
                raise ValueError("Invalid ePSF sampling or zone centers")
            row = table[np.argmin(np.where(finite, distances, np.inf))]
            data = np.asarray(row["EPSF"], dtype=float)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise DataError("invalid_epsf", f"Cannot read the observation ePSF: {exc}") from exc

    integral = data.sum()
    if data.shape != (33, 33) or not np.isfinite(data).all() or integral <= 0:
        raise DataError("invalid_epsf", "The observation ePSF has an invalid image or normalization")
    # The FITS grid has unit sum. ImagePSF needs fractions on the native pixel grid.
    data = data * (sample_x * sample_y / integral)
    return ImagePSF(data, x_0=x, y_0=y, oversampling=(sample_y, sample_x))


def measure_source(data_dir: Path, observation: Observation, ra: float, dec: float) -> Photometry:
    image = read_image(data_dir, observation)
    if image.spectral is None or image.variance is None or image.flags is None or "EPSF" not in image.metadata["quality_hdus"]:
        raise DataError("photometry_unavailable", "Source photometry requires a SPHEREx ePSF, wavelength WCS, and variance", 409)
    if not image.unit.is_equivalent(u.Jy / u.sr):
        raise DataError("photometry_unavailable", "Source photometry requires a surface brightness image", 409)

    try:
        x, y = map(float, image.wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg", frame="icrs")))
    except NoConvergence as exc:
        raise DataError("outside_coverage", "The source position could not be mapped into the exposure", 404) from exc
    height, width = image.signal.shape
    if not (-0.5 <= x < width - 0.5 and -0.5 <= y < height - 0.5):
        raise DataError("outside_coverage", "The source position is outside the exposure", 404)

    cx, cy = int(np.floor(x + 0.5)), int(np.floor(y + 0.5))
    radius = FIT_RADIUS
    if not (radius <= cx < width - radius and radius <= cy < height - radius):
        raise DataError("photometry_unavailable", "The exposure does not contain a complete fit window at this position", 409)
    region = np.s_[cy - radius:cy + radius + 1, cx - radius:cx + radius + 1]
    variance = image.variance[region]
    usable = image.valid[region] & np.isfinite(variance) & (variance > 0)
    core = np.s_[radius - 1:radius + 2, radius - 1:radius + 2]
    if not usable[core].all() or usable.sum() < usable.size / 2:
        raise DataError("photometry_unavailable", "Quality flags or missing variance exclude too many fit pixels", 409)

    model = _local_epsf(data_path(data_dir, observation), x, y, image.metadata["detector"])
    yy, xx = np.mgrid[cy - radius:cy + radius + 1, cx - radius:cx + radius + 1]
    profile = model(xx, yy)[usable]
    weights = 1 / variance[usable]
    signal = image.signal[region][usable]

    # Centering the profile removes the constant sky term from the weighted fit.
    mean_profile = np.average(profile, weights=weights)
    centered_profile = profile - mean_profile
    information = np.sum(weights * centered_profile**2)
    if not np.isfinite(information) or information <= 0:
        raise DataError("invalid_epsf", "The ePSF cannot constrain the source flux")
    mean_signal = np.average(signal, weights=weights)
    amplitude = np.sum(weights * centered_profile * (signal - mean_signal)) / information
    residual = signal - mean_signal - amplitude * centered_profile
    reduced_chi_square = np.sum(weights * residual**2) / (len(signal) - 2)
    snr = amplitude * np.sqrt(information)
    if not np.all(np.isfinite([amplitude, reduced_chi_square, snr])):
        raise DataError("photometry_unavailable", "The source fit did not produce a finite result", 409)

    # Estimate the local pixel area from the celestial WCS, including distortion.
    left, right, bottom, top = image.wcs.pixel_to_world([x - 0.5, x + 0.5, x, x], [y, y, y - 0.5, y + 0.5])
    east_x, north_x = left.spherical_offsets_to(right)
    east_y, north_y = bottom.spherical_offsets_to(top)
    area = abs(east_x.rad * north_y.rad - east_y.rad * north_x.rad)
    if not np.isfinite(area) or area <= 0:
        raise DataError("invalid_fits", "The celestial WCS gives an invalid local pixel area")
    conversion = (area * u.sr * image.unit).to_value(u.uJy)

    wavelength, bandwidth = image.spectral.wcs_pix2world([[x, y]], 0)[0]
    wave_unit, width_unit = image.spectral.wcs.cunit
    if not np.all(np.isfinite([wavelength, bandwidth])) or min(wavelength, bandwidth) <= 0:
        raise DataError("photometry_unavailable", "The wavelength WCS does not cover the source position", 409)
    quality_flags: list[QualityFlag] = []
    if not usable.all():
        quality_flags.append("masked_fit_pixels")
    if snr < 5:
        quality_flags.append("low_snr")
    if reduced_chi_square > 5:
        quality_flags.append("high_residual")
    return Photometry(
        epoch=observation.epoch, release=observation.release, observation_id=observation.observation_id,
        observation_start_mjd=observation.observation_start_mjd, calibration=observation.calibration, ra=ra, dec=dec,
        flux_density_ujy=amplitude * conversion, statistical_error_ujy=conversion / np.sqrt(information),
        snr=snr, wavelength_um=wave_unit.to(u.um, wavelength),
        bandwidth_um=width_unit.to(u.um, bandwidth), reduced_chi_square=reduced_chi_square,
        pixels_used=len(signal), fit_pixel_flags=int(np.bitwise_or.reduce(image.flags[region].ravel())),
        quality_flags=quality_flags, pixel_solid_angle_sr=area,
    )
