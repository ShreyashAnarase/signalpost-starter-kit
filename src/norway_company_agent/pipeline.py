"""Research a company with the same bounded strategies used in official batches."""
from __future__ import annotations

import copy
import multiprocessing
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from .acquisition import ResearchSession, SnapshotStore
from .evidence import evidence, utc_now
from .network import DNSValidationCache
from .nav_jobs import collect_jobs
from .official import BRREG_ENTITY, fetch_official_modules
from .site_research import research_site
from .search_discovery import SearchBudget
from .versioning import STRATEGY_VERSION

DEFAULT_MODULES = ["registry", "registry_live", "financials", "roles", "group", "locations", "website"]


def research_company(profile: dict, config: dict) -> dict:
    profile = copy.deepcopy(profile)
    started = time.monotonic()
    session = ResearchSession(SnapshotStore(config["snapshot_dir"]), timeout=config.get("request_timeout", 8),
                              deadline=min(config["deadline"], started + config.get("company_timeout", 100)),
                              max_requests=config.get("max_requests", 40),
                              dns_validation_cache=config.get("_dns_validation_cache"))
    profile.setdefault("evidence", {})
    profile["errors"] = []
    requested = set(config.get("modules", DEFAULT_MODULES))
    # Official identity first: do not research a wrong response, even if a source
    # or proxy accidentally returns another organisation's otherwise valid JSON.
    modules = {}
    for module in ["registry_live", "financials", "roles", "group", "locations", "financial_history"]:
        if module not in requested:
            continue
        try:
            records, _ = fetch_official_modules(profile["organisation_number"], {module}, fetcher=session.fetch_json)
            modules.update(records)
        except Exception as exc:
            modules[module] = evidence(module, "source_error", "official_registry", BRREG_ENTITY.format(org=profile["organisation_number"]), note=f"{type(exc).__name__}: {str(exc)[:200]}")
    for name, record in modules.items():
        capture = session.captures.get(record["source_url"])
        if capture:
            record.update(capture.metadata())
            if capture.status in {401, 403, 429}:
                record["status"] = "blocked"
            elif record["status"] == "available":
                record["extraction_method"] = "official_json_normalizer_v1"
        profile["evidence"][name] = record
    live = profile["evidence"].get("registry_live", {})
    if live.get("status") == "available":
        identity = live.get("value") or {}
        if str(identity.get("organisation_number")) != profile["organisation_number"]:
            for name, record in modules.items():
                profile["evidence"][name] = {**record, "status": "ambiguous", "value": None, "note": "Live registry response organisation number mismatches requested company"}
            profile["errors"].append({"module": "registry_live", "message": "Wrong-company registry response quarantined"})
        else:
            for key in ["name", "website", "employees", "legal_form", "bankrupt", "liquidating", "latest_submitted_accounts"]:
                if identity.get(key) is not None:
                    profile[key] = identity[key]
    if "website" in requested:
        try:
            profile["evidence"]["website"] = research_site(profile, session, max_pages=config.get("max_pages", 10),
                                                          wikidata_discovery=config.get("wikidata_discovery", False),
                                                          search_budget=config.get("_search_budget"),
                                                          search_provider=config.get("search_provider") or "brave")
        except Exception as exc:
            profile["evidence"]["website"] = evidence("website", "source_error", "company_owned", profile.get("website") or BRREG_ENTITY.format(org=profile["organisation_number"]), note=f"{type(exc).__name__}: {str(exc)[:200]}")
    for module in requested:
        if module not in profile["evidence"]:
            profile["evidence"][module] = evidence(module, "source_error", "unresolved", BRREG_ENTITY.format(org=profile["organisation_number"]), note="Module did not complete")
    profile["run_metrics"] = {**session.metrics(), "runtime_ms": int((time.monotonic() - started) * 1000)}
    profile["attempts"] = session.attempts
    profile["research_version"] = STRATEGY_VERSION
    profile["completed_at"] = utc_now()
    return profile


def failed_profile(profile: dict, modules: list[str], reason: str) -> dict:
    result = copy.deepcopy(profile)
    result.setdefault("evidence", {})
    for module in modules:
        if module in {"registry", "nav_jobs"} and module in result["evidence"]:
            continue
        result["evidence"][module] = evidence(module, "source_error", "unresolved", BRREG_ENTITY.format(org=profile["organisation_number"]), note=reason)
    result["errors"] = [{"module": "runner", "message": reason}]
    result["run_metrics"] = {"requests": 0, "bytes": 0, "runtime_ms": 0, "third_party_cost_usd": 0,
                             "telemetry_complete": False}
    return result


