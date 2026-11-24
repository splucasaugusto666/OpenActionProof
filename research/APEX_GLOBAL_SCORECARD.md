# APEX global leadership scorecard v1

Baseline observed 2026-11-23 São Paulo / 2026-11-24 UTC. GitHub repository API and release metadata; counts are snapshots, not verified distinct users or organic attribution.

| Repository | Stars | Forks | Scope |
|---|---:|---:|---|
| splucasaugusto666/OpenActionProof | 1 | 0 | Outcome verification and conformance |
| bfeng1122/verieffect | 0 | 0 | Deterministic probes and signed evidence |
| SadgunaPrabhath/agent-outcome-integrity | 0 | 0 | Outcome verification and recovery |
| AgentVerify/agentverify | 0 | 0 | Static agent analysis; adjacent |
| Postcept/sdk | 1 | 0 | Client SDK; hosted verifier, not the whole product |

Sources: https://api.github.com/repos/OWNER/REPO for each row; https://api.github.com/repos/splucasaugusto666/OpenActionProof/releases. OAP had one public prerelease, zero wheel downloads and zero checksum downloads, no description or topics. Subscriber count was 1. Contributors endpoint unavailable in this connection; unique installs, active users, traffic, retention, search impressions and external mentions are unknown. Do not infer users from stars or aggregate a vendor's recognition from a single SDK.

## Frozen scorecard dimensions

| Dimension | Weight | Evidence required |
|---|---:|---|
| Technology | 40 | Comparable correctness, abstention, security, performance, scope |
| Experience and adoption | 20 | Measured first success, installation, real integrations, retention |
| Recognition and distribution | 25 | Observed stars, release downloads, search visibility and external references |
| Authority and sustainability | 15 | Reproducible studies, external replication, contributors, governance |

No overall numerical score until criteria, normalization, denominators and comparable data are frozen for each dimension. Unknowns are not zero. The previous technical scorecard remains the inner engineering evaluation, not a second set of aggregate weights. Current evidence: narrow 100/100 tie with Verieffect, not global leadership. No current global leader established.

## Growth experiments

1. README quickstart: direct official wheel link, first observable result, trust limits, navigation. Hypothesis: fewer steps to first successful local verification. Record elapsed time and failed steps in reproducible usability tests; no tracking of individuals.
2. Discoverability: concise repository description and relevant topics. GitHub Docs confirms these fields support repository search. Current connector has no supported write action for metadata; owner action needed. Suggested description: "Open-source AI agent outcome verification, signed evidence, durable replay protection, and reproducible conformance benchmarks." Suggested topics: ai-agents, outcome-verification, agent-reliability, ai-safety, python, ed25519, conformance-testing, open-source. No keyword stuffing.
3. Citation and reproducibility: CFF metadata, changelog, stable protocol and benchmark links. Citation counts are unknown; do not imply academic endorsement.
4. Catalog readiness: awesome-verified-agents (https://github.com/tonydzi/awesome-verified-agents) publishes an evidence-artifact inclusion criterion. Verify current guidelines and no duplicate, draft a single accurate entry for review; no external submission made. Avoid mass outreach.
5. Distribution: GitHub releases available; PyPI and other registries not established. Do not claim registration or publish to accounts without authorized tools. Maintain provenance and release gates first.

Reference patterns: Verieffect public PyPI distribution and quickstart (https://pypi.org/project/verieffect/); Postcept documented quickstart and public benchmark (https://postcept.com/docs and https://postcept.com/); GitHub official discovery guidance (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository). These are observed design patterns, not causal proof of adoption.

Checkpoint: PR #19 merged with nine successful checks; PR #20 merged after eight successful checks. Release v0.9.0rc2 remains public. Next: independent evidence, broader external comparisons, secure deployment boundaries and release 1.0. Record growth snapshots on future scheduled runs using the same sources. Respect the no-spam, no-fake-engagement and no-cost constraints.
