# Project state

Stage: v0.4 research MVP, 2026-11-23.

Implemented: file verifier, 14-case loopback HTTP lab including actual socket timeout and observer HTTP 503, receipt checksums, HMAC envelope with bounded replay guard, two naive benchmark baselines, CLI, CI definition, research/governance docs. Local Python 3.13.5: 23 unit tests passed and all 14 in-sample fixture verdicts matched. GitHub Actions execution is not yet confirmed.

Not production-ready. Remaining: separate actor/observer trust domains, durable replay/key handling, generic adapter protocol, stale authoritative observations, held-out external verifier comparisons, real LLM integrations, independent reproduction and release validation. Guinness eligibility remains unapproved.

## Proposed v0.5 (PR)

Durable SQLite replay guard added. Local Python 3.13.5: 30/30 unit tests passed, including seven new tests for persistence, separate-process reopening, concurrency, invalid MAC, capacity, missing and corrupt storage. Remote CI pending. Not yet merged or released. Observer independence, key lifecycle, held-out external evaluation and real integrations remain open.

## Observer contract and authenticated pairs (2026-11-23)

PR #4 (durable replay) and PR #5 (reference observer) merged after GitHub Actions passed on Python 3.10, 3.12 and 3.13. PR #5 merge: e69be5b384c12b1a285222656c1a1db9378fd29b. The proposed follow-up binds task ID, expected state digest, resource, observer, challenge, request window and observation to an HMAC-SHA256 envelope and consumes both challenges in one SQLite transaction. Local Python 3.13.5: 48/48 tests passed, including nine additional pair tests; remote CI for the new changes is pending. Still a research prototype, not a released v1.0. No real-agent integration, external benchmark comparison or independent security certification yet.

## Authenticated subprocess transport — candidate

PR #6 merged after successful Python CI on 3.10, 3.12 and 3.13. This follow-up adds a fixed local observer worker that reads SQLite state and authenticates observations; a full integration test executes the actor separately, observes before/after through workers and rejects replay using persistent storage. Local Python 3.13.5: 55/55 tests passed, including seven new worker tests. Remote CI pending. This is a reference transport, not a privilege sandbox or LLM integration. External benchmarks and production security validation remain incomplete.
