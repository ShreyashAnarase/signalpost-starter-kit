# Signalpost handoff — 11 October 2026

## Continuation update — 12 October 2026 (read first)

Work now runs directly in Documents. See `docs/coverage-progress-20261012.md` for
changes, exact artifacts, commands and measurement limits. The original handoff
below is historical where this update supersedes it.

- Retrieval fixes: declared/detected HTML encodings with matching audit decoding,
  same-host frames and image maps, robots-checked HTTP fallback for TLS failures,
  exact legal-name/registered-phone contact blocks, conflicts on any legal footer.
- Website claims cite identity-bearing pages. Fixed nested-footer locators and
  privacy/cookie pages incorrectly emitted as contact-page claims.
- Graceful worker exit now succeeds. Source/input fingerprints enter resume
  configuration; strategy is `free_sources_v2`. Prior refresh snapshot corruption
  is rejected without discarding current facts; old leadership is marked last known.
- `scripts/prepare_coverage_review.py` freezes equal-allocation diagnostic splits.
  `data/coverage-review-v1/` contains 24 development + 24 untouched holdout
  companies, excluding the previously used 100. This is not a population sample.
- Targeted live v4: **3/4 sites**, 37 requests, 63.505 seconds, $0, exit 0.
  AAS and Bærum now verify; AIOTA retained; APPELX rejected. Corrected export:
  `out/development-v4-reviewed/` (136 audited locators, zero errors).
- New stratified live run: **6/24 sites**, no jobs/news, 230 requests, 73.097
  seconds, $0, exit 0. Final offline export: `out/coverage-development-v1-final/`
  (119 snapshots, 812 locators, zero errors). Six positive identities inspected by
  the assistant; no independent human review or official score. Review notes and
  per-stratum counts are in that directory. Do not compare 6/24 to old 1/100.
- `scripts/reexport_competition.py` re-extracts retained accepted-site pages and
  exports/audits without network, recording acquisition and export hashes. It
  does not redo discovery. Use a fresh output directory.
- Final regression suite: **133 tests pass** (3.381 seconds).
- The 100-company smoke has not been rerun. Evidence paths are still absolute;
  packaging remains unfinished. No UI work, paid services, submission or Git
  repository creation occurred. API credentials/budget questions remain deferred.

Next: candidate discovery for the 11/12 no-registry-website companies still
unresolved in the new development set; dated news/jobs extraction; independent
labels; then untouched holdout and final smoke. Keep attribution strict.

## Read this first

The user is entering the Signalpost competition and wants a score capable of winning. UI is secondary. They approved implementation after planning. Continue the engineering work; do not mistake passing local checks for a competitive score.

The user explicitly deferred the question about organizer-provided model/search credentials and time/API budgets: **ask later, not immediately on resuming**. No paid API budget is approved. Never request that they paste a secret into chat. No organizer messages, publication, or submission have been authorized or performed.

The actual project is `/Users/sanarase/Documents/signalpost-starter-kit`. The previous Downloads location is gone. Open the Documents folder in the new chat so its workspace permissions are correct. Work in this session used `/private/tmp/signalpost-finish-20261011` because the client still granted writes only to Downloads; changes and artifacts were synchronized back to Documents. The staging directory is disposable after verifying the Documents copy.

## Competition and strategy

Challenge: https://builderr.ai/challenges/signalpost

Latest page checked during this work: board reviewed October 5, 37 submissions, 28 assessed, none qualified. Leader Nikita: 60.80 = recall 13.82/50 + evidence 26.98/30 + synthesis 12/12 + UX 8/8. The evaluation set is now 1,500 companies, each run twice. The user's pasted October 1 board (leader 45.59, 1,200 companies) is older.

Current scoring: recall/coverage 50, precision/evidence 30, synthesis 12, UX 8; qualifying score 65. The opportunity is more correctly attributed external facts with complete evidence. Registry-only enrichment and polished UI will not suffice. No official score for our entry exists. Old local proxy rubrics are obsolete and must not drive optimization.

Detailed contract calls for a 100-company smoke report, reproducible command, repository and exact commit; the banner's 1,000-profile language is not a substitute for the submission contract. Revisions reportedly close October 18; challenge closes October 21; first submission plus four revisions maximum. Recheck official rules before submitting. No Git repository/commit has been created here yet.

