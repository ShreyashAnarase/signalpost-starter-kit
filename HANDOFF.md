## Highest-priority continuation — 15 October 2026: prepare early version 1

User explicitly prefers an early submission; first version +4 revisions (=5total),
verified against current official contract15Oct. Earlier daily scores stay inmean.
Prepare first entry now with Tavily + BRREG + company sites; NAV optional/off,
no LLM. Do not wait for NAV or maximal coverage. No official score is known.

Fresh current-code100 on15Oct:100outputs,14sites,7articles/3companies,0jobs,
173.707s,1190operations,94Basic queries under verified free allowance (preflight
Researcher396used/1000, paygo0).448snapshots/3164locators audit. Runtime source
b98393804c380ae1fbff62f7c4d7a97b42aa631e615f6e70701f4e08adcf5973.
Public smoke docs updated, static100sampleincluded at signalpost/index.html;
source raw snapshots not exported. Paid reference $0.752/100; proposedmax8.80/1100.
Canonical run command now explicitly matches tested crawl/time caps, with only
local free pricing and smoke query cap differing from declared official limits.
See docs/version-1-release.md and docs/first-submission-draft.md.

Actual GitHub repository visibility is PRIVATE (verified15Oct). Do not change
visibility without owner approval. Evaluator read access is a real release issue,
not a reason to abandon private preparation. Exact candidate SHA and clean
verification belong in ignored out/first-entry-20261015/release-manifest.json once
created; email contact and prepared .eml must stay in ignored out/, not Git.

Entrant has SENT NAV consumer application and shared automatic acknowledgment
15Oct; NAV says replywithin2days. Older 'not sent' notes are historical. NoNAVkey
configured. No competition email authorized or sent by assistant. Complete candidate
and clean checks before final access/publication decision. Preserve all priorwork.

---

## Latest continuation — 14 October 2026: real NAV job integration validated

Read `docs/jobs-improvement-20261014.md` and `docs/nav-access-request.md`.
User asked how to improve jobs0; investigated and fixed real adapter gaps.
Live NAV uses `ad_content`, not the old `json` fixture shape. NAV employer IDs often
identify workplaces. Adapter now verifies official BRREG `underenheter/{id}`:
exact child ID, BEDR, not deleted, direct overordnetEnhet matching an input legal
company. No corporate group/subsidiary substitution. Job labels registered
workplace+legal owner, with NAV and BRREG evidence both required by compile_claims.
Candidate name matching tolerates whole-name workplace suffixes/reordering only;
publication remains exact-ID verified. New `scripts/build_nav_candidate_cache.py`
creates a declared bounded hints-only index using permitted NAV_API_TOKEN.
No automatic production public experiment-token fallback.

334 tests pass. Selected 3-company positive controls (all frozen-universe eligible):
ASSEMBLIN AS965808752=1job, OCAB AS916326211=2jobs, ADECCO NORGE AS935333156=14jobs.
**17 live jobs total**, 30 snapshots/51locators audit with zero errors. Real offline
missing-key refresh removes all17 from display, retains private evidence, is
idempotent and audits with zeroHTTP. These are selected hiring positives, NOT
random coverage, a new100 smoke, independent human precision or official score.
Original100 remains14sites/7articles/0jobs. Holdout not deliberately targeted.

Private `out/jobs-improvement-20261014/positive-control-v3/` is the successful
control (includes report/envelopes/profiles/package/refresh-check). Earlier control
attempts failed due to response shape then workplace mismatch; not successes.
`nav-broader/` has a partial30day candidate index:60kchange entries/8354hints,
no candidate-name matches in the existing100+24development inputs. No absence
inference. Public rotating experiment token was memory-only, never persisted.
No Tavily queries or paid API calls in this work. NAV API free; compute etc unpriced.

