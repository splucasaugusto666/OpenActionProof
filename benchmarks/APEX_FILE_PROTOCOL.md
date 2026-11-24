# APEX competitive evaluation v1 — frozen protocol

Date: 2026-11-23. Baseline OpenActionProof commit b535850af64a460f96edfbcf56fa40df0d5ff974. External comparator: published Verieffect 0.2.0a4 wheel, SHA-256 4d58a0f2521140fcc762c9b19e672645a82964bd4bc7532097e33858a5088d1f. Source commit abe4636b6ea43558b78d6381b685cef022c08a62. Reference: https://pypi.org/project/verieffect/0.2.0a4/ and https://github.com/bfeng1122/verieffect.

Primary endpoint: exact final regular-file content, as pinned by the host before the operation; not causal attribution or whole-operation safety. Both systems see identical file fixtures in separate fresh temporary directories. OAP: verify_action with its final observation matches_expected (not its higher-level attempt verdict); Verieffect: actual CLI file_exists probe with expected SHA-256 and its documented PASS/FAIL/UNVERIFIABLE. No mock comparator, no shell or network probe, no paid APIs. Raw exit code, mapped decision, OAP attempt verdict and receipt integrity reported. If dependency installation or adapter contract fails, report not evaluated; do not substitute a baseline. Each case counts once. A script error or unsupported verdict is not a true negative. The comparator has a private temporary VERIEFFECT_HOME; CI read-only permissions and no secrets.

Corpus (developer-authored, not independent); expected bytes: "expected" except where explicit. Cases:
- write_exact: absent -> expected, positive
- replace_exact: "old" -> expected, positive
- preexisting_exact: expected -> unchanged, positive
- empty_exact: absent -> empty (goal empty), positive
- unicode_exact: absent -> UTF-8 "ação ✓" (same goal), positive
- committed_then_error: absent -> expected then raise, positive
- absent_noop: absent -> unchanged, negative
- wrong_same_size: absent -> "xxxxxxxx" (8 bytes), negative
- partial_write: absent -> "exp", negative
- existing_wrong: "old" -> unchanged, negative
- deleted: expected -> deleted, negative
- overwritten: absent -> expected then "wrong", negative

Score 0–100 for this endpoint only: 45*TN/(TN+FP+negative abstentions) + 35*TP/(TP+FN+positive abstentions) + 20*decisions/N, with abstentions distinguished from FAIL, no exclusions. More weight on avoiding unsafe acceptance; abstention penalizes coverage and respective class score. Report TP/TN/FP/FN/abstentions, class counts, raw per-case rows. No aggregate score if a method cannot run all cases. Do not rank projects overall from this test. Secondary descriptive endpoint: newly attained state (initial not equal to goal and final equal); compare OAP's richer verdict separately, do not treat a final-state comparator as promising transition semantics. No latency ranking across in-process vs CLI interfaces; report elapsed time only as observed end-to-end diagnostic.

Competitive roadmap weights (not scored until evidence): 35 outcome correctness/abstention, 25 security and trust boundaries, 15 integration coverage, 10 interoperability and packaging, 10 reproducible performance, 5 developer usability. Market adoption separate. Unknown dimensions stay unscored, not zero. Expand coverage with AOIE, AgentVerify and others in subsequent separately frozen experiments. A single developer-designed corpus cannot establish category leadership.

Freeze protocol before running or tuning. Publish all results, including losses, and preserve baseline commit and exact dependency versions.
