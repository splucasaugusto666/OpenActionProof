import concurrent.futures
import tempfile
import sqlite3
import unittest
from pathlib import Path
from openactionproof.economic import BudgetError, EconomicLedger


class EconomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'budget.db'
        self.ledger = EconomicLedger(self.path, currency='BRL', limit=100, initialize=True)
        self.intent = 'a' * 64
        self.evidence = 'b' * 64

    def test_reserve_settle(self):
        self.assertEqual(self.ledger.reserve('a', self.intent, 80), 'CREATED')
        self.assertEqual(self.ledger.snapshot()['available'], 20)
        self.assertEqual(self.ledger.settle('a', 60, self.evidence), 'SETTLED')
        self.assertEqual(self.ledger.snapshot(), dict(currency='BRL', limit=100, reserved=0, spent=60, available=40))

    def test_release(self):
        self.ledger.reserve('a', self.intent, 100)
        self.assertEqual(self.ledger.release('a', self.evidence), 'RELEASED')
        self.assertEqual(self.ledger.snapshot()['available'], 100)

    def test_replay_and_conflict(self):
        self.ledger.reserve('a', self.intent, 50)
        self.assertEqual(self.ledger.reserve('a', self.intent, 50), 'REPLAY:RESERVED')
        for digest, amount in [('c'*64, 50), (self.intent, 51)]:
            with self.assertRaises(BudgetError):
                self.ledger.reserve('a', digest, amount)
        self.ledger.settle('a', 30, self.evidence)
        self.assertEqual(self.ledger.settle('a', 30, self.evidence), 'REPLAY:SETTLED')
        self.assertEqual(self.ledger.reserve('a', self.intent, 50), 'REPLAY:SETTLED')
        with self.assertRaises(BudgetError):
            self.ledger.release('a', self.evidence)

    def test_insufficient_and_overshoot_hold(self):
        self.ledger.reserve('a', self.intent, 80)
        with self.assertRaises(BudgetError):
            self.ledger.reserve('b', self.intent, 21)
        with self.assertRaises(BudgetError):
            self.ledger.settle('a', 81, self.evidence)
        self.assertEqual(self.ledger.snapshot()['reserved'], 80)

    def test_restart_and_configuration(self):
        self.ledger.reserve('a', self.intent, 40)
        reopened = EconomicLedger(self.path, currency='BRL', limit=100)
        self.assertEqual(reopened.reserve('a', self.intent, 40), 'REPLAY:RESERVED')
        for currency, limit in [('USD',100), ('BRL',101)]:
            with self.assertRaises(BudgetError):
                EconomicLedger(self.path, currency=currency, limit=limit)

    def test_missing_storage_fails_closed(self):
        self.ledger.reserve('a', self.intent, 40)
        self.path.unlink()
        with self.assertRaises(sqlite3.Error):
            self.ledger.reserve('a', self.intent, 40)
        with self.assertRaises(sqlite3.Error):
            EconomicLedger(self.path, currency='BRL', limit=100)
        self.assertFalse(self.path.exists())

    def test_no_reinitialize_or_empty_schema(self):
        with self.assertRaises(FileExistsError):
            EconomicLedger(self.path, currency='BRL', limit=100, initialize=True)
        other = self.path.parent / 'empty.db'
        other.touch()
        with self.assertRaises(BudgetError):
            EconomicLedger(other, currency='BRL', limit=100)

    def test_invalid_inputs(self):
        for amount in [True, 1.5, -1, 0, 10**16]:
            with self.assertRaises(BudgetError):
                self.ledger.reserve('a', self.intent, amount)
        for request, digest in [('',self.intent),('a','bad'),('x y',self.intent)]:
            with self.assertRaises(BudgetError):
                self.ledger.reserve(request, digest, 1)
        with self.assertRaises(BudgetError):
            self.ledger.release('unknown', self.evidence)
        self.assertEqual(self.ledger.snapshot()['available'], 100)

    def test_concurrent_cap(self):
        def attempt(i):
            try:
                return self.ledger.reserve(str(i), self.intent, 30)
            except BudgetError:
                return 'DENIED'
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))
        self.assertEqual(results.count('CREATED'), 3)
        self.assertEqual(results.count('DENIED'), 5)
        self.assertEqual(self.ledger.snapshot()['available'], 10)

    def test_concurrent_replay(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.ledger.reserve('same', self.intent, 30), range(8)))
        self.assertEqual(results.count('CREATED'), 1)
        self.assertEqual(results.count('REPLAY:RESERVED'), 7)
        self.assertEqual(self.ledger.snapshot()['reserved'], 30)


if __name__ == '__main__':
    unittest.main()
