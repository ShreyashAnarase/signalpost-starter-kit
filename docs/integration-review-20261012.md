# Three-chat integration — 12 October 2026

The uploaded live-validation, evaluation/human-review, and packaging/reliability
patches are integrated into this coordinator checkout. Existing work is preserved;
no commits, push, paid API calls, publication, or submission occurred.

## Transfer and review

- Every destination was checked against assigned ownership. File sets do not
  overlap between the three workers. `git apply --check` passed for each patch.
- The original live patch matches its declared SHA-256. The normalized evaluation
  patch also matches its declared SHA-256 after restoring one markdown fence
  context line from the known original documentation. No code was inferred.
- Packaging supplied no verifiable declared hash in the uploaded text. Its patch
  parses completely, applies against this prepared snapshot, and passes combined
  validation. Saved transfer/extracted hashes are in
  `out/integration-review/transfer-manifest.json`.
- Initial owned-file copies and extracted patches are retained in ignored
  `out/integration-review/` for review and recovery.

## Delivered

| Track | Integrated behavior |
| --- | --- |
| Live development validation | One to four frozen development companies; supervised budgets; exact public identity gate; snapshots, pre-DNS attempts and failure telemetry; one terminal envelope per input |
| Evaluation and human review | Blank portable review packet with contained/hash-checked bytes; stronger provenance, scope, pool and refresh completeness checks; unknown reviews cannot promote |
| Packaging and reliability | Explicit whole-evaluator timeout; process-group/descendant cleanup; preserved error exit statuses; atomic evaluator status; stronger malformed locator/CSV/cross-envelope evidence auditing |

The first combined run found nine setup errors: the new live-runner tests assumed
an ignored output parent existed. Test setup now creates its own parent; it does
not depend on worker-generated artifacts surviving transfer.

## Coordinator validation

- **205 tests passed**, including actual timeout/process-tree tests, offline
  evaluator commands, review packet generation and evidence/path corruption cases.
- Offline refresh: both expected changes, zero false changes, idempotent rerun.
- Packaged dated-event evidence audit: three envelopes, eight unique snapshots,
  11 locators checked, zero errors. These are synthetic event fixtures.
- Frozen split audit: no organisation or known registrable-domain overlap. Twelve
  unknown hosts per split still prevent claiming full host separation.
- Whitespace check passes. Worker-only test counts do not replace these combined
  checks. Human labels, official precision/coverage and qualification remain unset.

## Current network diagnosis

The integrated bounded live run selected development organisations 985215294 and
984589344. Both failed local DNS before HTTP; it produced two failure envelopes,
zero acquisitions, zero cited evidence and complete failure telemetry. A passing
failure-path audit is not successful research or proof of absent facts.

Runtime status now lists `data.brreg.no`, `www.nf.no`, and `www.nfs.no` with current
observations, but network enforcement state remains `unknown`.

A fresh inherited-proxy HTTPS request to the registry **succeeded** and returned
the exact identity of 984589344. The previous universal proxy denial is therefore
not the current diagnosis. Local `socket.getaddrinfo` fails for registry and both
company hosts, including when checked outside the command sandbox. The crawler
requires public-DNS validation before following URLs; that safeguard was retained.
No proxy bypass, DNS/route override, or verification disablement was used.

Artifacts: `out/live-development-review/integrated-20261012/` (profiles, envelopes,
telemetry, report and audit), `out/integration-review/registry-probe.json` (diagnostic
public API response, not published claim evidence), refresh and dated-event audits.

## First-submission path

1. Restore functioning DNS in the managed executor and rerun the same bounded
   command. The required domains are already configured; duplicating the earlier
   allowlist edit is not a demonstrated remedy. Preserve/publish the integrated
   snapshot before a restart that may replace filesystem state. Environment
   publication is not a competition submission or repository commit.
2. Once the actual crawler acquires and audits real evidence, prepare the fresh
   required 100-company smoke. Avoid spending on extra connectors before proving
   the core run. Current default third-party API estimate is $0, excluding hosting.
3. Freeze a reviewed exact commit and complete `docs/first-submission-plan.md`.
   Obtain explicit authorization before submitting. The user wants an official
   result first, then improvements; do not delay for every optional experiment.

Remaining limitations: fresh live smoke unrun, independent human reviews missing,
unknown-host separation unresolved, relocated package-as-refresh-input unsupported,
organizer resource compliance unverified, and no official result or guaranteed
65-point qualification. Paid providers are neither required nor enabled.
