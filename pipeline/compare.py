from typing import Literal

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import NoConvergence, WCS
from reproject import reproject_interp

from pipeline.catalog import DataError, Observation, Position
from pipeline.images import Image

Mode = Literal["side_by_side", "difference", "sum", "stack"]
MAX_PIXELS = 256


def output_grid(position: Position, native_scale: float) -> tuple[WCS, tuple[int, int]]:
    # Odd width keeps the requested coordinate at the center of a pixel.
    width = min(MAX_PIXELS - 1, max(3, 2 * int(position.fov / native_scale / 2) + 1))
    scale = position.fov / width
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.radesys = "ICRS"
    wcs.wcs.crval = [position.ra, position.dec]
    wcs.wcs.crpix = [(width + 1) / 2] * 2
    wcs.wcs.cdelt = [-scale, scale]
    return wcs, (width, width)


def nullable_pixels(values: np.ndarray) -> list:
    return np.where(np.isfinite(values), values, None).tolist()


def _aligned(image: Image, wcs: WCS, shape: tuple[int, int]):
    planes = [np.where(image.valid, image.signal, np.nan)]
    if image.variance is not None:
        planes.append(np.where(image.valid & (image.variance > 0), image.variance, np.nan))
    if image.flags is not None:
        planes.append(image.flags.astype(float))
    result, footprint = reproject_interp((np.stack(planes), image.wcs), wcs, shape_out=shape, order="nearest-neighbor")
    signal = np.where(footprint[0] > 0, result[0], np.nan)
    variance = result[1] if image.variance is not None else np.full(shape, np.nan)
    flags = result[-1] if image.flags is not None else None
    return signal, variance, flags


def _bandpass(image: Image, sky: SkyCoord) -> tuple[np.ndarray, np.ndarray]:
    x, y = image.wcs.world_to_pixel(sky)
    detector_pixels = np.stack((np.rint(x), np.rint(y)), axis=-1)
    wavelength, bandwidth = image.spectral.wcs_pix2world(detector_pixels.reshape(-1, 2), 0).T
    wave_unit, width_unit = image.spectral.wcs.cunit
    return wave_unit.to(u.um, wavelength).reshape(x.shape), width_unit.to(u.um, bandwidth).reshape(x.shape)


