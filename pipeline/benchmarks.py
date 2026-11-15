from pathlib import Path

from pipeline.catalog import Observation, load_manifest

BENCHMARK_FIELDS = {"wise-0855": 0.18, "epsilon-indi-b": 0.2}


def load_benchmark_observations(manifests_dir: Path) -> dict[str, list[Observation]]:
    return {
        target_id: load_manifest(manifests_dir / f"spherex-{target_id}.json").observations
        for target_id in BENCHMARK_FIELDS
    }
