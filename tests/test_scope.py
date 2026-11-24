from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.scope import scope_digest, verify_scoped_write


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "state.db"
        self.initial = {"target": (0, "old"), "other": (0, "untouched")}
        self.execute("CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)",
                     "INSERT INTO resource_state VALUES ('target',0,'old')",
                     "INSERT INTO resource_state VALUES ('other',0,'untouched')")
        self.guard = DurableReplayGuard(Path(self.tmp.name) / "replay.db", initialize=True)
        self.key = secrets.token_bytes(32)

    def execute(self, *statements):
        with closing(sqlite3.connect(self.db)) as conn:
            for statement in statements:
                conn.execute(statement)
            conn.commit()

    def verify(self, actor, **changes):
        args = dict(database=self.db, guard=self.guard, key=self.key, task_id="task", observer_id="observer",
                    initial=self.initial, target="target", desired="new", actor=actor)
        args.update(changes)
        return verify_scoped_write(**args)

    def write(self):
        self.execute("UPDATE resource_state SET revision=revision+1,value='new' WHERE resource='target'")

    def test_exact_scoped_write(self):
        result = self.verify(self.write)
        self.assertEqual((result.actor_status, result.verdict), ("RETURNED", "STATE_MATCHED_UNATTRIBUTED"))

    def test_collateral_write(self):
        def actor():
            self.write()
            self.execute("UPDATE resource_state SET revision=1,value='changed' WHERE resource='other'")
        self.assertEqual(self.verify(actor).verdict, "STATE_MISMATCH")

    def test_duplicate_write(self):
        self.assertEqual(self.verify(lambda: (self.write(), self.write())).verdict, "STATE_MISMATCH")

    def test_changed_initial_state_does_not_invoke(self):
        self.execute("UPDATE resource_state SET revision=1 WHERE resource='other'")
        result = self.verify(lambda: self.fail("actor invoked"))
        self.assertEqual((result.actor_status, result.verdict), ("NOT_INVOKED", "PRECONDITION_MISMATCH"))

    def test_insert_unexpected_row(self):
        def actor():
            self.write()
            self.execute("INSERT INTO resource_state VALUES ('unexpected',0,'extra')")
        self.assertEqual(self.verify(actor).verdict, "STATE_MISMATCH")

    def test_error_after_commit_keeps_actor_status_separate(self):
        def actor():
            self.write()
            raise RuntimeError("private information")
        result = self.verify(actor)
        self.assertEqual((result.actor_status, result.verdict), ("RAISED", "STATE_MATCHED_UNATTRIBUTED"))

    def test_missing_initial_db_no_invocation(self):
        self.db.unlink()
        result = self.verify(lambda: self.fail("actor invoked"))
        self.assertEqual((result.actor_status, result.verdict), ("NOT_INVOKED", "INDETERMINATE"))
        self.assertFalse(self.db.exists())

    def test_invalid_scope_and_order_independence(self):
        self.assertEqual(scope_digest(self.initial), scope_digest(dict(reversed(list(self.initial.items())))))
        for initial in ({}, {"target": (True, "old")}, {"target": (0, "x" * 16385)}):
            with self.assertRaises(ValueError):
                self.verify(lambda: self.fail("actor invoked"), initial=initial)
        with self.assertRaises(ValueError):
            self.verify(lambda: self.fail("actor invoked"), desired="old")
