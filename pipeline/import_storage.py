import logging
import re
import shutil
import sqlite3
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from tempfile import mkdtemp

from pipeline.catalog import DataError

IMPORTED_EPOCH = re.compile(r"^irsa-[a-f0-9]{64}$")
STAGING_PREFIX = ".download-"
LEASED_STAGING_PREFIX = ".download-leased-"
LEASE_FILE = ".active.sqlite3"
METADATA = "observation.json"
FILENAME = "cutout.fits"
DEFAULT_IMPORT_QUOTA_BYTES = 1024**3
QUOTA_ERROR = "import_quota_exceeded"
logger = logging.getLogger(__name__)


@contextmanager
def file_write_lock(path: Path, *, timeout: float):
    with closing(sqlite3.connect(path, timeout=timeout)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        yield


def _stored_bytes(directory: Path, filenames: tuple[str, ...]) -> int:
    total = 0
    for name in filenames:
        try:
            total += (directory / name).stat().st_size
        except FileNotFoundError:
            pass
    return total


class ImportQuota:
    def __init__(self, directory: Path, limit_bytes: int, *, epoch_pattern=IMPORTED_EPOCH,
                 filenames=(FILENAME, METADATA)):
        self.directory = directory
        self.limit_bytes = limit_bytes
        self.epoch_pattern = epoch_pattern
        self.filenames = filenames

    @contextmanager
    def write_lock(self):
        # SQLite coordinates writers across processes on the same volume.
        # The files themselves are the accounting records.
        try:
            with file_write_lock(self.directory / ".quota.sqlite3", timeout=5):
                yield
        except sqlite3.Error as exc:
            raise DataError("import_storage_unavailable", "Could not lock the imported exposure storage", 503) from exc

    def _recover_staging(self):
        """Call with the write lock held so staging ownership cannot change."""
        for stage in self.directory.resolve().iterdir():
            if not stage.name.startswith(LEASED_STAGING_PREFIX) or not stage.is_dir() or stage.resolve() != stage:
                continue
            try:
                with file_write_lock(stage / LEASE_FILE, timeout=0):
                    pass
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode == sqlite3.SQLITE_BUSY:
                    continue
                raise
            # SQLite releases the lock when the owner process exits. Close our
            # probe before removing the directory, including on Windows.
            shutil.rmtree(stage)

    @contextmanager
    def staging(self, *, minimum_bytes: int = 1):
        self.directory.mkdir(parents=True, exist_ok=True)
        stage = None
        with ExitStack() as owner:
            try:
                with self.write_lock():
                    self._recover_staging()
                    if minimum_bytes:
                        self.check_space(minimum_bytes)
                    stage = Path(mkdtemp(prefix=LEASED_STAGING_PREFIX, dir=self.directory.resolve()))
                    owner.enter_context(file_write_lock(stage / LEASE_FILE, timeout=0))
                yield stage
            finally:
                if stage is not None:
                    try:
                        with self.write_lock():
                            owner.close()
                            shutil.rmtree(stage)
                    except (OSError, DataError):
                        logger.warning("Could not remove import staging directory %s", stage, exc_info=True)

    def check_space(self, additional_bytes: int):
        """Call with the write lock held before growing or publishing a file."""
        used_bytes = 0
        for entry in self.directory.iterdir():
            if self.epoch_pattern.fullmatch(entry.name):
                used_bytes += _stored_bytes(entry, self.filenames)
            elif entry.name.startswith(STAGING_PREFIX):
                try:
                    for path in entry.iterdir():
                        if self.epoch_pattern.fullmatch(path.name):
                            used_bytes += _stored_bytes(path, self.filenames)
                except FileNotFoundError:
                    # Older workers can remove their staging directories outside this lock.
                    continue
        if additional_bytes > self.limit_bytes - used_bytes:
            raise DataError(QUOTA_ERROR, "The imported exposure storage quota is full", 507,
                            details={"limit_bytes": self.limit_bytes, "used_bytes": used_bytes,
                                     "additional_bytes": additional_bytes})
