from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    Ed25519PrivateKey = None

from openactionproof.core import canonical, sha256
from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.observer import Observation, ObservationRequest

if Ed25519PrivateKey is not None:
    from openactionproof.key_policy import KeyGrant, KeyPolicy, assess_authorized_pair
    from openactionproof.public_observation import observe_signed


class FixedObserver:
    def __init__(self, observation):
        self.observation = observation

    def observe(self, request):
        return self.observation


@unittest.skipIf(Ed25519PrivateKey is None, "optional public-key extra not installed")
class KeyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.guard = DurableReplayGuard(Path(self.tmp.name) / "replay.db", initialize=True)
        self.old = Ed25519PrivateKey.generate()
        self.new = Ed25519PrivateKey.generate()
        self.expected = sha256(canonical("new"))
        self.b = ObservationRequest("observer", "target", "a"*64, 10, 20)
        self.a = ObservationRequest("observer", "target", "b"*64, 30, 40)
        self.grant = KeyGrant("observer", self.old.public_key(), 0, 50)

    def envelopes(self, key):
        b = Observation("observer", "target", self.b.challenge, 15, 0, sha256(canonical("old")))
        a = Observation("observer", "target", self.a.challenge, 35, 1, self.expected)
        return tuple(observe_signed(FixedObserver(obs), key, "task", self.expected, req)
                     for obs, req in ((b, self.b), (a, self.a)))

    def assess(self, grants, envelopes=None, now=36):
        be, ae = self.envelopes(self.old) if envelopes is None else envelopes
        return assess_authorized_pair(self.guard, KeyPolicy(grants), "task", self.expected,
                                      self.b, self.a, be, ae, now_ns=now)

    def test_authorized_pair_and_replay(self):
        self.assertEqual(self.assess((self.grant,)), "STATE_MATCHED_UNATTRIBUTED")
        self.assertEqual(self.assess((self.grant,)), "INDETERMINATE")

    def test_revocation_denies_historical_signature(self):
        self.assertEqual(self.assess((replace(self.grant, revoked=True),)), "INDETERMINATE")
        self.assertEqual(self.assess((self.grant,)), "STATE_MATCHED_UNATTRIBUTED")

    def test_window_must_be_covered_in_full(self):
        for grant in (replace(self.grant, valid_from_ns=11), replace(self.grant, valid_until_ns=40)):
            self.assertEqual(self.assess((grant,)), "INDETERMINATE")
        self.assertEqual(self.assess((self.grant,), now=50), "INDETERMINATE")
        self.assertEqual(self.assess((replace(self.grant, valid_from_ns=10, valid_until_ns=41),)), "STATE_MATCHED_UNATTRIBUTED")

    def test_observer_binding(self):
        self.assertEqual(self.assess((replace(self.grant, observer_id="other"),)), "INDETERMINATE")
        self.assertEqual(self.assess((self.grant,)), "STATE_MATCHED_UNATTRIBUTED")

    def test_untrusted_key_and_mixed_pair(self):
        old = self.envelopes(self.old)
        new = self.envelopes(self.new)
        self.assertEqual(self.assess((self.grant,), new), "INDETERMINATE")
        grants = (self.grant, KeyGrant("observer", self.new.public_key(), 0, 50))
        self.assertEqual(self.assess(grants, (old[0], new[1])), "INDETERMINATE")
        self.assertEqual(self.assess(grants, new), "STATE_MATCHED_UNATTRIBUTED")

    def test_rotation_preserves_replay_scope(self):
        self.assertEqual(self.assess((self.grant,)), "STATE_MATCHED_UNATTRIBUTED")
        grants = (replace(self.grant, revoked=True), KeyGrant("observer", self.new.public_key(), 0, 50))
        self.assertEqual(self.assess(grants, self.envelopes(self.new)), "INDETERMINATE")

    def test_invalid_policy_and_grants(self):
        for grant in ({"observer_id":"bad id"}, {"valid_from_ns":True}, {"valid_until_ns":0}, {"revoked":1}):
            with self.assertRaises(ValueError):
                replace(self.grant, **grant)
        for grants in ([self.grant], (self.grant, self.grant), (None,)):
            with self.assertRaises(ValueError):
                KeyPolicy(grants)

    def test_malformed_envelopes_and_empty_policy(self):
        self.assertEqual(self.assess((), self.envelopes(self.old)), "INDETERMINATE")
        self.assertEqual(self.assess((self.grant,), ({}, None)), "INDETERMINATE")
        self.assertEqual(self.assess((self.grant,)), "STATE_MATCHED_UNATTRIBUTED")
