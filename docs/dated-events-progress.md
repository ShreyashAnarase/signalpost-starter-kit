# Dated jobs and news milestone — 12 October 2026

The integrated packaging/evaluation/discovery changes passed the initial
155-test regression suite. The dated-event milestone adds eight regression tests;
all 163 now pass. The bundled refresh replay remains idempotent, finds both
expected changes, and reports no false changes. No competition score is claimed.

## Changes

- News/careers index content cards may lead to opaque same-host detail URLs. The
  source family is carried only through article/heading links outside navigation,
  headers and footers. Existing page/request/deadline budgets still apply.
- Individual HTML articles with a single headline and scoped ISO date can produce
  news claims without JSON-LD. Publication meta tags are supported when an article
  body is established. Careers DOM extraction additionally requires explicit
  employer metadata that passes the legal-name gate.
- JSON-LD events preserve an exact script index and JSON pointer; DOM events
  preserve exact positional selectors and date/employer attributes. Offline audit
  checks the recorded fields, not just that a headline appears somewhere.
- Index cards, undated/future articles, offsite DOM canonicals, unrelated employers
  and group-name mismatches abstain. Expiry is compared with snapshot retrieval
  date rather than today's clock. Replaying old bytes is deterministic; a failed
  refresh preserves prior jobs as last known rather than deleting them.
- Page-navigation claims use a real title/heading span, and are omitted if none
  exists, instead of citing a URL that may not appear in retained HTML.
- Strategy version is `free_sources_v3_dated_events` so changed extraction is
  identifiable. Source/config fingerprints continue to protect resume.

## Before/after evidence

The same three **synthetic company fixtures** were run through the captured old
extractor and the new extractor. This is not live coverage, independent human
precision, population recall, or the organizer's verified reference pool.

| Fixture outcome | Baseline | Current |
| --- | ---: | ---: |
| Companies with dated news | 0 | 1 |
| Dated news claims | 0 | 2 |
| Companies with a dated job | 0 | 1 |
| Dated job claims | 0 | 1 |
| Simulated page reads | 5 | 9 |

The extra four reads fetch the previously missed detail pages. The other employer
and conflicting legal owner are rejected. Three envelopes, eight snapshots, and
11 evidence locators pass audit with zero errors. The new event locators also pass
after packaging, relocation, and deletion of acquisition originals in tests.
No third-party cost or external fixture requests occurred.

Artifacts in ignored `out/dated-events-review/` include captured baseline code and
envelopes, `comparison.json` with fixture/code hashes, current envelopes and
portable package, package audit, refresh replay, and the live-access report.
Tracked fixture: `tests/fixtures/dated-events-sites.json`.

## Live validation blocker

A bounded attempt used only NORVIGROUP NORSK DUN AS (985215294, www.nf.no) and
NORSK FARMASØYTISK SELSKAP (984589344, www.nfs.no) from the development set.
Both failed hostname resolution before an HTTP request. Follow-up proxy requests
to company robots and official identity API returned CONNECT HTTP 403. No live
profiles, dates, coverage gains, or absence conclusions were established.

The environment draft now adds only `data.brreg.no`, `www.nfs.no`, and `www.nf.no`
to the existing custom allowlist while preserving selected presets. Saving the
draft did not change current runtime access or publish the environment. Review and
save the additions in environment settings, then publish; retry the same bounded
operation afterward. DNS/proxy readiness must be verified rather than assumed.
Redirect destinations may need additional narrowly scoped rules if observed.

## Next development work

1. Retry bounded development acquisition after network configuration is active.
   Use retained identical bytes for baseline/challenger comparison where possible;
   retain exact legal-owner checks and audit every added event.
2. Obtain independent human identity/claim labels and establish opportunities for
   unresolved companies. Successful-output review alone cannot measure recall.
3. Broaden extraction only from observed failures: localized visible dates,
   sitemap indexes/feeds, graph-referenced employers, and permitted external ATS
   routes remain unsupported or limited. Do not silently relax employer matching.
4. Validate complete execution budgets, then run a fresh audited 100-company live
   smoke. The holdout remains untouched; these tests do not validate it.

All existing uncommitted work was preserved. No paid APIs, credential collection,
submission, Git commits, or publication were performed.
