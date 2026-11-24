# Durable tool dispatch (experimental)

The dispatch adapter accepts a Chat Completions-shaped offline function call, but does not require or integrate a live model SDK. The trusted host pins a scope, target resource and expected value before accepting tool calls. Only the function name write_resource and exact resource/value JSON fields are accepted. Unknown fields, duplicate JSON keys, invalid types, oversized arguments and out-of-intent operations are rejected before claiming an invocation.

A dedicated SQLite ledger records (scope, call_id, digest) using BEGIN IMMEDIATE and a unique primary key. Only a newly committed claim may invoke the trusted verifier callback. Duplicate calls with the same ID and digest are blocked; reusing an ID for a different digest is a conflict. The host chooses a stable scope and must preserve the invocation ID across retries. New IDs or new scopes can legitimately dispatch again; this does not prevent semantic duplicates with different IDs.

The adapter prioritizes avoiding duplicate execution over automatic recovery. A crash after the claim but before/during the tool operation leaves uncertainty; do not blindly retry using a fresh ID. Reconcile authoritative application state and use business-level idempotency. A CLAIMED status means dispatch authorization was consumed, not that the tool succeeded. CLAIMED_UNRESOLVED and ALREADY_CLAIMED do not assert success or failure. The original claim-only ledger did not persist tool results. The recovery extension below persists a bounded outcome summary; it still does not guarantee exactly-once side effects. Storage is trusted and local; no rollback resistance, automatic expiry, storage quota, distributed guarantees, or hardened actor isolation. Use a dedicated directory and plan retention conservatively; deletion/rollback can invalidate protection. Hashes can reveal low-entropy values to a party with database access.

The verifier callback and writer are trusted code and must match the pinned intent. Use verify_tool_call to collect authenticated before/after observations. No hosted model was used in the tests. These are application-level safeguards, not an unrestricted security boundary.

## Local evidence

Python 3.13.5: 71 tests passed in 19.647 seconds, including 9 dispatch tests. 16 concurrent identical calls: 1 claim and 15 duplicate rejections. An end-to-end test verified a SQLite write and observed revision=1 after repeating the same call. The previous 16-case observation corpus was re-run, with 16/16 labels matched. No independent competitor or live-agent evaluation.

Reproduce: PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -q

Next: live framework adapter with pinned dependencies, durable intent issuance and recovery protocol, capacity/retention policy, independent security review, external comparison, packaging and release validation.


## Durable recovery journal (proposed extension)

The ledger now records an immutable outcome summary after dispatch, bound to the original scope, call ID and digest. Use `ledger.lookup(scope, call_id)` to distinguish:

- `NOT_FOUND`: no record in this local ledger.
- `PENDING_RECONCILIATION`: dispatch claim exists, but no outcome was committed. The actor may still be running, may not have started, or may have produced side effects.
- `UNRESOLVED`: verifier failed or returned an invalid result.
- `OUTCOME_RECORDED`: a trusted verifier's actor status and state verdict were recorded. A verdict of INDETERMINATE remains uncertain; a matching state does not prove causality.
- `STORAGE_UNAVAILABLE`: schema or storage is unavailable; fail closed.
- `INVALID_CALL`: invalid lookup identifiers.

A repeated call with the same digest remains ALREADY_CLAIMED and may return its previously stored outcome, which is a historical observation, not a fresh observation or permission to run the tool again. A failed outcome write returns CLAIMED_UNRESOLVED, even if the actor produced effects. The original claim is never deliberately erased. The journal stores only enumerated summaries, not authenticated receipts, raw payloads, credentials, or exception messages. Trusted callers and storage remain prerequisites. A direct trusted caller can record summaries; they are not public attestations.

### Migration

New databases use schema version 1. For an existing dedicated legacy dispatch database, stop all writers, retain a secure backup for investigation, and explicitly run `DispatchLedger(path, upgrade=True)` once. Do not restore old snapshots into an active system. Existing claims become pending reconciliation; no outcomes are fabricated. Missing tables or unsupported versions fail closed rather than silently recreating storage. Do not use a legacy version of the adapter against upgraded storage. This schema is intended only for the dedicated dispatch ledger.

### Evidence

Local Python 3.13.5: 81 tests passed in 19.899 seconds; 10 new recovery tests passed. A real subprocess exited immediately after committing the claim; reopening preserved the claim without permitting duplicate invocation. Tests also cover concurrent write-once outcome recording (16 attempts, one accepted), explicit migration, missing schema, simulated outcome write failure after an effect, invalid outcomes and duplicate retrieval. The observation corpus remained 16/16. CI for this proposal is pending. No physical power-loss, distributed storage, independent security certification, live model SDK, or automatic reconciliation protocol has been demonstrated.
