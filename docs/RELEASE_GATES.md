# Release gates — current research preview

- PR #11 merged after all seven GitHub Actions jobs passed: Python 3.10/3.12/3.13, installed wheel on Ubuntu/Windows/macOS, and the pinned Inspect AI controlled evaluation. The integration executes the actual evaluation framework but no live model.
- Local preview package 0.9.0rc1 was built and installed; 33 installed smoke cases passed. No official release tag or GitHub release yet.
- Proposed scope PR: 91/91 local tests passed. Frozen 12-case evaluation matched every target verdict; broader exact-operation endpoint exposed two false positives when the target verdict was misused. An optional exact snapshot scope adapter addresses the two known classes in regression tests. See benchmarks/POST_FREEZE_SCOPE_RESULTS.md and docs/SCOPED_VERIFICATION.md. Remote CI for this PR pending.
- Independent held-out evaluation and external verifier comparison: not yet demonstrated. Developer-authored post-freeze corpus is not independent or blinded.
- Independent threat-model review, stronger observer isolation and secret lifecycle: pending.
- Recovery journal exists; fresh authenticated reconciliation protocol and durable intent lifecycle remain incomplete.
- Release provenance review, official version metadata and GitHub release publication: pending.

No merge while required CI is unconfirmed. A 1.0 release must be identifiable and usable, with a documented scope and limitations, passing relevant tests, reproducible framework integration and honest comparative evidence. Do not silently weaken the saved release gates, claim external approval, or tag 1.0 before the criteria are met.

- PR #14: all seven CI jobs passed; merged. Proposed public-key evidence extension: 114/114 local tests passed with cryptography 46.0.4, including nine Ed25519 tests. Dedicated optional-extension CI pending. Signature verification improves key separation but does not close independent observer isolation, key lifecycle or independent benchmark gates. Official v1.0.0 remains unpublished.
