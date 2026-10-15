#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.acquisition import SnapshotStore, file_sha256
from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs
from norway_company_agent.evidence import utc_now
from norway_company_agent.operations import latency_summary, peak_rss_bytes
from norway_company_agent.pipeline import DEFAULT_MODULES, collect_batch, failed_profile
from norway_company_agent.search_discovery import SearchBudget
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
    parser.add_argument("--wikidata-discovery", action="store_true",
                        help="Opt-in candidate-only Wikidata fallback; validate provider policy before live use")
    parser.add_argument("--search-provider", choices=["brave", "tavily"], help="Opt-in licensed search candidates; requires an API key and explicit cost limits")
    parser.add_argument("--search-max-queries", type=int)
    parser.add_argument("--search-price-per-1000", help="Current account price in USD per 1,000 queries; zero for an authorized free allowance")
    parser.add_argument("--search-budget-usd", help="Shared estimated spending cap; zero allowed only with an explicitly free account price")
    parser.add_argument("--max-requests", type=int, default=40)
    parser.add_argument("--nav-jobs", action="store_true", help="Optional official NAV feed; evaluator supplies NAV_API_TOKEN")
    parser.add_argument("--nav-max-pages", type=int, default=20)
    parser.add_argument("--nav-max-details", type=int, default=100)
    parser.add_argument("--nav-lookback-days", type=int, default=7)
    parser.add_argument("--nav-timeout", type=float, default=90)
    parser.add_argument("--nav-max-requests", type=int, default=500)
    parser.add_argument("--nav-cache-input", help="Declared candidate index; every job is live-verified")
    parser.add_argument("--nav-cache-output", help="New candidate index file; never overwrites an existing file")
    parser.add_argument("--snapshot-dir", help="Defaults to a snapshots folder beside the result file")
    parser.add_argument("--previous-output", help="Previous envelopes; preserve evidence and report changes")
    parser.add_argument("--changes-output", help="Optional flat JSONL of material changes")
    args = parser.parse_args()
    if (args.nav_cache_input or args.nav_cache_output) and not args.nav_jobs:
        parser.error("NAV cache options require --nav-jobs")
    if args.nav_cache_input and args.nav_cache_output and Path(args.nav_cache_input).resolve() == Path(args.nav_cache_output).resolve():
        parser.error("NAV cache input and output must be different files")
    if min(args.workers, args.checkpoint_every, args.deadline_seconds, args.company_timeout, args.request_timeout, args.max_pages, args.max_requests) <= 0:
        parser.error("Worker, checkpoint, timeout, and crawl budgets must be positive")
    if min(args.nav_max_pages, args.nav_max_details, args.nav_lookback_days, args.nav_timeout, args.nav_max_requests) <= 0:
        parser.error("NAV scan budgets must be positive")
    if any(not math.isfinite(value) for value in [args.deadline_seconds, args.company_timeout, args.request_timeout, args.nav_timeout]):
        parser.error("Timeouts must be finite")
    search_args = [args.search_max_queries, args.search_price_per_1000, args.search_budget_usd]
    if args.search_provider:
        if any(value is None for value in search_args):
            parser.error("Search requires explicit --search-max-queries, --search-price-per-1000 and --search-budget-usd")
        try:
            SearchBudget(max_queries=args.search_max_queries, price_per_1000=args.search_price_per_1000, budget_usd=args.search_budget_usd)
        except (ValueError, InvalidOperation):
            parser.error("Invalid search query limit, account price or spending cap")
        key_name = "BRAVE_SEARCH_API_KEY" if args.search_provider == "brave" else "TAVILY_API_KEY"
        if not os.environ.get(key_name, "").strip():
            parser.error(key_name + " must be supplied through the environment")
    elif any(value is not None for value in search_args):
        parser.error("Search cost options require --search-provider")

    started_at, started = utc_now(), time.monotonic()
    inputs = read_organisation_inputs(args.organisations)
    orgs = [item["organisation_number"] for item in inputs]
    if args.expected_count is not None and len(orgs) != args.expected_count:
        parser.error(f"Expected {args.expected_count} organisations, received {len(orgs)}")
    modules = [item.strip() for item in args.modules.split(",") if item.strip()]
    unknown = set(modules) - set(DEFAULT_MODULES + ["accounting_obligation", "financial_history"])
    if unknown:
        parser.error(f"Unknown modules: {sorted(unknown)}")
    if args.nav_jobs:
        modules.append("nav_jobs")
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
              "wikidata_discovery": args.wikidata_discovery,
              "search_provider": args.search_provider, "search_max_queries": args.search_max_queries,
              "search_price_per_1000": args.search_price_per_1000, "search_budget_usd": args.search_budget_usd,
              "nav_jobs": args.nav_jobs, "nav_max_pages": args.nav_max_pages,
              "nav_max_details": args.nav_max_details, "nav_lookback_days": args.nav_lookback_days,
              "nav_timeout": args.nav_timeout, "nav_max_requests": args.nav_max_requests,
              "nav_cache_input": args.nav_cache_input, "nav_cache_output": args.nav_cache_output,
              "nav_cache_sha256": file_sha256(Path(args.nav_cache_input)) if args.nav_cache_input and Path(args.nav_cache_input).is_file() else None,
              "previous_output_sha256": hashlib.sha256(Path(args.previous_output).read_bytes()).hexdigest() if args.previous_output else None,
              "registry_sha256": registry["registry_snapshot_sha256"], "strategy": STRATEGY_VERSION,
              "source_sha256": source_fingerprint(ROOT),
              "input_sha256": hashlib.sha256(Path(args.organisations).read_bytes()).hexdigest()}
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    reserve = min(20, max(3, args.deadline_seconds * 0.05))
    config["deadline"] = started + max(0, args.deadline_seconds - reserve)
    state = {}
    profiles_path = Path(args.profiles_output)
    if args.resume and profiles_path.exists() and not args.nav_jobs:
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
    previous = {}
    if args.previous_output:
        previous = {item["organisation_number"]: item for item in read_jsonl(Path(args.previous_output))}
    if args.nav_jobs:
        config["nav_prior_job_ids"] = sorted({
            claim["value"]["nav_job_id"]
            for org, row in previous.items() if org in set(orgs)
            for claim in row.get("claims", [])
            if claim.get("field") == "job_posting" and claim.get("availability") == "available"
            and isinstance(claim.get("value"), dict) and isinstance(claim["value"].get("nav_job_id"), str)})
    _, execution = collect_batch(pending, config, workers=args.workers, on_result=checkpoint)
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
        "source_policy": {"paid_apis": bool(args.search_provider and Decimal(args.search_price_per_1000) > 0), "model_calls": 0,
                          "sources": ["official_registry", "company_owned"] + (["licensed_search_candidates"] if args.search_provider else []) + (["official_job_feed"] if args.nav_jobs else []),
                          "robots_obeyed": True},
        "search_usage": {"provider": args.search_provider, "max_queries": args.search_max_queries,
                         "price_per_1000_usd": args.search_price_per_1000, "budget_usd": args.search_budget_usd,
                         "reserved_queries": sum((state[org].get("evidence", {}).get("website", {}).get("candidate_discovery") or {}).get("queries", 0) for org in orgs),
                         "cost_basis": "Conservative attempted-query estimate at declared account price; not a provider invoice",
                         "raw_results_retained": False},
        "shared_sources": execution.get("shared_sources", {}),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["run_id", "expected_count", "emitted_envelopes", "operations", "execution", "validation"]}, indent=2))
    raise SystemExit(0 if validation["passed"] else 1)


if __name__ == "__main__":
    main()
