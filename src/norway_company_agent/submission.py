"""Current competition envelope; only evidence-bearing facts are published."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .versioning import STRATEGY_VERSION

Availability = Literal["available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"]
STATES = {"available": "available", "not_found": "not_available", "not_available": "not_available",
          "blocked": "blocked", "not_applicable": "not_applicable", "ambiguous": "ambiguous",
          "not_fetched": "failed", "source_error": "failed", "failed": "failed"}


def stable_id(prefix: str, *parts: Any) -> str:
    value = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return prefix + "-" + hashlib.sha256(value.encode()).hexdigest()[:24]


class Claim(BaseModel):
    id: str
    field: str
    value: Any = None
    availability: Availability
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    reporting_period: Any = None
    account_scope: str | None = None
    effective_at: str | None = None
    relationship: str | None = None
    note: str | None = None
    freshness: Literal["current", "last_known"] = "current"

    @model_validator(mode="after")
    def supported(self):
        if self.availability == "available" and (self.value is None or not self.evidence_ids):
            raise ValueError("Available claims require a value and source evidence")
        if self.availability != "available" and self.value is not None:
            raise ValueError("Unavailable claims cannot carry an asserted value")
        return self


class SourceEvidence(BaseModel):
    id: str
    source_url: str
    source_class: str
    retrieved_at: str
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    snapshot_path: str
    claim_span: str
    source_locator: dict[str, Any]
    extraction_method: str
    reporting_period: Any = None


class Run(BaseModel):
    run_id: str
    started_at: str
    completed_at: str
    terminal_status: Literal["completed", "partial", "failed"]


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "signalpost-claims-v2"
    organisation_number: str = Field(pattern=r"^\d{9}$")
    availability: Availability
    run: Run
    legal_identity: dict[str, Any]
    claims: list[Claim]
    evidence: list[SourceEvidence]
    summary: list[dict[str, Any]]
    changes: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    operations: dict[str, Any]
    refresh: dict[str, Any]

    @model_validator(mode="after")
    def references(self):
        evidence_ids = {item.id for item in self.evidence}
        claim_ids = {item.id for item in self.claims}
        if len(evidence_ids) != len(self.evidence) or len(claim_ids) != len(self.claims):
            raise ValueError("Duplicate evidence or claim IDs")
        for claim in self.claims:
            if not set(claim.evidence_ids).issubset(evidence_ids):
                raise ValueError("Dangling claim evidence reference")
        for sentence in self.summary:
            if not sentence.get("claim_ids") or not set(sentence["claim_ids"]).issubset(claim_ids):
                raise ValueError("Summary sentence lacks valid claim references")
        for change in self.changes:
            if change.get("claim_id") not in claim_ids or not set(change.get("old_evidence_ids", []) + change.get("new_evidence_ids", [])).issubset(evidence_ids):
                raise ValueError("Change has dangling claim or evidence references")
        return self


def _pointer(body: Any, pointer: str) -> Any:
    result = body
    if not pointer:
        return result
    for key in pointer.lstrip("/").split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        result = result[int(key)] if isinstance(result, list) else result[key]
    return result


def _source_body(record: dict) -> Any:
    path = record.get("snapshot_path")
    if path and str(path).endswith(".bin"):
        try:
            return json.loads(Path(path).read_bytes())
        except (OSError, ValueError):
            pass
    return record.get("value")


@lru_cache(maxsize=8192)
def _checked_digest(path: str, size: int, modified: int) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def snapshot_valid(record: dict) -> bool:
    try:
        path = str(record["snapshot_path"])
        stat = Path(path).stat()
        return _checked_digest(path, stat.st_size, stat.st_mtime_ns) == record["content_sha256"]
    except (OSError, KeyError):
        return False


def compile_claims(profile: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    org = profile["organisation_number"]
    records = profile.get("evidence", {})
    claims: list[dict] = []
    sources: dict[str, dict] = {}

    def emit(field: str, value: Any, record: dict, *, pointer: str = "", key: Any = None,
             period: Any = None, effective_at: str | None = None, site_fact: dict | None = None,
             account_scope: str | None = None):
        availability = STATES.get(record.get("status"), "failed")
        note = record.get("note")
        if availability == "available" and value in (None, ""):
            availability = "not_available"
            note = "Field is absent from the checked source"
        ids = []
        metadata = site_fact or record
        if availability == "available":
            if not all(metadata.get(name) for name in ("source_url", "retrieved_at", "content_sha256", "snapshot_path")) or not snapshot_valid(metadata):
                availability, note = "failed", "Retained source snapshot or provenance is missing"
            else:
                if site_fact:
                    span = site_fact["claim_span"]
                    locator = site_fact.get("source_locator") or {"type": "extracted_text", "text": span}
                else:
                    body = _source_body(record)
                    try:
                        span_value = _pointer(body, pointer)
                    except (KeyError, IndexError, TypeError, ValueError):
                        availability, note = "failed", "Source field could not be located in the retained snapshot"
                        span_value = None
                    span = json.dumps(span_value, ensure_ascii=False, separators=(",", ":"))
                    locator = {"type": "json_pointer", "pointer": pointer}
                    if record.get("source_row_key"):
                        locator = {"type": "csv_row", "organisation_number": org, "column": pointer.lstrip("/")}
                if availability == "available":
                    source_id = stable_id("ev", metadata["source_url"], metadata["content_sha256"], locator)
                    sources[source_id] = {
                        "id": source_id, "source_url": metadata["source_url"],
                        "source_class": "company_owned" if site_fact else record.get("source_class", "official_registry"),
                        "retrieved_at": metadata["retrieved_at"], "content_sha256": metadata["content_sha256"],
                        "snapshot_path": metadata["snapshot_path"], "claim_span": span,
                        "source_locator": locator,
                        "extraction_method": site_fact.get("extraction_method", "company_site_dom") if site_fact else "official_json_or_csv_field",
                        "reporting_period": period,
                    }
                    ids = [source_id]
        claims.append({"id": stable_id("claim", org, field, key), "field": field,
                       "value": value if availability == "available" else None,
                       "availability": availability, "evidence_ids": ids, "confidence": None,
                       "reporting_period": period, "effective_at": effective_at,
                       "account_scope": account_scope,
                       "relationship": (site_fact or {}).get("relationship"), "note": note})

    registry = records.get("registry_live", {})
    if registry.get("status") != "available":
        registry = records.get("registry", {})
    is_bulk = bool(registry.get("source_row_key"))
    values = registry.get("value") or {}
    fields = {
        "legal_name": ("name", "navn"), "legal_form": ("legal_form", "organisasjonsform/kode"),
        "employee_count": ("employees", "antallAnsatte"), "registered_address": ("business_address", "forretningsadresse"),
        "industry": ("industry", "naeringskode1"), "contact_email": ("email", "epostadresse"),
        "contact_phone": ("phone", "telefon"), "latest_filing_year": ("latest_submitted_accounts", "sisteInnsendteAarsregnskap"),
    }
    for field, (normalized, original) in fields.items():
        if is_bulk:
            column = original.replace("/", ".")
            if field == "registered_address":
                column = "forretningsadresse.adresse"
            elif field == "industry":
                column = "naeringskode1.beskrivelse"
            value = values.get(column)
            if field == "employee_count" and value not in (None, ""):
                value = int(value) if str(value).isdigit() else None
            emit(field, value, registry, pointer="/" + column)
        else:
            if field == "contact_phone" and not (_source_body(registry) or {}).get("telefon"):
                original = "mobil"
            emit(field, values.get(normalized), registry, pointer="/" + original)

    financial = records.get("financials", {})
    accounts = (financial.get("value") or {}).get("records") or []
    finance_paths = {
        "revenue": "resultatregnskapResultat/driftsresultat/driftsinntekter/sumDriftsinntekter",
        "operating_result": "resultatregnskapResultat/driftsresultat/driftsresultat",
        "profit_before_tax": "resultatregnskapResultat/ordinaertResultatFoerSkattekostnad",
        "annual_result": "resultatregnskapResultat/aarsresultat", "assets": "eiendeler/sumEiendeler",
        "equity": "egenkapitalGjeld/egenkapital/sumEgenkapital", "debt": "egenkapitalGjeld/gjeldOversikt/sumGjeld",
    }
    for index, account in enumerate(accounts):
        period = account.get("period")
        for field, pointer in finance_paths.items():
            record = financial if period else {**financial, "status": "failed", "note": "Financial reporting period is missing"}
            emit("financials." + field, account.get(field), record, pointer=f"/{index}/{pointer}",
                 key=[period, account.get("account_type"), account.get("record_id")], period=period, account_scope=account.get("account_type"))
        emit("financials.currency", account.get("currency"), financial, pointer=f"/{index}/valuta", key=[period, account.get("account_type"), account.get("record_id")], period=period)
    if not accounts:
        emit("financials", None, financial)

    for module, collection in [("roles", "roles"), ("locations", "locations")]:
        record = records.get(module, {})
        items = (record.get("value") or {}).get(collection)
        pointer = "/rollegrupper" if module == "roles" else "/_embedded/underenheter"
        if items == []:
            pointer = ""
        emit(module, items, record, pointer=pointer)
    group = records.get("group", {})
    emit("group_relationships", group.get("value"), group)
    history = records.get("financial_history", {})
    if not history and accounts:
        periods = list({json.dumps(item.get("period"), sort_keys=True): item.get("period") for item in accounts if item.get("period")}.values())
        history = {**financial, "note": "Reporting periods observed in the accounts API; this is not a claim of complete filing history"}
        emit("financial_history", periods, history)
    else:
        emit("financial_history", (history.get("value") or {}).get("years"), history)

    website = records.get("website", {})
    facts = (website.get("value") or {}).get("facts") or []
    for fact in facts:
        key = None
        if fact["field"] in {"job_posting", "company_news"}:
            key = [fact["source_url"], fact["value"].get("title") or fact["value"].get("headline")]
        elif fact["field"] == "company_declared_profile":
            key = fact["value"]["url"]
        elif fact["field"].endswith("_page"):
            key = fact["value"]
        emit(fact["field"], fact["value"], website, site_fact=fact, key=key, effective_at=fact.get("effective_at"))
    present = {item["field"] for item in facts}
    for field in ["official_website", "business_description", "company_declared_profile", "job_posting", "company_news"]:
        if field not in present:
            record = website
            if website.get("status") == "available":
                partial = bool((website.get("value") or {}).get("crawl_errors"))
                record = {**website, "status": "source_error" if partial else "not_found",
                          "note": "Relevant pages could not all be checked" if partial else "No supported fact found in the bounded website search; not proof of absence"}
            emit(field, None, record)
    return claims, list(sources.values())


def summarize(claims: list[dict]) -> list[dict]:
    available = [claim for claim in claims if claim["availability"] == "available"]
    by_field = {claim["field"]: claim for claim in available}
    sentences = []
    for field, prefix in [("legal_name", "Registered company: "), ("business_description", "Company description: "),
                          ("employee_count", "Registered employees: ")]:
        if field in by_field:
            claim = by_field[field]
            qualifier = "Last known — " if claim.get("freshness") == "last_known" else ""
            sentences.append({"text": qualifier + prefix + str(claim["value"]), "claim_ids": [claim["id"]]})
    revenue = [claim for claim in available if claim["field"] == "financials.revenue" and claim.get("freshness", "current") == "current"]
    if revenue:
        claim = max(revenue, key=lambda item: str((item.get("reporting_period") or {}).get("tilDato", "")))
        period = claim.get("reporting_period") or {}
        currency = next((item for item in available if item["field"] == "financials.currency" and item.get("reporting_period") == period), None)
        scope = claim.get("account_scope") or "reported accounts"
        sentences.append({"text": f"Filed revenue for {period.get('fraDato', '?')}–{period.get('tilDato', '?')}: {claim['value']} {currency['value'] if currency else '(currency unavailable)'}; scope: {scope}.",
                          "claim_ids": [claim["id"]] + ([currency["id"]] if currency else [])})
    roles = by_field.get("roles")
    if roles and isinstance(roles["value"], list):
        leaders = [item for item in roles["value"] if not item.get("inactive") and item.get("role_code") in {"DAGL", "LEDE"} and item.get("name")]
        if leaders:
            qualifier = "Last known — " if roles.get("freshness") == "last_known" else ""
            sentences.append({"text": qualifier + "Registered leadership: " + "; ".join(f"{item['name']} ({item.get('role') or item['role_code']})" for item in leaders) + ".", "claim_ids": [roles["id"]]})
    for field, label in [("job_posting", "Dated job postings captured"), ("company_news", "Dated company news items captured")]:
        matches = [claim for claim in available if claim["field"] == field and claim.get("freshness", "current") == "current"]
        if matches:
            sentences.append({"text": f"{label}: {len(matches)}.", "claim_ids": [claim["id"] for claim in matches]})
    unknown = [claim for claim in claims if claim["availability"] != "available" and claim["field"] in {"official_website", "job_posting", "company_news", "financials"}]
    if unknown:
        sentences.append({"text": "Unresolved information: " + ", ".join(f"{item['field']} ({item['availability']})" for item in unknown) + ".",
                          "claim_ids": [item["id"] for item in unknown]})
    return sentences


def submission_envelope(profile: dict, *, run_id: str, started_at: str, completed_at: str,
                        changes: list[dict] | None = None, previous_run: str | None = None) -> dict:
    claims, sources = compile_claims(profile)
    available = [claim for claim in claims if claim["availability"] == "available"]
    failed = [claim for claim in claims if claim["availability"] == "failed"]
    status = "partial" if available and failed else "completed" if available else "failed"
    values = {claim["field"]: claim["value"] for claim in available}
    errors = list(profile.get("errors") or [])
    errors.extend({"field": item["field"], "availability": item["availability"], "message": item.get("note") or "Source unavailable"} for item in claims if item["availability"] in {"failed", "blocked", "ambiguous"})
    metrics = profile.get("run_metrics") or {}
    result = Envelope(
        organisation_number=profile["organisation_number"], availability="available" if available else "failed",
        run=Run(run_id=run_id, started_at=started_at, completed_at=completed_at, terminal_status=status),
        legal_identity={"organisation_number": profile["organisation_number"], "name": values.get("legal_name"), "legal_form": values.get("legal_form")},
        claims=claims, evidence=sources, summary=summarize(claims), changes=changes or [], errors=errors,
        operations={"requests": metrics.get("requests", 0), "bytes": metrics.get("bytes", 0),
                    "runtime_ms": metrics.get("runtime_ms", 0), "third_party_cost_usd": metrics.get("third_party_cost_usd", 0)},
        refresh={"previous_run_id": previous_run, "checked_at": completed_at, "strategy_version": STRATEGY_VERSION},
    )
    return result.model_dump()


def validate_submission(envelopes: list[dict], organisations: list[str]) -> dict:
    emitted = [item.get("organisation_number") for item in envelopes]
    invalid = []
    for item in envelopes:
        try:
            Envelope.model_validate(item)
        except ValueError as exc:
            invalid.append({"organisation_number": item.get("organisation_number"), "error": str(exc)[:500]})
    checks = {"exact_input_membership_and_order": emitted == organisations,
              "unique_organisation_numbers": len(emitted) == len(set(emitted)),
              "one_envelope_per_input": len(emitted) == len(organisations),
              "valid_claims_and_evidence": not invalid}
    return {"passed": all(checks.values()), "checks": checks, "invalid_envelopes": invalid}


def merge_refresh(current: dict, previous: dict | None) -> dict:
    if not previous:
        return current
    if current["organisation_number"] != previous["organisation_number"]:
        raise ValueError("Refresh requires the same organisation number")
    # Invalid history must not contaminate valid newly acquired facts. Preserve
    # the original previous artifact; refuse to reuse it and explain why.
    try:
        Envelope.model_validate(previous)
        if not all(snapshot_valid(source) for source in previous["evidence"]):
            raise ValueError("Prior retained snapshot is missing or corrupt")
    except ValueError as exc:
        current["errors"].append({"module": "refresh", "message": str(exc)[:300]})
        current["refresh"].update(previous_run_id=previous.get("run", {}).get("run_id"), previous_evidence_status="rejected")
        return Envelope.model_validate(current).model_dump()
    old_claims = {item["id"]: item for item in previous["claims"]}
    new_claims = {item["id"]: item for item in current["claims"]}
    source_map = {item["id"]: item for item in current["evidence"]}
    previous_sources = {item["id"]: item for item in previous["evidence"]}
    changes = []
    for claim_id, claim in list(new_claims.items()):
        old = old_claims.get(claim_id)
        if claim["availability"] != "available":
            if old and old["availability"] == "available":
                new_claims[claim_id] = {**old, "freshness": "last_known", "note": f"Refresh outcome: {claim['availability']}. {claim.get('note') or ''}".strip()}
                for source_id in old["evidence_ids"]:
                    source_map[source_id] = previous_sources[source_id]
            continue
        if old and old["availability"] == "available" and old["value"] == claim["value"]:
            continue
        changes.append({"id": stable_id("change", claim_id, old.get("value") if old else None, claim["value"], claim["evidence_ids"]),
                        "type": "changed" if old and old["availability"] == "available" else "newly_observed",
                        "claim_id": claim_id, "field": claim["field"],
                        "old_value": old.get("value") if old else None, "new_value": claim["value"],
                        "old_evidence_ids": old.get("evidence_ids", []) if old else [],
                        "new_evidence_ids": claim["evidence_ids"]})
        if old:
            for source_id in old.get("evidence_ids", []):
                source_map[source_id] = previous_sources[source_id]
    # A bounded crawl's omission is not evidence that a previous item was deleted.
    for claim_id, claim in old_claims.items():
        if claim_id not in new_claims and claim["availability"] == "available":
            new_claims[claim_id] = {**claim, "freshness": "last_known", "note": "Not reconfirmed by this bounded refresh"}
            for source_id in claim["evidence_ids"]:
                source_map[source_id] = previous_sources[source_id]
    current["claims"] = list(new_claims.values())
    current["evidence"] = list(source_map.values())
    current["changes"] = changes
    current["summary"] = summarize(current["claims"])
    current["refresh"]["previous_run_id"] = previous["run"]["run_id"]
    return Envelope.model_validate(current).model_dump()
