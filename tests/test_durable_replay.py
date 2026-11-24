import concurrent.futures
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from openactionproof.attestation import Intent, seal
from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.http_lab import CASES, execute


class DurableReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "replay.sqlite3"
        self.key = secrets.token_bytes(32)
        self.receipt = execute(CASES[0])
        self.intent = Intent("normal", "observer-1", secrets.token_hex(32))
        self.envelope = seal(self.key, self.intent, self.receipt)

    def test_restart_and_explicit_provisioning(self):
        with self.assertRaises(sqlite3.Error):
            DurableReplayGuard(self.path)
        self.assertFalse(self.path.exists())
        guard = DurableReplayGuard(self.path, initialize=True)
        self.assertTrue(guard.accept(self.key, self.intent, self.envelope))
        self.assertFalse(DurableReplayGuard(self.path).accept(self.key, self.intent, self.envelope))
        with self.assertRaises(FileExistsError):
            DurableReplayGuard(self.path, initialize=True)

    def test_concurrent_connections_accept_once(self):
        DurableReplayGuard(self.path, initialize=True)
        def accept(_):
            return DurableReplayGuard(self.path).accept(self.key, self.intent, self.envelope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(accept, range(16))), 1)

    def test_separate_process_rejects_consumed_challenge(self):
        guard = DurableReplayGuard(self.path, initialize=True)
        self.assertTrue(guard.accept(self.key, self.intent, self.envelope))
        script = """import json, sys
from pathlib import Path
from openactionproof.attestation import Intent
from openactionproof.durable_replay import DurableReplayGuard
p = json.load(sys.stdin)
g = DurableReplayGuard(Path(p['path']))
print(g.accept(bytes.fromhex(p['key']), Intent(**p['intent']), p['envelope']))
"""
        payload = {"path": str(self.path), "key": self.key.hex(), "intent": self.intent.body(), "envelope": self.envelope}
        run = subprocess.run([sys.executable, "-c", script], input=json.dumps(payload), text=True, capture_output=True, timeout=10, check=True)
        self.assertEqual(run.stdout.strip(), "False")

    def test_invalid_mac_does_not_consume_challenge(self):
        guard = DurableReplayGuard(self.path, initialize=True)
        self.assertFalse(guard.accept(secrets.token_bytes(32), self.intent, self.envelope))
        self.assertTrue(guard.accept(self.key, self.intent, self.envelope))

    def test_capacity_persists_and_config_cannot_drift(self):
        guard = DurableReplayGuard(self.path, capacity=1, initialize=True)
        self.assertTrue(guard.accept(self.key, self.intent, self.envelope))
        another = Intent("normal", "observer-1", secrets.token_hex(32))
        self.assertFalse(DurableReplayGuard(self.path, capacity=1).accept(self.key, another, seal(self.key, another, self.receipt)))
        with self.assertRaises(ValueError):
            DurableReplayGuard(self.path, capacity=2)

    def test_missing_database_fails_closed(self):
        guard = DurableReplayGuard(self.path, initialize=True)
        self.path.unlink()
        self.assertFalse(guard.accept(self.key, self.intent, self.envelope))
        self.assertFalse(self.path.exists())

    def test_corrupt_database_fails_closed(self):
        guard = DurableReplayGuard(self.path, initialize=True)
        self.path.write_bytes(b"not a database")
        self.assertFalse(guard.accept(self.key, self.intent, self.envelope))


if __name__ == "__main__":
    unittest.main()
