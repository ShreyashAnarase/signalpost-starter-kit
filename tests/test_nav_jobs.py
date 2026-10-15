from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.acquisition import AcquisitionError, Capture, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.nav_jobs import BASE, FEED, collect_jobs, feed_url
from norway_company_agent.packaging import package_submission
from norway_company_agent.showcase import public_profiles
from norway_company_agent.submission import merge_refresh, submission_envelope

UID = '12345678-1234-1234-1234-123456789abc'
ORG = '123456789'
PROFILE = {'organisation_number': ORG, 'name': 'EXAMPLE WIDGET AS', 'evidence': {}}
NOW = '2026-10-14T00:00:00Z'


def header(uid=UID, status='ACTIVE', name='EXAMPLE WIDGET AS'):
    return {'url': '/api/v1/feedentry/'+uid, '_feed_entry': {'uuid': uid, 'status': status, 'businessName': name}}


def detail():
    return {'uuid': UID, 'status': 'ACTIVE', 'json': {'uuid': UID, 'employer': {'orgnr': ORG, 'name': PROFILE['name']},
            'title': 'Engineer', 'published': '2026-10-01T00:00:00Z', 'expires': '2026-10-31T00:00:00Z',
            'applicationUrl': 'https://apply.example.test/engineer',
            'contactList': [{'name': 'Private contact must not enter public output'}]}}


class Session:
    def __init__(self, store, pages):
        self.store, self.pages = store, pages
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        assert kwargs['allow_redirects'] is False
        if url not in self.pages:
            raise AcquisitionError('Fixture timeout')
        value = self.pages[url]
        status, body = value if isinstance(value, tuple) else (200, value)
        raw = json.dumps(body).encode()
        return Capture(url, url, status, 'application/json', raw, NOW, **self.store.save(raw))

    def _validate_url(self, url):
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.hostname != 'apply.example.test' or parts.username:
            raise AcquisitionError('Invalid application URL', 'blocked')

    def metrics(self):
        return {'requests': len(self.calls), 'bytes': 0, 'latencies_ms': [1]*len(self.calls), 'third_party_cost_usd': 0}


class NavJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = SnapshotStore(self.root/'snapshots')

    def collect(self, payload=None, *, items=None, next_url=None, extra=None, **options):
        pages = {FEED: {'items': items if items is not None else [header()], 'next_url': next_url},
                 BASE+'/api/v1/feedentry/'+UID: detail() if payload is None else payload}
        pages.update(extra or {})
        session = Session(self.store, pages)
        records, report = collect_jobs([PROFILE], session, token='never-log-this-token',
            since=datetime(2026, 9, 1, tzinfo=timezone.utc), **options)
        self.assertNotIn('never-log-this-token', json.dumps([records, report]))
        return records, report, session

    def envelope(self, records, run='nav'):
        return submission_envelope({**PROFILE, 'evidence': {'nav_jobs': records[ORG]}},
            run_id=run, started_at=NOW, completed_at=NOW)

    def test_exact_employer_active_detail_emits_auditable_official_source_and_portable_package(self):
        records, report, session = self.collect()
        self.assertEqual(report['confirmed_jobs'], 1)
        self.assertEqual(report['companies'], 1)
        self.assertTrue(report['scan_complete'])
        self.assertEqual(len(session.calls), 2)
        e = self.envelope(records)
        job = next(c for c in e['claims'] if c['field']=='job_posting' and c['availability']=='available')
        self.assertEqual(job['value']['employer_organisation_number'], ORG)
        source = next(s for s in e['evidence'] if s['id'] in job['evidence_ids'])
        self.assertEqual(source['source_class'], 'official_job_feed')
        self.assertTrue(audit_envelopes([e], [ORG])['passed'])
        self.assertNotIn('Private contact', json.dumps(public_profiles([e])))
        self.assertTrue(package_submission([e], [ORG], self.root/'package')['audit']['passed'])
        tampered = copy.deepcopy(e)
        next(s for s in tampered['evidence'] if s['id']==source['id'])['claim_span'] = '{}'
        self.assertFalse(audit_envelopes([tampered], [ORG])['passed'])

    def test_wrong_employer_subunit_stale_future_expired_and_wrong_uuid_are_rejected(self):
        variations = []
        for org in ['987654321', 123456789]:
            p = detail();p['json']['employer']['orgnr']=org;variations.append(p)
        for key, value in [('published', '2026-10-15T00:00:00Z'), ('expires', '2026-10-13T00:00:00Z'), ('expires', None)]:
            p=detail();p['json'][key]=value;variations.append(p)
        p=detail();p['status']='INACTIVE';variations.append(p)
        p=detail();p['uuid']='98765432-1234-1234-1234-123456789abc';variations.append(p)
        for p in variations:
            records, report, _ = self.collect(p)
            self.assertEqual(report['confirmed_jobs'], 0)
            self.assertNotEqual(records[ORG]['status'], 'available')

    def test_unsafe_pagination_cannot_receive_bearer_token_and_bounds_are_explicit(self):
        records, report, session = self.collect(items=[], next_url='https://attacker.test/api/v1/feed')
        self.assertFalse(report['scan_complete'])
        self.assertEqual(session.calls, [FEED])
        self.assertEqual(records[ORG]['status'], 'source_error')
        records, report, session = self.collect(items=[], next_url='/api/v1/feed/page2', max_pages=1)
        self.assertFalse(report['scan_complete'])
        self.assertEqual(len(session.calls), 1)
        for url in ['http://pam-stilling-feed.nav.no/api/v1/feed', BASE+'@attacker.test/api/v1/feed', BASE+'/admin']:
            with self.assertRaises(ValueError):feed_url(url)

    def test_inactive_later_entry_removes_earlier_confirmed_job(self):
        records, report, _ = self.collect(next_url='/api/v1/feed/page2', extra={
            BASE+'/api/v1/feed/page2': {'items': [header(status='INACTIVE')], 'next_url': None}})
        self.assertEqual(report['confirmed_jobs'], 0)
        self.assertNotEqual(records[ORG]['status'], 'available')

    def test_failure_or_missing_key_keeps_all_company_records_and_no_public_token_fallback(self):
        profiles = [PROFILE, {'organisation_number': '987654321', 'name': 'OTHER AS'}]
        session = Session(self.store, {FEED: (403, {})})
        records, report = collect_jobs(profiles, session, token='secret')
        self.assertEqual(set(records), {ORG, '987654321'})
        self.assertTrue(all(r['status']=='blocked' for r in records.values()))
        self.assertEqual(report['companies'], 0)
        session = Session(self.store, {})
        with patch.dict(os.environ, {'NAV_API_TOKEN': ''}):
            records, _ = collect_jobs(profiles, session)
        self.assertEqual(len(records), 2)
        self.assertEqual(session.calls, [])

    def test_invalid_application_url_cannot_be_published(self):
        for url in ['javascript:alert(1)', 'http://127.0.0.1/private', 'https://user:pass@apply.example.test/']:
            p=detail();p['json']['applicationUrl']=url
            _, report, _ = self.collect(p)
            self.assertEqual(report['confirmed_jobs'], 0)

    def test_prior_job_is_freshly_revalidated_outside_discovery_window(self):
        records, report, session = self.collect(items=[], prior_job_ids=[UID])
        self.assertEqual(report['prior_jobs_rechecked'], 1)
        self.assertEqual(report['confirmed_jobs'], 1)
        self.assertEqual(session.calls[0], BASE+'/api/v1/feedentry/'+UID)
        self.assertFalse(report['full_active_window_covered'])
        self.assertEqual(records[ORG]['status'], 'available')
        _, report, _ = self.collect(detail() | {'status':'INACTIVE'}, items=[], prior_job_ids=[UID])
        self.assertEqual(report['confirmed_jobs'],0)

    def test_old_inactive_event_does_not_hide_a_freshly_reactivated_job(self):
        row=header(status='INACTIVE');row['date_modified']='2026-10-02T00:00:00Z'
        _, report, _ = self.collect(items=[row], prior_job_ids=[UID])
        self.assertEqual(report['confirmed_jobs'],1)

    def test_detail_cap_does_not_appear_as_complete_scan(self):
        other='87654321-1234-1234-1234-123456789abc'
        _, report, session = self.collect(items=[header(),header(uid=other)], max_details=1)
        self.assertFalse(report['scan_complete'])
        self.assertEqual(report['candidate_details'],1)
        self.assertEqual(len(session.calls),2)

    def test_failed_refresh_removes_nav_job_from_display_but_preserves_private_evidence(self):
        records, _, _ = self.collect()
        old = self.envelope(records)
        missing = {ORG: {'status': 'source_error', 'note': 'NAV unavailable'}}
        current = self.envelope(missing, 'refresh')
        merged = merge_refresh(current, old)
        jobs = [c for c in merged['claims'] if c['field']=='job_posting']
        self.assertTrue(all(c['value'] is None and c['availability']!='available' for c in jobs))
        self.assertTrue(any(c['source_policy']=='nav_remove_from_display' for c in merged['changes']))
        self.assertTrue(audit_envelopes([merged], [ORG])['passed'])
        display = json.dumps(public_profiles([merged]))
        self.assertNotIn('Engineer', display)
        self.assertNotIn('Private contact', display)
        self.assertTrue(any(s['source_class']=='official_job_feed' for s in merged['evidence']))
        self.assertEqual(merged, merge_refresh(copy.deepcopy(current), old))


if __name__ == '__main__':
    unittest.main()
