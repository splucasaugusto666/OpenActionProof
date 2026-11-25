from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from openactionproof.core import canonical, sha256
from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.observer import ObservationRequest
from openactionproof.observer_worker import read_authenticated
from openactionproof.verified_observation import assess_authenticated_pair, authenticate


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "state.sqlite3"
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)")
            conn.execute("INSERT INTO resource_state VALUES ('target', 0, 'old')")
            conn.commit()
        self.key = secrets.token_bytes(32)
        self.expected = sha256(canonical("new"))

    def request(self, duration_ns=5_000_000_000):
        start = time.time_ns()
        return ObservationRequest("observer", "target", secrets.token_hex(32), start, start + duration_ns)

    def read(self, req, **kwargs):
        return read_authenticated(self.db, self.key, "task", self.expected, req, **kwargs)

    def test_authenticated_worker_read(self):
        req = self.request()
        envelope = self.read(req)
        obs = authenticate(self.key, "task", self.expected, req, envelope, now_ns=time.time_ns())
        self.assertIsNotNone(obs)
        self.assertEqual(obs.revision, 0)
        self.assertEqual(obs.state_sha256, sha256(canonical("old")))
        self.assertNotIn(self.key.hex(), json.dumps(envelope))

    def test_end_to_end_actor_observer_and_durable_replay(self):
        before = self.request(2_000_000_000)
        be = self.read(before)
        self.assertIsNotNone(be)
        # Actor is a different process; no observation signing key is provided.
        subprocess.run([sys.executable, "-c", "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"UPDATE resource_state SET revision=1,value='new' WHERE resource='target'\"); c.commit(); c.close()", str(self.db)], check=True, timeout=5)
        delay = (before.deadline_ns - time.time_ns()) / 1_000_000_000
        if delay > 0:
            time.sleep(delay + 0.01)
        after = self.request()
        ae = self.read(after)
        self.assertIsNotNone(ae)
        storage = Path(self.tmp.name) / "replay.db"
        guard = DurableReplayGuard(storage, initialize=True)
        def evaluate(g):
            return assess_authenticated_pair(g, self.key, "task", self.expected, before, after, be, ae, now_ns=time.time_ns())
        self.assertEqual(evaluate(guard), "STATE_MATCHED_UNATTRIBUTED")
        self.assertEqual(evaluate(DurableReplayGuard(storage)), "INDETERMINATE")

    def test_missing_resource_or_db(self):
        req = self.request()
        self.assertIsNone(self.read(replace(req, resource="missing")))
        self.db.unlink()
        self.assertIsNone(self.read(self.request()))
        self.assertFalse(self.db.exists())

    def test_expired_and_future_requests_never_spawn(self):
        with patch("openactionproof.observer_worker.subprocess.run") as run:
            self.assertIsNone(self.read(ObservationRequest("observer", "target", "a"*64, 1, 2)))
            req = self.request()
            self.assertIsNone(self.read(replace(req, not_before_ns=req.deadline_ns)))
            run.assert_not_called()

    def test_timeout_and_bad_worker_output(self):
        with patch("openactionproof.observer_worker.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 1)):
            self.assertIsNone(self.read(self.request()))
        for data in (b"not json", b'{"a":1,"a":2}', b"x"*65537, b"{}"):
            with patch("openactionproof.observer_worker.subprocess.run", return_value=subprocess.CompletedProcess([], 0, data)):
                self.assertIsNone(self.read(self.request()))

    def test_worker_bad_payload_does_not_log_secret(self):
        req = self.request()
        payload = json.dumps({"key": self.key.hex(), "task_id": "task", "expected": self.expected, "request": {"invalid": True}}).encode()
        r = subprocess.run([sys.executable, "-m", "openactionproof.observer_worker", str(self.db), req.observer_id], input=payload, capture_output=True, timeout=5)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout + r.stderr, b"")

    def test_worker_ignores_ambient_import_paths_and_site_hooks(self):
        shadow = Path(self.tmp.name) / "shadow"
        package = shadow / "openactionproof"
        package.mkdir(parents=True)
        marker = shadow / "unexpected.txt"
        # Harmless sentinel, not a secret: prove neither shadow package nor
        # Python startup hook runs in the worker receiving the signing key.
        sentinel = f"from pathlib import Path; Path({str(marker)!r}).write_text('unexpected')\n"
        (package / "__init__.py").write_text(sentinel, encoding="utf-8")
        (package / "observer_worker.py").write_text(sentinel, encoding="utf-8")
        (shadow / "sitecustomize.py").write_text(sentinel, encoding="utf-8")
        cwd = Path.cwd()
        try:
            os.chdir(shadow)
            with patch.dict(os.environ, {"PYTHONPATH": str(shadow)}):
                self.assertIsNotNone(self.read(self.request()))
        finally:
            os.chdir(cwd)
        self.assertFalse(marker.exists())

    def test_invalid_request_or_timeout_fails_closed_without_spawn(self):
        with patch("openactionproof.observer_worker.subprocess.run") as run:
            self.assertIsNone(self.read(None))
            for timeout in (True, "1", None, float("nan"), float("inf"), 0, 31):
                self.assertIsNone(self.read(self.request(), timeout=timeout))
            run.assert_not_called()

    def test_key_not_in_command_line(self):
        with patch("openactionproof.observer_worker.subprocess.run", wraps=subprocess.run) as run:
            self.assertIsNotNone(self.read(self.request()))
            args, kwargs = run.call_args
            self.assertNotIn(self.key.hex(), " ".join(args[0]))
            self.assertIn(self.key.hex().encode(), kwargs["input"])


if __name__ == "__main__":
    unittest.main()
