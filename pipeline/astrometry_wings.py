import numpy as np
from scipy.optimize import least_squares

from pipeline.catalog import DataError
from pipeline.images import read_image


def _fit_wing(dx, dy, signal, noise):
    # Normalize the profile at three pixels to avoid extrapolating a saturated peak.
    def residual(parameters):
        amplitude, background, offset_x, offset_y, core_squared, exponent, axis_ratio = parameters
        radius_squared = ((dx - offset_x) / axis_ratio)**2 + ((dy - offset_y) * axis_ratio)**2
        profile = ((core_squared + 9) / (core_squared + radius_squared))**exponent
        return (amplitude * profile + background - signal) / noise

    amplitude = max(float(np.percentile(signal, 80)), float(np.median(noise)))
    fit = least_squares(
        residual, [amplitude, 0, 0, 0, 1, 2, 1],
        bounds=([0, -np.inf, -1.5, -1.5, 1e-8, 0.8, 0.65], [np.inf, np.inf, 1.5, 1.5, 16, 6, 1.55]),
        loss="soft_l1", x_scale="jac", max_nfev=400,
    )
    residual_scale = np.median(abs(fit.fun)) / 0.67449
    if (not fit.success or residual_scale > 3 or fit.x[0] <= 5 * np.median(noise)
            or np.max(abs(fit.x[2:4])) >= 1.4):
        raise DataError("centroid_unavailable", "The saturation-wing profile did not pass the fit checks", 409)
    covariance = np.linalg.pinv(fit.jac.T @ fit.jac)[2:4, 2:4] * max(1, residual_scale**2)
    return fit.x[2:4], covariance, float(residual_scale)


def fit_saturated_wings(directory, record, expected):
    image = read_image(directory, record)
    x, y = map(float, image.wcs.world_to_pixel(expected))
    if image.variance is None or not np.isfinite([x, y]).all():
        raise DataError("centroid_unavailable", "The saturation-wing fit needs a valid coordinate and variance", 409)
    cx, cy = round(x), round(y)
    height, width = image.signal.shape
    if not (12 <= cx < width - 12 and 12 <= cy < height - 12):
        raise DataError("centroid_unavailable", "The saturation-wing fit needs a wider cutout", 409)
    region = np.s_[cy - 12:cy + 13, cx - 12:cx + 13]
    yy, xx = np.mgrid[region]
    dx, dy = xx - x, yy - y
    radius = np.hypot(dx, dy)
    signal, variance = image.signal[region], image.variance[region]
    valid = image.valid[region] & np.isfinite(variance) & (variance > 0)
    sky = signal[valid & (radius >= 9) & (radius < 12)]
    if sky.size < 30:
        raise DataError("centroid_unavailable", "Too few unmasked wing background pixels", 409)
    background = np.median(sky)
    sky_noise = 1.4826 * np.median(abs(sky - background))
    fits = []
    for inner, outer in ((1.8, 6.5), (2.8, 8.5)):
        selected = valid & (radius >= inner) & (radius < outer)
        quadrants = ((dx >= 0) * 2 + (dy >= 0))[selected]
        if np.min(np.bincount(quadrants, minlength=4)) < 6:
            raise DataError("centroid_unavailable", "The unmasked wings do not cover all quadrants", 409)
        fits.append(_fit_wing(dx[selected], dy[selected], signal[selected] - background,
                             np.hypot(np.sqrt(variance[selected]), sky_noise)))
    (offset, pixel_covariance, residual), (check, _, _) = fits
    delta = check - offset
    if np.linalg.norm(delta) > 0.4:
        raise DataError("centroid_unavailable", "The two wing windows disagree on the centroid", 409)
    pixel_covariance += np.outer(delta, delta)
    x, y = x + offset[0], y + offset[1]
    measured = image.wcs.pixel_to_world(x, y).icrs
    cardinal = image.wcs.pixel_to_world([x - 0.5, x + 0.5, x, x], [y, y, y - 0.5, y + 0.5]).icrs
    east, north = measured.spherical_offsets_to(cardinal)
    corners = np.stack((east.arcsec, north.arcsec))
    jacobian = corners[:, [1, 3]] - corners[:, [0, 2]]
    covariance = jacobian @ pixel_covariance @ jacobian.T
    if not np.isfinite(covariance).all() or np.linalg.eigvalsh(covariance)[0] <= 0:
        raise DataError("centroid_unavailable", "The wing fit has no usable centroid covariance", 409)
    return image, measured, covariance, {
        "ra": float(measured.ra.deg), "dec": float(measured.dec.deg), "snr": None,
        "method": "saturated_wings", "normalized_residual_mad": residual,
        "wing_window_delta_arcsec": float(np.linalg.norm(jacobian @ delta)),
        "centroid_covariance_arcsec2": covariance.tolist(),
    }
