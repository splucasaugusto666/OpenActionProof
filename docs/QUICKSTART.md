# Verify your first AI-agent outcome

This five-minute example uses trusted local Python callbacks and an explicitly pinned file goal. It does not require an AI model, account or network during execution.

Install the [official research preview](https://github.com/splucasaugusto666/OpenActionProof/releases/tag/v0.9.0rc2) in a dedicated virtual environment after checking its checksum. Run the README demo, then try this standalone Python script:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from openactionproof.core import ActionSpec, verify_action

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    # Pin the desired bytes before invoking a trusted action.
    spec = ActionSpec("example", "report.txt", b"approved", True)

    def claim_without_effect(path):
        return "success"

    receipt = verify_action(root, spec, claim_without_effect,
                            operation_name="example_false_claim")
    print(receipt["verification"]["verdict"])  # FALSE_SUCCESS

    def write_report(path):
        path.write_bytes(b"approved")

    receipt = verify_action(root, spec, write_report,
                            operation_name="example_write")
    print(receipt["verification"]["verdict"])  # CONFIRMED

    receipt = verify_action(root, spec, claim_without_effect,
                            operation_name="example_preexisting")
    print(receipt["verification"]["verdict"])  # STATE_SATISFIED_UNATTRIBUTED
```

Here CONFIRMED means the observed file changed to the requested contents in the local controlled test, not cryptographic proof of actor causation. The caller and the workspace are trusted. Never execute arbitrary model-produced Python with this example.

Next: [authenticated tool integration](TOOL_INTEGRATION.md), [durable dispatch](TOOL_DISPATCH.md), [signed observations](PUBLIC_EVIDENCE.md), [reconciliation](RECONCILIATION.md). The public preview does not contain every change on main. Install main from a trusted checkout to try the newest code. For a safe research evaluation, use disposable resources and compare explicit observations with predeclared labels.
