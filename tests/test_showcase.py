from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from bs4 import BeautifulSoup
from norway_company_agent.showcase import build_showcase, public_profiles
from norway_company_agent.submission import submission_envelope


class ShowcaseTests(unittest.TestCase):
    def row(self):
        return submission_envelope({'organisation_number': '123456789', 'evidence': {}, 'name': '</script><script>alert(1)</script>'},
                                   run_id='test', started_at='2026-10-13T00:00:00Z', completed_at='2026-10-13T00:00:00Z')

    def test_script_breakout_data_is_escaped_and_static_app_uses_safe_dom_text(self):
        row = self.row()
        row['legal_identity']['name'] = '</script><script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'signalpost'
            build_showcase([row], output, expected_count=1)
            html = (output / 'index.html').read_text()
            soup = BeautifulSoup(html, 'lxml')
            self.assertEqual(len(soup.select('script')), 2)
            data = json.loads(soup.select_one('#data').get_text())
            self.assertEqual(data[0]['identity']['name'], row['legal_identity']['name'])
            self.assertNotIn('innerHTML', html)
            self.assertNotIn('snapshot_path', html)
            self.assertIn("['https:','http:']", html)

    def test_count_audit_and_new_output_requirements_are_enforced(self):
        row = self.row()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Expected 100'):
                build_showcase([row], Path(directory) / 'sample')
            row['claims'][0]['evidence_ids'] = ['missing-source']
            with self.assertRaisesRegex(ValueError, 'requires passing'):
                build_showcase([row], Path(directory) / 'sample', expected_count=1)

    def test_public_data_does_not_export_private_paths_errors_or_raw_registry_spans(self):
        row = self.row()
        row['errors'] = [{'message': '/private/secret-path'}]
        row['evidence'] = [{'id': 'source', 'source_url': 'https://data.brreg.no/', 'source_class': 'official_roles',
                            'retrieved_at': '2026-10-13', 'content_sha256': 'a'*64, 'snapshot_path': '/private/snapshot.bin',
                            'claim_span': 'unnecessary raw registry personal metadata'}]
        raw = json.dumps(public_profiles([row]))
        self.assertNotIn('/private/', raw)
        self.assertNotIn('unnecessary raw registry', raw)


if __name__ == '__main__':
    unittest.main()
