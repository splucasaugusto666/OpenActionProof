# Contributing

1. Open an issue with a concrete failure case and intended result.
2. Propose the smallest change, with a new test that fails before the fix.
3. Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
4. Do not submit private data, credentials, exploit payloads for live targets, or falsified research results.
5. Clearly distinguish observed results from hypotheses. Follow SECURITY.md for sensitive reports.
## First contribution

Try docs/QUICKSTART.md in an isolated environment. For a regression report, provide version/commit, OS and Python version, expected outcome, observed state, actual verdict and a minimal synthetic reproduction. Do not attach real account credentials, private records or production data. For comparative research, freeze the protocol before execution and preserve failures, abstentions and unsupported cases. For documentation, distinguish the tagged wheel from main. For a proposed integration, include a reproducible controlled test and explain the trust boundary. Cite the exact commit or tagged release using CITATION.cff.
