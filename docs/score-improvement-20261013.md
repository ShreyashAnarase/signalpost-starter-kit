# Measured improvements — 13 October 2026

The same frozen 100-company smoke input now completes in **127.498 seconds**,
with **100 terminal envelopes**, complete telemetry, no unfinished companies and
an accepted evidence package. This is local measurement, not an official score.
The input, registry snapshot, workers and six-page/request/time budgets match the
earlier completed 100-company acquisition; fresh source retrieval times differ.

| Measure | Earlier reviewed baseline | Improved live run |
| --- | ---: | ---: |
| Whole evaluator runtime | 596.945 s | 127.498 s |
| Budgeted requests, including DNS | 1,796 | 661 |
| Verified websites | 4/100 | 6/100 |
| Company-authored dated articles | 0 | 4 across 2 companies |
| Supported job postings | 0 | 0 |
| Companies with supported revenue | 90 | 90 |
| Comparable annual revenue explanations | 0 | 60 |
| Paid API cost | $0 | $0 |

The improved run audits **421 snapshots and 3,116 evidence locators**, with zero
errors. Company runtime p50/p95 is 6.415/17.361 seconds; maximum is 25.378 seconds.
The API cost excludes hosting, compute, storage and transfer. The current source
also generates a local browsable 100-profile sample with search, financials,
activity, people, workplaces and source navigation.

## Why it improved

- Recognize `Organisation number`, `Organization number` and `NO … MVA` in legal
  footers. PROPLAN AS and MOST LIKELY NO REASON FOR HYSTERIA AS now resolve through
  their exact organisation numbers. Wrong legal owners still cause abstention.
- Share successful HTTPS DNS validation inside a run, bounded by both answer
  families' TTLs, negative SOA minimums and a maximum of 60 seconds. Failed/local
  DNS answers are never cached. URL, proxy, redirect, robots and TLS checks remain.
- After verifying ownership, alternate news/careers pages and their detail
  links. Preserve the publisher's detail-link order and avoid spending the
  entire crawl budget on contact/privacy pages. Encode Norwegian URL paths.
- Parse explicitly labelled Norwegian publication dates on individual article
  pages with a same-host parent breadcrumb. Dates in body prose, image URLs,
  footers, deadlines and ambiguous indexes do not become publication dates.
- Preserve the accounts scope on currency claims. Revenue comparisons require
  consecutive comparable annual periods, one unambiguous value for each period,
  matching currencies/scopes, current evidence and a positive prior denominator.
  Explanations cite both amounts and currencies; original financial claims remain.
- Show the latest captured article and its date. Company-authored publications
  remain distinct from independent sentiment. Jobs with an unresolved legal
  employer or required dates remain unavailable.

Three of the four captured posts are historical psychology articles dated 2017,
2018 and 2025. The fourth is Proplan's 9 September 2026 publication. These are
dated publications, not four recent news events or independent press coverage.
Six accepted websites were inspected by the assistant; this is not independent
human precision review. Availability remains explicit for every other company.

## Validation and provenance

A fresh source copy at `/workspace/verification/signalpost-improved-20261013`
installs through the existing locked setup and passes **274 tests**, including
DNS expiry/private-answer checks, transient API storage, spending caps, mixed
account scopes, malformed evidence, and HTML script-injection regressions.
The final display-formatting change also passes the three focused showcase tests.
Chromium checks confirm all 100 profiles render, search/selection works,
financial tables populate, evidence navigation works and empty search is handled,
with no JavaScript runtime exceptions. This is a source-copy check, not a remote
clean-clone check at an unpublished commit.

The offline refresh reports both expected changes, no false changes and an
idempotent rerun. `git diff --check` passes. The smoke snapshots and baseline
outputs are preserved. A final export after display-formatting changes makes
zero new HTTP requests, records acquisition/export fingerprints and passes the
same evidence audit. The verified source copy matches the current runtime source.

Ignored evidence/artifacts:

- `out/score-improvement-20261013/release-smoke/`: final live profiles, envelopes,
  metrics, snapshots and accepted evidence package.
- `out/score-improvement-20261013/reviewed-final/`: offline audited export.
- `out/score-improvement-20261013/public/signalpost/index.html`: public sample
  artifact, generated locally; no site has been deployed.
- `out/score-improvement-20261013/improvement-report.json`: machine-readable
  comparison and validation provenance.
- `out/score-improvement-20261013/provider-research/`: retrieved provider SDK
  documentation. Provider pricing/terms requests remain blocked by the current
  network allowlist; documentation-domain additions are saved for review.

## Next scoring gap

Most inputs still have no website candidate. Six verified sites and zero jobs
remain low external coverage. The optional Brave API discovery path is implemented and
tested offline, with shared query/spending caps, transient search results and
independent exact-company page verification. It is **disabled**: no key, paid
budget, provider terms verification or live search evaluation has been completed.
See [provider research](search-provider-research.md). A provider comparison on
frozen development inputs is the next coverage experiment; the original holdout
remains untouched.

The user has chosen to improve before the first official entry because earlier
daily batch scores remain in the final mean. No GitHub publication or official
submission occurred. The official reference pool and resource budget remain
unknown; these results do not establish 65-point qualification or official-scale
completion. The larger-batch runtime still needs measurement under that budget.
