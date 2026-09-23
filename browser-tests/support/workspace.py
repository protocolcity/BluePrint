"""Disposable synthetic workspace roots for browser journeys."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _seed_store(root: Path, name: str, *, registered: bool = True) -> None:
    if registered:
        manifest = root / name / ".protocolcity/desk-join.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps({"slug": name, "prefix": "demo", "display": name}),
            encoding="utf-8",
        )
    data = root / "worklane/worklane/local/data"
    data.mkdir(parents=True, exist_ok=True)
    db = data / f"{name}.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE tasks(
              id INTEGER, ext_id TEXT, title TEXT, description TEXT, status TEXT,
              priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT
            );
            CREATE TABLE task_comments(
              id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT
            );
            """
        )


def build_healthy_workspace(root: Path) -> Path:
    """Registered store with readable orders for Work, Projects, and reader."""
    root.mkdir(parents=True, exist_ok=True)
    _seed_store(root, "demo")
    with sqlite3.connect(root / "worklane/worklane/local/data/demo.db") as conn:
        conn.executemany(
            "INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    1,
                    None,
                    "Synthetic ready order",
                    "Browser fixture order for verification.",
                    "backlog",
                    2,
                    "2026-09-23T12:00:00Z",
                    json.dumps(["worker:demo-seat"]),
                    None,
                    None,
                ),
                (
                    2,
                    None,
                    "Deferred synthetic order",
                    "Shows deferred gate in filters.",
                    "backlog",
                    3,
                    "2026-09-23T12:00:00Z",
                    json.dumps([]),
                    "deferred",
                    "Waiting on prerequisite",
                ),
                (
                    3,
                    None,
                    "Live synthetic order",
                    "In progress row for seat views.",
                    "in_progress",
                    2,
                    "2026-09-23T12:05:00Z",
                    json.dumps(["worker:demo-seat"]),
                    None,
                    None,
                ),
            ],
        )
    papers = root / "demo/docs/Product"
    papers.mkdir(parents=True, exist_ok=True)
    (papers / "overview.md").write_text("# Synthetic paper\n\nFixture content.\n", encoding="utf-8")
    return root


def build_partial_workspace(root: Path) -> Path:
    """One readable store and one broken store for unavailable surfaces."""
    build_healthy_workspace(root)
    broken = root / "worklane/worklane/local/data/broken.db"
    broken.write_bytes(b"not-a-database")
    join = root / "broken/.protocolcity/desk-join.json"
    join.parent.mkdir(parents=True, exist_ok=True)
    join.write_text(
        json.dumps({"slug": "broken", "prefix": "brk", "display": "broken"}),
        encoding="utf-8",
    )
    return root


def build_empty_workspace(root: Path) -> Path:
    """Binder with no registered project stores."""
    root.mkdir(parents=True, exist_ok=True)
    (root / ".blueprint").mkdir(exist_ok=True)
    (root / ".blueprint/overview.json").write_text("{}", encoding="utf-8")
    return root
