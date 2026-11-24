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


class DispatchLedger:
    """Explicitly provision a trusted database once; never silently recreate it."""
    def __init__(self, path: Path, *, initialize: bool = False):
        self.path = Path(path).absolute()
        if initialize:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        with closing(self._connect()) as conn:
            if initialize:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("CREATE TABLE dispatch (scope TEXT NOT NULL, call_id TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(scope,call_id))")
                conn.commit()
            conn.execute("SELECT scope, call_id, digest FROM dispatch LIMIT 0")

    def _connect(self):
        conn = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=3)
        try:
            conn.execute("PRAGMA synchronous=FULL")
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
                row = conn.execute("SELECT digest FROM dispatch WHERE scope=? AND call_id=?", (scope, call_id)).fetchone()
                if row is not None:
                    return "ALREADY_CLAIMED" if row[0] == digest else "CALL_ID_CONFLICT"
                conn.execute("INSERT INTO dispatch VALUES (?,?,?)", (scope, call_id, digest))
                conn.commit()
                return "CLAIMED"
        except sqlite3.Error:
            return "STORAGE_UNAVAILABLE"


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
    if claimed != "CLAIMED":
        return DispatchResult(claimed)
    try:
        outcome = verify(lambda: write(permitted_resource, expected_value))
        if not isinstance(outcome, ToolOutcome):
            return DispatchResult("CLAIMED_UNRESOLVED")
        return DispatchResult("CLAIMED", outcome)
    except Exception:
        return DispatchResult("CLAIMED_UNRESOLVED")
