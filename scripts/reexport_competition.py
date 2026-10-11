#!/usr/bin/env python3
"""Re-extract retained company pages and export/audit envelopes without network."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from norway_company_agent.acquisition import Capture
from norway_company_agent.audit import audit_envelopes
from norway_company_agent.site_research import assess_site, extract_site_facts, page_kind, read_page
from norway_company_agent.submission import snapshot_valid, submission_envelope
from norway_company_agent.versioning import source_fingerprint
from run_competition_batch import coverage_report, read_jsonl, write_jsonl


class RetainedSession:
    def __init__(self, pages):
        self.pages = {page["url"]: page for page in pages}

    def get(self, url, **kwargs):
        page = self.pages[url]
        if not snapshot_valid(page):
            raise ValueError("Missing or corrupt retained page")
        return Capture(page.get("requested_url", url), url, 200, page["content_type"],
                       Path(page["snapshot_path"]).read_bytes(), page["retrieved_at"],
                       page["content_sha256"], page["snapshot_path"], page.get("redirect_chain", []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--acquisition-report", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    profiles = read_jsonl(Path(args.profiles))
    acquired = json.loads(Path(args.acquisition_report).read_text())
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    envelopes = []
    for profile in profiles:
        record = profile["evidence"].get("website", {})
        if record.get("status") == "available":
            value = record["value"]
            session = RetainedSession(value["pages"])
            pages = [read_page(session, page["url"], "homepage" if index == 0 else page_kind(page["url"]) or page["kind"])[0]
                     for index, page in enumerate(value["pages"])]
            identity = assess_site(profile, pages)
            if identity["publishable"]:
                value["facts"] = extract_site_facts(profile, pages)
                value["identity_assessment"] = identity
            else:
                record.update(status="ambiguous", value=None, note="Retained pages fail current identity checks")
        envelopes.append(submission_envelope(profile, run_id=acquired["run_id"] + "-reexport",
            started_at=acquired["started_at"], completed_at=acquired["completed_at"]))
    audit = audit_envelopes(envelopes, [profile["organisation_number"] for profile in profiles])
    report = {"mode": "offline_reexport", "acquisition_report": args.acquisition_report,
              "acquisition_source_sha256": acquired.get("source_sha256"), "export_source_sha256": source_fingerprint(ROOT),
              "new_http_requests": 0, "coverage": coverage_report(envelopes), "audit": audit}
    write_jsonl(output / "envelopes.jsonl", envelopes)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
