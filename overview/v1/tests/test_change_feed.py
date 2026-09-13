"""D2 change feed — watcher unit tests (disposable workspaces only).

Locks: a stat change on a store file emits one event with source
``worklane``; a ledger append emits ``workforce``; a supervisor report
emits ``supervisor``; bursts within the debounce window coalesce to one
event; a full subscriber set refuses a ninth client; no path outside the
basename ever travels.
"""
from __future__ import annotations

import queue
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

from server.change_feed import ChangeFeed, DEBOUNCE_SECS, MAX_CLIENTS  # noqa: E402


def _drain(q: "queue.Queue") -> list[dict]:
    events = []
    while True:
        try:
            events.append(q.get_nowait())
        except queue.Empty:
            break
    return events


class ChangeFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "worklane" / "worklane" / "local" / "data").mkdir(parents=True)
        workforce = self.root / ".protocolcity" / "workforce" / "local"
        workforce.mkdir(parents=True)
        (workforce / "roster.json").write_text("{}")
        (workforce / "daemon.json").write_text("{}")
        (workforce / "ledger").mkdir()
        (workforce / "reports" / "supervisor").mkdir(parents=True)
        self.feed = ChangeFeed(self.root, poll_interval=999)
        client = self.feed.subscribe()
        assert client is not None
        self.client_id, self.inbox = client

    def tearDown(self) -> None:
        self.feed.unsubscribe(self.client_id)
        self.feed.stop()

    def test_store_file_change_emits_worklane(self) -> None:
        db = self.root / "worklane" / "worklane" / "local" / "data" / "acme.db"
        db.write_bytes(b"x")
        self.feed.poll_once()
        events = _drain(self.inbox)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "worklane")
        self.assertEqual(events[0]["path"], "acme.db")
        self.assertIn("observed_at", events[0])

    def test_ledger_append_emits_workforce(self) -> None:
        ledger = self.root / ".protocolcity" / "workforce" / "local" / "ledger" / "bp-claude-implementer.log"
        ledger.write_text("2026-09-13T00:00:00Z START budget_secs=60\n")
        self.feed.poll_once()
        _drain(self.inbox)
        time.sleep(DEBOUNCE_SECS + 0.05)
        ledger.write_text(ledger.read_text() + "2026-09-13T00:01:00Z STOP\n")
        self.feed.poll_once()
        events = _drain(self.inbox)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "workforce")
        self.assertEqual(events[0]["path"], "bp-claude-implementer.log")

    def test_supervisor_report_emits_supervisor(self) -> None:
        report = self.root / ".protocolcity" / "workforce" / "local" / "reports" / "supervisor" / "2026-09-13T00-00-00.json"
        report.write_text("{}")
        self.feed.poll_once()
        events = _drain(self.inbox)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "supervisor")
        self.assertEqual(events[0]["path"], report.name)

    def test_bursts_within_debounce_coalesce_to_one_event(self) -> None:
        daemon = self.root / ".protocolcity" / "workforce" / "local" / "daemon.json"
        for i in range(4):
            daemon.write_text("{\"tick\": %d}" % i)
            self.feed.poll_once()
        events = _drain(self.inbox)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "workforce")

    def test_disconnect_frees_slot(self) -> None:
        feed = ChangeFeed(self.root, poll_interval=999)
        clients = []
        for _ in range(MAX_CLIENTS):
            sub = feed.subscribe()
            self.assertIsNotNone(sub)
            clients.append(sub)
        self.assertIsNone(feed.subscribe())
        cid, _ = clients[0]
        feed.unsubscribe(cid)
        self.assertIsNotNone(feed.subscribe())
        feed.stop()

    def test_no_path_leaks_only_basename(self) -> None:
        db = self.root / "worklane" / "worklane" / "local" / "data" / "acme.db"
        db.write_bytes(b"x")
        self.feed.poll_once()
        events = _drain(self.inbox)
        for event in events:
            self.assertNotIn(str(self.root), event["path"])
            self.assertEqual(event["path"], Path(event["path"]).name)


if __name__ == "__main__":
    unittest.main()
