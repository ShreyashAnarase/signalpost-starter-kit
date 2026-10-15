#!/usr/bin/env python3
"""Development-only, single-worker acquisition with hard process supervision."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from norway_company_agent.acquisition import ResearchSession, SnapshotStore
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.evidence import evidence, utc_now
from norway_company_agent.official import BRREG_ENTITY, fetch_official_modules
from norway_company_agent.pipeline import collect_batch, failed_profile
from norway_company_agent.site_research import research_site
from norway_company_agent.submission import submission_envelope
from norway_company_agent.versioning import STRATEGY_VERSION, source_fingerprint
from run_competition_batch import coverage_report, read_jsonl, write_jsonl

DEVELOPMENT = ROOT / "data/coverage-review-v1/development.jsonl"
DEFAULT_ORGS = ["985215294", "984589344"]
LIMITS = dict(max_companies=4, workers=1, max_pages=4, request_timeout=8,
              company_timeout=40, max_requests=20, overall_timeout=180,
              wikidata_discovery=False)
MODULES = ["registry_live", "website"]


def save_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def select_development(orgs):
    if not 1 <= len(orgs) <= LIMITS["max_companies"] or len(set(orgs)) != len(orgs):
        raise ValueError("Select one to four unique development companies")
    available = {p["organisation_number"]: p for p in read_jsonl(DEVELOPMENT)}
    if any(org not in available or available[org].get("evaluation_split") != "development" for org in orgs):
        raise ValueError("Every selected company must belong to the frozen development input")
    return [copy.deepcopy(available[org]) for org in orgs]


class LoggedSession(ResearchSession):
    """Persist attempts before DNS, and captures after every operation, even failure."""
    def __init__(self, *args, telemetry_path, **kwargs):
        super().__init__(*args, **kwargs)
        self.telemetry_path = Path(telemetry_path)
        self.operations = []
        self.flush()

    def flush(self):
        captures = {c.snapshot_path + c.final_url: c for c in self.captures.values()}
        save_json(self.telemetry_path, {"operations": self.operations,
            "attempts": self.attempts, "metrics": self.metrics(),
            "captures": [c.metadata() for c in captures.values()]})

    def get(self, url, **kwargs):
        operation = {"url": url, "started_at": utc_now(), "state": "started"}
        self.operations.append(operation)
        self.flush()
        start = time.monotonic()
        try:
            capture = super().get(url, **kwargs)
            operation.update(state="returned", http_status=capture.status)
            return capture
        except Exception as exc:
            operation.update(state="error", error_type=type(exc).__name__, error=str(exc)[:300])
            raise
        finally:
            operation["runtime_ms"] = int((time.monotonic() - start) * 1000)
            self.flush()


def review_company(profile, config):
    profile = copy.deepcopy(profile)
    start = time.monotonic()
    session = LoggedSession(SnapshotStore(config["snapshot_dir"]), timeout=8,
        deadline=config["deadline"], max_requests=20,
        telemetry_path=Path(config["telemetry_dir"]) / (profile["organisation_number"] + ".json"))
    profile["evidence"], profile["errors"] = {}, []
    records, _ = fetch_official_modules(profile["organisation_number"], {"registry_live"}, session.fetch_json)
    live = records["registry_live"]
    capture = session.captures.get(live["source_url"])
    if capture:
        live.update(capture.metadata())
        live["extraction_method"] = "official_json_normalizer_v1"
        if capture.status in {401, 403, 429}:
            live["status"] = "blocked"
    identity = live.get("value") or {}
    mismatch = live["status"] == "available" and str(identity.get("organisation_number")) != profile["organisation_number"]
    if mismatch:
        live.update(status="ambiguous", value=None, note="Wrong-company public registry response quarantined")
    profile["evidence"]["registry_live"] = live
    if live["status"] == "available":
        for key in ["name", "website", "employees", "legal_form"]:
            if identity.get(key) is not None:
                profile[key] = identity[key]
    if mismatch:
        website = evidence("website", "ambiguous", "unresolved", BRREG_ENTITY.format(org=profile["organisation_number"]), note="Public identity mismatch; site acquisition skipped")
    else:
        try:
            website = research_site(profile, session, max_pages=4, wikidata_discovery=False)
        except Exception as exc:
            website = evidence("website", "source_error", "company_owned", profile.get("website"), note=f"{type(exc).__name__}: {str(exc)[:300]}")
        # Frozen candidate records do not substitute for fresh public identity evidence.
        if live["status"] != "available" and website["status"] == "available":
            website.update(status="ambiguous", value=None, note="Site captured but fresh public registry identity unavailable")
    profile["evidence"]["website"] = website
    profile["run_metrics"] = {**session.metrics(), "runtime_ms": int((time.monotonic() - start) * 1000), "telemetry_complete": True}
    profile["attempts"] = session.attempts
    profile["research_version"], profile["completed_at"] = STRATEGY_VERSION, utc_now()
    return profile


def run_review(orgs, output, *, worker=review_company, overall_timeout=180, company_timeout=40, expected_strategy=None):
    if not 0 < overall_timeout <= 180 or not 0 < company_timeout <= 40:
        raise ValueError("Budgets must be positive and cannot exceed assignment limits")
    profiles = select_development(orgs)
    if expected_strategy is not None and STRATEGY_VERSION != expected_strategy:
        raise ValueError("Wrong strategy snapshot")
    output = Path(output).resolve()
    assigned_output = (ROOT / "out/live-development-review").resolve()
    if not output.is_relative_to(assigned_output) or output == assigned_output:
        raise ValueError("Use a fresh run subdirectory of out/live-development-review")
    output.mkdir(parents=True, exist_ok=False)
    (output / "telemetry").mkdir()
    (output / "snapshots").mkdir()
    start, started = time.monotonic(), utc_now()
    deadline = start + overall_timeout
    write_jsonl(output / "inputs.jsonl", profiles)
    results, supervision = [], []
    for profile in profiles:
        # Reserve shutdown time inside each hard budget; supervisor cleanup may use 2s.
        company_deadline = min(deadline, time.monotonic() + company_timeout) - 2
        if company_deadline <= time.monotonic():
            result = failed_profile(profile, MODULES, "Overall supervised budget exhausted")
            status = {"deadline_exhausted": True, "unfinished": 1}
        else:
            config = {**LIMITS, "modules": MODULES, "deadline": company_deadline,
                      "snapshot_dir": str(output / "snapshots"), "telemetry_dir": str(output / "telemetry")}
            collected, status = collect_batch([profile], config, workers=1, worker=worker)
            result = collected[profile["organisation_number"]]
        results.append(result)
        supervision.append({"organisation_number": profile["organisation_number"], **status})
        write_jsonl(output / "profiles.jsonl", results)
    completed = utc_now()
    envelopes = [submission_envelope(p, run_id=output.name, started_at=started, completed_at=completed) for p in results]
    write_jsonl(output / "envelopes.jsonl", envelopes)
    audit = audit_envelopes(envelopes, orgs)
    save_json(output / "audit.json", audit)
    report = {"mode": "development_live_review", "strategy": STRATEGY_VERSION,
        "run_id": output.name, "started_at": started, "completed_at": completed,
        "source_sha256": source_fingerprint(ROOT),
        "development_input_sha256": hashlib.sha256(DEVELOPMENT.read_bytes()).hexdigest(),
        "limits": {**LIMITS, "overall_timeout": overall_timeout, "company_timeout": company_timeout},
        "organisation_numbers": orgs, "supervision": supervision,
        "acquisition_runtime_ms": int((time.monotonic() - start) * 1000),
        "requests": sum(p.get("run_metrics", {}).get("requests", 0) for p in results),
        "bytes": sum(p.get("run_metrics", {}).get("bytes", 0) for p in results),
        "telemetry_complete": all(p.get("run_metrics", {}).get("telemetry_complete", False) for p in results),
        "third_party_cost_usd": 0, "coverage": coverage_report(envelopes), "audit": audit,
        "comparison": "No captured same-byte baseline available; no measured improvement claimed"}
    save_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisations", nargs="+", default=DEFAULT_ORGS)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-strategy", help="Optional assertion for replaying an explicitly frozen strategy")
    args = parser.parse_args()
    report = run_review(args.organisations, args.output_dir, expected_strategy=args.expected_strategy)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["audit"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
