# Experimental Inspect AI interoperability

The optional integration uses Inspect AI's actual task, solver and scorer APIs, with pinned dependency inspect-ai==0.3.292 (Python 3.11+). It evaluates three deterministic local SQLite tool scenarios: a write, a false success claim with no write, and a preexisting desired state. The custom solver invokes OpenActionProof's authenticated tool-session verifier; the scorer compares the trusted evaluator-produced verdict to the predeclared fixture target. All callbacks report the same success string; it is not used as evidence. No live model, external API credentials, hosted inference, sandbox or untrusted agent is involved.

Install into a separate virtual environment: python -m pip install . inspect-ai==0.3.292
Run: python integrations/inspect_ai_smoke.py
CI disables model APIs other than mockllm via INSPECT_DISABLE_MODEL_API=1. The mock model is configured but not invoked. A successful run requires all three scored samples and successful Inspect log status.

References checked 2026-11-23:
- https://inspect.aisi.org.uk/solvers.html
- https://inspect.aisi.org.uk/custom-scorers.html
- https://inspect.aisi.org.uk/eval-logs.html
- https://pypi.org/project/inspect-ai/0.3.292/

Status: integration source and CI job provided; Inspect AI is absent from the offline local environment and this job has not yet been confirmed. This is a compatibility experiment, not an independent comparison with Inspect AI or a real-agent validation. The remaining release gates are in docs/RELEASE_GATES.md. No claim of independent attestation, security certification or causal proof.
