import unittest
from openactionproof.observation_benchmark import run


class ObservationBenchmarkTests(unittest.TestCase):
    def test_corpus_and_confusion_matrices(self):
        report = run()
        self.assertEqual(report['cases'], 16)
        self.assertEqual(report['exact_matches'], 16)
        for metric in report['metrics'].values():
            self.assertEqual(sum(metric[k] for k in ('tp', 'fp', 'tn', 'fn')), 16)
        self.assertEqual(report['metrics']['authenticated']['fp'], 0)
        self.assertEqual(report['metrics']['authenticated']['fn'], 0)
