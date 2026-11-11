"""Core security regressions; injected adapters only, never a real browser/model."""
import copy
import multiprocessing
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from repager.store import ReviewStore, StaleRecordError
from repager.service import ReviewService, ServiceError
from test_core_service import FakeBrowser, FakeLLM, _source, approve_displayed
from test_core_store import _record


def locked_increment(root, rid, count):
    store = ReviewStore(Path(root))
    for _ in range(count):
        with store.record_lock(rid):
            record = store.get(rid)
            record['goal'] = str(int(record['goal']) + 1)
            store.save(record)


class CoreRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ReviewStore(Path(self.tmp.name))

    def test_nested_locks_across_instances_and_threads(self):
        rec = self.store.create(_record(goal='0'))
        rid = rec['id']
        other = ReviewStore(self.store.root)
        with self.store.record_lock(rid):
            with other.record_lock(rid):
                other.save(other.get(rid))
        errors = []
        def run():
            try:
                locked_increment(self.tmp.name, rid, 20)
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=run) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.store.get(rid)['goal'], '80')

    def test_multiprocess_lock(self):
        rec = self.store.create(_record(goal='0'))
        ctx = multiprocessing.get_context('spawn')
        processes = [ctx.Process(target=locked_increment, args=(self.tmp.name, rec['id'], 12)) for _ in range(3)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(15)
            if process.is_alive():
                process.terminate()
                process.join()
                self.fail('record lock deadlocked')
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(self.store.get(rec['id'])['goal'], '36')

    def test_corrupt_record_is_not_overwritten(self):
        rec = self.store.create(_record())
        path = self.store.run_dir(rec['id']) / (rec['id'] + '.json')
        path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.store.save(rec)
        self.assertEqual(path.read_text(), '{broken')

    def test_run_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            rid = 'a' * 32
            (self.store.root / rid).symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.store.run_dir(rid)

    def test_real_host_parsed_result_and_metadata(self):
        fake = FakeLLM()
        class Host:
            def complete_structured(self, **kwargs):
                return SimpleNamespace(parsed=copy.deepcopy(fake.result), model='host-model', provider='host-provider')
        service = ReviewService(self.store, FakeBrowser(), Host())
        rec = service.create_review('https://example.com/', 'audience', 'goal')
        approve_displayed(service, rec['id'], rec['findings'][0]['id'])
        generated = service.generate(rec['id'])
        self.assertEqual(generated['status'], 'generated')
        self.assertEqual(generated['revisions'][0]['model'], 'host-model')
        self.assertEqual(generated['revisions'][0]['provider'], 'host-provider')


if __name__ == '__main__':
    unittest.main()
