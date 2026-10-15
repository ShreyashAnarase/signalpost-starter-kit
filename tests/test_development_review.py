from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_development_review as review
from norway_company_agent.acquisition import AcquisitionError, Capture, ResearchSession, SnapshotStore
from norway_company_agent.evidence import evidence


def failed_worker(profile, config):
    raise RuntimeError("offline simulated source failure")


def hung_worker(profile, config):
    time.sleep(10)
    return profile


class DevelopmentReviewTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "out/live-development-review").mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="test-", dir=ROOT / "out/live-development-review"))
        self.addCleanup(shutil.rmtree, self.directory)

    def test_selection_rejects_duplicate_unknown_and_over_limit_without_network(self):
        self.assertEqual([p["organisation_number"] for p in review.select_development(review.DEFAULT_ORGS)], review.DEFAULT_ORGS)
        for orgs in [[], ["985215294"] * 2, ["000000000"], review.DEFAULT_ORGS * 3]:
            with self.subTest(orgs=orgs), self.assertRaises(ValueError):
                review.select_development(orgs)

    def test_source_failure_emits_one_envelope_per_input_and_passes_audit(self):
        report = review.run_review(review.DEFAULT_ORGS, self.directory / "failure", worker=failed_worker)
        envelopes = review.read_jsonl(self.directory / "failure/envelopes.jsonl")
        self.assertEqual([e["organisation_number"] for e in envelopes], review.DEFAULT_ORGS)
        self.assertTrue(report["audit"]["passed"], report["audit"])
        self.assertFalse(report["telemetry_complete"])
        self.assertTrue(all(p["errors"] for p in review.read_jsonl(self.directory / "failure/profiles.jsonl")))
        with self.assertRaises(FileExistsError):
            review.run_review(review.DEFAULT_ORGS, self.directory / "failure", worker=failed_worker)

    def test_hung_worker_terminated_and_remaining_input_finalized(self):
        started = time.monotonic()
        report = review.run_review(review.DEFAULT_ORGS, self.directory / "hung", worker=hung_worker,
                                   overall_timeout=3, company_timeout=3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(len(review.read_jsonl(self.directory / "hung/envelopes.jsonl")), 2)
        self.assertTrue(report["audit"]["passed"])
        self.assertTrue(report["supervision"][0]["deadline_exhausted"])
        self.assertFalse(report["telemetry_complete"])

    def test_no_escape_from_assigned_output_or_larger_budget(self):
        for kwargs in [{"overall_timeout": 181}, {"company_timeout": 41}]:
            with self.assertRaises(ValueError):
                review.run_review(review.DEFAULT_ORGS, self.directory / "invalid", **kwargs)
        with self.assertRaises(ValueError):
            review.run_review(review.DEFAULT_ORGS, ROOT / "out/other")

    def test_pre_dns_failure_and_source_bytes_retained(self):
        path = self.directory / "telemetry.json"
        session = review.LoggedSession(SnapshotStore(self.directory / "snapshots"), telemetry_path=path)
        with patch.object(ResearchSession, "get", side_effect=ValueError("Cannot resolve public hostname")):
            with self.assertRaises(ValueError):
                session.get("https://example.test/")
        recorded = json.loads(path.read_text())
        self.assertEqual(recorded["operations"][0]["state"], "error")
        self.assertIn("resolve", recorded["operations"][0]["error"])
        self.assertEqual(recorded["metrics"]["requests"], 0)
        raw = b"retained source"
        capture = Capture("https://example.test/", "https://example.test/", 200, "text/plain", raw,
                          "2026-10-12T00:00:00Z", **session.store.save(raw))
        session.captures[capture.final_url] = capture
        session.flush()
        retained = json.loads(path.read_text())["captures"][0]
        self.assertEqual(Path(retained["snapshot_path"]).read_bytes(), raw)

    def test_public_identity_mismatch_prevents_site_research(self):
        config = {"deadline": time.monotonic() + 30, "snapshot_dir": str(self.directory / "snapshots"),
                  "telemetry_dir": str(self.directory)}
        record = evidence("registry_live", "available", "official_registry_live", "https://example.test/",
                          value={"organisation_number": "000000000"})
        with patch.object(review, "fetch_official_modules", return_value=({"registry_live": record}, [])), patch.object(review, "research_site") as site:
            profile = review.review_company(review.select_development([review.DEFAULT_ORGS[0]])[0], config)
        site.assert_not_called()
        self.assertEqual(profile["evidence"]["registry_live"]["status"], "ambiguous")

    def test_unavailable_public_identity_cannot_publish_site(self):
        config = {"deadline": time.monotonic() + 30, "snapshot_dir": str(self.directory / "snapshots"),
                  "telemetry_dir": str(self.directory)}
        record = evidence("registry_live", "source_error", "official_registry_live", "https://example.test/", note="DNS")
        with patch.object(review, "fetch_official_modules", return_value=({"registry_live": record}, [])), patch.object(review, "research_site", return_value={"status": "available", "value": {"facts": []}}) as site:
            profile = review.review_company(review.select_development([review.DEFAULT_ORGS[0]])[0], config)
        self.assertEqual(profile["evidence"]["website"]["status"], "ambiguous")
        self.assertIsNone(profile["evidence"]["website"]["value"])
        self.assertEqual(site.call_args.kwargs, {"max_pages": 4, "wikidata_discovery": False})

    def test_successful_offline_acquisition_is_repeatable_and_audited(self):
        profile = review.select_development([review.DEFAULT_ORGS[0]])[0]
        org = profile["organisation_number"]
        registry = {"organisasjonsnummer": org, "navn": profile["name"], "hjemmeside": "https://fixture.test/"}
        html = f'<html><main><h1>{profile["name"]}</h1></main><footer>Org.nr. {org}</footer></html>'

        def fixture_get(session, url, **kwargs):
            raw = json.dumps(registry).encode() if "data.brreg.no" in url else html.encode()
            capture = Capture(url, url, 200, "application/json" if "data.brreg.no" in url else "text/html; charset=utf-8",
                              raw, "2026-10-12T00:00:00Z", **session.store.save(raw))
            session.captures[url] = capture
            session.requests += 1
            session.bytes_received += len(raw)
            return capture

        envelopes = []
        config = {"deadline": time.monotonic() + 30, "snapshot_dir": str(self.directory / "snapshots"),
                  "telemetry_dir": str(self.directory)}
        with patch.object(ResearchSession, "get", fixture_get):
            for _ in range(2):
                acquired = review.review_company(profile, config)
                self.assertEqual(acquired["evidence"]["website"]["status"], "available")
                envelope = review.submission_envelope(acquired, run_id="offline", started_at="2026-10-12T00:00:00Z", completed_at="2026-10-12T00:00:00Z")
                self.assertTrue(review.audit_envelopes([envelope], [org])["passed"])
                envelopes.append(envelope)
        # Resource observations vary; claims/locators from identical bytes must not.
        for envelope in envelopes:
            envelope["operations"].pop("runtime_ms")
        self.assertEqual(envelopes[0], envelopes[1])
        retained = json.loads((self.directory / (org + ".json")).read_text())
        self.assertGreaterEqual(len(retained["captures"]), 2)
        self.assertTrue(any("data.brreg.no" in c["source_url"] for c in retained["captures"]))
        self.assertTrue(any(c["source_url"] == "https://fixture.test/" for c in retained["captures"]))
        self.assertTrue(all(Path(c["snapshot_path"]).is_file() for c in retained["captures"]))

    def test_session_request_and_timeout_budgets(self):
        session = review.LoggedSession(SnapshotStore(self.directory / "snapshots"), timeout=8,
            deadline=time.monotonic() + 30, max_requests=20, telemetry_path=self.directory / "limits.json")
        for index in range(20):
            session._reserve(f"https://budget-{index}.test/")
        with self.assertRaises(AcquisitionError):
            session._reserve("https://budget-overflow.test/")
        self.assertEqual(session.requests, 20)
        self.assertLessEqual(session.remaining(), 8)
        session.deadline = time.monotonic() - 1
        with self.assertRaises(AcquisitionError):
            session.remaining()


if __name__ == "__main__":
    unittest.main()
