# OpenActionProof 0.9.0rc2 — Research preview

This candidate provides caller-pinned outcome verification, durable duplicate prevention, authenticated reconciliation, scoped SQLite state verification, optional Ed25519 public-key evidence and a controlled Inspect AI integration.

Install the attached wheel with Python 3.10 or newer:

```sh
python -m pip install open_action_proof-0.9.0rc2-py3-none-any.whl
python -m openactionproof demo
```

Optional signature verification: install the wheel with its public-evidence extra. Check the attached SHA256SUMS.txt before installation. The core has no mandatory third-party runtime dependencies.

Previous PR #15 passed eight remote checks. This release workflow independently requires the installed-wheel smoke test and full unit suite across supported Python/OS combinations, including optional Ed25519 and a controlled Inspect AI evaluation, before publishing the preview.

This is not v1.0.0 or a production security claim. Independent evaluation, comparative benchmarking, security review and observer/key lifecycle improvements remain open. A valid signature does not establish observer honesty, causal execution or whole-system side-effect absence. See docs/RELEASE_GATES.md.
