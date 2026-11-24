import concurrent.futures
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openactionproof.core import canonical, sha256
from openactionproof.tool_dispatch import DispatchLedger, dispatch_write
from openactionproof.tool_session import ToolOutcome


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'dispatch.db'
        self.ledger = DispatchLedger(self.path, initialize=True)
        self.digest = sha256(canonical({'name':'write_resource','arguments':{'resource':'target','value':'new'}}))
        self.outcome = ToolOutcome('RETURNED', 'STATE_MATCHED_UNATTRIBUTED')
        self.effects = []

    def dispatch(self, verifier=None):
        return dispatch_write(ledger=self.ledger, scope='scope', permitted_resource='target', expected_value='new',
                              call={'id':'call','type':'function','function':{'name':'write_resource','arguments':json.dumps({'resource':'target','value':'new'})}},
                              verify=verifier or (lambda actor: (actor(), self.outcome)[1]),
                              write=lambda r,v: self.effects.append((r,v)))

    def test_recorded_outcome_persists_and_duplicate_returns_record(self):
        self.assertEqual(self.dispatch().outcome, self.outcome)
        self.ledger = DispatchLedger(self.path)
        record = self.ledger.lookup('scope','call')
        self.assertEqual((record.status, record.outcome), ('OUTCOME_RECORDED', self.outcome))
        duplicate = self.dispatch()
        self.assertEqual((duplicate.status, duplicate.outcome), ('ALREADY_CLAIMED', self.outcome))
        self.assertEqual(len(self.effects), 1)

    def test_interrupted_process_is_not_retried(self):
        script = """import os,sys
from pathlib import Path
from openactionproof.tool_dispatch import DispatchLedger
assert DispatchLedger(Path(sys.argv[1])).claim('scope','call',sys.argv[2]) == 'CLAIMED'
os._exit(73)
"""
        proc = subprocess.run([sys.executable,'-c',script,str(self.path),self.digest], timeout=5)
        self.assertEqual(proc.returncode,73)
        self.assertEqual(self.ledger.lookup('scope','call').status,'PENDING_RECONCILIATION')
        self.assertEqual(self.dispatch().status,'ALREADY_CLAIMED')
        self.assertFalse(self.effects)

    def test_exception_is_durably_unresolved(self):
        def fail(actor):
            actor()
            raise RuntimeError('secret')
        self.assertEqual(self.dispatch(fail).status,'CLAIMED_UNRESOLVED')
        record = DispatchLedger(self.path).lookup('scope','call')
        self.assertEqual(record.status,'UNRESOLVED')
        self.assertIsNone(record.outcome)
        self.assertNotIn('secret', repr(record))
        self.assertEqual(self.dispatch().status,'ALREADY_CLAIMED')
        self.assertEqual(len(self.effects),1)

    def test_record_failure_after_effect_never_returns_success(self):
        with patch.object(self.ledger,'record',return_value=False):
            self.assertEqual(self.dispatch().status,'CLAIMED_UNRESOLVED')
        self.assertEqual(self.ledger.lookup('scope','call').status,'PENDING_RECONCILIATION')
        self.assertEqual(self.dispatch().status,'ALREADY_CLAIMED')
        self.assertEqual(len(self.effects),1)

    def test_result_is_write_once_and_bound_to_digest(self):
        self.assertEqual(self.ledger.claim('scope','call',self.digest),'CLAIMED')
        self.assertFalse(self.ledger.record('scope','call','f'*64,self.outcome))
        self.assertTrue(self.ledger.record('scope','call',self.digest,self.outcome))
        self.assertFalse(self.ledger.record('scope','call',self.digest,None))
        self.assertEqual(self.ledger.lookup('scope','call').outcome,self.outcome)

    def test_concurrent_recording_only_one_commit(self):
        self.ledger.claim('scope','call',self.digest)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: DispatchLedger(self.path).record('scope','call',self.digest,self.outcome),range(16)))
        self.assertEqual(sum(results),1)

    def test_explicit_legacy_migration_preserves_unresolved_claim(self):
        path = Path(self.tmp.name)/'legacy.db'
        with closing(sqlite3.connect(path)) as c:
            c.execute('CREATE TABLE dispatch(scope TEXT NOT NULL, call_id TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(scope,call_id))')
            c.execute('INSERT INTO dispatch VALUES (?,?,?)',('scope','call',self.digest))
            c.commit()
        with self.assertRaises(ValueError):
            DispatchLedger(path)
        upgraded = DispatchLedger(path,upgrade=True)
        self.assertEqual(upgraded.lookup('scope','call').status,'PENDING_RECONCILIATION')
        self.assertEqual(upgraded.claim('scope','call',self.digest),'ALREADY_CLAIMED')
        with self.assertRaises(ValueError):
            DispatchLedger(path,upgrade=True)

    def test_missing_outcome_table_fails_closed(self):
        with closing(sqlite3.connect(self.path)) as c:
            c.execute('DROP TABLE dispatch_outcome'); c.commit()
        self.assertEqual(self.dispatch().status,'STORAGE_UNAVAILABLE')
        self.assertEqual(self.ledger.lookup('scope','call').status,'STORAGE_UNAVAILABLE')
        self.assertFalse(self.effects)

    def test_invalid_verifier_outcome_is_not_saved_as_success(self):
        result = self.dispatch(lambda actor: ToolOutcome('NOT_INVOKED','STATE_MATCHED_UNATTRIBUTED'))
        self.assertEqual(result.status,'CLAIMED_UNRESOLVED')
        self.assertEqual(self.ledger.lookup('scope','call').status,'UNRESOLVED')

    def test_not_found_and_invalid_are_distinct(self):
        self.assertEqual(self.ledger.lookup('scope','missing').status,'NOT_FOUND')
        self.assertEqual(self.ledger.lookup('scope','bad id').status,'INVALID_CALL')
