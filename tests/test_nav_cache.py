from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_nav_jobs as fixtures
from test_nav_jobs import BASE, FEED, UID, ORG, PROFILE, NOW, Session, detail, header
from norway_company_agent import nav_cache
from norway_company_agent.nav_jobs import collect_jobs


class NavCacheTests(unittest.TestCase):
    setUp = fixtures.NavJobTests.setUp
    collect = fixtures.NavJobTests.collect
    def seed(self):
        capture = Session(self.store, {FEED: {'items': []}}).get(FEED, allow_redirects=False)
        row = nav_cache.entry(UID, PROFILE['name'], capture, org=ORG)
        path = self.root/'candidates.json'
        nav_cache.save(path, {UID: row})
        return path

    def test_cached_hint_requires_new_detail_and_current_evidence(self):
        path = self.seed()
        records, report, session = self.collect(items=[], cache_input=path)
        self.assertEqual(session.calls, [BASE+'/api/v1/feedentry/'+UID, FEED])
        self.assertEqual(report['cached_jobs_rechecked'], 1)
        self.assertEqual(report['cache_input']['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(report['confirmed_jobs'], 1)
        fact = records[ORG]['value']['facts'][0]
        self.assertEqual(fact['retrieved_at'], NOW)
        self.assertNotEqual(fact['content_sha256'], nav_cache.load(path)[0][UID]['content_sha256'])

    def test_cache_without_credentials_never_publishes(self):
        path = self.seed()
        session = Session(self.store, {})
        with patch.dict(os.environ, {'NAV_API_TOKEN': ''}):
            records, report = collect_jobs([PROFILE], session, cache_input=path)
        self.assertEqual(session.calls, [])
        self.assertEqual(report['confirmed_jobs'], 0)
        self.assertNotEqual(records[ORG]['status'], 'available')

    def test_inactive_expired_or_wrong_employer_cannot_be_reused(self):
        path = self.seed()
        for change in ['inactive', 'expired', 'wrong-employer']:
            payload = detail()
            if change == 'inactive': payload['status'] = 'INACTIVE'
            if change == 'expired': payload['json']['expires'] = '2026-10-01T00:00:00Z'
            if change == 'wrong-employer': payload['json']['employer']['orgnr'] = '987654321'
            output = self.root/(change+'.json')
            records, report, _ = self.collect(payload, items=[], cache_input=path, cache_output=output)
            self.assertEqual(report['confirmed_jobs'], 0)
            self.assertEqual(set(records), {ORG})
            rows, _ = nav_cache.load(output)
            if change == 'wrong-employer': self.assertEqual(rows[UID]['employer_organisation_number'], '987654321')
            else: self.assertNotIn(UID, rows)

    def test_tampered_or_missing_cache_falls_back_to_live_discovery(self):
        path = self.seed()
        for expected in ['0'*64, None]:
            if expected is None: path.write_text('{"claims": "untrusted profile export"}')
            records, report, _ = self.collect(cache_input=path, expected_cache_sha256=expected)
            self.assertEqual(report['cache_input']['status'], 'rejected')
            self.assertEqual(report['confirmed_jobs'], 1)
            self.assertEqual(records[ORG]['status'], 'available')
        _, report, _ = self.collect(cache_input=self.root/'absent.json')
        self.assertEqual(report['confirmed_jobs'], 1)

    def test_global_headers_are_only_hints_and_inactive_events_remove_them(self):
        other = '87654321-1234-1234-1234-123456789abc'
        output = self.root/'global.json'
        records, report, session = self.collect(items=[header(uid=other, name='ANOTHER COMPANY AS')], cache_output=output)
        self.assertEqual(set(records), {ORG})
        self.assertEqual(report['confirmed_jobs'], 0)
        self.assertEqual(session.calls, [FEED])
        rows, declaration = nav_cache.load(output)
        self.assertEqual(set(rows), {other})
        self.assertTrue(declaration['live_verification_required'])
        self.assertEqual(rows[other]['employer_organisation_number'], None)
        second = self.root/'removed.json'
        _, _, _ = self.collect(items=[header(uid=other, status='INACTIVE')], cache_input=output, cache_output=second)
        self.assertEqual(nav_cache.load(second)[0], {})
        self.assertNotIn('Private contact', output.read_text())
        self.assertNotIn('Engineer', output.read_text())

    def test_existing_output_is_preserved_and_cache_failure_does_not_drop_live_fact(self):
        path = self.seed()
        before = path.read_bytes()
        _, report, _ = self.collect(cache_output=path)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(report['cache_output']['status'], 'failed')
        self.assertEqual(report['confirmed_jobs'], 1)

    def test_index_bounds_are_enforced_during_scan_and_load(self):
        output = self.root/'bounded.json'
        other = '87654321-1234-1234-1234-123456789abc'
        with patch.object(nav_cache, 'MAX_ENTRIES', 1):
            _, report, _ = self.collect(items=[header(), header(uid=other, name='OTHER AS')], cache_output=output)
            self.assertEqual(report['cache_evictions'], 1)
            self.assertEqual(len(nav_cache.load(output)[0]), 1)
        with patch.object(nav_cache, 'MAX_BYTES', 10):
            with self.assertRaises(ValueError): nav_cache.load(output)

    def test_cache_provenance_cannot_name_other_hosts(self):
        path = self.seed()
        payload = json.loads(path.read_text())
        payload['entries'][0]['source_url'] = 'https://pam-stilling-feed.nav.no.attacker.test/api/v1/feed'
        path.write_text(json.dumps(payload))
        with self.assertRaises(ValueError): nav_cache.load(path)

    def test_cli_requires_nav_and_distinct_input_output(self):
        root = Path(__file__).resolve().parents[1]
        base = [sys.executable, str(root/'scripts/run_competition_batch.py'), '--organisations', 'unused', '--bulk', 'unused',
                '--output', 'unused', '--profiles-output', 'unused', '--report', 'unused', '--run-id', 'test']
        for args, message in [(['--nav-cache-input', 'cache.json'], 'require --nav-jobs'),
                              (['--nav-jobs', '--nav-cache-input', 'cache.json', '--nav-cache-output', './cache.json'], 'must be different')]:
            result = subprocess.run(base+args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(message, result.stderr)
