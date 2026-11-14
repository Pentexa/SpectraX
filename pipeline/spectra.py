from contextlib import contextmanager

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from reproject import reproject_interp

from pipeline.catalog import Cube, DataError, Position, data_path
from pipeline.compare import nullable_flags, nullable_pixels, output_grid


@contextmanager
def open_cube(data_dir, cube: Cube):
    path = data_path(data_dir, cube)
    try:
        if path.stat().st_size != cube.size_bytes:
            raise ValueError("Size differs from the manifest")
        with fits.open(path, memmap=True) as hdus:
            image, hits, flags, channels = (hdus[name] for name in ("IMAGE", "NHITS", "FLAGS", "SPECTRAL_CHANNELS"))
            if len(image.shape) != 3 or not image.shape == hits.shape == flags.shape:
                raise ValueError("Cube planes do not share a three-dimensional grid")
            if not image.shape[0] == len(channels.data) == cube.bands:
                raise ValueError("Cube plane count differs from the calibrated channel table")
            channel_ids = set(zip(channels.data['DETECTOR'], channels.data['SUBCHAN']))
            if channel_ids != {(detector, channel) for detector in range(1, 7) for channel in range(1, 18)}:
                raise ValueError("Unexpected detector/subchannel assignments")
            wavelengths = u.Unit(channels.columns['WAVELENGTH'].unit).to(u.um, channels.data['WAVELENGTH'])
            if not np.all(np.isfinite(wavelengths) & (wavelengths > 0)):
                raise ValueError("Invalid channel wavelengths")
            unit = u.Unit(image.header['BUNIT'], format='fits').to_string()
            wcs = WCS(image.header, fobj=hdus).celestial
            if not wcs.has_celestial:
                raise ValueError("Missing celestial WCS")
            yield image, hits, flags, channels.data, wavelengths, wcs, unit
    except (OSError, ValueError, KeyError, TypeError, fits.VerifyError) as exc:
        raise DataError("invalid_fits", f"{cube.filename}: {exc}") from exc


def spectrum(data_dir, cube: Cube, ra: float, dec: float) -> dict:
    with open_cube(data_dir, cube) as (image, hits, flags, table, wavelengths, wcs, unit):
        x, y = wcs.world_to_pixel(SkyCoord(ra, dec, unit='deg'))
        if not (np.isfinite(x) and np.isfinite(y) and
                -0.5 <= x < image.shape[2] - 0.5 and -0.5 <= y < image.shape[1] - 0.5):
            raise DataError("outside_coverage", "The coordinate is outside this cube tile", 404)
        x, y = int(np.floor(x + 0.5)), int(np.floor(y + 0.5))
        flux = image.section[:, y, x]
        count = hits.section[:, y, x]
        quality = flags.section[:, y, x]
        points = []
        for index in np.argsort(wavelengths):
            row = table[index]
            available = bool(count[index] > 0 and np.isfinite(flux[index]))
            points.append({
                "detector": int(row['DETECTOR']), "channel": int(row['SUBCHAN']),
                "wavelength_um": float(wavelengths[index]), "flux": float(flux[index]) if available else None,
                "uncertainty": None, "flags": int(quality[index]) & 0xFFFFFFFF,
                "nhits": int(count[index]), "masked": not available,
            })
    available_count = sum(not point['masked'] for point in points)
    return {
        "epoch": cube.epoch, "time_mode": "multi_epoch_coadd", "quantity": "pixel_surface_brightness",
        "unit": unit, "expected_channels": cube.bands, "available_channels": available_count,
        "complete": available_count == cube.bands, "channels": points,
        "dataset": cube.metadata(data_dir),
        "warnings": ["Pixel surface brightness from a multi-epoch mosaic. The cube provides no per-channel uncertainty."],
    }


def layers(data_dir, cube: Cube) -> dict:
    with open_cube(data_dir, cube) as (_, _, _, table, wavelengths, _, unit):
        groups = []
        for detector in range(1, 7):
            group = table['DETECTOR'] == detector
            representative = group & (table['SUBCHAN'] == 9)
            groups.append({
                "detector": detector, "representative_channel": 9,
                "representative_wavelength_um": float(wavelengths[representative][0]),
                "min_wavelength_um": float(wavelengths[group].min()),
                "max_wavelength_um": float(wavelengths[group].max()),
            })
    return {"epoch": cube.epoch, "unit": unit, "layers": groups, "dataset": cube.metadata(data_dir)}


def detector_layer(data_dir, cube: Cube, position: Position, detector: int, channel: int) -> dict:
    with open_cube(data_dir, cube) as (image, hits, flags, table, wavelengths, wcs, unit):
        index = int(np.flatnonzero((table['DETECTOR'] == detector) & (table['SUBCHAN'] == channel))[0])
        values = np.asarray(image.section[index], dtype=float)
        count = hits.section[index]
        quality = np.asarray(flags.section[index], dtype=np.uint32)
        values = np.where((count > 0) & np.isfinite(values), values, np.nan)
        grid, shape = output_grid(position, float(max(proj_plane_pixel_scales(wcs))))
        stack, _ = reproject_interp((np.stack((values, quality)), wcs), grid, shape_out=shape, order='nearest-neighbor')
        if not np.isfinite(stack[0]).any():
            raise DataError("outside_coverage", "The region has no valid pixels in this channel", 404)
        wavelength = float(wavelengths[index])
    return {
        "epoch": cube.epoch, "detector": detector, "channel": channel, "wavelength_um": wavelength,
        "unit": unit, "grid": {"width": shape[1], "height": shape[0], "wcs": dict(grid.to_header())},
        "image": nullable_pixels(stack[0]), "flags": nullable_flags(stack[1]), "dataset": cube.metadata(data_dir),
    }
