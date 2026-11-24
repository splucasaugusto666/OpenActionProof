"""Authenticated lab receipts with a caller-pinned intent and one-time challenge.

HMAC authenticates to holders of a shared secret, not to the public. A trusted
observer and secure key distribution are required. This is not remote attestation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re
import threading

from .core import canonical
from .http_lab import check_receipt, verdict

SCHEMA = "openactionproof.hmac-envelope.v0.1"
MAX_BYTES = 65536
TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
NONCE = re.compile(r"[a-f0-9]{64}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")


def valid_token(value) -> bool:
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def counter(value) -> bool:
    return type(value) is int and 0 <= value <= 1000000


def snapshot_valid(value) -> bool:
    if not isinstance(value, dict) or set(value) != {"counts", "events", "pending"}:
        return False
    counts, events = value["counts"], value["events"]
    if not isinstance(counts, dict) or set(counts) != {"target", "other"}:
        return False
    if not all(counter(n) for n in counts.values()) or not counter(value["pending"]):
        return False
    if not isinstance(events, list) or len(events) > 1000:
        return False
    for event in events:
        if not isinstance(event, dict) or set(event) != {"resource", "key"}:
            return False
        if event["resource"] not in ("target", "other") or not valid_token(event["key"]):
            return False
    return len({event["key"] for event in events}) == len(events)


def consistent_transition(before: dict, after: dict) -> bool:
    old = before["events"]
    new = after["events"]
    if new[:len(old)] != old:
        return False
    added = new[len(old):]
    return all(after["counts"][r] - before["counts"][r] == sum(e["resource"] == r for e in added)
               for r in ("target", "other"))


def validate_lab_receipt(receipt, task_id: str) -> bool:
    try:
        if not isinstance(receipt, dict) or len(canonical(receipt)) > MAX_BYTES:
            return False
        if set(receipt) != {"schema", "case", "expected_state", "before", "attempts", "agent_claim", "after", "verdict", "fixture_label", "receipt_sha256"}:
            return False
        if receipt["case"] != task_id or receipt["expected_state"] != {"target": 1, "other": 0}:
            return False
        if any(type(v) is not int for v in receipt["expected_state"].values()):
            return False
        claim, before, after = receipt["agent_claim"], receipt["before"], receipt["after"]
        if claim is not None and type(claim) is not bool:
            return False
        if not snapshot_valid(before) or (after is not None and not snapshot_valid(after)):
            return False
        if after is not None and not consistent_transition(before, after):
            return False
        attempts = receipt["attempts"]
        if not isinstance(attempts, list) or not 1 <= len(attempts) <= 1000:
            return False
        for attempt in attempts:
            if not isinstance(attempt, dict) or set(attempt) != {"mode", "resource", "key", "status"}:
                return False
            if not valid_token(attempt["mode"]) or attempt["resource"] not in ("target", "other") or not valid_token(attempt["key"]):
                return False
            s = attempt["status"]
            if s is not None and (type(s) is not int or not 100 <= s <= 599):
                return False
        if after is not None:
            known = {(a["resource"], a["key"]) for a in attempts}
            if any((e["resource"], e["key"]) not in known for e in after["events"][len(before["events"]):]):
                return False
        return check_receipt(receipt) and receipt["verdict"] == verdict(before, after, claim)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return False


@dataclass(frozen=True)
class Intent:
    task_id: str
    observer_id: str
    challenge: str

    def valid(self) -> bool:
        return valid_token(self.task_id) and valid_token(self.observer_id) and isinstance(self.challenge, str) and NONCE.fullmatch(self.challenge) is not None

    def body(self) -> dict:
        return {"task_id": self.task_id, "observer_id": self.observer_id, "challenge": self.challenge}


def _mac(key: bytes, body: dict) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Use a securely generated shared secret of at least 32 bytes")
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


def seal(key: bytes, intent: Intent, receipt: dict) -> dict:
    if not intent.valid() or not validate_lab_receipt(receipt, intent.task_id):
        raise ValueError("Invalid intent or receipt")
    body = {"schema": SCHEMA, **intent.body(), "receipt": receipt}
    # Return a detached copy so caller mutation cannot silently alter signed contents.
    import json
    body = json.loads(canonical(body))
    return {**body, "mac": _mac(key, body)}


def verify(key: bytes, intent: Intent, envelope) -> bool:
    try:
        if not intent.valid() or not isinstance(envelope, dict):
            return False
        if set(envelope) != {"schema", "task_id", "observer_id", "challenge", "receipt", "mac"}:
            return False
        if envelope["schema"] != SCHEMA or any(envelope[k] != v for k, v in intent.body().items()):
            return False
        if not isinstance(envelope["mac"], str) or HEX.fullmatch(envelope["mac"]) is None:
            return False
        body = {k: v for k, v in envelope.items() if k != "mac"}
        if len(canonical(body)) > MAX_BYTES:
            return False
        if not hmac.compare_digest(_mac(key, body), envelope["mac"]):
            return False
        return validate_lab_receipt(envelope["receipt"], intent.task_id)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return False


class ReplayGuard:
    """Bounded, thread-safe, process-local consumption; not durable across restart."""
    def __init__(self, capacity: int = 10000):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._used: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def accept(self, key: bytes, intent: Intent, envelope) -> bool:
        if not verify(key, intent, envelope):
            return False
        token = (intent.observer_id, intent.challenge)
        with self._lock:
            if token in self._used or len(self._used) >= self._capacity:
                return False
            self._used.add(token)
            return True
