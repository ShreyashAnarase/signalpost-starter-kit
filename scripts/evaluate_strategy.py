#!/usr/bin/env python3
"""Offline diagnostics against an explicitly reviewed local opportunity pool."""
from __future__ import annotations

import argparse
import hashlib
import math
import re
from datetime import datetime
from collections import Counter
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from norway_company_agent.operations import latency_summary
from norway_company_agent.website import _registered_domain


def ratio(n, d):
    return n / d if d else None


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def domain(value):
    url = str(value or "").strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return _registered_domain(url) or host or None


def audit_split(development, holdout):
    for rows in [development, holdout]:
        membership_ids(rows)
    def known(rows):
        return {domain(url) for row in rows for url in [row.get("website"), *row.get("known_websites", [])] if domain(url)}
    def unknown(rows):
        return [str(row["organisation_number"]) for row in rows if not known([row])]
    orgs = [{str(row["organisation_number"]) for row in rows} for rows in [development, holdout]]
    domains = [known(rows) for rows in [development, holdout]]
    org_overlap = sorted(orgs[0] & orgs[1])
    host_overlap = sorted(domains[0] & domains[1])
    return {"organisation_overlap": org_overlap, "known_domain_overlap": host_overlap,
            "duplicate_organisations": {name: len(rows) - len(ids) for name, rows, ids in zip(["development", "holdout"], [development, holdout], orgs)},
            "unknown_host_organisations": {"development": unknown(development), "holdout": unknown(holdout)},
            "complete_host_separation": not unknown(development) and not unknown(holdout) and not org_overlap and not host_overlap and all(len(rows) == len(ids) for rows, ids in zip([development, holdout], orgs)),
            "known_separation_passed": not org_overlap and not host_overlap and all(len(rows) == len(ids) for rows, ids in zip([development, holdout], orgs)),
            "boundary": "Offline registrable-domain checks using bundled suffix data; undiscovered hosts may still overlap."}


def reviewed(row, mode):
    review = row.get("review") or {}
    if not isinstance(review, dict):
        raise ValueError("Review provenance must be an object or null")
    reviewer, at = review.get("reviewer"), review.get("reviewed_at")
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(at, str) or not at:
        return False
    try:
        if datetime.fromisoformat(at.replace("Z", "+00:00")).tzinfo is None:
            return False
    except ValueError:
        return False
    return review.get("kind") in ({"independent_human"} if mode == "independent_human" else {"independent_human", "assistant"})


def membership_ids(rows):
    """Validate supplied membership without discovering or reading holdout outcomes."""
    ids = []
    for row in rows:
        org = row.get("organisation_number")
        if not isinstance(org, str) or not org.strip() or org != org.strip():
            raise ValueError("Membership requires a nonempty string organisation_number")
        urls = row.get("known_websites", [])
        if not isinstance(urls, list) or any(not isinstance(url, str) for url in urls):
            raise ValueError("known_websites must be a list of URL strings")
        ids.append(org)
    return ids


