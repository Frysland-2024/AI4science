"""Unified entry point; subprotocols remain independently frozen."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def dispatch(command, arm, timeout=10800):
    started = time.time()
    if arm == 'e1' and command in ('audit', 'verify', 'report'):
        # E1 is frozen, and its original atomic Path.replace writer fails on
        # existing Windows artifacts in this worktree. Recompute reports only
        # when the resulting JSON bytes are identical to the frozen outputs.
        from . import e1
        from .delivery import _e1_write_only_if_recomputed_bytes_match
        original_writer = e1.write
        try:
            e1.write = _e1_write_only_if_recomputed_bytes_match
            outcome = getattr(e1, command)()
            print(json.dumps(outcome, ensure_ascii=False, allow_nan=False))
            return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        finally:
            e1.write = original_writer
    module = f'pxrd_heuristic_rruff_validation.{arm}'
    args = [sys.executable, '-m', module, command]
    if arm == 'e2' and ((ROOT/'reports/e2_results.json').exists() or command in ('verify', 'report')):
        args = [sys.executable, '-m', 'pxrd_heuristic_rruff_validation.e2_verify']
    try:
        result = subprocess.run(args, check=False, timeout=timeout)
        code = result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        code = 1
        print(str(exc), file=sys.stderr)
    if command == 'run':
        path = ROOT / 'reports' / 'runner_events.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'time': time.time(), 'arm': arm, 'command': args,
                'exit_code': code, 'seconds': time.time()-started})+'\n')
    return code

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit', 'preflight', 'run', 'status', 'verify', 'report'])
    parser.add_argument('--arm', choices=['e1', 'e2', 'all'], default='all')
    options = parser.parse_args()
    arms = ['e1', 'e2'] if options.arm == 'all' else [options.arm]
    if options.command == 'report' and options.arm == 'all':
        return subprocess.run([sys.executable, '-m', 'pxrd_heuristic_rruff_validation.delivery'], check=False, timeout=300).returncode
    if options.command == 'status':
        for arm in arms:
            if arm == 'e1':
                completed = sorted(p.stem.replace('.complete', '') for p in (ROOT/'reports/e1').glob('*.complete.json'))
                events = ROOT/'reports/e1/events.jsonl'
                last = json.loads(events.read_text(encoding='utf-8').splitlines()[-1]) if events.exists() else None
                print(json.dumps({'arm':arm,'completed_materials':completed,'last_event':last}))
            else:
                result = ROOT/'reports/e2_results.json'
                data = json.loads(result.read_text(encoding='utf-8')) if result.exists() else {}
                print(json.dumps({'arm':arm,'status':data.get('status','NOT_RUN'),'NN_status':data.get('NN_status','NOT_RUN')}))
        return 0
    command = 'audit' if options.command == 'preflight' else options.command
    started = time.monotonic()
    codes = []
    for arm in arms:
        remaining = 10800 - (time.monotonic() - started)
        if remaining <= 0:
            print('BLOCKED: shared three-hour execution budget exhausted', file=sys.stderr)
            return 2
        codes.append(dispatch(command, arm, timeout=remaining))
    return max(codes)

if __name__ == '__main__':
    raise SystemExit(main())

