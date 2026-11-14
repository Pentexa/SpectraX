import argparse
import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

from dotenv import load_dotenv

from pipeline.catalog import ArchiveFile, DataError, Observation, Product, load_manifest

ROOT = Path(__file__).resolve().parents[1]


def configured_path(variable: str, default: str) -> Path:
    return ROOT / os.environ.get(variable, default)


def _download(source: ArchiveFile, target: Path):
    temporary = None
    try:
        with NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            size = 0
            with urlopen(str(source.access), timeout=30) as response:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > source.size_bytes:
                        raise ValueError("Download exceeded expected size")
                    digest.update(chunk)
                    output.write(chunk)
        if size != source.size_bytes or digest.hexdigest() != source.sha256:
            raise ValueError("Size or SHA-256 mismatch")
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def fetch(product: Product, data_dir: Path, *, full_image: bool = False) -> Path:
    target = data_dir / product.filename
    sources = [product]
    if isinstance(product, Observation) and product.full_image is not None:
        sources = [product.full_image] if full_image else [product, product.full_image]
    if target.is_file() and target.stat().st_size in {source.size_bytes for source in sources}:
        with target.open("rb") as file:
            digest = hashlib.file_digest(file, "sha256").hexdigest()
        if any(digest == source.sha256 for source in sources):
            return target

    data_dir.mkdir(exist_ok=True, parents=True)
    errors = []
    for source in sources:
        try:
            _download(source, target)
            return target
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    raise ValueError("; ".join(errors))


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Fetch and verify FITS products listed in the manifest")
    parser.add_argument("--manifest", type=Path, default=configured_path("PLANET_X_MANIFEST", "data/manifests/spherex-dr1.json"))
    parser.add_argument("--data-dir", type=Path, default=configured_path("PLANET_X_DATA_DIR", "data/samples"))
    parser.add_argument("--include-cubes", action="store_true", help="Also fetch the optional spectral cube(s)")
    parser.add_argument("--full-images", action="store_true", help="Prefer full exposures over cutouts when available")
    parser.add_argument("--release", help="Only fetch products from this release, e.g. DR1 or QR3")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    try:
        observations, cubes = manifest.select_release(args.release) if args.release else (manifest.observations, manifest.cubes)
    except DataError as exc:
        parser.error(str(exc))
    if args.release and not (observations or cubes):
        parser.error(f"No FITS products are listed for release '{args.release.upper()}'")
    products = [*observations, *(cubes if args.include_cubes else [])]
    for product in products:
        try:
            print(f"{product.epoch}: {fetch(product, args.data_dir, full_image=args.full_images)}")
        except (OSError, ValueError) as exc:
            parser.exit(1, f"Could not download {product.epoch}: {exc}\n")


if __name__ == "__main__":
    main()
