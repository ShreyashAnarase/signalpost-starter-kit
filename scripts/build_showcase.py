#!/usr/bin/env python3
"""Create the /signalpost public sample locally; no deployment or network calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.showcase import build_showcase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-dir', required=True, help='New directory ending in signalpost for the public route')
    parser.add_argument('--snapshot-root', help='Root of a relocated portable evidence package, when applicable')
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    report = build_showcase(rows, Path(args.output_dir), snapshot_root=args.snapshot_root)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
