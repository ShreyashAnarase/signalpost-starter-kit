"""Bounded, auditable HTTP acquisition shared by every production connector."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .evidence import utc_now
from .http import FetchResult
from .html_text import decode_html
from .network import DNSValidationCache, ResolutionError
from .website import assert_public_url

USER_AGENT = "SignalpostResearch/0.2"
_host_lock = threading.Lock()
_host_next: dict[str, float] = {}


class AcquisitionError(Exception):
    def __init__(self, message: str, availability: str = "failed", *, tls_failure: bool = False):
        super().__init__(message)
        self.availability = availability
        self.tls_failure = tls_failure


def file_sha256(path: str | Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class SnapshotStore:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, raw: bytes) -> dict[str, str]:
        digest = hashlib.sha256(raw).hexdigest()
        target = self.directory / f"{digest}.bin"
        if not target.exists():
            temporary = target.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
            temporary.write_bytes(raw)
            temporary.replace(target)
        return {"content_sha256": digest, "snapshot_path": str(target.resolve())}

    def retain_file(self, path: str | Path, digest: str) -> dict[str, str]:
        source = Path(path).resolve()
        target = self.directory / f"{digest}{source.suffix}"
        if not target.exists():
            # A hard link would allow a later in-place registry download to
            # mutate previously retained evidence.
            temporary = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(source, temporary)
            temporary.replace(target)
        return {"content_sha256": digest, "snapshot_path": str(target.resolve())}


@dataclass
class Capture:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    retrieved_at: str
    content_sha256: str
    snapshot_path: str
    redirects: list[str] = field(default_factory=list)

    def metadata(self) -> dict[str, Any]:
        return {
            "requested_url": self.requested_url,
            "source_url": self.final_url,
            "retrieved_at": self.retrieved_at,
            "content_sha256": self.content_sha256,
            "snapshot_path": self.snapshot_path,
            "http_status": self.status,
            "redirect_chain": self.redirects,
        }


class ResearchSession:
    def __init__(self, store: SnapshotStore, *, timeout: float = 8, deadline: float | None = None,
                 max_requests: int = 40, dns_validation_cache: DNSValidationCache | None = None):
        self.store = store
        self.timeout = timeout
        self.deadline = deadline
        self.max_requests = max_requests
        self.captures: dict[str, Capture] = {}
        self.robots: dict[str, urllib.robotparser.RobotFileParser | bool] = {}
        self.requests = 0
        self.bytes_received = 0
        self.latencies: list[int] = []
        self.attempts: list[dict[str, Any]] = []
        self.third_party_cost_usd = 0.0
        self.dns_validation_cache = dns_validation_cache or DNSValidationCache()

    def remaining(self) -> float:
        remaining = self.timeout if self.deadline is None else min(self.timeout, self.deadline - time.monotonic())
        if remaining <= 0:
            raise AcquisitionError("Research budget exhausted")
        return remaining

    def _reserve(self, url: str) -> None:
        if self.requests >= self.max_requests:
            raise AcquisitionError("Research request budget exhausted")
        self.remaining()
        host = urllib.parse.urlsplit(url).hostname or ""
        # Development search keys allow 100 requests/minute. Share pacing across
        # workers and sessions, with headroom below that cap (about 92/minute).
        interval = 0.65 if host == "api.tavily.com" else 2.1 if "/aarsregnskap/kopi/" in url and url.endswith("/aar") else 0.2
        with _host_lock:
            now = time.monotonic()
            start = max(now, _host_next.get(host, now))
            _host_next[host] = start + interval
        delay = start - time.monotonic()
        if delay > 0:
            if self.deadline is not None and start >= self.deadline:
                raise AcquisitionError("Research deadline reached while waiting for host")
            time.sleep(delay)
        self.remaining()
        self.requests += 1

    def _allowed(self, url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self.robots:
            response = self.get(origin + "/robots.txt", robots=False, max_bytes=250_000, attempts=1)
            if response.status == 404:
                self.robots[origin] = True
            elif 200 <= response.status < 300:
                try:
                    text = decode_html(response.body, response.content_type)[0]
                    parser = urllib.robotparser.RobotFileParser()
                    parser.parse(text.splitlines())
                    self.robots[origin] = parser
                except ValueError:
                    self.robots[origin] = False
            else:
                self.robots[origin] = False
        policy = self.robots[origin]
        return policy if isinstance(policy, bool) else policy.can_fetch(USER_AGENT, url)

    def _dns_observer(self, event: dict[str, Any]) -> None:
        if event["state"] == "started":
            self._reserve(event["url"])
        else:
            self.bytes_received += event["bytes"]
            self.latencies.append(event["latency_ms"])
            self.attempts.append({**event, "retrieved_at": utc_now()})

    def _validate_url(self, url: str) -> None:
        try:
            assert_public_url(url, timeout=self.remaining(), dns_observer=self._dns_observer,
                              dns_cache=self.dns_validation_cache)
        except ValueError as exc:
            # An unavailable resolver is an operational error, not a site refusal.
            status = "failed" if isinstance(exc, ResolutionError) else "blocked"
            raise AcquisitionError(str(exc), status) from exc

    def get(self, url: str, *, robots: bool = False, max_bytes: int = 2_000_000,
            attempts: int = 2, request_headers: dict[str, str] | None = None,
            retain: bool = True, allow_redirects: bool = True,
            request_body: bytes | None = None) -> Capture:
        if (request_headers or request_body is not None) and (allow_redirects or urllib.parse.urlsplit(url).scheme != "https"):
            raise AcquisitionError("Authenticated API requests require HTTPS and disabled redirects", "blocked")
        self._validate_url(url)
        if robots and not self._allowed(url):
            raise AcquisitionError("robots.txt denied access or could not establish permission", "blocked")
        session = self
        redirects: list[str] = []
        validated_urls = {url}

        class RedirectHandler(urllib.request.HTTPRedirectHandler):
            max_redirections = 5

            def redirect_request(self, req, fp, code, msg, headers, newurl):
                if not allow_redirects:
                    raise AcquisitionError("Redirects are prohibited for this authenticated API request", "blocked")
                session._validate_url(newurl)
                if robots and not session._allowed(newurl):
                    raise AcquisitionError("Redirect target disallows crawling", "blocked")
                session._reserve(newurl)
                redirects.append(newurl)
                validated_urls.add(newurl)
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        opener = urllib.request.build_opener(RedirectHandler())
        logged_url = url if retain else urllib.parse.urlunsplit((*urllib.parse.urlsplit(url)[:3], "", ""))
        for attempt in range(attempts):
            self._reserve(url)
            started = time.monotonic()
            response = None
            try:
                request = urllib.request.Request(url, data=request_body, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,application/xml,text/plain,*/*", **(request_headers or {})})
                try:
                    response = opener.open(request, timeout=self.remaining())
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    if response.geturl() not in validated_urls:
                        self._validate_url(response.geturl())
                    body = response.read(max_bytes + 1)
                    self.bytes_received += len(body)
                    if len(body) > max_bytes:
                        raise AcquisitionError("Source exceeds response byte budget")
                    retained = self.store.save(body) if retain else {"content_sha256": hashlib.sha256(body).hexdigest(), "snapshot_path": ""}
                    capture = Capture(url, response.geturl(), response.code,
                                      response.headers.get("Content-Type", ""), body, utc_now(),
                                      **retained, redirects=list(redirects))
                if retain:
                    self.captures[url] = capture
                    self.captures[capture.final_url] = capture
                # Search queries/titles/snippets are transient; log only the API
                # endpoint and query hash, never the authentication headers.
                self.attempts.append({"url": logged_url, "status": capture.status, "retrieved_at": capture.retrieved_at,
                                      "content_sha256": capture.content_sha256})
                if capture.status not in {429, 500, 502, 503, 504} or attempt + 1 == attempts:
                    return capture
            except AcquisitionError:
                raise
            except (OSError, ValueError, urllib.error.URLError) as exc:
                self.attempts.append({"url": logged_url, "error": type(exc).__name__, "retrieved_at": utc_now()})
                if isinstance(exc, ssl.SSLError) or isinstance(getattr(exc, "reason", None), ssl.SSLError):
                    raise AcquisitionError(f"TLS verification/connection failed: {str(exc)[:180]}", tls_failure=True) from exc
                if attempt + 1 == attempts:
                    raise AcquisitionError(f"{type(exc).__name__}: {str(exc)[:180]}") from exc
            finally:
                self.latencies.append(int((time.monotonic() - started) * 1000))
            self.remaining()
            time.sleep(min(0.4 * (attempt + 1), self.remaining()))
        raise AcquisitionError("Source request failed")

    def fetch_json(self, url: str) -> FetchResult:
        started = time.monotonic()
        try:
            capture = self.get(url)
            body = json.loads(capture.body) if capture.status == 200 else None
            return FetchResult(url, capture.status, int((time.monotonic() - started) * 1000), len(capture.body),
                               body=body, error=None if capture.status == 200 else f"HTTP {capture.status}",
                               content_sha256=capture.content_sha256, retrieved_at=capture.retrieved_at)
        except (AcquisitionError, json.JSONDecodeError) as exc:
            return FetchResult(url, 0, int((time.monotonic() - started) * 1000), 0,
                               error=str(exc), retrieved_at=utc_now())

    def metrics(self) -> dict[str, Any]:
        return {"requests": self.requests, "bytes": self.bytes_received,
                "latencies_ms": self.latencies, "third_party_cost_usd": self.third_party_cost_usd}
