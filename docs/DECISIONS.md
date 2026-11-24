# Architecture decisions

- 2026-11-23: Prioritize adversarial verifier conformance, not tracing dashboards.
- Python standard library keeps local experiments reproducible without paid APIs.
- File actions distinguish before/after observation, expected state, and claims; preexisting state is unattributed and timeouts are indeterminate.
- HTTP lab may reconcile a lost acknowledgment using a trusted authoritative service ledger. This is different from attributing a filesystem write without a transaction log.
- Self-checksums are not signatures or provenance.
- The fixture oracle is predeclared but in-sample; external validation remains necessary.
