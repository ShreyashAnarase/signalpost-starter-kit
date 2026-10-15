# Job discovery improvements — 14 October 2026

The corrected NAV pipeline verified **17 live advertisements for three legal
companies** in a selected positive-control check. This establishes that the real
source-to-company-to-evidence path works. These companies were selected because
we had already found their ads; this is **not random coverage, an official score,
or a replacement for the 100-company smoke**, which still reports zero jobs.

| Legal company | Organisation number | Freshly verified ads |
| --- | --- | ---: |
| ASSEMBLIN AS | 965808752 | 1 |
| OCAB AS | 916326211 | 2 |
| ADECCO NORGE AS | 935333156 | 14 |

All three are in the frozen public eligible universe and the identities were
anchored to the frozen BRREG bulk snapshot. No holdout company was deliberately
targeted. This assistant verification is not independent human precision review.

## What prevented useful results

1. The actual detail endpoint returns `ad_content`, while our earlier adapter
   expected `json`. Earlier live scans had no matching candidates and never
   exercised detail extraction, so fixture tests missed the integration defect.
2. NAV frequently identifies a registered workplace rather than the main legal
   entity. Exact string comparison against the parent input ID discarded valid
   ads. Every positive-control ad used an official workplace relationship.
3. Exact business-name filtering missed reordered names and workplace suffixes.
   Candidate matching now tolerates those forms; legal publication still requires
   an exact ID or a fresh official direct workplace-parent proof.

The adapter accepts the real envelope and the earlier JSON export/fixture shape;
ambiguous envelopes with both shapes are rejected. It fetches BRREG's
`/api/underenheter/{number}` for an otherwise valid candidate when needed, verifies
that the response identifies that exact workplace, has type `BEDR`, is not deleted,
and has a direct `overordnetEnhet` equal to an input legal company. Corporate
subsidiaries/group parents and name guesses cannot establish this relationship.
The NAV credential is not forwarded to BRREG.

A job retains its registered workplace number, identifies the legal owner, and
labels `registered_workplace_of`. Its claim references **both** the newly fetched
NAV ad and the official BRREG relationship snapshot. Missing/corrupt relationship
evidence prevents publication. Active status, dates, UUID and safe URL checks
remain in place. No publication/expiry date was invented to increase coverage.

## Discovery and cache

A private permitted experiment scanned 30 days of updates, creating an index with
8,354 candidate IDs from 60,000 change entries. The scan remained partial, so it
cannot establish absence. No names matched our 100-company smoke plus 24-company
development inputs. This suggests we need a broader index/discovery strategy;
it does not show those companies have no vacancies elsewhere.

A new production helper builds such a declared index without selecting evaluator
companies or publishing ads:

```sh
.venv/bin/python scripts/build_nav_candidate_cache.py --output-dir out/nav-bootstrap
```

It requires securely supplied permitted `NAV_API_TOKEN` access. Defaults are a
30-day window, 60 pages, 100 request operations and 180 seconds; all are configurable.
The output reports `complete`, `partial` or `failed`. The index is limited to
50,000 rows/32MB and contains hints/provenance, not reusable job claims. A partial
index can be used for discovery, never proof of no jobs. Bootstrap is a separate,
declared preparation step; it is not an install or hidden official-run prerequisite.
The evaluator can run cold when no cache is supplied.

With permitted access, append `--nav-jobs` and optionally
`--nav-cache-input /path/to/candidates.json` to the evaluator command. Every
published detail and required workplace relationship is fetched again. Source
budgets still need to fit the forthcoming common official limits.

## Verification

**334 tests pass**, including real-envelope handling, reordered/suffixed names,
wrong-company rejection, official workplace resolution, corporate/deleted/other-
company negatives, corrupt relationship evidence and cache bootstrap behavior.
The positive-control package passes 30 snapshot / 51 locator checks with zero
errors. An offline missing-key refresh removes all 17 ads from current display,
preserves private evidence, passes audit and is idempotent, with zero HTTP calls.

The initial shape-mismatched and pre-workplace control attempts failed; they are
preserved privately and are not claimed as successful runs. The final positive
control re-fetched all published details and relationship evidence after the fixes.
No Tavily queries or paid APIs were used for this job-discovery work. NAV's feed is
free; compute/storage/transfer/indexing costs still need separate measurement.
The selected-control runtime/request figures are not an official-batch estimate.

Private evidence and reports:
`out/jobs-improvement-20261014/nav-broader/` (partial index),
`positive-control-v3/` (final 3-company/17-job check, package and refresh proof),
`access-docs/` (current access instructions). Source fingerprints are recorded in
the final control report; this job-source update follows the earlier live100 code.

The current-code offline re-export of the earlier 100-company smoke also passes
its audit with all 14 verified sites retained and zero jobs, using zero HTTP.
This is a regression export, not another live smoke. Machine-readable evidence
is in [jobs-validation-report.json](jobs-validation-report.json).

## Production access

Private experiments used only NAV's documented rotating public experiment token,
kept in memory and never retained in files/logs. That does not establish stable
production access. The production helper/evaluator never obtains it automatically.

NAV says private access requires consumer registration and written acceptance of
its terms plus identifier, contact email, phone and contact person. The complete
unsent request is [nav-access-request.md](nav-access-request.md). No email or
agreement was sent on the entrant's behalf. An optional `NAV_API_TOKEN` secret
requirement is saved in the cloud draft, scoped only to `pam-stilling-feed.nav.no`.
After NAV issues the key, add it securely, review/save the settings, and publish
the environment. Saving the requirement has not configured or activated a key.

Tavily remains the intended website-discovery API. The access question to Builderr
is still held, per the user. No main-repository commit, push, public deployment or
competition submission occurred. Final published-commit clean verification remains
a release requirement; the earlier 325-test clean clone predates these changes.
