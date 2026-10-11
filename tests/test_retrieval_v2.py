from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from norway_company_agent.acquisition import AcquisitionError, Capture, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.site_research import assess_site, page_kind, research_site
from norway_company_agent.submission import submission_envelope
from norway_company_agent.versioning import source_fingerprint


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = SnapshotStore(self.directory.name)
        self.profile = {"organisation_number": "123456789", "name": "BÆRUM TEST AS",
                        "website": "https://example.no", "evidence": {}}

    def capture(self, url, html, content_type="text/html; charset=windows-1252"):
        body = html.encode("windows-1252")
        return Capture(url, url, 200, content_type, body, "2026-10-12T00:00:00Z", **self.store.save(body))

    def test_frame_contact_proves_company_with_charset_and_auditable_bytes(self):
        pages = {
            "https://example.no/": '<title>BÆRUM TEST AS</title><frame src="menu.htm">',
            "https://example.no/menu.htm": '<a href="kontakt.htm">Kontakt</a>',
            "https://example.no/kontakt.htm": '<title>Kontakt BÆRUM TEST AS</title><footer><div class="footer">BÆRUM TEST AS Org.nr. 123456789</div></footer>',
        }
        session = Mock()
        session.get.side_effect = lambda url, **kwargs: self.capture(url, pages[url])
        result = research_site(self.profile, session)
        self.assertEqual(result["status"], "available")
        self.assertEqual(len(result["value"]["pages"]), 3)
        self.profile["evidence"]["website"] = result
        envelope = submission_envelope(self.profile, run_id="test", started_at="2026-10-12T00:00:00Z", completed_at="2026-10-12T00:01:00Z")
        report = audit_envelopes([envelope], ["123456789"])
        self.assertTrue(report["passed"], report)
        website = next(claim for claim in envelope["claims"] if claim["field"] == "official_website")
        proof = next(source for source in envelope["evidence"] if source["id"] in website["evidence_ids"])
        self.assertEqual(proof["source_url"], "https://example.no/kontakt.htm")
        self.assertIn("BÆRUM", result["value"]["title"])
        source = Path(envelope["evidence"][0]["snapshot_path"])
        source.write_bytes(b"corrupted source")
        self.assertFalse(audit_envelopes([envelope], ["123456789"])["passed"])

    def test_tls_fallback_checks_http_through_same_robots_acquisition(self):
        session = Mock()
        session.get.side_effect = [AcquisitionError("certificate", tls_failure=True),
            self.capture("http://example.no/", '<title>BÆRUM TEST AS</title><footer>Org.nr. 123456789</footer><a href="/kontakt">Kontakt</a>'),
            self.capture("http://example.no/kontakt", '<title>Kontakt</title>')]
        result = research_site(self.profile, session)
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["value"]["url"], "http://example.no/")
        self.assertTrue(all(call.kwargs["robots"] for call in session.get.call_args_list))

    def test_access_denial_never_triggers_http_fallback(self):
        session = Mock()
        session.get.side_effect = AcquisitionError("robots denied", "blocked")
        self.assertEqual(research_site(self.profile, session)["status"], "blocked")
        self.assertEqual(session.get.call_count, 1)

    def test_privacy_pages_are_not_contact_claims(self):
        self.assertEqual(page_kind("https://example.no/legal/privacy"), "legal")
        self.assertEqual(page_kind("https://example.no/kontakt"), "contact")

    def test_contact_footer_conflict_overrides_homepage_match(self):
        pages = [{"url": "https://example.no", "identity_text_excerpt": "Org.nr. 123456789"},
                 {"url": "https://example.no/contact", "identity_text_excerpt": "Org.nr. 987654321"}]
        self.assertFalse(assess_site(self.profile, pages)["publishable"])

    def test_legacy_bold_contact_requires_full_legal_name_and_local_registered_phone(self):
        self.profile["evidence"] = {"registry_live": {"value": {"phone": "92260499"}}}
        page = {"url": "https://example.no/contact", "contact_blocks": [
            {"names": ["Bærum Test AS"], "text": "Bærum Test AS Mobil: 92 26 04 99"}]}
        self.assertTrue(assess_site(self.profile, [page])["publishable"])
        page["contact_blocks"][0]["names"] = ["Bærum Test Holding AS"]
        self.assertFalse(assess_site(self.profile, [page])["publishable"])
        page["contact_blocks"][0]["names"] = ["Bærum Test AS"]
        page["contact_blocks"][0]["text"] = "Bærum Test AS"
        page["full_text"] = "An unrelated contact elsewhere has phone 92 26 04 99"
        self.assertFalse(assess_site(self.profile, [page])["publishable"])

    def test_source_fingerprint_changes_with_code_and_not_location(self):
        root = Path(self.directory.name)
        (root / "src").mkdir()
        code = root / "src" / "a.py"
        code.write_text("version = 1")
        before = source_fingerprint(root)
        code.touch()
        self.assertEqual(before, source_fingerprint(root))
        code.write_text("version = 2")
        self.assertNotEqual(before, source_fingerprint(root))


if __name__ == "__main__":
    unittest.main()
