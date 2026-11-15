import numpy as np
from astropy import units as u
from astropy.wcs import NoConvergence

from pipeline.catalog import DataError, Position
from pipeline.compare import _aligned, _bandpass, output_grid
from pipeline.images import read_image


def wing_change(selected, samples):
    if len(selected) != 2:
        return None
    (a, directory_a), (b, directory_b) = selected
    if a.comparison_key != b.comparison_key or a.observation_end_mjd >= b.observation_start_mjd:
        return None
    # The raw masks must establish why the core was rejected in both epochs.
    details = [(sample["error"] or {}).get("details", {}) for sample in samples]
    if not all(detail.get("core_pixels_usable") == 0 and "BLOOM" in detail.get("core_flags", [])
               for detail in details):
        return None
    try:
        first, second = read_image(directory_a, a), read_image(directory_b, b)
        if (first.spectral is None or second.spectral is None
                or not first.unit.is_equivalent(u.MJy / u.sr) or not second.unit.is_equivalent(u.MJy / u.sr)):
            return None
        native_scale = max(first.pixel_scale, second.pixel_scale)
        grid, shape = output_grid(Position(ra=samples[0]["ra"], dec=samples[0]["dec"], fov=0.05), native_scale)
        image_a, _, _ = _aligned(first, grid, shape)
        image_b, _, _ = _aligned(second, grid, shape)
        image_a *= first.unit.to(u.MJy / u.sr)
        image_b *= second.unit.to(u.MJy / u.sr)
        y, x = np.indices(shape)
        sky = grid.pixel_to_world(x, y)
        wave_a, width_a = _bandpass(first, sky)
        wave_b, width_b = _bandpass(second, sky)
    except (DataError, NoConvergence, ValueError):
        return None
    center_y, center_x = [axis // 2 for axis in shape]
    tolerance = 0.25 * np.minimum(width_a, width_b)
    same_band = (tolerance > 0) & (np.abs(wave_a - wave_b) <= tolerance)
    if not same_band[center_y, center_x]:
        return None
    common = same_band & np.isfinite(image_a) & np.isfinite(image_b)
    xx, yy = x - center_x, y - center_y
    pixel_scale = abs(grid.wcs.cdelt[0])
    radius = np.hypot(xx, yy) * pixel_scale / native_scale
    background = common & (radius >= 11) & (radius < 14)
    if np.count_nonzero(background) < 50:
        return None
    signal_a = image_a - np.median(image_a[background])
    signal_b = image_b - np.median(image_b[background])
    delta = signal_b - signal_a
    sky_delta = delta[background]
    scatter = 1.4826 * np.median(np.abs(sky_delta - np.median(sky_delta)))
    if not np.isfinite(scatter) or scatter <= 0:
        return None

    rings = []
    for inner, outer in ((4, 6), (6, 8)):
        ring = (radius >= inner) & (radius < outer)
        valid = common & ring
        pixels = int(valid.sum())
        if pixels < 0.7 * ring.sum():
            return None
        median_a, median_b = np.median(signal_a[valid]), np.median(signal_b[valid])
        change = np.median(delta[valid])
        if min(median_a, median_b) <= 3 * scatter:
            return None
        threshold = max(3 * scatter, 0.1 * max(median_a, median_b))
        for x_side, y_side in ((xx >= 0, yy >= 0), (xx < 0, yy >= 0), (xx >= 0, yy < 0), (xx < 0, yy < 0)):
            quadrant = valid & x_side & y_side
            if quadrant.sum() < 6 or np.median(delta[quadrant]) * np.sign(change) <= threshold:
                return None
        rings.append({
            "inner_arcsec": inner * native_scale * 3600, "outer_arcsec": outer * native_scale * 3600,
            "common_pixels": pixels, "a_mjy_sr": float(median_a), "b_mjy_sr": float(median_b),
            "change_mjy_sr": float(change),
        })
    if np.sign(rings[0]["change_mjy_sr"]) != np.sign(rings[1]["change_mjy_sr"]):
        return None
    return {
        "method": "matched_annular_surface_brightness",
        "wavelength_a_um": float(wave_a[center_y, center_x]), "wavelength_b_um": float(wave_b[center_y, center_x]),
        "elapsed_days": samples[1]["mjd"] - samples[0]["mjd"],
        "sky_scatter_mjy_sr": float(scatter), "rings": rings,
    }
