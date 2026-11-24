"""Version-pinned external file-outcome comparison; see frozen protocol."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter_ns

from openactionproof.core import ActionSpec, check_receipt, sha256, verify_action

GOAL = b'expected'
CASES = (
    ('write_exact', None, (GOAL,), GOAL, False, True),
    ('replace_exact', b'old', (GOAL,), GOAL, False, True),
    ('preexisting_exact', GOAL, (), GOAL, False, True),
    ('empty_exact', None, (b'',), b'', False, True),
    ('unicode_exact', None, ('ação ✓'.encode(),), 'ação ✓'.encode(), False, True),
    ('committed_then_error', None, (GOAL,), GOAL, True, True),
    ('absent_noop', None, (), GOAL, False, False),
    ('wrong_same_size', None, (b'xxxxxxxx',), GOAL, False, False),
    ('partial_write', None, (b'exp',), GOAL, False, False),
    ('existing_wrong', b'old', (), GOAL, False, False),
    ('deleted', GOAL, (None,), GOAL, False, False),
    ('overwritten', None, (GOAL, b'wrong'), GOAL, False, False),
)


def prepare(root, initial):
    root.mkdir()
    if initial is not None:
        (root / 'target').write_bytes(initial)


def mutate(path, changes, raises):
    for content in changes:
        if content is None:
            path.unlink()
        else:
            path.write_bytes(content)
    if raises:
        raise RuntimeError('controlled post-commit error')


def external(root, home, goal, cli):
    env = os.environ.copy()
    env['VERIEFFECT_HOME'] = str(home)
    receipt = root / 'receipt.json'
    start = perf_counter_ns()
    proc = subprocess.run([cli, 'claim', 'file_exists', '--agent', 'apex-fixture', '--target', './target',
                           '--expect', json.dumps({'sha256': sha256(goal)}), '--out', str(receipt)],
                          cwd=root, env=env, capture_output=True, text=True, timeout=30)
    elapsed = (perf_counter_ns() - start) / 1e6
    if proc.returncode not in (0, 1, 3) or not receipt.is_file():
        raise RuntimeError(f'external adapter failed: exit {proc.returncode}')
    body = json.loads(receipt.read_text(encoding='utf-8'))
    verdict = {0:'PASS', 1:'FAIL', 3:'UNVERIFIABLE'}[proc.returncode]
    if body.get('verdict') != verdict:
        raise RuntimeError('external verdict/exit mismatch')
    verified = subprocess.run([sys.executable, '-m', 'verify_receipt', '--pubkey',
                               str(home / 'keys' / 'verieffect_ed25519.pub'), str(receipt)],
                              cwd=root, env=env, capture_output=True, text=True, timeout=30)
    if verified.returncode != 0:
        raise RuntimeError('external receipt verification failed')
    return {'decision': verdict, 'exit_code': proc.returncode, 'signature_verified': True, 'elapsed_ms': elapsed}


def score(rows, method):
    counts = {k:0 for k in ('tp','tn','fp','fn','positive_abstentions','negative_abstentions')}
    for row in rows:
        positive = row['positive']
        decision = row[method]['decision']
        if decision == 'PASS':
            key = 'tp' if positive else 'fp'
        elif decision == 'FAIL':
            key = 'fn' if positive else 'tn'
        elif decision == 'UNVERIFIABLE':
            key = 'positive_abstentions' if positive else 'negative_abstentions'
        else:
            raise ValueError('unknown decision')
        counts[key] += 1
    c = counts
    p = c['tp'] + c['fn'] + c['positive_abstentions']
    n = c['tn'] + c['fp'] + c['negative_abstentions']
    decisions = c['tp'] + c['tn'] + c['fp'] + c['fn']
    return {**c, 'score':45*c['tn']/n + 35*c['tp']/p + 20*decisions/len(rows)}


def run(local_only=False):
    cli = None if local_only else shutil.which('verieffect')
    if not local_only and (not cli or importlib.metadata.version('verieffect') != '0.2.0a4'):
        raise RuntimeError('exact external version required; no substitute')
    rows = []
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, initial, changes, goal, raises, positive in CASES:
            a = root / (name + '-oap')
            prepare(a, initial)
            start = perf_counter_ns()
            receipt = verify_action(a, ActionSpec(name, 'target', goal, True),
                                    lambda path: mutate(path, changes, raises), operation_name='fixture')
            elapsed = (perf_counter_ns() - start) / 1e6
            if not check_receipt(receipt):
                raise RuntimeError('OAP checksum failed')
            row = {'case':name, 'positive':positive, 'newly_attained':positive and initial != goal,
                   'oap':{'decision':'PASS' if receipt['verification']['matches_expected'] else 'FAIL',
                          'attempt_verdict':receipt['verification']['verdict'],
                          'checksum_valid':True, 'elapsed_ms':elapsed}}
            if cli:
                b = root / (name + '-external')
                prepare(b, initial)
                try:
                    mutate(b / 'target', changes, raises)
                except RuntimeError:
                    if not raises:
                        raise
                row['verieffect'] = external(b, root / (name + '-keys'), goal, cli)
            rows.append(row)
    metrics = {'oap':score(rows, 'oap')}
    if cli:
        metrics['verieffect'] = score(rows, 'verieffect')
    return {'cases':len(rows), 'mode':'local-only' if local_only else 'external-comparison',
            'external_version':None if local_only else '0.2.0a4', 'scores':metrics, 'rows':rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.local_only), indent=2, ensure_ascii=False))
