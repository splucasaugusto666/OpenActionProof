# Evidence envelope v0.1 — experimental, HTTP lab only

The underlying receipt records case, expected state, before/after snapshots, attempts, agent claim, fixture label, verifier verdict and a canonical JSON SHA-256 checksum. The validator checks exact top-level keys, nonnegative typed counters, unique event IDs, append-only event prefixes, counter/event consistency, known attempt keys and recomputes the verdict. Fixture labels are test metadata, not proof.

An authenticated envelope binds schema, task_id, observer_id, challenge and receipt with HMAC-SHA256. The client must generate a fresh cryptographically random 32-byte challenge, pin the expected intent independently, and use a securely distributed key of at least 32 bytes. Key holders can forge MACs; a compromised observer or shared key defeats authentication. A hash alone does not authenticate evidence.

Example in examples/authenticated_receipt.py. ReplayGuard is bounded and process-local; it fails closed on repeated challenges or exhausted capacity. It does not survive restarts. Never expose the mock HTTP service to hostile users. No key storage, rotation, public signature, cross-language canonicalization guarantee, remote attestation, or independent custody yet. The challenge is bound to the signed receipt, not cryptographically bound to the underlying HTTP execution; a trusted signer must obtain fresh observations.
