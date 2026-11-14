import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

from pipeline.catalog import DataError, Observation, data_path


def numeric_header(header, *keys):
    for key in keys:
        if key in header:
            value = float(header[key])
            if np.isfinite(value):
                return value
    return None


@dataclass
class Image:
    signal: np.ndarray
    variance: np.ndarray | None
    valid: np.ndarray
    flags: np.ndarray | None
    wcs: WCS
    spectral: WCS | None
    unit: u.UnitBase
    pixel_scale: float
    metadata: dict


def _auxiliary(hdus, name: str, shape: tuple, dtype):
    if name not in hdus:
        return None
    data = np.array(hdus[name].data, dtype=dtype)
    if data.shape != shape:
        raise ValueError(f"{name} shape differs from the science image")
    return data


def _spectral_wcs(header, hdus):
    # The alternate WCS maps detector pixels through a table. Celestial SIP
    # distortion belongs to the primary WCS and does not apply to this lookup.
    spectral_header = header.copy()
    for key in header:
        if re.fullmatch(r"(?:A|B|AP|BP)_(?:ORDER|DMAX|\d+_\d+)", key):
            spectral_header.remove(key, ignore_missing=True)
    spectral = WCS(spectral_header, fobj=hdus, key="W")
    if list(spectral.wcs.ctype) != ["WAVE-TAB", "WAVE-TAB"]:
        raise ValueError("Missing SPHEREx wavelength/bandwidth lookup")
    if any(not unit.is_equivalent(u.um) for unit in spectral.wcs.cunit):
        raise ValueError("Invalid spectral WCS unit")
    return spectral


@lru_cache(maxsize=4)
def _read_image(path: Path, modified_ns: int, size: int, spectral_wcs: str, reject_bits: int) -> Image:
    try:
        with fits.open(path, memmap=False) as hdus:
            hdus.verify("exception")
            hdu = hdus["IMAGE"] if "IMAGE" in hdus else hdus[0]
            header = hdus[0].header.copy()
            header.extend(hdu.header, update=True)
            if hdu.data is None or hdu.data.ndim != 2:
                raise ValueError("Expected a two-dimensional science image")
            signal = np.array(hdu.data, dtype=float)
            wcs = WCS(hdu.header, fobj=hdus).celestial
            if not wcs.has_celestial:
                raise ValueError("Missing celestial WCS")
            scales = proj_plane_pixel_scales(wcs)
            if not np.all(np.isfinite(scales) & (scales > 0)):
                raise ValueError("Invalid celestial pixel scale")
            unit = u.Unit(header["BUNIT"], format="fits")
            flags = _auxiliary(hdus, "FLAGS", signal.shape, np.uint32)
            mask = _auxiliary(hdus, "MASK", signal.shape, bool)
            variance = _auxiliary(hdus, "VARIANCE", signal.shape, float)
            if variance is not None and hdus["VARIANCE"].header.get("BUNIT"):
                variance *= u.Unit(hdus["VARIANCE"].header["BUNIT"], format="fits").to(unit**2)
            if variance is None:
                sigma = _auxiliary(hdus, "UNCERTAINTY", signal.shape, float)
                if sigma is not None:
                    if hdus["UNCERTAINTY"].header.get("BUNIT"):
                        sigma *= u.Unit(hdus["UNCERTAINTY"].header["BUNIT"], format="fits").to(unit)
                    variance = np.where(sigma > 0, sigma**2, np.nan)
            valid = np.isfinite(signal)
            if flags is not None:
                valid &= (flags & reject_bits) == 0
            if mask is not None:
                valid &= ~mask
            spectral = _spectral_wcs(hdu.header, hdus) if spectral_wcs == "spherex-lvf" else None
            if spectral is not None and flags is None:
                raise ValueError("SPHEREx FLAGS extension is required")
            start = numeric_header(header, "MJD-BEG", "MJD-OBS")
            if start is None and header.get("DATE-OBS"):
                start = float(Time(header["DATE-OBS"], scale="utc").mjd)
            if start is None:
                raise ValueError("Missing observation time")
            end = numeric_header(header, "MJD-END")
            exposure = numeric_header(header, "EXPTIME", "TEXPTIME", "XPOSURE")
            detector = numeric_header(header, "DETECTOR")
            metadata = {
                "observed_at": Time(start, format="mjd", scale="utc").isot + "Z",
                "start_mjd": start,
                "end_mjd": end,
                "exposure_seconds": exposure,
                "elapsed_seconds": numeric_header(header, "TELAPSE"),
                "detector": int(detector) if detector is not None else None,
                "band": header.get("FILTER") or header.get("BAND"),
                "product_id": header.get("OBSID"),
                "shape": list(signal.shape),
                "psf_fwhm_arcsec": numeric_header(header, "PSF_FWHM"),
                "aurora_contamination": header.get("AURORA_CONT"),
                "quality_hdus": [name for name in ("FLAGS", "MASK", "VARIANCE", "UNCERTAINTY", "ZODI", "EPSF", "PSF") if name in hdus],
                "flag_rejection_mask": reject_bits if flags is not None else None,
                "fits_history": list(header.get("HISTORY", [])),
                "wcs": dict(wcs.to_header(relax=True)),
            }
    except (OSError, ValueError, KeyError, TypeError, fits.VerifyError) as exc:
        raise DataError("invalid_fits", f"{path.name}: {exc}") from exc
    return Image(signal, variance, valid, flags, wcs, spectral, unit, float(np.max(scales)), metadata)


def read_image(data_dir: Path, observation: Observation) -> Image:
    path = data_path(data_dir, observation)
    stat = path.stat()
    sizes = {observation.size_bytes}
    if observation.full_image is not None:
        sizes.add(observation.full_image.size_bytes)
    if stat.st_size not in sizes:
        raise DataError("invalid_fits", f"{path.name}: size differs from the manifest")
    image = _read_image(path, stat.st_mtime_ns, stat.st_size, observation.spectral_wcs, observation.reject_flag_bits)
    start = image.metadata["start_mjd"]
    end = image.metadata["end_mjd"]
    if abs(start - observation.observation_start_mjd) > 1 / 86400:
        raise DataError("metadata_mismatch", f"{observation.epoch}: FITS start time differs from the manifest")
    if end is not None and abs(end - observation.observation_end_mjd) > 1 / 86400:
        raise DataError("metadata_mismatch", f"{observation.epoch}: FITS end time differs from the manifest")
    if observation.detector is not None and observation.detector != image.metadata["detector"]:
        raise DataError("metadata_mismatch", f"{observation.epoch}: FITS detector differs from the manifest")
    if image.metadata["product_id"] and observation.observation_id != image.metadata["product_id"]:
        raise DataError("metadata_mismatch", f"{observation.epoch}: FITS observation ID differs from the manifest")
    return image
