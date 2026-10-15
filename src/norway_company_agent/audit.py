"""Offline verification of retained source bytes and evidence locators."""
from __future__ import annotations

import html
import copy
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError

from .sampling import iter_bulk
from .html_text import decode_html
from .submission import _pointer, snapshot_valid, validate_submission
from .website import normalize_social_url


def _clean(value: str) -> str:
    return " ".join(html.unescape(value).split())


def resolve_snapshot_path(path: str, snapshot_root: str | Path | None = None) -> Path:
    candidate = Path(path)
    if snapshot_root is None or candidate.is_absolute():
        return candidate
    root = Path(snapshot_root).resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Relative snapshot path escapes the evidence root")
    return resolved


def audit_envelopes(envelopes: list[dict], organisations: list[str], *,
                    snapshot_root: str | Path | None = None) -> dict:
    if any(not isinstance(item, dict) for item in envelopes):
        return {"passed": False, "errors": [{"error": "Envelope must be an object"}],
                "boundary": "Checks bytes and locators, not claim truth or an official score."}
    try:
        contract = validate_submission(envelopes, organisations)
    except (TypeError, ValueError, AttributeError) as exc:
        return {"passed": False, "errors": [{"error": f"Invalid envelope contract: {exc}"}],
                "boundary": "Checks bytes and locators, not claim truth or an official score."}
    if not contract["passed"]:
        return {"passed": False, "contract": contract, "envelopes": len(envelopes),
                "unique_snapshots": 0, "evidence_locators_checked": 0,
                "errors": [{"error": "Invalid envelope contract or input membership"}],
                "boundary": "Checks retained bytes and locators, not exact-company precision or official score."}
    envelopes = copy.deepcopy(envelopes)
    try:
        for envelope in envelopes:
            for source in envelope["evidence"]:
                source["snapshot_path"] = str(resolve_snapshot_path(source["snapshot_path"], snapshot_root))
    except ValueError as exc:
        return {"passed": False, "contract": contract, "envelopes": len(envelopes),
                "unique_snapshots": 0, "evidence_locators_checked": 0,
                "errors": [{"error": str(exc)}]}
    errors = []
    grouped = defaultdict(list)
    for envelope in envelopes:
        for source in envelope["evidence"]:
            if not isinstance(source["source_locator"].get("type"), str):
                errors.append({"evidence_id": source["id"], "error": "Evidence locator needs a string type"})
                continue
            grouped[source["snapshot_path"]].append(source)
    checked = 0
    for path, sources in grouped.items():
        if not all(snapshot_valid(source) for source in sources):
            errors.append({"snapshot_path": path, "error": "Retained snapshot missing or hash mismatch"})
            continue
        raw = Path(path).read_bytes()
        json_body = None
        soup = None
        csv_rows = {}
        if any(source["source_locator"]["type"] == "csv_row" for source in sources):
            wanted = {source["source_locator"].get("organisation_number") for source in sources
                      if source["source_locator"]["type"] == "csv_row"
                      and isinstance(source["source_locator"].get("organisation_number"), str)}
            try:
                for row in iter_bulk(path):
                    if row["organisation_number"] in wanted:
                        csv_rows[row["organisation_number"]] = row["raw"]
                        if len(csv_rows) == len(wanted):
                            break
            except (OSError, ValueError):
                errors.append({"snapshot_path": path, "error": "Cannot decode retained CSV snapshot"})
        if any(source["source_locator"]["type"] == "json_pointer" for source in sources):
            try:
                json_body = json.loads(raw)
            except ValueError:
                pass
        for source in sources:
            locator = source["source_locator"]
            kind = locator["type"]
            supported = False
            try:
                if kind in {"css_text", "normalized_outbound_link", "extracted_text", "jsonld_pointer", "dom_fields"}:
                    page_html = decode_html(raw, encoding=locator.get("encoding"))[0]
                    soup = BeautifulSoup(page_html, "lxml")
                if kind == "jsonld_pointer":
                    scripts = soup.select('script[type="application/ld+json"]')
                    index = locator["script_index"]
                    if type(index) is int and index >= 0:
                        script = scripts[index]
                        value = _pointer(json.loads(script.string or script.get_text()), locator["pointer"])
                        supported = value == json.loads(source["claim_span"])
                elif kind == "dom_fields":
                    fields = locator["fields"]
                    if not isinstance(fields, dict):
                        raise ValueError("DOM fields must be a mapping")
                    actual = {}
                    for name, spec in fields.items():
                        if not isinstance(spec, dict) or not isinstance(spec.get("selector"), str):
                            raise ValueError("DOM field needs a selector")
                        nodes = soup.select(spec["selector"])
                        if len(nodes) != 1:
                            break
                        node = nodes[0]
                        value = str(node.get(spec["attribute"], "")) if spec.get("attribute") else node.get_text(" ", strip=True)
                        if value != spec["value"]:
                            break
                        actual[name] = value
                    supported = bool(fields) and len(actual) == len(fields) and actual == json.loads(source["claim_span"])
                elif kind == "json_pointer":
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
            except (ValueError, KeyError, TypeError, IndexError, SelectorSyntaxError, LookupError):
                supported = False
            checked += 1
            if not supported:
                errors.append({"evidence_id": source["id"], "source_url": source["source_url"], "locator_type": kind,
                               "error": "Evidence locator does not resolve to the recorded source span"})
    return {"passed": contract["passed"] and not errors, "contract": contract,
            "envelopes": len(envelopes), "unique_snapshots": len(grouped),
            "evidence_locators_checked": checked, "errors": errors,
            "boundary": "Checks retained bytes and locators, not human exact-company precision or the official competition score."}
