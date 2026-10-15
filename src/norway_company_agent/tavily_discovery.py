"""Tavily Basic Search candidates; transient provider output, no generated answer."""
from __future__ import annotations

import hashlib
import json
import os

from .acquisition import AcquisitionError, ResearchSession
from .search_discovery import SearchBudget, rank_candidates

ENDPOINT = "https://api.tavily.com/search"
STRATEGY = "tavily_basic_transient_candidates_v2"


def discover_candidates(profile: dict, session: ResearchSession, budget: SearchBudget,
                        *, allow_keyless: bool = False) -> tuple[list[dict], dict]:
    """Keyless mode is an explicit private development experiment, not a default.

    Production requires an evaluator-provided account key. Account pricing/free
    allowance is explicit in the shared budget; Basic always costs one credit.
    """
    # An explicit anonymous experiment must never consume account credits just
    # because a key was later added to the environment.
    key = "" if allow_keyless else os.environ.get("TAVILY_API_KEY", "").strip()
    diagnostic = {"provider": "tavily_search_api", "strategy": STRATEGY, "role": "candidate_only",
                  "status": "failed", "raw_results_retained": False, "queries": 0,
                  "search_depth": "basic", "credits_per_query": 1,
                  "access_mode": "account" if key else "keyless_development_trial",
                  "cost_basis": "conservative reservation at declared account price"}
    if not key and not allow_keyless:
        return [], {**diagnostic, "error": "TAVILY_API_KEY is not configured"}
    if not key and budget.price != 0:
        return [], {**diagnostic, "error": "Keyless development must declare zero paid cost"}
    price = budget.reserve()
    if price is None:
        return [], {**diagnostic, "error": "Declared search query/spending budget exhausted"}
    diagnostic.update(queries=1, estimated_cost_usd=float(price))
    session.third_party_cost_usd += float(price)
    name = " ".join(str(profile.get("name") or "").split()).replace('"', '')
    municipality = " ".join(str(profile.get("municipality") or "").split())
    # Company names/location only: no government IDs or sensitive inputs.
    query = f'"{name}" {municipality} Norway official website'
    diagnostic["query_sha256"] = hashlib.sha256(query.encode()).hexdigest()
    body = {"query": query, "topic": "general", "country": "norway", "max_results": 10,
            "search_depth": "basic", "auto_parameters": False, "include_answer": False,
            "include_raw_content": False, "include_images": False, "include_usage": True}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "X-Client-Source": "signalpost-company-discovery"}
    if key:
        headers["Authorization"] = "Bearer " + key
    else:
        headers["X-Tavily-Access-Mode"] = "keyless"
    try:
        capture = session.get(ENDPOINT, request_body=json.dumps(body).encode(), request_headers=headers,
                              retain=False, allow_redirects=False, max_bytes=500_000, attempts=1)
        diagnostic.update(retrieved_at=capture.retrieved_at, http_status=capture.status)
        if capture.status != 200:
            diagnostic["status"] = "blocked" if capture.status in {401, 403, 429, 432, 433} else "failed"
            return [], diagnostic
        if "json" not in capture.content_type.lower():
            raise ValueError("Search response is not JSON")
        payload = json.loads(capture.body)
        if not isinstance(payload, dict):
            raise ValueError("Malformed search response")
        if payload.get("error"):
            # Recoverable keyless envelopes are quota decisions, not permission
            # to retry/change identity. Never persist the provider's message.
            return [], {**diagnostic, "status": "blocked", "error": "Provider denied the request or reached a usage limit"}
        results = payload.get("results")
        if not isinstance(results, list) or len(results) > 20 or any(not isinstance(row, dict) for row in results):
            raise ValueError("Invalid search result list")
        ranked = rank_candidates(profile, [{"url": row.get("url"), "title": row.get("title"),
                                          "snippet": row.get("content"), "rank": index + 1}
                                         for index, row in enumerate(results)])
        candidates = [{**row, "discovery_method": STRATEGY} for row in ranked]
        diagnostic.update(status="available" if candidates else "not_available", candidate_count=len(candidates))
        # Usage accounting is private run telemetry; generated answers, content,
        # provider latency and rankings are neither retained nor published.
        usage = payload.get("usage")
        if isinstance(usage, dict) and type(usage.get("credits")) in {int, float}:
            diagnostic["reported_credits"] = usage["credits"]
        return candidates, diagnostic
    except (AcquisitionError, ValueError, TypeError, KeyError):
        return [], {**diagnostic, "error": "Search request or response validation failed"}
