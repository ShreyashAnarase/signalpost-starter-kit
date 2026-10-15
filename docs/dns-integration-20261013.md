# DNS fallback integration and first live evidence — 13 October 2026

The received DNS patch exactly matches SHA-256
`69156f8b356da66a7b2a3a4b155caf6cd8cc3b5927bb0aae5bf577ecd2841adf`.
It applies to the integrated snapshot and changes only the five assigned files.
Original touched-file bytes and the patch are retained in ignored
`out/network-integration-review/`. Existing uncommitted work is preserved.

Review confirms explicit opt-in, inherited-proxy requirements, verified resolver
TLS, no resolver redirects, validated A/AAAA questions and CNAME ownership,
public-address checks including embedded IPv6 addresses, redirect/robots checks,
and request/deadline/byte telemetry. Resolver responses are not claim evidence.
Local DNS remains the default. `SIGNALPOST_DNS_OVER_HTTPS=1` permits fallback only
when local lookup fails. Preflight does not pin the proxy's eventual connection;
this limitation also existed with local DNS and remains documented.

## Combined validation

- **242 tests pass**, including 37 new DNS/URL/network regression tests.
- Offline refresh still finds both changes, no false changes, idempotent replay.
- The resolver probe now succeeds in this coordinator instance. The worker's
  previous `dns.google` CONNECT denial is not the current access result.
- A bounded live run with the flag set acquires real registry records and pages.
  Both company processes exit 0 with complete telemetry and one envelope per input.

## Live result

Inputs remain development organisations 985215294 and 984589344; no holdout.
Limits remain four pages, 20 budgeted requests and a 40-second company supervision
budget per company, one worker, 180-second overall acquisition budget.

| Outcome | Result |
| --- | --- |
| Terminal envelopes | 2/2 |
| Supported registry legal names | 2/2 |
| Verified company websites | 1/2 |
| Dated news/job claims | 0/0 |
| Budgeted requests including DNS validation | 37 |
| Received bytes including resolver responses | 218,462 |
| Acquisition/export/audit wall time | 43.031 seconds |
| Third-party API charges | $0 |
| Evidence audit | 5 cited snapshots, 20 locators, zero errors |

NORSK FARMASØYTISK SELSKAP (984589344) verifies using its exact organisation number
in retained legal footers on four pages. It supplies website, description and an
outbound company-declared Facebook link; this is not scraped Facebook content.
No news/jobs were found within the bounded four-page search, not proof of absence.
Identity checks are deterministic/assistant-reviewed, not independent human labels.

NORVIGROUP NORSK DUN AS (985215294) has a supported registry record but unresolved
website. A further non-following robots request shows `www.nf.no` redirects to
`https://www.nordicform.no/robots.txt`. That new destination is a candidate only;
it has not been acquired or established as the exact legal company's site.

The two companies are selected diagnostic examples, not a representative coverage
sample. Comparing with earlier acquisition failures proves current live operation,
not measured strategy recall improvement on identical source snapshots.

## Artifacts and configuration

- `out/live-development-review/integrated-doh-20261013/`: real profiles, snapshots,
  telemetry, envelopes, report and audit.
- `out/network-integration-review/live-package/`: audited portable live evidence.
- `out/network-integration-review/human-review/`: 38 claim rows, 20 blank review
  judgments, five copied snapshots, zero missing/hash-mismatch issues. Review
  provenance remains blank; packet generation is not independent human review.
- Resolver probe, redirect headers and refresh replay are retained alongside them.

Draft configuration preserves prior rules, includes `dns.google`, suggests the
non-secret variable `SIGNALPOST_DNS_OVER_HTTPS=1`, and adds the observed redirect
host `www.nordicform.no`. These saves do not apply/publish configuration. Review and
save those settings and publish the now-integrated snapshot for future tasks.
The successful run used a command-local flag; do not assume future processes
inherit it until runtime injection is verified.

## First-submission next step

Prepare the required fresh 100-company smoke with real permitted-source access,
audit every envelope and material locator, measure full runtime/request costs,
and freeze the reviewed commit. The two-company run is not that smoke deliverable.
Wider website destinations and the public-universe download may require explicit
network additions. Resolve those from the actual selected batch and observed
redirects, preserving existing rules rather than guessing broad access.

No paid provider, secrets, holdout research, commit, push, publication or submission
was performed by this integration. The baseline API estimate remains $0; hosting
and compute are excluded. Qualification and leaderboard appearance are unproven.
