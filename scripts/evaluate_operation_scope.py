"""Post-freeze evaluation of target-only evidence vs complete operation scope."""
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter_ns
from statistics import median

from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.tool_session import verify_tool_call

MATCH = "STATE_MATCHED_UNATTRIBUTED"
MISMATCH = "STATE_MISMATCH"
UNKNOWN = "INDETERMINATE"
PREEXISTING = "STATE_PREEXISTING"
CASES = (
    ("normal", "old", (("target", "new"),), False, "new", MATCH, True),
    ("false_claim", "old", (), False, "new", MISMATCH, False),
    ("wrong_resource", "old", (("other", "new"),), False, "new", MISMATCH, False),
    ("wrong_value", "old", (("target", "wrong"),), False, "new", MISMATCH, False),
    ("collateral_write", "old", (("target", "new"), ("other", "changed")), False, "new", MATCH, False),
    ("duplicate_write", "old", (("target", "new"), ("target", "new")), False, "new", MATCH, False),
    ("overwritten_target", "old", (("target", "new"), ("target", "wrong")), False, "new", MISMATCH, False),
    ("error_after_commit", "old", (("target", "new"),), True, "new", MATCH, True),
    ("preexisting", "new", (), False, "new", PREEXISTING, False),
    ("deleted_target", "old", (("target", None),), False, "new", UNKNOWN, False),
    ("missing_initial", None, (), False, "new", UNKNOWN, False),
    ("unicode_goal", "old", (("target", "ação ✓"),), False, "ação ✓", MATCH, True),
)


def evaluate_case(case, directory):
    name, initial, mutations, raises, expected, label, exact = case
    db = directory / "state.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)")
        conn.execute("INSERT INTO resource_state VALUES ('other',0,'untouched')")
        if initial is not None:
            conn.execute("INSERT INTO resource_state VALUES ('target',0,?)", (initial,))
        conn.commit()
    guard = DurableReplayGuard(directory / "replay.db", initialize=True)
    invoked = 0

    def actor():
        nonlocal invoked
        invoked += 1
        with closing(sqlite3.connect(db)) as conn:
            for resource, value in mutations:
                if value is None:
                    conn.execute("DELETE FROM resource_state WHERE resource=?", (resource,))
                else:
                    conn.execute("UPDATE resource_state SET value=?,revision=revision+1 WHERE resource=?", (value, resource))
            conn.commit()
        if raises:
            raise RuntimeError("controlled error after commit")
        return "success"

    start = perf_counter_ns()
    result = verify_tool_call(database=db, guard=guard, key=secrets.token_bytes(32),
                              task_id=name, observer_id="scope-observer", resource="target",
                              expected_value=expected, actor=actor, window_seconds=1.0)
    elapsed_ms = (perf_counter_ns() - start) / 1_000_000
    with closing(sqlite3.connect(db)) as conn:
        state = {resource: (revision, value) for resource, revision, value in conn.execute("SELECT resource,revision,value FROM resource_state")}
    full_oracle = initial is not None and initial != expected and state == {"target": (1, expected), "other": (0, "untouched")}
    return {"case": name, "expected_verdict": label, "verdict": result.verdict,
            "expected_exact_operation": exact, "full_state_oracle": full_oracle,
            "actor_status": result.actor_status, "actor_invocations": invoked,
            "claim_only": result.actor_status == "RETURNED",
            "final_target_only": state.get("target", (None, None))[1] == expected,
            "oap_target": result.verdict == MATCH, "elapsed_ms": elapsed_ms}


def metrics(rows, endpoint):
    report = {}
    for method in ("claim_only", "final_target_only", "oap_target"):
        tp = sum(r[method] and endpoint(r) for r in rows)
        fp = sum(r[method] and not endpoint(r) for r in rows)
        tn = sum(not r[method] and not endpoint(r) for r in rows)
        fn = sum(not r[method] and endpoint(r) for r in rows)
        report[method] = {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                          "accuracy": (tp + tn) / len(rows),
                          "false_positive_cases": [r["case"] for r in rows if r[method] and not endpoint(r)]}
    return report


def run():
    with TemporaryDirectory() as tmp:
        rows = []
        for case in CASES:
            directory = Path(tmp) / case[0]
            directory.mkdir()
            rows.append(evaluate_case(case, directory))
    elapsed = [r["elapsed_ms"] for r in rows]
    return {"cases": len(rows), "exact_verdict_matches": sum(r["verdict"] == r["expected_verdict"] for r in rows),
            "full_oracle_matches": sum(r["full_state_oracle"] == r["expected_exact_operation"] for r in rows),
            "target_scope": metrics(rows, lambda r: r["expected_verdict"] == MATCH),
            "complete_operation_scope": metrics(rows, lambda r: r["expected_exact_operation"]),
            "elapsed_ms": {"min": min(elapsed), "median": median(elapsed), "max": max(elapsed)},
            "rows": rows, "scope": "Developer-authored post-freeze local evaluation; no independent or live-model comparison."}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["exact_verdict_matches"] == result["full_oracle_matches"] == result["cases"] else 1)
