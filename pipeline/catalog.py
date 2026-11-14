import json
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, FiniteFloat, model_validator


class DataError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.status = status


class Position(BaseModel):
    ra: FiniteFloat = Field(ge=0, lt=360)
    dec: FiniteFloat = Field(ge=-90, le=90)
    fov: FiniteFloat = Field(gt=0, le=2)


class ArchiveFile(BaseModel):
    access: AnyHttpUrl
    size_bytes: int = Field(gt=0, le=512 * 1024**2)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Product(ArchiveFile):
    epoch: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    source: str
    release: str
    observation_id: str
    observation_start_mjd: FiniteFloat | None
    observation_end_mjd: FiniteFloat | None
    filename: str = Field(pattern=r"^[A-Za-z0-9_-]+\.fits$")
    calibration: str = Field(min_length=1)
    processing_history: list[str] = Field(min_length=1)
    coverage: Position
    flags: str

    @model_validator(mode="after")
    def validate_time_range(self):
        if (self.observation_start_mjd is not None and self.observation_end_mjd is not None
                and self.observation_end_mjd < self.observation_start_mjd):
            raise ValueError("Observation end is earlier than the start")
        return self

    def metadata(self, data_dir: Path) -> dict:
        return self.model_dump(mode="json", exclude={"filename"}) | {
            "available_locally": (data_dir / self.filename).is_file(),
        }


class Observation(Product):
    observation_start_mjd: FiniteFloat
    observation_end_mjd: FiniteFloat
    band: str = Field(min_length=1)
    detector: int | None = Field(default=None, ge=1, le=6)
    spectral_wcs: Literal["spherex-lvf", "fixed"]
    reject_flag_bits: int = Field(default=0xFFFFFFFF, ge=0, le=0xFFFFFFFF)
    full_image: ArchiveFile | None = None

    def metadata(self, data_dir: Path) -> dict:
        metadata = super().metadata(data_dir)
        if metadata["available_locally"]:
            size = (data_dir / self.filename).stat().st_size
            metadata["local_variant"] = "full_image" if self.full_image and size == self.full_image.size_bytes else "primary"
        return metadata


class Cube(Product):
    bands: Literal[102] = 102
    detector: Literal["D1-D6"] = "D1-D6"


class Manifest(BaseModel):
    schema_version: Literal[1]
    observations: list[Observation]
    cubes: list[Cube] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_products(self):
        products = [*self.observations, *self.cubes]
        if len({item.epoch for item in products}) != len(products):
            raise ValueError("Each epoch ID must be unique")
        if len({item.filename for item in products}) != len(products):
            raise ValueError("Each local FITS filename must be unique")
        return self


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def data_path(data_dir: Path, product: Product) -> Path:
    path = data_dir / product.filename
    if not path.is_file():
        raise DataError("data_unavailable", f"FITS for '{product.epoch}' is missing. Run planet-x-data.", 503)
    return path
