# Experiments

## Local v0.1 evidence

Command: PYTHONPATH=src python -m unittest discover -s tests -v
Observed 2026-11-23: 8 tests, all passing in local Python environment.

Command: PYTHONPATH=src python -m openactionproof demo
Observed: A_confirmed=CONFIRMED; B_false_success=FALSE_SUCCESS; C_partial_timeout=INDETERMINATE.

The tests are synthetic construction tests. They do not validate real agent behavior, accuracy against external baselines, or independent signatures. For reproducibility rerun the commands, inspect generated JSON receipts, and check them using verify-receipt.

## v0.2 HTTP benchmark

12 unit tests passed locally; 12/12 fixture labels matched. See `benchmarks/METHODOLOGY.md` for confusion matrices and limitations.
