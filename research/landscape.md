# Competitive landscape — preliminary

Existing tools and benchmarks include OpenAI Agents SDK tracing, Langfuse, OpenTelemetry, Inspect AI, AgentDojo, OSWorld, SWE-bench, AgentVerify, and an Agent Action Receipts Internet-Draft.

Tracing records attempts and responses but a logged tool call does not alone guarantee successful persistent effects. Inspect AI allows custom outcome scorers, and AgentVerify already explores verified agent outcomes and signed evidence. Thus outcome verification and receipts are **not novel** by themselves.

Research hypothesis (unproven): a vendor-neutral, intentionally adversarial *conformance suite for verifiers* may expose failure modes overlooked by claim-only or trace-only evaluations.

Sources:
- https://openai.github.io/openai-agents-python/tracing/
- https://github.com/langfuse/langfuse
- https://opentelemetry.io/
- https://inspect.aisi.org.uk/
- https://github.com/ethz-spylab/agentdojo
- https://github.com/aliasfoxkde/AgentVerify
- https://datatracker.ietf.org/doc/html/draft-sahu-agent-action-receipts-00

These are reference sources, not confirmation of unique technology or validated competitive advantage.
