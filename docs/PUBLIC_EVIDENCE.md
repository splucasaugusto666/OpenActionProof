# Publicly verifiable observation evidence (experimental)

The optional public-evidence extra uses Ed25519 through the cryptography library rather than implementing a signature primitive locally. Install with python -m pip install ".[public-evidence]". The base package remains dependency-free at runtime.

The observer holds an Ed25519 private key and signs its own observations with observe_signed. A relying party pins the corresponding public key, task, expected state digest and observation request independently. authenticate_signed verifies the domain-separated canonical envelope, key fingerprint, request binding, observation window and signature. The key fingerprint is SHA-256 over the raw public key; it identifies a pinned key, not a certified observer identity. The envelope cannot nominate a new trusted key.

assess_signed_pair validates two observations against the same pinned key and consumes both challenges atomically in the durable replay guard. Replay scope remains observer ID and challenge, so selecting a new key does not reset previously consumed challenges. The relying party must determine whether a key is authorized and handle rotation, revocation, time and key custody. Independent verification of a signature does not establish observer honesty, actor attribution, process isolation, unchanged outside resources or proof that a historical action happened. Expired observations do not become valid merely because their signature verifies. No public transparency log, certificate infrastructure, cross-language canonicalization standard, or independent security audit is provided.

Local evidence: cryptography 46.0.4; all nine new tests passed, including RFC 8032 test vector 1, body and signature tampering, key substitution, expired and mismatched requests, schema confusion, durable replay under concurrency (one acceptance in sixteen attempts), and replay across a key change. Full local suite: 114/114 passed in 26.139 seconds using PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -q. Both new Python blobs match the locally tested source files. An explicit public-evidence CI job is added; remote verification of this proposal is pending. The prior PR #14 passed all seven existing CI jobs and was merged.

Reproduce: python -m pip install ".[public-evidence]" then python -m unittest discover -s tests -p test_public_observation.py -v.

This is an optional signature layer, not evidence of comparative superiority to other projects.
