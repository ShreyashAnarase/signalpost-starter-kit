# Reproducible batch execution and portable evidence

From the repository root, use Python 3.12+ and install the exact dependencies in
`uv.lock` without rewriting it:

```sh
bash scripts/setup_codex_cloud.sh
```

This installs locked dependencies, runs regressions, and checks offline refresh.
Core installation requires no API secrets. Live research requires network access
to official registry and verified company-owned sites. No paid connector is enabled
by default. See repository source-policy documentation before enabling a connector.

## One evaluator command

Provide the organizer's current organisation-number batch and frozen official bulk
CSV snapshot. Both gzip and plain CSV are supported by content detection. Batch
size is taken from the input, not hardcoded. Duplicate organisation numbers are
rejected rather than silently dropped. Use a new output directory and run ID:

```sh
.venv/bin/python scripts/evaluate_signalpost.py \
  --organisations /path/to/official-batch.jsonl \
  --bulk /path/to/frozen-registry.csv \
  --output-dir out/current-run --run-id current-run \
  --workers 8 --deadline-seconds 600 --company-timeout 75 \
  --evaluator-timeout-seconds 720
```

The wrapper runs the current competition batch CLI, then copies all cited snapshots
into an audited `out/current-run/package/`. Source profiles, telemetry, and original
snapshots remain outside that portable directory. The portable package contains:

- `envelopes.jsonl`: one terminal envelope per input, including failures;
- `organisations.jsonl`: batch order and membership for an offline audit;
- `snapshots/`: content-addressed bytes for current and retained prior evidence;
- `manifest.json`: output/batch hashes, snapshot byte counts/hashes, and audit result.

Snapshots preserve bytes, timestamps, evidence IDs, extraction methods and locators.
Only evidence `snapshot_path` changes to a package-relative reference. Repackaging
identical envelopes produces identical envelope bytes. An invalid contract, missing
or corrupt snapshot, escaping relative path, or invalid evidence locator prevents
package publication. Existing output directories are never overwritten. Packaging
copies every cited snapshot, including a whole registry file when cited; allow disk
space for this. It does not bundle uncited acquisition pages or profiles needed for
future re-extraction.

Supported forwarded value options are `--workers`, `--deadline-seconds`,
`--company-timeout`, `--request-timeout`, `--max-pages`, `--max-requests`, `--modules`,
and `--expected-count`. Pass options and values separately, not `--option=value`.
Optional `--wikidata-discovery` explicitly enables candidate discovery; it remains
subject to source access policy and exact-company verification. The wrapper does
not select it by default. Option abbreviations are rejected to prevent accidental
managed-output overrides. Organizer budgets are not known; the example's 720
seconds is illustrative, not an organizer limit.

`--evaluator-timeout-seconds` optionally sets one finite, positive wall-clock budget
shared by both subprocess stages. It starts when the wrapper enters `main` and
covers input/output setup, bulk preprocessing, research, export, evidence copying
and audits. There is no default. `--deadline-seconds` remains the runner's research
budget. Installation, interpreter startup, final process reaping/status reporting,
CPU, memory, disk capacity and API cost are not bounded by this option. Measure
resources on the target host before declaring organizer compliance.

The wrapper requires POSIX. It starts each stage in a new session and kills that
stage's process group on timeout, interruption, failure or stage completion,
including inherited worker descendants. Current runner workers inherit this group;
processes that deliberately detach into another session are outside this guarantee.
No runner change is needed for the current worker model.

`evaluator-status.json` is atomically saved beside the acquisition outputs. Only
`status: completed` and `package_accepted: true` describe a completed audited
wrapper run. Positive subprocess exit codes are preserved; signal exits use the
shell convention `128 + signal` and retain the negative raw subprocess return code
in the report. Timeout exits 124 with `status: timed_out`; interruption exits 130.
Spawn errors fail with exit 1. Invalid wrapper arguments exit 2 before creating a
run directory. Invalid runner inputs/options fail in the batch stage and skip
packaging. Existing output directories are refused.

Failed and timed-out runs retain acquisition/partial artifacts for diagnosis; they
are not accepted evaluator runs even if a package rename raced with the deadline.
Killing a packaging process may leave a hidden `.signalpost-package-*` staging
directory. Normal packaging exceptions clean staging and never publish a partial
package. Preserve original acquisition data. Relocation audits check every locator,
including repeated evidence IDs across envelopes. Audit report destinations may
not overwrite envelopes, the organisation batch or cited source bytes.

## Package an existing acquisition without network

```sh
.venv/bin/python scripts/package_submission.py \
  --input out/current-run/envelopes.jsonl \
  --organisations /path/to/official-batch.jsonl \
  --output-dir out/portable-copy
```

For relative input evidence paths, the default root is the input file's directory;
use `--snapshot-root` when those references were intentionally based elsewhere.
Absolute acquisition paths remain supported. Relative paths and symlinks escaping
an explicit root are rejected.

Move the package to another machine or directory, then audit it from any working
directory using the project installation:

```sh
.venv/bin/python scripts/audit_submission.py \
  --input /new/location/package/envelopes.jsonl \
  --organisations /new/location/package/organisations.jsonl \
  --report out/relocated-audit.json
```

The audit checks bytes, locators and schema/batch membership. It does not establish
independent exact-company precision, recall, source rights, or an official score.
The manifest records file hashes; the evidence auditor does not itself authenticate
or compare the manifest's envelope/batch hashes against a trusted external copy.

## Refresh scope

Existing `run_competition_batch.py --previous-output` accepts acquisition envelopes
whose snapshot paths still resolve. The new wrapper intentionally does not expose
refresh/resume options. Do not feed a relocated portable package directly to
`--previous-output`: refresh still resolves relative paths against its process
working directory, not the previous envelope directory. Preserve original
acquisition profiles/envelopes for refresh and re-extraction. Packaged envelopes
include retained prior sources, and offline relocation audit verifies them.

## Offline verification

```sh
.venv/bin/python -m unittest discover -s tests -p test_packaging.py -v
.venv/bin/python -m unittest discover -s tests -p test_evaluator_reliability.py -v
```

Tests cover relocation after acquisition deletion, retained refresh history,
idempotent repackaging, corruption, duplicate/mismatched batches, containment and
symlink escape, a synthetic 1,101-company failed batch, and the complete evaluator
command on a two-company offline registry fixture (`--modules ''`). Existing batch
isolation checks also exercise a synthetic 1,200-company batch. These do not replace
a fresh live 100-company smoke report or an organizer official run.

Reliability tests also exercise actual sleeping stage processes and descendants,
shared stage deadlines, unrelated-process survival, real exit/signal codes, invalid
options/inputs, report overwrite prevention, copy failures, malformed locators and
relocated DOM/JSON-LD events with retained refresh history and tampering negatives.
