# Chat assignment: live development validation

Follow ../parallel-chat-plan.md, including its exact file ownership. This task
checks real development evidence; it does not alter discovery/extraction logic.

Read ../dated-events-progress.md and ../website-discovery.md. Confirm snapshot
version `free_sources_v3_dated_events` and the current tests/fixtures are present.

1. Inspect current environment network configuration when available and retry
   the existing two-company development check. Previous DNS/proxy failures are
   observations, not proof they persist. Inspect credential names/presence only if
   actually needed; these core sources require no paid credentials.
2. Prepare a bounded runner using existing ResearchSession, site research,
   snapshot and envelope APIs. Select only companies from development.jsonl.
   Begin with 985215294 and 984589344; at most four development companies total,
   max four pages/company, eight-second source timeout, 40-second company budget,
   20 requests/company, 180-second overall supervised run budget, one worker.
   Expose these non-secret limits in the report. Do not enable unvalidated Wikidata.
3. Persist acquisition profiles, source bytes, terminal envelopes, request/error
   telemetry and an offline evidence audit in out/live-development-review/.
   Use public identity records to verify the exact company; never assume a
   registry-listed site is verified. Respect robots/terms, TLS and URL checks.
4. If access is blocked, diagnose DNS/proxy/denial and finish runner/tests offline.
   Save only narrow necessary network additions, preserving known rules. Report
   settings action required; never bypass verification or assume a saved draft
   changed runtime. Don't retry unchanged failing operations repeatedly.
5. If acquisition succeeds, report verified site/event counts and request/runtime
   costs. Compare only same-source bytes when a captured baseline is available;
   otherwise report current results without claiming measured improvement.

Acceptance: deterministic bounded runner tested offline, exactly one envelope per
selected input including failures, evidence audit outcomes recorded, live results
or specific external blocker reported honestly. No holdout, bulk download, paid
API, independent-human-precision claim or official-score claim.

Save docs/task-results/live-validation.md. If a production bug prevents progress,
describe it and the smallest proposed change; do not edit coordinator-owned code.
