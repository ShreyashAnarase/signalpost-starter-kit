#!/usr/bin/env python3
"""Freeze small stratified diagnostic sets before reviewing website matches."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import heapq
import json
from collections import Counter
from pathlib import Path


def company_type(row):
    division = str(row.get("industry_code") or "").split(".")[0]
    sector = "finance_property" if division in {"64", "65", "66", "68"} else "other_sectors"
    size = "5plus_staff" if (row.get("employees") or 0) >= 5 else "small_or_unknown_staff"
    return "|".join([sector, size, "registry_web" if row.get("website") else "no_registry_web"])


def select_sets(rows, excluded, per_stratum=3, seed="signalpost-coverage-20261012"):
    heaps, population = {}, Counter()
    for row in rows:
        org = row["organisation_number"]
        if org in excluded:
            continue
        group = company_type(row)
        population[group] += 1
        rank = int(hashlib.sha256(f"{seed}:{org}".encode()).hexdigest(), 16)
        heap = heaps.setdefault(group, [])
        entry = (-rank, org, row)
        if len(heap) < 2 * per_stratum:
            heapq.heappush(heap, entry)
        elif rank < -heap[0][0]:
            heapq.heapreplace(heap, entry)
    splits = {"development": [], "holdout": []}
    for group, heap in sorted(heaps.items()):
        for index, (_, _, row) in enumerate(sorted(heap, reverse=True)):
            split = "development" if index % 2 == 0 else "holdout"
            splits[split].append({**row, "coverage_stratum": group, "evaluation_split": split})
    return splits, dict(sorted(population.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", required=True)
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--per-stratum", type=int, default=3)
    args = parser.parse_args()
    if args.per_stratum < 1:
        parser.error("per-stratum must be positive")
    excluded = {json.loads(line)["organisation_number"] for path in args.exclude
                for line in Path(path).read_text().splitlines() if line.strip()}
    opener = gzip.open if args.universe.endswith(".gz") else open
    with opener(args.universe, "rt") as handle:
        splits, population = select_sets((json.loads(line) for line in handle if line.strip()), excluded, args.per_stratum)
    directory = Path(args.output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    for split, rows in splits.items():
        (directory / f"{split}.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    manifest = {"seed": "signalpost-coverage-20261012", "population_by_stratum": population,
                "excluded_companies": len(excluded), "split_counts": {name: len(rows) for name, rows in splits.items()},
                "files_sha256": {name: hashlib.sha256((directory / f"{name}.jsonl").read_bytes()).hexdigest() for name in splits},
                "interpretation": "Equal allocation diagnostic sample, not population-weighted recall. Holdout must remain unused during tuning. Missing employee counts are grouped, never asserted as zero.",
                "review_required": "For each company record candidate URL, exact/wrong/unresolved label, supporting source URL/hash/span, and reviewer. Unknown is not a true negative. Report coverage and reviewed precision separately by stratum; do not derive an official score."}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