def _measurement(wcs: WCS, a, b, variance, compatible, unit: u.UnitBase) -> dict:
    y, x = (length // 2 for length in a.shape)
    location = wcs.pixel_to_world(x, y).icrs
    valid = compatible[y, x]
    return {
        "kind": "center_pixel_surface_brightness_difference" if unit.is_equivalent(u.Jy / u.sr) else "center_pixel_difference",
        "ra": float(location.ra.deg),
        "dec": float(location.dec.deg),
        "value_a": float(a[y, x]) if np.isfinite(a[y, x]) else None,
        "value_b": float(b[y, x]) if np.isfinite(b[y, x]) else None,
        "difference": float(b[y, x] - a[y, x]) if valid else None,
        "uncertainty": float(np.sqrt(variance[y, x])) if valid and np.isfinite(variance[y, x]) else None,
        "unit": unit.to_string(),
    }


def compare(position: Position, mode: Mode, epoch_a: Observation, epoch_b: Observation, a: Image, b: Image) -> dict:
    arithmetic = mode != "side_by_side"
    same_product_type = (epoch_a.source, epoch_a.band, epoch_a.detector, epoch_a.spectral_wcs, epoch_a.calibration) == (
        epoch_b.source, epoch_b.band, epoch_b.detector, epoch_b.spectral_wcs, epoch_b.calibration,
    )
    matching_units = a.unit.is_equivalent(b.unit)
    if arithmetic and (not same_product_type or not matching_units):
        raise DataError("incompatible_epochs", "Arithmetic requires compatible units, band and calibration")

    wcs, shape = output_grid(position, max(a.pixel_scale, b.pixel_scale))
    try:
        aligned_a, var_a, flags_a = _aligned(a, wcs, shape)
        aligned_b, var_b, flags_b = _aligned(b, wcs, shape)
    except (ValueError, RuntimeError, NoConvergence) as exc:
        raise DataError("alignment_failed", f"Reprojection failed: {exc}") from exc
    overlap = np.isfinite(aligned_a) & np.isfinite(aligned_b)
    minimum_overlap = 0.1
    if arithmetic and overlap.mean() < minimum_overlap:
        raise DataError("insufficient_overlap", "Less than 10% of the requested grid has valid coverage in both epochs")
    if not (np.isfinite(aligned_a).any() or np.isfinite(aligned_b).any()):
        raise DataError("outside_coverage", "The requested region has no unmasked pixels", 404)

    warnings = ["WCS-only registration. Residual astrometry and local PSF differences have not been calibrated.",
                "Nearest-neighbor resampling. Adjacent residual pixels can reuse an input pixel."]
    if a.metadata['psf_fwhm_arcsec'] != b.metadata['psf_fwhm_arcsec']:
        warnings.append("Input PSF FWHM metadata differ. PSFs were not matched.")

    spectral_info = None
    compatible = overlap.copy() if arithmetic else np.zeros(shape, dtype=bool)
    if arithmetic and a.spectral is not None and b.spectral is not None:
        try:
            sky = wcs.pixel_to_world(*np.indices(shape)[::-1])
            wave_a, width_a = _bandpass(a, sky)
            wave_b, width_b = _bandpass(b, sky)
        except (ValueError, RuntimeError, NoConvergence) as exc:
            raise DataError("alignment_failed", f"Spectral WCS lookup failed: {exc}") from exc
        # Rounded detector coordinates reflect the actual samples used in each image.
        tolerance = 0.25 * np.minimum(width_a, width_b)
        compatible &= (tolerance > 0) & (np.abs(wave_a - wave_b) <= tolerance)
        if compatible.mean() < minimum_overlap:
            raise DataError("incompatible_bandpass", "Less than 10% of the grid has matching SPHEREx pixel bandpasses")
        cy, cx = (length // 2 for length in shape)
        spectral_info = {
            "center_wavelength_a_um": nullable_pixels(wave_a[cy, cx]),
            "center_wavelength_b_um": nullable_pixels(wave_b[cy, cx]),
            "max_separation_in_narrower_bandwidths": 0.25,
        }
        warnings.append("Bandpass matching uses approximate LVF wavelengths. Sky background, including zodiacal light, is retained.")

    result = uncertainty = snr = measurement = display = None
    if arithmetic:
        conversion = b.unit.to(a.unit)
        aligned_b *= conversion
        var_b *= conversion**2
        same_observation = (epoch_a.source, epoch_a.observation_id) == (epoch_b.source, epoch_b.observation_id)
        if same_observation and epoch_a.epoch != epoch_b.epoch:
            raise DataError("incompatible_epochs", "Both entries refer to the same observation; use a single epoch ID")
        variance = var_a + var_b
        if same_observation:
            variance = np.zeros(shape) if mode == "difference" else 4 * var_a
        operations = {
            "difference": lambda: aligned_b - aligned_a,
            "sum": lambda: aligned_a + aligned_b,
            "stack": lambda: (aligned_a + aligned_b) / 2,
        }
        result = np.where(compatible, operations[mode](), np.nan)
        if mode == "stack":
            variance = variance / 4
        uncertainty = np.where(compatible, np.sqrt(variance), np.nan)
        if mode == "difference":
            with np.errstate(divide="ignore", invalid="ignore"):
                snr = np.where(compatible & (variance > 0), result / np.sqrt(variance), np.nan)
            measurement = _measurement(wcs, aligned_a, aligned_b, variance, compatible, a.unit)
            if np.isfinite(snr).any():
                warnings.append("SNR includes statistical input variance only and assumes independent epochs.")
        low, high = np.percentile(result[compatible], [2, 98]).tolist()
        if mode == "difference":
            high = max(abs(low), abs(high))
            low = -high
        if low == high:
            low, high = low - 1, high + 1
        display = {"min": low, "max": high, "stretch": "linear", "percentiles": [2, 98]}

    return {
        "mode": mode,
        "grid": {"width": shape[1], "height": shape[0], "wcs": dict(wcs.to_header()),
                 "pixel_order": "rows increasing FITS Y, columns increasing FITS X; array index starts at zero"},
        "alignment": {"method": "WCS / reproject_interp, nearest-neighbor", "overlap_fraction": float(overlap.mean()),
                      "arithmetic_valid_fraction": float(compatible.mean()) if arithmetic else None,
                      "astrometric_offset_verified": False},
        "images": {"a": nullable_pixels(aligned_a), "b": nullable_pixels(aligned_b),
                   "result": nullable_pixels(result) if result is not None else None,
                   "uncertainty": nullable_pixels(uncertainty) if uncertainty is not None and np.isfinite(uncertainty).any() else None,
                   "snr": nullable_pixels(snr) if snr is not None and np.isfinite(snr).any() else None},
        "flags": {"a": nullable_flags(flags_a), "b": nullable_flags(flags_b)},
        "units": {"a": a.unit.to_string(), "b": (a.unit if arithmetic else b.unit).to_string(),
                  "result": a.unit.to_string() if arithmetic else None},
        "display": display,
        "spectral_match": spectral_info,
        "measurement": measurement,
        "warnings": warnings,
    }


def nullable_flags(flags: np.ndarray | None) -> list | None:
    if flags is None:
        return None
    finite = np.isfinite(flags)
    integers = np.where(finite, flags, 0).astype(np.uint32)
    return np.where(finite, integers, None).tolist()
