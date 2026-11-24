"""Read-only reconciliation of a dispatch claim, not permission to retry."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
import secrets
import time

from .core import canonical, sha256
from .durable_replay import DurableReplayGuard
from .observer import ObservationRequest
from .observer_worker import read_authenticated
from .tool_dispatch import DispatchLedger, DispatchRecord
from .verified_observation import authenticate

TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
KNOWN = ("PENDING_RECONCILIATION", "UNRESOLVED", "OUTCOME_RECORDED")


@dataclass(frozen=True)
class Reconciliation:
    historical: DispatchRecord
    current: str
    observed_ns: int | None = None
    revision: int | None = None


def reconcile_write(*, ledger: DispatchLedger, guard: DurableReplayGuard, database: Path,
                    key: bytes, scope: str, call_id: str, observer_id: str,
                    resource: str, expected_value: str, timeout: float = 5.0) -> Reconciliation:
    """Check current state with a fresh challenge bound to the original claim.

    Never dispatch an actor, update the historical journal or authorize retry.
    Matching current state is not proof of historical execution or absent side effects.
    """
    if (not all(isinstance(v, str) and TOKEN.fullmatch(v) for v in (scope, call_id, observer_id, resource))
            or not isinstance(expected_value, str) or not isinstance(key, bytes) or not 32 <= len(key) <= 128
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0.1 <= timeout <= 30):
        raise ValueError("invalid reconciliation configuration")
    digest = sha256(canonical({"name": "write_resource", "arguments": {"resource": resource, "value": expected_value}}))
    historical = ledger.lookup(scope, call_id, expected_digest=digest)
    if historical.status not in KNOWN:
        return Reconciliation(historical, "NOT_OBSERVED")
    task_id = sha256(canonical({"domain": "openactionproof.reconciliation.v1", "scope": scope, "call_id": call_id, "digest": digest}))
    expected = sha256(canonical(expected_value))
    start = time.time_ns()
    req = ObservationRequest(observer_id, resource, secrets.token_hex(32), start, start + int(timeout * 1_000_000_000))
    envelope = read_authenticated(database, key, task_id, expected, req, timeout=timeout)
    obs = authenticate(key, task_id, expected, req, envelope, now_ns=time.time_ns())
    if obs is None or not guard._consume_tokens(((observer_id, req.challenge),)):
        return Reconciliation(historical, "INDETERMINATE")
    historical = ledger.lookup(scope, call_id, expected_digest=digest)
    if historical.status not in KNOWN:
        return Reconciliation(historical, "INDETERMINATE")
    current = "CURRENT_STATE_MATCHES_UNATTRIBUTED" if obs.state_sha256 == expected else "CURRENT_STATE_DIFFERS"
    return Reconciliation(historical, current, obs.observed_ns, obs.revision)
