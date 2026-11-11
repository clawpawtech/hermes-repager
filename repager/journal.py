"""Authenticated local record head with crash-recoverable, two-state publication.

This detects record-only edits and rollback. It is NOT an external monotonic
anchor: restoring both the record and its head/key from a full backup restores
that backup's state. A host owner controlling the key can forge local seals.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import integrity, models
from .store import atomic_write, StaleRecordError


class JournalError(ValueError):
    pass


class RecordJournal:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def state(record):
        # Store.save owns updated_at. Everything else, including version, source,
        # approval, complete history and receipt, belongs to the sealed state.
        return integrity.digest({k: v for k, v in record.items() if k != 'updated_at'})

    def _path(self, rid):
        return self.store.run_dir(rid) / '.head.json'

    def _write(self, rid, states):
        head = {'review_id': rid, 'states': list(states)}
        head['signature'] = integrity.sign(self.store.root, head)
        atomic_write(self._path(rid), json.dumps(head, sort_keys=True).encode())

    def check(self, record):
        path = self._path(record['id'])
        if path.is_symlink():
            raise JournalError('Review head integrity failed: symlink head is forbidden')
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                data = os.read(fd, 4097)
            finally:
                os.close(fd)
        except FileNotFoundError:
            modern_seals = (isinstance(record.get('contract'), dict) and bool(record['contract'].get('signature'))
                            or bool(record.get('review_events'))
                            or any('contract_snapshot' in r or 'origin' in r for r in record.get('revisions', [])))
            if record.get('integrity_version') or modern_seals:
                raise JournalError('Review head integrity failed: authenticated head is missing; modern seals cannot downgrade to legacy')
            # Pre-head records are inspectable, but unsigned approvals cannot be
            # used again. Explicit reapproval upgrades them through save().
            return
        except OSError as exc:
            raise JournalError('Review head integrity failed: head cannot be read safely') from exc
        try:
            if len(data) > 4096:
                raise ValueError('oversized head')
            head = json.loads(data)
            integrity.validate(self.store.root, head)
            states = head['states']
            if head['review_id'] != record['id'] or not isinstance(states, list) or not 1 <= len(states) <= 2:
                raise ValueError('wrong head identity or state count')
            state = self.state(record)
            if state not in states:
                raise ValueError('record signature/head mismatch: edited or rolled-back record')
            if len(states) == 2:
                # All callers hold the same advisory record lock. A pending
                # publication here therefore represents a crashed/lost-ack writer.
                self._write(record['id'], [state])
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise JournalError(f'Review head integrity failed: {exc}') from exc

    def get(self, rid):
        with self.store.record_lock(rid):
            record = self.store.get(rid)
            if record is not None:
                self.check(record)
            return record

    def create(self, record):
        record = models.validate_review(dict(record, version=1, integrity_version=1))
        rid = record['id']
        with self.store.record_lock(rid):
            if self.store.get(rid) is not None or self._path(rid).exists() or self._path(rid).is_symlink():
                raise StaleRecordError('review already exists or has an interrupted publication')
            state = self.state(record)
            self._write(rid, [state])
            created = self.store.create(record)
            if self.state(created) != state:
                raise JournalError('Review creation did not match its authenticated head')
            return created

    def save(self, record):
        rid = record['id']
        with self.store.record_lock(rid):
            current = self.store.get(rid)
            if current is None or record.get('version') != current['version']:
                raise StaleRecordError('review changed since read; reload before saving')
            self.check(current)
            prepared = models.validate_review(dict(record, integrity_version=1))
            prepared['version'] = current['version'] + 1
            before, after = self.state(current), self.state(prepared)
            # Both legitimate states are authenticated BEFORE record replacement.
            # A failed save retains before; a lost acknowledgement retains after.
            self._write(rid, [before, after])
            saved = self.store.save(dict(record, integrity_version=1))
            if self.state(saved) != after:
                raise JournalError('Published review differs from authenticated candidate')
            self._write(rid, [after])
            return saved
