"""Explicitly synthetic local review fixtures; no real company or human labels."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("human_review", ROOT / "scripts/prepare_human_review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
import evaluate_strategy


class HumanReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = b'{"name":"Synthetic company only"}'
        (self.root / "synthetic.json").write_bytes(self.raw)
        self.development = [{"organisation_number": "000000001", "name": "Synthetic company", "evaluation_split": "development"},
                            {"organisation_number": "000000002", "name": "Synthetic unresolved company", "evaluation_split": "development"}]
        self.holdout = [{"organisation_number": "000000003", "evaluation_split": "holdout"}]
        self.envelopes = [{"organisation_number": "000000001", "legal_identity": {"name": "Synthetic company"},
                           "claims": [{"id": "synthetic-claim", "field": "official_website", "value": "https://example.invalid",
                                       "availability": "available", "evidence_ids": ["synthetic-evidence"]}],
                           "evidence": [{"id": "synthetic-evidence", "source_url": "https://example.invalid/synthetic",
                                         "retrieved_at": "2026-10-12T00:00:00Z", "reporting_period": "2026",
                                         "content_sha256": hashlib.sha256(self.raw).hexdigest(), "snapshot_path": "synthetic.json",
                                         "claim_span": '"Synthetic company only"', "source_locator": {"type": "json_pointer", "pointer": "/name"},
                                         "extraction_method": "synthetic_fixture"}]},
                          {"organisation_number": "000000002", "claims": [{"id": "synthetic-unknown", "field": "official_website",
                           "value": None, "availability": "not_available", "evidence_ids": []}], "evidence": []}]

    def prepare(self):
        return module.prepare(self.envelopes, self.development, self.holdout, self.root, "synthetic", ["official_website"])

    def test_offline_reproducible_blank_template_and_exact_evidence(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("No DNS")), patch("urllib.request.urlopen", side_effect=AssertionError("No HTTP")):
            packet, labels, snapshots = self.prepare()
            self.assertEqual((packet, labels, snapshots), self.prepare())
        self.assertEqual(len(packet["claims"]), 2)
        self.assertEqual(len(labels["judgments"]), 1)
        row = labels["judgments"][0]
        for key in ["exact_entity", "correct", "material", "evidence_valid"]:
            self.assertIsNone(row[key])
        self.assertEqual(row["review"], {"kind": None, "reviewer": None, "reviewed_at": None})
        self.assertEqual(len(labels["scope"]), 2)
        self.assertEqual(labels["opportunities"], [])
        source = packet["claims"][0]["evidence"][0]
        self.assertEqual(source["source_locator"], {"type": "json_pointer", "pointer": "/name"})
        self.assertEqual(source["claim_span"], '"Synthetic company only"')
        self.assertEqual(source["retrieved_at"], "2026-10-12T00:00:00Z")
        self.assertEqual(snapshots[source["snapshot_path"]], self.raw)
        self.assertTrue(packet["retained_bytes_complete"])
        output = self.root / "packet"
        module.write_packet(output, packet, labels, snapshots)
        self.assertEqual(json.loads((output / "labels-template.json").read_text()), labels)
        self.assertEqual((output / source["snapshot_path"]).read_bytes(), self.raw)
        with self.assertRaises(FileExistsError):
            module.write_packet(output, packet, labels, snapshots)

    def test_missing_and_corrupt_snapshots_remain_unknown(self):
        (self.root / "synthetic.json").unlink()
        packet, labels, snapshots = self.prepare()
        self.assertFalse(packet["retained_bytes_complete"])
        self.assertEqual(packet["evidence_issues"][0]["bytes_status"], "missing")
        self.assertEqual(snapshots, {})
        self.assertIsNone(labels["judgments"][0]["evidence_valid"])
        (self.root / "synthetic.json").write_bytes(b"synthetic corrupted bytes")
        packet, _, snapshots = self.prepare()
        self.assertEqual(packet["evidence_issues"][0]["bytes_status"], "hash_mismatch")
        self.assertEqual(snapshots, {})

    def test_path_traversal_absolute_and_symlink_escape_refused(self):
        source = self.envelopes[0]["evidence"][0]
        for value in ["../outside.json", "/etc/passwd"]:
            source["snapshot_path"] = value
            with self.assertRaisesRegex(ValueError, "escapes"):
                self.prepare()
        (self.root / "escape").symlink_to("/etc/passwd")
        source["snapshot_path"] = "escape"
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.prepare()
        source["snapshot_path"] = str(self.root / "synthetic.json")
        self.assertTrue(self.prepare()[0]["retained_bytes_complete"])

    def test_holdout_refused_before_evidence_read(self):
        self.envelopes[0]["organisation_number"] = "000000003"
        with patch.object(Path, "read_bytes", side_effect=AssertionError("Must not open evidence")):
            with self.assertRaisesRegex(ValueError, "Holdout"):
                self.prepare()

    def test_malformed_membership_and_missing_duplicate_envelopes(self):
        original = copy.deepcopy(self.development)
        for org in [None, 123, "", " 000000001"]:
            self.development[0]["organisation_number"] = org
            with self.assertRaises(ValueError):
                self.prepare()
        self.development = original
        self.development[0]["known_websites"] = "https://example.invalid"
        with self.assertRaises(ValueError):
            self.prepare()
        self.development = original = copy.deepcopy(original)
        self.development[0].pop("known_websites")
        self.envelopes.pop()
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.prepare()
        self.envelopes.append(copy.deepcopy(self.envelopes[0]))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.prepare()

    def test_holdout_marked_development_and_overlap_refused(self):
        self.development[0]["evaluation_split"] = "holdout"
        with self.assertRaisesRegex(ValueError, "non-development"):
            self.prepare()
        self.development[0]["evaluation_split"] = "development"
        self.holdout[0]["organisation_number"] = "000000001"
        with self.assertRaisesRegex(ValueError, "overlaps"):
            self.prepare()

    def test_dangling_metadata_and_unavailable_assertions_refused(self):
        self.envelopes[0]["claims"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "Dangling"):
            self.prepare()
        self.envelopes[0]["claims"][0]["evidence_ids"] = ["synthetic-evidence"]
        self.envelopes[1]["claims"][0]["value"] = 0
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.prepare()
        self.envelopes[1]["claims"][0]["value"] = None
        self.envelopes[0]["evidence"][0].pop("source_locator")
        with self.assertRaisesRegex(ValueError, "locator"):
            self.prepare()

    def test_blank_and_assistant_only_import_cannot_promote(self):
        _, labels, _ = self.prepare()
        result = evaluate_strategy.evaluate(self.envelopes, labels, "synthetic", [r["organisation_number"] for r in self.development])
        self.assertFalse(result["review_complete"])
        self.assertIsNone(result["claim_precision"])
        row = labels["judgments"][0]
        row.update(exact_entity=True, correct=True, evidence_valid=True, material=True)
        row["review"] = {"kind": "assistant", "reviewer": "synthetic-assistant", "reviewed_at": "2026-10-12T00:00:00Z"}
        result = evaluate_strategy.evaluate(self.envelopes, labels, "synthetic", [r["organisation_number"] for r in self.development])
        self.assertFalse(result["review_complete"])
        result["complete_host_separation"] = True
        policy = {"target_fields": ["official_website"], "minimum_coverage_gain": .1, "maximum_precision_loss": 0,
                  "resource_caps": {"requests": 10}}
        self.assertFalse(evaluate_strategy.compare(result, result, policy)["promotion_passed"])

    def test_cli_synthetic_packet(self):
        for name, rows in [("envelopes", self.envelopes), ("development", self.development), ("holdout", self.holdout)]:
            (self.root / f"{name}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare_human_review.py"),
                                 "--development", str(self.root / "development.jsonl"), "--holdout", str(self.root / "holdout.jsonl"),
                                 "--envelopes", str(self.root / "envelopes.jsonl"), "--snapshot-root", str(self.root),
                                 "--run", "synthetic", "--output-dir", str(self.root / "cli")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["blank_judgments"], 1)


if __name__ == "__main__":
    unittest.main()
