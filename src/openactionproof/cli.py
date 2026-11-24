"""Offline demonstration CLI, no API keys required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .core import ActionSpec, check_receipt, verify_action


def demo(output: Path) -> dict[str, str]:
    output.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}
    with TemporaryDirectory(prefix="oap-") as tmp:
        root = Path(tmp)
        cases = [
            ("A_confirmed", "expected full data\n", "write_expected", True),
            ("B_false_success", "expected full data\n", "no_op", True),
            ("C_partial_timeout", "expected full data\n", "partial_then_timeout", None),
        ]
        for case_id, content, operation_name, agent_claim in cases:
            # Isolated file per run; intentional duplicate filenames are safe.
            path = f"{case_id}.txt"
            spec = ActionSpec(case_id, path, content.encode(), agent_claim)
            def op(target: Path, name: str = operation_name, payload: bytes = spec.expected_bytes) -> None:
                if name == "write_expected":
                    target.write_bytes(payload)
                elif name == "partial_then_timeout":
                    target.write_bytes(payload[:5])
                    raise TimeoutError("synthetic timeout after partial side effect")
                elif name == "no_op":
                    return
                else:
                    raise AssertionError("unsupported test operation")
            receipt = verify_action(root, spec, op, operation_name=operation_name)
            assert check_receipt(receipt)
            output.joinpath(f"{case_id}.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            results[case_id] = receipt["verification"]["verdict"]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenActionProof: verify action outcomes")
    sub = parser.add_subparsers(dest="command", required=True)
    p_demo = sub.add_parser("demo", help="Run three synthetic action scenarios")
    p_demo.add_argument("--output", type=Path, default=Path("evidence/generated"))
    p_check = sub.add_parser("verify-receipt", help="Verify the local JSON receipt checksum (not provenance)")
    p_check.add_argument("file", type=Path)
    args = parser.parse_args()
    if args.command == "demo":
        print(json.dumps(demo(args.output), indent=2))
    else:
        try:
            valid = check_receipt(json.loads(args.file.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            valid = False
        print("CHECKSUM_VALID" if valid else "CHECKSUM_INVALID")
        if not valid:
            raise SystemExit(1)

if __name__ == "__main__":
    main()
