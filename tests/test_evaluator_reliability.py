from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evaluator', ROOT / 'scripts/evaluate_signalpost.py')
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


@unittest.skipUnless(os.name == 'posix', 'POSIX process group supervision')
class EvaluatorReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'scripts').mkdir()
        self.batch = self.root / 'batch.txt'
        self.bulk = self.root / 'bulk.csv'
        self.batch.write_text('123456789\n')
        self.bulk.write_text('organisasjonsnummer,navn\n123456789,Example AS\n')

    def script(self, name, body):
        path = self.root / 'scripts' / name
        path.write_text(body)
        return path

    def run_fixture(self, timeout=None):
        args = ['--organisations', str(self.batch), '--bulk', str(self.bulk),
                '--output-dir', str(self.root / 'run'), '--run-id', 'fixture']
        if timeout is not None:
            args += ['--evaluator-timeout-seconds', str(timeout)]
        with patch.object(evaluator, 'ROOT', self.root):
            code = evaluator.main(args)
        status = json.loads((self.root / 'run/evaluator-status.json').read_text())
        return code, status

    def assert_stopped(self, pid):
        # Reparented zombies may await init's reaper; they cannot run or write.
        for _ in range(100):
            path = Path(f'/proc/{pid}/stat')
            if not path.exists() or path.read_text().split(') ', 1)[1].startswith('Z'):
                return
            time.sleep(.01)
        self.fail(f'Process {pid} still running')

    def sleeper(self, name):
        return self.script(name, """import os, pathlib, subprocess, sys, time
root = pathlib.Path(__file__).resolve().parents[1]
child = subprocess.Popen([sys.executable, '-c', "import pathlib, os, time; pathlib.Path(" + repr(str(root / 'descendant.pid')) + ").write_text(str(os.getpid())); time.sleep(60)"])
(root / 'leader.pid').write_text(str(os.getpid()))
while not (root / 'descendant.pid').exists(): time.sleep(.01)
time.sleep(60)
""")

    def test_timeout_kills_sleeping_batch_and_descendant_preserves_unrelated_process(self):
        self.sleeper('run_competition_batch.py')
        self.script('package_submission.py', "raise RuntimeError('must not package')")
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.addCleanup(lambda: (unrelated.kill(), unrelated.wait()) if unrelated.poll() is None else None)
        before = self.bulk.read_bytes(), self.batch.read_bytes()
        code, status = self.run_fixture(1)
        self.assertEqual(code, 124)
        self.assertEqual(status['status'], 'timed_out')
        self.assertEqual(status['stage'], 'batch')
        self.assertIsNone(status['subprocess_returncode'])
        self.assertFalse(status['package_accepted'])
        self.assertFalse((self.root / 'run/package').exists())
        for name in ['leader.pid', 'descendant.pid']:
            self.assert_stopped(int((self.root / name).read_text()))
        self.assertIsNone(unrelated.poll())
        self.assertEqual(before, (self.bulk.read_bytes(), self.batch.read_bytes()))

    def test_timeout_covers_packaging_and_partial_outputs(self):
        self.script('run_competition_batch.py', "import pathlib; pathlib.Path(__file__).resolve().parents[1].joinpath('run/envelopes.jsonl').write_text('partial')")
        self.sleeper('package_submission.py')
        code, status = self.run_fixture(1)
        self.assertEqual(code, 124)
        self.assertEqual(status['stage'], 'packaging')
        self.assertEqual(status['status'], 'timed_out')
        self.assertEqual((self.root / 'run/envelopes.jsonl').read_text(), 'partial')
        for name in ['leader.pid', 'descendant.pid']:
            self.assert_stopped(int((self.root / name).read_text()))

    def test_subprocess_exit_code_is_preserved_and_packaging_skipped(self):
        self.script('run_competition_batch.py', 'raise SystemExit(7)')
        self.script('package_submission.py', "raise RuntimeError('must not package')")
        code, status = self.run_fixture()
        self.assertEqual(code, 7)
        self.assertEqual(status['subprocess_returncode'], 7)
        self.assertEqual(status['status'], 'failed')
        self.assertFalse(status['package_accepted'])
        self.assertIsNone(status['evaluator_timeout_seconds'])

    def test_signal_exit_and_packaging_failure_are_distinct(self):
        self.script('run_competition_batch.py', 'import os, signal; os.kill(os.getpid(), signal.SIGTERM)')
        code, status = self.run_fixture()
        self.assertEqual(code, 128 + signal.SIGTERM)
        self.assertEqual(status['subprocess_returncode'], -signal.SIGTERM)
        (self.root / 'run').rename(self.root / 'signal-run')
        self.script('run_competition_batch.py', 'pass')
        self.script('package_submission.py', 'raise SystemExit(9)')
        code, status = self.run_fixture()
        self.assertEqual(code, 9)
        self.assertEqual(status['stage'], 'packaging')
        self.assertFalse(status['package_accepted'])

    def test_deadline_is_shared_between_stages(self):
        self.script('run_competition_batch.py', 'import time; time.sleep(.65)')
        self.script('package_submission.py', 'import time; time.sleep(.65)')
        code, status = self.run_fixture(1)
        self.assertEqual(code, 124)
        self.assertEqual(status['stage'], 'packaging')

    def test_failed_leader_cleanup_stops_its_remaining_descendant(self):
        script = self.sleeper('run_competition_batch.py')
        script.write_text(script.read_text().replace('\ntime.sleep(60)\n', '\nraise SystemExit(7)\n'))
        code, status = self.run_fixture(5)
        self.assertEqual(code, 7)
        self.assertEqual(status['status'], 'failed')
        self.assert_stopped(int((self.root / 'descendant.pid').read_text()))

    def test_spawn_error_marks_run_failed(self):
        with patch.object(evaluator.subprocess, 'Popen', side_effect=OSError('fixture spawn failure')):
            code, status = self.run_fixture()
        self.assertEqual(code, 1)
        self.assertEqual(status['status'], 'failed')
        self.assertIn('fixture spawn failure', status['error'])
        self.assertFalse(status['package_accepted'])

    def test_invalid_timeout_and_forwarded_options_do_not_create_outputs(self):
        for option in [('0',), ('-1',), ('nan',), ('inf',)]:
            with self.subTest(option=option), self.assertRaises(SystemExit) as raised:
                evaluator.main(['--organisations', str(self.batch), '--bulk', str(self.bulk),
                                '--output-dir', str(self.root / 'run'), '--run-id', 'bad',
                                '--evaluator-timeout-seconds', *option])
            self.assertEqual(raised.exception.code, 2)
        with self.assertRaises(SystemExit):
            evaluator.main(['--organisations', str(self.batch), '--bulk', str(self.bulk),
                            '--output-dir', str(self.root / 'run'), '--run-id', 'bad', '--output', 'escape'])
        self.assertFalse((self.root / 'run').exists())

    def test_real_invalid_batch_options_and_successful_arbitrary_batch(self):
        for name, extras, batch in [
            ('duplicate', [], '123456789\n123456789\n'),
            ('workers', ['--workers', '0'], '123456789\n'),
            ('modules', ['--modules', 'invalid'], '123456789\n'),
            ('success', ['--modules', '', '--workers', '1'], '123456789\n987654321\n111222333\n'),
        ]:
            with self.subTest(name=name):
                self.batch.write_text(batch)
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/evaluate_signalpost.py'),
                                         '--organisations', str(self.batch), '--bulk', str(self.bulk),
                                         '--output-dir', str(self.root / name), '--run-id', name,
                                         '--evaluator-timeout-seconds', '30', *extras],
                                        capture_output=True, text=True, timeout=35)
                status = json.loads((self.root / name / 'evaluator-status.json').read_text())
                self.assertEqual(result.returncode == 0, name == 'success', result.stderr)
                self.assertEqual(status['package_accepted'], name == 'success')
                if name == 'success':
                    manifest = json.loads((self.root / name / 'package/manifest.json').read_text())
                    self.assertEqual(manifest['envelopes'], 3)
                    self.assertTrue(manifest['audit']['passed'])
                else:
                    self.assertFalse((self.root / name / 'package').exists())


if __name__ == '__main__':
    unittest.main()
