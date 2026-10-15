# Bounded development acquisition

`scripts/run_development_review.py` reads only the frozen
`data/coverage-review-v1/development.jsonl`. Its default selections are
NORVIGROUP NORSK DUN AS (985215294) and NORSK FARMASØYTISK SELSKAP (984589344).
Unknown, duplicate, empty, or more than four selections are rejected before
network work. Holdout inputs are never loaded. The required strategy is
`free_sources_v3_dated_events`; Wikidata is disabled.

```sh
.venv/bin/python scripts/run_development_review.py \
  --output-dir out/live-development-review/retry-unique-id
.venv/bin/python -m unittest discover -s tests -p test_development_review.py -v
```

Use a new output directory for each run. Output is restricted to a fresh
subdirectory of `out/live-development-review/`. An optional `--organisations`
accepts one to four development organisation numbers. Limits cannot be increased
from the CLI: one worker, four pages/company, eight-second source timeout,
20 HTTP requests/company, 40-second supervised company budget and 180-second
overall acquisition budget. Each company runs in its own killable process through
the existing `collect_batch` API. Two seconds are reserved within each budget
for termination/kill cleanup; this also bounds stalled DNS/read calls. Offline
export/audit follows acquisition. Scheduling and process startup have normal OS
overhead; the budgets are supervision deadlines, not real-time guarantees.

Acquisition uses `ResearchSession`, `SnapshotStore`, `fetch_official_modules` and
`research_site`, preserving public URL validation, TLS verification, redirects,
robots policy, pacing and exact legal ownership checks. A mismatching public
registry identity prevents site research. Unavailable fresh registry identity
allows diagnostic acquisition against frozen development candidates but prevents
publishing a site as verified. No identity evidence is invented from frozen input.
The scope is registry identity and site research; other official modules are not
queried and their envelope placeholders do not measure those sources' availability.

Artifacts include selected `inputs.jsonl`, acquisition `profiles.jsonl`, immutable
`snapshots/*.bin`, one `envelopes.jsonl` entry per input, `audit.json`, `report.json`
and per-company `telemetry/*.json`. Telemetry saves an operation before DNS and
records exceptions, HTTP attempts, capture metadata and resource counters after
each completed operation. A killed worker may leave `state: started` and orphan
source bytes; the terminal profile explicitly marks its resource telemetry
incomplete. Such requests/bytes must not be presented as complete totals.

Audit checks exact input membership/order, envelope structure and all cited
retained bytes/locators. An all-failure run can pass with zero locators: this
validates terminal output handling and proves no successful acquisition. It does
not establish independent human precision, recall or an official score.

The 12 October retry captured no source bytes: public hostnames failed to resolve,
and separate diagnostics could not connect to the inherited proxy at port 8080.
The three required hosts are already in the runtime policy snapshot. No extra
domains are supported by this evidence. Restore executor DNS/proxy connectivity
through environment settings/support, then rerun once into a fresh directory.
Saving a configuration draft alone does not establish runtime readiness. Do not
unset proxies, disable TLS or weaken public URL checks to work around the failure.
