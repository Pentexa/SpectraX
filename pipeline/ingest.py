import argparse
import hashlib
import os
from pathlib import Path
from functools import lru_cache
from http.client import HTTPException
from tempfile import NamedTemporaryFile
from time import monotonic
from urllib.request import urlopen

from dotenv import load_dotenv

from pipeline.benchmarks import load_benchmark_observations
from pipeline.catalog import ArchiveFile, DataError, Observation, Product, load_manifest

ROOT = Path(__file__).resolve().parents[1]


def configured_path(variable: str, default: str) -> Path:
    return ROOT / os.environ.get(variable, default)


def _download(source: ArchiveFile, target: Path, deadline: float | None = None):
    temporary = None
    try:
        with NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            size = 0
            timeout = 30 if deadline is None else min(12, deadline - monotonic())
            if timeout <= 0:
                raise TimeoutError("Archive download deadline reached")
            with urlopen(str(source.access), timeout=timeout) as response:
                while chunk := response.read(1024 * 1024):
                    if deadline is not None and monotonic() > deadline:
                        raise TimeoutError("Archive download deadline reached")
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


def _sources(product: Product, full_image: bool = False) -> list[ArchiveFile]:
    if isinstance(product, Observation) and product.full_image is not None:
        return [product.full_image] if full_image else [product, product.full_image]
    return [product]


@lru_cache(maxsize=64)
def _sha256(path: Path, mtime_ns: int, size: int) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def verified_file(product: Product, directory: Path, *, full_image: bool = False) -> bool:
    target = directory / product.filename
    try:
        stat = target.stat()
        expected = {source.sha256 for source in _sources(product, full_image) if source.size_bytes == stat.st_size}
        return bool(expected) and _sha256(target, stat.st_mtime_ns, stat.st_size) in expected
    except OSError:
        return False


def fetch(product: Product, data_dir: Path, *, full_image: bool = False, deadline: float | None = None) -> Path:
    target = data_dir / product.filename
    if verified_file(product, data_dir, full_image=full_image):
        return target

    data_dir.mkdir(exist_ok=True, parents=True)
    errors = []
    for source in _sources(product, full_image):
        for url in (source.access, *source.download_mirrors):
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("Archive download deadline reached")
            try:
                _download(source.model_copy(update={"access": url}), target, deadline)
                return target
            except (OSError, ValueError, HTTPException) as exc:
                errors.append(str(exc))
    raise ValueError("; ".join(errors))


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Fetch and verify FITS products listed in the manifest")
    parser.add_argument("--manifest", type=Path, default=configured_path("PLANET_X_MANIFEST", "data/manifests/spherex-dr1.json"))
    parser.add_argument("--data-dir", type=Path, default=configured_path("PLANET_X_DATA_DIR", "data/samples"))
    parser.add_argument("--include-cubes", action="store_true", help="Also fetch the optional spectral cube(s)")
    parser.add_argument("--include-benchmarks", action="store_true", help="Also fetch the verified target image pairs")
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
    products = [(product, args.data_dir) for product in [*observations, *(cubes if args.include_cubes else [])]]
    if args.include_benchmarks:
        manifest_dir = configured_path("PLANET_X_BENCHMARK_MANIFEST_DIR", str(args.manifest.resolve().parent))
        for target, records in load_benchmark_observations(manifest_dir).items():
            products.extend((record, args.data_dir / target) for record in records
                            if not args.release or record.release == args.release.upper())
    for product, directory in products:
        try:
            print(f"{product.epoch}: {fetch(product, directory, full_image=args.full_images)}")
        except (OSError, ValueError) as exc:
            parser.exit(1, f"Could not download {product.epoch}: {exc}\n")


if __name__ == "__main__":
    main()
