# OpenActionProof (Project Genesis X) — research prototype v0.4

> **Did the AI agent actually do what it claimed?** An offline, vendor-neutral outcome-verification experiment and seed for an adversarial conformance lab.

[Status: Proof of Concept] This is **not** a production security system, an authenticated attestation service, or proof that any third-party agent acted.

## Install & try locally

Requires Python 3.10+. **No API keys, model account, network, or pip dependencies.**

```bash
PYTHONPATH=src python -m openactionproof demo --output evidence/generated
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m openactionproof verify-receipt evidence/generated/A_confirmed.json
```

On Windows PowerShell, set `$env:PYTHONPATH="src"` before invoking Python, or install with `python -m pip install -e .` then use `oap demo`.

Expected verdicts:

| Scenario | Agent claim | Independent observed state | Verdict |
|---|---|---|---|
| A: controlled successful write | success | expected content SHA-256 | `CONFIRMED` |
| B: claim-only / no effect | success | file missing | `FALSE_SUCCESS` |
| C: partial write + synthetic timeout | unknown | partial file SHA-256 | `INDETERMINATE` |

The command writes JSON evidence receipts in the requested output directory, then checksum-checks their serialization. Operations happen in a fresh local temporary workspace.

## Positioning and prior work

This field has direct competitors: AgentVerify already checks outcomes with signed receipts; Inspect AI supports custom state scorers; Internet-Drafts propose receipt formats. This project will explore **adversarial conformance testing of verifiers** rather than claim to invent receipts. See `research/landscape.md`.

## Architecture

```
predeclared expected outcome + task identifier
                  |
          trusted local action
                  |
       independent file snapshot
                  |
          verifier verdict
                  |
      canonical JSON + SHA-256
```

* `ActionSpec` pins the desired file bytes before the action.
* `verify_action` observes the filesystem after the operation and never uses the agent's claim as a success oracle.
* `INDETERMINATE` is conservatively returned on timeout/error, even if the file is present.
* `STATE_SATISFIED_UNATTRIBUTED` is returned when the target state already existed; final-state satisfaction is not proof that the agent acted.
* Receipts include hashes and sizes, **not private file content**, and a checksum that detects accidental edits if checked against a trusted copy.

### Threat model and limitations

- Demo actions are local Python callbacks, **not actual LLM agents**. This verifies a mechanism, not real deployment integration.
- The filesystem observer is in the same local trust domain as the operation. A compromised actor can modify both data and receipt; SHA-256 **does not authenticate the author**.
- Receipt checksum verification does **not** re-check the filesystem or independently validate a claimed action. Third-party attestations, signatures and independent witnesses are out of scope.
- Timeout means incomplete knowledge, not confirmed failure or success. It does not guarantee safe retry or prevent duplicate side effects.
- Path checks reject traversal/symlinks in simple local cases; not robust against hostile concurrent filesystem swaps, hard links or races. Do not run with untrusted callbacks.
- No real GitHub, HTTP, cloud, database or model adapter in v0.1. No durability guarantee across crashes.
- Synthetic cases are construction tests, **not evidence of production accuracy or superiority**.

See `docs/DECISIONS.md`, `docs/EXPERIMENTS.md`, `docs/NEXT_ACTIONS.md`, and `research/landscape.md`.

## Contributing

Start with a reproducible failure case or evidence contract, add a regression test, and open an issue or PR. See CONTRIBUTING.md. Project is licensed under Apache-2.0.

## HTTP conformance lab (v0.2)

Run `PYTHONPATH=src python -m openactionproof.http_lab --output evidence/generated/http-benchmark.json` to execute 14 controlled fixtures, compare two naive baselines, and produce checksummed evidence. See `benchmarks/METHODOLOGY.md`. Synthetic results do not establish real-agent reliability.


## Authenticated evidence (v0.3)

The `attestation` module validates HTTP receipts, binds a task, observer and one-time challenge to an HMAC-SHA256 envelope, and rejects repeated challenges via a bounded process-local guard. This authenticates to a trusted shared-key holder; it is not a public signature, remote attestation, or proof of observer independence. See `docs/EVIDENCE_PROTOCOL.md`.


### Transport failure tests (v0.4)

The lab now includes a real socket read timeout after a controlled commit and an actual HTTP 503 from the observer. These are loopback experiments only, not a distributed durability guarantee.
