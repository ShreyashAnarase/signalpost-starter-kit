from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from norway_company_agent.acquisition import Capture, SnapshotStore, ResearchSession
from norway_company_agent.search_discovery import SearchBudget
from norway_company_agent.tavily_discovery import discover_candidates
from norway_company_agent.site_research import research_site

PROFILE = {'organisation_number': '123456789', 'name': 'EXAMPLE WIDGET AS', 'municipality': 'OSLO', 'evidence': {}}


class TavilyTests(unittest.TestCase):
    def budget(self, price='8', count=10, cap='1'):
        return SearchBudget(max_queries=count, price_per_1000=price, budget_usd=cap)

    def session(self, payload=None, status=200):
        payload = payload if payload is not None else {'results': [{'url': 'https://brand.no/about', 'title': 'Example Widget AS', 'content': 'Transient snippet'}], 'answer': 'Never use as evidence', 'usage': {'credits': 1}}
        raw = json.dumps(payload).encode()
        session = Mock()
        session.third_party_cost_usd = 0
        session.get.return_value = Capture('provider', 'provider', status, 'application/json', raw,
            '2026-10-13T20:00:00Z', hashlib.sha256(raw).hexdigest(), '')
        return session

    @patch.dict(os.environ, {'TAVILY_API_KEY': 'test-secret'})
    def test_basic_only_payload_transient_output_and_explicit_price(self):
        session = self.session()
        candidates, diagnostic = discover_candidates(PROFILE, session, self.budget())
        self.assertEqual(candidates[0]['url'], 'https://brand.no/')
        self.assertAlmostEqual(session.third_party_cost_usd, .008)
        kwargs = session.get.call_args.kwargs
        payload = json.loads(kwargs['request_body'])
        self.assertEqual(payload['search_depth'], 'basic')
        self.assertFalse(payload['auto_parameters'])
        self.assertFalse(payload['include_answer'])
        self.assertFalse(payload['include_raw_content'])
        self.assertNotIn(PROFILE['organisation_number'], payload['query'])
        self.assertEqual(kwargs['request_headers']['Authorization'], 'Bearer test-secret')
        self.assertFalse(kwargs['allow_redirects'])
        self.assertFalse(kwargs['retain'])
        public = json.dumps([candidates, diagnostic])
        self.assertNotIn('Transient snippet', public)
        self.assertNotIn('Never use as evidence', public)
        self.assertNotIn('test-secret', public)

    @patch.dict(os.environ, {'TAVILY_API_KEY': ''})
    def test_production_without_key_makes_no_request(self):
        session = self.session()
        budget = self.budget()
        self.assertEqual(discover_candidates(PROFILE, session, budget)[0], [])
        self.assertEqual(budget.queries, 0)
        session.get.assert_not_called()

    @patch.dict(os.environ, {'TAVILY_API_KEY': 'must-not-consume-account-credits'})
    def test_explicit_keyless_trial_never_uses_an_account_key(self):
        session = self.session()
        _, diagnostic = discover_candidates(PROFILE, session, self.budget(price='0', count=1), allow_keyless=True)
        headers = session.get.call_args.kwargs['request_headers']
        self.assertNotIn('Authorization', headers)
        self.assertEqual(headers['X-Tavily-Access-Mode'], 'keyless')
        self.assertEqual(diagnostic['access_mode'], 'keyless_development_trial')
        self.assertEqual(session.third_party_cost_usd, 0)

    @patch.dict(os.environ, {'TAVILY_API_KEY': ''})
    def test_keyless_with_nonzero_price_rejected_before_transport(self):
        session = self.session()
        _, diagnostic = discover_candidates(PROFILE, session, self.budget(), allow_keyless=True)
        self.assertEqual(diagnostic['queries'], 0)
        session.get.assert_not_called()

    @patch.dict(os.environ, {'TAVILY_API_KEY': 'test-secret'})
    def test_quota_or_provider_failure_does_not_retry(self):
        for body, status in [({'error': {'code': 'quota_limit', 'message': 'test-secret'}}, 200),
                             ({'detail': 'test-secret'}, 432), ({'results': 'bad'}, 200),
                             ({'results': [None]}, 200)]:
            session = self.session(body, status)
            candidates, diagnostic = discover_candidates(PROFILE, session, self.budget())
            self.assertEqual(candidates, [])
            self.assertIn(diagnostic['status'], ['failed', 'blocked'])
            self.assertEqual(session.get.call_count, 1)
            self.assertEqual(session.get.call_args.kwargs['attempts'], 1)
            self.assertNotIn('test-secret', json.dumps(diagnostic))

    @patch.dict(os.environ, {'TAVILY_API_KEY': 'test-secret'})
    def test_shared_budget_exhaustion_never_contacts_provider(self):
        session = self.session()
        budget = self.budget(count=1)
        discover_candidates(PROFILE, session, budget)
        candidates, diagnostic = discover_candidates(PROFILE, session, budget)
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostic['queries'], 0)
        self.assertEqual(session.get.call_count, 1)

    @patch.dict(os.environ, {'TAVILY_API_KEY': 'test-secret'})
    def test_pipeline_dispatch_preserves_company_ownership_gate(self):
        for owner, expected in [('123456789', 'available'), ('987654321', 'ambiguous')]:
            with tempfile.TemporaryDirectory() as directory:
                store = SnapshotStore(directory)
                session = self.session()
                provider = session.get.return_value
                def fetch(url, **kwargs):
                    if 'api.tavily.com' in url:
                        return provider
                    html = ('<h1>Example Widget AS</h1><footer>Org.nr. '+owner+'</footer>').encode()
                    return Capture(url, url, 200, 'text/html', html, '2026-10-13T20:00:00Z', **store.save(html))
                session.get.side_effect = fetch
                record = research_site(PROFILE, session, max_pages=1, search_budget=self.budget(), search_provider='tavily')
                self.assertEqual(record['status'], expected)
                self.assertEqual(record['candidate_discovery']['provider'], 'tavily_search_api')
                self.assertNotIn('Transient snippet', json.dumps(record))

    def test_zero_budget_is_valid_only_for_a_declared_free_route(self):
        free = self.budget(price='0', cap='0', count=1)
        self.assertEqual(free.reserve(), 0)
        self.assertIsNone(free.reserve())
        with self.assertRaises(ValueError):
            self.budget(price='8', cap='0')

    def test_multiple_sessions_share_development_search_key_pacing(self):
        clock = [10.0]
        def advance(seconds):
            clock[0] += seconds
        with tempfile.TemporaryDirectory() as directory, patch('norway_company_agent.acquisition._host_next', {}), \
             patch('norway_company_agent.acquisition.time.monotonic', side_effect=lambda: clock[0]), \
             patch('norway_company_agent.acquisition.time.sleep', side_effect=advance):
            sessions = [ResearchSession(SnapshotStore(directory)) for _ in range(2)]
            starts = []
            for index in range(5):
                sessions[index % 2]._reserve('https://api.tavily.com/search')
                starts.append(clock[0])
            for first, second in zip(starts, starts[1:]):
                self.assertGreaterEqual(second - first, .6499)

    def test_cli_requires_tavily_account_key_and_accepts_new_provider(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_competition_batch.py'),
            '--organisations', 'not-present', '--bulk', 'not-present', '--output', 'not-present',
            '--profiles-output', 'not-present', '--report', 'not-present', '--run-id', 'test',
            '--search-provider', 'tavily', '--search-max-queries', '10', '--search-price-per-1000', '0', '--search-budget-usd', '1'],
            env={**os.environ, 'TAVILY_API_KEY': ''}, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('TAVILY_API_KEY must be supplied', result.stderr)
        self.assertNotIn('invalid choice', result.stderr)


if __name__ == '__main__':
    unittest.main()
