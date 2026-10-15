# Submission APIs, licences and estimated cost

Intended configuration: Tavily-assisted candidate website discovery plus direct
permitted registry/company-source acquisition. No LLM is currently used. No
personal credential is embedded in the code. Runtime credentials must follow the
organizer's official instructions. The user has held the access question while
we continue development; no outreach is required or authorized here.

| Service | Purpose | Credential | Source/licence basis |
| --- | --- | --- | --- |
| BRREG / Regnskapsregisteret | Identity, accounts, roles, group/subunit records | Public API; supplied frozen registry for identity | Official-source conditions; bulk NLOD 2.0 as declared in source map |
| Tavily Basic Search | Find candidate company websites | `TAVILY_API_KEY` | API service terms; result bodies/snippets not retained or published |
| Verified company websites | Direct evidence for business, links, dated news/jobs | Usually none | Source rights and robots/access policy; no blanket redistribution licence asserted |
| Google Public DNS | Optional public-address validation when local DNS fails | None | Public resolver service; technical dependency, not company claim evidence |
| NAV official feed | Optional exact-employer jobs, disabled in intended command | `NAV_API_TOKEN` | Official feed terms, permitted access, live detail verification and ad removal |

Brave/Wikidata adapters are implemented but are not enabled in the intended
configuration. Social platforms are not scraped; a verified site's outbound link
is labelled as a company-declared link, not an independently verified account.
See `search-provider-research.md`, `nav-job-feed-research.md`,
`external-connectors.md` and `../OFFICIAL_RUN.md` for terms/access details.
Dependency declarations/lockfile are authoritative for installed packages. Core
third-party metadata includes MIT/BSD/Apache licences. The repository has no
project licence file; no broader source-code licence grant is invented here.

## Conservative fee model

Tavily Basic uses one credit/query. Official pricing checked again 15 October 2026:
https://docs.tavily.com/documentation/api-credits — advertised pay-as-you-go price
$0.008/credit. Price and terms must be rechecked before freezing. API search depth
is explicitly Basic; automatic depth, generated answers, images and provider page
extraction are disabled. Client reservations count failed attempts conservatively.

The intended evaluator command in `../OFFICIAL_RUN.md` reserves at most 1,100
queries and $8.80 of search fees at that paid rate. This does not fix the company
count: all supplied companies still receive envelopes, and the query limit is a
shared budget. Registry candidates verified without search consume no query.
The actual common official resource/API budget is not yet known; adjust these
limits before freezing if needed. No paid command was executed or spending
permission inferred from this declaration.

Latest measured search-enabled sample: **94 attempted queries for 100 companies**
([smoke report](submission-smoke-report.md)). At the paid rate that would cost
**$0.752**, or **$0.00752 per company**. A proportional planning estimate is
**$7.52 for 1,000** or **$8.272 for 1,100** companies. These are extrapolations,
not official-batch measurements. Composition, failures and the shared cap change
actual usage. Do not describe the reference-rate estimate as a provider invoice.

Before the first-entry run on 15 October, the local endpoint reported Researcher,
a 1,000-credit limit, 396 plan credits used and zero pay-as-you-go usage. The local 100-query cap fit
that reported free allowance with explicit price/cap zero. Earlier usage readings lagged attempts, so the endpoint does not by itself
reconcile the 94 attempted queries or verify an invoice. Billing settings are not verified by that endpoint.
Free credits are monthly/shared, not an official daily-run pricing assumption.

No other paid API is enabled. These fee figures exclude CPU, hosting, storage,
network transfer and evidence retention. Report those resources separately.
