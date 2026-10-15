from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from norway_company_agent import site_research
from norway_company_agent.acquisition import AcquisitionError, Capture, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.packaging import package_submission
from norway_company_agent.submission import merge_refresh, submission_envelope

FIXTURE = ROOT / "tests/fixtures/dated-events-sites.json"


class FixtureSession:
    def __init__(self, pages, store, retrieved_at):
        self.pages, self.store, self.retrieved_at = pages, store, retrieved_at
        self.requests = []

    def get(self, url, **kwargs):
        self.requests.append(url)
        path = urlsplit(url).path
        body = self.pages.get(path)
        if body is None:
            raise AcquisitionError("HTTP 404", "not_available")
        raw = body.encode()
        return Capture(url, url, 200, "text/html; charset=utf-8", raw,
                       self.retrieved_at, **self.store.save(raw))


def fixture_run(module, root):
    fixture = json.loads(FIXTURE.read_text())
    envelopes, requests = [], 0
    for company in fixture["companies"]:
        profile = {key: value for key, value in company.items() if key != "pages"}
        profile["evidence"] = {}
        session = FixtureSession(company["pages"], SnapshotStore(root), fixture["retrieved_at"])
        profile["evidence"]["website"] = module.research_site(profile, session)
        profile["run_metrics"] = {"requests": len(session.requests), "runtime_ms": 0, "third_party_cost_usd": 0}
        envelopes.append(submission_envelope(profile, run_id="fixture", started_at=fixture["retrieved_at"], completed_at=fixture["retrieved_at"]))
        requests += len(session.requests)
    return envelopes, requests


class DatedEventTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.store = SnapshotStore(self.root / "snapshots")

    def record(self, html, kind="news", captured="2026-10-12T00:00:00Z"):
        profile = {"organisation_number": "123456789", "name": "EXAMPLE AS", "website": "https://example.test/", "evidence": {}}
        # Test page has independent legal ownership proof; it still passes the gate.
        html += '<footer>Org.nr. 123456789</footer>'
        session = FixtureSession({"/": html}, self.store, captured)
        page, _ = site_research.read_page(session, profile["website"], kind)
        facts = site_research.extract_site_facts(profile, [page])
        profile["evidence"]["website"] = {"status": "available", "value": {"facts": facts}}
        envelope = submission_envelope(profile, run_id="test", started_at=captured, completed_at=captured)
        return facts, envelope

    def events(self, facts):
        return [f for f in facts if f["field"] in {"job_posting", "company_news"}]

    def test_opaque_article_links_improve_fixture_and_portable_audit(self):
        envelopes, requests = fixture_run(site_research, self.root / "fixture")
        actual = [(e["organisation_number"], c["field"]) for e in envelopes for c in e["claims"] if c["availability"] == "available" and c["field"] in {"company_news", "job_posting"}]
        self.assertEqual(actual, [("123456789", "company_news"), ("123456789", "company_news"), ("987654321", "job_posting")])
        self.assertLessEqual(requests, 9)
        orgs = [e["organisation_number"] for e in envelopes]
        audit = audit_envelopes(envelopes, orgs)
        self.assertTrue(audit["passed"], audit)
        manifest = package_submission(envelopes, orgs, self.root / "package")
        self.assertTrue(manifest["audit"]["passed"])
        shutil.rmtree(self.root / "fixture")
        shutil.move(self.root / "package", self.root / "relocated")
        portable = [json.loads(line) for line in (self.root / "relocated/envelopes.jsonl").read_text().splitlines()]
        self.assertTrue(audit_envelopes(portable, orgs, snapshot_root=self.root / "relocated")["passed"])

    def test_indexes_footer_dates_undated_and_future_articles_abstain(self):
        for html in [
            '<main><h1>News</h1><article><h2>One</h2><time datetime="2026-10-01"/></article><article><h2>Two</h2><time datetime="2026-10-02"/></article></main>',
            '<main><h1>Article</h1></main><footer><time datetime="2026-10-01"/></footer>',
            '<article><h1>Article</h1><time datetime="2026-13-01"/></article>',
            '<article><h1>Scheduled</h1><time datetime="2026-11-01"/></article>',
        ]:
            with self.subTest(html=html):
                self.assertEqual(self.events(self.record(html)[0]), [])

    def test_jsonld_nested_pointer_audits_all_event_fields(self):
        item = {"@type": "NewsArticle", "headline": "New branch", "datePublished": "2026-10-01", "url": "https://example.test/"}
        html = '<h1>New branch</h1><script type="application/ld+json">' + json.dumps({"@graph": [item]}) + '</script>'
        facts, envelope = self.record(html)
        event = self.events(facts)[0]
        self.assertEqual(event["source_locator"]["pointer"], "/@graph/0")
        self.assertTrue(audit_envelopes([envelope], ["123456789"])["passed"])
        changed = copy.deepcopy(envelope)
        source = next(s for s in changed["evidence"] if s["source_locator"]["type"] == "jsonld_pointer")
        span = json.loads(source["claim_span"])
        span["datePublished"] = "2026-09-01"
        source["claim_span"] = json.dumps(span)
        self.assertFalse(audit_envelopes([changed], ["123456789"])["passed"])

    def test_dom_date_and_employer_cannot_pass_with_altered_locator_values(self):
        html = '<main><h1>Engineer</h1><time itemprop="datePosted" datetime="2026-10-01"/><div itemprop="hiringOrganization"><span itemprop="legalName">EXAMPLE AS</span></div></main>'
        facts, envelope = self.record(html, "careers")
        self.assertEqual(len(self.events(facts)), 1)
        self.assertTrue(audit_envelopes([envelope], ["123456789"])["passed"])
        source = next(s for s in envelope["evidence"] if s["source_locator"]["type"] == "dom_fields")
        source["source_locator"]["fields"]["date"]["value"] = "2026-09-01"
        self.assertFalse(audit_envelopes([envelope], ["123456789"])["passed"])

    def test_snapshot_expiry_is_deterministic_and_failed_refresh_preserves_job(self):
        item = {"@type": "JobPosting", "title": "Engineer", "datePosted": "2025-01-01", "validThrough": "2025-02-01", "hiringOrganization": {"legalName": "EXAMPLE AS"}}
        html = '<script type="application/ld+json">' + json.dumps(item) + '</script>'
        facts, previous = self.record(html, "careers", "2025-01-10T00:00:00Z")
        self.assertEqual(len(self.events(facts)), 1)
        self.assertEqual(facts, self.record(html, "careers", "2025-01-10T00:00:00Z")[0])
        self.assertEqual(self.events(self.record(html, "careers", "2025-03-01T00:00:00Z")[0]), [])
        current = submission_envelope({"organisation_number": "123456789", "evidence": {"website": {"status": "source_error", "note": "Timeout"}}},
                                      run_id="failed-refresh", started_at="2026-10-12T00:00:00Z", completed_at="2026-10-12T00:00:00Z")
        merged = merge_refresh(current, previous)
        old = next(c for c in merged["claims"] if c["field"] == "job_posting" and c["availability"] == "available")
        self.assertEqual(old["freshness"], "last_known")
        self.assertTrue(audit_envelopes([merged], ["123456789"])["passed"])

    def test_offsite_canonical_employer_conflict_and_article_card_abstain(self):
        for html, kind in [
            ('<link rel="canonical" href="https://other.test/article"><article><h1>Article</h1><time datetime="2026-10-01"/></article>', "news"),
            ('<main><h1>Engineer</h1><time itemprop="datePosted" datetime="2026-10-01"/><div itemprop="hiringOrganization"><span itemprop="legalName">OTHER AS</span></div></main>', "careers"),
            ('<script type="application/ld+json">{"@type":"NewsArticle","headline":"Card","datePublished":"2026-10-01","url":"https://example.test/detail"}</script>', "news"),
            ('<h1>News index</h1><script type="application/ld+json">{"@type":"NewsArticle","headline":"Card","datePublished":"2026-10-01"}</script>', "news"),
            ('<main><h1>Engineer</h1><time itemprop="datePosted" datetime="2026-10-01"/><div itemprop="hiringOrganization"><span itemprop="legalName">EXAMPLE GROUP AS</span></div></main>', "careers"),
        ]:
            self.assertEqual(self.events(self.record(html, kind)[0]), [])

    def test_context_links_remain_same_host_content_only_and_respect_page_budget(self):
        soup = BeautifulSoup('<main><article><h2><a href="/item/1">Opening</a></h2><a href="https://other.test/item/2">Other company</a></article></main><nav><h2><a href="/item/3">Menu</a></h2></nav><footer><a href="/item/4">Footer</a></footer>', "lxml")
        self.assertEqual(site_research.page_links("https://example.test/news", soup, family="news"), [("https://example.test/item/1", "news")])
        fixture = json.loads(FIXTURE.read_text())
        company = fixture["companies"][0]
        profile = {k: v for k, v in company.items() if k != "pages"}
        session = FixtureSession(company["pages"], self.store, fixture["retrieved_at"])
        record = site_research.research_site(profile, session, max_pages=2)
        self.assertEqual(len(session.requests), 2)
        self.assertEqual(self.events(record["value"]["facts"]), [])

    def test_malformed_structured_types_do_not_break_valid_dom_article(self):
        html = '<script type="application/ld+json">{"@type":[{"bad":"type"}]}</script><article><h1>Opening</h1><time datetime="2026-10-01"/></article>'
        self.assertEqual(len(self.events(self.record(html)[0])), 1)

    def test_appointment_booking_does_not_become_careers_page_on_retained_replay(self):
        self.assertIsNone(site_research.page_kind("https://example.test/timebestilling/", "Bestill time"))
        for url in ["https://example.test/jobs/", "https://example.test/stillinger/", "https://example.test/jobb/"]:
            self.assertEqual(site_research.page_kind(url), "careers")
        profile = {"organisation_number": "123456789", "name": "EXAMPLE AS", "website": "https://example.test/", "evidence": {}}
        html = '<title>Bestill time</title><main><h1>Bestill time</h1></main><footer>Org.nr. 123456789</footer>'
        session = FixtureSession({"/timebestilling/": html}, self.store, "2026-10-13T00:00:00Z")
        # Old retained acquisitions may still carry the incorrect family.
        page, _ = site_research.read_page(session, "https://example.test/timebestilling/", "careers")
        facts = site_research.extract_site_facts(profile, [page])
        self.assertFalse(any(f["field"] in {"careers_page", "job_posting"} for f in facts))

    def test_single_word_shared_brand_phone_requires_legal_name_or_org_proof(self):
        profile = {"organisation_number": "123456789", "name": "FASIA AS", "evidence": {"registry_live": {"value": {"phone": "99155500"}}}}
        page = {"url": "https://example.test/", "title": "FASIA clinics", "full_text": "Our clinics: Bergen - practitioner 99155500; another independent clinic", "headings": [], "identity_text_excerpt": ""}
        self.assertFalse(site_research.assess_site(profile, [page])["publishable"])
        page["title"] = "FASIA AS"
        self.assertTrue(site_research.assess_site(profile, [page])["publishable"])
        page["title"] = "FASIA clinics"
        page["identity_text_excerpt"] = "Org.nr. 123456789"
        self.assertTrue(site_research.assess_site(profile, [page])["publishable"])

    def test_contact_identity_cites_name_and_phone_instead_of_generic_footer(self):
        profile = {"organisation_number": "123456789", "name": "EXAMPLE WIDGET AS", "website": "https://example.test/", "evidence": {"registry_live": {"value": {"phone": "12345678"}}}}
        html = '<title>Example Widget</title><main><h1>Example Widget</h1><a href="tel:12345678">12 34 56 78</a></main><footer>Made by Web Designer</footer>'
        session = FixtureSession({"/": html}, self.store, "2026-10-13T00:00:00Z")
        record = site_research.research_site(profile, session)
        self.assertEqual(record["status"], "available")
        website = next(f for f in record["value"]["facts"] if f["field"] == "official_website")
        self.assertEqual(website["source_locator"]["type"], "dom_fields")
        self.assertEqual(json.loads(website["claim_span"])["registered_contact"], "12 34 56 78")
        profile["evidence"] = {"website": record}
        envelope = submission_envelope(profile, run_id="identity", started_at="2026-10-13T00:00:00Z", completed_at="2026-10-13T00:00:00Z")
        self.assertTrue(audit_envelopes([envelope], ["123456789"])["passed"])


if __name__ == "__main__":
    unittest.main()
