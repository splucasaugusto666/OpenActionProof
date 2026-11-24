import concurrent.futures
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.tool_dispatch import DispatchLedger, dispatch_write
from openactionproof.tool_session import ToolOutcome, verify_tool_call


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'dispatch.db'
        self.ledger = DispatchLedger(self.path, initialize=True)
        self.calls = []

    def call(self, id='call1', resource='target', value='new'):
        return {'id':id, 'type':'function', 'function':{'name':'write_resource', 'arguments':json.dumps({'resource':resource,'value':value})}}

    def run_call(self, call=None, **kwargs):
        options = dict(ledger=self.ledger, scope='session1', permitted_resource='target', expected_value='new',
                       call=self.call() if call is None else call,
                       verify=lambda actor: (actor(), ToolOutcome('RETURNED','STATE_MATCHED_UNATTRIBUTED'))[1],
                       write=lambda r,v: self.calls.append((r,v)))
        options.update(kwargs)
        return dispatch_write(**options)

    def test_reopen_no_duplicate(self):
        self.assertEqual(self.run_call().status, 'CLAIMED')
        self.assertEqual(self.run_call(ledger=DispatchLedger(self.path)).status, 'ALREADY_CLAIMED')
        self.assertEqual(len(self.calls), 1)

    def test_same_id_different_digest(self):
        self.assertEqual(self.run_call().status, 'CLAIMED')
        self.assertEqual(self.run_call(self.call(value='other'), expected_value='other').status, 'CALL_ID_CONFLICT')
        self.assertEqual(len(self.calls), 1)

    def test_outside_intent_does_not_claim(self):
        for call in (self.call(resource='other'), self.call(value='other')):
            self.assertEqual(self.run_call(call).status, 'OUTSIDE_INTENT')
        self.assertEqual(self.run_call().status, 'CLAIMED')

    def test_bad_shapes(self):
        calls = [{}, {**self.call(), 'extra':True}, self.call(id='bad id')]
        for raw in ('{}', 'null', '{"resource":"target","resource":"target","value":"new"}', '{"resource":"target","value":true}', 'x'*65537):
            c = self.call(); c['function']['arguments'] = raw; calls.append(c)
        for call in calls:
            self.assertEqual(self.run_call(call).status, 'INVALID_CALL')
        self.assertEqual(self.calls, [])

    def test_concurrent_claims(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.run_call().status, range(16)))
        self.assertEqual(results.count('CLAIMED'), 1)
        self.assertEqual(results.count('ALREADY_CLAIMED'), 15)
        self.assertEqual(len(self.calls), 1)

    def test_failure_after_claim_no_auto_retry(self):
        def fail(actor):
            actor()
            raise RuntimeError('private data')
        self.assertEqual(self.run_call(verify=fail).status, 'CLAIMED_UNRESOLVED')
        self.assertEqual(self.run_call().status, 'ALREADY_CLAIMED')
        self.assertEqual(len(self.calls), 1)

    def test_missing_storage(self):
        self.path.unlink()
        self.assertEqual(self.run_call().status, 'STORAGE_UNAVAILABLE')
        self.assertFalse(self.path.exists())
        self.assertFalse(self.calls)

    def test_scope_separation(self):
        self.assertEqual(self.run_call().status, 'CLAIMED')
        self.assertEqual(self.run_call(scope='session2').status, 'CLAIMED')
        self.assertEqual(len(self.calls), 2)

    def test_end_to_end_authenticated_tool(self):
        state = Path(self.tmp.name)/'state.db'
        with closing(sqlite3.connect(state)) as conn:
            conn.execute('CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)')
            conn.execute("INSERT INTO resource_state VALUES ('target',0,'old')")
            conn.commit()
        guard = DurableReplayGuard(Path(self.tmp.name)/'replay.db', initialize=True)
        key = secrets.token_bytes(32)
        def write(resource, value):
            with closing(sqlite3.connect(state)) as conn:
                conn.execute('UPDATE resource_state SET revision=revision+1,value=? WHERE resource=?',(value,resource))
                conn.commit()
        def verify(actor):
            return verify_tool_call(database=state, guard=guard, key=key, task_id='task', observer_id='observer',
                                    resource='target', expected_value='new', actor=actor, window_seconds=1.0)
        r = self.run_call(write=write,verify=verify)
        self.assertEqual(r.outcome.verdict, 'STATE_MATCHED_UNATTRIBUTED')
        self.assertEqual(self.run_call(write=write,verify=verify).status, 'ALREADY_CLAIMED')
        with closing(sqlite3.connect(state)) as conn:
            self.assertEqual(conn.execute('SELECT revision,value FROM resource_state').fetchone(),(1,'new'))
