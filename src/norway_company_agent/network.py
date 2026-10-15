"""Public URL preflight with an opt-in, proxied HTTPS DNS resolver.

Local DNS remains the default. SIGNALPOST_DNS_OVER_HTTPS=1 permits the documented
Google Public DNS JSON API when local resolution fails and both the source and
resolver use the inherited HTTP(S) proxy. Every A/AAAA answer must be public.
This is a DNS preflight, not connection pinning: a forward proxy resolves its
own destination, just as it did with the original local-DNS preflight.
"""
from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

DNS_JSON_ENDPOINT = "https://dns.google/resolve"
DNS_MAX_BYTES = 65_536
DNSObserver = Callable[[dict[str, Any]], None]


class DNSValidationCache:
    """Run-local successful DoH validations, bounded by DNS TTL and 60 seconds.

    No failed or local-DNS result is cached. URL syntax and current proxy policy
    are checked on every call, including hits. This stores no source content.
    """

    def __init__(self):
        self._entries: dict[str, float] = {}
        self._lock = threading.Lock()

    def valid(self, host: str) -> bool:
        with self._lock:
            return self._entries.get(host, 0) > time.monotonic()

    def remember(self, host: str, expires: float) -> None:
        with self._lock:
            now = time.monotonic()
            self._entries = {name: expiry for name, expiry in self._entries.items() if expiry > now}
            if len(self._entries) >= 512:
                self._entries.pop(next(iter(self._entries)))
            if expires > now:
                self._entries[host] = expires


def _dns_ttl(document: dict) -> int:
    # An absent address family needs a bounded negative-cache SOA as well.
    records = document.get("Answer") or document.get("Authority") or []
    ttls = [record.get("TTL") for record in records if isinstance(record, dict)]
    if not ttls or len(ttls) != len(records) or any(type(ttl) is not int or ttl <= 0 for ttl in ttls):
        return 0
    if not document.get("Answer"):
        # RFC 2308 bounds a negative answer by the lesser of the SOA TTL and
        # SOA.MINIMUM. Non-SOA/malformed authority records cannot cache absence.
        for record in records:
            minimum = str(record.get("data", "")).split()
            if record.get("type") != 6 or not minimum or not minimum[-1].isdigit():
                return 0
            ttls.append(int(minimum[-1]))
    return min(60, *ttls)


class UnsafeURLError(ValueError):
    """A URL or resolved address violates the public-network policy."""


class ResolutionError(ValueError):
    """Public DNS validation could not be completed; never permission to fetch."""


def _public_address(value: str) -> None:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ResolutionError("DNS returned an invalid address") from exc
    if "%" in value or not ip.is_global or ip.is_multicast or ip.is_reserved:
        raise UnsafeURLError("Private, loopback, link-local, multicast, and reserved addresses are blocked")
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped or ip.sixtofour
        if embedded is not None:
            _public_address(str(embedded))
        if ip.teredo is not None:
            for address in ip.teredo:
                _public_address(str(address))
        # Well-known NAT64 addresses can encode a private IPv4 destination.
        if ip in ipaddress.IPv6Network("64:ff9b::/96"):
            _public_address(str(ipaddress.IPv4Address(int(ip) & 0xffffffff)))


def _dns_name(host: str) -> str:
    try:
        name = host.removesuffix(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UnsafeURLError("Invalid public hostname") from exc
    if name == "localhost" or name.endswith((".localhost", ".local")):
        raise UnsafeURLError("Local hosts are blocked")
    labels = name.split(".")
    if (len(name) > 253 or len(labels) < 2 or labels[-1].isdigit()
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)):
        raise UnsafeURLError("Only fully qualified public hostnames are allowed")
    return name


def _proxy_used(scheme: str, host: str) -> bool:
    proxy = urllib.request.getproxies().get(scheme)
    if not proxy or urllib.request.proxy_bypass(host):
        return False
    try:
        parsed = urllib.parse.urlsplit(proxy)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


class _NoDNSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ResolutionError("HTTPS DNS resolver redirects are prohibited")


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ResolutionError("Hostname did not resolve within the DNS validation budget")
    return remaining


def _dns_query(host: str, kind: int, deadline: float, observer: DNSObserver | None) -> dict:
    url = DNS_JSON_ENDPOINT + "?" + urllib.parse.urlencode({"name": host, "type": kind})
    _remaining(deadline)
    if observer:
        observer({"url": url, "kind": "dns_validation", "state": "started"})
    started = time.monotonic()
    event: dict[str, Any] = {"url": url, "kind": "dns_validation", "state": "error", "bytes": 0}
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": "SignalpostResearch/0.2"})
        # Default ProxyHandler and HTTPSHandler preserve inherited proxy/CA trust.
        # Resolver redirects never reach another endpoint or a private address.
        opener = urllib.request.build_opener(_NoDNSRedirects())
        with opener.open(request, timeout=_remaining(deadline)) as response:
            event["status"] = response.status
            if response.status != 200:
                raise ResolutionError("HTTPS DNS resolver did not return HTTP 200")
            raw = response.read(DNS_MAX_BYTES + 1)
            event["bytes"] = len(raw)
        _remaining(deadline)
        if len(raw) > DNS_MAX_BYTES:
            raise ResolutionError("HTTPS DNS response exceeds the byte budget")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ResolutionError("Invalid HTTPS DNS response")
        event["state"] = "returned"
        return result
    except (OSError, ValueError, urllib.error.URLError) as exc:
        event["error"] = type(exc).__name__
        if isinstance(exc, ResolutionError):
            raise
        # Do not expose proxy credentials from exception text.
        raise ResolutionError("Hostname did not resolve: HTTPS DNS request failed (" + type(exc).__name__ + ")") from exc
    finally:
        if observer:
            observer({**event, "latency_ms": int((time.monotonic() - started) * 1000)})


