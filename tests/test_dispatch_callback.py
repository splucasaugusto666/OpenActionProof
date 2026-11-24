"""Regression tests for buggy synchronous verifier adapters."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openactionproof.tool_dispatch import DispatchLedger, dispatch_write
from openactionproof.tool_session import ToolOutcome


class DispatchCallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = DispatchLedger(Path(self.tmp.name) / "ledger.db", initialize=True)
        self.effects = []
        self.good = ToolOutcome("RETURNED", "STATE_MATCHED_UNATTRIBUTED")

    def dispatch(self, verify, write=None):
        return dispatch_write(ledger=self.ledger, scope="session", permitted_resource="target", expected_value="new",
                              call={"id":"call", "type":"function", "function":{"name":"write_resource", "arguments":json.dumps({"resource":"target", "value":"new"})}},
                              verify=verify, write=write or (lambda r, v: self.effects.append((r, v))))

    def test_duplicate_callback_rejected_even_if_adapter_swallows_error(self):
        def verify(actor):
            actor()
            with self.assertRaises(RuntimeError):
                actor()
            return self.good
        self.assertEqual(self.dispatch(verify).status, "CLAIMED_UNRESOLVED")
        self.assertEqual(len(self.effects), 1)

    def test_claim_without_invocation_is_unresolved(self):
        self.assertEqual(self.dispatch(lambda actor: self.good).status, "CLAIMED_UNRESOLVED")
        self.assertFalse(self.effects)

    def test_no_invocation_report_is_accepted_without_effect(self):
        result = self.dispatch(lambda actor: ToolOutcome("NOT_INVOKED", "INDETERMINATE"))
        self.assertEqual(result.status, "CLAIMED")
        self.assertFalse(self.effects)

    def test_delayed_callback_cannot_execute(self):
        saved = []
        def verify(actor):
            saved.append(actor)
            return ToolOutcome("NOT_INVOKED", "INDETERMINATE")
        self.dispatch(verify)
        with self.assertRaises(RuntimeError):
            saved[0]()
        self.assertFalse(self.effects)

    def test_cross_thread_callback_cannot_execute(self):
        def verify(actor):
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(RuntimeError):
                    pool.submit(actor).result(timeout=2)
            return ToolOutcome("NOT_INVOKED", "INDETERMINATE")
        self.assertEqual(self.dispatch(verify).status, "CLAIMED_UNRESOLVED")
        self.assertFalse(self.effects)

    def test_writer_exception_cannot_be_reported_as_returned(self):
        def write(r, v):
            self.effects.append((r, v))
            raise ValueError("private information")
        def verify(actor):
            with self.assertRaises(ValueError):
                actor()
            return self.good
        self.assertEqual(self.dispatch(verify, write).status, "CLAIMED_UNRESOLVED")
        self.assertEqual(len(self.effects), 1)
