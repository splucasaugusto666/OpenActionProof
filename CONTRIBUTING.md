# Contributing

1. Open an issue with a concrete failure case and intended result.
2. Propose the smallest change, with a new test that fails before the fix.
3. Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
4. Do not submit private data, credentials, exploit payloads for live targets, or falsified research results.
5. Clearly distinguish observed results from hypotheses. Follow SECURITY.md for sensitive reports.