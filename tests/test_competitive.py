from __future__ import annotations

import copy
import csv
import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from norway_company_agent.acquisition import AcquisitionError, ResearchSession, SnapshotStore
from norway_company_agent.batch import profiles_from_bulk
from norway_company_agent.evidence import evidence
from norway_company_agent.pipeline import collect_batch
from norway_company_agent.site_research import assess_site, extract_site_facts, page_links, website_candidates
from norway_company_agent.submission import Envelope, compile_claims, merge_refresh, submission_envelope, validate_submission
from bs4 import BeautifulSoup


def fake_worker(profile, config):
    if profile.get("crash"):
        raise RuntimeError("simulated company failure")
    if profile.get("hang"):
        time.sleep(30)
    return {**profile, "run_metrics": {"requests": 1}}


class SnapshotTests(unittest.TestCase):
    def test_retained_bytes_are_immutable_and_content_addressed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "snapshots")
            original = Path(directory) / "bulk.csv"
            original.write_bytes(b"original source\n")
            digest = hashlib.sha256(original.read_bytes()).hexdigest()
            retained = store.retain_file(original, digest)
            original.write_bytes(b"later replacement\n")
            self.assertEqual(Path(retained["snapshot_path"]).read_bytes(), b"original source\n")
            one = store.save(b"page")
            self.assertEqual(one, store.save(b"page"))

    def test_last_allowed_request_is_usable_and_next_request_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ResearchSession(SnapshotStore(directory), max_requests=1)
            session._reserve("https://example.test")
            self.assertGreater(session.remaining(), 0)
            with self.assertRaises(AcquisitionError):
                session._reserve("https://example.test")

    def test_private_url_cannot_reach_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ResearchSession(SnapshotStore(directory))
            with patch("urllib.request.build_opener") as opener:
                with self.assertRaises(AcquisitionError):
                    session.get("http://127.0.0.1/private")
                opener.assert_not_called()


