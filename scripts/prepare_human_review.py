#!/usr/bin/env python3
"""Prepare an offline development review packet; all human labels remain unknown."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from evaluate_strategy import audit_split, membership_ids, read_jsonl


def prepare(envelopes, development, holdout, snapshot_root, run, fields):
    """Return deterministic packet, blank comparator labels and verified local bytes.

    Membership is checked before any evidence file is opened. Missing/corrupt
    bytes are exposed for review preparation, never treated as valid evidence.
    """
    dev_ids, hold_ids = membership_ids(development), membership_ids(holdout)
    if len(dev_ids) != len(set(dev_ids)) or len(hold_ids) != len(set(hold_ids)):
        raise ValueError("Duplicate split membership")
    if set(dev_ids) & set(hold_ids):
        raise ValueError("Development overlaps holdout")
    if any(r.get("evaluation_split", "development") != "development" for r in development):
        raise ValueError("Development contains a non-development member")
    if any(r.get("evaluation_split", "holdout") != "holdout" for r in holdout):
        raise ValueError("Holdout membership is malformed")
    emitted = membership_ids(envelopes)
    if set(emitted) & set(hold_ids):
        raise ValueError("Holdout organisations refused")
    if len(emitted) != len(set(emitted)) or set(emitted) != set(dev_ids):
        raise ValueError("Require exactly one envelope per development organisation")
    if not run or not fields or len(fields) != len(set(fields)) or any(not isinstance(f, str) or not f.strip() for f in fields):
        raise ValueError("Run and unique nonempty review fields are required")
    root = Path(snapshot_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Evidence root must be a local directory")
    companies = {r["organisation_number"]: r for r in development}
    packet_rows, judgments, snapshots = [], [], {}
    blank_review = {"kind": None, "reviewer": None, "reviewed_at": None}
    for envelope in sorted(envelopes, key=lambda e: e["organisation_number"]):
        org = envelope["organisation_number"]
        claims, sources = envelope.get("claims", []), envelope.get("evidence", [])
        if not isinstance(claims, list) or not isinstance(sources, list):
            raise ValueError("Claims and evidence must be lists")
        source_map = {}
        for source in sources:
            sid = source.get("id")
            if not isinstance(sid, str) or not sid or sid in source_map:
                raise ValueError("Evidence IDs must be unique nonempty strings")
            for key in ["source_url", "retrieved_at", "content_sha256", "claim_span", "extraction_method"]:
                if not isinstance(source.get(key), str) or not source[key].strip():
                    raise ValueError(f"Evidence requires {key}")
            if not isinstance(source.get("source_locator"), dict) or not source["source_locator"].get("type"):
                raise ValueError("Evidence requires an exact source locator")
            path_value = source.get("snapshot_path")
            if not isinstance(path_value, str) or not path_value:
                raise ValueError("Evidence needs a local snapshot path")
            candidate = Path(path_value)
            path = (candidate if candidate.is_absolute() else root / candidate).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Snapshot path escapes the evidence root")
            item = copy.deepcopy(source)
            item["original_snapshot_path"] = path_value
            item["snapshot_path"] = None
            item["bytes_status"] = "missing"
            if path.exists():
                if not path.is_file():
                    raise ValueError("Snapshot must be a regular local file")
                raw = path.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                item["observed_sha256"] = digest
                if digest == source.get("content_sha256"):
                    item["bytes_status"] = "verified"
                    item["snapshot_path"] = f"snapshots/{digest}.bin"
                    snapshots[item["snapshot_path"]] = raw
                else:
                    item["bytes_status"] = "hash_mismatch"
            source_map[sid] = item
        ids = set()
        for claim in claims:
            cid = claim.get("id")
            if not isinstance(cid, str) or not cid or cid in ids or not claim.get("field"):
                raise ValueError("Claims require unique IDs and a field")
            ids.add(cid)
            if claim.get("availability") not in {"available", "not_available", "blocked", "not_applicable", "ambiguous", "failed"}:
                raise ValueError("Unknown claim availability")
            refs = claim.get("evidence_ids", [])
            if not isinstance(refs, list) or any(ref not in source_map for ref in refs):
                raise ValueError("Dangling or malformed claim evidence references")
            if claim["availability"] == "available" and (claim.get("value") is None or not refs):
                raise ValueError("Available claim requires value and evidence")
            if claim["availability"] != "available" and claim.get("value") is not None:
                raise ValueError("Unavailable claim must leave value unknown")
            evidence = [source_map[ref] for ref in refs]
            packet_rows.append({"organisation_number": org, "company": companies[org],
                                "legal_identity": envelope.get("legal_identity", {}),
                                "run": run, "claim": copy.deepcopy(claim), "evidence": evidence})
            if claim["availability"] == "available":
                judgments.append({"run": run, "organisation_number": org, "claim_id": cid,
                                  "opportunity_id": None, "exact_entity": None, "correct": None,
                                  "evidence_valid": None, "material": None,
                                  "review": dict(blank_review)})
    scope = [{"organisation_number": org, "field": field, "search_scope": None,
              "complete_within_scope": None, "notes": None, "review": dict(blank_review)}
             for org in sorted(dev_ids) for field in sorted(fields)]
    missing = [{"organisation_number": row["organisation_number"], "claim_id": row["claim"]["id"],
                "evidence_id": e["id"], "bytes_status": e["bytes_status"]}
               for row in packet_rows for e in row["evidence"] if e["bytes_status"] != "verified"]
    packet = {"schema_version": "signalpost-human-review-v1", "run": run,
              "envelopes_sha256": hashlib.sha256(json.dumps(envelopes, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
              "development_companies": [companies[org] for org in sorted(dev_ids)],
              "split_audit": audit_split(development, holdout), "claims": packet_rows,
              "evidence_issues": missing, "retained_bytes_complete": not missing,
              "boundary": "Local bytes only. Hash verification does not judge identity, claim support or locators. Unresolved companies are unknown, never negatives."}
    labels = {"opportunities": [], "judgments": judgments, "scope": scope, "refresh_judgments": []}
    return packet, labels, snapshots


def write_packet(output, packet, labels, snapshots):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in sorted(snapshots.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for name, value in [("packet.json", packet), ("labels-template.json", labels)]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", required=True)
    parser.add_argument("--holdout", required=True, help="Membership only; no research outcomes")
    parser.add_argument("--envelopes", required=True)
    parser.add_argument("--snapshot-root", required=True, help="Explicit local evidence containment root")
    parser.add_argument("--run", required=True, help="Must match comparator run name")
    parser.add_argument("--fields", nargs="+", default=["official_website", "job_posting", "company_news"])
    parser.add_argument("--output-dir", required=True, help="New directory; existing outputs refused")
    args = parser.parse_args()
    try:
        packet, labels, snapshots = prepare(read_jsonl(args.envelopes), read_jsonl(args.development),
                                            read_jsonl(args.holdout), args.snapshot_root, args.run, args.fields)
        write_packet(args.output_dir, packet, labels, snapshots)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Review preparation refused: {exc}\n")
    print(json.dumps({"claims": len(packet["claims"]), "blank_judgments": len(labels["judgments"]),
                      "snapshots": len(snapshots), "evidence_issues": len(packet["evidence_issues"])}))


if __name__ == "__main__":
    main()
