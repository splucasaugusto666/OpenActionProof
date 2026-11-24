from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.tool_session import verify_tool_call


class ToolSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'state.db'
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)')
            c.execute("INSERT INTO resource_state VALUES ('target', 0, 'old')")
            c.commit()
        self.guard = DurableReplayGuard(Path(self.tmp.name) / 'replay.db', initialize=True)
        self.key = secrets.token_bytes(32)

    def run_tool(self, actor, **kwargs):
        options = dict(database=self.db, guard=self.guard, key=self.key, task_id='task', observer_id='observer',
                       resource='target', expected_value='new', actor=actor, window_seconds=1.0)
        options.update(kwargs)
        return verify_tool_call(**options)

    def write(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("UPDATE resource_state SET revision=revision+1,value='new' WHERE resource='target'")
            c.commit()

    def test_write_and_preexisting(self):
        result = self.run_tool(self.write)
        self.assertEqual((result.actor_status, result.verdict), ('RETURNED', 'STATE_MATCHED_UNATTRIBUTED'))
        self.assertEqual(self.run_tool(lambda: None).verdict, 'STATE_PREEXISTING')

    def test_claim_without_effect(self):
        self.assertEqual(self.run_tool(lambda: 'success').verdict, 'STATE_MISMATCH')

    def test_error_after_write_not_actor_confirmation(self):
        def actor():
            self.write()
            raise RuntimeError('private data')
        result = self.run_tool(actor)
        self.assertEqual((result.actor_status, result.verdict), ('RAISED', 'STATE_MATCHED_UNATTRIBUTED'))
        self.assertNotIn('private data', repr(result))

    def test_missing_initial_observation_never_invokes(self):
        with patch('openactionproof.tool_session.read_authenticated', return_value=None):
            result = self.run_tool(lambda: self.fail('actor invoked'))
        self.assertEqual((result.actor_status, result.verdict), ('NOT_INVOKED', 'INDETERMINATE'))

    def test_invalid_inputs_never_invoke_actor(self):
        for kw in ({'task_id':'bad id'}, {'key':b'weak'}, {'resource':'bad resource'}, {'window_seconds':float('nan')}):
            with self.assertRaises(ValueError):
                self.run_tool(lambda: self.fail('actor invoked'), **kw)

    def test_missing_post_state_is_indeterminate(self):
        def actor():
            self.db.unlink()
        self.assertEqual(self.run_tool(actor).verdict, 'INDETERMINATE')
