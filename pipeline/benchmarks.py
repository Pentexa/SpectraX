from pathlib import Path

from pipeline.catalog import Observation, load_manifest

BENCHMARK_FIELDS = {
    "barnard": 0.05,
    "epsilon-indi-b": 0.2,
    "wise-0855": 0.18,
    "rw-aurigae": 0.05,
    "r-draconis": 0.05,
}


def load_benchmark_observations(manifests_dir: Path) -> dict[str, list[Observation]]:
    observations = {}
    for target_id in BENCHMARK_FIELDS:
        manifest = manifests_dir / f"spherex-{target_id}.json"
        if manifest.is_file():
            observations[target_id] = load_manifest(manifest).observations
    return observations
