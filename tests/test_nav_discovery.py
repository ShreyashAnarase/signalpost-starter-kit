from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_nav_jobs as fixtures
from test_nav_jobs import FEED, BASE, UID, ORG, PROFILE, Session, header, detail
from norway_company_agent.nav_jobs import candidate_employers, collect_jobs
from norway_company_agent.identity import _tokens
from norway_company_agent import nav_cache
from norway_company_agent.audit import audit_envelopes

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_nav_candidate_cache',ROOT/'scripts/build_nav_candidate_cache.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class NavDiscoveryTests(unittest.TestCase):
    setUp=fixtures.NavJobTests.setUp
    collect=fixtures.NavJobTests.collect

    def test_workplace_suffix_or_reordered_name_still_gets_fresh_exact_employer_check(self):
        for name in ['EXAMPLE WIDGET AS avdeling Oslo','WIDGET EXAMPLE AS']:
            records,report,session=self.collect(items=[header(name=name)])
            self.assertEqual(report['confirmed_jobs'],1)
            self.assertEqual(report['candidate_details'],1)
            self.assertIn(BASE+'/api/v1/feedentry/'+UID,session.calls)
            self.assertEqual(records[ORG]['status'],'available')

    def test_subsidiary_name_candidate_cannot_publish_for_parent(self):
        payload=detail();payload['json']['employer']['orgnr']='987654321'
        records,report,_=self.collect(payload,items=[header(name='EXAMPLE WIDGET SUBSIDIARY AS')])
        self.assertEqual(report['candidate_details'],1)
        self.assertEqual(report['confirmed_jobs'],0)
        self.assertNotEqual(records[ORG]['status'],'available')

    def test_live_ad_content_shape_emits_audited_fact_and_verified_cache_identity(self):
        payload=detail();payload['ad_content']=payload.pop('json')
        output=self.root/'live-shape.json'
        records,report,_=self.collect(payload,cache_output=output)
        self.assertEqual(report['confirmed_jobs'],1)
        envelope=fixtures.NavJobTests.envelope(self,records)
        self.assertTrue(audit_envelopes([envelope],[ORG])['passed'])
        self.assertEqual(nav_cache.load(output)[0][UID]['employer_organisation_number'],ORG)
        source=next(s for s in envelope['evidence'] if s['source_class']=='official_job_feed')
        self.assertIn('ad_content',json.loads(source['claim_span']))
        self.assertNotIn('json',json.loads(source['claim_span']))

    def test_conflicting_envelopes_or_live_wrong_employer_never_publish(self):
        payload=detail();payload['ad_content']=json.loads(json.dumps(payload['json']))
        payload['ad_content']['employer']['orgnr']='987654321'
        _,report,_=self.collect(payload)
        self.assertEqual(report['confirmed_jobs'],0)
        payload.pop('json')
        _,report,_=self.collect(payload)
        self.assertEqual(report['confirmed_jobs'],0)

    def test_official_workplace_parent_is_labelled_and_both_sources_are_required(self):
        child='987654321';url='https://data.brreg.no/enhetsregisteret/api/underenheter/'+child
        payload=detail();payload['ad_content']=payload.pop('json');payload['ad_content']['employer']['orgnr']=child
        relationship={'organisasjonsnummer':child,'overordnetEnhet':ORG,'organisasjonsform':{'kode':'BEDR'}}
        records,report,_=self.collect(payload,extra={url:relationship})
        self.assertEqual(report['confirmed_jobs'],1)
        self.assertEqual(report['subunit_matched_jobs'],1)
        envelope=fixtures.NavJobTests.envelope(self,records)
        job=next(c for c in envelope['claims'] if c['field']=='job_posting' and c['availability']=='available')
        self.assertEqual(job['value']['employer_organisation_number'],ORG)
        self.assertEqual(job['value']['registered_employer_organisation_number'],child)
        self.assertEqual(job['relationship'],'registered_workplace_of')
        self.assertEqual(len(job['evidence_ids']),2)
        self.assertTrue(audit_envelopes([envelope],[ORG])['passed'])
        source=next(s for s in envelope['evidence'] if s['source_url']==url)
        Path(source['snapshot_path']).write_text('{}')
        broken=fixtures.NavJobTests.envelope(self,records)
        self.assertFalse(any(c['field']=='job_posting' and c['availability']=='available' for c in broken['claims']))

    def test_corporate_parent_other_company_deleted_or_mismatched_workplace_is_rejected(self):
        child='987654321';url='https://data.brreg.no/enhetsregisteret/api/underenheter/'+child
        payload=detail();payload['json']['employer']['orgnr']=child
        base={'organisasjonsnummer':child,'overordnetEnhet':ORG,'organisasjonsform':{'kode':'BEDR'}}
        for change in [{'overordnetEnhet':'555555555'},{'organisasjonsform':{'kode':'AS'}},
                       {'organisasjonsnummer':'111111111'},{'slettedato':'2026-10-01'}]:
            _,report,_=self.collect(payload,extra={url:base|change})
            self.assertEqual(report['confirmed_jobs'],0)

    def test_short_generic_name_is_not_a_workplace_prefix(self):
        names={frozenset(_tokens('AB AS')):{ORG}}
        self.assertFalse(candidate_employers('AB CONSULTING AS',names))
        self.assertEqual(candidate_employers('AB AS',names),{ORG})
        self.assertFalse(candidate_employers('EXAMPLE CONSTRUCTION AS',{frozenset(_tokens(PROFILE['name'])):{ORG}}))

    def test_cache_builder_requires_permitted_credential_and_preserves_existing_output(self):
        target=self.root/'not-created'
        with patch.dict(os.environ,{'NAV_API_TOKEN':''}):
            with self.assertRaises(SystemExit) as exc:builder.main(['--output-dir',str(target)])
        self.assertEqual(exc.exception.code,2);self.assertFalse(target.exists())
        target.mkdir();(target/'existing').write_text('preserve')
        with patch.dict(os.environ,{'NAV_API_TOKEN':'fixture-token'}):
            with self.assertRaises(SystemExit):builder.main(['--output-dir',str(target)])
        self.assertEqual((target/'existing').read_text(),'preserve')

    def test_cache_builder_indexes_global_headers_without_publishing_jobs(self):
        target=self.root/'index'
        def session_factory(store,**kwargs):
            return Session(store,{FEED:{'items':[header()], 'next_url':'/api/v1/feed/page2'}})
        with patch.dict(os.environ,{'NAV_API_TOKEN':'fixture-token'}),patch.object(builder,'ResearchSession',side_effect=session_factory):
            result=builder.main(['--output-dir',str(target),'--max-pages','1'])
        self.assertEqual(result,0)
        report=json.loads((target/'report.json').read_text())
        self.assertEqual(report['status'],'partial')
        self.assertEqual(report['published_company_claims'],0)
        self.assertEqual(report['report']['candidate_details'],0)
        rows,_=nav_cache.load(target/'candidates.json')
        self.assertEqual(set(rows),{UID})
        self.assertNotIn('fixture-token',json.dumps(report))
