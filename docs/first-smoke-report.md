# First live 100-company smoke — 13 October 2026

The local smoke completed with **100 inputs, 100 terminal envelopes, no unfinished
companies, and an accepted audited evidence package**. This is a reproducible
baseline, not an official score or proof of 65-point qualification.

| Result | Measured outcome |
| --- | ---: |
| Whole evaluator wall time, including packaging | 596.945 seconds (9m 57s) |
| Acquisition/batch wall time | 593.516 seconds |
| Budgeted requests, including DNS validation | 1,796 |
| Received source and DNS bytes | 16,460,092 |
| Paid API cost per 100 companies | $0 |
| Company runtime p50 / p95 | 38.727 / 91.775 seconds |
| Maximum measured company runtime | 150.655 seconds |
| Final accepted websites | 4/100 |
| Dated job / news claims | 0 / 0 |
| Companies with supported revenue claims | 90/100 |
| Roles / registered workplaces available | 100/100 each |
| Final evidence audit | 411 snapshots, 3,101 locators, zero errors |

The machine-readable report is [first-smoke-report.json](first-smoke-report.json).
Exact input IDs are [first-smoke-input.jsonl](first-smoke-input.jsonl). API cost
excludes hosting, compute, storage and transfer. No runtime generative model,
paid search provider, or optional Wikidata route was used.

## Input and validation

Both Builderr public-universe hashes match the published evaluation contract,
and the archive contains exactly 411,160 rows. One hundred companies were selected
by stable hash rank with seed 20261013. The previous 24 development and 24 holdout
IDs were excluded, as were known holdout registrable domains. Unknown holdout
hosts remain unknown; no holdout research was performed. This is a sample from
the filtered public universe, not Builderr's official batch.

The fresh official BRREG CSV snapshot is 154,951,361 compressed bytes, with SHA-256
`511f437caeccc62aa75c3208b3eaa6db6f5f697cc4a4db70806796a754bc8fca`.
The full streaming parse completed, checking gzip integrity. This current local
identity snapshot does not replace the organizer's supplied frozen snapshot.

Locked installation and all **245 tests** pass in a fresh source directory with
an initially empty virtual environment. The final runtime source fingerprint
matches that verified source copy. The offline refresh finds both expected changes,
no false changes, and an idempotent rerun. A remote clean clone at the eventual
submitted commit remains to be validated after code publication.

## Live command and observed budgets

The completed acquisition used:

```sh
.venv/bin/python scripts/evaluate_signalpost.py \
  --organisations out/first-smoke-prep/smoke-companies.jsonl \
  --bulk out/first-smoke-prep/brreg-enheter.csv \
  --output-dir out/smoke-20261013-v2 --run-id smoke-20261013-v2 \
  --expected-count 100 --workers 8 --deadline-seconds 1500 \
  --company-timeout 150 --request-timeout 15 --max-pages 6 \
  --max-requests 60 --evaluator-timeout-seconds 1800
```

The cloud injected `SIGNALPOST_DNS_OVER_HTTPS=1`; public HTTPS DNS requests consume
the same request/time budgets and are counted as operations, not claim evidence.
Robots, TLS, public-address, exact-identity and redirect checks remain enabled.
Company timeout is a session deadline; the measured maximum slightly exceeded
150 seconds due to blocking operations. The whole evaluator has process-group
supervision. Official-scale budget compliance has not been established.

The first 8-second-request-budget attempt was intentionally interrupted after
diagnosing DNS/throttle contention. It is preserved in `out/smoke-20261013/` with
an interrupted evaluator status. It is not the completed smoke result.

## Review and final export

Original live acquisition accepted five websites. Assistant review found three
issues: an appointment-booking URL matching `stilling`, a shared one-word brand
whose site ownership was insufficiently proven, and generic footer citations for
contact-based identity proofs. The code now excludes the false careers category,
abstains on the insufficient brand proof, and cites the actual name/contact nodes.

The final export re-extracts the same retained pages and makes **zero new HTTP
requests**. It records separate acquisition/export code fingerprints. Four sites
remain accepted; statutory claims are retained. Both original acquisition and
reviewed outputs are preserved. This is not a second live run or an independent
human precision assessment. All other website outcomes remain explicit:
79 not_available, eight ambiguous, six failed, and three blocked. Bounded missing
results are not proof of absence. Financial missing values remain distinct from zero.

## Artifacts and first-submission status

- `out/smoke-20261013-v2/`: immutable live profiles, snapshots, report and package.
- `out/smoke-20261013-final/`: reviewed envelopes, export report and audited package.
- `out/first-smoke-prep/`: verified inputs, dataset hashes, sampling manifest,
  dependency-license metadata, and current organizer contract/page snapshots.
- Raw company page snapshots remain ignored/private; public report contains
  aggregate results and provenance rather than redistributing site content.

The 100-company smoke deliverable is complete. Next release steps are a reviewed
exact repository commit, publication and clean-clone validation, then submission.
The implementation is still uncommitted; GitHub main is the original import.
No submission or official result has occurred. Low external coverage remains the
largest known performance limitation; first qualification is not promised.
