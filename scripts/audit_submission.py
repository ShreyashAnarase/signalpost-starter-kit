#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from norway_company_agent.audit import audit_envelopes, resolve_snapshot_path
from norway_company_agent.batch import read_organisation_numbers


def main():
    parser = argparse.ArgumentParser(description="Verify source snapshot hashes, evidence locators and batch membership offline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--snapshot-root", help="Relative evidence path root; defaults to envelope file directory")
    args = parser.parse_args()
    output = Path(args.report).resolve()
    protected = {Path(args.input).resolve(), Path(args.organisations).resolve()}
    if output in protected:
        parser.error('Report must not overwrite input envelopes or organisation batch')
    envelopes = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    root = args.snapshot_root or Path(args.input).resolve().parent
    for envelope in envelopes:
        for source in envelope.get('evidence', []) if isinstance(envelope, dict) else []:
            try:
                if output == resolve_snapshot_path(source['snapshot_path'], root).resolve():
                    parser.error('Report must not overwrite retained source bytes')
            except (KeyError, TypeError, ValueError):
                pass
    report = audit_envelopes(envelopes, read_organisation_numbers(args.organisations),
                             snapshot_root=args.snapshot_root or Path(args.input).resolve().parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            handle.close()
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
