# Synthetic HTTP verifier benchmark v0.2

The fixture labels in CASES specify whether confirmation is justified, not whether any effect exists. A missing authoritative observation is therefore an unconfirmed case even if the write happened. Exactly one effect on the target and zero effects on the other resource are expected. Twelve construction fixtures are included, with four positive and eight non-confirmed labels.

The three binary classifiers are: explicit success claim, any 2xx acknowledgement, and authoritative-state verification. Accuracy is (TP + TN) / 12. No exclusions, no statistical inference, no external agents. Exact multiclass match is separately reported. Fixtures are hand-constructed and in-sample: not an independent evaluation. The stale-read case emulates a misleading response, and observer unavailability is injected rather than an on-wire fault. Lost acknowledgement is an intentional disconnect, not a wall-clock timeout.

Reproduce: PYTHONPATH=src python -m openactionproof.http_lab --output evidence/generated/http-benchmark.json

Observed local Python 3.13.5 run: 12/12 exact labels; state verifier TP=4 FP=0 TN=8 FN=0; claim-only TP=3 FP=7 TN=1 FN=1; HTTP 2xx TP=3 FP=8 TN=0 FN=1. These are not comparative results against AgentVerify or Inspect AI.

Next: freeze a held-out corpus, use separate observer trust domains, integrate independent external verifiers, assess generalization, record errors and resource costs. Publish negative findings.