def evaluate(envelopes, labels, run, organisations, mode="independent_human"):
    if mode not in {"independent_human", "assistant_diagnostic"}:
        raise ValueError("Unknown review mode")
    organisations = list(organisations)
    if any(not isinstance(org, str) or not org.strip() for org in organisations) or len(set(organisations)) != len(organisations):
        raise ValueError("Input population must contain unique nonempty string IDs")
    expected = set(map(str, organisations))
    emitted = [str(e["organisation_number"]) for e in envelopes]
    publications = {(str(e["organisation_number"]), c["id"]): c for e in envelopes for c in e.get("claims", []) if c.get("availability") == "available"}
    if len(publications) != sum(c.get("availability") == "available" for e in envelopes for c in e.get("claims", [])):
        raise ValueError("Duplicate published claim IDs within an organisation")
    judgments = {}
    for row in labels.get("judgments", []):
        if row["run"] != run or not reviewed(row, mode):
            continue
        key = (str(row["organisation_number"]), row["claim_id"])
        if key in judgments:
            raise ValueError("Duplicate judgment")
        if key not in publications:
            raise ValueError("Judgment does not reference a published claim")
        for field in ["exact_entity", "correct", "evidence_valid", "material"]:
            if type(row.get(field)) is not bool:
                raise ValueError(f"Judgment needs boolean {field}; leave unknown claims unreviewed")
        judgments[key] = row
    opportunities = {}
    for row in labels.get("opportunities", []):
        if not reviewed(row, mode):
            continue
        evidence = row.get("evidence")
        if not isinstance(evidence, dict) or str(row["organisation_number"]) not in expected:
            raise ValueError("Opportunity needs evidence and an input organisation")
        if (not row.get("id") or not row.get("field") or
            any(not isinstance(evidence.get(k), str) or not evidence[k].strip() for k in ["source_url", "retrieved_at", "extraction_method"]) or
            not re.fullmatch(r"[a-f0-9]{64}", str(evidence.get("content_sha256", ""))) or
            not (evidence.get("claim_span") or evidence.get("span")) or
            not isinstance(evidence.get("source_locator"), dict) or not evidence["source_locator"].get("type")):
            raise ValueError("Opportunity needs ID, field, source/date/hash/method and exact span/locator")
        if row["id"] in opportunities:
            raise ValueError("Duplicate opportunity ID")
        opportunities[row["id"]] = row
    scope = [r for r in labels.get("scope", []) if reviewed(r, mode)]
    for row in scope:
        if str(row.get("organisation_number")) not in expected or not row.get("field") or not row.get("search_scope") or type(row.get("complete_within_scope")) is not bool:
            raise ValueError("Reviewed scope needs input organisation, field, search_scope and boolean completeness")
    scope_keys = [(str(r["organisation_number"]), r["field"]) for r in scope]
    if len(scope_keys) != len(set(scope_keys)):
        raise ValueError("Duplicate reviewed company-field scope")
    hits = set()
    for key, j in judgments.items():
        oid = j.get("opportunity_id")
        if oid:
            o = opportunities.get(oid)
            if not o or (str(o["organisation_number"]), o["field"]) != (key[0], publications[key]["field"]):
                raise ValueError("Opportunity mapping must resolve to the exact organisation and field")
            if j["exact_entity"] and j["correct"] and j["evidence_valid"]:
                hits.add(oid)
    fields = sorted({c["field"] for c in publications.values()} | {o["field"] for o in opportunities.values()})
    per_field = {}
    for field in fields:
        pool = {oid: o for oid, o in opportunities.items() if o["field"] == field}
        found = hits & pool.keys()
        pool_orgs = {str(o["organisation_number"]) for o in pool.values()}
        hit_orgs = {str(pool[oid]["organisation_number"]) for oid in found}
        keys = [key for key, c in publications.items() if c["field"] == field]
        audited = [judgments[key] for key in keys if key in judgments]
        company_recall, claim_recall = ratio(len(hit_orgs), len(pool_orgs)), ratio(len(found), len(pool))
        per_field[field] = {"publications": len(keys), "reviewed_publications": len(audited),
                            "claim_precision": ratio(sum(j["exact_entity"] and j["correct"] for j in audited), len(audited)),
                            "known_opportunities": len(pool), "known_positive_companies": len(pool_orgs),
                            "company_recall": company_recall, "individual_claim_recall": claim_recall,
                            "weighted_known_pool_coverage": .7 * company_recall + .3 * claim_recall if pool else None}
    ops = [e.get("operations", {}) for e in envelopes]
    def total(field):
        values = [o.get(field) for o in ops]
        return sum(values) if values and all(type(v) in {int, float} and math.isfinite(v) and v >= 0 for v in values) else None
    refresh = [r for r in labels.get("refresh_judgments", []) if r.get("run") == run and reviewed(r, mode)]
    for r in refresh:
        if type(r.get("correct")) is not bool or type(r.get("false_change")) is not bool:
            raise ValueError("Refresh judgments require boolean correct and false_change")
    if any(not r.get("case_id") for r in refresh) or len({r["case_id"] for r in refresh}) != len(refresh):
        raise ValueError("Refresh judgments require unique case IDs")
    runtime = [o["runtime_ms"] for o in ops if type(o.get("runtime_ms")) in {int, float} and math.isfinite(o["runtime_ms"]) and o["runtime_ms"] >= 0]
    material = [key for key, j in judgments.items() if j["material"]]
    availability_complete = bool(envelopes) and all(e.get("availability") in {"available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"} for e in envelopes)
    return {"run": run, "review_mode": mode,
            "input_fingerprint": hashlib.sha256(json.dumps(sorted(expected)).encode()).hexdigest(),
            "opportunity_pool_fingerprint": hashlib.sha256(json.dumps(opportunities, sort_keys=True).encode()).hexdigest(), "input_companies": len(expected), "envelopes": len(envelopes),
            "terminal_completeness": len(emitted) == len(expected) and set(emitted) == expected and len(emitted) == len(set(emitted)),
            "successful_company_fraction": ratio(sum(e.get("availability") == "available" for e in envelopes), len(expected)) if availability_complete and set(emitted) == expected and len(emitted) == len(expected) else None,
            "envelope_availability_complete": availability_complete,
            "publications": len(publications), "reviewed_publications": len(judgments),
            "review_complete": len(judgments) == len(publications),
            "opportunity_review_complete": len(opportunities) == len(labels.get("opportunities", [])),
            "scope_review_complete": len(scope) == len(labels.get("scope", [])),
            "exact_company_precision": ratio(sum(j["exact_entity"] for j in judgments.values()), len(judgments)),
            "claim_precision": ratio(sum(j["exact_entity"] and j["correct"] for j in judgments.values()), len(judgments)),
            "wrong_company_publications": sum(not j["exact_entity"] for j in judgments.values()),
            "material_wrong_company_publications": sum(not judgments[k]["exact_entity"] for k in material),
            "reviewed_evidence_validity": ratio(sum(j["evidence_valid"] for j in judgments.values()), len(judgments)),
            "material_evidence_complete": bool(material) and all(judgments[k]["evidence_valid"] for k in material),
            "availability_states": dict(Counter(c.get("availability") for e in envelopes for c in e.get("claims", []))),
            "per_field": per_field,
            "reviewed_scope": scope,
            "refresh": {"review_complete": len(refresh) == sum(r.get("run") == run for r in labels.get("refresh_judgments", [])),
                        "reviewed_cases": len(refresh), "correctness": ratio(sum(r["correct"] for r in refresh), len(refresh)),
                        "false_change_rate": ratio(sum(r["false_change"] for r in refresh), len(refresh))},
            "operations": {"requests": total("requests"), "third_party_cost_usd": total("third_party_cost_usd"),
                           "cost_per_input_company_usd": ratio(total("third_party_cost_usd"), len(expected)) if total("third_party_cost_usd") is not None else None,
                           "company_runtime_ms": latency_summary(runtime) if len(runtime) == len(envelopes) else {"n": len(runtime), "p50_ms": None, "p95_ms": None, "max_ms": None}, "runtime_complete": len(runtime) == len(envelopes), "runtime_observations": len(runtime)},
            "boundary": "Reviewed local opportunity pool only; assistant mode is diagnostic, unreviewed is unknown, no official score or qualification."}


