"""Authenticated observer subprocess reference transport, not a sandbox.

Keys travel over stdin, never command-line arguments or application logs.
The trusted caller and observer still share the same OS trust domain.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from .observer import ObservationRequest, SQLiteObserver
from .verified_observation import authenticate, observe_authenticated

MAX_MESSAGE = 65536
# Explicitly import only the trusted package containing this module. Do not
# let cwd, PYTHONPATH or site startup hooks choose the code receiving the key.
WORKER_BOOTSTRAP = (
    "import sys, runpy; sys.path.insert(0, sys.argv.pop(1)); "
    "runpy.run_module('openactionproof.observer_worker', run_name='__main__')"
)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _decode(data: bytes):
    if len(data) > MAX_MESSAGE:
        raise ValueError("message too large")
    return json.loads(data, object_pairs_hook=_unique_object)


def read_authenticated(path: Path, key: bytes, task_id: str, expected: str,
                       request: ObservationRequest, *, timeout: float = 5.0) -> dict | None:
    """Read through the fixed worker module, authenticating before returning.

    Intended for trusted local deployments; do not accept caller-supplied worker
    executables or expose the worker as a general signing oracle.
    """
    if (not isinstance(request, ObservationRequest) or not request.valid()
            or not isinstance(key, bytes) or not 32 <= len(key) <= 128):
        return None
    if type(timeout) not in (int, float) or not 0 < timeout <= 30:
        return None
    now = time.time_ns()
    remaining_ns = request.deadline_ns - now
    if now < request.not_before_ns or remaining_ns <= 0:
        return None
    # Bound before conversion, including untrusted huge integer deadlines.
    remaining = min(remaining_ns, 30_000_000_000) / 1_000_000_000
    payload = {"key": key.hex(), "task_id": task_id, "expected": expected,
               "request": asdict(request)}
    try:
        data = json.dumps(payload, allow_nan=False).encode("utf-8")
        if len(data) > MAX_MESSAGE:
            return None
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-c", WORKER_BOOTSTRAP,
             str(Path(__file__).resolve().parents[1]), str(Path(path).absolute()), request.observer_id],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=min(timeout, remaining), check=False,
        )
        if result.returncode != 0:
            return None
        envelope = _decode(result.stdout)
        return envelope if authenticate(key, task_id, expected, request, envelope, now_ns=time.time_ns()) is not None else None
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, OverflowError, RecursionError):
        return None


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    try:
        payload = _decode(sys.stdin.buffer.read(MAX_MESSAGE + 1))
        if not isinstance(payload, dict) or set(payload) != {"key", "task_id", "expected", "request"}:
            return 2
        key = bytes.fromhex(payload["key"])
        if not 32 <= len(key) <= 128:
            return 2
        request = ObservationRequest(**payload["request"])
        envelope = observe_authenticated(SQLiteObserver(Path(sys.argv[1]), sys.argv[2]), key,
                                         payload["task_id"], payload["expected"], request)
        print(json.dumps(envelope, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, OverflowError, RecursionError):
        # No raw request, key, exception details or database contents on failure.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
