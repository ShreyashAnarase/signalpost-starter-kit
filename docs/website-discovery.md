# Optional exact-organisation website candidate discovery

The production default remains registry website and business-email discovery.
`--wikidata-discovery` opts into `wikidata_exact_org_candidates_v1`, only when
those routes produce no candidates. It issues one bounded WDQS query for an exact
nine-digit organisation number (P2333), returning website candidates (P856), then
runs the unchanged company-site identity checks. No hardcoded company answers or
name-to-domain guesses were added. This does not replace an existing candidate
that subsequently fails verification.

## External validation is pending

This connector is implemented and tested **offline only**. Access to authoritative
P2333 semantics, licensing and service-policy pages was blocked by the cloud proxy
with HTTP 403. No live Wikidata query or development-company crawl was performed.
Before live use, verify the property meanings and current service access rules:

- https://www.wikidata.org/wiki/Property:P2333
- https://www.wikidata.org/wiki/Property:P856
- https://www.wikidata.org/wiki/Wikidata:Licensing
- https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual

Future environment network settings may need `www.wikidata.org`,
`www.mediawiki.org` and `query.wikidata.org`. Preserve existing allowlists. No new
secret, paid service or dependency is required. WDQS service throttling/concurrency
must be checked before any batch use; the generic acquisition host pacing is not
a demonstrated guarantee of compliance with current WDQS limits. Begin with one
worker and a small development-only experiment after policy verification.

## Evidence and errors

The query uses one acquisition attempt, the existing robots/URL/TLS checks,
request/deadline budgets and a 200 KB response cap. It retrieves at most four
bindings, accepts at most three deduplicated URLs, and reports when the result
limit is reached. Malformed or wrong-org bindings are rejected. Provider denial,
empty results, malformed output and budget exhaustion remain explicit diagnostics.

Provider responses are immutable content-addressed snapshots. The website record
has `candidate_discovery` diagnostics, including provider, strategy, exact org,
source URL, retrieval time, hash, snapshot path and rejected-binding reasons.
Candidate attempts additionally retain entity identifier and binding index.
These remain **candidate provenance**, not published-claim evidence. Accepted
website claims cite independently retrieved company pages and identity proofs;
provider responses cannot establish website ownership on their own. Keep the
profiles and their referenced snapshots if exporting discovery provenance: the
submission envelope's claim evidence intentionally does not cite WDQS responses.

Multiple returned entities or websites are candidates, not a resolved legal or
group relationship. Parent, subsidiary, franchise, similar-name and conflicting
footer fixtures remain rejected by the existing identity gate.

## Validation and measurement limits

```sh
.venv/bin/python -m unittest discover -s tests -p test_wikidata_discovery.py -v
```

On the same synthetic no-registry-website input, the unchanged baseline performs
no request and finds no site; the opt-in fixture acquires one candidate and
accepts independently supplied exact-org company-page evidence. Six focused tests
also exercise negatives, corrupt provider output, empty results, denial, budget
exhaustion, candidate bounds and unchanged default behavior. This proves integration
behavior only. Real development coverage gain, independently reviewed precision,
provider-policy compatibility, real request cost/runtime, and official score are
unmeasured. The holdout was not read or crawled.

After external validation, compare baseline and challenger on the same frozen
development inputs with separate run/output directories. Record accepted and
rejected sites, candidate provenance, assistant versus independent review,
requests and runtime. Enable the flag in both documented commands and declared
submission configuration only if the evidence supports promotion. The flag is
included in the run configuration/resume fingerprint, preventing reuse between
baseline and challenger modes.
