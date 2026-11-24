"""Simplest host-agent integration pattern; does not make the agent trusted."""
from pathlib import Path
from tempfile import TemporaryDirectory
from openactionproof.core import ActionSpec, verify_action

with TemporaryDirectory() as tmp:
    workspace = Path(tmp)
    goal = ActionSpec(task_id="document-write", path="report.txt", expected_bytes=b"hello\n", claim=True)
    def tool_like_callback(target: Path) -> None:
        target.write_bytes(b"hello\n")
    result = verify_action(workspace, goal, tool_like_callback, operation_name="demo-agent-write")
    print(result["verification"]["verdict"])
