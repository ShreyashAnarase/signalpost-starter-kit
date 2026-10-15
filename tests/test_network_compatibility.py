"""Offline URL/DNS/proxy regressions; no real DNS, sockets, or source requests."""
from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import ssl
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import network
from norway_company_agent.acquisition import AcquisitionError, ResearchSession, SnapshotStore
from norway_company_agent.website import SafeRedirectHandler, assert_public_url

PUBLIC_V4 = "8.8.8.8"
PUBLIC_V6 = "2001:4860:4860::8888"


def local_answers(*addresses):
    return [(socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses]


def dns_answer(host="company.example", kind=1, addresses=None):
    if addresses is None:
        addresses = [PUBLIC_V4] if kind == 1 else [PUBLIC_V6]
    return {"Status": 0, "TC": False, "Question": [{"name": host + ".", "type": kind}],
            "Answer": [{"name": host + ".", "type": kind, "data": ip} for ip in addresses]}


class Response(io.BytesIO):
    def __init__(self, body=b"page", *, url="https://company.example/", code=200, content_type="text/html"):
        super().__init__(body)
        self.url, self.code, self.status = url, code, code
        self.headers = {"Content-Type": content_type}

    def geturl(self):
        return self.url


class NetworkFixture(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "1"}))
        self.proxy = self.stack.enter_context(patch("urllib.request.getproxies", return_value={"http": "http://proxy:8080", "https": "http://proxy:8080"}))
        self.bypass = self.stack.enter_context(patch("urllib.request.proxy_bypass", return_value=False))
        self.dns = self.stack.enter_context(patch("socket.getaddrinfo", side_effect=socket.gaierror(socket.EAI_AGAIN, "DNS unavailable")))
        # A transport tripwire protects every test from accidental live HTTP.
        self.openers = self.stack.enter_context(patch("urllib.request.build_opener", side_effect=AssertionError("Unexpected HTTP transport")))

    def resolver(self, documents=None, error=None):
        if documents is None:
            documents = [dns_answer(), dns_answer(kind=28)]
        opener = Mock()
        if error:
            opener.open.side_effect = error
        else:
            opener.open.side_effect = [Response(json.dumps(doc).encode(), url=network.DNS_JSON_ENDPOINT, content_type="application/json") for doc in documents]
        self.openers.side_effect = None
        self.openers.return_value = opener
        return opener


