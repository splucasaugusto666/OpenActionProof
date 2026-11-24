import unittest
from openactionproof.http_lab import CASES, benchmark, check_receipt, execute


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


if __name__ == "__main__":
    unittest.main()
