import copy
import secrets
import unittest

from openactionproof.attestation import Intent, ReplayGuard, seal, verify, validate_lab_receipt
from openactionproof.core import canonical, sha256
from openactionproof.http_lab import CASES, execute


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.key = secrets.token_bytes(32)
        self.intent = Intent("normal", "observer-1", secrets.token_hex(32))
        self.receipt = execute(CASES[0])
        self.envelope = seal(self.key, self.intent, self.receipt)

    def test_valid_envelope(self):
        self.assertTrue(verify(self.key, self.intent, self.envelope))

    def test_all_lab_receipts(self):
        for case in CASES:
            with self.subTest(case=case.name):
                receipt = execute(case)
                intent = Intent(case.name, "observer-1", secrets.token_hex(32))
                self.assertTrue(verify(self.key, intent, seal(self.key, intent, receipt)))

    def test_wrong_key(self):
        self.assertFalse(verify(secrets.token_bytes(32), self.intent, self.envelope))

    def test_wrong_intent(self):
        for intent in (Intent("wrong", self.intent.observer_id, self.intent.challenge),
                       Intent(self.intent.task_id, "wrong", self.intent.challenge),
                       Intent(self.intent.task_id, self.intent.observer_id, secrets.token_hex(32))):
            self.assertFalse(verify(self.key, intent, self.envelope))

    def test_recomputed_checksum_cannot_replace_mac(self):
        forged = copy.deepcopy(self.envelope)
        receipt = forged["receipt"]
        receipt["fixture_label"] = "forged"
        receipt["receipt_sha256"] = sha256(canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"}))
        self.assertFalse(verify(self.key, self.intent, forged))

    def test_inconsistent_state_rejected_even_with_recomputed_checksum(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["after"]["counts"]["target"] = 2
        receipt["receipt_sha256"] = sha256(canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"}))
        self.assertFalse(validate_lab_receipt(receipt, self.intent.task_id))
        with self.assertRaises(ValueError):
            seal(self.key, self.intent, receipt)

    def test_replay_and_capacity(self):
        guard = ReplayGuard(capacity=1)
        self.assertTrue(guard.accept(self.key, self.intent, self.envelope))
        self.assertFalse(guard.accept(self.key, self.intent, self.envelope))
        other = Intent("normal", "observer-1", secrets.token_hex(32))
        self.assertFalse(guard.accept(self.key, other, seal(self.key, other, self.receipt)))

    def test_bad_envelope_and_weak_key(self):
        for value in (None, {}, {**self.envelope, "extra": True}, {**self.envelope, "mac": "x"}):
            self.assertFalse(verify(self.key, self.intent, value))
        with self.assertRaises(ValueError):
            seal(b"weak", self.intent, self.receipt)

    def test_detached_payload(self):
        self.receipt["verdict"] = "FALSE_SUCCESS"
        self.assertTrue(verify(self.key, self.intent, self.envelope))


if __name__ == "__main__":
    unittest.main()
