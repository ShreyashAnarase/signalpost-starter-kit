"""Opt-in Brave API discovery with transient results and a shared spending cap.

Search output supplies crawl candidates only. The company-owned bytes and the
existing exact-entity gate establish every published fact independently.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from decimal import Decimal
from urllib.parse import urlencode, urlsplit

from .acquisition import AcquisitionError, ResearchSession
from .discovery import BLOCKED_DISCOVERY_HOSTS, GENERIC_NAME_TOKENS, _tokens, parse_brave_web_results
from .website import _registered_domain, normalize_homepage

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
STRATEGY = "brave_transient_candidates_v1"


class SearchBudget:
    """Reserve before transport; charge failed attempts conservatively as well."""

    def __init__(self, *, max_queries: int, price_per_1000: str, budget_usd: str):
        self.max_queries = max_queries
        self.price = Decimal(str(price_per_1000)) / 1000
        self.limit = Decimal(str(budget_usd))
        if (type(max_queries) is not int or max_queries <= 0 or not self.price.is_finite()
                or not self.limit.is_finite() or self.price < 0 or self.limit < 0
                or (self.limit == 0 and self.price > 0)):
            raise ValueError("Search query and spending limits must be finite and valid")
        self.queries = 0
        self.spent = Decimal(0)
        self._lock = threading.Lock()

    def reserve(self) -> Decimal | None:
        with self._lock:
            if self.queries >= self.max_queries or self.spent + self.price > self.limit:
                return None
            self.queries += 1
            self.spent += self.price
            return self.price


def rank_candidates(profile: dict, results: list[dict]) -> list[dict]:
    """Rank conservatively, without requiring the legal name in the domain.

    A public brand can differ from its legal name. A candidate is still subject
    to independent legal-number/contact verification after its pages are read.
    """
    name_words = [token for token in _tokens(profile.get("name")) if token not in GENERIC_NAME_TOKENS]
    names = set(name_words)
    org = profile["organisation_number"]
    candidates, seen = [], set()
    for row in results[:20]:
        try:
            url = normalize_homepage(row.get("url"))
            parts = urlsplit(url or "")
            if not url or parts.username is not None or parts.password is not None or not _registered_domain(url):
                continue
        except (ValueError, UnicodeError):
            continue
        host = (parts.hostname or "").lower().removeprefix("www.")
        if any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_DISCOVERY_HOSTS):
            continue
        # Crawl the origin, not a search-indexed article/directory page.
        url = f"{parts.scheme}://{parts.netloc.lower()}/"
        title = set(_tokens(row.get("title")))
        context = title | set(_tokens(row.get("snippet")))
        exact_org = bool(re.search(r"(?<!\d)" + r"[ .-]*".join(org) + r"(?!\d)", str(row.get("snippet") or "") + " " + str(row.get("title") or "")))
        name_match = bool(names and names <= context)
        if url in seen or not (exact_org or name_match):
            continue
        seen.add(url)
        name_in_host = bool(name_words and "".join(name_words) in "".join(_tokens(host)))
        candidates.append({"url": url, "discovery_method": STRATEGY,
                           "_rank": (not name_in_host, not exact_org, not names.issubset(title), row.get("rank") or 999)})
    candidates.sort(key=lambda row: row["_rank"])
    return [{key: value for key, value in row.items() if key != "_rank"} for row in candidates[:3]]


def discover_candidates(profile: dict, session: ResearchSession, budget: SearchBudget) -> tuple[list[dict], dict]:
    diagnostic = {"provider": "brave_search_api", "strategy": STRATEGY, "role": "candidate_only",
                  "status": "failed", "raw_results_retained": False, "queries": 0,
                  "cost_basis": "conservative reservation at declared account price"}
    key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        return [], {**diagnostic, "error": "BRAVE_SEARCH_API_KEY is not configured"}
    price = budget.reserve()
    if price is None:
        return [], {**diagnostic, "error": "Declared search query/spending budget exhausted"}
    diagnostic["queries"] = 1
    diagnostic["estimated_cost_usd"] = float(price)
    session.third_party_cost_usd += float(price)
    name = " ".join(str(profile.get("name") or "").split()).replace('"', '')
    municipality = " ".join(str(profile.get("municipality") or "").split())
    query = f'"{name}" {municipality} Norway official website'
    diagnostic["query_sha256"] = hashlib.sha256(query.encode()).hexdigest()
    url = ENDPOINT + "?" + urlencode({"q": query, "country": "NO", "search_lang": "nb", "count": 10, "spellcheck": "0"})
    try:
        capture = session.get(url, max_bytes=500_000, attempts=1, retain=False, allow_redirects=False,
                              request_headers={"Accept": "application/json", "X-Subscription-Token": key})
        diagnostic.update(retrieved_at=capture.retrieved_at, http_status=capture.status)
        if capture.status != 200:
            diagnostic["status"] = "blocked" if capture.status in {401, 403, 429} else "failed"
            return [], diagnostic
        if "json" not in capture.content_type.lower():
            raise ValueError("Search response is not JSON")
        payload = json.loads(capture.body)
        if not isinstance(payload, dict) or not isinstance(payload.get("web", {}), dict):
            raise ValueError("Malformed search response")
        results = payload.get("web", {}).get("results", [])
        if not isinstance(results, list) or len(results) > 20 or any(not isinstance(row, dict) for row in results):
            raise ValueError("Invalid search result list")
        candidates = rank_candidates(profile, parse_brave_web_results(payload, query=query))
        diagnostic.update(status="available" if candidates else "not_available", candidate_count=len(candidates))
        return candidates, diagnostic
    except (AcquisitionError, ValueError, TypeError, KeyError):
        # Exception strings may include request material or credentials; retain
        # only a fixed diagnostic, never provider bodies or headers.
        return [], {**diagnostic, "error": "Search request or response validation failed"}