class NetworkTests(NetworkFixture):
    def test_local_public_dns_remains_default_and_does_not_contact_resolver(self):
        self.dns.side_effect = None
        self.dns.return_value = local_answers(PUBLIC_V4, PUBLIC_V6)
        with patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "0"}):
            assert_public_url("https://Company.Example./")
        self.dns.assert_called_once_with("company.example", 443, type=socket.SOCK_STREAM)
        self.openers.assert_not_called()

    def test_fallback_is_opt_in_and_fails_closed_by_default(self):
        with patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "0"}):
            with self.assertRaisesRegex(network.ResolutionError, "not enabled"):
                assert_public_url("https://company.example/")
        self.openers.assert_not_called()

    def test_proxied_resolver_validates_both_families_after_dns_failure(self):
        opener = self.resolver()
        assert_public_url("https://company.example/", timeout=3)
        self.assertEqual(opener.open.call_count, 2)
        requests = [call.args[0] for call in opener.open.call_args_list]
        self.assertEqual([r.full_url for r in requests], [
            "https://dns.google/resolve?name=company.example&type=1",
            "https://dns.google/resolve?name=company.example&type=28"])
        self.assertTrue(all(0 < call.kwargs["timeout"] <= 3 for call in opener.open.call_args_list))
        self.assertTrue(all(isinstance(call.args[0], network._NoDNSRedirects) for call in self.openers.call_args_list))

    def test_one_absent_family_is_allowed_but_both_must_be_queried(self):
        opener = self.resolver([dns_answer(), dns_answer(kind=28, addresses=[])])
        assert_public_url("https://company.example/")
        self.assertEqual(opener.open.call_count, 2)

    def test_no_dns_addresses_are_rejected(self):
        self.resolver([dns_answer(addresses=[]), dns_answer(kind=28, addresses=[])])
        with self.assertRaisesRegex(network.ResolutionError, "any addresses"):
            assert_public_url("https://company.example/")

    def test_public_ip_literals_need_no_dns_or_fallback(self):
        for url in ["https://8.8.8.8/", "https://[2001:4860:4860::8888]/"]:
            assert_public_url(url)
        self.dns.assert_not_called()
        self.openers.assert_not_called()

    def test_unsafe_literals_and_ambiguous_urls_never_reach_dns_or_http(self):
        urls = [
            "http://127.0.0.1/", "http://10.1.2.3/", "http://172.16.1.1/", "http://192.168.1.1/",
            "http://169.254.169.254/", "http://0.0.0.0/", "http://100.64.0.1/", "http://224.0.0.1/",
            "http://192.0.2.1/", "http://[::1]/", "http://[fe80::1]/", "http://[fd00::1]/", "http://[ff02::1]/",
            "http://[::ffff:127.0.0.1]/", "http://[2002:7f00:1::1]/", "http://[64:ff9b::7f00:1]/",
            "http://localhost/", "http://x.localhost/", "http://company.local/", "http://internal/",
            "http://2130706433/", "http://0177.0.0.1/", "http://0x7f000001/", "http://127.1/",
            "http://%31%32%37.0.0.1/", "http://[fe80::1%25eth0]/", "file:///etc/passwd", "ftp://company.example/",
            "http://user:pass@company.example/", "http://@company.example/", "http://company.example:0/",
            "http://company.example:65536/", "http://company.example:bad/", "http://[broken]/",
            "http://company.example\\@127.0.0.1/", "http://company.example/\r\nHost:x", "http://company.example /",
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(network.UnsafeURLError):
                assert_public_url(url)
        self.dns.assert_not_called()
        self.openers.assert_not_called()

    def test_mixed_local_public_private_dns_never_falls_back(self):
        self.dns.side_effect = None
        for private in ["127.0.0.1", "10.0.0.1", "169.254.1.1", "::1", "fd00::1", "224.0.0.1"]:
            self.dns.return_value = local_answers(PUBLIC_V4, private)
            with self.subTest(private=private), self.assertRaises(network.UnsafeURLError):
                assert_public_url("https://company.example/")
        self.openers.assert_not_called()

    def test_empty_or_invalid_local_answers_fail_closed_without_fallback(self):
        self.dns.side_effect = None
        for addresses in [[], ["invalid"]]:
            self.dns.return_value = local_answers(*addresses)
            with self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/")
        self.openers.assert_not_called()

    def test_local_permission_error_does_not_trigger_fallback(self):
        self.dns.side_effect = OSError(1, "Operation not permitted")
        with self.assertRaises(network.ResolutionError):
            assert_public_url("https://company.example/")
        self.openers.assert_not_called()

    def test_private_ipv4_or_ipv6_in_https_dns_is_rejected(self):
        for private in ["127.0.0.1", "10.0.0.1", "169.254.169.254", "100.64.0.1", "224.0.0.1", "::1", "fd00::1", "fe80::1", "ff02::1"]:
            kind = 28 if ":" in private else 1
            documents = ([dns_answer(), dns_answer(kind=28, addresses=[PUBLIC_V6, private])] if kind == 28
                         else [dns_answer(addresses=[PUBLIC_V4, private])])
            self.resolver(documents)
            with self.subTest(private=private), self.assertRaises(network.UnsafeURLError):
                assert_public_url("https://company.example/")

    def test_unsuccessful_or_truncated_dns_never_establishes_permission(self):
        for changes in [{"Status": 2}, {"Status": 3}, {"Status": True}, {"TC": True}, {"TC": None}, {"Answer": {}}, {"Question": []}, {"Question": [{"name": None, "type": 1}]}]:
            bad = {**dns_answer(), **changes}
            self.resolver([bad])
            with self.subTest(changes=changes), self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/")

    def test_dns_question_and_answer_must_match_host_and_type(self):
        mutations = [
            lambda d: d["Question"][0].update(name="other.example."),
            lambda d: d["Question"][0].update(type=28),
            lambda d: d["Question"][0].update(type=True),
            lambda d: d["Answer"][0].update(name="other.example."),
            lambda d: d["Answer"][0].update(type=28, data=PUBLIC_V6),
            lambda d: d["Answer"][0].update(data=PUBLIC_V6),
            lambda d: d["Answer"][0].update(data="invalid"),
            lambda d: d["Answer"][0].update(type=16),
            lambda d: d["Answer"].append("bad"),
        ]
        for mutate in mutations:
            doc = dns_answer()
            mutate(doc)
            self.resolver([doc])
            with self.subTest(doc=doc), self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/")

    def test_cname_answers_are_validated_and_not_used_as_address_substitutes(self):
        cname = {"name": "company.example.", "type": 5, "data": "cdn.example."}
        doc = dns_answer()
        doc["Answer"][0]["name"] = "cdn.example."
        doc["Answer"].insert(0, cname)
        self.resolver([doc, dns_answer(kind=28, addresses=[])])
        assert_public_url("https://company.example/")
        for bad in [
            {**dns_answer(), "Answer": [cname, {"name": "cdn.example.", "type": 5, "data": "company.example."}]},
            {**dns_answer(), "Answer": [dict(cname, data="localhost.")]},
            {**dns_answer(), "Answer": [cname]},
        ]:
            self.resolver([bad, dns_answer(kind=28, addresses=[])])
            with self.assertRaises(ValueError):
                assert_public_url("https://company.example/")

    def test_unavailable_aaaa_query_rejects_even_with_public_a(self):
        opener = self.resolver()
        opener.open.side_effect = [Response(json.dumps(dns_answer()).encode()), urllib.error.URLError("resolver unavailable")]
        with self.assertRaises(network.ResolutionError):
            assert_public_url("https://company.example/")

    def test_proxy_denial_and_tls_errors_do_not_allow_source_transport(self):
        for error in [urllib.error.URLError("Tunnel connection failed: 403 Forbidden"),
                      urllib.error.URLError(ssl.SSLCertVerificationError("bad cert")),
                      urllib.error.HTTPError(network.DNS_JSON_ENDPOINT, 403, "Forbidden", {}, None)]:
            self.resolver(error=error)
            with self.subTest(error=type(error).__name__), self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/")

    def test_resolver_malformed_oversized_and_non_200_responses_fail_closed(self):
        for response in [Response(b"not json"), Response(b"[]"), Response(b"x" * (network.DNS_MAX_BYTES + 1)), Response(code=302), Response(code=403)]:
            opener = self.resolver()
            opener.open.side_effect = [response]
            with self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/")

    def test_proxy_required_for_source_and_resolver_including_no_proxy(self):
        for proxies, bypass in [({}, False), ({"http": "http://proxy:8080"}, False),
                                ({"https": "socks5://proxy:8080"}, False),
                                ({"https": "http://proxy:8080"}, True)]:
            self.proxy.return_value, self.bypass.return_value = proxies, bypass
            with self.assertRaisesRegex(network.ResolutionError, "inherited proxy"):
                assert_public_url("https://company.example/")
        self.openers.assert_not_called()

    def test_source_specific_no_proxy_is_respected(self):
        for bypass_host in ["company.example", "dns.google"]:
            self.bypass.side_effect = lambda host: host == bypass_host
            with self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/")
        self.openers.assert_not_called()

    def test_http_source_fallback_requires_http_proxy_too(self):
        self.proxy.return_value = {"https": "http://proxy:8080"}
        with self.assertRaises(network.ResolutionError):
            assert_public_url("http://company.example/")
        self.openers.assert_not_called()

    def test_dns_queries_share_a_single_timeout(self):
        self.resolver()
        with patch("norway_company_agent.network.time.monotonic", side_effect=[0, 0.1, 0.1, 0.2, 0.9, 1.1]):
            with self.assertRaisesRegex(network.ResolutionError, "budget"):
                assert_public_url("https://company.example/", timeout=1)

    def test_invalid_timeout_never_reaches_https_resolver(self):
        for timeout in [0, -1, float("inf"), float("nan")]:
            with self.assertRaises(network.ResolutionError):
                assert_public_url("https://company.example/", timeout=timeout)
        self.dns.assert_not_called()
        self.openers.assert_not_called()

    def test_resolver_and_legacy_redirects_reject_private_or_credential_urls(self):
        request = urllib.request.Request("https://company.example/")
        for target in ["http://127.0.0.1/", "https://user:pass@company.example/"]:
            with self.assertRaises(network.UnsafeURLError):
                SafeRedirectHandler().redirect_request(request, None, 302, "Found", {}, target)
        with self.assertRaises(network.ResolutionError):
            network._NoDNSRedirects().redirect_request(request, None, 302, "Found", {}, "https://other.example/")
        self.dns.assert_not_called()
        self.openers.assert_not_called()


class AcquisitionNetworkTests(NetworkFixture):
    def setUp(self):
        super().setUp()
        self.directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.session = ResearchSession(SnapshotStore(self.directory), timeout=3, deadline=time.monotonic() + 10, max_requests=10)
        self.stack.enter_context(patch.object(self.session, "_reserve", wraps=self.session._reserve))
        # Avoid real host pacing in offline fixtures.
        self.stack.enter_context(patch("norway_company_agent.acquisition.time.sleep"))
        self.stack.enter_context(patch("norway_company_agent.acquisition._host_next", {}))

    def local(self):
        self.dns.side_effect = None
        self.dns.return_value = local_answers(PUBLIC_V4)

    def source(self, action=None):
        opener = Mock()
        opener.open.side_effect = action or [Response()]
        self.openers.side_effect = None
        self.openers.return_value = opener
        return opener

    def test_initial_private_url_never_reaches_transport(self):
        with self.assertRaises(AcquisitionError) as caught:
            self.session.get("http://169.254.169.254/")
        self.assertEqual(caught.exception.availability, "blocked")
        self.openers.assert_not_called()
        self.assertEqual(self.session.requests, 0)

    def test_resolver_failure_is_source_error_without_acquisition(self):
        self.resolver(error=urllib.error.URLError("403 Forbidden"))
        result = self.session.fetch_json("https://company.example/")
        self.assertEqual(result.status, 0)
        self.assertEqual(self.session.captures, {})
        self.assertEqual(self.session.requests, 1)
        self.assertEqual(self.session.attempts[0]["kind"], "dns_validation")
        self.assertEqual(self.session.attempts[0]["state"], "error")

    def test_proxied_dns_queries_use_request_budget_and_telemetry(self):
        dns = self.resolver()
        source = Mock()
        source.open.return_value = Response()
        self.openers.side_effect = [dns, dns, source]
        capture = self.session.get("https://company.example/", attempts=1)
        self.assertEqual(capture.body, b"page")
        self.assertEqual(self.session.requests, 3)
        self.assertEqual([a.get("kind") for a in self.session.attempts], ["dns_validation", "dns_validation", None])
        self.assertGreater(self.session.bytes_received, len(capture.body))
        self.assertEqual(len(self.session.latencies), 3)

    def test_dns_request_budget_exhaustion_never_reaches_source(self):
        dns = self.resolver()
        self.session.max_requests = 1
        with self.assertRaisesRegex(AcquisitionError, "request budget"):
            self.session.get("https://company.example/", attempts=1)
        self.assertEqual(dns.open.call_count, 1)
        self.assertEqual(self.session.captures, {})

    def test_redirect_private_credentials_or_dns_private_answers_block_before_following(self):
        for target in ["http://127.0.0.1/", "https://@company.example/", "https://other.example/"]:
            self.local()
            self.dns.side_effect = lambda host, *a, **kw: local_answers("10.0.0.1" if host == "other.example" else PUBLIC_V4)

            def redirect(request, **kwargs):
                handler = self.openers.call_args.args[0]
                handler.redirect_request(request, None, 302, "Found", {}, target)
                self.fail("Unsafe redirect was followed")

            self.source(redirect)
            with self.subTest(target=target), self.assertRaises(AcquisitionError) as caught:
                self.session.get("https://company.example/", attempts=1)
            self.assertEqual(caught.exception.availability, "blocked")
            self.assertEqual(self.session.captures, {})

    def test_redirect_local_dns_failure_is_operational_error(self):
        self.local()
        self.dns.side_effect = lambda host, *a, **kw: (local_answers(PUBLIC_V4) if host == "company.example" else (_ for _ in ()).throw(socket.gaierror("DNS failed")))

        def redirect(request, **kwargs):
            self.openers.call_args.args[0].redirect_request(request, None, 302, "Found", {}, "https://other.example/")

        self.source(redirect)
        with patch.dict(os.environ, {"SIGNALPOST_DNS_OVER_HTTPS": "0"}):
            with self.assertRaises(AcquisitionError) as caught:
                self.session.get("https://company.example/", attempts=1)
        self.assertEqual(caught.exception.availability, "failed")

    def test_redirect_https_dns_private_answer_is_blocked_before_following(self):
        self.dns.side_effect = lambda host, *a, **kw: (local_answers(PUBLIC_V4) if host == "company.example"
                                                    else (_ for _ in ()).throw(socket.gaierror("DNS failed")))
        dns = Mock()
        dns.open.return_value = Response(json.dumps(dns_answer("other.example", addresses=["10.0.0.1"])).encode())
        source = Mock()

        def build(handler):
            if isinstance(handler, network._NoDNSRedirects):
                return dns

            def redirect(request, **kwargs):
                handler.redirect_request(request, None, 302, "Found", {}, "https://other.example/")
                self.fail("Private HTTPS DNS redirect was followed")

            source.open.side_effect = redirect
            return source

        self.openers.side_effect = build
        with self.assertRaises(AcquisitionError) as caught:
            self.session.get("https://company.example/", attempts=1)
        self.assertEqual(caught.exception.availability, "blocked")
        self.assertEqual(self.session.captures, {})
        self.assertEqual(dns.open.call_count, 1)

    def test_public_redirect_via_https_dns_keeps_robots_check_and_chain(self):
        self.dns.side_effect = lambda host, *a, **kw: (local_answers(PUBLIC_V4) if host == "company.example"
                                                    else (_ for _ in ()).throw(socket.gaierror("DNS failed")))
        dns = Mock()
        dns.open.side_effect = [Response(json.dumps(dns_answer("other.example", kind=kind)).encode()) for kind in (1, 28)]
        source = Mock()

        def build(handler):
            if isinstance(handler, network._NoDNSRedirects):
                return dns

            def redirect(request, **kwargs):
                handler.redirect_request(request, None, 302, "Found", {}, "https://other.example/page")
                return Response(url="https://other.example/page")

            source.open.side_effect = redirect
            return source

        self.openers.side_effect = build
        with patch.object(self.session, "_allowed", return_value=True) as allowed:
            capture = self.session.get("https://company.example/", robots=True, attempts=1)
        self.assertEqual([call.args[0] for call in allowed.call_args_list], ["https://company.example/", "https://other.example/page"])
        self.assertEqual(capture.redirects, ["https://other.example/page"])
        self.assertEqual(capture.body, b"page")
        self.assertEqual(dns.open.call_count, 2)
        self.assertEqual(self.session.requests, 4)

    def test_redirect_target_robots_policy_is_checked_before_following(self):
        self.local()

        def redirect(request, **kwargs):
            self.openers.call_args.args[0].redirect_request(request, None, 302, "Found", {}, "https://other.example/page")
            self.fail("Robots denied redirect was followed")

        self.source(redirect)
        with patch.object(self.session, "_allowed", side_effect=[True, False]) as allowed:
            with self.assertRaisesRegex(AcquisitionError, "disallows crawling"):
                self.session.get("https://company.example/", robots=True, attempts=1)
            self.assertEqual([c.args[0] for c in allowed.call_args_list], ["https://company.example/", "https://other.example/page"])

    def test_robots_denial_prevents_source_page_after_proxied_dns(self):
        dns = self.resolver()
        self.openers.side_effect = [dns, dns]
        with patch.object(self.session, "_allowed", return_value=False) as allowed:
            with self.assertRaisesRegex(AcquisitionError, "robots.txt"):
                self.session.get("https://company.example/", robots=True, attempts=1)
        allowed.assert_called_once_with("https://company.example/")
        self.assertEqual(self.openers.call_count, 2)

    def test_real_robots_parser_denies_disallow_and_unavailable_policy(self):
        self.local()
        for status, raw in [(200, b"User-agent: *\nDisallow: /\n"), (403, b"Forbidden"), (503, b"Unavailable")]:
            self.session.robots.clear()
            self.source([Response(raw, url="https://company.example/robots.txt", code=status, content_type="text/plain")])
            with self.subTest(status=status), self.assertRaisesRegex(AcquisitionError, "robots.txt"):
                self.session.get("https://company.example/", robots=True, attempts=1)

    def test_unexpected_response_url_is_validated_before_body_or_snapshot(self):
        self.local()
        response = Response(b"private", url="http://127.0.0.1/")
        self.source([response])
        with patch.object(response, "read", wraps=response.read) as read:
            with self.assertRaises(AcquisitionError):
                self.session.get("https://company.example/", attempts=1)
            read.assert_not_called()
        self.assertEqual(self.session.captures, {})
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_source_tls_verification_failure_remains_an_error(self):
        self.local()
        self.source([urllib.error.URLError(ssl.SSLCertVerificationError("bad certificate"))])
        with self.assertRaises(AcquisitionError) as caught:
            self.session.get("https://company.example/", attempts=1)
        self.assertTrue(caught.exception.tls_failure)
        self.assertEqual(self.session.captures, {})

    def test_default_opener_keeps_proxy_and_verified_tls_handlers(self):
        # Construct the standard opener offline; no open()/network calls.
        # Exercise the original builder saved independently of the transport mock.
        opener = ORIGINAL_BUILD_OPENER(network._NoDNSRedirects())
        proxy = next(h for h in opener.handlers if isinstance(h, urllib.request.ProxyHandler))
        self.assertEqual(proxy.proxies, self.proxy.return_value)
        tls = next(h for h in opener.handlers if isinstance(h, urllib.request.HTTPSHandler))
        self.assertEqual(tls._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(tls._context.check_hostname)


ORIGINAL_BUILD_OPENER = urllib.request.build_opener


if __name__ == "__main__":
    unittest.main()
