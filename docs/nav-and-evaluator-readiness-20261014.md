# NAV integration and evaluator portability — 14 October 2026

The optional NAV adapter is implemented, and the official-page traps are now
covered by entry-point checks and a clean local-clone exercise. This is not an
official run, a score estimate or verification of the eventual GitHub commit.

## Official-page checks

| Requirement | Current evidence |
| --- | --- |
| Read Builderr's supplied companies | Evaluator takes a runtime file; order and exact membership are checked. No sampling occurs in this entry point. |
| Handle batches beyond 100 | A fresh 1,511-company synthetic runtime batch emits exactly 1,511 envelopes, including one registry-missing company. |
| Process companies concurrently | The actual batch runner uses eight workers by default; the structural exercise used that runner. NAV scans once for the whole batch. |
| One run command | Documented in [OFFICIAL_RUN.md](../OFFICIAL_RUN.md); no fixed `--expected-count 100` in the official command. |
| Clean installation | Declared setup succeeds in a new pinned local clone without `.venv`, `.tools` or `out`; all 312 tests and refresh pass. |
| Reproducible credentials | Default uses public sources. Personal Tavily credentials are excluded from the official dependency contract. NAV/model access needs organizer confirmation. |

Malformed JSON wrappers now fail explicitly rather than silently becoming an empty
batch. Complete legal names come from registry evidence; input annotations cannot
replace them. Missing records and source failures remain explicit envelopes.

The clean exercise initially failed because uv tried to write under a read-only
home. `scripts/setup_codex_cloud.sh` now defaults uv/pip caches to ignored local
`.tools/` paths. Dependency declarations and `uv.lock` were not changed.

## Clean-clone boundary

The exact local validation commit is
`8f05a66947dafa50687a821ffe89339ede9b0f0e`. It was created in an isolated verification
repository and cloned to
`/workspace/verification/signalpost-nav-20261014-clean-v3`. Only the declared install
script was used before running the evaluator on newly supplied synthetic files.
The runtime/source fingerprint matches the development checkout.

With personal provider variables empty and optional NAV access unavailable, the
single evaluator command emits all **1,511/1,511** inputs in order and produces an
accepted package. No HTTP requests or third-party charges occur in that structural
test (`--modules registry` against a synthetic registry fixture). Its 6.698-second
runtime is **not** live research performance at official scale. The previous
1,507-input structural exercise also passed.

GitHub still points to the earlier commit; no repository commit, push, PR or
submission was made in the user's checkout. The isolated validation hash is not
a published submission hash. Once release code is published, repeat the same
check against that exact remote commit and the organizer's confirmed budget.

## NAV behavior and evidence

- `--nav-jobs` opts into one bounded shared scan, with server-side
  `NAV_API_TOKEN` supplied by the evaluator. The production command has no
  anonymous/public-token fallback and no dependency on a developer NAV account.
- Feed names select candidates. Fresh detail responses must provide the exact
  requested legal employer number, matching job UUID, active status and supported
  publication/expiry dates. Subunits, recruiters and parents are not collapsed.
- Facts cite immutable detail JSON, retrieval time/hash and an exact JSON pointer.
  Application URLs pass the existing public-URL policy. Public export omits
  contact details and withdrawn-ad values.
- Limits cover pages, details, requests and shared elapsed time. Default discovery
  covers the last seven days of updates; reports distinguish finishing that
  window from full active-job coverage. There is no warm cross-run index.
- Prior NAV job IDs from supplied refresh input are freshly rechecked before
  discovery. An unchanged active job outside the discovery window is retained
  only after detail verification. Inactive, expired or unconfirmed NAV jobs leave
  the current display; private evidence history is preserved. Old inactive events
  cannot overwrite a newer confirmed reactivation.
- Missing/denied NAV access does not prevent the other company modules or drop
  inputs. NAV resume checkpoints are not reused as fresh active-job evidence.

All 312 tests pass, including identity/date/UUID mismatches, tampered evidence,
private URL rejection, unsafe pagination, source limits, tombstones, failed refresh,
reactivation ordering, public privacy and arbitrary runtime batch sizes.

## Live source check and remaining gap

The actual connector was exercised privately with NAV's documented public
experiment access on the existing 100-company smoke plus 24-company development
inputs. It read **12,000 entries over 12 pages**, produced a record for all 124
inputs, and found no exact-name candidates. The scan was incomplete. **No live
job-coverage improvement is claimed.** Existing registry evidence was reused;
this is not a new full 100-company acquisition or independent precision review.
The original holdout was not researched.

The test verifies real feed access and header handling. Positive job extraction
and publication are currently verified with deterministic source fixtures, not a
newly observed target-company job. API cost is estimated at $0 under NAV's free
service; compute, hosting and storage are separate. Stable production credentials
and official resource capacity remain unverified.

The requested [Builderr access/budget message](builderr-runtime-access-request.md)
is ready for review and **has not been sent**. It asks for model provider/endpoint,
model/tool support, budget, compatible evaluator-owned optional API access and the
exact batch/registry/resource contract. LLM use is permitted, but no unsupported
model or personal key is assumed. Official qualification remains unmeasured.

Private ignored artifacts are under `out/nav-integration-20261014/`, including the
clean-clone manifest, verification report and live-connector diagnostics. Prior
100-company coverage remains the separately reviewed 12 sites/seven articles/zero
jobs; that personal-search development result is not an official credential plan.
