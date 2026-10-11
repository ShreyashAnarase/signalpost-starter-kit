#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.batch import read_organisation_numbers


def main():
    parser = argparse.ArgumentParser(description="Verify source snapshot hashes, evidence locators and batch membership offline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    envelopes = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    report = audit_envelopes(envelopes, read_organisation_numbers(args.organisations))
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
