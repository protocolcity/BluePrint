"""pc-1554: single-flight /api/operations cache."""
from __future__ import annotations

import threading
import time
import unittest

from server.operations_cache import (
    OperationsCache,
    cached_operations_snapshot,
    reset_operations_cache,
)


class OperationsCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_operations_cache()

    def tearDown(self) -> None:
        reset_operations_cache()

    def test_concurrent_waiters_share_one_build(self) -> None:
        calls = []
        started = threading.Event()

        def builder():
            calls.append(1)
            started.set()
            time.sleep(0.25)
            return {'n': len(calls)}

        cache = OperationsCache(builder, ttl=2.0, wait=2.0)
        results = []

        def worker():
            results.append(cache.get())

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        self.assertTrue(started.wait(1.0))
        for thread in threads:
            thread.join(2.0)
            self.assertFalse(thread.is_alive())
        self.assertEqual(calls, [1])
        self.assertEqual(results, [{'n': 1}, {'n': 1}, {'n': 1}])

    def test_ttl_serves_the_same_snapshot_without_rebuilding(self) -> None:
        calls = []

        def builder():
            calls.append(1)
            return {'n': len(calls)}

        cache = OperationsCache(builder, ttl=1.0, wait=1.0)
        self.assertEqual(cache.get()['n'], 1)
        self.assertEqual(cache.get()['n'], 1)
        self.assertEqual(calls, [1])

    def test_waiter_timeout_without_stale_raises(self) -> None:
        started = threading.Event()

        def builder():
            started.set()
            time.sleep(0.4)
            return {'ok': True}

        cache = OperationsCache(builder, ttl=1.0, wait=0.05)
        threading.Thread(target=cache.get, daemon=True).start()
        self.assertTrue(started.wait(1.0))
        with self.assertRaises(TimeoutError):
            cache.get()

    def test_cached_operations_snapshot_is_keyed_per_binder(self) -> None:
        seen = []

        def make_builder(name):
            def builder():
                seen.append(name)
                return {'workspace': name}
            return builder

        first = cached_operations_snapshot('alpha', builder=make_builder('alpha'), ttl=2.0)
        second = cached_operations_snapshot('beta', builder=make_builder('beta'), ttl=2.0)
        again = cached_operations_snapshot('alpha', builder=make_builder('other'), ttl=2.0)
        self.assertEqual(first['workspace'], 'alpha')
        self.assertEqual(second['workspace'], 'beta')
        self.assertEqual(again['workspace'], 'alpha')
        self.assertEqual(seen, ['alpha', 'beta'])


if __name__ == '__main__':
    unittest.main()
