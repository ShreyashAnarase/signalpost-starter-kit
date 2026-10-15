from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.acquisition import AcquisitionError, Capture, ResearchSession, SnapshotStore
from norway_company_agent.search_discovery import SearchBudget, discover_candidates, rank_candidates
from norway_company_agent.site_research import research_site

PROFILE = {'organisation_number': '123456789', 'name': 'EXAMPLE WIDGET AS', 'municipality': 'OSLO', 'evidence': {}}
PAYLOAD = {'web': {'results': [{'url': 'https://brand.no/about', 'title': 'Example Widget AS – Brand', 'description': 'Private search snippet to discard'}]}}


class Response(io.BytesIO):
    code = status = 200
    headers = {'Content-Type': 'application/json'}
    def geturl(self):
        return 'https://api.search.brave.com/res/v1/web/search?q=test'


class SearchTests(unittest.TestCase):
    def budget(self, **overrides):
        return SearchBudget(**({'max_queries': 10, 'price_per_1000': '5', 'budget_usd': '0.05'} | overrides))

    def fixture(self, payload=PAYLOAD, status=200):
        session = Mock()
        session.third_party_cost_usd = 0
        raw = json.dumps(payload).encode()
        session.get.return_value = Capture('provider', 'provider', status, 'application/json', raw,
            '2026-10-13T00:00:00Z', hashlib.sha256(raw).hexdigest(), '')
        return session

    def test_decimal_cap_and_concurrent_reservations_do_not_overspend(self):
        budget = self.budget(max_queries=20, budget_usd='0.015')
        with ThreadPoolExecutor(max_workers=8) as workers:
            reservations = list(workers.map(lambda _: budget.reserve(), range(40)))
        self.assertEqual(sum(price is not None for price in reservations), 3)
        self.assertEqual(budget.spent, Decimal('0.015'))
        self.assertIsNone(self.budget(max_queries=1, budget_usd='0.004').reserve())
        free = self.budget(max_queries=1, price_per_1000='0')
        self.assertEqual(free.reserve(), Decimal(0))
        self.assertIsNone(free.reserve())

    def test_invalid_limits_rejected(self):
        for overrides in [{'max_queries': 0}, {'max_queries': True}, {'price_per_1000': '-1'},
                          {'budget_usd': 'NaN'}, {'price_per_1000': 'Infinity'}, {'budget_usd': '0'}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.budget(**overrides)

    @patch.dict(os.environ, {'BRAVE_SEARCH_API_KEY': 'secret-test-key'})
    def test_candidates_can_have_a_different_brand_and_raw_results_are_discarded(self):
        session = self.fixture()
        candidates, diagnostic = discover_candidates(PROFILE, session, self.budget())
        self.assertEqual(candidates[0]['url'], 'https://brand.no/')
        self.assertEqual(diagnostic['queries'], 1)
        self.assertAlmostEqual(session.third_party_cost_usd, .005)
        self.assertFalse(diagnostic['raw_results_retained'])
        self.assertNotIn('Private search snippet', json.dumps([candidates, diagnostic]))
        kwargs = session.get.call_args.kwargs
        self.assertFalse(kwargs['retain'])
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(kwargs['attempts'], 1)

    def test_directories_social_profiles_and_unrelated_results_are_rejected(self):
        rows = [{'url': url, 'title': PROFILE['name'], 'snippet': '123456789'} for url in
                ['https://proff.no/company', 'https://linkedin.com/company/test', 'https://user:pass@example.no/',
                 'https://virksomhet.brreg.no/company', 'https://utdanning.no/company']]
        rows.append({'url': 'https://unrelated.no/', 'title': 'Unrelated AS'})
        self.assertEqual(rank_candidates(PROFILE, rows), [])

    @patch.dict(os.environ, {'BRAVE_SEARCH_API_KEY': ''})
    def test_missing_key_makes_no_request_or_spend(self):
        session = self.fixture()
        budget = self.budget()
        candidates, diagnostic = discover_candidates(PROFILE, session, budget)
        self.assertEqual(candidates, [])
        self.assertEqual(budget.spent, 0)
        session.get.assert_not_called()

    @patch.dict(os.environ, {'BRAVE_SEARCH_API_KEY': 'secret-test-key'})
    def test_provider_errors_and_malformed_bodies_are_explicit_and_sanitized(self):
        for body, status in [({'error': 'secret-test-key'}, 403), ({'web': {'results': 'bad'}}, 200),
                             ({'web': {'results': [None]}}, 200), ({'web': []}, 200)]:
            session = self.fixture(body, status)
            candidates, diagnostic = discover_candidates(PROFILE, session, self.budget())
            self.assertEqual(candidates, [])
            self.assertIn(diagnostic['status'], ['blocked', 'failed'])
            self.assertNotIn('secret-test-key', json.dumps(diagnostic))
            self.assertAlmostEqual(session.third_party_cost_usd, .005)

    @patch.dict(os.environ, {'BRAVE_SEARCH_API_KEY': 'secret-test-key'})
    def test_candidate_still_fails_wrong_company_footer(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(directory)
            session = self.fixture()
            provider = session.get.return_value
            html = b'<h1>Example Widget AS</h1><footer>Org.nr. 987654321</footer>'
            def get(url, **kwargs):
                if 'api.search.brave.com' in url:
                    return provider
                return Capture(url, url, 200, 'text/html', html, '2026-10-13T00:00:00Z', **store.save(html))
            session.get.side_effect = get
            record = research_site(PROFILE, session, search_budget=self.budget())
            self.assertEqual(record['status'], 'ambiguous')
            self.assertIsNone(record.get('value'))
            self.assertNotIn('Private search snippet', json.dumps(record))

    def test_default_does_not_contact_provider(self):
        session = self.fixture()
        self.assertEqual(research_site(PROFILE, session)['status'], 'not_found')
        session.get.assert_not_called()

    def test_transient_acquisition_never_writes_search_bytes_or_logs_queries(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ResearchSession(SnapshotStore(directory))
            opener = Mock()
            opener.open.return_value = Response(json.dumps(PAYLOAD).encode())
            with patch.object(session, '_validate_url'), patch.object(session, '_reserve'), patch('urllib.request.build_opener', return_value=opener):
                capture = session.get(Response(b'').geturl(), retain=False, allow_redirects=False,
                    request_headers={'X-Subscription-Token': 'secret-test-key'})
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertEqual(session.captures, {})
            self.assertEqual(capture.snapshot_path, '')
            self.assertNotIn('q=test', json.dumps(session.attempts))
            self.assertNotIn('secret-test-key', json.dumps(session.metrics()) + json.dumps(session.attempts))

    def test_authenticated_transport_cannot_follow_redirect_or_use_plain_http(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ResearchSession(SnapshotStore(directory))
            with self.assertRaises(AcquisitionError):
                session.get('http://api.example.no/', request_headers={'Authorization': 'secret'}, allow_redirects=False)
            opener = Mock()
            def redirect(request, **kwargs):
                handler = build.call_args.args[0]
                return handler.redirect_request(request, None, 302, 'Found', {}, 'https://attacker.no/')
            opener.open.side_effect = redirect
            with patch.object(session, '_validate_url') as validate, patch.object(session, '_reserve'), patch('urllib.request.build_opener', return_value=opener) as build:
                with self.assertRaisesRegex(AcquisitionError, 'Redirects are prohibited'):
                    session.get('https://api.example.no/', request_headers={'Authorization': 'secret'}, allow_redirects=False)
                self.assertEqual(validate.call_count, 1)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_cli_refuses_search_without_key_before_acquisition(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_competition_batch.py'),
            '--organisations', 'not-present', '--bulk', 'not-present', '--output', 'not-present',
            '--profiles-output', 'not-present', '--report', 'not-present', '--run-id', 'test',
            '--search-provider', 'brave', '--search-max-queries', '10', '--search-price-per-1000', '5', '--search-budget-usd', '1'],
            env={**os.environ, 'BRAVE_SEARCH_API_KEY': ''}, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('BRAVE_SEARCH_API_KEY must be supplied', result.stderr)


if __name__ == '__main__':
    unittest.main()
