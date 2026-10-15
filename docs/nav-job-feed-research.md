# Latest NAV implementation update — 14 October 2026

Read [the live job validation](jobs-improvement-20261014.md). Fixed the actual
`ad_content` response shape and official registered-workplace-to-legal-company
resolution. Selected positive controls now verify **17 live ads across three
eligible companies**, with two-source evidence when a workplace is involved.
334 tests pass; portable package and idempotent ad-removing refresh pass.
This does not change the original random100 result (zero jobs) or establish a
competition score. The bounded 30-day candidate index is partial. Stable private
access still requires NAV registration; the unsent request is `nav-access-request.md`.
Optional cloud key requirement is saved; no key was supplied or email sent.
Older research notes below are historical, including their detail JSON field name.

---

# NAV job-feed access research — 14 October 2026

NAV provides a free official feed with explicit permission to republish job
advertisements and use them for statistical or analytical purposes. This is a
promising source for exact-company job coverage without requiring a verified
company website first. An optional bounded connector is now implemented in
`src/norway_company_agent/nav_jobs.py`; enable it with `--nav-jobs` only when
evaluator-provisioned credentials are agreed. It is disabled by default and no
stable production credential has been verified. See [OFFICIAL_RUN.md](../OFFICIAL_RUN.md).

Verified official documentation:

- [NAV API terms](https://arbeidsplassen.nav.no/vilkar-api)
- [Feed documentation](https://navikt.github.io/pam-stilling-feed/)
- [Public dataset description](https://data.norge.no/datasets/62409bc8-680d-3f70-98bf-d2f2beebaa50)

The feed documentation offers a rotating public token for experiments at
`https://pam-stilling-feed.nav.no/api/publicToken`. Private consumer access requires
emailing NAV with acceptance of its terms, an identifier, contact email, phone
and contact person. No registration email has been sent. Public experiment-token
access does not establish stable credentials for a reproducible official run.

## Implementation requirements

- This is a change feed, not a server-side company search. Index it once per
  batch/shared refresh, within explicit page/time/byte limits. Do not scan the
  entire feed independently for every company.
- The detail response includes `json.employer.orgnr`; match it to the exact input
  legal entity. A business name, brand, recruiter or parent is insufficient.
  Workplace/subunit numbers need an independently verified parent relationship.
- Publish only active entries with supported publication and expiry dates,
  titles, employer identity and safe source/application URLs. Cite retained
  detail JSON using exact pointers and record retrieval time/hash.
- NAV requires immediate updates/removal when an advertisement changes or becomes
  inactive/deleted. Process tombstones, preserve the audit history privately,
  and avoid keeping withdrawn advertisements visible as current jobs during a
  failed refresh. Generic last-known job preservation needs source-specific
  treatment before this connector can be enabled.
- Keep application links directed to the originating application system. Do not
  export contact-person details when the product does not need them.
- Declare bootstrap/index caches and their source timestamps. A bounded partial
  scan must explicitly report incomplete coverage. An empty partial scan is not
  evidence that a company has no jobs.

The source is free; compute, indexing, storage and transfer still need measurement.
Documentation and sanitized access diagnostics are retained privately in
`out/discovery-gaps-20261014-prep/`. No API token is retained in those artifacts.

## Bounded live experiment

The documented experiment-token endpoint and authenticated feed both returned
HTTP 200. A bounded six-page scan read 6,000 change entries spanning 1–3 September
2026; 4,692 headers said active. Header business names produced no exact-name
candidates for the 100-company smoke plus 24-company development inputs, so no
employer detail or job claim was published. This is an **incomplete scan**, not a
finding that these companies have no jobs. Header status alone cannot establish
a current job; detail retrieval is required. The original holdout was untouched.

The successful experiment established the API route, not production credentials.
The connector now performs one bounded in-memory scan per batch, verifies exact
legal employer IDs from detail responses and removes unconfirmed NAV advertisements
from current display during refresh. It rechecks supplied prior job IDs before
scanning new updates. Public display omits historical withdrawn-ad values and
contact-person data; retained evidence stays private. Scans default to the last
seven days and explicitly distinguish that window from full active-job coverage.
No warm cross-run index is assumed. Larger bootstrap/index budgets and stable
private-consumer credentials remain necessary before an official release using NAV.

## Organizer clarification and explicit candidate index — 14 October

Builderr permits a declared NAV official-feed cache when access is permitted,
each published ad is live-verified and company-matched, and refresh metadata is
retained. The implementation now supports `--nav-cache-input` and
`--nav-cache-output` with `--nav-jobs`. It indexes candidate IDs/names and optional
employer IDs alongside source hashes/timestamps, never ad texts or published
claims. Input/output hashes, retrieval range, row counts and live rechecks are
reported; the bounded index evicts rows explicitly. Missing/invalid caches allow
cold live discovery. Missing credentials never publish cached jobs. Every fresh
claim still references a newly fetched detail response. No permitted production
credential is available yet, and this implementation has not increased measured
live job coverage. See `OFFICIAL_RUN.md` for the command/configuration contract.
