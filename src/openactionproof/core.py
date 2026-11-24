"""File outcome verification with checksum receipts (research-only).
Callbacks must be trusted; this does not isolate hostile agents or prove provenance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "openactionproof.receipt.v0.1"

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def relative_target(workspace: Path, relative_path: str) -> Path:
    """Confine paths in a nonhostile local workspace; NOT race/TOCTOU-safe."""
    rel = Path(relative_path)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or "." in rel.parts:
        raise ValueError("Target path must be a safe relative path")
    root = workspace.resolve(strict=True)
    target = root.joinpath(*rel.parts)
    if any(p.is_symlink() for p in (root, *list(target.parents)[:-1], target)):
        raise ValueError("Symlink targets are not supported")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Path escaped the workspace")
    return target

def snapshot(workspace: Path, relative_path: str) -> dict[str, Any]:
    target = relative_target(workspace, relative_path)
    if not target.exists():
        return {"exists": False, "sha256": None, "size": None}
    if not target.is_file():
        raise ValueError("Only regular files can be verified")
    data = target.read_bytes()
    return {"exists": True, "sha256": sha256(data), "size": len(data)}

@dataclass(frozen=True)
class ActionSpec:
    task_id: str
    path: str
    expected_bytes: bytes
    claim: bool | None = None

def verify_action(
    workspace: Path,
    spec: ActionSpec,
    operation: Callable[[Path], None],
    *,
    operation_name: str,
) -> dict[str, Any]:
    """Measure final state independently of an agent's claim, NOT authenticated causality."""
    target = relative_target(workspace, spec.path)
    expected = {"exists": True, "sha256": sha256(spec.expected_bytes), "size": len(spec.expected_bytes)}
    before = snapshot(workspace, spec.path)
    error = None
    attempt = "ATTEMPTED"
    try:
        operation(target)
    except TimeoutError as exc:
        error = f"TimeoutError: {exc}"
        attempt = "TIMED_OUT"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        attempt = "ERRORED"
    after = snapshot(workspace, spec.path)
    matches = after == expected
    if error is not None:
        verdict = "INDETERMINATE"
        reason = "Operation failed or timed out; execution outcome is uncertain"
    elif matches and before == expected:
        verdict = "STATE_SATISFIED_UNATTRIBUTED"
        reason = "Expected state pre-existed; this observation cannot attribute execution to the agent"
    elif matches:
        verdict = "CONFIRMED"
        reason = "Observed state changed to match predeclared expected state; causality not authenticated"
    elif spec.claim is True:
        verdict = "FALSE_SUCCESS"
        reason = "Agent claimed success, but observed state differs"
    else:
        verdict = "NOT_CONFIRMED"
        reason = "Observed state does not match expected state"
    body = {
        "schema": SCHEMA,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": spec.task_id,
        "requested_action": {"kind": "write_file", "relative_path": spec.path},
        "planned_expected_state": expected,
        "initial_observation": before,
        "attempt": {"name": operation_name, "status": attempt, "error": error},
        "agent_claimed_success": spec.claim,
        "final_observation": after,
        "verification": {"verifier": "filesystem-sha256-v0.1", "verdict": verdict,
                         "matches_expected": matches, "reason": reason},
        "limitations": "Local observation only. Receipt hash is not an authenticated signature or proof of independent custody.",
    }
    return {**body, "receipt_sha256": sha256(canonical(body))}

def check_receipt(receipt: dict[str, Any]) -> bool:
    """Verify self-checksum ONLY. A forger can recompute it."""
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        return False
    stored = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return isinstance(stored, str) and len(stored) == 64 and sha256(canonical(body)) == stored
