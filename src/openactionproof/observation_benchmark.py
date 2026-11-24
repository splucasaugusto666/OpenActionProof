"""Run the frozen developer-authored observation corpus. No external services."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .core import canonical, sha256
from .durable_replay import DurableReplayGuard
from .observer import Observation, ObservationRequest
from .verified_observation import assess_authenticated_pair, observe_authenticated

MATCH = 'STATE_MATCHED_UNATTRIBUTED'
MISMATCH = 'STATE_MISMATCH'
PREEXISTING = 'STATE_PREEXISTING'
UNKNOWN = 'INDETERMINATE'
CASES = (
    ('normal', MATCH, True), ('lost_ack', MATCH, False),
    ('no_effect', MISMATCH, True), ('preexisting', PREEXISTING, True),
    ('wrong_state', MISMATCH, True), ('missing', UNKNOWN, True),
    ('expired', UNKNOWN, True), ('wrong_key', UNKNOWN, True),
    ('tampered', UNKNOWN, True), ('wrong_task', UNKNOWN, True),
    ('wrong_goal', UNKNOWN, True), ('replay', UNKNOWN, True),
    ('rollback', UNKNOWN, True), ('same_revision_change', UNKNOWN, True),
    ('wrong_resource', UNKNOWN, True), ('future_observation', UNKNOWN, True),
)


class FixedObserver:
    def __init__(self, observation):
        self.observation = observation

    def observe(self, request):
        return self.observation


def evaluate_case(name, label, claim, storage):
    key = b'\x01' * 32  # Public deterministic fixture key; never use in production.
    expected = sha256(canonical('new'))
    old = sha256(canonical('old'))
    before_req = ObservationRequest('observer', 'target', 'a'*64, 10, 20)
    after_req = ObservationRequest('observer', 'target', 'b'*64, 30, 40)
    before = Observation('observer', 'target', before_req.challenge, 15, 1, old)
    after = Observation('observer', 'target', after_req.challenge, 35, 2, expected)
    if name == 'no_effect':
        after = replace(after, revision=1, state_sha256=old)
    elif name == 'preexisting':
        before = replace(before, state_sha256=expected)
    elif name == 'wrong_state':
        after = replace(after, state_sha256=sha256(canonical('other')))
    elif name == 'rollback':
        after = replace(after, revision=0)
    elif name == 'same_revision_change':
        after = replace(after, revision=1)
    elif name == 'future_observation':
        after = replace(after, observed_ns=39)
    signed_req = after_req
    if name == 'wrong_resource':
        signed_req = replace(after_req, resource='other')
        after = replace(after, resource='other')
    def seal(req, obs, signing_key=key, task='task', digest=expected):
        return observe_authenticated(FixedObserver(obs), signing_key, task, digest, req)
    be = seal(before_req, before)
    ae = seal(signed_req, after, signing_key=b'\x02'*32 if name == 'wrong_key' else key,
              task='other' if name == 'wrong_task' else 'task', digest=old if name == 'wrong_goal' else expected)
    if name == 'missing':
        ae = None
    elif name == 'tampered':
        ae['observation']['revision'] = 3
    now = 41 if name == 'expired' else 36
    guard = DurableReplayGuard(storage, initialize=True)
    def assess():
        return assess_authenticated_pair(guard, key, 'task', expected, before_req, after_req, be, ae, now_ns=now)
    if name == 'replay':
        if assess() != MATCH:
            raise RuntimeError('replay setup failed')
    observed = assess()
    return {'case':name, 'expected':label, 'observed':observed, 'positive':label == MATCH,
            'claim_only':claim, 'state_only':ae is not None and ae['observation']['state_sha256'] == expected,
            'authenticated':observed == MATCH}


def run():
    with TemporaryDirectory() as tmp:
        rows = [evaluate_case(*case, Path(tmp)/f'{i}.db') for i, case in enumerate(CASES)]
    metrics = {}
    for method in ('claim_only', 'state_only', 'authenticated'):
        tp = sum(r[method] and r['positive'] for r in rows)
        fp = sum(r[method] and not r['positive'] for r in rows)
        tn = sum(not r[method] and not r['positive'] for r in rows)
        fn = sum(not r[method] and r['positive'] for r in rows)
        metrics[method] = dict(tp=tp, fp=fp, tn=tn, fn=fn, accuracy=(tp+tn)/len(rows))
    return {'cases':len(rows), 'exact_matches':sum(r['expected']==r['observed'] for r in rows),
            'metrics':metrics, 'rows':rows, 'scope':'Synthetic developer-authored construction cases; no actor attribution or independent competitor evaluation.'}


if __name__ == '__main__':
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result['exact_matches'] == result['cases'] else 1)
