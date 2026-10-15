#!/usr/bin/env python3
"""Build a declared, bounded official NAV candidate index without company claims."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from norway_company_agent.acquisition import ResearchSession, SnapshotStore
from norway_company_agent.nav_jobs import collect_jobs
from norway_company_agent.versioning import source_fingerprint


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, help='New private directory; includes cache and source snapshots')
    parser.add_argument('--lookback-days', type=int, default=30)
    parser.add_argument('--max-pages', type=int, default=60)
    parser.add_argument('--max-requests', type=int, default=100)
    parser.add_argument('--timeout-seconds', type=float, default=180)
    parser.add_argument('--request-timeout', type=float, default=15)
    args = parser.parse_args(argv)
    if min(args.lookback_days,args.max_pages,args.max_requests,args.timeout_seconds,args.request_timeout)<=0 or not all(
            math.isfinite(value) for value in [args.timeout_seconds,args.request_timeout]):
        parser.error('All NAV acquisition budgets must be finite and positive')
    if not os.environ.get('NAV_API_TOKEN','').strip():
        parser.error('Set permitted NAV_API_TOKEN access securely; no public experiment-token fallback')
    output=Path(args.output_dir)
    try:
        output.mkdir(parents=True,exist_ok=False)
    except OSError:
        parser.error('Output must be a new writable directory')
    started=time.monotonic()
    session=ResearchSession(SnapshotStore(output/'snapshots'),timeout=args.request_timeout,
        deadline=started+args.timeout_seconds,max_requests=args.max_requests)
    records,report=collect_jobs([],session,max_pages=args.max_pages,max_details=1,
        lookback_days=args.lookback_days,cache_output=output/'candidates.json')
    saved=report.get('cache_output',{}).get('status')=='saved'
    usable=saved and report['pages']>0
    result={'mode':'declared_nav_candidate_bootstrap','status':'complete' if usable and report['scan_complete'] else 'partial' if usable else 'failed',
            'source_sha256':source_fingerprint(ROOT),'elapsed_seconds':round(time.monotonic()-started,3),
            'published_company_claims':0,'live_detail_verification_required':True,'report':report,
            'boundary':'Candidate discovery only. Partial or empty indices do not prove absence of jobs.'}
    assert not records
    (output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='report'},indent=2))
    return 0 if usable else 1


if __name__=='__main__':
    raise SystemExit(main())
