"""Optional Ed25519 observation signatures; trust in the observer remains required."""
from __future__ import annotations

from dataclasses import asdict
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .core import canonical, sha256
from .durable_replay import DurableReplayGuard
from .observer import Observation, ObservationRequest, Observer, assess, validate

SCHEMA = "openactionproof.observation.ed25519.v1"
TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
SIGNATURE = re.compile(r"[a-f0-9]{128}\Z")


def key_id(public_key: Ed25519PublicKey) -> str:
    if not isinstance(public_key, Ed25519PublicKey):
        raise TypeError("Ed25519 public key required")
    return sha256(public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def _body(public_key, task_id, expected, request, observation):
    if not isinstance(task_id, str) or not TOKEN.fullmatch(task_id) or not isinstance(expected, str) or not HEX.fullmatch(expected):
        raise ValueError("invalid task or expected digest")
    return {"schema": SCHEMA, "key_id": key_id(public_key), "task_id": task_id,
            "expected_sha256": expected, "request": asdict(request), "observation": asdict(observation)}


def observe_signed(observer: Observer, private_key: Ed25519PrivateKey, task_id: str,
                   expected: str, request: ObservationRequest) -> dict:
    """Sign the observer's own reading; do not expose an arbitrary signing oracle."""
    if not isinstance(private_key, Ed25519PrivateKey) or not request.valid():
        raise ValueError("invalid signing configuration")
    obs = observer.observe(request)
    if not isinstance(obs, Observation) or not validate(request, obs, obs.observed_ns):
        raise ValueError("invalid observation")
    body = _body(private_key.public_key(), task_id, expected, request, obs)
    return {**body, "signature": private_key.sign(canonical(body)).hex()}


def authenticate_signed(public_key: Ed25519PublicKey, task_id: str, expected: str,
                        request: ObservationRequest, envelope, *, now_ns: int) -> Observation | None:
    """Verify with a caller-pinned key, never a key supplied by the envelope."""
    if not isinstance(request, ObservationRequest) or not request.valid():
        return None
    try:
        if not isinstance(envelope, dict) or set(envelope) != {"schema", "key_id", "task_id", "expected_sha256", "request", "observation", "signature"}:
            return None
        signature = envelope["signature"]
        if not isinstance(signature, str) or not SIGNATURE.fullmatch(signature):
            return None
        obs = Observation(**envelope["observation"])
        if not validate(request, obs, now_ns):
            return None
        body = _body(public_key, task_id, expected, request, obs)
        provided = {k: v for k, v in envelope.items() if k != "signature"}
        if canonical(provided) != canonical(body):
            return None
        public_key.verify(bytes.fromhex(signature), canonical(body))
        return obs
    except (InvalidSignature, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return None


def assess_signed_pair(guard: DurableReplayGuard, public_key: Ed25519PublicKey,
                       task_id: str, expected: str, before_request: ObservationRequest,
                       after_request: ObservationRequest, before_envelope, after_envelope,
                       *, now_ns: int) -> str:
    """Verify a pinned pair and consume both challenges in one transaction.

    Both observations must use the same trusted key. Rotation requires explicit
    caller policy; key changes do not reset observer-scoped replay protection.
    """
    if type(now_ns) is not int or not isinstance(before_request, ObservationRequest) or not isinstance(after_request, ObservationRequest):
        return "INDETERMINATE"
    if not before_request.valid() or not after_request.valid():
        return "INDETERMINATE"
    before = authenticate_signed(public_key, task_id, expected, before_request, before_envelope,
                                 now_ns=min(now_ns, before_request.deadline_ns))
    after = authenticate_signed(public_key, task_id, expected, after_request, after_envelope, now_ns=now_ns)
    result = assess(before_request, after_request, before, after, expected, now_ns=now_ns)
    if result == "INDETERMINATE":
        return result
    tokens = ((before_request.observer_id, before_request.challenge), (after_request.observer_id, after_request.challenge))
    return result if guard._consume_tokens(tokens) else "INDETERMINATE"
