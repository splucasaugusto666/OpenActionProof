# Product Requirements Document (v0.1)

Problem: agents may claim an action succeeded without a corresponding persistent result. Tool-call observability alone is insufficient for an outcome guarantee.

Audience: maintainers of agent applications, evaluations, reliability/security tooling.

MVP scope: local controlled file-write actions, before/after snapshots, predeclared expected SHA-256, verdict labels, self-checksum receipt, three demos, unit tests, no paid services.

Non-goals: production-grade security, independent custody, transaction rollback, universal agent integration, cryptographic signatures.

Acceptance: each documented demo has an expected verdict; local tests pass with Python 3.10+; tampering a receipt field invalidates its checksum; path traversal attempts are rejected in static controlled tests.

Next milestone: adversarial mock HTTP conformance suite with authoritative observation and idempotency.
