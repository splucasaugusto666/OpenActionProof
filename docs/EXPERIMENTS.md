# Experiments

## Local v0.1 evidence

Command: PYTHONPATH=src python -m unittest discover -s tests -v
Observed 2026-11-23: 8 tests, all passing in local Python environment.

Command: PYTHONPATH=src python -m openactionproof demo
Observed: A_confirmed=CONFIRMED; B_false_success=FALSE_SUCCESS; C_partial_timeout=INDETERMINATE.

The tests are synthetic construction tests. They do not validate real agent behavior, accuracy against external baselines, or independent signatures. For reproducibility rerun the commands, inspect generated JSON receipts, and check them using verify-receipt.

## v0.2 HTTP benchmark

12 unit tests passed locally; 12/12 fixture labels matched. See `benchmarks/METHODOLOGY.md` for confusion matrices and limitations.

## v0.3 authenticated receipts

Local Python 3.13.5: 21 unit tests passed. Nine new tests exercise valid envelopes, all HTTP fixture receipts, wrong key, wrong task/observer/challenge, recomputed checksum forgery, inconsistent transition, replay/capacity, malformed inputs/weak keys, and detached copies. These tests do not validate key custody or a remote security boundary.

## v0.4 transport tests

Local Python 3.13.5: 23 unit tests passed, 14/14 fixture verdicts matched. Binary confirmation metrics: state verifier TP=5 FP=0 TN=9 FN=0; claim-only TP=3 FP=8 TN=1 FN=2; HTTP 2xx TP=3 FP=9 TN=0 FN=2. In-sample, synthetic fixtures only. A real socket timeout and HTTP 503 were tested separately.

## Proposed v0.5: durable replay protection

2026-11-23, Python 3.13.5: `PYTHONPATH=src python -m unittest discover -s tests -v` produced 30 passing tests in 2.055 seconds. In the concurrent test, exactly one of 16 competing connections consumed the challenge. A separate Python process rejected a previously consumed challenge. Invalid MACs did not consume a challenge, missing/corrupt databases failed closed, and persisted capacity prevented drift. Not a power-loss or distributed-storage experiment. Remote CI unconfirmed.

## Authenticated observation pair experiment

2026-11-23, Python 3.13.5: `PYTHONPATH=src python -m unittest discover -s tests -q` ran 48 tests in 4.091 seconds, all passed. Nine new tests cover authenticated pair acceptance, replay after reopen, wrong key/task/goal/window, tampering, incomplete pairs, rollback on second-token conflict, 16 competing threads (one accepted, 15 indeterminate), capacity exhaustion, state mismatch and missing storage. Local construction tests only. The prior observer PR #5 CI passed on Python 3.10, 3.12 and 3.13. CI for these new changes is pending.

## Authenticated observer worker experiment

`PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -q`: 55 tests passed in 9.896 seconds (Python 3.13.5). Seven new tests exercise authenticated observation, separate actor and observer processes, persisted replay rejection, missing resources, expired/future windows, malformed and oversized output, simulated timeout, redacted failure, and no key in command-line arguments. The timeout is injected in this worker test; it is not a measured worker deadline benchmark. An existing SQLite connection leak in a test was corrected. All three changed Python files were compared with the published Git blob SHA. No external-agent or competitor claims.

## Tool integration and observation corpus v1

Frozen labels documented before the run in benchmarks/OBSERVATION_CORPUS.md (local SHA-256 3496bef740c641aee13943da0a03d354140ee4e493e04befb99885a6ac1a90dd). Python 3.13.5: `PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -q` ran 62 tests in 17.814 seconds, all passing. `PYTHONPATH=src python -m openactionproof.observation_benchmark`: 16/16 exact multiclass verdicts. Binary positive is authenticated changed-to-expected state, NOT actor causality. Authenticated method TP=2 FP=0 TN=14 FN=0; claim-only TP=1 FP=14 TN=0 FN=1; state-only TP=2 FP=11 TN=3 FN=0. Accuracy 100%, 6.25%, 31.25%, respectively, on this deliberately failure-heavy synthetic corpus (2 positives, 14 negatives). No exclusions. Naive baselines omit trust checks by design; this is not external or independent research or an estimate of production accuracy. CI pending.
