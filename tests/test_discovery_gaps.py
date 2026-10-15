from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.acquisition import AcquisitionError, Capture, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.search_discovery import SearchBudget, rank_candidates
from norway_company_agent.site_research import assess_site, extract_site_facts, legal_org_numbers, read_page, research_site
from norway_company_agent.submission import submission_envelope

PROFILE = {'organisation_number': '123456789', 'name': 'EXAMPLE WIDGET AS', 'evidence': {}}


class DiscoveryGapTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = SnapshotStore(directory.name)

    def session(self, pages):
        store = self.store
        class Session:
            third_party_cost_usd = 0
            def get(self, url, **kwargs):
                if url not in pages:
                    raise AcquisitionError('HTTP 404', 'not_available')
                raw = pages[url].encode()
                return Capture(url, url, 200, 'text/html; charset=utf-8', raw,
                               '2026-10-14T00:00:00Z', **store.save(raw))
        return Session()

    def test_common_org_label_punctuation_is_evidence_but_phone_is_not(self):
        for text in ['Org. nr.: 123 456 789 MVA', 'Org.nr: NO123456789', 'Organisasjonsnummer: 123456789']:
            self.assertEqual(legal_org_numbers(text), {'123456789'}, text)
        for text in ['Phone: 123456789', 'Our orders total 123456789', 'Organization: no ID available']:
            self.assertEqual(legal_org_numbers(text), set())

    def test_legal_paragraph_is_cited_and_conflicting_owner_still_rejected(self):
        url = 'https://example.no/privacy'
        body = '<main><h1>Privacy</h1><p>Example Widget AS is the data controller (organisation number 123456789).</p></main>'
        page, _ = read_page(self.session({url: body}), url, 'legal')
        self.assertTrue(assess_site(PROFILE, [page])['publishable'])
        facts = extract_site_facts(PROFILE, [page])
        profile = copy.deepcopy(PROFILE)
        profile['evidence']['website'] = {'status': 'available', 'value': {'facts': facts}}
        envelope = submission_envelope(profile, run_id='test', started_at=page['retrieved_at'], completed_at=page['retrieved_at'])
        self.assertTrue(audit_envelopes([envelope], ['123456789'])['passed'])
        footer = {**page, 'identity_text_excerpt': 'Org.nr.: 987654321'}
        self.assertFalse(assess_site(PROFILE, [footer])['publishable'])
        for text in ['Our partner Example Widget AS organisation number 123456789 and Another AS org.nr. 987654321',
                     'Example Widget Ltd organisation number 123456789']:
            other, _ = read_page(self.session({url: '<main><p>'+text+'</p></main>'}), url, 'legal')
            self.assertFalse(assess_site(PROFILE, [other])['publishable'])

    def test_new_directory_hosts_cannot_consume_company_candidates(self):
        rows = [{'url': 'https://'+host+'/company', 'title': PROFILE['name'], 'snippet': '123456789'}
                for host in ['opplysning.byndle.no', 'kredittsjekk.no', '1850.no', 'vimeo.com']]
        rows.append({'url': 'https://examplewidget.no/', 'title': PROFILE['name']})
        self.assertEqual([c['url'] for c in rank_candidates(PROFILE, rows)], ['https://examplewidget.no/'])

    def test_failed_registry_candidate_gets_one_capped_search_and_keeps_attempts(self):
        profile = {**PROFILE, 'website': 'https://old.no/'}
        session = self.session({'https://old.no/': '<footer>Org.nr. 987654321</footer>',
                                'https://new.no/': '<footer>Org.nr.: 123456789</footer>'})
        diagnostic = {'provider': 'tavily_search_api', 'status': 'available', 'queries': 1}
        with patch('norway_company_agent.site_research.discover_tavily_candidates',
                   return_value=([{'url': 'https://new.no/', 'discovery_method': 'tavily'}], diagnostic)) as search:
            result = research_site(profile, session, max_pages=1, search_provider='tavily',
                                   search_budget=SearchBudget(max_queries=1, price_per_1000='0', budget_usd='0'))
        self.assertEqual(result['status'], 'available')
        self.assertEqual(len(result['value']['discovery_attempts']), 2)
        self.assertEqual(result['candidate_discovery'], diagnostic)
        self.assertEqual(search.call_count, 1)

    def test_verified_registry_candidate_does_not_spend_a_query(self):
        with patch('norway_company_agent.site_research.discover_tavily_candidates') as search:
            result = research_site({**PROFILE, 'website': 'https://example.no/'},
                self.session({'https://example.no/': '<footer>Org.nr. 123456789</footer>'}),
                max_pages=1, search_provider='tavily',
                search_budget=SearchBudget(max_queries=1, price_per_1000='0', budget_usd='0'))
        self.assertEqual(result['status'], 'available')
        search.assert_not_called()

    def test_search_fallback_does_not_retry_an_existing_domain(self):
        session = self.session({'https://old.no/': '<footer>Org.nr. 987654321</footer>'})
        with patch('norway_company_agent.site_research.discover_tavily_candidates',
                   return_value=([{'url': 'http://www.old.no/', 'discovery_method': 'tavily'}],
                                 {'provider': 'tavily_search_api', 'status': 'available', 'queries': 1})) as search:
            result = research_site({**PROFILE, 'website': 'https://old.no/'}, session,
                                   max_pages=1, search_provider='tavily',
                                   search_budget=SearchBudget(max_queries=1, price_per_1000='0', budget_usd='0'))
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(len(result['discovery_attempts']), 1)
        self.assertEqual(search.call_count, 1)

    def test_labelled_job_has_auditable_employer_date_and_deadline(self):
        body = '<main><h1>Senior engineer</h1><p>Arbeidsgiver: EXAMPLE WIDGET AS</p><p>Publisert: 1. oktober 2026</p><p>Søknadsfrist: 31. oktober 2026</p></main><footer>Org.nr. 123456789</footer>'
        url = 'https://example.no/jobs/engineer'
        page, _ = read_page(self.session({url: body}), url, 'careers')
        facts = extract_site_facts(PROFILE, [page])
        job = next(f for f in facts if f['field'] == 'job_posting')
        self.assertEqual(job['value']['date_posted'], '2026-10-01')
        self.assertEqual(job['value']['valid_through'], '2026-10-31')
        profile = copy.deepcopy(PROFILE)
        profile['evidence']['website'] = {'status': 'available', 'value': {'facts': facts}}
        envelope = submission_envelope(profile, run_id='test', started_at=page['retrieved_at'], completed_at=page['retrieved_at'])
        self.assertTrue(audit_envelopes([envelope], ['123456789'])['passed'])
        source = next(e for e in envelope['evidence'] if e['source_locator']['type'] == 'dom_fields')
        source['source_locator']['fields']['employer']['value'] = 'Arbeidsgiver: OTHER AS'
        self.assertFalse(audit_envelopes([envelope], ['123456789'])['passed'])

    def test_job_missing_dates_wrong_employer_expired_and_conflicting_dates_abstain(self):
        base = '<main><h1>Engineer</h1>{}</main><footer>Org.nr. 123456789</footer>'
        for fields in [
            '<p>Arbeidsgiver: EXAMPLE WIDGET AS</p>',
            '<p>Arbeidsgiver: OTHER AS</p><p>Publisert: 2026-10-01</p>',
            '<p>Arbeidsgiver: EXAMPLE WIDGET AS</p><p>Publisert: 2026-10-01</p><p>Søknadsfrist: 2026-10-02</p>',
            '<p>Arbeidsgiver: EXAMPLE WIDGET AS</p><p>Publisert: 2026-10-01</p><p>Publisert: 2026-10-02</p>',
            '<p>Arbeidsgiver: EXAMPLE WIDGET AS</p><p>Publisert: 2026-10-15</p>',
            '<p>Arbeidsgiver: EXAMPLE WIDGET AS</p><p>Arbeidsgiver: OTHER AS</p><p>Publisert: 2026-10-01</p>',
        ]:
            url = 'https://example.no/jobs/engineer'
            page, _ = read_page(self.session({url: base.format(fields)}), url, 'careers')
            self.assertFalse(any(f['field'] == 'job_posting' for f in extract_site_facts(PROFILE, [page])), fields)

    def test_careers_index_with_metadata_is_not_an_individual_job(self):
        url = 'https://example.no/jobs/'
        body = '<main><h1>Ledige stillinger</h1><p>Arbeidsgiver: EXAMPLE WIDGET AS</p><p>Publisert: 2026-10-01</p><h2>Engineer</h2><h2>Designer</h2></main><footer>Org.nr. 123456789</footer>'
        page, _ = read_page(self.session({url: body}), url, 'careers')
        self.assertFalse(any(f['field'] == 'job_posting' for f in extract_site_facts(PROFILE, [page])))


if __name__ == '__main__':
    unittest.main()