Primary references read during the work:
- https://builderr.ai/docs/signalpost-evaluation-harness.md
- https://builderr.ai/starter-briefs/signalpost.md
- https://builderr.ai/starter-briefs/signalpost-sources.md
- https://builderr.ai/starter-briefs/signalpost-agent-playbook.md
- https://builderr.ai/starter-briefs/signalpost-learning-harness.md

Requirements include exact legal-company attribution, six availability states, URL/time/hash/period/snippet/locator evidence, immutable history, idempotent refresh, bounded execution and one result per input. Missing values must not become zero. Model guesses cannot establish exact identity.

## Implemented

- `acquisition.py`: content-addressed retained response bytes and immutable bulk snapshots; request budgets, retries, robots checks, public URL/DNS checks, redirect capture and telemetry.
- `site_research.py`: registry/bulk/email-domain website candidates; strict legal-company verification; bounded contact/about/careers/news crawling; structured dated jobs/news, descriptions and social links. Explicit conflicting legal footer ownership rejects a site. Personal email providers and restricted platforms excluded.
- `submission.py`: current six-state envelope and cited claims, official JSON/CSV locators, snapshot validity checks, account scope, observed financial periods and deterministic cited summaries. Refresh keeps omitted/failed old facts marked last_known instead of inventing deletions.
- `pipeline.py`: independent official-source failure handling and supervised worker process with hard batch deadline and one output per company.
- `scripts/run_competition_batch.py`: dynamic input size, bounded concurrent runs, checkpoint/resume, snapshots, refresh/change outputs, coverage and resource reports.
- `batch.py`: streaming bulk hashing and fallback placeholders for organizations absent from bulk.
- `sampling.py`: handles both gzip and plain CSV (the supplied .csv is gzip).
- `official.py`: email and phone normalization, including mobile fallback.
- `website.py`: bundled public-suffix data, avoiding unexpected tldextract network fetches.
- `audit.py` and `scripts/audit_submission.py`: offline membership/schema, source file hash, JSON pointer, CSV row, text/CSS and outbound-link evidence audit.
- `tests/test_competitive.py`: 19 added tests; snapshots, identity negatives, budgets, schema, zero/missing, refresh, missing bulk row, synthetic 1,200-company isolation and hung-worker termination.

README, OUTPUT_CONTRACT and some other documentation still describe legacy behavior. Legacy prototype UI has not been adapted to the new evidence envelopes. This is an implemented foundation, not a finished submission.

## Verified results and limits

Final source tree: **123 unittest tests pass** (3.219 seconds). The 1,200-company test is synthetic; no live 1,200/1,500-company validation has been done.

Live 100-company run: `out/competitive-smoke/`:
- 100/100 output envelopes, 605 HTTP requests, 131.022 seconds, 5,034,276 response bytes, $0 third-party API cost.
- No unfinished companies or batch deadline exhaustion; telemetry complete.
- Offline evidence audit passes: 100 envelopes, 410 unique snapshots, 2,888 evidence locators checked, zero errors.
- Website availability: available 1, ambiguous 9, source_error 7, blocked 2, not_found 81. No jobs/news found.
- Only **1/100 verified websites**, versus 2 in the older baseline. Do not claim a coverage improvement. Stronger attribution correctly rejects several unrelated, parent and accountant sites, but discovery remains inadequate.
- Successful run reports worker_exit_code -15 because cleanup permits only 0.2 seconds before terminating the completed worker process. All outputs arrived, but fix graceful process cleanup.
- Maximum request latency was 32,011 ms despite nominal 8-second timeout (DNS/multiple socket attempts); process supervision provides the hard overall bound.

Four-company live run: `out/development-v2/`, 4/4 outputs, 44 requests, 77.310 seconds. Audit passes: 18 snapshots, 123 locators.
- 888567232 AAS ELEKTRONIKK AS: HTTPS self-signed certificate; legacy HTTP fallback obtained evidence, new collector does not yet fall back. Never disable TLS verification.
- 914561302 APPELX AS: registry URL redirects to STUDIO X, footer organization 920990029. Correct rejection. Alternate email domain timed out.
- 999288448 BÆRUM EIENDOMSTAKSERING AS: betakst.no reachable but insufficient identity cues extracted from legacy homepage/navigation.
- 933787141 AIOTA AS: verified website, description and contact-page facts.

