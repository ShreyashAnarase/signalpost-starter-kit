from __future__ import annotations

import gzip
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.acquisition import AcquisitionError, Capture, ResearchSession, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.html_text import decode_html
from norway_company_agent.site_research import extract_site_facts, read_page
from norway_company_agent.submission import submission_envelope


class CompressedHTMLTests(unittest.TestCase):
    def test_compressed_source_keeps_original_bytes_and_audits_decoded_evidence(self):
        raw = gzip.compress('<h1>Example</h1><footer>Org.nr. 123456789</footer>'.encode())
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(directory)
            class Session:
                def get(self, url, **kwargs):
                    return Capture(url, url, 200, 'text/html', raw, '2026-10-14T00:00:00Z', **store.save(raw))
            page, _ = read_page(Session(), 'https://example.no/', 'homepage')
            profile = {'organisation_number': '123456789', 'name': 'EXAMPLE AS', 'evidence': {}}
            facts = extract_site_facts(profile, [page])
            self.assertTrue(any(f['field'] == 'official_website' for f in facts))
            self.assertEqual(Path(page['snapshot_path']).read_bytes(), raw)
            self.assertEqual(page['content_sha256'], hashlib.sha256(raw).hexdigest())
            profile['evidence']['website'] = {'status': 'available', 'value': {'facts': facts}}
            envelope = submission_envelope(profile, run_id='gzip', started_at=page['retrieved_at'], completed_at=page['retrieved_at'])
            self.assertTrue(audit_envelopes([envelope], ['123456789'])['passed'])

    def test_corrupt_and_oversized_compression_fail_closed(self):
        with self.assertRaises(ValueError):
            decode_html(b'\x1f\x8bnot-valid-gzip')
        with patch('norway_company_agent.html_text.MAX_DECOMPRESSED_HTML_BYTES', 100):
            with self.assertRaises(ValueError):
                decode_html(gzip.compress(b'x' * 101))
            self.assertEqual(decode_html(gzip.compress(b'x' * 100))[0], 'x' * 100)

    def test_bad_compressed_page_is_an_explicit_acquisition_failure(self):
        class Session:
            def get(self, url, **kwargs):
                return Capture(url, url, 200, 'text/html', b'\x1f\x8bbad', '2026-10-14T00:00:00Z', 'unused', '')
        with self.assertRaises(AcquisitionError):
            read_page(Session(), 'https://example.no/', 'homepage')

    def test_compressed_robots_disallow_is_enforced_and_corruption_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            for raw, allowed in [(gzip.compress(b'User-agent: *\nDisallow: /private\n'), False),
                                 (gzip.compress(b'User-agent: *\nAllow: /\n'), True),
                                 (b'\x1f\x8bbad-gzip', False)]:
                session = ResearchSession(SnapshotStore(directory))
                capture = Capture('https://example.no/robots.txt', 'https://example.no/robots.txt',
                                  200, 'text/plain', raw, '2026-10-14T00:00:00Z', 'unused', '')
                with patch.object(session, 'get', return_value=capture):
                    self.assertEqual(session._allowed('https://example.no/private'), allowed)


if __name__ == '__main__':
    unittest.main()
