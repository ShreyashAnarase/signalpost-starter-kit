from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import test_discovery_gaps as fixtures
from norway_company_agent.acquisition import Capture
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.site_research import assess_site, extract_site_facts, legal_org_numbers, read_page, research_site
from norway_company_agent.submission import submission_envelope

PROFILE = {**fixtures.PROFILE, 'evidence': {'registry_live': {'value': {
    'business_address': {'adresse': ['Example Street 13'], 'postnummer': '0480'}}}}}


class LegalNoticeRecoveryTests(unittest.TestCase):
    setUp = fixtures.DiscoveryGapTests.setUp
    session = fixtures.DiscoveryGapTests.session

    def assert_audited(self, pages):
        facts = extract_site_facts(PROFILE, pages)
        self.assertTrue(any(f['field']=='official_website' for f in facts))
        profile = copy.deepcopy(PROFILE)
        profile['evidence']['website'] = {'status': 'available', 'value': {'facts': facts}}
        envelope = submission_envelope(profile, run_id='legal', started_at=pages[0]['retrieved_at'], completed_at=pages[0]['retrieved_at'])
        audit = audit_envelopes([envelope], [PROFILE['organisation_number']])
        self.assertTrue(audit['passed'], audit)
        return envelope

    def test_foreign_register_label_and_norwegian_definite_form_resolve_footer(self):
        for label in ['Foretaksregisteret:', 'Foretaksregister:', 'Registration number:']:
            url = 'https://example.no/'
            page, _ = read_page(self.session({url: '<footer>'+label+' 123 456 789</footer>'}), url, 'homepage')
            self.assertTrue(assess_site(PROFILE, [page])['publishable'])
            self.assert_audited([page])
        self.assertEqual(legal_org_numbers('Foretaksregisteret: 987654321'), {'987654321'})
        self.assertEqual(legal_org_numbers('Order number: 123456789'), set())

    def test_adjacent_legal_paragraphs_require_exact_name_and_registered_address(self):
        url = 'https://example.no/terms'
        body = '<main><div><p>Registration number: 123 456 789</p><p>\u200b</p><p>EXAMPLE WIDGET AS</p><p>Example Street 13</p><p>0480 Oslo</p></div></main>'
        page, _ = read_page(self.session({url: body}), url, 'legal')
        self.assertTrue(assess_site(PROFILE, [page])['publishable'])
        envelope = self.assert_audited([page])
        sources = [e for e in envelope['evidence'] if e['source_locator']['type']=='css_text']
        self.assertTrue(any(',' in e['source_locator']['selector'] for e in sources))
        for before, after in [('Example Street 13', 'Somewhere Else 24'), ('0480', '9999'),
                              ('EXAMPLE WIDGET AS', 'EXAMPLE WIDGET HOLDING AS'),
                              ('</div>', '<p>Another AS org.nr. 987654321</p></div>'),
                              ('<p>EXAMPLE WIDGET AS</p>', '<h2>Another business</h2><p>EXAMPLE WIDGET AS</p>')]:
            changed, _ = read_page(self.session({url: body.replace(before, after)}), url, 'legal')
            self.assertFalse(assess_site(PROFILE, [changed])['publishable'], (before,after))

    def test_deep_legal_link_is_followed_with_existing_page_budget(self):
        home='https://example.no/'
        pages={home:'<h1>Example</h1><a href="/about">About</a>',
               home+'about':'<h1>About us</h1><a href="/terms">Terms</a>',
               home+'terms':'<footer>Foretaksregisteret: 123456789</footer>'}
        profile={**PROFILE,'website':home}
        short=research_site(profile,self.session(pages),max_pages=2)
        self.assertNotEqual(short['status'],'available')
        result=research_site(profile,self.session(pages),max_pages=3)
        self.assertEqual(result['status'],'available')
        self.assertEqual(len(result['value']['pages']),3)
        self.assert_audited(result['value']['pages'])

    def test_xml_declaration_with_non_utf8_html_keeps_original_bytes_and_audits(self):
        text='<?xml version="1.0" encoding="ISO-8859-1"?><html><head><title>Blåbær</title><meta name="description" content="Norwegian blåbær business"><script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Blåbær AS"}</script></head><body><main><p>Welcome to our blåbær business and products.</p></main><footer>Org.nr. 123456789</footer></body></html>'
        raw=text.encode('iso-8859-1')
        store=self.store
        class Session:
            def get(self,url,**kwargs):
                return Capture(url,url,200,'text/html; charset=iso-8859-1',raw,'2026-10-14T00:00:00Z',**store.save(raw))
        page,_=read_page(Session(),'https://example.no/','homepage')
        self.assertEqual(page['title'],'Blåbær')
        self.assertEqual(page['structured_organisations'][0]['name'],'Blåbær AS')
        self.assertEqual(page['content_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(Path(page['snapshot_path']).read_bytes(),raw)
        self.assert_audited([page])
