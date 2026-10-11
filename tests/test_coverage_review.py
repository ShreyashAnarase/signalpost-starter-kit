import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("coverage_review", Path(__file__).resolve().parents[1] / "scripts/prepare_coverage_review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CoverageReviewTests(unittest.TestCase):
    def test_order_independent_disjoint_splits_exclude_seen_companies(self):
        rows = [{"organisation_number": str(100000000 + index), "employees": None,
                 "industry_code": "68.320", "website": ""} for index in range(20)]
        excluded = {rows[0]["organisation_number"]}
        splits, population = module.select_sets(rows, excluded)
        self.assertEqual((splits, population), module.select_sets(reversed(rows), excluded))
        dev = {row["organisation_number"] for row in splits["development"]}
        holdout = {row["organisation_number"] for row in splits["holdout"]}
        self.assertEqual(len(dev), 3)
        self.assertEqual(len(holdout), 3)
        self.assertFalse(dev & holdout or (dev | holdout) & excluded)
        self.assertTrue(all(row["employees"] is None for row in splits["development"]))