Prepared unsent NAV consumer application at `docs/nav-access-request.md`. NAV
requires written terms acceptance plus contactemail/phone/person, which remain
user fields. No email/acceptance sent. Optional user_provided NAV_API_TOKEN
requirement saved in draft to pam-stilling-feed.nav.no only; draft save is not
key readiness/publication. After receiving key, enter securely, review/save and
publish. Do not add a required missing key or block core/Tavily workflow.
Tavily remains chosen; Builderr access question still held peruser.
Strategy sources_v9_live_nav_ad_content_and_candidates. Finalcontrol fingerprint
b98393804c380ae1fbff62f7c4d7a97b42aa631e615f6e70701f4e08adcf5973.
Earlier cleanclone325tests predates changes; finalpublishedcommit still needscheck.
No mainrepo commit/push/deployment/submission. Current-code offline100 re-export passes audit, retaining14sites/0jobs with
zeroHTTP; no new100acquisition. Public machine-readable jobs proof is
`docs/jobs-validation-report.json`. Older continuation notes below
are historical. Preserve all earlier work.

---

## Latest continuation — 14 October 2026: fresh 14-site smoke and chosen Tavily configuration

Read `docs/submission-smoke-report.md` / `.json` and
`docs/submission-apis-and-cost.md`. User clarified that chosen APIs should be
declared, and asked to hold the access question while improving. Tavily stays in
the intended configuration; do not remove search or block on outreach. No personal
key is embedded; credential delivery follows forthcoming official instructions.
No LLM is currently used and NAV is optional, with no stable production credential.

