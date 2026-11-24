import concurrent.futures
from dataclasses import replace
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory
import unittest

from openactionproof.core import canonical, sha256
from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.observer import Observation, ObservationRequest
from openactionproof.verified_observation import assess_authenticated_pair, observe_authenticated


class FixtureObserver:
    def __init__(self, obs):
        self.obs = obs

    def observe(self, request):
        return self.obs


class VerifiedObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'replay.db'
        self.guard = DurableReplayGuard(self.db, initialize=True)
        self.key = secrets.token_bytes(32)
        self.expected = sha256(canonical('new'))
        self.b = ObservationRequest('observer', 'target', 'a'*64, 10, 20)
        self.a = ObservationRequest('observer', 'target', 'b'*64, 30, 40)
        self.before = Observation('observer', 'target', self.b.challenge, 15, 0, sha256(canonical('old')))
        self.after = Observation('observer', 'target', self.a.challenge, 35, 1, self.expected)
        self.be = self.seal(self.b, self.before)
        self.ae = self.seal(self.a, self.after)

    def seal(self, req, obs):
        return observe_authenticated(FixtureObserver(obs), self.key, 'task', self.expected, req)

    def run_pair(self, **kw):
        args = dict(guard=self.guard, key=self.key, task_id='task', expected=self.expected,
                    before_request=self.b, after_request=self.a, before_envelope=self.be,
                    after_envelope=self.ae, now_ns=36)
        args.update(kw)
        return assess_authenticated_pair(**args)

    def test_valid_and_replay_after_reopen(self):
        self.assertEqual(self.run_pair(), 'STATE_MATCHED_UNATTRIBUTED')
        self.assertEqual(self.run_pair(guard=DurableReplayGuard(self.db)), 'INDETERMINATE')

    def test_wrong_key_task_goal_or_window(self):
        for kw in ({'key': secrets.token_bytes(32)}, {'task_id':'another'},
                   {'expected':'f'*64}, {'after_request':replace(self.a, deadline_ns=39)}, {'now_ns':41}):
            self.assertEqual(self.run_pair(**kw), 'INDETERMINATE')
        self.assertEqual(self.run_pair(), 'STATE_MATCHED_UNATTRIBUTED')

    def test_tampering_rejected(self):
        forged = {**self.ae, 'observation':{**self.ae['observation'], 'revision':2}}
        self.assertEqual(self.run_pair(after_envelope=forged), 'INDETERMINATE')
        self.assertEqual(self.run_pair(), 'STATE_MATCHED_UNATTRIBUTED')

    def test_invalid_pair_never_consumes_half(self):
        self.assertEqual(self.run_pair(after_envelope={}), 'INDETERMINATE')
        self.assertEqual(self.run_pair(), 'STATE_MATCHED_UNATTRIBUTED')

    def test_conflict_on_second_token_rolls_back_first(self):
        self.assertTrue(self.guard._consume_tokens((('observer', self.a.challenge),)))
        self.assertEqual(self.run_pair(), 'INDETERMINATE')
        self.assertTrue(self.guard._consume_tokens((('observer', self.b.challenge),)))

    def test_concurrent_pair_only_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.run_pair(), range(16)))
        self.assertEqual(results.count('STATE_MATCHED_UNATTRIBUTED'), 1)
        self.assertEqual(results.count('INDETERMINATE'), 15)

    def test_capacity_exhaustion_is_atomic(self):
        guard = DurableReplayGuard(Path(self.tmp.name)/'small.db', capacity=1, initialize=True)
        self.assertEqual(self.run_pair(guard=guard), 'INDETERMINATE')
        self.assertTrue(guard._consume_tokens((('observer', self.b.challenge),)))

    def test_authenticated_mismatch_is_not_success(self):
        ae = self.seal(self.a, replace(self.after, state_sha256=self.before.state_sha256))
        self.assertEqual(self.run_pair(after_envelope=ae), 'STATE_MISMATCH')
        self.assertEqual(self.run_pair(), 'INDETERMINATE')

    def test_missing_storage_denies_confirmation(self):
        self.db.unlink()
        self.assertEqual(self.run_pair(), 'INDETERMINATE')
        self.assertFalse(self.db.exists())


if __name__ == '__main__':
    unittest.main()
