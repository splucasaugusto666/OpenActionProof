"""Loopback HTTP outcome-verifier conformance lab, not a production security boundary."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any

from .core import canonical, sha256

CONFIRMED = "CONFIRMED"
FALSE_SUCCESS = "FALSE_SUCCESS"
INDETERMINATE = "INDETERMINATE"
UNATTRIBUTED = "STATE_SATISFIED_UNATTRIBUTED"
NOT_CONFIRMED = "NOT_CONFIRMED"


@dataclass(frozen=True)
class Case:
    name: str
    attempts: tuple[tuple[str, str, str], ...]
    claim: bool | None
    expected: str
    settle: bool = True
    preexisting: bool = False
    observer_down: bool = False


# Each attempt is (fault mode, resource, idempotency key). Expected labels are
# declared before execution; they are fixture expectations, not measured truth.
CASES = (
    Case("normal", (("ok", "target", "a"),), True, CONFIRMED),
    Case("accepted_then_failed", (("queued_fail", "target", "a"),), True, FALSE_SUCCESS),
    Case("accepted_pending", (("queued", "target", "a"),), True, INDETERMINATE, settle=False),
    Case("accepted_then_completed", (("queued", "target", "a"),), True, CONFIRMED),
    Case("elapsed_timeout_after_commit", (("timeout", "target", "a"),), None, CONFIRMED),
    Case("lost_ack_after_commit", (("lost_ack", "target", "a"),), None, CONFIRMED),
    Case("retry_idempotent", (("lost_ack", "target", "a"), ("ok", "target", "a")), True, CONFIRMED),
    Case("duplicate_retry", (("ok", "target", "a"), ("ok", "target", "b")), True, FALSE_SUCCESS),
    Case("wrong_resource", (("ok", "other", "a"),), True, FALSE_SUCCESS),
    Case("stale_agent_read", (("stale", "target", "a"),), True, FALSE_SUCCESS),
    Case("preexisting_state", (("noop", "target", "a"),), True, UNATTRIBUTED, preexisting=True),
    Case("observer_http_503", (("ok", "target", "a"),), True, INDETERMINATE),
    Case("observer_unavailable", (("ok", "target", "a"),), True, INDETERMINATE, observer_down=True),
    Case("no_claim_no_effect", (("noop", "target", "a"),), None, NOT_CONFIRMED),
)


class Store:
    def __init__(self, preexisting: bool = False):
        self.counts = {"target": int(preexisting), "other": 0}
        self.events: list[dict[str, Any]] = []
        self.pending: list[tuple[str, str, str]] = []
        self.keys: set[str] = set()
        self.observer_http_down = False

    def apply(self, resource: str, key: str) -> None:
        self.counts[resource] += 1
        self.events.append({"resource": resource, "key": key})

    def snapshot(self) -> dict[str, Any]:
        return {"counts": dict(self.counts), "events": list(self.events), "pending": len(self.pending)}

    def settle(self) -> None:
        for mode, resource, key in self.pending:
            if mode == "queued":
                self.apply(resource, key)
        self.pending.clear()


@contextmanager
def service(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status: int, payload: dict):
            body = canonical(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/state":
                if store.observer_http_down:
                    self.reply(503, {"error": "observer unavailable"})
                else:
                    self.reply(200, store.snapshot())
            else:
                self.reply(404, {})

        def do_POST(self):
            # Consume the request body before sending a response or closing the
            # socket. Closing with unread bytes can reset the connection on Windows.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 65536:
                    raise ValueError("invalid request length")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("incomplete request")
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    raise ValueError("invalid request body")
            except (ValueError, OSError, RecursionError):
                self.reply(400, {"error": "invalid request body"})
                return
            if self.path == "/settle":
                if data:
                    self.reply(400, {"error": "settle requires empty object"})
                    return
                store.settle()
                self.reply(200, {"settled": True})
                return
            if self.path != "/action":
                self.reply(404, {})
                return
            if (set(data) != {"mode", "resource", "key"}
                    or not all(isinstance(v, str) for v in data.values())
                    or data["mode"] not in {"ok", "queued", "queued_fail", "noop", "stale", "timeout", "lost_ack"}
                    or data["resource"] not in store.counts):
                self.reply(400, {"error": "invalid action"})
                return
            mode, resource, key = data["mode"], data["resource"], data["key"]
            if key in store.keys:
                self.reply(200, {"deduplicated": True})
                return
            store.keys.add(key)
            if mode in ("queued", "queued_fail"):
                store.pending.append((mode, resource, key))
                self.reply(202, {"accepted": True})
            elif mode in ("noop", "stale"):
                self.reply(200, {"reported_count": 1})
            else:
                store.apply(resource, key)
                if mode == "timeout":
                    time.sleep(0.15)
                    self.close_connection = True
                    return
                if mode == "lost_ack":
                    # Close without a response: deterministic lost acknowledgement,
                    # not a simulated elapsed-time timeout.
                    self.close_connection = True
                    return
                self.reply(200, {"accepted": True})

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(port: int, method: str, path: str, data: dict | None = None, *, timeout: float = 2) -> tuple[int, dict]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        body = canonical(data) if data is not None else None
        conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, json.loads(response.read())
    finally:
        conn.close()


def verdict(before: dict, after: dict | None, claim: bool | None) -> str:
    if after is None or after["pending"]:
        return INDETERMINATE
    correct_state = after["counts"] == {"target": 1, "other": 0}
    new_events = after["events"][len(before["events"]):]
    if correct_state and before["counts"] == after["counts"] and not new_events:
        return UNATTRIBUTED
    if correct_state and before["counts"] == {"target": 0, "other": 0} and len(new_events) == 1 and new_events[0]["resource"] == "target":
        return CONFIRMED
    return FALSE_SUCCESS if claim is True else NOT_CONFIRMED


def execute(case: Case) -> dict:
    store = Store(case.preexisting)
    with service(store) as port:
        _, before = request(port, "GET", "/state")
        attempts = []
        for mode, resource, key in case.attempts:
            try:
                status, _ = request(port, "POST", "/action", {"mode": mode, "resource": resource, "key": key}, timeout=0.03 if mode == "timeout" else 2)
            except (OSError, http.client.HTTPException):
                status = None
            attempts.append({"mode": mode, "resource": resource, "key": key, "status": status})
        if case.settle:
            request(port, "POST", "/settle", {})
        if case.name == "observer_http_503":
            store.observer_http_down = True
        # Separately exercise an actual HTTP error and an injected absent observation.
        after = None
        if not case.observer_down:
            try:
                status, observation = request(port, "GET", "/state")
                if status == 200:
                    after = observation
            except (OSError, http.client.HTTPException, ValueError):
                pass
    result = {"schema": "openactionproof.http-lab.v0.2", "case": case.name,
              "expected_state": {"target": 1, "other": 0}, "before": before,
              "attempts": attempts, "agent_claim": case.claim, "after": after,
              "verdict": verdict(before, after, case.claim), "fixture_label": case.expected}
    return {**result, "receipt_sha256": sha256(canonical(result))}


def check_receipt(receipt: dict) -> bool:
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    return receipt.get("schema") == "openactionproof.http-lab.v0.2" and receipt.get("receipt_sha256") == sha256(canonical(body))


def benchmark() -> dict:
    rows = []
    for case in CASES:
        receipt = execute(case)
        rows.append({"case": case.name, "fixture_label": case.expected, "observed_verdict": receipt["verdict"],
                     "expected_confirmed": case.expected == CONFIRMED,
                     "claim_only": case.claim is True,
                     "http_2xx": any(a["status"] is not None and 200 <= a["status"] < 300 for a in receipt["attempts"]),
                     "state_verifier": receipt["verdict"] == CONFIRMED, "receipt": receipt})
    metrics = {}
    for name in ("claim_only", "http_2xx", "state_verifier"):
        tp = sum(r[name] and r["expected_confirmed"] for r in rows)
        fp = sum(r[name] and not r["expected_confirmed"] for r in rows)
        tn = sum(not r[name] and not r["expected_confirmed"] for r in rows)
        fn = sum(not r[name] and r["expected_confirmed"] for r in rows)
        metrics[name] = {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "accuracy": (tp + tn) / len(rows)}
    return {"fixture_count": len(rows), "exact_verdict_matches": sum(r["fixture_label"] == r["observed_verdict"] for r in rows),
            "metrics": metrics, "rows": rows, "limitations": "Synthetic in-sample fixtures; shared service/observer trust domain; no external verifier comparison or real-agent accuracy claim."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = benchmark()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    if report["exact_verdict_matches"] != report["fixture_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