def _dns_addresses(document: dict, host: str, kind: int) -> set[str]:
    if type(document.get("Status")) is not int or document["Status"] != 0 or document.get("TC") is not False:
        raise ResolutionError("HTTPS DNS response is unsuccessful or truncated")
    questions = document.get("Question")
    if (not isinstance(questions, list) or len(questions) != 1 or not isinstance(questions[0], dict)
            or type(questions[0].get("type")) is not int or questions[0]["type"] != kind
            or not isinstance(questions[0].get("name"), str)
            or questions[0]["name"].lower().removesuffix(".") != host):
        raise ResolutionError("HTTPS DNS question does not match the requested hostname/type")
    answers = document.get("Answer", [])
    if not isinstance(answers, list):
        raise ResolutionError("Invalid HTTPS DNS answers")
    aliases: dict[str, str] = {}
    addresses: list[tuple[str, str]] = []
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("name"), str) or type(answer.get("type")) is not int or not isinstance(answer.get("data"), str):
            raise ResolutionError("Invalid HTTPS DNS answer record")
        name = _dns_name(answer["name"])
        if answer["type"] == 5:
            alias = _dns_name(answer["data"])
            if name in aliases and aliases[name] != alias:
                raise ResolutionError("Conflicting HTTPS DNS aliases")
            aliases[name] = alias
        elif answer["type"] in {1, 28}:
            data = answer["data"]
            _public_address(data)
            if ipaddress.ip_address(data).version != (4 if answer["type"] == 1 else 6):
                raise ResolutionError("HTTPS DNS address family mismatch")
            if answer["type"] != kind:
                raise ResolutionError("HTTPS DNS answer type mismatch")
            addresses.append((name, data))
        else:
            raise ResolutionError("Unexpected HTTPS DNS answer type")
    chain = {host}
    current = host
    while current in aliases:
        current = aliases[current]
        if current in chain or len(chain) >= 16:
            raise ResolutionError("HTTPS DNS alias loop or excessive depth")
        chain.add(current)
    if any(name not in chain for name, _ in addresses) or any(name not in chain for name in aliases):
        raise ResolutionError("HTTPS DNS answer belongs to an unrelated hostname")
    return {address for _, address in addresses}


def assert_public_url(url: str, *, timeout: float = 8, dns_observer: DNSObserver | None = None,
                      dns_cache: DNSValidationCache | None = None) -> None:
    """Reject unsafe URLs; resolve locally or explicitly opt into proxied HTTPS DNS.

    Fallback applies only to local resolver errors, never to an unsafe/empty DNS
    answer. A and AAAA must both validate, with at least one public address in
    total. NO_PROXY, missing proxies and resolver failure all fail closed.
    """
    if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url) or "\\" in url:
        raise UnsafeURLError("Malformed public HTTP(S) URL")
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError("Malformed public HTTP(S) URL") from exc
    if parsed.scheme not in {"http", "https"} or not host:
        raise UnsafeURLError("Only public HTTP(S) URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("Credentials in source URLs are prohibited")
    if port is not None and port == 0:
        raise UnsafeURLError("Invalid source URL port")
    if "%" in host:
        raise UnsafeURLError("Encoded or scoped host addresses are blocked")
    try:
        ipaddress.ip_address(host.removesuffix("."))
    except ValueError:
        host = _dns_name(host)
    else:
        _public_address(host.removesuffix("."))
        return
    if not math.isfinite(timeout) or timeout <= 0:
        raise ResolutionError("Invalid DNS validation budget")
    started = time.monotonic()
    deadline = started + timeout
    fallback_allowed = (os.environ.get("SIGNALPOST_DNS_OVER_HTTPS") == "1"
                        and _proxy_used(parsed.scheme, parsed.netloc) and _proxy_used("https", "dns.google"))
    if dns_cache is not None and fallback_allowed and dns_cache.valid(host):
        return
    ttl = 0
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        if os.environ.get("SIGNALPOST_DNS_OVER_HTTPS") != "1":
            raise ResolutionError("Hostname did not resolve; HTTPS DNS fallback is not enabled") from exc
        if not _proxy_used(parsed.scheme, parsed.netloc) or not _proxy_used("https", "dns.google"):
            raise ResolutionError("Hostname did not resolve; HTTPS DNS requires the inherited proxy for source and resolver") from exc
        addresses = set()
        ttls = []
        for kind in (1, 28):
            document = _dns_query(host, kind, deadline, dns_observer)
            addresses.update(_dns_addresses(document, host, kind))
            ttls.append(_dns_ttl(document))
        ttl = min(ttls)
    except OSError as exc:
        raise ResolutionError("Hostname did not resolve: local resolver unavailable") from exc
    if not addresses:
        raise ResolutionError("Hostname did not resolve to any addresses")
    for address in addresses:
        _public_address(address)
    if dns_cache is not None and ttl:
        dns_cache.remember(host, started + ttl)
