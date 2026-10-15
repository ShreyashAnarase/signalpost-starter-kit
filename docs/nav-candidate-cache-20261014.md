# Declared NAV candidate cache — 14 October 2026

Implemented the organizer's allowance for a declared official-feed cache. The
cache is optional and supplies discovery hints only. No credentials or private
contact information are stored, and no cached advertisement becomes a claim.

## Behavior

- Batch CLI/evaluator accept `--nav-cache-input` and `--nav-cache-output`, requiring
  `--nav-jobs`. A source fingerprint/config hash includes the candidate-cache
  input hash. Changed input is rejected before use. Output never overwrites a file.
- Index rows hold UUID, business name, optional employer organisation number,
  source URL, retrieval/modified timestamps and source content hash. All feed
  header candidates can be indexed, including companies outside the current
  batch. Output envelopes still cover exactly the supplied batch.
- A cached candidate matching a supplied company is freshly fetched from NAV's
  fixed official detail route. Publication requires active, unexpired detail and
  the exact legal employer ID. Evidence/hash/time come from the new response.
- Missing/invalid caches explicitly fall back to live discovery. Missing NAV
  credentials produce zero NAV acquisitions and no cached published facts.
  Inactive/expired jobs are removed from the index; wrong-employer detail cannot
  publish a claim for the input company. Existing NAV refresh removal is preserved.
- Input/output declarations report hashes, schema/count, source retrieval range,
  rechecks and export state. The index has 50,000-row/32MB limits with explicit
  eviction/truncation reporting. Index persistence is opt-in.

## Verification

All **321 tests** pass, including nine new candidate-cache tests for fresh evidence,
credential absence, inactive/expired/wrong-company detail, malformed/changed caches,
global header hints, tombstones, output preservation, bounds, provenance and CLI
constraints. `git diff --check` passed.

The real evaluator command processed **1,511 newly supplied synthetic inputs**
(including one absent from its registry fixture) with `--modules registry`,
`--nav-jobs`, an absent candidate-cache input, and empty NAV/search keys. It emitted
1,511 envelopes and passed the portable package audit: one snapshot, 3,020 evidence
locators, zero errors. Runtime: **7.712 seconds**, zero requests/bytes/API fees.
Missing token and rejected optional cache were explicit in the shared source
report. The output cache was a declared empty index. This is an **offline
structural check**, not a live scale/coverage/cost result or an official score.

Artifacts: `out/nav-candidate-cache-20261014/structural-1511/` and
`out/nav-candidate-cache-20261014/candidates.json` (ignored/private).
Source fingerprint: `06d1933a12406f941781eaa7d9041bcb69868d7363db3fdc3955dfc3c4c4d0bd`.

The earlier 312-test clean-clone verification is historical. The final published
commit still needs its own clean-clone install/run check before submission.
Dependencies have not changed. No paid API calls or new live job acquisitions
were performed for this change. Live measured baseline remains 12 verified sites,
seven company-authored articles across three companies and zero jobs per 100.

## Release communication

Organizer clarifications are in `docs/organizer-clarifications-20261014.md`.
The unsent submission draft now lists the confirmed submit/follow-up addresses,
required fields and board delay. The runtime request acknowledges forthcoming
provider instructions instead of repeating already answered questions. No email,
publication, main-repository commit or official submission was performed.
