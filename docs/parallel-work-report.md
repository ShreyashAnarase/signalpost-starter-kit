# Parallel implementation handoff

Subsequent jobs/news work and the current 163-test validation are documented in
[dated-events-progress.md](dated-events-progress.md). The parallel-track results
below remain the baseline for that later milestone.

Three internal agents implemented separate tracks in the existing cloud checkout.
These were agents within the coordination chat, not separate UI chats. No commits,
submission, publication, paid services, bulk download, or holdout crawl occurred.

## Delivered

1. Packaging: `scripts/evaluate_signalpost.py` runs the batch and packages cited
   evidence. `scripts/package_submission.py` copies immutable source bytes into a
   relocatable bundle. The auditor resolves package-relative paths. See
   [submission-packaging.md](submission-packaging.md) for commands and scope.
2. Evaluation: `scripts/evaluate_strategy.py` audits split membership and known
   registrable domains, compares reviewed local opportunity coverage using the
   70/30 weighting, and applies explicit promotion gates. Unreviewed claims remain
   unknown; assistant review cannot satisfy promotion. See
   [strategy-evaluation.md](strategy-evaluation.md) for labels and review workflow.
3. Discovery: optional `--wikidata-discovery` adds exact-organisation candidate
   lookup when registry/email routes yield none. Existing site identity gates
   still decide publication. Default behavior is unchanged. See
   [website-discovery.md](website-discovery.md) for provenance and limitations.

## Combined validation

`.venv/bin/python -m unittest discover -s tests -v` passed all 155 tests.
The offline refresh replay found both expected changes, no false changes, and
passed idempotence. Packaging tests include relocation after deleting originals,
retained prior evidence, corruption/path escape rejection, a synthetic
1,101-company failure batch, and the full evaluator command with offline inputs.
These checks do not establish live company coverage or an official score.

The real development/holdout split audit found no organisation or known
registrable-domain overlap. Each split has 12 companies with unknown website
hosts: complete host separation is unresolved. Outputs are in ignored
`out/strategy-split-audit.json` and `out/refresh-demo.json`.

## Remaining priorities

1. Validate Wikidata property semantics and service access policy using reachable
   authoritative documentation before enabling live discovery. Cloud proxy
   requests returned HTTP 403. Required destinations for that validation and
   provider are `www.wikidata.org`, `www.mediawiki.org`, `query.wikidata.org`.
   No network configuration was broadened. Measure any gain on development inputs;
   fixture success is not real coverage evidence.
2. Reacquire bounded development evidence, obtain independent human identity and
   support labels, and establish reviewed opportunities beyond successful outputs.
   Precision review alone cannot estimate recall. Resolve host split uncertainty
   without tuning on holdout outcomes.
3. The first dated jobs/news milestone is implemented with precise evidence and
   refresh regressions; validate it on reachable development sites and expand
   only from measured failures. See the dated-events report.
4. Complete reliability/resource-budget validation and a fresh 100-company live
   smoke with every output and evidence locator audited. Verify organizer budgets
   and current batch requirements before declaring evaluator compliance.
5. Adapt presentation to current envelopes after interfaces stabilize. Prepare an
   exact commit and submission package only after integration checks.

Portable bundles currently support offline audit; passing relocated package
envelopes directly to batch `--previous-output` is not supported. Keep resolving
acquisition envelopes/profiles and snapshots for refresh/re-extraction. Candidate
provider provenance is retained in acquisition profiles, not bundled as claim
evidence. The research deadline is not a complete preprocessing/packaging timeout.

Future chats should read `AGENTS.md`, the latest `HANDOFF.md` continuation, this
report, and the relevant track document. Existing source changes are uncommitted;
preserve them and inspect status before assigning additional file ownership.
