# Release gates

- Local construction suite: passed (23 unit tests, 14 synthetic HTTP fixture labels at v0.4).
- Published source: versioned in GitHub; remote CI and cross-platform results not yet confirmed.
- Held-out benchmark with independent baselines: pending.
- Independent observer boundary and threat-model review: pending.
- Integration example using a real agent framework: pending.
- Release package, dependency and provenance review: pending.
- External replication: pending.

A research MVP is not a production-ready or independently validated system. Do not claim record eligibility, universal accuracy, or industry superiority.

Proposed v0.5 PR: 30/30 local unit tests passed; durable replay is implemented for trusted local SQLite storage. Remote CI, integration and independent validation gates remain open. Do not merge while required CI is unverified.
