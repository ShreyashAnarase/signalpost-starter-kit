# Reviewed 100-company smoke — 14 October 2026

The published environment works with authenticated, opt-in search discovery.
The same frozen 100-company input completed with one terminal envelope per input,
no unfinished companies and complete telemetry. The corrected evidence package
passes its contract, snapshot-integrity and locator checks. This is a local run,
not an official score or independent precision measurement.

| Application measure | Previous reviewed run | Current reviewed run |
| --- | ---: | ---: |
| Terminal envelopes | 100 | 100 |
| Verified company websites | 6 | 10 |
| Dated company-authored articles | 4 across 2 companies | 7 across 3 companies |
| Supported job postings | 0 | 0 |
| Companies with supported revenue | 90 | 90 |
| Whole evaluator runtime | 127.498 seconds | 162.751 seconds |
| Budgeted outbound operations, including DNS | 661 | 1,296 |
| Estimated paid API cost | $0 | $0 |

Both runs use the same frozen input and registry bulk snapshot. Fresh external
retrievals differ; this is an overall application comparison, not a controlled
search-provider performance benchmark. API cost excludes compute, storage,
hosting and transfer. Monthly free credits are shared across runs.

## Attribution review

Four additional accepted sites belong to Hurum Elektro, Varanger KraftFiber,
Piperehabilitering and Bø Taxi. The assistant inspected their retained identity
evidence; this is not independent human review. Three added articles are Varanger
KraftFiber publications dated 6 August, 1 June and 22 May 2026. Company-authored
content is distinct from independent news or sentiment. Three earlier psychology
articles are historical, dated 2017, 2018 and 2025.

The raw acquisition also accepted a property-manager website for LUNDETANGEN
KONTORPARK AS based on its property heading and shared address. Its footer contact
block names Hjørnekontor AS. A new ownership check now rejects that conflicting
legal contact owner; the corrected export marks the website and dependent claims
ambiguous. Designer credits elsewhere in a footer do not trigger this check.
The raw package is retained for diagnosis and must not be submitted.

## Validation and retained artifacts

- All **286 regression tests** pass, including the conflicting-owner case and
  valid footer contact blocks with unrelated designer credits.
- Corrected offline export and portable package audit **432 snapshots and 3,137
  evidence locators** with zero errors. Re-export makes zero HTTP requests and
  records separate acquisition and export source fingerprints.
- Deterministic refresh finds both expected changes, no false changes, and an
  idempotent rerun. These fixture results are not measured live refresh accuracy.
- The local public sample contains 100 profiles. Chromium checks rendering,
  search/selection, financial tables, source navigation and empty search with no
  JavaScript exceptions. The sample has not been deployed.

Ignored local artifacts:

- `out/tavily-smoke-20261014/`: immutable original acquisition and telemetry.
- `out/tavily-smoke-20261014-reviewed/package/`: corrected audited package.
- `out/tavily-smoke-20261014-reviewed/public/signalpost/`: local public sample.
- `out/tavily-smoke-20261014-reviewed/comparison.json`: comparison and provenance.
- `out/tavily-smoke-20261014-prep/`: private, sanitized account/quota checks.

The account preflight reported a free Researcher plan with 1,000 unused credits.
The fixed Basic-depth probe and run together were capped at 101 requests, within
that observed allowance. Paid API spend is estimated at $0. Subsequent account
usage still reported zero; credit consumption, the remaining balance and final
billing are not independently reconciled. Pay-as-you-go being disabled was not
verified. No paid spending or larger daily-run funding is authorized.

## Remaining release gap

Ninety companies still lack a verified website, job coverage is zero, and
independent external field families remain sparse. Availability and ambiguous
matches are explicit; abstention is not coverage. The original holdout remains
untouched. No score estimate establishes the 65-point qualification threshold.

Next work should improve exact-company discovery, supported jobs and external
field coverage, then measure larger-scale completion against Builderr's actual
resource budget. The free monthly allowance does not establish sustainable
daily official-run capacity. Code remains uncommitted; no GitHub push or official
submission has occurred.
