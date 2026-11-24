# Comparative landscape — 2026-11-23

This is a documented feature review, not a head-to-head benchmark. GitHub Trending is a discovery signal, not evidence of technical superiority.

## Complementary projects

- CLI-Anything: agent-native software interfaces; see https://github.com/HKUDS/CLI-Anything and https://github.com/trending.
- Agent Desktop: desktop automation through accessibility APIs; https://github.com/vercel-labs/agent-desktop.
- Superpowers: engineering skills and verification-before-completion methodology; https://github.com/obra/superpowers.

OpenActionProof focuses on outcome evidence rather than general execution. A future integration may let these tools benefit from an independent outcome verifier; no integration with those three projects is currently claimed.

## Direct alternatives

- AOIE: https://github.com/SadgunaPrabhath/agent-outcome-integrity. Published scripted and browser evaluation, recovery policies and dashboard. Its reported results use different datasets and endpoints; do not compare percentages directly. OAP should learn from the cross-agent evaluation and stale-read abstention.
- Verieffect: https://github.com/bfeng1122/verieffect. Deterministic probes, Ed25519-signed receipts, hash chain and offline public-key verification. The reviewed README describes operator-owned named checks as a roadmap item; OAP already supports caller-pinned intent and persistent invocation claims in its local SQLite reference. This is a design distinction, not demonstrated security superiority. Verieffect has broader documented probes and public-key verification; OAP's HMAC cannot provide the same public provenance.
- AgentVerify: https://github.com/AgentVerify/agentverify. Static analysis of tool reachability, permissions and execution paths. Complementary to runtime outcome verification, not an equivalent baseline.

## Evidence and gaps

PR #13: all seven GitHub Actions jobs passed (Python 3.10/3.12/3.13, installed wheel on Linux, Windows, macOS, controlled Inspect AI task). Local proposed callback fix: 105/105 tests (Python 3.13.5, 26.199s). No independent external reviewer or comparable competitor experiment yet. The frozen scope evaluation demonstrated two false positives when target-only checks were misused to confirm full operations; the regression fix addresses only the declared local table scope.

Next: implement a comparable adapter harness, pin competitors' versions and common outcome semantics before execution, report unsupported cases explicitly and publish confusion matrices, uncertainty and latency without extrapolating across datasets. Improve public-key verification and trust isolation only after defining the threat model. Do not use stars, test counts, or developer-authored accuracy as a ranking of technical quality.
