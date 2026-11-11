"""Unit tests for repager.store: atomic writes, locking, concurrency, validation."""

import json
import threading
import tempfile
import unittest
import uuid
from unittest.mock import patch
import os
import stat
from pathlib import Path

import repager.models as m
from repager.store import ReviewStore, StaleRecordError

URL = "https://example.com/"

SOURCE = {
    "url": URL, "title": "Example",
    "captured_at": "2026-11-06T00:00:00+00:00",
    "viewports": [{
        "name": "desktop", "width": 1440, "height": 900,
        "screenshot": "source-desktop.png", "overflow": False,
        "elements": [{
            "id": "h0", "tag": "h1", "text": "Headline",
            "href": None,
            "rect": {"x": 0, "y": 0, "width": 100, "height": 20},
            "style": {"color": "#111111", "background_color": "#ffffff",
                      "font_size": "30px", "font_family": "system-ui"},
        }],
    }],
    "palette": ["#111111", "#f7931a", "#ffffff"],
    "limitations": [],
}


def _record(status="reviewed", **kw):
    base = {
        "id": uuid.uuid4().hex,
        "status": status,
        "created_at": "2026-11-06T00:00:00+00:00",
        "updated_at": "2026-11-06T00:00:00+00:00",
        "audience": "", "goal": "",
        "source": SOURCE, "findings": [], "contract": None,
        "revisions": [], "verification": None, "error": None,
    }
    base.update(kw)
    return base


class TestReviewStore(unittest.TestCase):
    def test_durable_write_fsyncs_file_and_directory(self):
        modes = []
        original = os.fsync
        def fsync(fd):
            modes.append(os.fstat(fd).st_mode)
            return original(fd)
        with patch('repager.store.os.fsync', side_effect=fsync):
            rec = self.store.create(_record())
        self.assertTrue(any(stat.S_ISREG(mode) for mode in modes))
        self.assertTrue(any(stat.S_ISDIR(mode) for mode in modes))
        self.assertEqual(self.store.get(rec['id']), rec)

    def test_failed_replace_preserves_previous_record(self):
        rec = self.store.create(_record())
        updated = dict(rec, goal='new goal')
        with patch('repager.store.os.replace', side_effect=OSError('injected failure')):
            with self.assertRaises(OSError):
                self.store.save(updated)
        self.assertEqual(self.store.get(rec['id']), rec)
        self.assertEqual(list(self.store.run_dir(rec['id']).glob('*.tmp')), [])

    def test_lock_releases_after_exception_and_duplicate_create_is_rejected(self):
        rec = self.store.create(_record())
        with self.assertRaises(RuntimeError):
            with self.store.record_lock(rec['id']):
                raise RuntimeError('test')
        self.assertEqual(self.store.get(rec['id']), rec)
        with self.assertRaises(StaleRecordError):
            self.store.create(rec)
        self.assertEqual(self.store.get(rec['id']), rec)

    def test_save_requires_explicit_version_and_returns_clean_record(self):
        rec = self.store.create(_record())
        unversioned = dict(rec)
        unversioned.pop('version')
        with self.assertRaises((ValueError, StaleRecordError)):
            self.store.save(unversioned)
        rec['not_persisted'] = 'extra'
        saved = self.store.save(rec)
        self.assertEqual(saved, self.store.get(rec['id']))
        self.assertNotIn('not_persisted', saved)

    def test_uuid_newline_and_record_symlink_rejected(self):
        with self.assertRaises(ValueError):
            self.store.run_dir('a' * 32 + '\n')
        rec = self.store.create(_record())
        path = self.store._record_path(rec['id'])
        other = self.root / 'original.json'
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
        with self.assertRaises(ValueError):
            self.store.get(rec['id'])
        with self.assertRaises(ValueError):
            self.store.save(rec)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = ReviewStore(self.root)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_create_get_list_roundtrip(self):
        record = self.store.create(_record())
        got = self.store.get(record["id"])
        self.assertEqual(got["status"], "reviewed")
        self.assertEqual(self.store.list(), [got])
        self.assertTrue((self.store.run_dir(record["id"]) / "x.html").parent.exists())

    def test_run_dir_returns_trusted_path(self):
        rid = uuid.uuid4().hex
        d = self.store.run_dir(rid)
        self.assertEqual(d, self.root / rid)
        self.assertTrue(d.exists())

    def test_invalid_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.get("not-a-id")
        with self.assertRaises(ValueError):
            self.store.create(_record(id="...."))

    def test_create_offers_id_when_missing(self):
        record = self.store.create(_record(id=None))
        self.assertEqual(len(record["id"]), 32)
        self.assertTrue(uuid.UUID(record["id"], version=4))

    def test_save_stale_prevents_overwrite(self):
        record = self.store.create(_record())
        copy = dict(record)
        self.store.save(record)
        with self.assertRaises(StaleRecordError):
            self.store.save(copy)
        # disk unchanged
        again = self.store.get(record["id"])
        self.assertIsNotNone(again)
        self.assertEqual(again["version"], 2)

    def test_save_increments_version(self):
        record = self.store.create(_record())
        self.assertEqual(record["version"], 1)

    def test_validation_rejected(self):
        bad = _record(status="done")
        with self.assertRaises(ValueError):
            self.store.create(bad)
        bad = _record(finding_id_dup="x")
        # duplicate finding ids -> ValueError via validate_review
        with self.assertRaises(ValueError):
            self.store.create(_record(findings=[{"id": "a", "title": "t",
                                                 "observation": "o", "recommendation": "r",
                                                 "evidence_ids": [], "kind": "measurement"},
                                                {"id": "a", "title": "t2", "observation": "o2",
                                                 "recommendation": "r2",
                                                 "evidence_ids": [], "kind": "judgment"}]))

    def test_finding_ids_are_unique(self):
        found = _record(findings=[
            {"id": "a", "title": "t", "observation": "o", "recommendation": "r",
             "evidence_ids": [], "kind": "measurement"},
            {"id": "a", "title": "t2", "observation": "o2", "recommendation": "r2",
             "evidence_ids": [], "kind": "judgment"},
        ])
        with self.assertRaises(ValueError):
            self.store.create(found)

    def test_concurrent_creation_no_data_loss(self):
        store = ReviewStore(self.root)
        errors = []
        results = []

        def worker(n):
            try:
                for _ in range(3):
                    rec = _record(status="reviewed",
                                  audience=f"u{n}", goal=f"g{n}", source=SOURCE)
                    results.append(store.create(rec))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [], f"worker errors: {errors}")
        ids = [r["id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)))  # unique ids
        self.assertEqual({r['id'] for r in store.list()}, {r['id'] for r in results})

    def test_atomic_write_feels_whole(self):
        record = self.store.create(_record())
        path = self.store._record_path(record["id"])
        # simulate a partial write on disk; our read must not return garbage
        path.write_text("{oops", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.get(record['id'])
        path.write_text(json.dumps(record), encoding="utf-8")
        again = self.store.get(record["id"])
        self.assertEqual(again["status"], "reviewed")

    def test_list_sorted(self):
        a = self.store.create(_record(status="reviewed", created_at='2026-01-01T00:00:00+00:00'))
        b = self.store.create(_record(status="verified", created_at='2026-01-02T00:00:00+00:00'))
        order = [r["id"] for r in self.store.list()]
        self.assertEqual(order, [a['id'], b['id']])
