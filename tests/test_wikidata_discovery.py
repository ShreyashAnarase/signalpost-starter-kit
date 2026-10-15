from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from norway_company_agent.acquisition import AcquisitionError, Capture, SnapshotStore
from norway_company_agent.site_research import research_site
from norway_company_agent.submission import submission_envelope
from norway_company_agent.wikidata_discovery import discover_candidates


class WikidataDiscoveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = SnapshotStore(directory.name)
        self.profile = {"organisation_number": "123456789", "name": "EXACT TEST AS", "evidence": {}}

    def capture(self, url, body, content_type="application/json", status=200):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        return Capture(url, url, status, content_type, raw, "2026-10-12T00:00:00Z", **self.store.save(raw))

    def binding(self, org="123456789", url="https://exact.example/", item="Q123"):
        return {"org": {"type": "literal", "value": org},
                "item": {"type": "uri", "value": "http://www.wikidata.org/entity/" + item},
                "website": {"type": "uri", "value": url}}

    def response(self, *bindings):
        return {"results": {"bindings": list(bindings)}}

    def session(self, *bindings, html=None):
        session = Mock()
        def get(url, **kwargs):
            if url.startswith("https://query.wikidata.org/"):
                return self.capture(url, self.response(*bindings))
            if url.endswith("sitemap.xml"):
                return self.capture(url, "<urlset/>", "application/xml")
            return self.capture(url, html or '<title>EXACT TEST AS</title><footer>Org.nr. 123456789</footer>', "text/html")
        session.get.side_effect = get
        return session

    def test_opt_in_improves_fixture_without_publishing_provider_as_claim_evidence(self):
        baseline_session = self.session(self.binding())
        self.assertEqual(research_site(self.profile, baseline_session)["status"], "not_found")
        baseline_session.get.assert_not_called()
        session = self.session(self.binding())
        record = research_site(self.profile, session, wikidata_discovery=True)
        self.assertEqual(record["status"], "available")
        attempt = record["value"]["discovery_attempts"][0]
        self.assertTrue(attempt["identity"]["publishable"])
        self.assertEqual(attempt["candidate_provenance"]["organisation_number"], "123456789")
        self.assertTrue(Path(attempt["candidate_provenance"]["snapshot_path"]).exists())
        self.profile["evidence"]["website"] = record
        envelope = submission_envelope(self.profile, run_id="fixture", started_at="2026-10-12T00:00:00Z", completed_at="2026-10-12T00:01:00Z")
        self.assertTrue(any(claim["field"] == "official_website" for claim in envelope["claims"]))
        self.assertFalse(any(source["source_url"].startswith("https://query.wikidata.org/") for source in envelope["evidence"]))

    def test_existing_registry_candidate_skips_provider_even_when_enabled(self):
        self.profile["website"] = "https://exact.example/"
        session = self.session()
        self.assertEqual(research_site(self.profile, session, wikidata_discovery=True)["status"], "available")
        self.assertFalse(any(call.args[0].startswith("https://query.wikidata.org/") for call in session.get.call_args_list))

    def test_wrong_org_and_corrupt_bindings_are_rejected(self):
        session = self.session(self.binding(org="987654321"))
        candidates, diagnostic = discover_candidates("123456789", session)
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostic["status"], "ambiguous")
        self.assertEqual(len(diagnostic["rejections"]), 1)
        session.get.side_effect = lambda url, **kw: self.capture(url, '{"results":false}')
        self.assertEqual(discover_candidates("123456789", session)[1]["status"], "failed")

    def test_provider_failure_empty_and_budget_are_explicit(self):
        session = self.session()
        self.assertEqual(research_site(self.profile, session, wikidata_discovery=True)["status"], "not_found")
        for status in (403, 429, 500):
            session.get.side_effect = lambda url, **kw: self.capture(url, {}, status=status)
            record = research_site(self.profile, session, wikidata_discovery=True)
            self.assertEqual(record["status"], "blocked" if status != 500 else "source_error")
        session.get.side_effect = AcquisitionError("Research request budget exhausted")
        record = research_site(self.profile, session, wikidata_discovery=True)
        self.assertEqual(record["status"], "source_error")
        self.assertIn("budget", record["candidate_discovery"]["error"])

    def test_parent_subsidiary_franchise_similar_name_and_conflict_do_not_pass(self):
        for html in (
            '<title>EXACT TEST GROUP AS</title><footer>Org.nr. 987654321</footer>',
            '<title>EXACT TEST SUBSIDIARY AS</title><footer>Org.nr. 987654321</footer>',
            '<title>EXACT TEST franchise</title><p>Franchise operated by another entity</p>',
            '<title>EXACT TESTING AS</title><p>Similar name only</p>',
            '<title>EXACT TEST AS</title><footer>Org.nr. 987654321</footer>',
        ):
            with self.subTest(html=html):
                record = research_site(self.profile, self.session(self.binding(), html=html), wikidata_discovery=True)
                self.assertEqual(record["status"], "ambiguous")
                self.assertFalse(record["discovery_attempts"][0]["identity"]["publishable"])

    def test_one_query_and_max_three_candidates_with_invalid_org_no_query(self):
        session = self.session(*(self.binding(url=f"https://candidate{i}.example/", item=f"Q{i+1}") for i in range(4)))
        candidates, diagnostic = discover_candidates("123456789", session)
        self.assertEqual(len(candidates), 3)
        self.assertTrue(diagnostic["candidate_limit_reached"])
        self.assertEqual(session.get.call_count, 1)
        self.assertTrue(session.get.call_args.kwargs["robots"])
        self.assertEqual(session.get.call_args.kwargs["attempts"], 1)
        session.reset_mock()
        self.assertEqual(discover_candidates('123" injection', session)[0], [])
        session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
