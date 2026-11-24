"""Caller-pinned authenticated observation pairs with atomic replay consumption.

The observer must obtain its own fresh observations. HMAC does not establish
public provenance, actor attribution, privilege isolation or storage integrity.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import hmac
import re

from .core import canonical
from .durable_replay import DurableReplayGuard
from .observer import Observation, ObservationRequest, Observer, assess, validate

SCHEMA = "openactionproof.observation.hmac.v1"
TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")


def _matches(pattern, value) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _mac(key: bytes, body: dict) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("shared key must contain at least 32 bytes")
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


def _body(task_id: str, expected: str, request: ObservationRequest, obs: Observation) -> dict:
    if not _matches(TOKEN, task_id) or not _matches(HEX, expected):
        raise ValueError("invalid task or expected digest")
    return {"schema": SCHEMA, "task_id": task_id, "expected_sha256": expected,
            "request": asdict(request), "observation": asdict(obs)}


def observe_authenticated(observer: Observer, key: bytes, task_id: str, expected: str,
                          request: ObservationRequest) -> dict:
    """Trusted observer-side function; do not expose an arbitrary signing oracle."""
    obs = observer.observe(request)
    if not isinstance(obs, Observation) or not validate(request, obs, obs.observed_ns):
        raise ValueError("invalid observation")
    body = _body(task_id, expected, request, obs)
    return {**body, "mac": _mac(key, body)}


def authenticate(key: bytes, task_id: str, expected: str, request: ObservationRequest,
                 envelope, *, now_ns: int) -> Observation | None:
    try:
        if not isinstance(envelope, dict) or set(envelope) != {"schema", "task_id", "expected_sha256", "request", "observation", "mac"}:
            return None
        if envelope["schema"] != SCHEMA or not _matches(HEX, envelope["mac"]):
            return None
        obs = Observation(**envelope["observation"])
        if not validate(request, obs, now_ns):
            return None
        body = _body(task_id, expected, request, obs)
        if any(envelope[k] != v for k, v in body.items()):
            return None
        # Verify canonical bytes as supplied, not only Python equality (True == 1).
        provided = {k: v for k, v in envelope.items() if k != "mac"}
        if canonical(provided) != canonical(body):
            return None
        return obs if hmac.compare_digest(_mac(key, body), envelope["mac"]) else None
    except (TypeError, KeyError, ValueError, OverflowError, RecursionError):
        return None


def assess_authenticated_pair(guard: DurableReplayGuard, key: bytes, task_id: str,
                              expected: str, before_request: ObservationRequest,
                              after_request: ObservationRequest, before_envelope,
                              after_envelope, *, now_ns: int) -> str:
    """Return a verdict only after both authenticated tokens commit atomically."""
    if type(now_ns) is not int:
        return "INDETERMINATE"
    before = authenticate(key, task_id, expected, before_request, before_envelope,
                          now_ns=min(now_ns, before_request.deadline_ns))
    after = authenticate(key, task_id, expected, after_request, after_envelope, now_ns=now_ns)
    result = assess(before_request, after_request, before, after, expected, now_ns=now_ns)
    if result == "INDETERMINATE":
        return result
    tokens = ((before_request.observer_id, before_request.challenge),
              (after_request.observer_id, after_request.challenge))
    return result if guard._consume_tokens(tokens) else "INDETERMINATE"
