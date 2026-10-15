# Evaluation and human review preparation result — 12 October 2026

Completed within the assigned ownership. Shared versus isolated filesystem:
**unknown**; an integration patch is supplied against this task's initial file
bytes. No additional workers were spawned.

## Snapshot verification

Before editing, read AGENTS.md, HANDOFF.md (latest cloud continuation first),
coverage-progress-20261012.md, parallel-chat-plan.md, the evaluation-review brief,
and strategy-evaluation.md. The current snapshot contains the dated-events
`free_sources_v3_dated_events` work and intentional uncommitted changes described
by the latest handoff. Initial status and diffs were inspected and preserved.
Both frozen split SHA-256 hashes match data/coverage-review-v1/manifest.json.
Initial owned-file bytes and repository file hashes are retained under
out/evaluation-review/baseline/ for integration and ownership verification.

## Changes

- scripts/evaluate_strategy.py: null review provenance is accepted as unknown;
  malformed reviewer/time provenance cannot count as independent review. Reject
  duplicate/malformed input populations and target fields, duplicate scope and
  refresh IDs, and placeholder opportunity evidence. Duplicate memberships no
  longer establish complete host separation. Missing envelope availability or
  membership suppresses successful-company fraction instead of becoming zero.
  Promotion requires complete submitted opportunity reviews, bounded independent
  scope review for every company/target field, and review of every submitted
  challenger refresh case. Partial publication review still cannot promote.
- scripts/prepare_human_review.py: offline packet CLI with exact development
  membership; holdout is refused before evidence reads. All absolute, relative
  and symlink-resolved snapshot paths must stay in the explicit evidence root.
  Hash-matching snapshots are copied under portable content-addressed paths;
  missing/corrupt bytes stay explicit. Company, claim/value/date, original source
  URL/date/hash/path and locator/span are retained. Unavailable claims stay visible
  without invented negative labels. All judgments and provenance remain blank.
- tests/test_strategy_evaluation.py, tests/test_human_review.py and
  tests/fixtures/strategy-evaluation.json: focused regressions and explicitly
  synthetic fixtures, including complete synthetic scope records. Synthetic
  reviewer metadata remains identified as test-only and is never exported as
  real human review.
- docs/strategy-evaluation.md: packet generation, safe path semantics, import
  instructions, completeness gates and development opportunity-review workflow.
- docs/task-results/evaluation-review.md: this result report.

## Validation and artifacts

Commands executed from the repository root:

```sh
.venv/bin/python -m unittest discover -s tests -p test_strategy_evaluation.py -v
.venv/bin/python -m unittest discover -s tests -p test_human_review.py -v
git diff --check
.venv/bin/python scripts/evaluate_strategy.py \
  --development data/coverage-review-v1/development.jsonl \
  --holdout data/coverage-review-v1/holdout.jsonl \
  --output out/evaluation-review/split-audit.json
.venv/bin/python scripts/prepare_human_review.py \
  --development out/evaluation-review/synthetic-inputs/development.jsonl \
  --holdout out/evaluation-review/synthetic-inputs/holdout.jsonl \
  --envelopes out/evaluation-review/synthetic-inputs/envelopes.jsonl \
  --snapshot-root out/evaluation-review/synthetic-inputs \
  --run challenger --output-dir out/evaluation-review/synthetic-packet
.venv/bin/python scripts/evaluate_strategy.py \
  --development out/evaluation-review/synthetic-inputs/development.jsonl \
  --holdout out/evaluation-review/synthetic-inputs/holdout.jsonl \
  --baseline out/evaluation-review/synthetic-inputs/envelopes.jsonl \
  --challenger out/evaluation-review/synthetic-inputs/envelopes.jsonl \
  --labels out/evaluation-review/synthetic-packet/labels-template.json \
  --policy out/evaluation-review/synthetic-inputs/policy.json \
  --output out/evaluation-review/synthetic-unreviewed-comparison.json
```

Final outcomes: **19 comparator tests + 9 packet tests pass**; whitespace check
passes. The synthetic CLI packet has two claims, one blank publication judgment,
one verified snapshot, and no evidence issues. The blank-template CLI comparison
has null precision and recall and promotion_passed=false. Tests verify repeated
packet reproducibility, missing/corrupt snapshots, absolute/traversal/symlink
escapes, unavailable assertions, malformed membership, holdout refusal, safe
output refusal, exact metadata, and assistant-only review rejection. Synthetic
fully reviewed comparator fixtures still pass the existing declared local policy.

Artifacts, all under out/evaluation-review/:

- test_strategy_evaluation.log and test_human_review.log: final focused checks.
- split-audit.json: real frozen membership/known-host audit only.
- synthetic-inputs/: synthetic local inputs and explicitly diagnostic policy.
- synthetic-packet/: packet.json, labels-template.json and retained snapshot.
- synthetic-unreviewed-comparison.json: unknown metrics and blocked promotion.
- integration.patch: only this worker's seven owned files, compared to initial
  bytes rather than Git HEAD (preserves earlier uncommitted implementations).
- ownership-check.json: hashes of unchanged pre-existing files outside ownership.

An initial focused run failed the old synthetic promotion fixture after scope
completeness became required; adding explicit synthetic scope evidence corrected
the fixture. No unresolved validation failures remain. A dry-run confirmed the integration
patch applies to the initial owned-file snapshot. The optional projectless output
mirror is unavailable (its mount is absent/read-only in this executor); all
requested results remain saved at the assigned repository paths. The coordinator owns the
full regression run after integration; it was not repeated here.

## Limits and next dependency

No external research requests, holdout outcomes, paid calls, submissions, commits,
pushes or publications. Snapshot hashes check retained bytes; they do not prove
legal identity, factual support or locator correctness. Review provenance is
declared, not authenticated. The existing evidence auditor remains unchanged and
should be run separately on real envelopes. Default production telemetry can
still hide missing measurements behind zeros; that production change is outside
ownership. No official score or cumulative-pool recall is claimed.

Known-domain separation passes, but **12 development and 12 holdout companies
have unknown hosts**, so complete host separation remains false. No real human
labels or historical retained development envelopes are available to this worker;
the saved packet is explicitly synthetic. Real packet generation depends on the
coordinator/live worker providing permitted development envelopes and their
retained local bytes. Scope completeness is bounded to declared sources and does
not turn unresolved companies into negatives.

Smallest concrete human review step: after local development evidence is
available, generate its packet and ask an independent reviewer to inspect one
published official_website claim against its legal identity and retained source,
then fill that one judgment's four booleans and their actual reviewer/time.
Leave every other judgment unknown. Expand to all publications, independently
establish opportunities and bounded scope for unresolved development companies,
and supply real refresh reviews before considering local promotion. Unknown-host
separation remains a separate dependency; do not crawl holdout to resolve it.
