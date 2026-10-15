#!/usr/bin/env python3
"""Create an offline audited, relocatable submission evidence package."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from norway_company_agent.batch import read_organisation_numbers
from norway_company_agent.packaging import package_submission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--organisations', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--snapshot-root', help='Root for relative input snapshot references; defaults to input file directory')
    args = parser.parse_args()
    source = Path(args.input).resolve()
    envelopes = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
    manifest = package_submission(envelopes, read_organisation_numbers(args.organisations), args.output_dir,
                                  snapshot_root=args.snapshot_root or source.parent)
    print(json.dumps({'envelopes': manifest['envelopes'], 'audit': manifest['audit']}, indent=2))


if __name__ == '__main__':
    main()
