from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.acquisition import SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.evidence import evidence
from norway_company_agent.packaging import package_submission
from norway_company_agent.pipeline import failed_profile
from norway_company_agent.submission import merge_refresh, submission_envelope


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.acquisition = self.root / 'acquisition'
        self.store = SnapshotStore(self.acquisition)

    def envelope(self, name='Eksempel AS'):
        raw = {'organisasjonsnummer': '123456789', 'navn': name,
               'organisasjonsform': {'kode': 'AS'}, 'antallAnsatte': 0}
        captured = self.store.save(json.dumps(raw, ensure_ascii=False).encode())
        record = evidence('registry_live', 'available', 'official_registry_live',
                          'https://data.brreg.no/enhetsregisteret/api/enheter/123456789',
                          value={'organisation_number': '123456789', 'name': name,
                                 'legal_form': 'AS', 'employees': 0},
                          retrieved_at='2026-10-12T00:00:00Z', content_sha256=captured['content_sha256'])
        record['snapshot_path'] = captured['snapshot_path']
        return submission_envelope({'organisation_number': '123456789', 'evidence': {'registry_live': record}},
                                   run_id='test', started_at='2026-10-12T00:00:00Z', completed_at='2026-10-12T00:01:00Z')

    def test_relocation_preserves_bytes_claims_and_locators_after_acquisition_deleted(self):
        envelope = self.envelope()
        before = copy.deepcopy(envelope)
        package = self.root / 'package'
        manifest = package_submission([envelope], ['123456789'], package)
        portable = [json.loads(line) for line in (package / 'envelopes.jsonl').read_text().splitlines()]
        self.assertEqual(envelope, before)
        for source, original in zip(portable[0]['evidence'], before['evidence']):
            self.assertFalse(Path(source['snapshot_path']).is_absolute())
            self.assertEqual({k: v for k, v in source.items() if k != 'snapshot_path'},
                             {k: v for k, v in original.items() if k != 'snapshot_path'})
        self.assertEqual(portable[0]['claims'], before['claims'])
        shutil.rmtree(self.acquisition)
        moved = self.root / 'moved' / 'package'
        moved.parent.mkdir()
        shutil.move(package, moved)
        self.assertTrue(audit_envelopes(portable, ['123456789'], snapshot_root=moved)['passed'])
        completed = subprocess.run([sys.executable, str(ROOT / 'scripts/audit_submission.py'),
                                    '--input', str(moved / 'envelopes.jsonl'),
                                    '--organisations', str(moved / 'organisations.jsonl'),
                                    '--report', str(self.root / 'audit.json')], cwd=self.root,
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(manifest['envelopes_sha256'], hashlib.sha256((moved / 'envelopes.jsonl').read_bytes()).hexdigest())

    def test_refresh_history_and_idempotent_repackage(self):
        previous = self.envelope('Gammelt AS')
        refreshed = merge_refresh(self.envelope('Nytt AS'), previous)
        self.assertTrue(refreshed['changes'])
        one, two = self.root / 'one', self.root / 'two'
        manifest = package_submission([refreshed], ['123456789'], one)
        portable = [json.loads((one / 'envelopes.jsonl').read_text())]
        package_submission(portable, ['123456789'], two, snapshot_root=one)
        self.assertEqual((one / 'envelopes.jsonl').read_bytes(), (two / 'envelopes.jsonl').read_bytes())
        self.assertEqual(len(manifest['snapshots']), 2)
        prior_ids = {source_id for change in refreshed['changes'] for source_id in change['old_evidence_ids']}
        self.assertTrue(prior_ids)
        self.assertTrue(prior_ids.issubset({s['id'] for s in portable[0]['evidence']}))

    def test_corruption_invalid_membership_and_existing_output_rejected(self):
        envelope = self.envelope()
        with self.assertRaises(ValueError):
            package_submission([envelope], ['987654321'], self.root / 'wrong')
        self.assertFalse((self.root / 'wrong').exists())
        Path(envelope['evidence'][0]['snapshot_path']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            package_submission([envelope], ['123456789'], self.root / 'bad')
        existing = self.root / 'existing'
        existing.mkdir()
        with self.assertRaises(FileExistsError):
            package_submission([], [], existing)

    def test_relative_traversal_and_symlink_escape_are_rejected(self):
        envelope = self.envelope()
        package = self.root / 'package'
        package.mkdir()
        envelope['evidence'][0]['snapshot_path'] = '../acquisition/' + Path(envelope['evidence'][0]['snapshot_path']).name
        self.assertFalse(audit_envelopes([envelope], ['123456789'], snapshot_root=package)['passed'])
        (package / 'linked').symlink_to(self.acquisition, target_is_directory=True)
        envelope['evidence'][0]['snapshot_path'] = 'linked/' + Path(envelope['evidence'][0]['snapshot_path']).name
        self.assertFalse(audit_envelopes([envelope], ['123456789'], snapshot_root=package)['passed'])

    def test_arbitrary_failed_batch_has_one_terminal_envelope_per_input(self):
        organisations = [str(100000000 + i) for i in range(1101)]
        envelopes = [submission_envelope(failed_profile({'organisation_number': org}, ['registry_live'], 'test failure'),
                                        run_id='test', started_at='2026-10-12T00:00:00Z', completed_at='2026-10-12T00:01:00Z')
                     for org in organisations]
        manifest = package_submission(envelopes, organisations, self.root / 'failures')
        self.assertEqual(manifest['envelopes'], 1101)
        self.assertTrue(manifest['audit']['passed'])
        self.assertTrue(all(row['run']['terminal_status'] == 'failed' for row in envelopes))
        with self.assertRaises(ValueError):
            package_submission(envelopes + envelopes[:1], organisations, self.root / 'duplicates')

    def test_every_cross_envelope_locator_is_checked_even_with_shared_evidence_id(self):
        first = self.envelope()
        second = copy.deepcopy(first)
        second['organisation_number'] = '987654321'
        first['evidence'][0]['claim_span'] = json.dumps('Tampered name')
        report = audit_envelopes([first, second], ['123456789', '987654321'])
        self.assertFalse(report['passed'])
        self.assertTrue(any(error.get('evidence_id') == first['evidence'][0]['id'] for error in report['errors']))

    def test_audit_report_cannot_overwrite_inputs_or_retained_bytes(self):
        envelope = self.envelope()
        source = self.root / 'envelopes.jsonl'
        source.write_text(json.dumps(envelope) + '\n')
        batch = self.root / 'batch.txt'
        batch.write_text('123456789\n')
        for protected in [source, batch, Path(envelope['evidence'][0]['snapshot_path'])]:
            before = protected.read_bytes()
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/audit_submission.py'),
                                     '--input', str(source), '--organisations', str(batch),
                                     '--report', str(protected)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(protected.read_bytes(), before)

    def test_copy_failure_never_publishes_partial_package_or_modifies_source(self):
        from unittest.mock import patch
        envelope = self.envelope()
        original = Path(envelope['evidence'][0]['snapshot_path'])
        before = original.read_bytes()
        with patch('norway_company_agent.packaging.shutil.copyfile', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                package_submission([envelope], ['123456789'], self.root / 'partial')
        self.assertFalse((self.root / 'partial').exists())
        self.assertEqual(list(self.root.glob('.signalpost-package-*')), [])
        self.assertEqual(original.read_bytes(), before)
        original.unlink()
        with self.assertRaises(ValueError):
            package_submission([envelope], ['123456789'], self.root / 'missing')
        self.assertFalse((self.root / 'missing').exists())

    def test_nonobject_input_is_rejected_without_publication(self):
        with self.assertRaises(ValueError):
            package_submission([None], ['123456789'], self.root / 'invalid')
        self.assertFalse((self.root / 'invalid').exists())

    def test_malformed_locators_fail_audit_without_crashing(self):
        for locator in [{}, {'type': ['json_pointer']},
                        {'type': 'csv_row'},
                        {'type': 'css_text', 'selector': '['},
                        {'type': 'json_pointer', 'pointer': '/missing'}]:
            with self.subTest(locator=locator):
                envelope = self.envelope()
                envelope['evidence'][0]['source_locator'] = locator
                self.assertFalse(audit_envelopes([envelope], ['123456789'])['passed'])

    def test_relocated_dom_and_jsonld_history_rejects_locator_and_byte_tampering(self):
        from test_site_events import DatedEventTests
        helper = DatedEventTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        html = '<article><h1>Opening</h1><time datetime="2026-10-01"/></article>'
        item = {'@type': 'NewsArticle', 'headline': 'New branch', 'datePublished': '2026-10-02', 'url': 'https://example.test/'}
        _, previous = helper.record(html)
        _, current = helper.record('<h1>New branch</h1><script type="application/ld+json">' + json.dumps(item) + '</script>')
        refreshed = merge_refresh(current, previous)
        package_submission([refreshed], ['123456789'], self.root / 'events')
        shutil.rmtree(helper.root / 'snapshots')
        shutil.move(self.root / 'events', self.root / 'relocated-events')
        root = self.root / 'relocated-events'
        portable = [json.loads((root / 'envelopes.jsonl').read_text())]
        kinds = {s['source_locator']['type'] for s in portable[0]['evidence']}
        self.assertTrue({'dom_fields', 'jsonld_pointer'}.issubset(kinds))
        self.assertTrue(audit_envelopes(portable, ['123456789'], snapshot_root=root)['passed'])
        for kind in ['dom_fields', 'jsonld_pointer']:
            changed = copy.deepcopy(portable)
            source = next(s for s in changed[0]['evidence'] if s['source_locator']['type'] == kind)
            if kind == 'jsonld_pointer':
                source['source_locator']['script_index'] = 99
            else:
                source['source_locator']['fields']['date']['value'] = '2026-09-01'
            self.assertFalse(audit_envelopes(changed, ['123456789'], snapshot_root=root)['passed'])
        source = next(s for s in portable[0]['evidence'] if s['source_locator']['type'] == 'dom_fields')
        (root / source['snapshot_path']).write_bytes(b'tampered history')
        self.assertFalse(audit_envelopes(portable, ['123456789'], snapshot_root=root)['passed'])

    def test_evaluator_clean_offline_command(self):
        bulk = self.root / 'bulk.csv'
        bulk.write_text('organisasjonsnummer,navn\n123456789,Eksempel AS\n', encoding='utf-8')
        batch = self.root / 'batch.txt'
        batch.write_text('123456789\n987654321\n')
        completed = subprocess.run([sys.executable, str(ROOT / 'scripts/evaluate_signalpost.py'),
                                    '--organisations', str(batch), '--bulk', str(bulk),
                                    '--output-dir', str(self.root / 'run'), '--run-id', 'offline',
                                    '--modules', '', '--workers', '1'], cwd=self.root,
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        manifest = json.loads((self.root / 'run/package/manifest.json').read_text())
        self.assertEqual(manifest['envelopes'], 2)
        self.assertTrue(manifest['audit']['passed'])


if __name__ == '__main__':
    unittest.main()
