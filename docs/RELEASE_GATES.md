# Release gates — current research preview

- Local construction suite: 83/83 tests passed in Python 3.13.5; two additional portable-path and exception-redaction regression tests.
- Prior PR #10: merged after Python 3.10, 3.12 and 3.13 GitHub Actions jobs passed.
- Local wheel 0.9.0rc1: built and installed in a clean Linux virtual environment with no runtime dependencies. Installed smoke test passed 3 file cases, 14 HTTP cases and 16 observation cases. The local wheel is a development build, not a published release or byte-identical remote CI artifact.
- Cross-platform installed wheel checks: configured for Ubuntu, Windows and macOS; results pending.
- Optional Inspect AI integration: configured with a pinned framework dependency and three controlled fixtures; framework unavailable locally, execution pending in CI. Not a live-agent evaluation.
- Held-out corpus, independent baseline comparison, and external replication: pending.
- Stronger observer isolation, independent threat-model review, secret lifecycle and reconciliation protocol: pending.
- Release package provenance review and tagged version: pending.

Do not merge the proposed PR while any required workflow is unconfirmed. This is not production-ready, independently validated, a Guinness record or evidence of superiority to competing tools.
