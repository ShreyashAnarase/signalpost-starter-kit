#!/usr/bin/env python3
"""Run the current company batch CLI and publish an audited evidence package."""
from __future__ import annotations
import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('Timeout must be finite and positive')
    return number


def run_stage(command, deadline):
    """Own a fresh POSIX process group, including inherited worker descendants."""
    remaining = None if deadline is None else deadline - time.monotonic()
    if remaining is not None and remaining <= 0:
        raise subprocess.TimeoutExpired(command, 0)
    process = subprocess.Popen(command, start_new_session=True)
    try:
        return process.wait(timeout=remaining)
    finally:
        # Also clean descendants when the leader exits unsuccessfully or leaves
        # workers behind. Never signal the wrapper's or an unrelated process group.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--organisations', required=True)
    parser.add_argument('--bulk', required=True)
    parser.add_argument('--output-dir', required=True, help='New run directory; package will be in package/')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--evaluator-timeout-seconds', type=positive_seconds,
                        help='Explicit wall time for evaluator stages, including preprocessing and packaging; no default')
    parser.add_argument('--wikidata-discovery', action='store_true', help='Opt into exact-org candidate discovery')
    parser.add_argument('--nav-jobs', action='store_true', help='Optional official NAV feed with evaluator-supplied credentials')
    args, budgets = parser.parse_known_args(argv)
    allowed = {'--workers', '--deadline-seconds', '--company-timeout', '--request-timeout',
               '--max-pages', '--max-requests', '--modules', '--expected-count',
               '--search-provider', '--search-max-queries', '--search-price-per-1000', '--search-budget-usd',
               '--nav-max-pages', '--nav-max-details', '--nav-lookback-days', '--nav-timeout', '--nav-max-requests'}
    allowed.update({'--previous-output', '--changes-output', '--nav-cache-input', '--nav-cache-output'})
    if len(budgets) % 2 or any(budgets[index] not in allowed for index in range(0, len(budgets), 2)):
        parser.error('Extra arguments must be supported budget/--modules options followed by values')
    if os.name != 'posix':
        parser.error('Evaluator process-tree supervision requires POSIX process groups')
    output = Path(args.output_dir).resolve()
    batch = Path(args.organisations).resolve()
    bulk = Path(args.bulk).resolve()
    if not batch.is_file() or not bulk.is_file():
        parser.error('Organisation batch and bulk snapshot must be existing files')
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(str(exc))
    deadline = None if args.evaluator_timeout_seconds is None else started + args.evaluator_timeout_seconds
    commands = [
        ('batch', [sys.executable, str(ROOT / 'scripts/run_competition_batch.py'),
                   '--organisations', str(batch), '--bulk', str(bulk),
                   '--output', str(output / 'envelopes.jsonl'),
                   '--profiles-output', str(output / 'profiles.jsonl'),
                   '--report', str(output / 'report.json'), '--snapshot-dir', str(output / 'snapshots'),
                   '--run-id', args.run_id, *(['--wikidata-discovery'] if args.wikidata_discovery else []),
                   *(['--nav-jobs'] if args.nav_jobs else []), *budgets]),
        ('packaging', [sys.executable, str(ROOT / 'scripts/package_submission.py'),
                       '--input', str(output / 'envelopes.jsonl'), '--organisations', str(batch),
                       '--output-dir', str(output / 'package')]),
    ]
    status, returncode, child_returncode, stage = 'failed', 1, None, 'batch'
    error = None
    try:
        for stage, command in commands:
            child_returncode = None
            child_returncode = run_stage(command, deadline)
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(command, args.evaluator_timeout_seconds)
            if child_returncode:
                returncode = child_returncode if child_returncode > 0 else 128 - child_returncode
                break
        else:
            status, returncode = 'completed', 0
    except subprocess.TimeoutExpired:
        status, returncode = 'timed_out', 124
        error = 'Explicit whole-evaluator deadline exhausted'
    except (OSError, KeyboardInterrupt) as exc:
        returncode = 130 if isinstance(exc, KeyboardInterrupt) else 1
        error = f'{type(exc).__name__}: {exc}'
    result = {'status': status, 'stage': stage, 'exit_code': returncode,
              'subprocess_returncode': child_returncode, 'error': error,
              'elapsed_seconds': time.monotonic() - started,
              'evaluator_timeout_seconds': args.evaluator_timeout_seconds,
              'package_accepted': status == 'completed',
              'artifacts': 'complete audited package' if status == 'completed' else 'failed/partial; not an accepted evaluator run',
              'boundary': 'Offline byte/locator validation is not claim truth or an official score.'}
    temporary = output / 'evaluator-status.json.tmp'
    temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output / 'evaluator-status.json')
    return returncode


if __name__ == '__main__':
    raise SystemExit(main())