Implemented Norwegian definite register label + English registration label,
strict adjacent legal-notice paragraphs (complete legal name, sole labelled ID,
registered street+postal match, narrow DOM locator), deeper contact/legal links,
and XML declaration handling after charset decoding without changing source bytes.
Strategy `sources_v8_legal_notices_and_xml_html`. Four new tests; **325 pass**.
Fresh same-input live100: **14 verified sites** (previous12 retained + AUR STUDIO AS
928022641 and HARD'N HEAVY RECORDS AS 919579269), ten descriptions, 24 outbound
company-declared profiles across nine companies, seven dated company-authored
articles across three companies, zero jobs. 100/100 envelopes, 172.623-second
whole evaluator, 1,171 operations, complete telemetry, no unfinished inputs.
Package audits 448 snapshots/3,164 locators with zero errors. Private artifacts
`out/coverage-next-20261014/smoke-100/`; local viewer under `public/signalpost/`.

94 Basic queries under observed free allowance: preflight Researcher usage303/
limit1000, paygo0; immediate postflight still303 (lagged, not invoice-reconciled).
No paid calls authorized/performed. Paid reference estimate $0.752/100,
$7.52/1000, $8.272/1100, proposed max1100queries/$8.80 (not an assumed official
budget). Both draft and OFFICIAL_RUN now specify chosen Tavily configuration.

Fresh pinned LOCAL verification clone commit e9561f0faeb4377245a61b4d65d193c1f054802c
started empty of venv/tools/out, ran only declared setup, passed325tests+refresh.
Its real registry-only evaluator emits1,511/1,511 synthetic inputs in8.828s with
search flags present and zeroHTTP: structural only, not live scale. Runtime
source fingerprint matches live100: 89070a9256eb80e83bda31505bca06d4cf30785aca5c45d9b6b61e2f161c0e1f.
This local hash is NOT a published submission hash. Main repo/remote unchanged;
all earlier user work preserved. Original holdout untouched. No email, push,
main-repo commit, public deployment or official submission. Final published-commit
check, contact and final-budget configuration remain release steps. Jobs and wider
external discovery remain the highest coverage gaps. Earlier notes are historical.

---

## Current continuation — 14 October 2026: organizer clarifications and NAV candidate cache

Newer than the historical notes below. See `docs/organizer-clarifications-20261014.md`
for the entrant-supplied Discord guidance and confirmed email submission route.
The official batch is currently 1,000 and may grow to 1,100. Model/provider/key/
budget details are forthcoming in official instructions, not reasons to halt
other work. No closed external field-family list. Search is candidates only.

Optional NAV candidate cache is wired through both CLIs and the shared pipeline.
`--nav-cache-input` and `--nav-cache-output` require `--nav-jobs`. Metadata-only
index, explicit provenance hash/times, bounded 50k rows/32MB, every ad live-checked
and exact-employer matched. No output reuse or personal credential requirement.
Missing/invalid cache falls back to discovery; missing token publishes no jobs.
Nine new focused cache tests pass. Final regression/structural results are in
`docs/nav-candidate-cache-20261014.md` once completed. Earlier 312-test clean clone
is historical; validate the final published commit before sending anything.

Submission draft updated at `docs/first-submission-draft.md`; request draft revised
at `docs/builderr-runtime-access-request.md`. No email, main-repository commit,
push, deployment or official submission was performed. Current live baseline
remains 12 verified sites, seven company-authored articles and zero jobs per 100.

---

# Signalpost handoff — 11 October 2026

## Cloud development update — 12 October 2026 (latest)

Latest continuation — 14 October, official traps and NAV integration: read
`OFFICIAL_RUN.md` and `docs/nav-and-evaluator-readiness-20261014.md`. User supplied
official guidance: dynamic runtime companies, growing batch, one command, clean
install and organizer-supplied model/API access; personal third-party keys cannot
be the official dependency. Prepared (not sent) the requested clarification in
`docs/builderr-runtime-access-request.md`; provider/model/tool/budget remain unknown.
Optional NAV adapter is implemented with shared bounded scan, exact employer/UUID,
fresh dates/status, safe URLs, auditable JSON, prior-ID revalidation and removal
of unconfirmed ads from current/public display while retaining private evidence.
It requires evaluator `NAV_API_TOKEN`; no production public-token fallback.
Default recent-update window is seven days with explicit incomplete coverage;
no cross-run index. Live private check: 12,000 entries/12 pages, records for all
124 development inputs, zero matching candidates; not a live job-coverage gain.
Strategy `sources_v6_optional_shared_nav_jobs`. **312 tests**, declared install
and refresh pass in a fresh pinned local clone without venv/tools/out. Fixed
read-only-home uv/pip caches using ignored project-local defaults. Fixed unknown
JSON wrapper silently becoming an empty batch. Actual evaluator emits 1,511/1,511
fresh synthetic runtime inputs in order with keys empty and NAV unavailable;
one registry-missing input retained, audited package accepted, no HTTP. This is
structural verification, not official-scale network performance. Isolated local
validation commit `8f05a66947dafa50687a821ffe89339ede9b0f0e` is NOT a published GitHub
hash; actual repo/remote remain at original HEAD with all user changes preserved.
Current code fingerprint matches the clean clone. No paid calls, deployment,
user-repo commit, push or submission. Need Builderr's runtime/credential answers,
score-relevant coverage work, then eventual exact published-commit verification.
Original holdout untouched. Prior continuation entries below are historical.

Latest continuation — 14 October, discovery gaps improved: read
`docs/discovery-improvements-20261014.md`. Final same-input 100-company acquisition
supports **12 websites** (all previous ten plus Eiklid Rusten and BB Media), seven
company-authored articles across three companies and zero jobs. Whole evaluator
178.895 seconds; 1,218 operations; $0 estimated paid APIs. **299 tests** pass.
Final current-code offline export/package under
`out/discovery-gaps-release-20261014/` audits 437 snapshots/3,147 locators with no
errors; use its package and local public sample. Browser and refresh checks pass.
Strategy `sources_v5_search_fallback_and_legal_blocks`: robust org-label
punctuation, compact legal-ID paragraphs, one capped search after failed
registry/email candidates, more directory exclusions, dated labelled HTML jobs,
bounded gzip HTML and robots decoding while preserving original evidence bytes.
Separate final development24 emits all inputs: six sites/four articles/zero jobs.
The NFS compressed page verifies/audits offline from retained bytes, but its fresh
robots endpoint returned 503; it stays blocked in live counts. A shortened-query
experiment was reverted after losing a valid candidate. The original holdout
remains untouched. NAV's documented public-token experiment **works**; six pages
contain 6,000 entries but zero exact-name candidates for these 124 inputs, so no
job claims. See `docs/nav-job-feed-research.md`: next is a shared feed index,
exact-employer checks, explicit incomplete scans, withdrawal handling, stable
consumer credentials and measured official-scale budgets. No NAV production
connector, paid budget, deployment, commit, push or submission. Qualification
and official score remain unmeasured. Prior entries below are historical.

Latest continuation — 14 October, authenticated smoke complete: published network
and `TAVILY_API_KEY` are ready. Read `docs/tavily-smoke-20261014.md`. Same frozen
100-company input completed in **162.751 seconds**, with 100 terminal envelopes,
complete telemetry and no unfinished companies. Reviewed results: **10 verified
websites, seven dated company-authored articles across three companies, zero
jobs**, versus the prior six sites/four articles. One property-manager website
was wrongly accepted during acquisition; the new footer legal-contact-owner gate
rejects it. Use `out/tavily-smoke-20261014-reviewed/package/`, never the raw package.
Offline corrected export: 432 snapshots, 3,137 locators, zero errors, zero new
HTTP. **286 tests**, refresh and the local 100-profile viewer pass. Free Researcher
allowance was verified before the bounded run; estimated paid API cost is $0.
Provider usage still reports zero, so nominal credits are not a verified invoice
or remaining balance. No paid-budget authorization, holdout crawl, deployment,
GitHub push or official submission. Coverage remains too limited to infer 65/100.
Next: broaden exact-company discovery and supported jobs/external field families;
measure official-scale resources and obtain the official budget before release.
Older continuation entries below are historical, including their missing-key state.

Latest continuation — 14 October: unrestricted networking is **enforced**, DNS
flag ready, and provider pricing/terms are verified. Read
`docs/search-provider-research.md` first. Recommend Tavily Basic free Researcher
(1,000 monthly credits, no card). Optional Tavily integration is implemented;
**283 tests**, refresh and private evidence audit pass. Four bounded anonymous
queries produced one newly verified company site and three 2026 company-authored
posts; unresolved matches stay ambiguous. This is private development with reused
registry evidence and unmeasured company runtime, not a fresh 100-company run.
Original holdout untouched; $0 paid cost. Local 100-profile viewer is refreshed
under `out/provider-research-20261014/local-public-refresh/signalpost/`, not deployed.
`TAVILY_API_KEY` requirement is saved, scoped to api.tavily.com, still missing.
User needs the free-plan key in environment settings (PAYG disabled), save/publish;
then verify and run the bounded same-input 100-company test with price/cap 0 and
max 100 queries. Production has no anonymous default. Brave/Serper remain unused;
current terms concerns are documented. No push or official submission. Earlier
13 October smoke results below are preserved; do not add the private trial to
those results and call it another full live batch.

Latest user priority — improve before the first official entry. Read
`docs/score-improvement-20261013.md` and `docs/search-provider-research.md` first.
Same-input 100-company run: **127.498 seconds, 661 requests, six verified sites,
four dated company-authored articles across two companies, zero jobs, 60
comparable annual revenue explanations, $0 paid APIs**. All envelopes and the
421-snapshot/3,116-locator package audit pass. Locked clean-source installation
passes **274 tests**; refresh and Chromium public-sample checks pass. Public
100-profile HTML is local under `out/score-improvement-20261013/public/signalpost/`.
Optional capped Brave discovery is implemented but disabled; no key/budget/terms
verification or live search test. Five pricing/terms domains are saved in the
environment draft and require save/publication before current-price research.
Current strategy: `sources_v4_discovery_and_crawl`. Holdout remains untouched;
code is uncommitted, no GitHub push or official submission. Earlier baseline
records below are preserved history, not the current release status.

First smoke complete — 13 October: read `docs/first-smoke-report.md` and JSON.
100/100 envelopes, no unfinished companies, 596.945-second whole evaluator,
$0 paid APIs. Both public-universe hashes verified; prior 48 diagnostic IDs and
known holdout domains excluded. Final reviewed export: four accepted websites,
no dated jobs/news, 411 snapshots and 3,101 locators with zero audit errors.
Raw acquisition initially accepted five; precision review tightened shared-brand
identity proof, contact citation spans and appointment/careers classification.
Re-export uses retained bytes with zero new HTTP; separate fingerprints recorded.
**245 tests and locked install pass in a fresh source copy**. Actual runtime code
matches that verified copy. The draft first submission is saved in
`docs/first-submission-draft.md`; next steps are reviewed code publication, exact
commit/clean-clone validation and explicit submission authorization. Code remains
uncommitted; no official score or qualification. Do not wait for optional APIs.

Newest update — 13 October: DNS compatibility is integrated; read
`docs/dns-integration-20261013.md`. **242 tests pass**. With the command-local
`SIGNALPOST_DNS_OVER_HTTPS=1` flag, the two-company live run acquires registry
evidence for both and verifies one real website. Five snapshots/20 locators audit
with zero errors. This supersedes the blanket live-DNS blocker below. The second
site redirects to www.nordicform.no and remains unresolved; no dated jobs/news in
the small run. The environment draft suggests the flag and adds the resolver and
observed redirect domain. Publish integrated changes/settings for future tasks;
the fresh 100-company smoke and official submission remain pending.

Latest integration: all three separate-chat patches are now applied in this
coordinator checkout. Read `docs/integration-review-20261012.md` first. **205 tests
pass**, including integrated timeout, live-runner and review-packet checks; refresh
and packaged dated-event evidence audits pass. A fresh proxy registry request now
succeeds, but local DNS still fails and the actual crawler produces failure
envelopes. Required domains are already listed: diagnose/restore executor DNS,
not another duplicate allowlist save, before the fresh 100-company smoke. Preserve
the uncommitted integrated changes before restarting/restoring the environment.

Current user priority: reach a first valid submission and official result quickly,
then improve through revisions. Use `docs/first-submission-plan.md` for the release
checklist and baseline cost declaration. The three workers' reports are now in
`docs/task-results/`; their original live artifacts were not transferred, and the
coordinator has rerun the bounded live check. Do not
wait for every planned connector; preserve required live smoke and validity checks.

Read `docs/parallel-work-report.md` and `docs/dated-events-progress.md` for cloud
changes after the historical local continuation below. Work is now in the existing
`/workspace/signalpost-starter-kit` checkout; preserve the uncommitted changes.

- Portable cited-evidence packaging, a single evaluator wrapper, offline reviewed
  strategy comparisons, and opt-in Wikidata candidates are implemented.
- Dated news/jobs now follow opaque same-host content-card links, extract scoped
  DOM metadata, and audit exact dates/employer fields or JSON-LD pointers.
- Job expiry uses snapshot time; failed refresh retains prior supported facts.
  Strategy is `free_sources_v3_dated_events`; **163 regression tests pass**.
- Synthetic before/after: 0 to 2 dated news items on one fixture company and 0 to
  1 job on another, with wrong-owner/employer negatives rejected. This is not a
  live gain, independent review, or official score.
- Two real development-site attempts failed DNS; proxy checks returned HTTP 403.
  Narrow registry/site domain additions were saved to the environment draft but
  are not applied/published. Details and retry scope are in the dated-events doc.
- Independent labels, complete host separation, real coverage measurements,
  resource-budget validation, and a fresh 100-company live smoke remain pending.
  Holdout is untouched. No paid calls, submission, commits, or publication.

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
