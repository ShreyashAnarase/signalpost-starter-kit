from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from norway_company_agent.submission import summarize, submission_envelope
from norway_company_agent.acquisition import SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.official import normalize_financials


def account(year, revenue, currency='NOK', scope='SELSKAP'):
    period = {'fraDato': f'{year}-01-01', 'tilDato': f'{year}-12-31'}
    base = {'availability': 'available', 'reporting_period': period, 'account_scope': scope}
    return [{**base, 'id': f'revenue-{year}-{scope}', 'field': 'financials.revenue', 'value': revenue},
            {**base, 'id': f'currency-{year}-{scope}', 'field': 'financials.currency', 'value': currency}]


class SynthesisTests(unittest.TestCase):
    def test_real_financial_export_preserves_currency_scope_and_trend_evidence(self):
        raw = [{'id': str(year), 'regnskapstype': 'SELSKAP', 'valuta': 'NOK',
                'regnskapsperiode': {'fraDato': f'{year}-01-01', 'tilDato': f'{year}-12-31'},
                'resultatregnskapResultat': {'driftsresultat': {'driftsinntekter': {'sumDriftsinntekter': value}}}}
               for year, value in [(2024, 100), (2025, 120)]]
        with tempfile.TemporaryDirectory() as directory:
            record = {'status': 'available', 'source_type': 'official_annual_accounts', 'source_url': 'https://data.brreg.no/regnskap/123456789',
                      'retrieved_at': '2026-10-13T00:00:00Z', 'value': normalize_financials(raw),
                      **SnapshotStore(directory).save(json.dumps(raw).encode())}
            envelope = submission_envelope({'organisation_number': '123456789', 'evidence': {'financials': record}},
                                           run_id='test', started_at=record['retrieved_at'], completed_at=record['retrieved_at'])
            currencies = [c for c in envelope['claims'] if c['field'] == 'financials.currency']
            self.assertEqual({c['account_scope'] for c in currencies}, {'SELSKAP'})
            self.assertEqual(next(s['calculation']['result_percent'] for s in envelope['summary'] if 'calculation' in s), 20)
            self.assertTrue(audit_envelopes([envelope], ['123456789'])['passed'])

    def test_comparable_annual_trend_cites_both_values_and_currencies(self):
        claims = account(2024, 100) + account(2025, 120)
        summary = summarize(claims)
        trend = next(sentence for sentence in summary if 'calculation' in sentence)
        self.assertEqual(trend['calculation']['result_percent'], 20)
        self.assertEqual(set(trend['claim_ids']), {c['id'] for c in claims})
        self.assertIn('calculation from filed accounts', trend['text'])
        self.assertEqual([c['value'] for c in claims if c['field'] == 'financials.revenue'], [100, 120])

    def test_missing_zero_mixed_currency_scopes_and_nonannual_periods_abstain(self):
        cases = [account(2024, 0) + account(2025, 120),
                 account(2024, 100, 'EUR') + account(2025, 120),
                 account(2024, 100, scope='KONSERN') + account(2025, 120),
                 account(2023, 100) + account(2025, 120),
                 account(2024, 100)[:1] + account(2025, 120)]
        short = account(2024, 100) + account(2025, 120)
        for claim in short[:2]:
            claim['reporting_period'] = {'fraDato': '2024-07-01', 'tilDato': '2024-12-31'}
        cases.append(short)
        for claims in cases:
            with self.subTest(claims=claims):
                self.assertFalse(any('calculation' in sentence for sentence in summarize(claims)))

    def test_entity_accounts_preferred_and_amended_conflicts_not_compared(self):
        summary = summarize(account(2025, 120) + account(2025, 900, scope='KONSERN'))
        self.assertIn('120 NOK; scope: SELSKAP', summary[0]['text'])
        claims = account(2024, 100) + account(2025, 120)
        amendment = {**claims[2], 'id': 'amendment', 'value': 125}
        self.assertFalse(any('calculation' in s for s in summarize(claims + [amendment])))
        conflict = {**claims[3], 'id': 'currency-conflict', 'value': 'EUR'}
        self.assertFalse(any('calculation' in s for s in summarize(claims + [conflict])))

    def test_last_known_financials_are_not_used_for_a_current_trend(self):
        claims = account(2024, 100) + account(2025, 120)
        for claim in claims[:2]:
            claim['freshness'] = 'last_known'
        self.assertFalse(any('calculation' in s for s in summarize(claims)))

    def test_latest_company_article_summary_keeps_its_date_and_claim_reference(self):
        claim = {'id': 'news', 'field': 'company_news', 'availability': 'available', 'effective_at': '2026-09-24',
                 'value': {'headline': 'New branch', 'date_published': '2026-09-24'}}
        sentence = summarize([claim])[-1]
        self.assertEqual(sentence['claim_ids'], ['news'])
        self.assertIn('company-authored', sentence['text'])
        self.assertIn('2026-09-24', sentence['text'])


if __name__ == '__main__':
    unittest.main()
