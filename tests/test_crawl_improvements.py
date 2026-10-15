from __future__ import annotations

import copy
import json
import os
import socket
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from norway_company_agent import network, site_events, site_research
from norway_company_agent.acquisition import Capture, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.submission import submission_envelope


class CrawlImprovementTests(unittest.TestCase):
    def test_property_heading_and_shared_manager_address_do_not_verify_ownership(self):
        profile = {'organisation_number': '123456789', 'name': 'EXAMPLE KONTORPARK AS', 'evidence': {
            'registry_live': {'value': {'business_address': {'adresse': ['Storgata 2'], 'postnummer': '0123'}}}}}
        html = '<h1>Offices in Example Kontorpark</h1><footer><address>Another Manager AS Storgata 2, 0123 Oslo</address></footer>'
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(directory)
            class Session:
                def get(self, url, **kwargs):
                    raw = html.encode()
                    return Capture(url, url, 200, 'text/html', raw, '2026-10-14T00:00:00Z', **store.save(raw))
            page, _ = site_research.read_page(Session(), 'https://manager.no/offices', 'contact')
            assessment = site_research.assess_site(profile, [page])
            self.assertFalse(assessment['publishable'])
            self.assertIn('another company', assessment['reasons'][0])

    def test_company_address_owner_matches_and_designer_copyright_is_separate(self):
        profile = {'organisation_number': '123456789', 'name': 'EXAMPLE WIDGET AS', 'evidence': {
            'registry_live': {'value': {'business_address': {'adresse': ['Storgata 2'], 'postnummer': '0123'}}}}}
        html = '<h1>Example Widget</h1><footer><address>Example Widget AS Storgata 2, 0123 Oslo</address><p>Web design by Another Software AS</p></footer>'
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(directory)
            class Session:
                def get(self, url, **kwargs):
                    raw = html.encode()
                    return Capture(url, url, 200, 'text/html', raw, '2026-10-14T00:00:00Z', **store.save(raw))
            page, _ = site_research.read_page(Session(), 'https://example.no/', 'homepage')
            self.assertTrue(site_research.assess_site(profile, [page])['publishable'])

    def test_english_and_vat_owners_verify_but_conflicts_still_abstain(self):
        profile = {"organisation_number": "123456789", "name": "EXAMPLE AS", "evidence": {}}
        for text in ["Organisation number: 123456789", "Organization number: 123 456 789", "EXAMPLE AS NO 123 456 789 MVA"]:
            page = {"url": "https://example.no/", "identity_text_excerpt": text}
            self.assertTrue(site_research.assess_site(profile, [page])["publishable"], text)
            conflict = {"url": "https://example.no/privacy", "identity_text_excerpt": "NO 987654321 MVA"}
            self.assertFalse(site_research.assess_site(profile, [page, conflict])["publishable"])
        self.assertEqual(site_research.legal_org_numbers("NO 123456789 orders, 123 456 789 phone"), set())

    def test_verified_crawl_reaches_both_event_families_before_more_legal_pages(self):
        queue = [("/kontakt", "contact"), ("/privacy", "legal"), ("/news", "news"), ("/jobs", "careers")]
        self.assertEqual(site_research.next_crawl_page(queue.copy(), verified=False, visits=Counter())[1], "contact")
        visits = Counter()
        self.assertEqual(site_research.next_crawl_page(queue, verified=True, visits=visits), ("/jobs", "careers"))
        visits["careers"] += 1
        queue.append(("/jobs/developer", "careers"))
        self.assertEqual(site_research.next_crawl_page(queue, verified=True, visits=visits), ("/news", "news"))
        visits["news"] += 1
        queue.append(("/news/new-office", "news"))
        self.assertEqual(site_research.next_crawl_page(queue, verified=True, visits=visits), ("/jobs/developer", "careers"))

    def test_unicode_paths_are_encoded_without_changing_encoded_paths(self):
        soup = BeautifulSoup('<a href="/personvernerklæring">Personvern</a><a href="/nyheter/økt-vekst">Nyheter</a>', "lxml")
        links = site_research.page_links("https://example.no/", soup)
        self.assertIn(("https://example.no/personvernerkl%C3%A6ring", "legal"), links)
        soup = BeautifulSoup('<a href="/nyheter/%C3%B8kt-vekst">Nyheter</a>', "lxml")
        self.assertEqual(site_research.page_links("https://example.no/", soup)[0][0], "https://example.no/nyheter/%C3%B8kt-vekst")

    def test_labelled_norwegian_publication_date_has_auditable_original_fields(self):
        html = '<main><a href="/nyheter/">Nyheter</a><h1>New branch</h1><div><span>Dato</span>24. september 2026</div><p>Company update.</p></main><footer>Organisation number: 123456789</footer>'
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(directory)
            class Session:
                def get(self, url, **kwargs):
                    raw = html.encode()
                    return Capture(url, url, 200, "text/html", raw, "2026-10-13T00:00:00Z", **store.save(raw))
            profile = {"organisation_number": "123456789", "name": "EXAMPLE AS", "evidence": {}}
            page, _ = site_research.read_page(Session(), "https://example.no/nyheter/new-branch/", "news")
            facts = site_research.extract_site_facts(profile, [page])
            event = next(f for f in facts if f["field"] == "company_news")
            self.assertEqual(event["value"]["date_published"], "2026-09-24")
            self.assertEqual(event["source_locator"]["fields"]["date"]["value"], "Dato 24. september 2026")
            profile["evidence"]["website"] = {"status": "available", "value": {"facts": facts}}
            envelope = submission_envelope(profile, run_id="test", started_at=page["retrieved_at"], completed_at=page["retrieved_at"])
            self.assertTrue(audit_envelopes([envelope], ["123456789"])["passed"])
            changed = copy.deepcopy(envelope)
            source = next(e for e in changed["evidence"] if e["source_locator"]["type"] == "dom_fields")
            source["source_locator"]["fields"]["date"]["value"] = "Dato 25. september 2026"
            self.assertFalse(audit_envelopes([changed], ["123456789"])["passed"])

    def test_dates_in_prose_footer_indexes_and_deadlines_are_not_publication_dates(self):
        for html, url in [
            ('<main><h1>News</h1><div>Dato 24. september 2026</div></main>', 'https://example.no/nyheter/'),
            ('<main><a href="/nyheter/">News</a><h1>Story</h1><p>Our event took place on 24. september 2026</p></main>', 'https://example.no/nyheter/story/'),
            ('<main><a href="/nyheter/">News</a><h1>Story</h1><p>Søknadsfrist: 24. september 2026</p></main>', 'https://example.no/nyheter/story/'),
            ('<main><a href="/nyheter/">News</a><h1>Story</h1></main><footer>Dato 24. september 2026</footer>', 'https://example.no/nyheter/story/'),
            ('<main><a href="/nyheter/">News</a><h1>Story</h1><p>Dato 24. september 2026</p><p>Dato 25. september 2026</p></main>', 'https://example.no/nyheter/story/'),
        ]:
            self.assertEqual(site_events.dated_events(BeautifulSoup(html, 'lxml'), url, 'news'), [], html)
        self.assertIsNone(site_events.publication_date('Dato 31. februar 2026'))


class DNSCacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = network.DNSValidationCache()
        self.documents = [
            {"Status": 0, "TC": False, "Question": [{"name": "example.no.", "type": 1}],
             "Answer": [{"name": "example.no.", "type": 1, "TTL": 60, "data": "8.8.8.8"}]},
            {"Status": 0, "TC": False, "Question": [{"name": "example.no.", "type": 28}],
             "Authority": [{"name": "example.no.", "type": 6, "TTL": 30, "data": "ns.example.no. hostmaster.example.no. 1 60 60 60 3600"}]},
        ]

    def validate(self, url="https://example.no/"):
        return network.assert_public_url(url, dns_cache=self.cache)

    def test_negative_dns_ttl_obeys_soa_minimum(self):
        doc = copy.deepcopy(self.documents[1])
        doc['Authority'][0]['data'] = 'ns.example.no. hostmaster.example.no. 1 60 60 60 5'
        self.assertEqual(network._dns_ttl(doc), 5)
        doc['Authority'][0]['data'] = 'malformed'
        self.assertEqual(network._dns_ttl(doc), 0)

    @patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "1"})
    @patch.object(network, "_proxy_used", return_value=True)
    @patch.object(network.socket, "getaddrinfo", side_effect=socket.gaierror("unavailable"))
    def test_hits_reuse_validated_answers_only_until_shortest_ttl(self, dns, proxy):
        now = [100.0]
        with patch.object(network.time, "monotonic", side_effect=lambda: now[0]), patch.object(network, "_dns_query", side_effect=self.documents * 2) as query:
            self.validate()
            now[0] = 129
            self.validate("https://example.no/other")
            self.assertEqual(query.call_count, 2)
            now[0] = 130
            self.validate()
            self.assertEqual(query.call_count, 4)
        self.assertEqual(dns.call_count, 2)

    @patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "1"})
    @patch.object(network, "_proxy_used", return_value=True)
    @patch.object(network.socket, "getaddrinfo", side_effect=socket.gaierror("unavailable"))
    def test_missing_ttl_or_missing_family_bounds_prevent_caching(self, dns, proxy):
        for field in ("Answer", "Authority"):
            docs = copy.deepcopy(self.documents)
            docs[0 if field == "Answer" else 1][field][0].pop("TTL")
            with patch.object(network, "_dns_query", side_effect=docs * 2) as query:
                self.validate()
                self.validate()
                self.assertEqual(query.call_count, 4)

    @patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "1"})
    @patch.object(network, "_proxy_used", return_value=True)
    @patch.object(network.socket, "getaddrinfo", side_effect=socket.gaierror("unavailable"))
    def test_hit_does_not_bypass_credentials_proxy_or_expired_private_answers(self, dns, proxy):
        with patch.object(network, "_dns_query", side_effect=self.documents):
            self.validate()
        with self.assertRaises(network.UnsafeURLError):
            self.validate("https://user:secret@example.no/")
        proxy.return_value = False
        with self.assertRaises(network.ResolutionError):
            self.validate()
        proxy.return_value = True
        self.cache._entries["example.no"] = 0
        unsafe = copy.deepcopy(self.documents[0])
        unsafe["Answer"][0]["data"] = "10.0.0.1"
        with patch.object(network, "_dns_query", return_value=unsafe), self.assertRaises(network.UnsafeURLError):
            self.validate()
        self.assertFalse(self.cache.valid("example.no"))


if __name__ == "__main__":
    unittest.main()
