"""Opt-in exact-organisation Wikidata candidates, never publication evidence."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode

from .acquisition import AcquisitionError, ResearchSession
from .website import normalize_homepage

STRATEGY = "wikidata_exact_org_candidates_v1"
ENDPOINT = "https://query.wikidata.org/sparql"


def discover_candidates(org: str, session: ResearchSession) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostic: dict[str, Any] = {"strategy": STRATEGY, "provider": "wikidata", "role": "candidate_only",
                                  "organisation_number": org, "status": "failed", "rejections": []}
    if not isinstance(org, str) or not re.fullmatch(r"\d{9}", org):
        diagnostic["error"] = "Expected a nine-digit organisation number"
        return [], diagnostic
    query = ('SELECT ?item ?org ?website WHERE { ?item wdt:P2333 ?org; wdt:P856 ?website. '
             f'FILTER(?org = "{org}") }} ORDER BY ?item ?website LIMIT 4')
    url = ENDPOINT + "?" + urlencode({"query": query, "format": "json"})
    diagnostic["source_url"] = url
    try:
        capture = session.get(url, robots=True, max_bytes=200_000, attempts=1)
        diagnostic.update(capture.metadata())
        if capture.status != 200:
            diagnostic["status"] = "blocked" if capture.status in {401, 403, 429} else "failed"
            diagnostic["error"] = f"HTTP {capture.status}"
            return [], diagnostic
        if "json" not in capture.content_type.lower():
            raise ValueError("Provider response is not JSON")
        payload = json.loads(capture.body)
        bindings = payload["results"]["bindings"]
        if not isinstance(bindings, list) or len(bindings) > 4:
            raise ValueError("Invalid or unbounded result bindings")
        candidates, seen = [], set()
        for index, row in enumerate(bindings):
            if not isinstance(row, dict):
                raise ValueError("Malformed result binding")
            item, number, website = (row.get(key, {}) for key in ("item", "org", "website"))
            if not all(isinstance(value, dict) for value in (item, number, website)):
                raise ValueError("Malformed binding values")
            normalized = normalize_homepage(website.get("value"))
            if (number.get("type") != "literal" or number.get("value") != org
                    or item.get("type") != "uri"
                    or not re.fullmatch(r"https?://www\.wikidata\.org/entity/Q[1-9]\d*", str(item.get("value", "")))
                    or website.get("type") != "uri" or not normalized):
                diagnostic["rejections"].append({"binding_index": index, "reason": "Invalid exact-org website binding"})
                continue
            if normalized.rstrip("/") in seen:
                continue
            seen.add(normalized.rstrip("/"))
            candidates.append({"url": normalized, "discovery_method": STRATEGY,
                               "candidate_provenance": {**capture.metadata(), "provider_entity": item["value"],
                                  "organisation_number": org, "binding_index": index,
                                  "extraction_method": STRATEGY, "role": "candidate_only"}})
        diagnostic["status"] = "available" if candidates else "not_available" if not bindings else "ambiguous"
        diagnostic["candidate_limit_reached"] = len(bindings) == 4
        diagnostic["candidate_count"] = min(3, len(candidates))
        return candidates[:3], diagnostic
    except (AcquisitionError, ValueError, KeyError, TypeError) as exc:
        diagnostic["status"] = getattr(exc, "availability", "failed")
        diagnostic["error"] = str(exc)[:200]
        return [], diagnostic
