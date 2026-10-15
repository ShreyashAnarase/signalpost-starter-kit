# First-entry smoke — 15 October 2026

Fresh acquisition on the current implementation produced **100/100 terminal
envelopes, 14 verified websites, seven company-authored articles across three
companies, and zero verified jobs**. NAV is disabled in the intended first entry.
This is a local smoke result, not an official score or independent human review.

| Measure | Result |
| --- | ---: |
| Whole evaluator, including packaging | 173.707 seconds |
| Budgeted operations including DNS | 1,190 |
| Received bytes | 72,264,482 |
| Company runtime p50 / p95 | 8.750 / 25.738 seconds |
| Tavily Basic attempted queries | 94 |
| Estimated local paid API fees | $0 |
| Evidence snapshots / locators audited | 448 / 3,164 |
| Audit errors / unfinished companies | 0 / 0 |

All 14 prior verified sites are retained. The acquisition/package is privately
retained at `out/first-entry-20261015/smoke-100/`. Public aggregate measurements
and provenance are in [submission-smoke-report.json](submission-smoke-report.json).
Runtime source SHA-256: `b98393804c380ae1fbff62f7c4d7a97b42aa631e615f6e70701f4e08adcf5973`.

The acquisition used the full-row frozen local input (SHA-256
`41d064e6c82e2e8c56627a4ecf51917c582ed629cc1b2ac38701e0fdd25a67a3`).
[The public reproduction input](first-smoke-input.jsonl) contains the same ordered
100 organisation numbers, SHA-256
`4664ca34c48814851f1601a00a70f1d54aa988197677abd13d8d2f14da9464bb`.
Optional name annotations are ignored by the evaluator. Neither is an official
evaluation batch. Identity uses the frozen registry CSV with
SHA-256 `511f437caeccc62aa75c3208b3eaa6db6f5f697cc4a4db70806796a754bc8fca`.
The original separate holdout was not targeted. No missing financial value was
silently converted to zero, and unverifiable websites/jobs remain explicit states.

## Run and cost

Install: `bash scripts/setup_codex_cloud.sh` (Python 3.12+, Linux/POSIX).
The intended official command is in [OFFICIAL_RUN.md](../OFFICIAL_RUN.md).
This smoke uses the same source/crawl/timeout settings, with a 100-query cap and
explicit zero price/spending limit inside the observed free local allowance.
The official configuration declares a conservative paid-rate budget; it does not
assume the entrant's free tier. No key appears in the repository.

At the checked $0.008/Basic-query reference rate, 94 queries imply
**$0.752/100 companies**, about **$7.520/1,000** or **$8.272/1,100** if
composition is similar. The intended cap is 1,100 queries/$8.80, subject to the
shared official budget. These are estimates, not invoices or measured official
batches. Compute, hosting, storage and transfer are excluded. NAV adds no
requirement to the first-entry command. No model is currently used.

Preflight reported a Researcher plan with 396/1,000 credits used and zero
pay-as-you-go usage, allowing the bounded 100-query local test. Usage readings
have lagged attempts; they do not verify invoices or disabled billing settings.
Current provider pricing and the evaluation contract were fetched on 15 October.

## Validation and sample

**334 regressions pass** on this implementation. Real NAV positive controls
(17 ads for three selected companies) and their workplace proofs are documented
separately in [jobs-improvement-20261014.md](jobs-improvement-20261014.md); they are
not added to this sample or enabled in the first command. Final exact-commit
clean-clone results are recorded in the release manifest accompanying submission.

The static 100-profile product sample is included at `signalpost/index.html`,
ready to be served under `/signalpost/`. It exports no raw snapshots. Source
links/quotes, identity, availability and refresh information are retained in the
viewer. Preparation of that artifact does not establish public hosting.

Coverage remains narrow, independent human precision/recall and the official
score are unknown, and a live 1,000–1,100-company budget has not been validated.
Refresh directly from a relocated portable package remains unsupported; raw
prior envelopes and retained snapshots support refresh. See
[API/licence declarations](submission-apis-and-cost.md) for access and fees.
