"""Optional real Inspect AI task; controlled callbacks, no paid model requests."""
from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
from tempfile import TemporaryDirectory
import asyncio

from inspect_ai import Task, eval, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer
from inspect_ai.solver import Generate, TaskState, solver

from openactionproof.durable_replay import DurableReplayGuard
from openactionproof.tool_session import verify_tool_call


def controlled_case(case: str) -> str:
    if case not in ("write", "no_effect", "preexisting"):
        raise ValueError("unknown fixture")
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.db"
        with closing(sqlite3.connect(path)) as conn:
            conn.execute("CREATE TABLE resource_state(resource TEXT PRIMARY KEY, revision INTEGER, value TEXT)")
            conn.execute("INSERT INTO resource_state VALUES ('target', 0, ?)", ("new" if case == "preexisting" else "old",))
            conn.commit()
        guard = DurableReplayGuard(Path(tmp) / "replay.db", initialize=True)

        def actor():
            if case == "write":
                with closing(sqlite3.connect(path)) as conn:
                    conn.execute("UPDATE resource_state SET revision=revision+1,value='new' WHERE resource='target'")
                    conn.commit()
            return "success"  # identical claim in all three fixtures

        return verify_tool_call(database=path, guard=guard, key=secrets.token_bytes(32),
                                task_id="inspect-fixture", observer_id="local-observer", resource="target",
                                expected_value="new", actor=actor, window_seconds=2.0).verdict


@solver
def controlled_tool():
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Fixture metadata is trusted evaluator configuration, not model input.
        state.metadata["oap_verdict"] = await asyncio.to_thread(controlled_case, state.metadata["case"])
        return state
    return solve


@scorer(metrics=[accuracy()])
def verified_state():
    async def score(state: TaskState, target: Target) -> Score:
        actual = state.metadata.get("oap_verdict")
        return Score(value=CORRECT if actual == target.text else INCORRECT,
                     answer=str(actual), explanation="Trusted evaluator observation, not model assertion.")
    return score


@task
def oap_controlled():
    return Task(
        dataset=[
            Sample(id="write", input="Controlled fixture", target="STATE_MATCHED_UNATTRIBUTED", metadata={"case":"write"}),
            Sample(id="no_effect", input="Controlled fixture", target="STATE_MISMATCH", metadata={"case":"no_effect"}),
            Sample(id="preexisting", input="Controlled fixture", target="STATE_PREEXISTING", metadata={"case":"preexisting"}),
        ],
        solver=controlled_tool(),
        scorer=verified_state(),
    )


if __name__ == "__main__":
    with TemporaryDirectory() as tmp:
        logs = eval(oap_controlled(), model="mockllm/model", log_dir=tmp, log_format="json")
        assert len(logs) == 1 and logs[0].status == "success", "Inspect evaluation failed"
        samples = logs[0].samples
        assert samples is not None and len(samples) == 3
        assert all(sample.scores and all(score.value == CORRECT for score in sample.scores.values()) for sample in samples), "Unexpected fixture verdict"
        print("Inspect AI controlled integration: 3/3 expected verdicts")
