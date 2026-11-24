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

## Release validation incident

The initial publication workflow (run 45311225714) correctly withheld publication: Windows full-suite execution reported WinError 10053 when POST /settle closed the connection. The endpoint had not consumed the request body before replying. The proposed correction consumes and validates request bodies, rejects malformed operations without mutation, and adds two regression tests. Local Linux Python 3.13.5: 116/116 tests passed in two groups (76 in 10.138 s, 40 in 16.473 s). Windows confirmation is required before publication; root cause remains a hypothesis until the remote validation succeeds. The source/test blobs match the locally tested files. Full installed-package tests are now also configured in the pull-request OS matrix. The original failed run is preserved.
