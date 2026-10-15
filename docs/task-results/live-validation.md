# Live validation result — 12 October 2026

Completed the bounded runner and offline validation within ownership. The real
two-company retry remains blocked by executor DNS/proxy connectivity. No live
coverage improvement, independent precision or official score is established.

## Snapshot and ownership

Verified before editing: latest 12 October cloud handoff, parallel-chat plan and
assigned brief, strategy `free_sources_v3_dated_events`, frozen development input,
dated-event and strategy-evaluation fixtures. Checkout HEAD is
`a7c24efa2a3d7193fcfaf8dbc3298ec295b667d7`, with intentional prior uncommitted
work. Initial status/diff were saved; the pre-existing tracked diff remains
byte-identical after this assignment. Shared versus isolated filesystem: **unknown**.
An owned-file patch is supplied for integration if needed.

Only these files were created:

- `scripts/run_development_review.py`
- `tests/test_development_review.py`
- `docs/live-development-review.md`
- `docs/task-results/live-validation.md`

## Implementation and limits

The runner selects only frozen development members, rejects duplicates/unknown
inputs, writes a fresh output subdirectory, and supervises one company process
at a time. Default inputs: 985215294 and 984589344. Maximum four companies,
four pages/company, eight-second source timeout, 40-second supervised company
budget, 20 requests/company, 180-second overall acquisition budget, one worker;
two seconds per supervision deadline are reserved for cleanup. Wikidata is off.
Public registry identity must match before any verified site can be published.
Existing robots, TLS, URL and exact-owner checks remain intact.

Pre-DNS operations, errors, source captures and telemetry are persisted.
Timeouts/source failures still produce exactly one terminal envelope per input.
Killed-worker counters are explicitly incomplete. Offline audit follows acquisition.
Only registry identity and site sources are requested; placeholders for other
envelope modules do not imply those sources were queried.

## Commands and outcomes

- `.venv/bin/python -m unittest discover -s tests -p test_development_review.py -v`:
  **9 tests passed**, 2.533 seconds. Covers successful same-byte replay/audit,
  input/output bounds, request/time limits, source failures, hung-process cleanup,
  retained source bytes, pre-DNS logging, and identity mismatch/unavailability.
  Test development found two fixture assertions that incorrectly included observed
  runtime or assumed an exact capture count; both were corrected and rerun.
- `.venv/bin/python -m unittest discover -s tests -p test_site_events.py -v`:
  **8 passed**, 0.296 seconds.
- `.venv/bin/python -m unittest discover -s tests -p test_wikidata_discovery.py -v`:
  **6 passed**, 0.151 seconds, offline only; no Wikidata requests.
- `.venv/bin/python scripts/run_development_review.py --output-dir out/live-development-review/live-20261012`:
  exit **0**, 2/2 envelopes, 1.414 seconds acquisition/export/audit wall time,
  both worker exit codes 0. The exit code reflects terminal-output/audit success,
  not successful acquisition.
- Offline evidence audit: **passed**, 2 envelopes, exact input order/membership,
  zero snapshots, zero cited locators, zero audit errors. This is a failure-path
  audit and provides no acquired-fact support.
- `git diff --check`: passed. Existing tracked diff comparison: identical.
  Full regression after integration remains the coordinator's assignment.

## Live blocker and measurements

At 13:41 IST on 12 October, both registry identity requests and the two site
homepage operations failed `Hostname did not resolve`, before HTTP acquisition.
Acquisition counters: **0 requests, 0 bytes, $0 third-party cost**. Four attempted
source operations were retained in telemetry; DNS checks are not counted as HTTP.
There are zero verified sites, news and jobs, with failed availability rather than
absence conclusions. No same-source captured baseline exists for comparison.

Three separate, eight-second inherited-proxy connectivity diagnostics targeted
the registry endpoint and `robots.txt` on each company host. All exited curl 7:
`Failed to connect to proxy port 8080 ... Could not connect to server`; status 000,
zero response bytes. These three diagnostic attempts are separate from acquisition
counters and are not claim evidence. The earlier CONNECT 403 was not reproduced.
No unchanged failing request was repeatedly retried.

Runtime environment status reported current observations and running state, but
network enforcement state `unknown`. `/etc/codex/network-policy.json` and status
already list `data.brreg.no`, `www.nf.no`, `www.nfs.no`. Necessary additions: **none**.
`network-requirements.json` preserves the known rules and records the needed action.
Restore DNS and connectivity to the configured proxy via environment settings or
support, restart/restore the runtime as appropriate, verify actual readiness, then
retry this command once with a fresh output directory. A saved draft alone is not
evidence of applied runtime access. No proxy bypass or disabled verification was used.

## Artifacts and next dependencies

All repository-generated artifacts are under `out/live-development-review/`:

- `live-20261012/inputs.jsonl`, `profiles.jsonl`, `envelopes.jsonl`, `report.json`,
  `audit.json`, per-company `telemetry/*.json`, empty `snapshots/`,
  `network-diagnostics.json`, and `network-requirements.json`.
- `work/initial-status.txt`, `initial.diff`, `head.txt`, `preserved-current.diff`,
  `live-command.log`, and focused test logs.
- `live-validation.patch` contains only the four owned new files.

No production bug requiring coordinator-owned changes was established. The next
dependency is working environment DNS/proxy access, followed by the same bounded
development retry. Coordinator integration/full regression and independent human
review remain separate work. No holdout read/crawl, bulk download, paid API,
credential collection, commit, push, publication or submission occurred.
