# APEX file comparison: local baseline checkpoint

The protocol was committed before evaluation at 25b021529a1d8cf30fe5b1388665b28f7f9af194. Local evaluation used the 12 frozen cases and the existing OpenActionProof file verifier. Actual command: PYTHONPATH=src python scripts/apex_file_compare.py --local-only.

6 TP, 6 TN, 0 FP, 0 FN, 0 abstentions; endpoint-specific weighted score 100/100. The final-file endpoint is intentionally different from action completion: the preexisting fixture produced STATE_SATISFIED_UNATTRIBUTED, and the committed-then-error fixture produced INDETERMINATE for attempt status, while both had matching final file content.

Local package retrieval for Verieffect 0.2.0a4 failed (no matching distribution in this environment). No external result, ranking, latency advantage or global leadership claim. The CI workflow downloads the exact PyPI wheel, verifies SHA-256, uses the genuine CLI and checks its signed receipts. It records dependency versions and uploads results. The local script's Git blob matched the published file (67c23226c07687245a0f338e4b0c955603e55216). CI execution is pending.

Competitors reviewed: Verieffect (file/HTTP/database probes and public signed hash-chained receipts); AOIE (browser/LLM adapter and recovery); AgentVerify (runtime contracts and signed evidence); Postcept (hosted system-of-record verification with open clients). No verified category-wide leader. The next experimental comparisons must expand beyond the easy file endpoint to stale observations, authorization, retries and recovery, without changing previously frozen criteria.

This benchmark is developer-authored, not independently curated. The base research preview remains publicly available at https://github.com/splucasaugusto666/OpenActionProof/releases/tag/v0.9.0rc2. PR #18 passed all eight jobs and merged. The official 1.0 and APEX leadership criteria remain separate.
