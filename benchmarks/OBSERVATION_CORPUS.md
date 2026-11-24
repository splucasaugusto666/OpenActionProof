# Frozen adversarial observation corpus v1 (development evaluation)

Define cases and expected labels before running the benchmark. All cases share fixed synthetic before/after windows, a pinned task and expected digest, and a dedicated replay store. Positive means changed-to-expected state with valid authenticated observations, **not actor attribution**. State-only baseline reads the final asserted digest without authentication or freshness checks; claim-only baseline trusts the fixture's actor claim. Each row counts once; no exclusions. Report TP, FP, TN, FN, accuracy, and exact multiclass verdicts for the tested method. These are developer-authored cases, not independent held-out research or a competitor comparison.

| Case | Label | Claim |
|---|---|---|
| normal | STATE_MATCHED_UNATTRIBUTED | true |
| lost_ack | STATE_MATCHED_UNATTRIBUTED | false |
| no_effect | STATE_MISMATCH | true |
| preexisting | STATE_PREEXISTING | true |
| wrong_state | STATE_MISMATCH | true |
| missing | INDETERMINATE | true |
| expired | INDETERMINATE | true |
| wrong_key | INDETERMINATE | true |
| tampered | INDETERMINATE | true |
| wrong_task | INDETERMINATE | true |
| wrong_goal | INDETERMINATE | true |
| replay | INDETERMINATE | true |
| rollback | INDETERMINATE | true |
| same_revision_change | INDETERMINATE | true |
| wrong_resource | INDETERMINATE | true |
| future_observation | INDETERMINATE | true |

Run `PYTHONPATH=src python -m openactionproof.observation_benchmark`. Timings (if reported separately) are environment-specific. No generalization or competitor superiority claim. Revisit the corpus in a new version rather than silently changing labels after execution.
