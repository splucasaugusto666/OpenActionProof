import unittest
from openactionproof.http_lab import CASES, Store, benchmark, check_receipt, execute, request, service


class HTTPConformanceTests(unittest.TestCase):
    def test_all_fixture_verdicts(self):
        for case in CASES:
            with self.subTest(case=case.name):
                receipt = execute(case)
                self.assertEqual(receipt["verdict"], case.expected)
                self.assertTrue(check_receipt(receipt))

    def test_tampered_receipt(self):
        receipt = execute(CASES[0])
        receipt["verdict"] = "FALSE_SUCCESS"
        self.assertFalse(check_receipt(receipt))

    def test_confusion_matrix_conservation(self):
        report = benchmark()
        self.assertEqual(report["exact_verdict_matches"], len(CASES))
        for metric in report["metrics"].values():
            self.assertEqual(sum(metric[k] for k in ("tp", "fp", "tn", "fn")), len(CASES))

    def test_lost_ack_and_deduplication(self):
        receipt = execute(next(c for c in CASES if c.name == "retry_idempotent"))
        self.assertIsNone(receipt["attempts"][0]["status"])
        self.assertEqual(receipt["after"]["counts"]["target"], 1)
        self.assertEqual(len(receipt["after"]["events"]), 1)

    def test_actual_socket_timeout(self):
        with service(Store()) as port:
            with self.assertRaises(TimeoutError):
                request(port, "POST", "/action", {"mode": "timeout", "resource": "target", "key": "t"}, timeout=0.03)
            status, state = request(port, "GET", "/state")
            self.assertEqual(status, 200)
            self.assertEqual(state["counts"]["target"], 1)

    def test_settle_consumes_body_and_rejects_invalid_payload(self):
        with service(Store()) as port:
            status, _ = request(port, "POST", "/action", {"mode": "queued", "resource": "target", "key": "a"})
            self.assertEqual(status, 202)
            status, _ = request(port, "POST", "/settle", {"unexpected": "x" * 8192})
            self.assertEqual(status, 400)
            _, state = request(port, "GET", "/state")
            self.assertEqual(state["pending"], 1)
            self.assertEqual(state["counts"]["target"], 0)
            status, _ = request(port, "POST", "/settle", {})
            self.assertEqual(status, 200)
            _, state = request(port, "GET", "/state")
            self.assertEqual(state["counts"]["target"], 1)

    def test_malformed_action_does_not_mutate_store(self):
        with service(Store()) as port:
            for data in ({}, {"mode": "unknown", "resource": "target", "key": "a"},
                         {"mode": "ok", "resource": "missing", "key": "a"}):
                self.assertEqual(request(port, "POST", "/action", data)[0], 400)
            _, state = request(port, "GET", "/state")
            self.assertEqual(state, {"counts": {"target": 0, "other": 0}, "events": [], "pending": 0})

    def test_actual_observer_http_503(self):
        store = Store()
        with service(store) as port:
            store.observer_http_down = True
            status, _ = request(port, "GET", "/state")
            self.assertEqual(status, 503)
        receipt = execute(next(c for c in CASES if c.name == "observer_http_503"))
        self.assertIsNone(receipt["after"])
        self.assertEqual(receipt["verdict"], "INDETERMINATE")


if __name__ == "__main__":
    unittest.main()
