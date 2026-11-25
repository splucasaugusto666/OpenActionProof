import concurrent.futures
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from openactionproof.economic import EconomicLedger
from openactionproof.economic_gateway import CostObservation, EconomicIntent, execute_budgeted


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'budget.db'
        self.ledger = EconomicLedger(self.path, currency='BRL', limit=100, initialize=True)
        self.intent = EconomicIntent('order-1', 'mock.write', 'a'*64, 'BRL', 60)
        self.calls = []

    def actor(self, intent):
        self.calls.append(intent.request_id)
        return 1  # untrusted claimed cost; never used

    def evidence(self, intent):
        return CostObservation(intent.request_id, intent.digest(), intent.currency, 40, 'b'*64)

    def run_gate(self, intent=None, execute=None, observe=None):
        return execute_budgeted(ledger=self.ledger, intent=intent or self.intent,
                                execute=execute or self.actor, observe=observe or self.evidence)

    def test_observed_not_claimed_cost(self):
        self.assertEqual(self.run_gate().status, 'COST_RECORDED')
        self.assertEqual(self.ledger.snapshot()['spent'], 40)
        self.assertEqual(self.run_gate().status, 'REPLAY:SETTLED')
        self.assertEqual(self.calls, ['order-1'])

    def test_denied_before_actor(self):
        self.assertEqual(self.run_gate(replace(self.intent, maximum=101)).status, 'DENIED')
        self.assertEqual(self.run_gate(replace(self.intent, currency='USD')).status, 'DENIED')
        self.assertEqual(self.calls, [])

    def test_missing_observation_retains_hold(self):
        self.assertEqual(self.run_gate(observe=lambda i: None).status, 'PENDING_RECONCILIATION')
        self.assertEqual(self.ledger.snapshot()['reserved'], 60)
        self.assertEqual(self.run_gate().status, 'REPLAY:RESERVED')
        self.assertEqual(len(self.calls), 1)

    def test_mismatched_observation_and_conflicting_retry(self):
        self.assertEqual(self.run_gate(observe=lambda i: replace(self.evidence(i), request_id='other')).status, 'PENDING_RECONCILIATION')
        self.assertEqual(self.run_gate(replace(self.intent, payload_sha256='c'*64)).status, 'DENIED')
        self.assertEqual(self.ledger.snapshot()['reserved'], 60)
        self.assertEqual(len(self.calls), 1)

    def test_overshoot_retains_hold(self):
        self.assertEqual(self.run_gate(observe=lambda i: replace(self.evidence(i), actual=61)).status, 'PENDING_RECONCILIATION')
        self.assertEqual(self.ledger.snapshot()['reserved'], 60)

    def test_actor_exception_observed_cost(self):
        def failed(i):
            self.actor(i)
            raise RuntimeError('lost response')
        result = self.run_gate(execute=failed)
        self.assertEqual((result.status, result.actor_status), ('COST_RECORDED', 'RAISED'))
        self.assertEqual(self.ledger.snapshot()['spent'], 40)

    def test_concurrent_replay(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(lambda _: self.run_gate().status, range(8)))
        self.assertEqual(statuses.count('COST_RECORDED'), 1)
        self.assertEqual(sum(s.startswith('REPLAY:') for s in statuses), 7)
        self.assertEqual(len(self.calls), 1)

    def test_missing_storage_no_dispatch(self):
        self.path.unlink()
        self.assertEqual(self.run_gate().status, 'STORAGE_UNAVAILABLE')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.path.exists())
