# Operation scope evaluation — observed 2026-11-23

Frozen protocol: commit 2d6930044d1c03d3227d374d974955702ed88b1b, before first execution. Baseline: merged PR #11. Local Python 3.13.5. Run PYTHONPATH=src python scripts/evaluate_operation_scope.py. Script Git blob b1f1adfaee550a168513342bea1830153bbc97a0 matches locally executed source. Full report SHA-256: 6694ee11df27802a1cce029f7dbddfc12303b1b0b47e05c407e349cf09347bb4 (includes local elapsed times).

12/12 expected target verdicts; 12/12 full-state oracle labels. No exclusions.

| Endpoint | Policy | TP | FP | TN | FN | Accuracy |
|---|---|---:|---:|---:|---:|---:|
| Target change | Actor return | 4 | 6 | 1 | 1 | 41.67% |
| Target change | Final target only | 5 | 1 | 6 | 0 | 91.67% |
| Target change | OAP target | 5 | 0 | 7 | 0 | 100% |
| Complete operation | Actor return | 2 | 8 | 1 | 1 | 25% |
| Complete operation | Final target only | 3 | 3 | 6 | 0 | 75% |
| Complete operation | OAP target | 3 | 2 | 7 | 0 | 83.33% |

Negative findings: collateral_write and duplicate_write both yielded valid STATE_MATCHED_UNATTRIBUTED target verdicts despite failing the complete-operation oracle. A target-only observer cannot attest to unchanged other resources or exactly one revision increment. These are false positives if the target verdict is misused as a complete-operation decision. Not defects in the stated target-only semantics, but an integration hazard. Do not silently relabel or remove these cases.

Measured verification call time: min 610.82 ms, median 1595.65 ms, max 1721.86 ms. Includes configured 1-second before window, subprocess startup, SQLite and actor; not comparative latency or production performance.

Developer-authored post-freeze evaluation, not blinded or independently curated. Baselines are explicit policies, not competing products. No live LLM. Future scoped contract must distinguish its measured scope from whole-system side effects and use additional independently authored cases for generalization.
