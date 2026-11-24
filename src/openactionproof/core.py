"""File outcome verifier and checksum receipts.

Security scope: trusted local test workspace only. Hashes provide tamper *detection*
when compared against a trusted copy; they do not establish who produced evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Callable

SCHEMA = "openactionproof.receipt.v0.1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_target(workspace: Path, relative_path: str) -> Path:
    """Constrain local demo targets to an existing, non-symlinked workspace.

    No protection against hostile concurrent filesystem mutation/TOCTOU.
    """
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path or "\x00" in relative_path:
        raise ValueError("Target path must be a portable relative path")
    parts = relative_path.split("/")
    windows = PureWindowsPath(relative_path)
    if windows.anchor or any(part in ("", ".", "..") or ":" in part or part.endswith((" ", ".")) or part.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in "123456789¹²³"), *(f"LPT{i}" for i in "123456789¹²³")} for part in parts):
        raise ValueError("Target path must be a portable relative path")
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
    # Bound read-side memory regardless of the observed file's size. This is
    # still a trusted-workspace snapshot, not a race-safe filesystem sandbox.
    digest = hashlib.sha256()
    size = 0
    with target.open("rb") as stream:
        while chunk := stream.read(256 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"exists": True, "sha256": digest.hexdigest(), "size": size}


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
    """Observe independent final state; do not trust the operation's success claim.

    `operation` is trusted test code provided by caller. Real third-party agent
    isolation, independent observers, signing, and remote integrations are future work.
    """
    target = relative_target(workspace, spec.path)
    expected = {"exists": True, "sha256": sha256(spec.expected_bytes), "size": len(spec.expected_bytes)}
    before = snapshot(workspace, spec.path)
    error = None
    attempt = "ATTEMPTED"
    try:
        operation(target)
    except TimeoutError:
        error = "TimeoutError"
        attempt = "TIMED_OUT"
    except Exception:  # do not persist arbitrary exception messages
        error = "OperationError"
        attempt = "ERRORED"
    after = snapshot(workspace, spec.path)
    matches = after == expected
    if error is not None:
        verdict = "INDETERMINATE"  # observed matching state cannot prove completed transaction
        reason = "Operation failed or timed out; execution outcome is uncertain"
    elif matches and before == expected:
        verdict = "STATE_SATISFIED_UNATTRIBUTED"
        reason = "Expected state pre-existed; this observation cannot attribute execution to the agent"
    elif matches:
        verdict = "CONFIRMED"
        reason = "Independently observed state changed to match predeclared expected state; causality is not authenticated"
    elif spec.claim is True:
        verdict = "FALSE_SUCCESS"
        reason = "Agent claimed success, but independently observed state differs"
    else:
        verdict = "NOT_CONFIRMED"
        reason = "Independently observed state does not match expected state"
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
        "verification": {"verifier": "filesystem-sha256-v0.1", "verdict": verdict, "matches_expected": matches, "reason": reason},
        "limitations": "Local observation only. Receipt hash is not an authenticated signature or proof of independent custody.",
    }
    return {**body, "receipt_sha256": sha256(canonical(body))}


def check_receipt(receipt: dict[str, Any]) -> bool:
    """Check checksum integrity ONLY; neither provenance nor environmental truth."""
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        return False
    stored = receipt.get("receipt_sha256")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return isinstance(stored, str) and len(stored) == 64 and sha256(canonical(body)) == stored
