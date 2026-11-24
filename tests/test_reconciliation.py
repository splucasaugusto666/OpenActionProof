from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openactionproof.core import canonical, sha256
from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.reconciliation import reconcile_write
from openactionproof.tool_dispatch import DispatchLedger
from openactionproof.tool_session import ToolOutcome


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.db = root / 'state.db'
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)')
            c.execute("INSERT INTO resource_state VALUES ('target',0,'old')")
            c.commit()
        self.ledger = DispatchLedger(root / 'dispatch.db', initialize=True)
        self.guard = DurableReplayGuard(root / 'replay.db', initialize=True)
        self.key = secrets.token_bytes(32)
        self.digest = sha256(canonical({'name':'write_resource','arguments':{'resource':'target','value':'new'}}))
        self.ledger.claim('scope','call',self.digest)

    def reconcile(self, **kw):
        args = dict(ledger=self.ledger, guard=self.guard, database=self.db, key=self.key,
                    scope='scope', call_id='call', observer_id='observer', resource='target', expected_value='new')
        args.update(kw)
        return reconcile_write(**args)

    def test_pending_matches_without_attribution_or_journal_change(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("UPDATE resource_state SET revision=1,value='new'")
            c.commit()
        r = self.reconcile()
        self.assertEqual((r.historical.status, r.current, r.revision), ('PENDING_RECONCILIATION','CURRENT_STATE_MATCHES_UNATTRIBUTED',1))
        self.assertEqual(self.ledger.lookup('scope','call').status,'PENDING_RECONCILIATION')
        self.assertEqual(self.ledger.claim('scope','call',self.digest),'ALREADY_CLAIMED')

    def test_current_mismatch_does_not_authorize_retry(self):
        self.assertEqual(self.reconcile().current,'CURRENT_STATE_DIFFERS')
        self.assertEqual(self.ledger.claim('scope','call',self.digest),'ALREADY_CLAIMED')

    def test_historical_record_separate_from_current(self):
        self.ledger.record('scope','call',self.digest,ToolOutcome('RETURNED','STATE_MATCHED_UNATTRIBUTED'))
        r = self.reconcile()
        self.assertEqual(r.historical.outcome.verdict,'STATE_MATCHED_UNATTRIBUTED')
        self.assertEqual(r.current,'CURRENT_STATE_DIFFERS')

    def test_unknown_or_wrong_intent_never_observes(self):
        with patch('openactionproof.reconciliation.read_authenticated') as read:
            self.assertEqual(self.reconcile(call_id='unknown').historical.status,'NOT_FOUND')
            self.assertEqual(self.reconcile(expected_value='wrong').historical.status,'CALL_ID_CONFLICT')
            self.assertEqual(self.reconcile(resource='other').historical.status,'CALL_ID_CONFLICT')
            read.assert_not_called()

    def test_missing_observer(self):
        self.db.unlink()
        self.assertEqual(self.reconcile().current,'INDETERMINATE')
        self.assertFalse(self.db.exists())

    def test_storage_exhaustion(self):
        guard = DurableReplayGuard(Path(self.tmp.name)/'small.db',capacity=1,initialize=True)
        self.assertEqual(self.reconcile(guard=guard).current,'CURRENT_STATE_DIFFERS')
        self.assertEqual(self.reconcile(guard=guard).current,'INDETERMINATE')

    def test_missing_dispatch_storage_never_observes(self):
        self.ledger.path.unlink()
        with patch('openactionproof.reconciliation.read_authenticated') as read:
            self.assertEqual(self.reconcile().historical.status,'STORAGE_UNAVAILABLE')
            read.assert_not_called()

    def test_malformed_or_weak_configuration(self):
        for kw in ({'key':b'weak'},{'scope':'bad scope'},{'timeout':float('nan')}):
            with self.assertRaises(ValueError):
                self.reconcile(**kw)
