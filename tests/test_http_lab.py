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
