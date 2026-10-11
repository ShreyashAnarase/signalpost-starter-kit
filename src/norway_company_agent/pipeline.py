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
from .official import BRREG_ENTITY, fetch_official_modules
from .site_research import research_site
from .versioning import STRATEGY_VERSION

DEFAULT_MODULES = ["registry", "registry_live", "financials", "roles", "group", "locations", "website"]


def research_company(profile: dict, config: dict) -> dict:
    profile = copy.deepcopy(profile)
    started = time.monotonic()
    session = ResearchSession(SnapshotStore(config["snapshot_dir"]), timeout=config.get("request_timeout", 8),
                              deadline=min(config["deadline"], started + config.get("company_timeout", 100)),
                              max_requests=config.get("max_requests", 40))
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
            profile["evidence"]["website"] = research_site(profile, session, max_pages=config.get("max_pages", 10))
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
        if module == "registry" and module in result["evidence"]:
            continue
        result["evidence"][module] = evidence(module, "source_error", "unresolved", BRREG_ENTITY.format(org=profile["organisation_number"]), note=reason)
    result["errors"] = [{"module": "runner", "message": reason}]
    result["run_metrics"] = {"requests": 0, "bytes": 0, "runtime_ms": 0, "third_party_cost_usd": 0,
                             "telemetry_complete": False}
    return result


def _collect(profiles: list[dict], config: dict, workers: int, output, worker: Callable) -> None:
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
    return results, {"deadline_exhausted": exhausted, "unfinished": unfinished,
                     "worker_exit_code": process.exitcode}
