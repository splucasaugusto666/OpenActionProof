# OpenActionProof (Project Genesis X) — research preview 0.9.0rc1

> **Did the AI agent actually do what it claimed?** An offline, vendor-neutral outcome-verification experiment and seed for an adversarial conformance lab.

[Status: Proof of Concept] This is **not** a production security system, an authenticated attestation service, or proof that any third-party agent acted.

## Install & try locally

Requires Python 3.10+. **The core runtime has no third-party dependencies or model API requirements.** Build tools may need downloading; the optional Inspect AI example requires its own dependencies.

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
- The original file demo has no external integrations; later modules provide loopback HTTP and local SQLite reference adapters, not production remote integrations. No durability guarantee across crashes.
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


## Durable replay protection (proposed v0.5)

`DurableReplayGuard` uses SQLite to consume authenticated challenges atomically across processes and reopenings. Explicitly provision a database once with `DurableReplayGuard(path, initialize=True)`; reopen with `DurableReplayGuard(path)`. Do not recreate or restore an older database while challenges are valid. Requires trusted local storage with SQLite locking; no distributed guarantee. See `docs/EVIDENCE_PROTOCOL.md`.

## Trusted tool integration (experimental)

Use `openactionproof.tool_session.verify_tool_call` to pin a desired SQLite resource value, observe it through an authenticated subprocess, invoke a trusted synchronous callback, then independently assess the final state. The tool return value is not a success oracle. Actor status and state verdict are separate; a matching state never establishes actor attribution. See `docs/TOOL_INTEGRATION.md`.

Run the new adversarial corpus: `PYTHONPATH=src python -m openactionproof.observation_benchmark`. It emits a JSON report with the per-case results and confusion matrices. The corpus is developer-authored, not an independent evaluation against existing verifiers.


## Research preview packaging

The proposed package metadata is now 0.9.0rc1 (not a tagged release). Build a wheel with `python -m pip wheel --no-deps --wheel-dir dist .`, then install the resulting wheel into a clean virtual environment with `python -m pip install --no-deps --no-index --find-links dist open-action-proof==0.9.0rc1`. Run `python scripts/smoke_installed.py` from a checkout using that environment. The smoke test exercises the installed CLI and both development corpora from a separate temporary working directory. Core runtime has zero third-party dependencies. The optional Inspect AI evaluation uses a pinned framework version and controlled callbacks, not a live LLM; see docs/INSPECT_INTEGRATION.md. Cross-platform and optional framework CI are pending.

## Exact declared scope (experimental)

The optional `openactionproof.scope.verify_scoped_write` verifies a caller-pinned initial and final SQLite table snapshot, detecting collateral row changes and repeated revision increments within that scope. It is not a whole-system side-effect or causal guarantee. See docs/SCOPED_VERIFICATION.md. Reproduce the post-freeze evaluation with `PYTHONPATH=src python scripts/evaluate_operation_scope.py`; its negative findings are preserved in benchmarks/POST_FREEZE_SCOPE_RESULTS.md. The 0.9.0rc1 package was validated by installed-wheel CI on Windows, Linux and macOS and by a controlled Inspect AI integration. This proposed extension still awaits CI.

## Public-key evidence (experimental)

Install the optional extra with `python -m pip install ".[public-evidence]"`. The new `openactionproof.public_observation` module supports Ed25519 signed observations and pinned-key verification with durable replay protection. Unlike HMAC, a verifier need not possess the private signing key. Observer trust and key authorization remain caller responsibilities; this is not causal proof or a certified identity system. See docs/PUBLIC_EVIDENCE.md.