def _collect(profiles: list[dict], config: dict, workers: int, output, worker: Callable) -> None:
    config = {**config, "_dns_validation_cache": DNSValidationCache()}
    if config.get("nav_jobs"):
        session = ResearchSession(SnapshotStore(config["snapshot_dir"]),
            timeout=config.get("request_timeout", 8),
            deadline=min(config["deadline"], time.monotonic() + config["nav_timeout"]),
            max_requests=config["nav_max_requests"], dns_validation_cache=config["_dns_validation_cache"])
        try:
            records, report = collect_jobs(profiles, session, max_pages=config["nav_max_pages"],
                max_details=config["nav_max_details"], lookback_days=config["nav_lookback_days"],
                prior_job_ids=config.get("nav_prior_job_ids", []),
                cache_input=config.get("nav_cache_input"), cache_output=config.get("nav_cache_output"),
                expected_cache_sha256=config.get("nav_cache_sha256"))
        except Exception as exc:
            records = {p["organisation_number"]: evidence("nav_jobs", "source_error", "official_job_feed",
                       "https://pam-stilling-feed.nav.no/api/v1/feed", note="Shared NAV acquisition failed") for p in profiles}
            report = {"scan_complete": False, "errors": [type(exc).__name__], "metrics": session.metrics()}
        output.put({"_batch_source": "nav_jobs", "records": records, "report": report})
        for profile in profiles:
            profile.setdefault("evidence", {})["nav_jobs"] = records[profile["organisation_number"]]
    if config.get("search_provider") in {"brave", "tavily"}:
        config["_search_budget"] = SearchBudget(max_queries=config["search_max_queries"],
            price_per_1000=config["search_price_per_1000"], budget_usd=config["search_budget_usd"])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, profile, config): profile for profile in profiles}
        for future in as_completed(futures):
            profile = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = failed_profile(profile, config["modules"], f"{type(exc).__name__}: {str(exc)[:200]}")
            output.put(result)


def collect_batch(profiles: list[dict], config: dict, *, workers: int = 8,
                  on_result: Callable[[dict], None] | None = None,
                  worker: Callable = research_company) -> tuple[dict[str, dict], dict]:
    """Supervise worker threads in a killable process, including stuck DNS/read calls.

    The parent retains input membership and finalizes every outstanding company
    after a hard deadline; Python's thread-pool shutdown cannot extend that deadline.
    """
    if not profiles:
        return {}, {"deadline_exhausted": False, "unfinished": 0}
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    process = context.Process(target=_collect, args=(profiles, config, workers, output, worker))
    process.start()
    results = {}
    shared_sources, shared_records = {}, {}
    exhausted = False
    while len(results) < len(profiles):
        remaining = config["deadline"] - time.monotonic()
        if remaining <= 0:
            exhausted = True
            break
        try:
            result = output.get(timeout=min(0.2, remaining))
        except queue.Empty:
            if not process.is_alive():
                break
            continue
        if result.get("_batch_source") == "nav_jobs":
            shared_sources["nav_jobs"] = result["report"]
            shared_records = result["records"]
            continue
        results[result["organisation_number"]] = result
        if on_result:
            on_result(result)
    if process.is_alive():
        process.join(timeout=min(3, max(0, config["deadline"] - time.monotonic())))
    if process.is_alive():
        process.terminate()
        process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join(timeout=1)
    unfinished = len(profiles) - len(results)
    for profile in profiles:
        org = profile["organisation_number"]
        if org not in results:
            results[org] = failed_profile(profile, config["modules"], "Batch deadline exhausted" if exhausted else "Worker process exited before returning this company")
            if on_result:
                on_result(results[org])
    output.close()
    if config.get("nav_jobs"):
        shared = shared_sources.get("nav_jobs", {}).get("metrics", {})
        # Allocate shared requests/bytes once across the input order. A scan is
        # never counted independently for every company; totals remain exact.
        for index, profile in enumerate(profiles):
            result = results[profile["organisation_number"]]
            record = shared_records.get(profile["organisation_number"])
            if record:
                result.setdefault("evidence", {})["nav_jobs"] = record
            metrics = result.setdefault("run_metrics", {})
            for key in ("requests", "bytes"):
                value, remainder = divmod(shared.get(key, 0), len(profiles))
                metrics[key] = metrics.get(key, 0) + value + int(index < remainder)
            metrics.setdefault("latencies_ms", []).extend(shared.get("latencies_ms", [])[index::len(profiles)])
            if "nav_jobs" not in shared_sources:
                metrics["telemetry_complete"] = False
    return results, {"deadline_exhausted": exhausted, "unfinished": unfinished,
                     "worker_exit_code": process.exitcode, "shared_sources": shared_sources}
