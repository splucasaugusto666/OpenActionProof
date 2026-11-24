"""Offline example: no secrets are logged or persisted."""
import secrets
from openactionproof.http_lab import CASES, execute
from openactionproof.attestation import Intent, ReplayGuard, seal

key = secrets.token_bytes(32)
intent = Intent("normal", "local-observer", secrets.token_hex(32))
receipt = execute(CASES[0])
envelope = seal(key, intent, receipt)
guard = ReplayGuard()
assert guard.accept(key, intent, envelope)
assert not guard.accept(key, intent, envelope)
print("Authenticated local receipt accepted once; replay rejected.")
