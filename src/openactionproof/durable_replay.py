"""SQLite replay consumption for trusted local storage; no distributed guarantee."""
from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import sqlite3

from .attestation import Intent, verify


class DurableReplayGuard:
    """Explicitly provision a new DB; reopening never creates a missing DB.

    Requires a trusted local directory and filesystem with SQLite locking.
    Never delete/restore an older DB while challenges remain valid.
    """

    def __init__(self, path: Path, capacity: int = 10000, *, initialize: bool = False):
        if type(capacity) is not int or not 1 <= capacity <= 1000000:
            raise ValueError("capacity must be 1..1000000")
        self.path = Path(path).absolute()
        self.capacity = capacity
        if initialize:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with closing(self._connect()) as conn:
            if initialize:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("CREATE TABLE config (id INTEGER PRIMARY KEY CHECK(id=1), capacity INTEGER NOT NULL)")
                conn.execute("INSERT INTO config VALUES (1, ?)", (capacity,))
                conn.execute("CREATE TABLE consumed (observer TEXT NOT NULL, challenge TEXT NOT NULL, PRIMARY KEY(observer, challenge))")
                conn.commit()
            self._check_config(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=3, isolation_level=None)
        try:
            conn.execute("PRAGMA synchronous=FULL")
        except sqlite3.Error:
            conn.close()
            raise
        return conn

    def _check_config(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT capacity FROM config WHERE id=1").fetchone()
        if row != (self.capacity,):
            raise ValueError("Replay database capacity mismatch")

    def accept(self, key: bytes, intent: Intent, envelope) -> bool:
        """Authenticate and atomically consume once; storage failure denies acceptance."""
        if not verify(key, intent, envelope):
            return False
        try:
            with closing(self._connect()) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._check_config(conn)
                if conn.execute("SELECT COUNT(*) FROM consumed").fetchone()[0] >= self.capacity:
                    conn.rollback()
                    return False
                conn.execute("INSERT INTO consumed VALUES (?, ?)", (intent.observer_id, intent.challenge))
                conn.commit()
                return True
        except (sqlite3.Error, ValueError):
            return False
