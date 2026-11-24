# Reference observer contract (proposed v0.6)

An observation request pins observer ID, resource, unique random 256-bit challenge, and an explicit observation window. A response carries the same binding, observation time, monotonic resource revision and a canonical state hash.

The trusted caller issues non-overlapping before/after windows and pins the expected state hash independently of the actor. The assessor rejects missing, expired, future-dated, misbound, reused-challenge or inconsistent-revision observations. It distinguishes STATE_MATCHED_UNATTRIBUTED, STATE_PREEXISTING, STATE_MISMATCH and INDETERMINATE. Matching state never proves that the intended actor caused the change.

SQLiteObserver provides a read-only reference adapter. A local test uses two separate observer subprocesses and an actor subprocess, verifying revision and content hash before and after the actor writes. This is process separation only, not privilege isolation: trust in the caller, interpreter, database, OS, observer transport, and clock is required. A malicious actor with the same filesystem privileges can corrupt the database or impersonate the observer. Timestamps are wall-clock observations, not proof of state freshness in a replicated store. Revision rollback protection is limited to the two snapshots. HMAC attestation and durable replay guard remain separate modules; their integration with a generalized observer contract is pending.

Run: PYTHONPATH=src python -m unittest discover -s tests -v

Local results, 2026-11-23: 39 tests passed, including nine new observer tests. External CI and review pending. No production-readiness, independent security certification or comparison to competing verifiers is claimed.

## Authenticated pair extension

The verifier pins task ID and expected digest before requesting before/after observations. The trusted observer-side wrapper reads the observation itself and HMAC-authenticates the request and returned state, using a domain-specific schema. Both observations must match their respective windows and independent caller expectations. The relying party verifies both envelopes and compares the states, then consumes the two observer/challenge tokens atomically in existing SQLite storage. Duplicate tokens, exhausted capacity and storage errors return INDETERMINATE; no partial consumption. A valid mismatch consumes both tokens too. Shared keys must be protected and uniquely assigned according to a trusted configuration; HMAC holders can forge envelopes, and an authenticated observer can misrepresent its own observations. This extension does not implement privilege separation, public signatures, freshness against replicated stores, durable challenge issuance, or attribution to an actor. The private token-consumption method is not an untrusted API. Local tests use fixture observers, and the previous reference adapter tests use real SQLite subprocesses; integrated authenticated subprocess custody remains future work.
