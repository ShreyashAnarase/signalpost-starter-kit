# Discovery and extraction improvements — 14 October 2026

The latest same-input live smoke supports **12 verified websites**, up from ten
in the preceding reviewed run. All ten previous sites remain supported. Two new
matches have exact legal-number evidence: Eiklid Rusten's privacy policy and
BB Media's footer. Assistant review is not independent human precision review.

| Application measure | Previous reviewed smoke | Current reviewed smoke |
| --- | ---: | ---: |
| Terminal envelopes | 100 | 100 |
| Verified company websites | 10 | 12 |
| Dated company-authored articles | 7 across 3 companies | 7 across 3 companies |
| Supported jobs | 0 | 0 |
| Companies with supported revenue | 90 | 90 |
| Whole evaluator runtime | 162.751 seconds | 178.895 seconds |
| Budgeted operations including DNS | 1,296 | 1,218 |
| Estimated paid API cost | $0 | $0 |

The input, registry bulk snapshot, workers and page/request/time budgets match.
External bytes and retrieval times differ. These are application measurements,
not a controlled provider benchmark. Compute, hosting, transfer and storage are
excluded from the API estimate. The free allowance is monthly, shared across
runs; provider usage has not been reconciled to an invoice.

## Implemented changes

- Accept the common `Org. nr.:` punctuation without treating an arbitrary phone
  number or unlabelled number as legal identity evidence.
- Recognize compact contact/legal paragraphs containing the full legal company
  name and its sole labelled organisation number. Cite the exact DOM paragraph;
  conflicting footer owners and multiple legal IDs still cause abstention.
- After every registry/email candidate fails, perform one optional capped search
  within the existing company and shared spending limits. Do not revisit an
  already attempted domain through the fallback. Existing verified candidates
  consume no search query.
- Exclude additional observed directories and social/video platforms before they
  consume the three company-site candidate slots. Search results remain transient
  candidates, never claim evidence.
- Extract job advertisements with explicit employer/publication/deadline labels
  in plain HTML. Preserve the original labels and DOM locators. Missing dates,
  future dates, conflicting employers/dates, expired deadlines and generic
  careers indexes remain rejected. This behavior is tested; it has not increased
  observed live job coverage on these inputs.
- Decode gzip HTML consistently during extraction and audit, bounded to 8 MB,
  while retaining original compressed bytes/hashes. Compressed robots rules are
  decoded too; corrupt compressed rules block crawling. Retained real evidence
  from Norsk Farmasøytisk Selskap now extracts and audits correctly offline. A
  fresh retry returned HTTP 503 from its robots endpoint, so the live result
  remains blocked rather than claiming another accepted site.

Strategy is `sources_v5_search_fallback_and_legal_blocks`. Source/config
fingerprints prevent silently resuming another implementation. The final job
index guard and compressed-HTML support were validated after the 100-company
acquisition through offline re-export with separate source fingerprints; this
is not another live 100-company acquisition.

## Verification and artifacts

All **299 tests** pass, including evidence tampering, wrong-owner cases, query
fallback, compressed robots denial, corrupt/oversized compression and job-date
negatives. The corrected 100-company package audits **437 snapshots and 3,147
locators** with zero errors. Offline refresh and the local browser sample pass.
The input hash remains
`41d064e6c82e2e8c56627a4ecf51917c582ed629cc1b2ac38701e0fdd25a67a3`.

The live acquisition used this evaluator command with the existing verified bulk
snapshot and a fresh output directory. Price/cap zero applies only inside the
verified free-account allowance; check the remaining allowance before repeating.

```sh
.venv/bin/python scripts/evaluate_signalpost.py \
  --organisations out/first-smoke-prep/smoke-companies.jsonl \
  --bulk out/first-smoke-prep/brreg-enheter.csv \
  --output-dir out/discovery-gaps-reproduction --run-id discovery-gaps-reproduction \
  --expected-count 100 --workers 8 --deadline-seconds 1500 \
  --company-timeout 150 --request-timeout 15 --max-pages 6 --max-requests 60 \
  --search-provider tavily --search-max-queries 100 \
  --search-price-per-1000 0 --search-budget-usd 0 \
  --evaluator-timeout-seconds 1800
```

Local ignored artifacts:

- `out/discovery-gaps-final-20261014/`: final fresh acquisition and telemetry.
- `out/discovery-gaps-release-20261014/package/`: final corrected audited package.
- `out/discovery-gaps-release-20261014/public/signalpost/`: local public sample.
- `out/discovery-gaps-release-20261014/comparison.json`: comparison/check provenance.
- `out/discovery-gaps-dev24-final-20261014/`: separate development acquisition.
- `out/discovery-gaps-20261014-prep/`: sanitized free-quota checks and NAV research.

The original holdout remains untouched. This is not an official run, measured
official recall or a qualification estimate. A local sample is not deployed.
No repository commit, GitHub push or competition submission occurred.

The separate 24-company development run completes every envelope with six
verified sites, four articles for one company, and zero jobs. Innlandet Maskin is
newly supported by its name and registered address; Norsk Farmasøytisk Selskap is
blocked in this fresh run. This stratified sample and its eight-page budget are
not comparable to the random 100-company smoke's six-page budget. The retained
compressed-page review makes zero HTTP requests and separately audits five
snapshots/37 locators; it is not added to the live counts.

## Next scoring gap

Website and external-field coverage remain limited. The strongest newly verified
source opportunity is [NAV's free official job feed](nav-job-feed-research.md).
Its authenticated experiment access works, but the bounded partial scan produced
no exact-company jobs and no production connector is enabled. Implement one
shared feed index and exact-employer checks, including withdrawal handling,
before treating it as scoring coverage. Stable official-run access and the
organizer's actual resource budget remain necessary for a release decision.
