# Project state

Stage: v0.4 research MVP, 2026-11-23.

Implemented: file verifier, 14-case loopback HTTP lab including actual socket timeout and observer HTTP 503, receipt checksums, HMAC envelope with bounded replay guard, two naive benchmark baselines, CLI, CI definition, research/governance docs. Local Python 3.13.5: 23 unit tests passed and all 14 in-sample fixture verdicts matched. GitHub Actions execution is not yet confirmed.

Not production-ready. Remaining: separate actor/observer trust domains, durable replay/key handling, generic adapter protocol, stale authoritative observations, held-out external verifier comparisons, real LLM integrations, independent reproduction and release validation. Guinness eligibility remains unapproved.

## Proposed v0.5 (PR)

Durable SQLite replay guard added. Local Python 3.13.5: 30/30 unit tests passed, including seven new tests for persistence, separate-process reopening, concurrency, invalid MAC, capacity, missing and corrupt storage. Remote CI pending. Not yet merged or released. Observer independence, key lifecycle, held-out external evaluation and real integrations remain open.