def compare(baseline, challenger, policy):
    targets = policy.get("target_fields")
    if not isinstance(targets, list) or not targets or any(not isinstance(f, str) or not f.strip() for f in targets) or len(set(targets)) != len(targets):
        raise ValueError("Policy requires unique nonempty target_fields")
    if any(type(policy.get(k)) not in {int, float} or not math.isfinite(policy[k]) for k in ["maximum_precision_loss", "minimum_coverage_gain"]) or not 0 <= policy["maximum_precision_loss"] <= 1 or not 0 < policy["minimum_coverage_gain"] <= 1:
        raise ValueError("Policy precision tolerance and positive coverage gain must be within [0, 1]")
    if any(k not in {"requests", "third_party_cost_usd", "cost_per_input_company_usd"} or type(v) not in {int, float} or not math.isfinite(v) or v < 0 for k, v in policy["resource_caps"].items()):
        raise ValueError("Unsupported or negative resource cap")
    checks = {"same_input_population": baseline["input_fingerprint"] == challenger["input_fingerprint"],
              "same_opportunity_pool": baseline["opportunity_pool_fingerprint"] == challenger["opportunity_pool_fingerprint"],
              "complete_host_separation": baseline.get("complete_host_separation") is True and challenger.get("complete_host_separation") is True,
              "runtime_complete": baseline["operations"]["runtime_complete"] and challenger["operations"]["runtime_complete"],
              "independent_review": all(r["review_mode"] == "independent_human" for r in [baseline, challenger]),
              "review_complete": all(r["review_complete"] and r["reviewed_publications"] > 0 for r in [baseline, challenger]),
              "opportunity_review_complete": all(r.get("opportunity_review_complete") is True for r in [baseline, challenger]),
              "target_scope_complete": all(r.get("scope_review_complete") is True and
                  all(sum(s["field"] == f and s["complete_within_scope"] is True for s in r["reviewed_scope"]) == r["input_companies"] for f in targets)
                  for r in [baseline, challenger]),
              "terminal_completeness": baseline["terminal_completeness"] and challenger["terminal_completeness"],
              "no_material_wrong_company": challenger["material_wrong_company_publications"] == 0,
              "no_additional_wrong_company": challenger["wrong_company_publications"] <= baseline["wrong_company_publications"],
              "material_evidence_complete": challenger["material_evidence_complete"],
              "precision_preserved": challenger["claim_precision"] is not None and baseline["claim_precision"] is not None and challenger["claim_precision"] >= baseline["claim_precision"] - policy["maximum_precision_loss"]}
    gains = []
    for field in policy["target_fields"]:
        a = baseline["per_field"].get(field, {}).get("weighted_known_pool_coverage")
        b = challenger["per_field"].get(field, {}).get("weighted_known_pool_coverage")
        gains.append(b - a if a is not None and b is not None else None)
    checks["declared_coverage_gain"] = bool(gains) and all(g is not None and g >= 0 for g in gains) and any(g is not None and g >= policy["minimum_coverage_gain"] and g > 0 for g in gains)
    for metric, cap in policy["resource_caps"].items():
        value = challenger["operations"].get(metric)
        checks[f"resource_{metric}"] = type(value) in {int, float} and value <= cap
    checks["resource_caps_declared"] = bool(policy["resource_caps"])
    checks["refresh_verified"] = challenger["refresh"].get("review_complete") is True and challenger["refresh"]["correctness"] == 1 and challenger["refresh"]["false_change_rate"] == 0
    return {"promotion_passed": all(checks.values()), "checks": checks, "boundary": "Local promotion decision, never official qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", required=True)
    parser.add_argument("--holdout", required=True, help="Membership/known URLs only; never crawled")
    parser.add_argument("--baseline")
    parser.add_argument("--challenger")
    parser.add_argument("--labels")
    parser.add_argument("--policy")
    parser.add_argument("--baseline-name", default="baseline")
    parser.add_argument("--challenger-name", default="challenger")
    parser.add_argument("--review-mode", choices=["independent_human", "assistant_diagnostic"], default="independent_human")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    development, holdout = read_jsonl(args.development), read_jsonl(args.holdout)
    report = {"split_audit": audit_split(development, holdout)}
    if any([args.baseline, args.challenger, args.labels, args.policy]):
        if not all([args.baseline, args.challenger, args.labels, args.policy]):
            parser.error("Comparison requires baseline, challenger, labels and policy")
        if not report["split_audit"]["known_separation_passed"]:
            parser.error("Split overlap or duplicate inputs; comparison refused")
        labels = json.loads(Path(args.labels).read_text())
        orgs = [r["organisation_number"] for r in development]
        for name, path, run in [("baseline", args.baseline, args.baseline_name), ("challenger", args.challenger, args.challenger_name)]:
            report[name] = evaluate(read_jsonl(path), labels, run, orgs, args.review_mode)
        for name in ["baseline", "challenger"]:
            report[name]["complete_host_separation"] = report["split_audit"]["complete_host_separation"]
        report["comparison"] = compare(report["baseline"], report["challenger"], json.loads(Path(args.policy).read_text()))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
