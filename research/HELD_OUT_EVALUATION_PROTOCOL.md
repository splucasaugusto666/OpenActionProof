# Held-out verifier evaluation protocol (proposal)

Status: proposed, not executed. This protocol is a next step beyond the developer-authored construction fixtures in [the observation corpus](../benchmarks/OBSERVATION_CORPUS.md) and [HTTP methodology](../benchmarks/METHODOLOGY.md). It does not establish production reliability or comparative superiority.

## Research question

Under controlled tool-call failures, when can a verifier distinguish a justified confirmation from an unsupported success claim, and at what cost in abstentions and observation latency?

## Hypotheses

H1: independent state observations reduce unjustified confirmations compared with claim-only and acknowledgement-only rules on a held-out corpus. H2: stricter evidence requirements increase indeterminate verdicts under observer failure. Neither hypothesis is established by this protocol.

## Corpus and execution

1. Freeze the task contract, target resource scope, evidence policy, verdict mapping and baseline versions before generating evaluation cases.
2. Have a contributor other than the verifier implementer author cases, or clearly mark cases as developer-authored if independent contributors are unavailable. Keep expected labels out of the verifier's input.
3. Include confirmed changes, false claims, pre-existing desired state, partial effects, stale observations, repeated writes, observer failure, wrong scope, and authenticated but inconsistent evidence. Record the fault and ground-truth observation separately from actor claims.
4. Use isolated temporary resources and controlled callbacks first; separately label any live-agent experiments with model, harness, tool configuration, and sampling parameters. Never treat synthetic callbacks as LLM trials.
5. Commit a hash of the frozen manifest before running evaluations. Record exact Git SHAs, environment, random seeds if applicable, and reproduction commands. Keep raw redacted outcomes and report every failure.
6. Evaluate claim-only, acknowledgement-only, state-only and the candidate under equivalent observable inputs; document which signals each baseline is allowed to use. A third-party comparator requires a separately documented adapter and version, not an assumed implementation.

## Metrics and reporting

Report per-class counts, exact verdict agreement, confusion matrix for justified confirmation, false-confirmation rate among ground-truth non-confirmations, confirmation recall, indeterminate rate, and median/p95 observation latency. Give denominators, missing observations, and exclusions explicitly. Report per-fault-category results and distinguish observed final state from causal attribution. Use uncertainty intervals only where the sampling design supports them; hand-authored fixtures do not imply population estimates.

## Acceptance and falsification

Before execution, publish a numerical acceptance threshold and sample plan appropriate to the corpus. Any unsupported confirmation is a safety-relevant counterexample to investigate, not an excuse to discard a case. If an external verifier is unavailable, report only the internal baselines. Publish negative results and retain the frozen corpus after changes; create a new corpus for a new held-out evaluation.

## Boundaries

This experiment does not establish actor identity, trust-domain independence, end-to-end security, or absence of out-of-scope side effects. Authentication is not equivalent to independent observation. The existing synthetic results remain historical; no new measurements or external adoption are claimed here.
