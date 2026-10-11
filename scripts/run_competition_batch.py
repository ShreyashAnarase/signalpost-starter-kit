#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.acquisition import SnapshotStore
from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs
from norway_company_agent.evidence import utc_now
from norway_company_agent.operations import latency_summary, peak_rss_bytes
from norway_company_agent.pipeline import DEFAULT_MODULES, collect_batch, failed_profile
from norway_company_agent.submission import merge_refresh, submission_envelope, validate_submission
from norway_company_agent.versioning import STRATEGY_VERSION, source_fingerprint


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def coverage_report(envelopes: list[dict]) -> dict:
    companies: dict[str, set] = {}
    claims: Counter = Counter()
    outcomes: dict[str, Counter] = {}
    for envelope in envelopes:
        for item in envelope["claims"]:
            field = item["field"]
            outcomes.setdefault(field, Counter())[item["availability"]] += 1
            if item["availability"] == "available" and item.get("freshness", "current") == "current":
                companies.setdefault(field, set()).add(envelope["organisation_number"])
                claims[field] += 1
    return {field: {"companies": len(companies.get(field, set())), "claims": claims[field],
                    "company_coverage": round(len(companies.get(field, set())) / len(envelopes), 4) if envelopes else 0,
                    "availability": dict(outcomes[field])}
            for field in sorted(outcomes)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-complete company research on an evaluator-supplied batch")
    parser.add_argument("--organisations", required=True)
    parser.add_argument("--bulk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profiles-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-count", type=int, help="Optional assertion; batch size comes from the input")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--resume", action="store_true", help="Resume this run and configuration; retry source failures")
    parser.add_argument("--modules", default=",".join(DEFAULT_MODULES))
    parser.add_argument("--deadline-seconds", type=float, default=900, help="Total run budget; reserves time for final output")
    parser.add_argument("--company-timeout", type=float, default=100)
    parser.add_argument("--request-timeout", type=float, default=8)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--snapshot-dir", help="Defaults to a snapshots folder beside the result file")
    parser.add_argument("--previous-output", help="Previous envelopes; preserve evidence and report changes")
    parser.add_argument("--changes-output", help="Optional flat JSONL of material changes")
    args = parser.parse_args()
    if min(args.workers, args.checkpoint_every, args.deadline_seconds, args.company_timeout, args.request_timeout, args.max_pages, args.max_requests) <= 0:
        parser.error("Worker, checkpoint, timeout, and crawl budgets must be positive")

    started_at, started = utc_now(), time.monotonic()
    inputs = read_organisation_inputs(args.organisations)
    orgs = [item["organisation_number"] for item in inputs]
    if args.expected_count is not None and len(orgs) != args.expected_count:
        parser.error(f"Expected {args.expected_count} organisations, received {len(orgs)}")
    modules = [item.strip() for item in args.modules.split(",") if item.strip()]
    unknown = set(modules) - set(DEFAULT_MODULES + ["accounting_obligation", "financial_history"])
    if unknown:
        parser.error(f"Unknown modules: {sorted(unknown)}")
    profiles, registry = profiles_from_bulk(args.bulk, orgs)
    store = SnapshotStore(args.snapshot_dir or str(Path(args.output).parent / "snapshots"))
    registry_snapshot = store.retain_file(args.bulk, registry["registry_snapshot_sha256"])
    annotations = {item["organisation_number"]: item for item in inputs}
    for profile in profiles:
        profile["evidence"]["registry"].update(registry_snapshot)
        profile.update({key: value for key, value in annotations[profile["organisation_number"]].items() if key != "organisation_number"})
    config = {"modules": modules, "snapshot_dir": str(store.directory.resolve()),
              "request_timeout": args.request_timeout, "company_timeout": args.company_timeout,
              "max_pages": args.max_pages, "max_requests": args.max_requests,
              "registry_sha256": registry["registry_snapshot_sha256"], "strategy": STRATEGY_VERSION,
              "source_sha256": source_fingerprint(ROOT),
              "input_sha256": hashlib.sha256(Path(args.organisations).read_bytes()).hexdigest()}
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    reserve = min(20, max(3, args.deadline_seconds * 0.05))
    config["deadline"] = started + max(0, args.deadline_seconds - reserve)
    state = {}
    profiles_path = Path(args.profiles_output)
    if args.resume and profiles_path.exists():
        prior = read_jsonl(profiles_path)
        if not {item["organisation_number"] for item in prior}.issubset(set(orgs)):
            parser.error("Resume checkpoint contains companies outside this input")
        for profile in prior:
            records = profile.get("evidence", {})
            if (profile.get("run_id") == args.run_id and profile.get("config_sha256") == fingerprint
                    and all(records.get(name, {}).get("status") in {"available", "not_found", "blocked", "ambiguous", "not_applicable"} for name in modules)):
                profile = copy.deepcopy(profile)
                profile["run_metrics"] = {"requests": 0, "bytes": 0, "runtime_ms": 0, "latencies_ms": [], "third_party_cost_usd": 0}
                state[profile["organisation_number"]] = profile
    resumed = len(state)
    completed_since_checkpoint = 0

    def checkpoint(profile):
        nonlocal completed_since_checkpoint
        profile["run_id"], profile["config_sha256"] = args.run_id, fingerprint
        state[profile["organisation_number"]] = profile
        completed_since_checkpoint += 1
        if completed_since_checkpoint % args.checkpoint_every == 0:
            write_jsonl(profiles_path, [state[org] for org in orgs if org in state])

    pending = [profile for profile in profiles if profile["organisation_number"] not in state]
    _, execution = collect_batch(pending, config, workers=args.workers, on_result=checkpoint)
    previous = {}
    if args.previous_output:
        previous = {item["organisation_number"]: item for item in read_jsonl(Path(args.previous_output))}
    completed_at = utc_now()
    envelopes = []
    for org in orgs:
        profile = state[org]
        try:
            envelope = submission_envelope(profile, run_id=args.run_id, started_at=started_at, completed_at=completed_at)
            envelope = merge_refresh(envelope, previous.get(org))
        except Exception as exc:
            profile = failed_profile({"organisation_number": org}, modules, f"Envelope validation failed: {type(exc).__name__}: {str(exc)[:200]}")
            state[org] = profile
            envelope = submission_envelope(profile, run_id=args.run_id, started_at=started_at, completed_at=completed_at)
        envelopes.append(envelope)
    validation = validate_submission(envelopes, orgs)
    write_jsonl(profiles_path, [state[org] for org in orgs])
    write_jsonl(Path(args.output), envelopes)
    if args.changes_output:
        write_jsonl(Path(args.changes_output), [{"organisation_number": item["organisation_number"], **change} for item in envelopes for change in item["changes"]])
    metrics = [state[org].get("run_metrics") or {} for org in orgs]
    report = {
        "run_id": args.run_id, "started_at": started_at, "completed_at": utc_now(),
        "expected_count": len(orgs), "emitted_envelopes": len(envelopes), "resumed_profiles": resumed,
        "profiles_fetched_this_run": len(pending), "modules": modules, "registry": registry,
        "operations": {"requests": sum(item.get("requests", 0) for item in metrics),
                       "bytes": sum(item.get("bytes", 0) for item in metrics),
                       "runtime_ms": int((time.monotonic() - started) * 1000),
                       "third_party_cost_usd": sum(item.get("third_party_cost_usd", 0) for item in metrics),
                       "request_latency_ms": latency_summary(value for item in metrics for value in item.get("latencies_ms", [])),
                       "company_runtime_ms": latency_summary(item.get("runtime_ms", 0) for item in metrics),
                       "parent_peak_rss_bytes": peak_rss_bytes(),
                       "telemetry_complete": not execution["unfinished"] and all(item.get("telemetry_complete", True) for item in metrics)},
        "execution": execution, "validation": validation, "coverage": coverage_report(envelopes),
        "config_sha256": fingerprint, "source_sha256": config["source_sha256"],
        "strategy": STRATEGY_VERSION, "snapshot_dir": str(store.directory.resolve()),
        "score_notice": "Coverage diagnostics only. Precision/recall require reviewed labels; only Builderr supplies an official competition score.",
        "source_policy": {"paid_apis": False, "model_calls": 0, "sources": ["official_registry", "company_owned"], "robots_obeyed": True},
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["run_id", "expected_count", "emitted_envelopes", "operations", "execution", "validation"]}, indent=2))
    raise SystemExit(0 if validation["passed"] else 1)


if __name__ == "__main__":
    main()
