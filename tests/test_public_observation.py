from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import concurrent.futures
import unittest

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    Ed25519PrivateKey = None

from openactionproof.core import canonical, sha256
from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.observer import Observation, ObservationRequest

if Ed25519PrivateKey is not None:
    from openactionproof.public_observation import assess_signed_pair, authenticate_signed, key_id, observe_signed


class FixedObserver:
    def __init__(self, obs):
        self.obs = obs

    def observe(self, request):
        return self.obs


@unittest.skipIf(Ed25519PrivateKey is None, "optional public-key extra not installed")
class PublicObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.guard = DurableReplayGuard(Path(self.tmp.name) / "replay.db", initialize=True)
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key()
        self.expected = sha256(canonical("new"))
        self.b = ObservationRequest("observer", "target", "a"*64, 10, 20)
        self.a = ObservationRequest("observer", "target", "b"*64, 30, 40)
        self.before = Observation("observer", "target", self.b.challenge, 15, 0, sha256(canonical("old")))
        self.after = Observation("observer", "target", self.a.challenge, 35, 1, self.expected)
        self.be = self.sign(self.b, self.before)
        self.ae = self.sign(self.a, self.after)

    def sign(self, req, obs, key=None):
        return observe_signed(FixedObserver(obs), key or self.private, "task", self.expected, req)

    def pair(self, **kw):
        args = dict(guard=self.guard, public_key=self.public, task_id="task", expected=self.expected,
                    before_request=self.b, after_request=self.a, before_envelope=self.be,
                    after_envelope=self.ae, now_ns=36)
        args.update(kw)
        return assess_signed_pair(**args)

    def test_public_key_only_verification_and_replay(self):
        self.assertEqual(self.ae["key_id"], key_id(self.public))
        self.assertEqual(self.pair(), "STATE_MATCHED_UNATTRIBUTED")
        self.assertEqual(self.pair(guard=DurableReplayGuard(self.guard.path)), "INDETERMINATE")

    def test_wrong_key_and_key_substitution(self):
        other = Ed25519PrivateKey.generate()
        self.assertEqual(self.pair(public_key=other.public_key()), "INDETERMINATE")
        self.assertEqual(self.pair(after_envelope=self.sign(self.a, self.after, other)), "INDETERMINATE")
        self.assertEqual(self.pair(), "STATE_MATCHED_UNATTRIBUTED")

    def test_tampered_body_and_signature(self):
        altered = {**self.ae, "observation": {**self.ae["observation"], "revision": 2}}
        for e in (altered, {**self.ae, "signature": "0"*128}, {**self.ae, "key_id": "f"*64}):
            self.assertEqual(self.pair(after_envelope=e), "INDETERMINATE")
        self.assertEqual(self.pair(), "STATE_MATCHED_UNATTRIBUTED")

    def test_binding_and_freshness(self):
        for kw in ({"task_id":"other"}, {"expected":"f"*64}, {"now_ns":41}, {"after_request":replace(self.a, deadline_ns=39)}):
            self.assertEqual(self.pair(**kw), "INDETERMINATE")
        self.assertEqual(self.pair(), "STATE_MATCHED_UNATTRIBUTED")

    def test_schema_confusion_and_extra_fields(self):
        for e in ({**self.ae, "schema":"openactionproof.observation.hmac.v1"}, {**self.ae, "public_key":"untrusted"}):
            self.assertEqual(self.pair(after_envelope=e), "INDETERMINATE")

    def test_concurrent_replay(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.pair(), range(16)))
        self.assertEqual(results.count("STATE_MATCHED_UNATTRIBUTED"), 1)
        self.assertEqual(results.count("INDETERMINATE"), 15)

    def test_key_rotation_does_not_reset_replay(self):
        self.assertEqual(self.pair(), "STATE_MATCHED_UNATTRIBUTED")
        other = Ed25519PrivateKey.generate()
        self.assertEqual(self.pair(public_key=other.public_key(), before_envelope=self.sign(self.b, self.before, other),
                                   after_envelope=self.sign(self.a, self.after, other)), "INDETERMINATE")

    def test_missing_and_malformed(self):
        for envelope in (None, {}, {**self.ae, "signature": []}, {**self.ae, "observation": None}):
            self.assertIsNone(authenticate_signed(self.public, "task", self.expected, self.a, envelope, now_ns=36))
        self.assertEqual(self.pair(before_request=None), "INDETERMINATE")
        self.assertIsNone(authenticate_signed(self.public, "task", self.expected, None, self.ae, now_ns=36))

    def test_rfc8032_vector(self):
        seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        key = Ed25519PrivateKey.from_private_bytes(seed)
        expected_signature = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155" "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertEqual(key.sign(b""), expected_signature)
        key.public_key().verify(expected_signature, b"")
