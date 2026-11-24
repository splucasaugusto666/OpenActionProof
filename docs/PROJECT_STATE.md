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

## Tool session and observation corpus — proposed candidate

PR #7 merged after GitHub Actions passed on Python 3.10, 3.12 and 3.13. New proposed changes: framework-neutral trusted synchronous tool API; 16-case developer-authored authenticated observation corpus with two explicit baselines; 62/62 local Python 3.13.5 tests passing. All five added source/test/corpus Git blob hashes match the tested local files. CI for this proposed PR remains pending. No external LLM framework is installed in the local environment; no real LLM integration or independent competitor comparison has been executed. Version labels in development discussion are milestones, not published release tags.

## Durable tool dispatch — proposed PR

PR #8 merged after three Python CI jobs succeeded. New proposed adapter validates structured tool calls against a host-pinned intent and atomically claims the invocation in a persistent SQLite ledger before dispatch. 71/71 local tests passed in Python 3.13.5, including 9 new dispatch tests; 16/16 observation benchmark cases matched again. Both new Python files match tested Git blob hashes. Remote CI for the proposal is pending. No live SDK integration, independent comparison, exactly-once execution, distributed safety or published 1.0 release claimed. See docs/TOOL_DISPATCH.md.

## Durable dispatch recovery — proposed PR

PR #9 merged after successful Python 3.10, 3.12 and 3.13 CI. The proposed recovery journal persists immutable verifier summaries and distinguishes pending, unresolved and recorded outcomes; an explicit migration preserves legacy claims. Python 3.13.5: 81/81 local tests passed (19.899 s), including ten recovery tests and an actual interrupted subprocess. Existing 16-case observation corpus: 16/16. Both changed Python blobs match the tested source files. Remote CI pending; no automatic reconciliation, physical power-loss guarantee, independently verified benchmark, or live framework integration. Next: review the PR, add a reconciliation protocol with fresh authenticated observations, and test real framework integration before a release.


## Research preview packaging and interoperability — proposed PR

PR #10 merged after all three Python CI jobs succeeded. New proposal aligns distribution and import versions at 0.9.0rc1, adds portable path restrictions and redacts raw exception messages in the original file receipts. Local Python 3.13.5: 83/83 unit tests passed (19.893 s); local wheel built without index access and installed in a fresh virtual environment with no runtime dependencies; 33 installed smoke cases passed (3 file, 14 HTTP, 16 observation). New cross-platform workflow and optional real Inspect AI framework task are configured but not yet executed remotely. Inspect AI is not installed locally; no framework success claim. Local wheel is a development artifact, not a release. See docs/RELEASE_GATES.md and docs/INSPECT_INTEGRATION.md.
