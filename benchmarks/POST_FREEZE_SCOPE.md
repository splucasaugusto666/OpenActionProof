# Post-freeze operation scope evaluation v1

Frozen before first evaluation; verifier baseline is the merged PR #11. This is a new developer-authored corpus, not independently curated or blinded. The verifier implementation must not be tuned to the cases before measuring. Use a local SQLite database with two resources, target and other, initial revision 0. Expected target is "new", unless noted; other starts "untouched". Each mutation increments the affected revision. All actor return claims are success (except the explicit error and no invocation cases). Actor status is recorded separately from the observer verdict.

Two endpoints: (A) evidence-backed change of the target only, using the existing observer semantics; (B) complete declared operation, exactly one revision increment of target to the expected value and no change to other. Preexisting state is not a newly completed operation. An error after a committed effect does not change the state-only labels. Missing observation is indeterminate for A and is not a positive complete operation for B.

| Case | Initial target | Mutations / actor behavior | A expected verdict | B exact operation |
|---|---|---|---|---|
| normal | old | target=new | STATE_MATCHED_UNATTRIBUTED | true |
| false_claim | old | no effect | STATE_MISMATCH | false |
| wrong_resource | old | other=new | STATE_MISMATCH | false |
| wrong_value | old | target=wrong | STATE_MISMATCH | false |
| collateral_write | old | target=new; other=changed | STATE_MATCHED_UNATTRIBUTED | false |
| duplicate_write | old | target=new twice | STATE_MATCHED_UNATTRIBUTED | false |
| overwritten_target | old | target=new; target=wrong | STATE_MISMATCH | false |
| error_after_commit | old | target=new; raise | STATE_MATCHED_UNATTRIBUTED | true |
| preexisting | new | no effect | STATE_PREEXISTING | false |
| deleted_target | old | delete target | INDETERMINATE | false |
| missing_initial | absent | must not invoke actor | INDETERMINATE | false |
| unicode_goal | old | target=ação ✓ | STATE_MATCHED_UNATTRIBUTED | true |

Compare three decision policies: agent return ("RETURNED" means success), authoritative final target equals expected (no historical or collateral check), and OpenActionProof target verdict equals STATE_MATCHED_UNATTRIBUTED. Report confusion matrices separately for A (positive iff expected verdict is STATE_MATCHED_UNATTRIBUTED) and B (positive iff exact operation is true). Also report exact A verdict matches, actual full-state oracle agreement and execution time distribution, no exclusions. The baselines intentionally have different evidence semantics; do not infer external competitor inferiority. Report false positives for B, including valid target observations with collateral effects, rather than adjusting labels after evaluation. No LLM or paid services. A new contract for multi-resource effects, if needed, must be evaluated on a later separate corpus.
