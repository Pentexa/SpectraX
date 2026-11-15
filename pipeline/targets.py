from typing import Literal
from urllib.parse import urlencode

from astropy import units as u
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time
from pydantic import BaseModel

from pipeline.catalog import DataError

REFERENCE_EPOCH = Time(2000, format="jyear", scale="tt")
DEFAULT_TARGET_MJD = 61100.0


class Target(BaseModel):
    id: str
    name: str
    kind: Literal["proper_motion", "binary", "variability"]
    reference_ra: float
    reference_dec: float
    reference_epoch_jyear: float = 2000.0
    pm_ra_cosdec_mas_yr: float
    pm_dec_mas_yr: float
    parallax_mas: float
    radial_velocity_kms: float | None
    source: str
    recommended_wavelength_um: float
    note: str | None = None

    def position(self, mjd: float) -> SkyCoord:
        time = Time(mjd, format="mjd", scale="utc")
        reference = SkyCoord(
            ra=self.reference_ra * u.deg, dec=self.reference_dec * u.deg, frame="icrs", obstime=REFERENCE_EPOCH,
            pm_ra_cosdec=self.pm_ra_cosdec_mas_yr * u.mas / u.yr, pm_dec=self.pm_dec_mas_yr * u.mas / u.yr,
            distance=(self.parallax_mas * u.mas).to(u.pc, equivalencies=u.parallax()),
            radial_velocity=(self.radial_velocity_kms or 0) * u.km / u.s,
        )
        barycentric = reference.apply_space_motion(time).cartesian.without_differentials()
        return SkyCoord(barycentric - get_body_barycentric("earth", time, ephemeris="builtin"), frame="icrs")

    def metadata(self, mjd: float) -> dict:
        position = self.position(mjd)
        return self.model_dump() | {"position_mjd": mjd, "ra": position.ra.deg, "dec": position.dec.deg,
                                    "position_kind": "catalog_prediction_geocentric", "fov": 0.05}


def _target(id, name, kind, ident, coordinate, motion, parallax, rv, wavelength, note=None):
    icrs = SkyCoord(coordinate, unit=(u.hourangle, u.deg), frame="icrs")
    return Target(id=id, name=name, kind=kind, reference_ra=icrs.ra.deg, reference_dec=icrs.dec.deg,
                  pm_ra_cosdec_mas_yr=motion[0], pm_dec_mas_yr=motion[1], parallax_mas=parallax,
                  radial_velocity_kms=rv, source="https://simbad.harvard.edu/simbad/sim-id?" + urlencode({"Ident": ident}),
                  recommended_wavelength_um=wavelength, note=note)


TARGETS = {item.id: item for item in (
    _target("barnard", "Barnard's Star", "proper_motion", "Barnard's star",
            "17 57 48.498470 +04 41 36.11388", (-801.551, 10362.394), 546.9759, -110.11, 4.65,
            "Saturation and blooming masked the core in the benchmark sample."),
    _target("epsilon-indi-b", "Epsilon Indi B", "binary", "eps Ind B",
            "22 04 10.5951812451 -56 46 58.239102418", (3981.977, -2466.832), 270.6580, None, 3.5,
            "Photometry near this position can contain blended light from Ba and Bb."),
    _target("wise-0855", "WISE 0855−0714", "proper_motion", "WISE J085510.83-071442.5",
            "08 55 16.53798 -07 14 49.3728", (-8123.7, 673.2), 439.0, None, 4.65,
            "The catalog position moves between observations. Preserve low-SNR and nondetection flags."),
    _target("rw-aurigae", "RW Aurigae", "variability", "RW Aur",
            "05 07 49.5662483 +30 24 05.177426", (7.23, -20.33), 15.42, 15.0, 1.02,
            "Photometry near this position can contain blended light from the RW Aur system."),
    _target("r-draconis", "R Draconis", "variability", "R Dra",
            "16 32 40.2265999080 +66 45 17.925901992", (-20.643, 6.149), 1.2509, -132.8, 4.65),
)}


def get_target(target_id: str) -> Target:
    target = TARGETS.get(target_id)
    if target is None:
        raise DataError("unknown_target", f"No benchmark target '{target_id}'", 404)
    return target
