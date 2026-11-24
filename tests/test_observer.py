from dataclasses import asdict, replace
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from openactionproof.core import canonical, sha256
from openactionproof.observer import Observation, ObservationRequest, SQLiteObserver, assess, validate


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.b = ObservationRequest("observer", "target", "a" * 64, 10, 20)
        self.a = ObservationRequest("observer", "target", "b" * 64, 30, 40)
        self.expected = sha256(canonical("new"))
        self.before = Observation("observer", "target", self.b.challenge, 15, 0, sha256(canonical("old")))
        self.after = Observation("observer", "target", self.a.challenge, 35, 1, self.expected)

    def result(self, before=None, after=None, now=36):
        return assess(self.b, self.a, self.before if before is None else before,
                      self.after if after is None else after, self.expected, now_ns=now)

    def test_matching_state_never_attributes_actor(self):
        self.assertEqual(self.result(), "STATE_MATCHED_UNATTRIBUTED")

    def test_stale_future_and_expired(self):
        for ts in (29, 37, 41):
            self.assertEqual(self.result(after=replace(self.after, observed_ns=ts)), "INDETERMINATE")
        self.assertEqual(self.result(now=41), "INDETERMINATE")

    def test_wrong_binding(self):
        for field, value in (("observer_id", "fake"), ("resource", "other"), ("challenge", self.b.challenge)):
            self.assertEqual(self.result(after=replace(self.after, **{field: value})), "INDETERMINATE")

    def test_missing_observation(self):
        self.assertEqual(assess(self.b, self.a, self.before, None, self.expected, now_ns=36), "INDETERMINATE")

    def test_revision_rollback_or_unversioned_change(self):
        self.assertEqual(self.result(after=replace(self.after, revision=0)), "INDETERMINATE")
        self.assertEqual(self.result(before=replace(self.before, revision=2)), "INDETERMINATE")

    def test_preexisting_and_mismatch(self):
        self.assertEqual(self.result(before=replace(self.before, state_sha256=self.expected)), "STATE_PREEXISTING")
        self.assertEqual(self.result(after=replace(self.after, state_sha256=self.before.state_sha256)), "STATE_MISMATCH")

    def test_reused_or_overlapping_request(self):
        for req in (replace(self.a, challenge=self.b.challenge), replace(self.a, not_before_ns=19)):
            self.assertEqual(assess(self.b, req, self.before, self.after, self.expected, now_ns=36), "INDETERMINATE")

    def test_separate_process_sqlite_observer(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)")
                conn.execute("INSERT INTO resource_state VALUES ('target', 0, 'old')")
            def read():
                start = time.time_ns()
                req = ObservationRequest("observer", "target", secrets.token_hex(32), start, start + 5_000_000_000)
                run = subprocess.run([sys.executable, "-m", "openactionproof.observer", str(db), "observer"],
                                     input=json.dumps(asdict(req)), text=True, capture_output=True, check=True, timeout=5)
                obs = Observation(**json.loads(run.stdout))
                self.assertTrue(validate(req, obs, time.time_ns()))
                return obs
            before = read()
            actor = subprocess.run([sys.executable, "-c", "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"UPDATE resource_state SET revision=1,value='new' WHERE resource='target'\"); c.commit(); c.close()", str(db)], check=True, timeout=5)
            after = read()
            self.assertEqual((before.revision, after.revision), (0, 1))
            self.assertEqual(after.state_sha256, self.expected)
            self.assertNotEqual(before.challenge, after.challenge)

    def test_read_only_missing_db(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "missing.db"
            start = time.time_ns()
            req = ObservationRequest("observer", "target", secrets.token_hex(32), start, start+5_000_000_000)
            with self.assertRaises(sqlite3.Error):
                SQLiteObserver(db, "observer").observe(req)
            self.assertFalse(db.exists())


if __name__ == "__main__":
    unittest.main()
