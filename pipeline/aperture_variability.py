from math import copysign, hypot

import numpy as np
from astropy import units as u
from astropy.stats import sigma_clip
from astropy.wcs import NoConvergence
from photutils.aperture import CircularAperture

from pipeline.catalog import DataError, data_path
from pipeline.images import read_image
from pipeline.photometry import _local_epsf

RADII = (2.0, 2.5)
FRACTIONAL_SYSTEMATIC = 0.05


def _measure(record, directory, ra, dec):
    image = read_image(directory, record)
    if image.flags is None or image.variance is None or image.spectral is None or not image.unit.is_equivalent(u.Jy / u.sr):
        return None
    x, y = map(float, image.wcs.world_to_pixel_values(ra, dec))
    height, width = image.signal.shape
    if not np.isfinite([x, y]).all():
        return None
    cx, cy = round(x), round(y)
    if not (10 <= cx < width - 10 and 10 <= cy < height - 10):
        return None
    cut = np.s_[cy - 10:cy + 11, cx - 10:cx + 11]
    yy, xx = np.mgrid[cut]
    signal, variance = image.signal[cut], image.variance[cut]
    usable = image.valid[cut] & np.isfinite(variance) & (variance > 0)
    distance = np.hypot(xx - x, yy - y)
    sky = sigma_clip(signal[usable & (distance >= 6) & (distance < 10)], sigma=3).compressed()
    if sky.size < 30:
        return None
    background = np.median(sky)
    background_error = 1.2533 * np.std(sky, ddof=1) / np.sqrt(sky.size)
    model = _local_epsf(data_path(directory, record), x, y, image.metadata["detector"])
    left, right, bottom, top = image.wcs.pixel_to_world([x - .5, x + .5, x, x], [y, y, y - .5, y + .5])
    east_x, north_x = left.spherical_offsets_to(right)
    east_y, north_y = bottom.spherical_offsets_to(top)
    area = abs(east_x.rad * north_y.rad - east_y.rad * north_x.rad)
    conversion = (area * u.sr * image.unit).to_value(u.uJy)
    wavelength, bandwidth = image.spectral.wcs_pix2world([[x, y]], 0)[0]
    wave_unit, width_unit = image.spectral.wcs.cunit
    if not np.all(np.isfinite([wavelength, bandwidth, area])) or min(wavelength, bandwidth, area) <= 0:
        return None

    measurements = []
    for radius in RADII:
        center = (x - (cx - 10), y - (cy - 10))
        weights = CircularAperture(center, radius).to_mask(method="exact").to_image(signal.shape)
        aperture = weights > 0
        if not usable[aperture].all():
            return None
        weight = weights[aperture]
        enclosed = np.sum(model(xx[aperture], yy[aperture]) * weight)
        if not 0.9 <= enclosed <= 1.05:
            return None
        flux = np.sum(weight * (signal[aperture] - background)) * conversion / enclosed
        error = hypot(np.sqrt(np.sum(weight**2 * variance[aperture])), weight.sum() * background_error)
        error *= conversion / enclosed
        if not np.isfinite([flux, error]).all() or error <= 0 or flux < 5 * error:
            return None
        measurements.append({"flux_ujy": float(flux), "statistical_error_ujy": float(error)})

    return wave_unit.to(u.um, wavelength), width_unit.to(u.um, bandwidth), measurements


def aperture_change(selected, samples):
    if len(selected) != 2:
        return None
    (a, _), (b, _) = selected
    if a.comparison_key != b.comparison_key or a.observation_end_mjd >= b.observation_start_mjd:
        return None
    try:
        measurements = [_measure(record, directory, sample["ra"], sample["dec"])
                        for (record, directory), sample in zip(selected, samples)]
    except (DataError, NoConvergence):
        return None
    first, second = measurements
    if first is None or second is None or abs(first[0] - second[0]) > 0.25 * min(first[1], second[1]):
        return None

    results = []
    for radius, sa, sb in zip(RADII, first[2], second[2]):
        fa, fb = sa["flux_ujy"], sb["flux_ujy"]
        uncertainty = hypot(sa["statistical_error_ujy"], sb["statistical_error_ujy"],
                            FRACTIONAL_SYSTEMATIC * fa, FRACTIONAL_SYSTEMATIC * fb)
        change = fb - fa
        results.append({"radius_pixels": radius, "a": sa, "b": sb, "change_ujy": change,
                        "uncertainty_ujy": uncertainty, "snr": change / uncertainty})

    primary, check = results
    if (min(abs(primary["snr"]), abs(check["snr"])) < 3
            or copysign(1, primary["change_ujy"]) != copysign(1, check["change_ujy"])
            or abs(primary["change_ujy"] - check["change_ujy"]) > primary["uncertainty_ujy"]):
        return None
    return {
        "method": "aperture_with_epsf_correction",
        "wavelength_a_um": float(first[0]), "wavelength_b_um": float(second[0]),
        "elapsed_days": samples[1]["mjd"] - samples[0]["mjd"],
        "fractional_systematic_per_epoch": FRACTIONAL_SYSTEMATIC,
        "measurement": primary, "radius_check": check,
    }
