"""Strict tool-call adapter with persistent at-most-one dispatch claim per call ID.

Trusted local storage only. Claim-before-execute may leave an unresolved operation
on crash; no automatic retries, exactly-once execution, or actor attribution.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Callable

from .core import canonical, sha256
from .tool_session import ToolOutcome

TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")


def _token(value):
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


@dataclass(frozen=True)
class DispatchResult:
    status: str
    outcome: ToolOutcome | None = None


@dataclass(frozen=True)
class DispatchRecord:
    status: str
    outcome: ToolOutcome | None = None


def _valid_outcome(outcome):
    return (isinstance(outcome, ToolOutcome)
            and outcome.actor_status in ("RETURNED", "RAISED", "NOT_INVOKED")
            and outcome.verdict in ("STATE_MATCHED_UNATTRIBUTED", "STATE_PREEXISTING", "STATE_MISMATCH", "INDETERMINATE")
            and (outcome.actor_status != "NOT_INVOKED" or outcome.verdict == "INDETERMINATE"))


class DispatchLedger:
    """Explicitly provision a trusted database once; never silently recreate it."""
    def __init__(self, path: Path, *, initialize: bool = False, upgrade: bool = False):
        if initialize and upgrade:
            raise ValueError("choose initialize or upgrade, not both")
        self.path = Path(path).absolute()
        if initialize:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with closing(self._connect()) as conn:
            if initialize:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("CREATE TABLE dispatch (scope TEXT NOT NULL, call_id TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(scope,call_id))")
                self._install_outcomes(conn)
                conn.commit()
            elif upgrade:
                conn.execute("BEGIN IMMEDIATE")
                if conn.execute("PRAGMA user_version").fetchone() != (0,):
                    raise ValueError("only legacy dispatch schema can be upgraded")
                conn.execute("SELECT scope, call_id, digest FROM dispatch LIMIT 0")
                self._install_outcomes(conn)
                conn.commit()
            self._check_schema(conn)

    @staticmethod
    def _install_outcomes(conn):
        conn.execute("CREATE TABLE dispatch_outcome (scope TEXT NOT NULL, call_id TEXT NOT NULL, status TEXT NOT NULL, actor_status TEXT, verdict TEXT, PRIMARY KEY(scope,call_id), FOREIGN KEY(scope,call_id) REFERENCES dispatch(scope,call_id), CHECK ((status='UNRESOLVED' AND actor_status IS NULL AND verdict IS NULL) OR (status='OUTCOME_RECORDED' AND actor_status IS NOT NULL AND verdict IS NOT NULL)))")
        conn.execute("PRAGMA user_version=1")

    @staticmethod
    def _check_schema(conn):
        if conn.execute("PRAGMA user_version").fetchone() != (1,):
            raise ValueError("unsupported dispatch schema; legacy databases require explicit upgrade")
        conn.execute("SELECT scope, call_id, digest FROM dispatch LIMIT 0")
        conn.execute("SELECT scope, call_id, status, actor_status, verdict FROM dispatch_outcome LIMIT 0")

    def _connect(self):
        conn = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=3)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.Error:
            conn.close()
            raise

    def claim(self, scope: str, call_id: str, digest: str) -> str:
        if not _token(scope) or not _token(call_id) or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            return "INVALID_CALL"
        try:
            with closing(self._connect()) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._check_schema(conn)
                row = conn.execute("SELECT digest FROM dispatch WHERE scope=? AND call_id=?", (scope, call_id)).fetchone()
                if row is not None:
                    return "ALREADY_CLAIMED" if row[0] == digest else "CALL_ID_CONFLICT"
                conn.execute("INSERT INTO dispatch VALUES (?,?,?)", (scope, call_id, digest))
                conn.commit()
                return "CLAIMED"
        except (sqlite3.Error, ValueError):
            return "STORAGE_UNAVAILABLE"

    def record(self, scope: str, call_id: str, digest: str, outcome: ToolOutcome | None) -> bool:
        """Record a trusted verifier result once; never overwrite or re-dispatch."""
        if (not _token(scope) or not _token(call_id) or not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or (outcome is not None and not _valid_outcome(outcome))):
            return False
        fields = ("UNRESOLVED", None, None) if outcome is None else ("OUTCOME_RECORDED", outcome.actor_status, outcome.verdict)
        try:
            with closing(self._connect()) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self._check_schema(conn)
                row = conn.execute("SELECT digest FROM dispatch WHERE scope=? AND call_id=?", (scope, call_id)).fetchone()
                if row != (digest,):
                    return False
                conn.execute("INSERT INTO dispatch_outcome VALUES (?,?,?,?,?)", (scope, call_id, *fields))
                conn.commit()
                return True
        except (sqlite3.Error, ValueError):
            return False

    def lookup(self, scope: str, call_id: str, *, expected_digest: str | None = None) -> DispatchRecord:
        """Read the local journal; absence is not proof that an actor did nothing."""
        if (not _token(scope) or not _token(call_id)
                or (expected_digest is not None and (not isinstance(expected_digest, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", expected_digest)))):
            return DispatchRecord("INVALID_CALL")
        try:
            with closing(self._connect()) as conn:
                self._check_schema(conn)
                row = conn.execute("SELECT d.digest,o.status,o.actor_status,o.verdict FROM dispatch d LEFT JOIN dispatch_outcome o USING(scope,call_id) WHERE d.scope=? AND d.call_id=?", (scope, call_id)).fetchone()
            if row is None:
                return DispatchRecord("NOT_FOUND")
            if expected_digest is not None and row[0] != expected_digest:
                return DispatchRecord("CALL_ID_CONFLICT")
            row = row[1:]
            if row == (None, None, None):
                return DispatchRecord("PENDING_RECONCILIATION")
            if row == ("UNRESOLVED", None, None):
                return DispatchRecord("UNRESOLVED")
            outcome = ToolOutcome(row[1], row[2])
            if row[0] == "OUTCOME_RECORDED" and _valid_outcome(outcome):
                return DispatchRecord("OUTCOME_RECORDED", outcome)
            return DispatchRecord("STORAGE_UNAVAILABLE")
        except (sqlite3.Error, ValueError):
            return DispatchRecord("STORAGE_UNAVAILABLE")


def dispatch_write(*, ledger: DispatchLedger, scope: str, permitted_resource: str,
                   expected_value: str, call: dict,
                   verify: Callable[[Callable[[], object]], ToolOutcome],
                   write: Callable[[str, str], object]) -> DispatchResult:
    """Accept one Chat Completions-shaped function call for a caller-pinned write.

    The caller, not the model, chooses scope, allowed resource and expected value.
    The caller supplies a trusted verifier wrapping the actual write. This is an
    offline protocol adapter, not a tested integration with a hosted model SDK.
    """
    try:
        if (not _token(scope) or not _token(permitted_resource) or not isinstance(expected_value, str)
                or not callable(verify) or not callable(write)
                or not isinstance(call, dict) or set(call) != {"id", "type", "function"}
                or not _token(call["id"]) or call["type"] != "function"):
            return DispatchResult("INVALID_CALL")
        fn = call["function"]
        if not isinstance(fn, dict) or set(fn) != {"name", "arguments"} or fn["name"] != "write_resource":
            return DispatchResult("INVALID_CALL")
        raw = fn["arguments"]
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 65536:
            return DispatchResult("INVALID_CALL")
        args = json.loads(raw, object_pairs_hook=_unique)
        if not isinstance(args, dict) or set(args) != {"resource", "value"}:
            return DispatchResult("INVALID_CALL")
        if not isinstance(args["resource"], str) or not isinstance(args["value"], str):
            return DispatchResult("INVALID_CALL")
        if args["resource"] != permitted_resource or args["value"] != expected_value:
            return DispatchResult("OUTSIDE_INTENT")
        digest = sha256(canonical({"name":fn["name"], "arguments":args}))
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return DispatchResult("INVALID_CALL")
    claimed = ledger.claim(scope, call["id"], digest)
    if claimed == "ALREADY_CLAIMED":
        record = ledger.lookup(scope, call["id"])
        return DispatchResult(claimed, record.outcome)
    if claimed != "CLAIMED":
        return DispatchResult(claimed)
    # A buggy trusted synchronous adapter must not accidentally invoke the writer
    # twice, move it to a different thread, or retain it for delayed execution.
    owner = threading.get_ident()
    lock = threading.Lock()
    invoked = False
    closed = False
    violated = False
    actual_status = "NOT_INVOKED"

    def once():
        nonlocal invoked, violated, actual_status
        with lock:
            if closed or invoked or threading.get_ident() != owner:
                violated = True
                raise RuntimeError("dispatch callback is single-use and synchronous")
            invoked = True
        try:
            result = write(permitted_resource, expected_value)
        except Exception:
            actual_status = "RAISED"
            raise
        actual_status = "RETURNED"
        return result

    try:
        outcome = verify(once)
    except Exception:
        outcome = None
    finally:
        with lock:
            closed = True
    if violated or not _valid_outcome(outcome) or outcome.actor_status != actual_status:
        ledger.record(scope, call["id"], digest, None)
        return DispatchResult("CLAIMED_UNRESOLVED")
    if not ledger.record(scope, call["id"], digest, outcome):
        return DispatchResult("CLAIMED_UNRESOLVED")
    return DispatchResult("CLAIMED", outcome)
