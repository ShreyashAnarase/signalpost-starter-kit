# Search provider recommendation — 14 October 2026

**Start with Tavily Basic Search on the free Researcher plan.** It supplies
1,000 monthly credits without a credit card, each Basic search uses one credit,
and the first live anonymous development experiment works. This is a practical
first-test recommendation, not a measured claim that Tavily is the best search
engine. Account access is now configured and verified; search stays opt-in.

Latest application results and strategy changes are recorded in
[the discovery improvement report](discovery-improvements-20261014.md). The full
legal-name query is retained; a shorter-name experiment lost a valid candidate
and was reverted. Candidate search also runs once after registry/email candidates
fail, without revisiting their domains or relaxing publication evidence.

The published cloud network is now unrestricted and enforced. Provider pricing
and terms pages load successfully. Source snapshots, hashes and retrieval times
are retained privately in `out/provider-research-20261014/`.

| Provider | Verified free allowance | Standard advertised paid price | Nominal 100 / 1,000 / 1,500 one-query profiles, before free allowances |
| --- | --- | --- | --- |
| Tavily Basic | 1,000 credits/month; no card required | $0.008/credit on pay-as-you-go; Basic = 1 credit | $0.80 / $8 / $12 |
| Brave Search | $5 monthly credits; card required | $5/1,000 requests | $0.50 / $5 / $7.50 |
| Serper Starter | 2,500 free queries; no card required | $50 prepaid for 50,000 queries ($1/1,000) | $0.10 / $1 / $1.50 amortized; $50 minimum purchase |

These are price calculations, not invoices or provider performance benchmarks.
The actual pipeline searches only companies without a candidate, capped by the
configured query limit. Monthly credits are shared across runs, not reset for
each batch. Source crawling, DNS, hosting, compute and storage are separate.
Tavily Advanced costs two credits; this connector fixes Basic depth and disables
automatic parameters, generated answers, images and provider page extraction.

## Verified official sources

- [Tavily pricing](https://docs.tavily.com/documentation/api-credits)
- [Tavily quickstart](https://docs.tavily.com/documentation/quickstart)
- [Tavily service terms](https://www.tavily.com/terms)
- [Tavily official SDK](https://github.com/tavily-ai/tavily-python)
- [Brave pricing](https://brave.com/search/api/)
- [Brave terms](https://api-dashboard.search.brave.com/terms-of-service)
- [Serper pricing](https://serper.dev/)
- [Serper terms](https://serper.dev/terms)

The Tavily terms expressly allow reasonable API use and integration into customer
applications. Section 3.2 restricts disclosure of service-performance information:
keep provider comparisons and provider-specific performance telemetry private.
Published company claims come from independently retrieved, verified company
pages, not API snippets or generated answers. No sensitive/government-ID input
is sent: discovery queries use legal company names and locations.

Brave's 1 September 2026 terms limit result storage to transient use, and section
3(b)(xiii) restricts using Search Results for AI-model/service evaluation,
benchmarking or improvement. Compatibility with the competition workflow needs
clarification or appropriate written plan rights before making Brave the primary
experiment. The implemented Brave route remains disabled; marketing claims do
not override its service terms.

Serper's terms say it is not affiliated with Google and supplies web-scraped data.
Its price alone does not establish upstream access rights for this competition;
we have not verified those rights and have not called its API. It is not the first
recommended scoring route. SDK code licences do not grant API or source rights.

## Implemented safeguards and private development result

Both `--search-provider tavily` and `--search-provider brave` use shared, decimal,
thread-safe query/spending reservations. They retain no API result bodies,
titles, snippets, answers or rankings. Authenticated API calls require HTTPS,
forbid redirects and make one attempt. Search supplies at most three candidates;
all published facts still pass the same legal-company, robots, public-address,
TLS, snapshot and evidence gates. Known directories, registry lookup pages, job
boards, Wikipedia and social networks cannot become company-site candidates.

The Tavily SDK's explicit anonymous mode was exercised privately. It never uses
an account key, even if one is later present, and stops on quota/access failures.
It is absent from the production CLI: official runs require `TAVILY_API_KEY` so
execution does not depend on anonymous shared limits. Private artifacts under
`out/provider-research-20261014/keyless-development/` retain the exact input IDs,
candidate decisions, independently acquired evidence and a passing audit. They
reuse prior registry evidence and do not measure per-company runtime; they are
not a new 100-company smoke or an official run. The holdout was untouched.

Company-page inspection supports the previously missed
[Varanger KraftFiber website](https://www.varanger-kraftfiber.no/) through its
specific brand/title and registered street/postal address. Captured dated posts
include its 6 August, 1 June and 22 May 2026 company-authored publications. These
are company promotional publications, not independent press or sentiment.
Unresolved candidate ownership remains ambiguous. The browser sample was locally
refreshed from retained evidence; it has not been deployed.

All **299 tests** pass, including transient POST requests, explicit free-budget
handling, keyless isolation, API denial, directory rejection, provider dispatch
and unchanged company-ownership checks. Offline refresh and `git diff --check`
pass. No paid API use, GitHub push or competition submission occurred.

## Account setup and completed smoke

Create a Tavily account at [app.tavily.com](https://app.tavily.com/) and choose the
free **Researcher** plan. Leave pay-as-you-go disabled; do not add billing for the
initial test. Create an API key, then enter it securely into the environment's
prepared `TAVILY_API_KEY` secret setting. Its proxy delivery is scoped to
`api.tavily.com`. Save and publish the settings; do not paste the key into chat.
The key is now ready in the published environment and an authenticated Basic
request succeeded. No key value is retained in reports or source files.

Before the run, the account endpoint reported the free Researcher plan, a
1,000-credit limit and zero usage. The probe plus the entire run were bounded to
at most 101 one-credit Basic requests, inside that observed free allowance.
The same-input 100-company run is now complete; see
[the reviewed application report](tavily-smoke-20261014.md). Estimated paid API
spend is $0. The account endpoint still reported zero usage afterward; do not
interpret that as confirmed zero credit consumption or a verified remaining
balance. Disabled pay-as-you-go was not verified by the API. No paid calls or
paid-plan transition are authorized. A client cap is not a provider invoice or a
substitute for the account's actual quota and billing settings.

The evaluator options for that explicitly free initial run are:

```sh
--search-provider tavily --search-max-queries 100 \
--search-price-per-1000 0 --search-budget-usd 0
```

Keep the original holdout separate. Report exact-company findings, rejected and
ambiguous matches, evidence validity and total application resource use. Private
provider diagnostics are not public API-service benchmarks. A larger official
batch needs a declared sustainable account/quota and verified resource budget;
the free monthly allowance alone does not demonstrate daily-run capacity.
