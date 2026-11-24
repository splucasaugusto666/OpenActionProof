# Architecture decisions

- 2026-11-23: Prioritize adversarial verifier conformance, not tracing dashboards.
- Python standard library keeps local experiments reproducible without paid APIs.
- File actions distinguish before/after observation, expected state, and claims; preexisting state is unattributed and timeouts are indeterminate.
- HTTP lab may reconcile a lost acknowledgment using a trusted authoritative service ledger. This is different from attributing a filesystem write without a transaction log.
- Self-checksums are not signatures or provenance.
- The fixture oracle is predeclared but in-sample; external validation remains necessary.

- Shared-key HMAC is an optional lab authentication experiment. The relying party supplies the task/observer/challenge and trusted key; the observer must sign only its own trusted observations. A verifier with the same key can forge evidence. No public nonrepudiation.

- Elapsed read timeout is separately tested from connection loss. An observer HTTP non-200 yields no usable observation, therefore INDETERMINATE. Confirmation after timeout depends on the controlled service's authoritative event ledger.

- Use explicit one-time SQLite provisioning, `BEGIN IMMEDIATE`, unique observer/challenge keys and `synchronous=FULL` for local durable replay consumption. Reopening cannot silently recreate missing storage. Do not claim exactly-once execution: only one-time acceptance of an authenticated challenge, contingent on trusted non-rollback storage.
