"""Authenticated exact-snapshot checks for a declared local SQLite table scope.

Revisions and storage must be trusted. No event-history, actor attribution, or
coverage of side effects outside the observed table is implied.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import math
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Callable

from .core import canonical, sha256
from .durable_replay import DurableReplayGuard
from .observer import Observation, ObservationRequest
from .verified_observation import authenticate, observe_authenticated, assess_authenticated_pair

TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
MAX_ROWS = 256
MAX_VALUE_BYTES = 16384
MAX_REVISION = 2**63 - 1
SCOPE_RESOURCE = "resource-state.scope.v1"


def _token(value):
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _value(value):
    try:
        return isinstance(value, str) and len(value.encode("utf-8")) <= MAX_VALUE_BYTES
    except UnicodeError:
        return False


def scope_digest(state: dict[str, tuple[int, str]]) -> str:
    if not isinstance(state, dict) or not 0 < len(state) <= MAX_ROWS:
        raise ValueError("invalid scoped state size")
    for resource, entry in state.items():
        if (not _token(resource) or not isinstance(entry, tuple) or len(entry) != 2
                or type(entry[0]) is not int or not 0 <= entry[0] <= MAX_REVISION
                or not _value(entry[1])):
            raise ValueError("invalid scoped row")
    return sha256(canonical({"schema": SCOPE_RESOURCE, "rows": [[r, *state[r]] for r in sorted(state)]}))


class SQLiteScopeObserver:
    """Trusted in-process reference observer using a separate read-only connection."""
    def __init__(self, path: Path, observer_id: str):
        self.path = Path(path).absolute()
        self.observer_id = observer_id

    def observe(self, request: ObservationRequest) -> Observation:
        start = time.time_ns()
        if (not request.valid() or request.observer_id != self.observer_id or request.resource != SCOPE_RESOURCE
                or not request.not_before_ns <= start <= request.deadline_ns):
            raise ValueError("invalid observation request")
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=2)) as conn:
            rows = conn.execute("SELECT resource, revision, value FROM resource_state LIMIT ?", (MAX_ROWS + 1,)).fetchall()
        state = {resource: (revision, value) for resource, revision, value in rows}
        if len(state) != len(rows) or len(rows) > MAX_ROWS:
            raise ValueError("invalid scope cardinality")
        digest = scope_digest(state)
        end = time.time_ns()
        if not start <= end <= request.deadline_ns:
            raise ValueError("observation expired")
        return Observation(self.observer_id, SCOPE_RESOURCE, request.challenge, end,
                           sum(revision for revision, _ in state.values()), digest)


@dataclass(frozen=True)
class ScopedOutcome:
    actor_status: str
    verdict: str


def verify_scoped_write(*, database: Path, guard: DurableReplayGuard, key: bytes,
                        task_id: str, observer_id: str, initial: dict[str, tuple[int, str]],
                        target: str, desired: str, actor: Callable[[], object],
                        window_seconds: float = 0.5) -> ScopedOutcome:
    """Pin all initial rows and expected final rows before invoking a trusted actor.

    A correct outcome requires exactly the declared final snapshot (including
    revisions), not an authenticated causal or historical claim. Unobserved
    effects, transient effects restored before observation, and dishonest
    revision counters remain outside this contract.
    """
    if (not _token(task_id) or not _token(observer_id) or not _token(target) or not _value(desired)
            or not callable(actor) or not isinstance(key, bytes) or not 32 <= len(key) <= 128
            or type(window_seconds) not in (int, float) or not math.isfinite(window_seconds)
            or not 0.1 <= window_seconds <= 30):
        raise ValueError("invalid scope configuration")
    initial_hash = scope_digest(initial)
    if target not in initial or initial[target][1] == desired or initial[target][0] == MAX_REVISION:
        raise ValueError("target must exist, change value, and permit a revision increment")
    expected = dict(initial)
    expected[target] = (initial[target][0] + 1, desired)
    expected_hash = scope_digest(expected)
    observer = SQLiteScopeObserver(database, observer_id)
    duration = int(window_seconds * 1_000_000_000)

    def request():
        now = time.time_ns()
        return ObservationRequest(observer_id, SCOPE_RESOURCE, secrets.token_hex(32), now, now + duration)

    before = request()
    try:
        be = observe_authenticated(observer, key, task_id, expected_hash, before)
        observed = authenticate(key, task_id, expected_hash, before, be, now_ns=time.time_ns())
    except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError):
        observed = None
    if observed is None:
        return ScopedOutcome("NOT_INVOKED", "INDETERMINATE")
    if observed.state_sha256 != initial_hash:
        return ScopedOutcome("NOT_INVOKED", "PRECONDITION_MISMATCH")
    try:
        actor()
        status = "RETURNED"
    except Exception:
        status = "RAISED"
    remaining = (before.deadline_ns - time.time_ns()) / 1_000_000_000
    if remaining > 0:
        if remaining > window_seconds:
            return ScopedOutcome(status, "INDETERMINATE")
        time.sleep(remaining)
    after = request()
    if after.not_before_ns < before.deadline_ns:
        return ScopedOutcome(status, "INDETERMINATE")
    try:
        ae = observe_authenticated(observer, key, task_id, expected_hash, after)
    except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError):
        return ScopedOutcome(status, "INDETERMINATE")
    result = assess_authenticated_pair(guard, key, task_id, expected_hash, before, after, be, ae, now_ns=time.time_ns())
    return ScopedOutcome(status, result)
