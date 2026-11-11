"""persistence for evidence-based reviews.

ReviewStore keeps one JSON document per review under a trusted root directory,
with:

* atomic durable writes ( tempfile + fsync + os.replace ),
* per-review advisory locks ( fcntl + an in-process re-entrant lock ) so that
  threads and processes cannot stale-overwrite each other,
* optimistic concurrency on ``version`` ( save() raises :class:`StaleRecordError`
  when the record on disk changed since it was read ).
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from . import models

__all__ = [
    "ReviewStore",
    "StaleRecordError",
]

_VALID_STATUSES = models._VALID_STATUSES


class StaleRecordError(Exception):
    """Another process/thread changed this review between our read and write."""


class _AdvisoryLock:
    """One RLock and one nesting-counted flock per resolved path/process."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.depth = 0
        self.fd = None

    def __enter__(self):
        self.lock.acquire()
        try:
            if self.depth == 0:
                fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                except BaseException:
                    os.close(fd)
                    raise
                self.fd = fd
            self.depth += 1
            return self
        except BaseException:
            self.lock.release()
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            self.depth -= 1
            if self.depth == 0:
                fd, self.fd = self.fd, None
                assert fd is not None
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)
        finally:
            self.lock.release()
        return False


_PATH_LOCKS = {}
_REGISTRY_LOCK = threading.Lock()


def _after_fork():
    global _PATH_LOCKS, _REGISTRY_LOCK
    for lock in _PATH_LOCKS.values():
        if lock.fd is not None:
            os.close(lock.fd)
    _PATH_LOCKS = {}
    _REGISTRY_LOCK = threading.Lock()


os.register_at_fork(after_in_child=_after_fork)


def atomic_write(path: Path, data: bytes, *, overwrite: bool = True) -> None:
    """Publish complete bytes, then fsync the containing directory."""
    if path.is_symlink():
        raise ValueError("symlink artifacts are forbidden")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.repager-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
            os.unlink(tmp)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

class ReviewStore:
    """JSON-file persistence for repager review records."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, _AdvisoryLock] = {}
        self._global = threading.RLock()

    # ------------------------------------------------------------------
    # paths
    # ------------------------------------------------------------------
    def run_dir(self, review_id: str) -> Path:
        """Trusted, id-derived directory for a review's artifacts."""
        if not isinstance(review_id, str) or not models._REVIEW_ID.match(review_id):
            raise ValueError("review.id must be a 32-hex UUID")
        d = self.root / review_id
        if d.is_symlink():
            raise ValueError("review directory must not be a symlink")
        created = not d.exists()
        d.mkdir(parents=True, exist_ok=True)
        if d.resolve() != d or not d.is_dir():
            raise ValueError("review directory escapes trusted root")
        if created:
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return d

    def _record_path(self, review_id: str) -> Path:
        return self.run_dir(review_id) / f"{review_id}.json"

    def _lock_path(self, review_id: str) -> Path:
        return self.run_dir(review_id) / ".review.lock"

    def _acquire(self, review_id: str) -> _AdvisoryLock:
        path = self._lock_path(review_id)
        with _REGISTRY_LOCK:
            lock = _PATH_LOCKS.get(path)
            if lock is None:
                lock = _AdvisoryLock(path)
                _PATH_LOCKS[path] = lock
            return lock

    @contextmanager
    def record_lock(self, review_id: str):
        """Exclusive per-review lock; safe across threads and sibling processes."""
        lock = self._acquire(review_id)
        with lock:
            yield

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a brand-new review record and return it."""
        record = dict(record)
        record["id"] = record.get("id") or uuid.uuid4().hex
        record["version"] = 1
        record = models.validate_review(record)
        with self.record_lock(record['id']):
            if self._read(record['id']) is not None:
                raise StaleRecordError("review already exists")
            self._write(record)
        return record

    def save(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Atomically persist a review record (validating + version check)."""
        if 'version' not in record:
            raise StaleRecordError('save requires the version returned by get/create')
        record = models.validate_review(dict(record))
        rid = record["id"]
        with self.record_lock(rid):
            current = self._read(rid)
            if current is None or current['version'] != record['version']:
                raise StaleRecordError(
                    f"review {rid} changed since read "
                    f"(supplied version {record.get('version')})"
                )
            record["version"] = current['version'] + 1
            record['updated_at'] = models.now_iso()
            self._write(record)
            return record

    def get(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Return a validated review record, or None if it does not exist."""
        if not isinstance(review_id, str) or not models._REVIEW_ID.match(review_id):
            raise ValueError("review.id must be a 32-hex UUID")
        with self.record_lock(review_id):
            current = self._read(review_id)
            if current is None:
                return None
            return models.validate_review(current)

    def review_ids(self):
        """Discover publications even when their record cannot be parsed."""
        ids = []
        for path in self.root.iterdir():
            if path.is_symlink() or not path.is_dir() or not models._REVIEW_ID.fullmatch(path.name): continue
            candidates = (path / f'{path.name}.json', path / '.head.json')
            if any(p.exists() or p.is_symlink() for p in candidates): ids.append(path.name)
        return sorted(ids)

    def list(self) -> List[Dict[str, Any]]:
        """Return every review, oldest first, each one validated."""
        out: List[Dict[str, Any]] = []
        for path in sorted(self.root.iterdir()):
            if path.is_symlink() or not path.is_dir() or not models._REVIEW_ID.fullmatch(path.name):
                continue
            try:
                record = self.get(path.name)
            except (ValueError, OSError):
                continue
            if record is not None:
                out.append(models.validate_review(record))
        out.sort(key=lambda r: (r.get("created_at", ""), r["id"]))
        return out

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _read(self, review_id: str) -> Optional[Dict[str, Any]]:
        path = self._record_path(review_id)
        if path.is_symlink():
            raise ValueError("record must not be a symlink")
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, encoding='utf-8') as stream:
                text = stream.read()
        except FileNotFoundError:
            return None
        data = models.validate_review(json.loads(text))
        if data['id'] != review_id:
            raise ValueError('record id does not match its path')
        return data

    def _write(self, record: Dict[str, Any]) -> None:
        path = self._record_path(record["id"])
        atomic_write(path, (json.dumps(record, indent=2) + '\n').encode('utf-8'))
