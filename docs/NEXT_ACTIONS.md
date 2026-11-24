# Next actions

1. Freeze an independent held-out fixture set; include stale authoritative observations, malformed evidence, crash/restart, and concurrent unrelated effects.
2. Design generic adapter interface and separate actor/observer processes. Implement durable replay storage and key lifecycle.
3. Compare with independent external verifiers (Inspect AI and AgentVerify where compatible); report failures and overhead.
4. Validate CI on supported platforms and publish a versioned release only after review.
5. Research external reproducibility and official Guinness eligibility separately.

Proposed v0.5 PR addresses the local durable replay portion of item 2. Next: validate CI, separate the observer interface from the actor, bind fresh observations to the requested intent, and test stale observations. Key rotation, crash/power-loss validation and external evaluation are still pending.

Current priority after authenticated pairs: end-to-end trusted observer subprocess integration with key custody and fresh challenge issuance, external verifier adapter and held-out evaluation, then packaging and documented release criteria. Recheck this PR's CI before merging. Do not mistake matched state for actor attribution. Security isolation, durable intent lifecycle, key rotation and storage rollback resistance remain open.

After the authenticated worker PR passes CI: add real framework integration with a deterministic offline tool-use path, freeze a held-out benchmark corpus and comparison methodology before evaluation, measure false-positive/negative rates and overhead, and verify installation on clean environments. Prioritize meaningful evidence over commit counts. Independent review and stronger key custody/isolation remain necessary.
