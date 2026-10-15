# Packaging and evaluator reliability result — 12 October 2026

Completed offline within the packaging assignment. Filesystem sharing with other
UI chats is **unknown**; a baseline-relative integration patch is supplied.

## Snapshot and ownership

Before editing, read AGENTS.md, the latest cloud continuation in HANDOFF.md,
coverage-progress-20261012.md, parallel-chat-plan.md, the assigned brief,
submission-packaging.md, dated-events-progress.md and parallel-work-report.md.
Verified the prepared snapshot contains the latest 163-test milestone, dated-event
implementation and all briefs. Git HEAD is
`a7c24ef` (import baseline); the latest prepared work is intentionally uncommitted,
so fetching/resetting GitHub main would not establish this assignment's snapshot.
Initial status and hashes/copies of owned existing files were saved under
`out/packaging-reliability/baseline/`. Preserved existing changes.

Changed only:

- `scripts/evaluate_signalpost.py`
- `scripts/audit_submission.py`
- `src/norway_company_agent/audit.py`
- `tests/test_packaging.py`
- `docs/submission-packaging.md`
- New `tests/test_evaluator_reliability.py`
- New `docs/task-results/packaging-reliability.md`

The existing packaging implementation and package CLI needed no edits.
No runner/pipeline, dependency, lockfile, strategy, frozen split, handoff or other
worker files were edited. No additional workers, source requests, paid calls,
holdout crawl, commit, push, publication or submission occurred.

## Findings and changes

The evaluator previously converted every failed subprocess into wrapper exit 1,
had no shared preprocessing/packaging deadline, and accepted `--output` as an
abbreviation overriding its managed output directory. It now rejects abbreviations,
supports optional finite positive `--evaluator-timeout-seconds` with no default,
and supervises each stage in its own POSIX process group. Cleanup kills inherited
worker descendants, including on failed-leader exit, without signaling unrelated
processes. Positive child exits are preserved; signal exits use 128 + signal and
record the negative raw code. Timeout is exit 124 and a failed evaluator outcome.
An atomic `evaluator-status.json` distinguishes complete, failed and timed-out runs;
packaging is skipped after batch failure. Partial artifacts remain diagnostic only.

The audit CLI could overwrite its input batch, envelopes or cited source bytes.
Those destinations are rejected, and valid reports are written by atomic replacement.
The auditor previously deduplicated evidence IDs across envelopes, allowing an
altered locator on an earlier envelope to go unchecked. It now checks every
reference. Nonobject envelopes, malformed locator types/selectors, missing fields
and undecodable CSV bytes fail rather than crashing or publishing a package.

Existing staging/rename packaging preserves source data and does not publish on
normal copy failures. Added negatives verify missing/corrupt snapshots, source
preservation and staging cleanup. Relocated DOM and JSON-LD evidence passes after
original acquisition deletion, including cited prior refresh evidence; altered
locators and tampered retained history fail. This establishes byte/locator support,
not metadata truth, exact-company precision, recall or an official score.

## Validation

All commands ran from the repository root using the existing Python 3.12.14
installation. No dependency installation or lockfile change was needed.

| Command | Outcome | Saved artifact |
| --- | --- | --- |
| `.venv/bin/python -m unittest discover -s tests -p test_packaging.py -v` | 12 tests passed | `out/packaging-reliability/packaging-tests.log` |
| `.venv/bin/python -m unittest discover -s tests -p test_evaluator_reliability.py -v` | 9 tests passed | `out/packaging-reliability/evaluator-tests.log` |
| `.venv/bin/python -m unittest discover -s tests -p test_site_events.py -v` | 8 tests passed | `out/packaging-reliability/dated-event-tests.log` |
| `.venv/bin/python scripts/run_refresh_replay.py --manifest tests/fixtures/refresh-snapshots.json --output out/packaging-reliability/refresh-replay.json` | Both expected changes, zero false changes, idempotent | `out/packaging-reliability/refresh-replay.json` and `.log` |
| `.venv/bin/python scripts/evaluate_signalpost.py --organisations out/packaging-reliability/offline-input/batch.txt --bulk out/packaging-reliability/offline-input/bulk.csv --output-dir out/packaging-reliability/offline-success --run-id packaging-reliability-offline --modules '' --workers 1 --evaluator-timeout-seconds 30` | Exit 0, 3 envelopes, accepted audited package | `out/packaging-reliability/offline-success/`, `offline-evaluator.log` |
| `.venv/bin/python scripts/audit_submission.py --input out/packaging-reliability/offline-success/package/envelopes.jsonl --organisations out/packaging-reliability/offline-success/package/organisations.jsonl --report out/packaging-reliability/offline-audit.json` | Passed; zero errors | `out/packaging-reliability/offline-audit.json` and `.log` |
| `git diff --check` | Passed | No output |

Total: **29 focused tests passed**. Tests include actual sleeping children and
descendants in both stages, an unrelated sleeping process, a shared deadline,
failed-leader cleanup, spawn failure, real exit/signal codes, real invalid batches
and budgets/modules, and successful arbitrary-size offline execution. The existing
1,101-company packaging fixture also passes. One initial regression exposed the
argparse abbreviation bug and another exposed uncaught SelectorSyntaxError; both
were fixed and final logs pass. The initial abbreviation-generated artifact was
moved into `out/packaging-reliability/initial-abbreviation-regression-artifact/`.
No unresolved test failure remains. A full integration regression run belongs to
the coordinator and was intentionally not run here.

## Limits and integration dependencies

No current runner change is needed for timeout cleanup: its multiprocessing worker
inherits the supervised process group. POSIX is required for the wrapper. Deliberate
session-detaching descendants are outside this guarantee. Installation/interpreter
startup, final reaping/status reporting, CPU, memory, disk and API cost are not bounded
by the new time option. The organizer's resource budget remains unknown.
A hard kill during packaging can leave hidden staging; even a package rename racing
with timeout must not be accepted unless evaluator status is completed. Normal
packaging exceptions remove staging and publish nothing.

Relocated portable packages remain unsupported as runner `--previous-output` inputs.
Preserve resolving original acquisition artifacts for refresh/re-extraction; history
validation was not disabled. Supporting relocated refresh requires coordinator-owned
runner path-resolution changes as a separate assignment. The package manifest is
not authenticated against a trusted external copy by the evidence auditor.

Coordinator next steps: integrate/review the baseline-relative patch when checkouts
are isolated, run the full regression/evidence audit, and validate resources on the
target host. Do not combine different input-snapshot scores or treat these synthetic
checks as a live/official run.

Integration patch: `out/packaging-reliability/packaging-reliability.patch`.
Apply against the verified prepared snapshot, not bare GitHub main; it excludes all
preexisting changes and contains only this assignment's modifications/new files.

Patch validation: `git apply --check --directory=out/packaging-reliability/patch-check out/packaging-reliability/packaging-reliability.patch` passed against copies of the owned baseline files.
