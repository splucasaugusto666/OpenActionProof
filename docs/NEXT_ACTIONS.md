# Next actions

1. Freeze an independent held-out fixture set; include stale authoritative observations, malformed evidence, crash/restart, and concurrent unrelated effects.
2. Design generic adapter interface and separate actor/observer processes. Implement durable replay storage and key lifecycle.
3. Compare with independent external verifiers (Inspect AI and AgentVerify where compatible); report failures and overhead.
4. Validate CI on supported platforms and publish a versioned release only after review.
5. Research external reproducibility and official Guinness eligibility separately.

Proposed v0.5 PR addresses the local durable replay portion of item 2. Next: validate CI, separate the observer interface from the actor, bind fresh observations to the requested intent, and test stale observations. Key rotation, crash/power-loss validation and external evaluation are still pending.