Important version boundary: the live 100-company output predates the final account_scope, observed financial_history and richer-summary changes in submission.py. The final source passes tests, but rerun or re-export and audit before claiming live validation of that exact version. Evidence audit proves retained bytes/locators, NOT human-reviewed exact-company precision, recall, or official score.

Original baseline files remain in out (smoke-retry-profiles/report and development-4 input). Older 100-company run had all official modules available, 7 registry website URLs, 6 fetched, 2 verified. Business email domains often belong to accountants/property managers and have not produced a demonstrated coverage gain.

## Commands

Working directory: `/Users/sanarase/Documents/signalpost-starter-kit`.
The moved `.venv/bin/python` works (Python 3.13). Dependencies and uv.lock already present. Local uv exists at `.tools/uv/bin/uv`; not on PATH.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests -q

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/audit_submission.py \
  --input out/competitive-smoke/envelopes.jsonl \
  --organisations smoke-companies.jsonl \
  --report out/competitive-smoke/audit.json

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/run_competition_batch.py \
  --organisations smoke-companies.jsonl --bulk brreg-enheter.csv \
  --profiles-output out/competitive-smoke-next/profiles.jsonl \
  --output out/competitive-smoke-next/envelopes.jsonl \
  --report out/competitive-smoke-next/report.json \
  --snapshot-dir out/snapshots --run-id competitive-smoke-next \
  --workers 8 --deadline-seconds 600 --company-timeout 75
```

Use a new run ID/output directory after code changes: resume fingerprints currently include configuration but not source code hash. Read runner --help for supported refresh and resume arguments. Snapshot metadata paths were rewritten to Documents during handoff; immutable .bin/.csv bytes were not modified.

## Prioritized next work

1. Improve independently verified website discovery and external facts on a representative, manually reviewed development set. Keep a separate holdout. Measure correct company matches and coverage by company type, not just claim counts. Current free email-domain heuristic is insufficient.
2. Fix graceful worker completion; HTML charset handling on older Norwegian websites; useful lawful HTTP fallback for sites with broken HTTPS; old frames/navigation discovery. Do not weaken legal identity checks to inflate hits.
3. Add code/strategy version to reproducibility and resume fingerprints (current strategy label free_sources_v1 is static). Make evidence paths portable for submission. Add regressions for audit, source corruption, mobile phone pointers, financial scope/history and explicit foreign footer owners.
4. Review refresh integrity: validate prior retained snapshots; ensure last_known leadership/identity is not described as current; preserve idempotency. Old reference structure validation alone is insufficient.
5. Scale test only after improving coverage and learning resource constraints. Default 900 seconds with a 0.2-second per-host start interval cannot support 1,500 companies times ~5 official calls (roughly 1,500 seconds minimum at that rate). Optimize lawful caching/bulk use or tune budgets transparently. No large live run has been performed.
6. Build a small evidence/changes viewer over the current envelopes, keeping UI secondary. Update README/output contract/reproducible instructions. Produce final repeatable smoke runs, then repository/commit/submission package. Do not submit without authorization.
7. Ask later whether Builderr provides model/search credentials and an official resource budget. Optional model/search integration is not implemented. Never infer that the user approved paid services.

## Candidate sources researched, not implemented

NAV job feed: https://navikt.github.io/pam-stilling-feed/ . Current API /api/v1/feed is paginated and has no employer filter. employer.orgnr and employer.homepage could support exact matches and website discovery. Experimental public token endpoint exists; production requires registration and acceptance of terms. No token/feed was fetched, and no email sent. Terms https://arbeidsplassen.nav.no/vilkar-api require removing stopped/expired jobs and constrain contact information retention; reconcile this with evidence retention before integration. The old pam-public-feed is deprecated.

Wikidata: P2333 Norwegian organization number and P856 website could yield candidate sites with independent verification. https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service . No query executed or connector implemented; confirm applicable service limits/licensing before use.

Existing Brave candidate connector may be usable if organizer-supported credentials and budget are supplied. It is not enabled. Do not replace it with unsupported search-result scraping.

## Operational notes

No applicable AGENTS.md was found. No subagents were used. No active live runs remain. Current source and artifacts are local only; no deployment, submission or official assessment exists. This handoff is the authoritative continuation context, but inspect the current files and rerun focused checks before changing them.
