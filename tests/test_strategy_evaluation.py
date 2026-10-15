import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("strategy_evaluation", ROOT / "scripts/evaluate_strategy.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StrategyEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((ROOT / "tests/fixtures/strategy-evaluation.json").read_text())

    def result(self, run="challenger", mode="independent_human"):
        result = module.evaluate(self.fixture[run], self.fixture["labels"], run, ["1", "2"], mode)
        result["complete_host_separation"] = True  # Fully separated synthetic fixture only.
        return result

    def test_weighted_recall_company_breadth_and_duplicate_claims(self):
        result = self.result()
        field = result["per_field"]["job_posting"]
        self.assertEqual(field["company_recall"], 1)
        self.assertEqual(field["individual_claim_recall"], 2 / 3)
        self.assertAlmostEqual(field["weighted_known_pool_coverage"], .9)
        self.assertTrue(result["review_complete"])
        self.assertTrue(module.compare(self.result("baseline"), result, self.fixture["policy"])["promotion_passed"])

    def test_assistant_reviews_are_not_independent(self):
        for row in self.fixture["labels"]["judgments"]:
            row["review"]["kind"] = "assistant"
        result = self.result()
        self.assertIsNone(result["claim_precision"])
        self.assertFalse(result["review_complete"])
        diagnostic = self.result(mode="assistant_diagnostic")
        self.assertEqual(diagnostic["claim_precision"], 1)
        self.assertFalse(module.compare(self.result("baseline", "assistant_diagnostic"), diagnostic, self.fixture["policy"])["promotion_passed"])

    def test_empty_unknown_denominators_are_null(self):
        self.fixture["labels"]["opportunities"] = []
        for row in self.fixture["labels"]["judgments"]:
            row.pop("opportunity_id", None)
        result = self.result()
        self.assertIsNone(result["per_field"]["job_posting"]["company_recall"])
        self.assertFalse(module.compare(self.result("baseline"), result, self.fixture["policy"])["promotion_passed"])

    def test_wrong_identity_and_evidence_block_promotion(self):
        judgment = next(j for j in self.fixture["labels"]["judgments"] if j["run"] == "challenger")
        judgment["exact_entity"] = False
        judgment["evidence_valid"] = False
        result = self.result()
        self.assertEqual(result["material_wrong_company_publications"], 1)
        comparison = module.compare(self.result("baseline"), result, self.fixture["policy"])
        self.assertFalse(comparison["checks"]["no_material_wrong_company"])
        self.assertFalse(comparison["checks"]["material_evidence_complete"])

    def test_missing_telemetry_and_refresh_block_promotion(self):
        self.fixture["challenger"][0]["operations"].pop("requests")
        self.fixture["labels"]["refresh_judgments"] = []
        result = self.result()
        self.assertIsNone(result["operations"]["requests"])
        comparison = module.compare(self.result("baseline"), result, self.fixture["policy"])
        self.assertFalse(comparison["checks"]["resource_requests"])
        self.assertFalse(comparison["checks"]["refresh_verified"])

    def test_membership_and_bad_opportunity_mapping(self):
        self.fixture["challenger"].pop()
        self.fixture["labels"]["judgments"] = [j for j in self.fixture["labels"]["judgments"] if not (j["run"] == "challenger" and j["organisation_number"] == "2")]
        self.assertFalse(self.result()["terminal_completeness"])
        self.fixture["labels"]["judgments"][1]["opportunity_id"] = "org2-job"
        with self.assertRaises(ValueError):
            self.result()

    def test_domain_overlap_offline_and_unknown_hosts(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("No DNS")):
            report = module.audit_split([{"organisation_number": "1", "website": "jobs.example.co.uk"}],
                                        [{"organisation_number": "2", "website": "www.example.co.uk"}, {"organisation_number": "3"}])
        self.assertEqual(report["known_domain_overlap"], ["example.co.uk"])
        self.assertEqual(report["unknown_host_organisations"]["holdout"], ["3"])
        self.assertFalse(report["known_separation_passed"])

    def test_unknown_hosts_and_pool_mismatch_block_promotion(self):
        baseline, challenger = self.result("baseline"), self.result()
        challenger["complete_host_separation"] = False
        challenger["opportunity_pool_fingerprint"] = "different"
        comparison = module.compare(baseline, challenger, self.fixture["policy"])
        self.assertFalse(comparison["checks"]["complete_host_separation"])
        self.assertFalse(comparison["checks"]["same_opportunity_pool"])

    def test_partial_runtime_and_invalid_policy(self):
        self.fixture["challenger"][0]["operations"].pop("runtime_ms")
        result = self.result()
        self.assertIsNone(result["operations"]["company_runtime_ms"]["p50_ms"])
        self.fixture["policy"]["resource_caps"]["requests"] = float("nan")
        with self.assertRaises(ValueError):
            module.compare(self.result("baseline"), result, self.fixture["policy"])

    def test_ambiguous_unknown_judgment_rejected(self):
        self.fixture["labels"]["judgments"][1]["correct"] = None
        with self.assertRaises(ValueError):
            self.result()

    def test_incomplete_opportunity_review_blocks_promotion(self):
        self.fixture["labels"]["opportunities"][1]["review"] = None
        result = self.result()
        self.assertFalse(result["opportunity_review_complete"])
        self.assertFalse(module.compare(self.result("baseline"), result, self.fixture["policy"])["checks"]["opportunity_review_complete"])

    def test_search_scope_missing_incomplete_and_duplicate(self):
        self.fixture["labels"]["scope"][0]["complete_within_scope"] = False
        self.assertFalse(module.compare(self.result("baseline"), self.result(), self.fixture["policy"])["checks"]["target_scope_complete"])
        self.fixture["labels"]["scope"] = []
        self.assertFalse(module.compare(self.result("baseline"), self.result(), self.fixture["policy"])["promotion_passed"])
        row = {"organisation_number": "1", "field": "job_posting", "search_scope": "synthetic", "complete_within_scope": True,
               "review": self.fixture["labels"]["judgments"][0]["review"]}
        self.fixture["labels"]["scope"] = [row, dict(row)]
        with self.assertRaisesRegex(ValueError, "Duplicate.*scope"):
            self.result()

    def test_unreviewed_and_duplicate_refresh_cases(self):
        row = dict(self.fixture["labels"]["refresh_judgments"][0], case_id="unreviewed", review=None)
        self.fixture["labels"]["refresh_judgments"].append(row)
        result = self.result()
        self.assertEqual(result["refresh"]["correctness"], 1)
        self.assertFalse(module.compare(self.result("baseline"), result, self.fixture["policy"])["checks"]["refresh_verified"])
        self.fixture["labels"]["refresh_judgments"] = [self.fixture["labels"]["refresh_judgments"][0]] * 2
        with self.assertRaisesRegex(ValueError, "unique case IDs"):
            self.result()

    def test_partial_publication_review_cannot_promote(self):
        self.fixture["labels"]["judgments"][2]["review"] = None
        result = self.result()
        self.assertEqual(result["claim_precision"], 1)
        self.assertFalse(module.compare(self.result("baseline"), result, self.fixture["policy"])["checks"]["review_complete"])

    def test_duplicate_and_malformed_population_and_policy(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            module.evaluate(self.fixture["challenger"], self.fixture["labels"], "challenger", ["1", "1", "2"])
        with self.assertRaisesRegex(ValueError, "nonempty string"):
            module.audit_split([{"organisation_number": None}], [])
        self.fixture["policy"]["target_fields"] = "job_posting"
        with self.assertRaisesRegex(ValueError, "target_fields"):
            module.compare(self.result("baseline"), self.result(), self.fixture["policy"])

    def test_opportunity_placeholder_evidence_rejected(self):
        self.fixture["labels"]["opportunities"][0]["evidence"] = {"note": "synthetic unsupported placeholder"}
        with self.assertRaisesRegex(ValueError, "exact span/locator"):
            self.result()

    def test_invalid_review_provenance_is_unknown(self):
        self.fixture["labels"]["judgments"][2]["review"]["reviewed_at"] = "invented date"
        self.assertFalse(self.result()["review_complete"])
        self.fixture["labels"]["judgments"][2]["review"]["reviewed_at"] = "2026-10-12T00:00:00"
        self.assertFalse(self.result()["review_complete"])

    def test_duplicate_membership_never_proves_host_separation(self):
        row = {"organisation_number": "1", "website": "https://example.com"}
        report = module.audit_split([row, dict(row)], [{"organisation_number": "2", "website": "https://example.org"}])
        self.assertFalse(report["complete_host_separation"])

    def test_missing_envelope_availability_is_unknown(self):
        self.fixture["challenger"][0].pop("availability")
        result = self.result()
        self.assertFalse(result["envelope_availability_complete"])
        self.assertIsNone(result["successful_company_fraction"])


if __name__ == "__main__":
    unittest.main()
