# Project state

Stage: v0.3 local research MVP, 2026-11-23.

Implemented: file verifier, 12-case loopback HTTP lab, checksummed receipts, two naive benchmark baselines, strict lab receipt checks, HMAC envelope, one-time challenge guard, CLI, CI definition and research/governance docs. Local Python 3.13.5: 21 unit tests passed; 12/12 synthetic HTTP verdicts matched. GitHub Actions results not yet confirmed.

Not complete: actual timeout and observer transport failure fixtures; generic adapter protocol; independent observer process and durable replay store; external verifier comparisons/held-out evaluation; real agent integrations; official Guinness eligibility. Not production-ready.
