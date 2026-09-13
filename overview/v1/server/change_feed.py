"""D2 change feed — one push when the engine files BluePrint already reads move.

Watches, with a single shared background thread and ``os.stat`` polling
(stdlib only, no third-party watcher):

- WorkLane store files: ``<binder>/worklane/worklane/local/data/*.db``
- WorkForce roster + daemon files and the ledger directory beside them
- The supervisor reports directory beside the roster (``reports/supervisor``)

A stat change in any group emits one ``{"source", "path", "observed_at"}``
event to every subscriber, coalesced so a burst of writes to the same
source produces at most one event per ``DEBOUNCE_SECS``. Never the file
content, never a path outside the workspace — only the basename travels.
"""
from __future__ import annotations

import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .local_projectors import resolve_daemon_path, resolve_roster_path, worklane_data_dir

POLL_INTERVAL_SECS = 1.0
DEBOUNCE_SECS = 0.5
HEARTBEAT_SECS = 20.0
MAX_CLIENTS = 8

SOURCES = ("worklane", "workforce", "supervisor")


def _within(path: Path, root: Path) -> bool:
    """Resolved-symlink boundary check — a target outside the workspace never counts."""
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def _stamp(path: Path, key: str) -> tuple | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (key, path.name, st.st_mtime_ns, st.st_size)


def _signature(paths: Iterable[tuple[Path, str]]) -> tuple:
    """Order-independent identity for a group of files.

    Keyed by each file's path relative to its source's root directory (a
    plain basename is not unique — the workforce group merges roster,
    daemon and ledger files, so a ledger member can share a name with the
    daemon file). Covers appends (mtime/size move), additions and removals
    (the tuple's membership changes) without needing to know the file list
    ahead of time.
    """
    rows = [row for row in (_stamp(p, key) for p, key in paths) if row is not None]
    return tuple(sorted(rows))


def _changed_name(before: tuple, after: tuple) -> str:
    """Basename most likely responsible for the move — never a full path."""
    prior = {row[0]: row for row in before}
    for row in after:
        if prior.get(row[0]) != row:
            return row[1]
    after_keys = {row[0] for row in after}
    removed_keys = sorted(key for key in prior if key not in after_keys)
    return prior[removed_keys[0]][1] if removed_keys else ""


def _worklane_paths(root: Path) -> list[tuple[Path, str]]:
    data = worklane_data_dir(root)
    if not _within(data, root) or not data.is_dir():
        return []
    return [(p, p.name) for p in data.glob("*.db")]


def _workforce_paths(root: Path) -> list[tuple[Path, str]]:
    paths: list[tuple[Path, str]] = []
    roster = resolve_roster_path(root)
    if roster is not None and _within(roster, root):
        paths.append((roster, roster.name))
    daemon = resolve_daemon_path(root)
    if daemon is not None and _within(daemon, root):
        paths.append((daemon, daemon.name))
        ledger = daemon.resolve().parent / "ledger"
        if _within(ledger, root) and ledger.is_dir():
            paths.extend((p, f"ledger/{p.name}") for p in ledger.iterdir() if p.is_file())
    return paths


def _supervisor_paths(root: Path) -> list[tuple[Path, str]]:
    roster = resolve_roster_path(root)
    if roster is None or not _within(roster, root):
        return []
    reports = roster.parent / "reports" / "supervisor"
    if not _within(reports, root) or not reports.is_dir():
        return []
    return [(p, p.name) for p in reports.iterdir() if p.is_file()]


_SOURCE_PATHS = {
    "worklane": _worklane_paths,
    "workforce": _workforce_paths,
    "supervisor": _supervisor_paths,
}


class ChangeFeed:
    """Shared watcher: one poll thread feeds many bounded subscriber queues.

    The watcher never blocks on a slow subscriber — a full queue drops the
    event for that one client rather than stalling the poll loop or every
    other client.
    """

    def __init__(
        self,
        root: Path | None,
        poll_interval: float = POLL_INTERVAL_SECS,
        auto_poll: bool = True,
    ):
        self._root = root
        self._poll_interval = poll_interval
        self._auto_poll = auto_poll
        self._lock = threading.Lock()
        self._poll_lock = threading.Lock()
        self._clients: dict[int, "queue.Queue[dict]"] = {}
        self._next_id = 0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Baseline at construction time — boot state is not a "change";
        # only a later stat move is.
        self._signatures: dict[str, tuple] = {
            name: (_signature(_SOURCE_PATHS[name](root)) if root is not None else ())
            for name in SOURCES
        }
        self._last_emit: dict[str, float] = {name: float("-inf") for name in SOURCES}
        self._pending: dict[str, str] = {}

    def subscribe(self):
        with self._lock:
            if len(self._clients) >= MAX_CLIENTS:
                return None
            self._ensure_thread_started()
            client_id = self._next_id
            self._next_id += 1
            q: "queue.Queue[dict]" = queue.Queue(maxsize=32)
            self._clients[client_id] = q
            return client_id, q

    def unsubscribe(self, client_id: int) -> None:
        with self._lock:
            self._clients.pop(client_id, None)

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def stop(self) -> None:
        self._stop.set()

    def _ensure_thread_started(self) -> None:
        if not self._auto_poll:
            return
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._root is not None:
                self.poll_once()
            time.sleep(self._poll_interval)

    def poll_once(self) -> None:
        """One stat sweep — public so tests can drive it without a thread.

        Serialized: the background thread and a test's manual call must
        never run concurrently, or both can observe the same stat move and
        double-emit (the second sees the change only if it reads the prior
        signature before the first writes the new one).
        """
        with self._poll_lock:
            now = time.monotonic()
            for source in SOURCES:
                before = self._signatures[source]
                after = _signature(_SOURCE_PATHS[source](self._root))
                if after == before:
                    continue
                self._signatures[source] = after
                self._pending[source] = _changed_name(before, after)
            for source, path in list(self._pending.items()):
                if now - self._last_emit[source] < DEBOUNCE_SECS:
                    continue
                self._last_emit[source] = now
                del self._pending[source]
                self._broadcast(source, path)

    def _broadcast(self, source: str, path: str) -> None:
        event = {
            "source": source,
            "path": path,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            for q in self._clients.values():
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass
