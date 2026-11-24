# OpenActionProof

**Verify the outcome of an AI agent's action — not just its success claim.**

[![Research preview](https://img.shields.io/github/v/release/splucasaugusto666/OpenActionProof?include_prereleases&label=research%20preview)](https://github.com/splucasaugusto666/OpenActionProof/releases) [![Python CI](https://github.com/splucasaugusto666/OpenActionProof/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/splucasaugusto666/OpenActionProof/actions/workflows/ci.yml) [![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE) [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

OpenActionProof is an open-source, vendor-neutral **AI agent outcome verification** toolkit and adversarial conformance lab. Pin the intended outcome before an action, check independently observed state, and preserve evidence of what is known and what remains uncertain. The core runs offline without model API keys or third-party runtime dependencies.

**Research preview, not a production security boundary.** A matching observation does not prove who caused it, and a valid signature does not establish observer honesty.

## Try it

Install the officially published [v0.9.0rc2 wheel](https://github.com/splucasaugusto666/OpenActionProof/releases/tag/v0.9.0rc2) on Python 3.10+ (Windows, macOS or Linux). Review the release notes and compare the downloaded wheel's SHA-256 to [SHA256SUMS.txt](https://github.com/splucasaugusto666/OpenActionProof/releases/download/v0.9.0rc2/SHA256SUMS.txt) before installing.

```sh
python -m pip install "https://github.com/splucasaugusto666/OpenActionProof/releases/download/v0.9.0rc2/open_action_proof-0.9.0rc2-py3-none-any.whl"
python -m openactionproof demo --output evidence/generated
python -m openactionproof verify-receipt evidence/generated/A_confirmed.json
```

Run inside a dedicated virtual environment. The demo writes three JSON receipts for controlled local file operations; it requires no LLM subscription. The checksum command validates serialization integrity, not the provenance of a receipt.

| Scenario | Agent's claim | Observed result | Attempt verdict |
|---|---|---|---|
| Expected write | Success | Exact contents | CONFIRMED |
| False completion | Success | Missing file | FALSE_SUCCESS |
| Partial write and timeout | Unknown | Partial contents | INDETERMINATE |

For a Python example, see [five-minute quickstart](docs/QUICKSTART.md). For new changes not yet in a tagged release, install from a checkout of main: `python -m pip install -e .`.

## What it does

| Capability | Implementation on main |
|---|---|
| Caller-pinned expected state and local file receipts | [Core evidence protocol](docs/EVIDENCE_PROTOCOL.md) |
| HTTP outcome and transport-failure evaluation | [Conformance methodology](benchmarks/METHODOLOGY.md) |
| SQLite-backed atomic challenge replay protection | [Observer contract](docs/OBSERVER_CONTRACT.md) |
| HMAC-authenticated subprocess observations | [Tool integration](docs/TOOL_INTEGRATION.md) |
| Persistent single-use dispatch and historical outcomes | [Dispatch ledger](docs/TOOL_DISPATCH.md) |
| Fresh read-only reconciliation without blind retries | [Reconciliation](docs/RECONCILIATION.md) |
| Exact declared table snapshot and revision checks | [Scoped verification](docs/SCOPED_VERIFICATION.md) |
| Optional Ed25519 signatures and caller-pinned key grants | [Public evidence](docs/PUBLIC_EVIDENCE.md) |
| Controlled evaluation in the actual Inspect AI framework | [Inspect integration](docs/INSPECT_INTEGRATION.md) |

Features on main can be newer than the published wheel. The key-policy and streaming file changes were merged after v0.9.0rc2. See [CHANGELOG](CHANGELOG.md) for this distinction.

## Evidence, not marketing claims

- [External comparison](https://github.com/splucasaugusto666/OpenActionProof/actions/runs/45314898752): OpenActionProof and the genuine Verieffect 0.2.0a4 CLI both scored 100/100 on a frozen 12-case exact-final-file-content corpus (6 true positives, 6 true negatives per tool). This is a tie on a narrow, developer-authored endpoint, not independent validation or overall superiority.
- [Scope evaluation](benchmarks/POST_FREEZE_SCOPE_RESULTS.md): target-only verification produced two false positives when used to infer complete-operation correctness. The negative finding is preserved; the scoped adapter addresses those known cases in regression tests.
- [Streaming snapshot experiment](benchmarks/STREAMING_SNAPSHOT.md): median peak traced Python allocations fell from 67,113,773 to 529,561 bytes for a 64 MiB observation in five alternating local trials; not a comparison to another product or measurement of total RSS.
- [Publication validation](https://github.com/splucasaugusto666/OpenActionProof/actions/runs/45313855917): six jobs passed, including full-suite and installed-wheel checks on Windows, Linux and macOS, then publication of the preview.

Reproduce the current development suite after cloning:

```sh
python -m pip install -e ".[public-evidence]"
python -m unittest discover -s tests -v
python -m openactionproof.observation_benchmark
python -m openactionproof.http_lab
python scripts/apex_file_compare.py --local-only
```

The external comparison requires the exact published Verieffect wheel and checksum documented in [APEX_FILE_PROTOCOL.md](benchmarks/APEX_FILE_PROTOCOL.md). The optional Ed25519 extra requires cryptography. See the [release gates](docs/RELEASE_GATES.md) for work remaining.

## Architecture and trust boundaries

```text
Host-pinned intent -> trusted action adapter -> observed state
       |                                      |
       +-------- evidence contract -----------+
                          |
        authenticated verdict / indeterminate
                          |
        durable replay and dispatch journal
                          |
             read-only reconciliation
```

- File checksums are not signatures; the Ed25519 extension uses caller-pinned trusted keys.
- The local observers, storage, revision counters, clock, callback and policy configuration are trusted as documented. No hostile-process sandbox, cross-database atomicity, distributed exactly-once guarantee or complete side-effect coverage.
- A state may preexist or be changed by another actor. Uncertainty never authorizes an automatic retry.
- The Inspect AI example uses controlled callbacks, not a live model. Development corpora are not independent production datasets.
- Do not use the preview to authorize irreversible or high-risk real-world transactions.

## Learn, reproduce, contribute

- [Quickstart](docs/QUICKSTART.md) · [Architecture decisions](docs/DECISIONS.md) · [Research methodology](benchmarks/METHODOLOGY.md)
- [Roadmap](ROADMAP.md) · [Release gates](docs/RELEASE_GATES.md) · [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Citation metadata](CITATION.cff)

Have a counterexample or independent evaluation? Open a reproducible issue with the expected and actual verdict, version, environment, and sanitized evidence. Do not include secrets or live-target attack details.

OpenActionProof / Project Genesis X is licensed under [Apache-2.0](LICENSE). Its aim is reliable, interoperable and verifiable AI systems, with honest evaluation of limitations and competing approaches.
