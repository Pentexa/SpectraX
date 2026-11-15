from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from time import monotonic

from pipeline.catalog import Observation
from pipeline.ingest import fetch, verified_file


class ArchiveFiles:
    """Fetch trusted manifest products once, keeping the prepared files as a fallback."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.lock = Lock()
        self.failures: dict[str, float] = {}
        self.product_locks = {}

    def cached_directory(self, record: Observation) -> Path | None:
        directory = self.directory / record.sha256
        return directory if verified_file(record, directory) else None

    def fetch_one(self, location, deadline):
        record, local = location
        directory = self.directory / record.sha256
        with self.lock:
            product_lock = self.product_locks.setdefault(record.sha256, Lock())
        if not product_lock.acquire(timeout=max(0, deadline - monotonic())):
            return location, "downloaded_fallback"
        try:
            if self.cached_directory(record) is not None:
                return (record, directory), "archive_cache"
            now = monotonic()
            if now < deadline and now >= self.failures.get(record.sha256, 0):
                try:
                    fetch(record, directory, deadline=deadline)
                except (OSError, ValueError):
                    self.failures[record.sha256] = monotonic() + 60
                else:
                    self.failures.pop(record.sha256, None)
                    return (record, directory), "archive_download"
            return (record, local), "downloaded_fallback"
        finally:
            product_lock.release()

    def fetch_many(self, locations):
        if not locations:
            return {}
        deadline = monotonic() + 30
        with ThreadPoolExecutor(max_workers=min(4, len(locations))) as pool:
            results = pool.map(lambda location: self.fetch_one(location, deadline), locations)
            return {location[0].epoch: (location, delivery) for location, delivery in results}