class DiscoveryTests(unittest.TestCase):
    def profile(self):
        return {"organisation_number": "123456789", "name": "Example Widget AS", "evidence": {
            "registry": {"value": {"epostadresse": "contact@example.no"}},
            "registry_live": {"value": {"business_address": {"adresse": ["Storgata 12"], "postnummer": "0123"}}},
        }}

    def test_registry_business_email_is_only_a_candidate(self):
        self.assertEqual(website_candidates(self.profile()), [{"url": "https://example.no/", "discovery_method": "registry_email_domain"}])
        self.profile()["evidence"]["registry"]["value"]["epostadresse"] = "info@gmail.com"

    def test_consumer_email_does_not_become_company_website(self):
        profile = self.profile()
        profile["evidence"]["registry"]["value"]["epostadresse"] = "info@gmail.com"
        self.assertEqual(website_candidates(profile), [])

    def test_name_match_without_corroboration_abstains(self):
        page = {"url": "https://example.no/", "title": "Example Widget AS", "full_text": "Another municipality"}
        self.assertFalse(assess_site(self.profile(), [page])["publishable"])
        page["full_text"] = "Example Widget AS, Storgata 12, 0123 Oslo"
        self.assertTrue(assess_site(self.profile(), [page])["publishable"])

    def test_brand_can_resolve_through_exact_legal_footer(self):
        page = {"url": "https://brand.no/", "title": "A public brand", "identity_text_excerpt": "Org.nr. 123 456 789 MVA"}
        self.assertTrue(assess_site(self.profile(), [page])["publishable"])

    def test_parent_portfolio_reference_does_not_verify_subsidiary(self):
        page = {"url": "https://parent.no/", "title": "Parent AS", "full_text": "Subsidiary Example Widget AS, org.nr. 123 456 789", "identity_text_excerpt": "Parent AS org.nr. 987 654 321"}
        self.assertFalse(assess_site(self.profile(), [page])["publishable"])

    def test_separate_numbers_cannot_be_joined_into_org_number(self):
        page = {"url": "https://example.no/", "identity_text_excerpt": "Org.nr. 1234 products 56789"}
        self.assertFalse(assess_site(self.profile(), [page])["publishable"])

    def test_careers_and_news_are_discovered_without_external_links(self):
        soup = BeautifulSoup('<a href="/karriere">Jobb hos oss</a><a href="/nyheter">Nyheter</a><a href="https://other.no/jobs">jobs</a>', "html.parser")
        self.assertEqual(page_links("https://example.no/", soup), [("https://example.no/karriere", "careers"), ("https://example.no/nyheter", "news")])

    def test_dated_items_require_employer_identity_and_preserve_source(self):
        page = {"url": "https://example.no/jobs/engineer", "kind": "careers", "title": "Engineer",
                "retrieved_at": "2026-10-02T00:00:00Z", "content_sha256": "a" * 64, "snapshot_path": "/saved/page",
                "identity_text_excerpt": "Org.nr. 123456789", "structured_items": [
                    {"@type": "JobPosting", "title": "Engineer", "datePosted": "2026-09-28", "hiringOrganization": {"name": "Example Widget AS"}},
                    {"@type": "JobPosting", "title": "Other employer", "datePosted": "2026-09-28", "hiringOrganization": {"name": "Unrelated AS"}},
                    {"@type": "NewsArticle", "headline": "New branch", "datePublished": "2026-09-29"},
                    {"@type": "NewsArticle", "headline": "Undated archive"},
                ]}
        facts = extract_site_facts(self.profile(), [page])
        self.assertEqual([item["value"]["title"] for item in facts if item["field"] == "job_posting"], ["Engineer"])
        self.assertEqual([item["value"]["headline"] for item in facts if item["field"] == "company_news"], ["New branch"])
        self.assertTrue(all(item["snapshot_path"] == "/saved/page" for item in facts))


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = SnapshotStore(self.directory.name)

    def profile(self, employees=0):
        raw = {"organisasjonsnummer": "123456789", "navn": "Example Widget AS", "organisasjonsform": {"kode": "AS"},
               "antallAnsatte": employees, "forretningsadresse": {"adresse": ["Storgata 12"]}, "epostadresse": "contact@example.no"}
        source = self.store.save(json.dumps(raw).encode())
        record = evidence("registry_live", "available", "official_registry_live", "https://data.brreg.no/enhetsregisteret/api/enheter/123456789",
                          value={"organisation_number": "123456789", "name": "Example Widget AS", "legal_form": "AS", "employees": employees, "business_address": raw["forretningsadresse"], "email": raw["epostadresse"]},
                          content_sha256=source["content_sha256"], retrieved_at="2026-10-02T00:00:00Z")
        record["snapshot_path"] = source["snapshot_path"]
        return {"organisation_number": "123456789", "evidence": {"registry_live": record}}

    def envelope(self, profile=None):
        return submission_envelope(profile or self.profile(), run_id="test", started_at="2026-10-02T00:00:00Z", completed_at="2026-10-02T00:01:00Z")

    def test_real_zero_missing_values_and_snapshot_provenance(self):
        output = self.envelope()
        fields = {claim["field"]: claim for claim in output["claims"]}
        self.assertEqual(fields["employee_count"]["value"], 0)
        self.assertEqual(fields["employee_count"]["availability"], "available")
        self.assertIsNone(fields["contact_phone"]["value"])
        self.assertEqual(fields["contact_phone"]["availability"], "not_available")
        self.assertTrue(validate_submission([output], ["123456789"])["passed"])
        self.assertFalse(validate_submission([output], ["987654321"])["passed"])
        for source in output["evidence"]:
            self.assertEqual(hashlib.sha256(Path(source["snapshot_path"]).read_bytes()).hexdigest(), source["content_sha256"])

    def test_dangling_evidence_and_unsupported_available_values_are_rejected(self):
        output = self.envelope()
        output["claims"][0]["evidence_ids"] = ["missing"]
        self.assertFalse(validate_submission([output], ["123456789"])["passed"])

    def test_legacy_hash_without_retained_source_cannot_publish(self):
        profile = self.profile()
        del profile["evidence"]["registry_live"]["snapshot_path"]
        claims, _ = compile_claims(profile)
        self.assertFalse(any(item["availability"] == "available" for item in claims))

    def test_identical_refresh_is_noop_and_actual_zero_change_is_reported(self):
        old = self.envelope(self.profile(employees=4))
        same = merge_refresh(copy.deepcopy(old), old)
        self.assertEqual(same["changes"], [])
        changed = merge_refresh(self.envelope(self.profile(employees=0)), old)
        self.assertEqual([(item["field"], item["old_value"], item["new_value"]) for item in changed["changes"]], [("employee_count", 4, 0)])
        source_ids = {item["id"] for item in changed["evidence"]}
        self.assertTrue(set(changed["changes"][0]["old_evidence_ids"]).issubset(source_ids))

    def test_failed_refresh_keeps_last_supported_values_without_false_changes(self):
        old = self.envelope()
        failed = self.envelope({"organisation_number": "123456789", "evidence": {}})
        refreshed = merge_refresh(failed, old)
        employee = next(item for item in refreshed["claims"] if item["field"] == "employee_count")
        self.assertEqual(employee["value"], 0)
        self.assertEqual(employee["freshness"], "last_known")
        self.assertEqual(refreshed["changes"], [])

    def test_corrupt_prior_snapshot_is_rejected_without_losing_new_evidence(self):
        old = self.envelope(self.profile(employees=4))
        Path(old["evidence"][0]["snapshot_path"]).write_bytes(b"corrupted")
        current = self.envelope(self.profile(employees=5))
        refreshed = merge_refresh(current, old)
        self.assertEqual(refreshed["refresh"]["previous_evidence_status"], "rejected")
        employee = next(item for item in refreshed["claims"] if item["field"] == "employee_count")
        self.assertEqual(employee["value"], 5)
        self.assertEqual(refreshed["changes"], [])

    def test_last_known_leadership_summary_is_explicit(self):
        from norway_company_agent.submission import summarize
        summary = summarize([{"id": "role", "field": "roles", "availability": "available", "freshness": "last_known",
                              "value": [{"role_code": "DAGL", "name": "Old Leader"}]}])
        self.assertTrue(summary[0]["text"].startswith("Last known"))

    def test_missing_registry_row_returns_placeholder_for_live_lookup(self):
        path = Path(self.directory.name) / "bulk.csv"
        with path.open("w") as handle:
            writer = csv.DictWriter(handle, fieldnames=["organisasjonsnummer", "navn"])
            writer.writeheader()
            writer.writerow({"organisasjonsnummer": "123456789", "navn": "Example"})
        profiles, report = profiles_from_bulk(path, ["123456789", "987654321"])
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[1]["evidence"]["registry"]["status"], "not_found")
        self.assertEqual(report["absent_from_snapshot"], ["987654321"])


class BatchIsolationTests(unittest.TestCase):
    def test_company_failure_cannot_drop_results_from_1200_company_batch(self):
        profiles = [{"organisation_number": str(100000000 + i)} for i in range(1200)]
        profiles[17]["crash"] = True
        results, report = collect_batch(profiles, {"modules": ["registry_live"], "deadline": time.monotonic() + 15}, workers=8, worker=fake_worker)
        self.assertEqual(set(results), {item["organisation_number"] for item in profiles})
        self.assertIn("simulated company failure", results[profiles[17]["organisation_number"]]["errors"][0]["message"])
        self.assertEqual(report["unfinished"], 0)
        self.assertEqual(report["worker_exit_code"], 0)

    def test_hung_worker_is_terminated_and_missing_result_is_finalized(self):
        started = time.monotonic()
        profiles = [{"organisation_number": "123456789", "hang": True}]
        results, report = collect_batch(profiles, {"modules": ["registry_live"], "deadline": started + 2}, worker=fake_worker)
        self.assertLess(time.monotonic() - started, 6)
        self.assertTrue(report["deadline_exhausted"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results["123456789"]["evidence"]["registry_live"]["status"], "source_error")


if __name__ == "__main__":
    unittest.main()
