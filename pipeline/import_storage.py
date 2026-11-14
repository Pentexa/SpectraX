import re
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from pipeline.catalog import DataError

IMPORTED_EPOCH = re.compile(r"^irsa-[a-f0-9]{64}$")
STAGING_PREFIX = ".download-"
METADATA = "observation.json"
FILENAME = "cutout.fits"
DEFAULT_IMPORT_QUOTA_BYTES = 1024**3
QUOTA_ERROR = "import_quota_exceeded"


def _stored_bytes(directory: Path) -> int:
    total = 0
    for name in (FILENAME, METADATA):
        try:
            total += (directory / name).stat().st_size
        except FileNotFoundError:
            pass
    return total


class ImportQuota:
    def __init__(self, directory: Path, limit_bytes: int):
        self.directory = directory
        self.limit_bytes = limit_bytes

    @contextmanager
    def write_lock(self):
        # SQLite coordinates writers across processes on the same volume.
        # The files themselves are the accounting records.
        try:
            with closing(sqlite3.connect(self.directory / ".quota.sqlite3", timeout=5)) as lock:
                lock.execute("BEGIN IMMEDIATE")
                yield
        except sqlite3.Error as exc:
            raise DataError("import_storage_unavailable", "Could not lock the imported exposure storage", 503) from exc

    def check_space(self, additional_bytes: int):
        """Call with the write lock held before growing or publishing a file."""
        used_bytes = 0
        for entry in self.directory.iterdir():
            if IMPORTED_EPOCH.fullmatch(entry.name):
                used_bytes += _stored_bytes(entry)
            elif entry.name.startswith(STAGING_PREFIX):
                try:
                    used_bytes += sum(_stored_bytes(path) for path in entry.iterdir())
                except FileNotFoundError:
                    # Another request discarded its staging directory.
                    continue
        if additional_bytes > self.limit_bytes - used_bytes:
            raise DataError(QUOTA_ERROR, "The imported exposure storage quota is full", 507,
                            details={"limit_bytes": self.limit_bytes, "used_bytes": used_bytes,
                                     "additional_bytes": additional_bytes})
