# Release gates

## Verified milestones

- Public research prerelease [v0.9.0rc2](https://github.com/splucasaugusto666/OpenActionProof/releases/tag/v0.9.0rc2), published 2026-11-24 UTC, with wheel and SHA256SUMS.txt. Workflow [45313855917](https://github.com/splucasaugusto666/OpenActionProof/actions/runs/45313855917): six successful jobs including Windows, macOS, Linux, Python 3.10/3.12/3.13 and controlled Inspect AI.
- PR #18 authorized observer key grants and passed eight CI jobs; PR #19 external comparison passed nine CI jobs; PR #20 bounded-memory snapshots passed eight CI jobs and merged. Combined-main CI is a separate check.
- PR #19 executed the actual Verieffect 0.2.0a4 distribution with pinned wheel digest, both tools scored 100/100 on twelve final-file cases. Narrow developer-authored experiment, not independent leadership evidence.
- PR #20 local 125/125 tests reported; local before/after memory improvement documented. See benchmarks/STREAMING_SNAPSHOT.md.
- The published wheel predates PRs #18–20. The repository and release are not interchangeable.

## Remaining gates before stable v1.0.0

- Independent held-out evaluation and broader like-for-like external comparison; report negative findings and unsupported cases.
- Independent threat-model and security review, stronger observer isolation and private-key custody/current-policy distribution, with no unresolved known critical failures.
- Reproducible integration, documented protocol and operational boundaries, complete installation and evidence instructions; controlled Inspect evaluation is already validated, no live model claim.
- Final source/version alignment, provenance and package validation, all required tests and CI on release commit, changelog and public stable release with actual assets confirmed.

Do not reduce these gates to increase apparent progress. External recognition and APEX growth are tracked separately in research/APEX_GLOBAL_SCORECARD.md; popularity does not gate v1.0.0.
