"""Offline verification of retained source bytes and evidence locators."""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .sampling import iter_bulk
from .html_text import decode_html
from .submission import _pointer, snapshot_valid, validate_submission
from .website import normalize_social_url


def _clean(value: str) -> str:
    return " ".join(html.unescape(value).split())


def audit_envelopes(envelopes: list[dict], organisations: list[str]) -> dict:
    contract = validate_submission(envelopes, organisations)
    errors = []
    grouped = defaultdict(dict)
    for envelope in envelopes:
        for source in envelope["evidence"]:
            grouped[source["snapshot_path"]][source["id"]] = source
    checked = 0
    for path, entries in grouped.items():
        sources = list(entries.values())
        if not all(snapshot_valid(source) for source in sources):
            errors.append({"snapshot_path": path, "error": "Retained snapshot missing or hash mismatch"})
            continue
        raw = Path(path).read_bytes()
        json_body = None
        soup = None
        csv_rows = {}
        if any(source["source_locator"]["type"] == "csv_row" for source in sources):
            wanted = {source["source_locator"]["organisation_number"] for source in sources}
            for row in iter_bulk(path):
                if row["organisation_number"] in wanted:
                    csv_rows[row["organisation_number"]] = row["raw"]
                    if len(csv_rows) == len(wanted):
                        break
        elif any(source["source_locator"]["type"] == "json_pointer" for source in sources):
            try:
                json_body = json.loads(raw)
            except ValueError:
                pass
        else:
            soup = BeautifulSoup(decode_html(raw)[0], "lxml")
        for source in sources:
            locator = source["source_locator"]
            kind = locator["type"]
            supported = False
            try:
                if kind in {"css_text", "normalized_outbound_link", "extracted_text"}:
                    page_html = decode_html(raw, encoding=locator.get("encoding"))[0]
                    soup = BeautifulSoup(page_html, "lxml")
                if kind == "json_pointer":
                    value = _pointer(json_body, locator["pointer"])
                    supported = value == json.loads(source["claim_span"])
                elif kind == "csv_row":
                    value = csv_rows[locator["organisation_number"]][locator["column"]]
                    supported = value == json.loads(source["claim_span"])
                elif kind == "css_text" and soup:
                    value = " ".join(node.get_text(" ", strip=True) for node in soup.select(locator["selector"]))[:12000]
                    supported = _clean(source["claim_span"]) == _clean(value)
                elif kind == "normalized_outbound_link" and soup:
                    values = [str(node.get("href") or node.get("data-href") or "") for node in soup.select("[href],[data-href]")]
                    values += re.findall(r'https?://[^\s"<>]+', page_html.replace("\\/", "/"))
                    supported = any((normalize_social_url(html.unescape(value)) or {}).get("url") == locator["url"] for value in values)
                elif kind == "extracted_text" and soup:
                    fragments = [soup.get_text(" ", strip=True), page_html]
                    fragments += [str(node.get("content") or "") for node in soup.select("meta[content]")]
                    for node in soup.select('script[type="application/ld+json"]'):
                        try:
                            fragments.append(json.dumps(json.loads(node.string or node.get_text()), ensure_ascii=False))
                        except ValueError:
                            pass
                    needle = _clean(source["claim_span"])
                    supported = bool(needle and any(needle in _clean(fragment) for fragment in fragments))
            except (ValueError, KeyError, TypeError, IndexError):
                supported = False
            checked += 1
            if not supported:
                errors.append({"evidence_id": source["id"], "source_url": source["source_url"], "locator_type": kind,
                               "error": "Evidence locator does not resolve to the recorded source span"})
    return {"passed": contract["passed"] and not errors, "contract": contract,
            "envelopes": len(envelopes), "unique_snapshots": len(grouped),
            "evidence_locators_checked": checked, "errors": errors,
            "boundary": "Checks retained bytes and locators, not human exact-company precision or the official competition score."}
