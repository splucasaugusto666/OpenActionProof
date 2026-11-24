"""Reference observation contract; freshness checks do not authenticate an observer.

Separate processes are an architectural boundary, not an OS security boundary.
The relying party must trust the observer transport and pin its configuration.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
import json
import re
import sqlite3
from contextlib import closing
import sys
import time

from .core import canonical, sha256

TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")


def _match(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


@dataclass(frozen=True)
class ObservationRequest:
    observer_id: str
    resource: str
    challenge: str
    not_before_ns: int
    deadline_ns: int

    def valid(self) -> bool:
        return (_match(TOKEN, self.observer_id) and _match(TOKEN, self.resource)
                and _match(HEX, self.challenge) and type(self.not_before_ns) is int
                and type(self.deadline_ns) is int and 0 <= self.not_before_ns <= self.deadline_ns)


@dataclass(frozen=True)
class Observation:
    observer_id: str
    resource: str
    challenge: str
    observed_ns: int
    revision: int
    state_sha256: str


class Observer(Protocol):
    def observe(self, request: ObservationRequest) -> Observation: ...


def validate(request: ObservationRequest, obs: Observation | None, now_ns: int) -> bool:
    if not request.valid() or not isinstance(obs, Observation) or type(now_ns) is not int:
        return False
    return (obs.observer_id == request.observer_id and obs.resource == request.resource
            and obs.challenge == request.challenge and type(obs.observed_ns) is int
            and request.not_before_ns <= obs.observed_ns <= min(request.deadline_ns, now_ns)
            and now_ns <= request.deadline_ns and type(obs.revision) is int and obs.revision >= 0
            and _match(HEX, obs.state_sha256))


def assess(before_request: ObservationRequest, after_request: ObservationRequest,
           before: Observation | None, after: Observation | None,
           expected_sha256: str, *, now_ns: int) -> str:
    """Compare trusted snapshots; never infer actor attribution from matching state."""
    if not (_match(HEX, expected_sha256) and before_request.valid() and after_request.valid()
            and before_request.observer_id == after_request.observer_id
            and before_request.resource == after_request.resource
            and before_request.challenge != after_request.challenge
            and before_request.deadline_ns <= after_request.not_before_ns):
        return "INDETERMINATE"
    # Validate the historical snapshot as of the end of its own observation window.
    if not validate(before_request, before, min(now_ns, before_request.deadline_ns)):
        return "INDETERMINATE"
    if not validate(after_request, after, now_ns):
        return "INDETERMINATE"
    if after.revision < before.revision or after.observed_ns < before.observed_ns:
        return "INDETERMINATE"
    if after.revision == before.revision and after.state_sha256 != before.state_sha256:
        return "INDETERMINATE"
    if after.state_sha256 != expected_sha256:
        return "STATE_MISMATCH"
    if before.state_sha256 == expected_sha256:
        return "STATE_PREEXISTING"
    return "STATE_MATCHED_UNATTRIBUTED"


class SQLiteObserver:
    """Read trusted local resource_state(resource, revision, value) in read-only mode."""
    def __init__(self, path: Path, observer_id: str):
        self.path = Path(path).absolute()
        self.observer_id = observer_id

    def observe(self, request: ObservationRequest) -> Observation:
        if not request.valid() or request.observer_id != self.observer_id:
            raise ValueError("invalid observation request")
        started = time.time_ns()
        if not request.not_before_ns <= started <= request.deadline_ns:
            raise ValueError("observation window unavailable")
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=2)) as conn:
            row = conn.execute("SELECT revision, value FROM resource_state WHERE resource=?", (request.resource,)).fetchone()
        if row is None or type(row[0]) is not int or row[0] < 0 or not isinstance(row[1], str):
            raise ValueError("resource not observable")
        finished = time.time_ns()
        if finished < started or finished > request.deadline_ns:
            raise ValueError("observation deadline exceeded")
        return Observation(self.observer_id, request.resource, request.challenge,
                           finished, row[0], sha256(canonical(row[1])))


def main():
    # Trusted caller passes fixed database/observer configuration, request over stdin.
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m openactionproof.observer DB OBSERVER_ID")
    request = ObservationRequest(**json.load(sys.stdin))
    result = SQLiteObserver(Path(sys.argv[1]), sys.argv[2]).observe(request)
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == "__main__":
    main()
