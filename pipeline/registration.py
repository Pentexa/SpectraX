import numpy as np
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from scipy.ndimage import maximum_filter
from scipy.spatial import cKDTree

from pipeline.images import Image

MIN_MATCHES = 5
MAX_REFERENCE_SOURCES = 128


def _centroids(image: Image, grid: WCS, shape: tuple[int, int]) -> SkyCoord:
    height, width = shape
    corners = grid.pixel_to_world([-0.5, width - 0.5, -0.5, width - 0.5],
                                  [-0.5, -0.5, height - 0.5, height - 0.5])
    x, y = image.wcs.world_to_pixel(corners)
    if not np.all(np.isfinite([x, y])):
        return SkyCoord([], [], unit="deg", frame="icrs")

    height, width = image.signal.shape
    left, right = max(0, int(np.floor(x.min()))), min(width, int(np.ceil(x.max())) + 1)
    top, bottom = max(0, int(np.floor(y.min()))), min(height, int(np.ceil(y.max())) + 1)
    if right - left < 5 or bottom - top < 5:
        return SkyCoord([], [], unit="deg", frame="icrs")

    region = np.s_[top:bottom, left:right]
    valid = image.valid[region]
    signal = np.where(valid, image.signal[region], -np.inf)
    if not valid.any():
        return SkyCoord([], [], unit="deg", frame="icrs")
    background = np.median(signal[valid])
    noise = 1.4826 * np.median(np.abs(signal[valid] - background))
    peaks = (signal == maximum_filter(signal, size=5)) & valid & (signal > background + 8 * noise)
    if image.variance is not None:
        variance = image.variance[region]
        good_variance = (variance > 0) & np.isfinite(variance)
        sigma = np.sqrt(np.where(good_variance, variance, np.inf))
        peaks &= (signal - background) > 8 * sigma

    offsets_y, offsets_x = np.indices((3, 3)) - 1
    ring = np.ones((5, 5), dtype=bool)
    ring[1:4, 1:4] = False
    cy, cx = np.nonzero(peaks[2:-2, 2:-2])
    order = np.argsort(signal[cy + 2, cx + 2], stable=True)[-MAX_REFERENCE_SOURCES:][::-1]
    centers = []
    for py, px in zip(cy[order] + 2, cx[order] + 2):
        patch = signal[py - 2:py + 3, px - 2:px + 3]
        if not np.isfinite(patch).all() or np.count_nonzero(patch == patch[2, 2]) != 1:
            continue
        weights = np.maximum(patch[1:4, 1:4] - np.median(patch[ring]), 0)
        total = weights.sum()
        if total > 0:
            centers.append((left + px + np.sum(weights * offsets_x) / total,
                            top + py + np.sum(weights * offsets_y) / total))

    if not centers:
        return SkyCoord([], [], unit="deg", frame="icrs")
    ra_dec = image.wcs.pixel_to_world(*np.asarray(centers).T).icrs
    gx, gy = grid.world_to_pixel(ra_dec)
    return ra_dec[(gx >= -0.5) & (gx < shape[1] - 0.5) & (gy >= -0.5) & (gy < shape[0] - 0.5)]


def assess_registration(a: Image, b: Image, grid: WCS, shape: tuple[int, int],
                        exclude: tuple[SkyCoord, SkyCoord] | None = None, *, exclude_radius_pixels: int = 3) -> dict:
    """Measure relative WCS residuals from mutually matched native-image peaks."""
    first = _centroids(a, grid, shape)
    second = _centroids(b, grid, shape)
    native_arcsec = 3600 * max(a.pixel_scale, b.pixel_scale)
    if exclude is not None:
        first = first[first.separation(exclude[0]).arcsec > exclude_radius_pixels * native_arcsec]
        second = second[second.separation(exclude[1]).arcsec > exclude_radius_pixels * native_arcsec]
    limit = native_arcsec / 2
    report = {
        "status": "insufficient_matches", "reference_sources_a": len(first), "reference_sources_b": len(second),
        "matched_sources": 0, "used_sources": 0, "minimum_matches": MIN_MATCHES,
        "median_offset_arcsec": None, "scatter_rms_arcsec": None, "tolerance_arcsec": limit,
        "method": "Native-pixel centroids, mutual nearest sky matches, median offset and clipped RMS",
    }
    if min(len(first), len(second)) < MIN_MATCHES:
        return report

    origin = grid.pixel_to_world((shape[1] - 1) / 2, (shape[0] - 1) / 2).icrs
    sky_offset = origin.skyoffset_frame()
    local_a, local_b = first.transform_to(sky_offset), second.transform_to(sky_offset)
    xy_a = np.column_stack((local_a.lon.arcsec, local_a.lat.arcsec))
    xy_b = np.column_stack((local_b.lon.arcsec, local_b.lat.arcsec))
    distance, index_b = cKDTree(xy_b).query(xy_a)
    index_a = cKDTree(xy_a).query(xy_b)[1]
    matched = (distance <= 2 * native_arcsec) & (index_a[index_b] == np.arange(len(xy_a)))
    offsets = xy_b[index_b[matched]] - xy_a[matched]
    report["matched_sources"] = len(offsets)
    if len(offsets) < MIN_MATCHES:
        return report

    median = np.median(offsets, axis=0)
    residuals = np.linalg.norm(offsets - median, axis=1)
    # Allow up to one native pixel for matching outliers. Requiring a majority
    # prevents a small subset of chance matches from certifying the field.
    inliers = residuals <= native_arcsec
    report["used_sources"] = int(inliers.sum())
    if inliers.sum() < max(MIN_MATCHES, 0.6 * len(offsets)):
        return report | {"status": "inconsistent_matches"}

    used = offsets[inliers]
    median = np.median(used, axis=0)
    scatter = float(np.sqrt(np.mean(np.sum((used - median)**2, axis=1))))
    magnitude = float(np.linalg.norm(median))
    return report | {
        "status": "passed" if max(magnitude, scatter) <= limit else "failed",
        "median_offset_arcsec": {"east": float(median[0]), "north": float(median[1]), "magnitude": magnitude},
        "scatter_rms_arcsec": scatter,
    }
