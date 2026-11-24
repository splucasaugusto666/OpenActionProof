# Architecture decisions

- 2026-11-23: Prefer an adversarial conformance lab to another generic tracing dashboard.
- Local Python standard library keeps the baseline reproducible without credentials or paid APIs.
- The action's predeclared expected state, before snapshot, callback execution, final snapshot, and agent claim are distinct.
- An observed matching final state does not prove causal attribution when the state pre-existed; use STATE_SATISFIED_UNATTRIBUTED.
- Timeout/error is INDETERMINATE, even when final bytes match; this is conservative, not a distributed transaction guarantee.
- Canonical JSON SHA-256 is a self-checksum, not a digital signature or independently witnessed proof.
- All result labels refer only to a controlled local experiment until third-party reproducibility is established.
