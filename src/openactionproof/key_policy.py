"""Caller-pinned Ed25519 authorization snapshot; no PKI or rollback protection."""
from __future__ import annotations

from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .observer import ObservationRequest
from .public_observation import TOKEN, key_id, assess_signed_pair
from .durable_replay import DurableReplayGuard


@dataclass(frozen=True)
class KeyGrant:
    observer_id: str
    public_key: Ed25519PublicKey
    valid_from_ns: int
    valid_until_ns: int
    revoked: bool = False

    def __post_init__(self):
        if (not isinstance(self.observer_id, str) or not TOKEN.fullmatch(self.observer_id)
                or not isinstance(self.public_key, Ed25519PublicKey)
                or type(self.valid_from_ns) is not int or type(self.valid_until_ns) is not int
                or not 0 <= self.valid_from_ns < self.valid_until_ns
                or type(self.revoked) is not bool):
            raise ValueError("invalid observer key grant")


@dataclass(frozen=True)
class KeyPolicy:
    """Trusted, current configuration; callers must prevent stale-policy use."""
    grants: tuple[KeyGrant, ...]

    def __post_init__(self):
        if (type(self.grants) is not tuple or len(self.grants) > 256
                or any(not isinstance(g, KeyGrant) for g in self.grants)):
            raise ValueError("invalid key policy")
        ids = [key_id(g.public_key) for g in self.grants]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate public key grant")

    def select(self, before: ObservationRequest, after: ObservationRequest,
               before_envelope, after_envelope, *, now_ns: int) -> Ed25519PublicKey | None:
        if (type(now_ns) is not int or not isinstance(before, ObservationRequest)
                or not isinstance(after, ObservationRequest) or not before.valid() or not after.valid()
                or before.observer_id != after.observer_id
                or not isinstance(before_envelope, dict) or not isinstance(after_envelope, dict)):
            return None
        fingerprint = before_envelope.get("key_id")
        if not isinstance(fingerprint, str) or fingerprint != after_envelope.get("key_id"):
            return None
        for grant in self.grants:
            if (not grant.revoked and grant.observer_id == before.observer_id
                    and fingerprint == key_id(grant.public_key)
                    and grant.valid_from_ns <= before.not_before_ns <= before.deadline_ns
                    <= after.not_before_ns <= after.deadline_ns < grant.valid_until_ns
                    and grant.valid_from_ns <= now_ns < grant.valid_until_ns):
                return grant.public_key
        return None


def assess_authorized_pair(guard: DurableReplayGuard, policy: KeyPolicy, task_id: str,
                           expected: str, before: ObservationRequest, after: ObservationRequest,
                           before_envelope, after_envelope, *, now_ns: int) -> str:
    """Apply current key authorization before authenticating/consuming challenges.

    Both request windows and verification time must be covered by one grant.
    Revocation denies even older unconsumed signatures. Rotation requires a new
    pair, not mixing keys in a pair. A stale policy is outside this contract.
    """
    if not isinstance(policy, KeyPolicy):
        return "INDETERMINATE"
    key = policy.select(before, after, before_envelope, after_envelope, now_ns=now_ns)
    if key is None:
        return "INDETERMINATE"
    return assess_signed_pair(guard, key, task_id, expected, before, after,
                              before_envelope, after_envelope, now_ns=now_ns)
