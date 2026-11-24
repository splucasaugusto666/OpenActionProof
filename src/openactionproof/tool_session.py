"""Small synchronous integration API for trusted tool adapters (not an agent sandbox)."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
import secrets
import time
from typing import Callable

from .core import canonical, sha256
from .durable_replay import DurableReplayGuard
from .observer import ObservationRequest
from .observer_worker import read_authenticated
from .verified_observation import assess_authenticated_pair


@dataclass(frozen=True)
class ToolOutcome:
    actor_status: str
    verdict: str


def verify_tool_call(*, database: Path, guard: DurableReplayGuard, key: bytes,
                     task_id: str, observer_id: str, resource: str, expected_value: str,
                     actor: Callable[[], object], window_seconds: float = 1.0) -> ToolOutcome:
    """Observe, invoke a trusted synchronous tool, and assess fresh state independently.

    A matching state is not actor attribution. Actor exceptions do not imply no effect.
    No actor timeout or privilege isolation is provided; the actor must be trusted.
    The expected state and observer configuration must come from the relying party.
    """
    if (not callable(actor) or not isinstance(expected_value, str)
            or not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", task_id)
            or not isinstance(key, bytes) or not 32 <= len(key) <= 128
            or type(window_seconds) not in (int, float) or not math.isfinite(window_seconds)
            or not 0.1 <= window_seconds <= 30):
        raise ValueError("invalid trusted integration configuration")
    expected = sha256(canonical(expected_value))
    duration = int(window_seconds * 1_000_000_000)
    def request():
        start = time.time_ns()
        return ObservationRequest(observer_id, resource, secrets.token_hex(32), start, start + duration)
    before = request()
    if not before.valid():
        raise ValueError("invalid observer or resource")
    be = read_authenticated(database, key, task_id, expected, before, timeout=window_seconds)
    if be is None:
        return ToolOutcome("NOT_INVOKED", "INDETERMINATE")
    try:
        actor()
        status = "RETURNED"
    except Exception:
        # Do not retain exception details, tool payloads, or credentials.
        status = "RAISED"
    remaining = (before.deadline_ns - time.time_ns()) / 1_000_000_000
    if remaining > 0:
        if remaining > window_seconds:
            return ToolOutcome(status, "INDETERMINATE")
        time.sleep(remaining)
    after = request()
    if after.not_before_ns < before.deadline_ns:
        return ToolOutcome(status, "INDETERMINATE")
    ae = read_authenticated(database, key, task_id, expected, after, timeout=window_seconds)
    verdict = assess_authenticated_pair(guard, key, task_id, expected, before, after, be, ae, now_ns=time.time_ns())
    return ToolOutcome(status, verdict)
