# Local strategy evaluation

`scripts/evaluate_strategy.py` compares current envelopes against a separately
reviewed local opportunity pool. It reports no official score or qualification.
The organizer's cumulative verified union, budgets and review cannot be reproduced
from these local labels. Legacy evaluation scripts remain historical and their
qualification flags must not drive current strategy promotion.

## Frozen inputs and separation

```sh
.venv/bin/python scripts/evaluate_strategy.py \
  --development data/coverage-review-v1/development.jsonl \
  --holdout data/coverage-review-v1/holdout.jsonl \
  --output out/evaluation/split-audit.json
```

This reads only membership and supplied known website metadata; it never crawls.
Registrable domains use the existing bundled suffix data, with no DNS or suffix
list fetch. `known_websites` can supply already-known URLs, but do not discover
holdout URLs to improve this audit. Missing hosts remain explicitly unknown:
passing known-domain checks does not prove complete host separation. Unknown hosts
block promotion readiness; resolve through independently established permitted
metadata without tuning on holdout, or report the remaining blocker. Verify frozen
input hashes against the manifest before an experiment. Do not tune on holdout.

The existing development/holdout sets each contain 24 diagnostic companies, not a
population sample. At initial inspection their manifest hashes matched, IDs were
disjoint, and each split had 12 missing registry websites. Historical `out/`
evidence and six assistant-reviewed positive matches are absent in a fresh
checkout; they are not independent labels.

## Review document

Supply one JSON document containing these lists. All rows require
`review: {kind: "independent_human" | "assistant", reviewer: "identifier",
reviewed_at: "ISO-8601 timestamp"}`. Provenance is declared, not independently
authenticated by this tool. Synthetic examples in tests are never usable gold.
Reviewer identifiers must be nonempty strings and review times must be parseable
ISO-8601 timestamps with a timezone. Null or malformed provenance is unreviewed.

- `opportunities`: `id`, `organisation_number`, `field`, `evidence` containing
  source URL/identifier, retrieval time, reporting/effective date if relevant,
  content hash, precise span/locator and extraction method. Each opportunity is
  one independently established company-field fact. No candidate/search snippet
  may establish a positive opportunity. Deduplicate equivalent facts before review.
  Required evidence keys are `source_url`, `retrieved_at`, `content_sha256`
  (64 lowercase hex digits), `extraction_method`, `claim_span` (or `span`), and
  `source_locator` with a `type`. Structural presence does not establish support;
  the human reviewer must verify the evidence.
- `judgments`: `run` (default `baseline` or `challenger`), `organisation_number`,
  `claim_id`, boolean `exact_entity`, `correct`, `evidence_valid`, `material`, and
  optional `opportunity_id`. The reviewer inspects the published claim and retained
  evidence, checks legal ownership/relationships, factual value and period, and
  maps supported positives to opportunity IDs. An unknown judgment must be left
  unreviewed, never encoded as false. Unmatched new discoveries require independent
  verification and addition to the same shared pool for both runs.
- `scope`: company-field review records with `organisation_number`, `field`,
  `search_scope`, `complete_within_scope` and notes. Record unknown/blocked sources,
  methods and cutoff. Completeness is bounded to that search scope, never the web.
- `refresh_judgments`: `run`, `case_id`, `correct`, `false_change`, evidence/notes
  and review provenance. Cover unchanged snapshots, material changes, and failed
  refresh preserving prior evidence. Distinguish measured cases from untested ones.

Default reporting uses independent-human rows only. `--review-mode
assistant_diagnostic` admits assistant rows and always blocks promotion.

Company recall counts reviewed positive companies found; individual recall counts
unique supported opportunity IDs found. Duplicate publications cannot increase
recall. Weighted local coverage is 70% company recall + 30% individual recall per
field. No opportunities means null recall, not zero. Precision uses reviewed
publications; review completeness and unresolved publications appear separately.
Availability/abstention counts do not contribute to recall. Evidence validity is
reviewed validity, not a replacement for the offline byte/locator auditor.

## Comparison and promotion

```sh
.venv/bin/python scripts/evaluate_strategy.py \
  --development data/coverage-review-v1/development.jsonl \
  --holdout data/coverage-review-v1/holdout.jsonl \
  --baseline out/baseline/envelopes.jsonl \
  --challenger out/challenger/envelopes.jsonl \
  --labels out/review/labels.json --policy out/review/policy.json \
  --output out/evaluation/comparison.json
```

Declare policy before evaluating: `target_fields`, `minimum_coverage_gain`,
`maximum_precision_loss`, and `resource_caps` (requests, third_party_cost_usd,
optional cost_per_input_company_usd). For example:

```json
{"target_fields":["official_website"],"minimum_coverage_gain":0.05,
 "maximum_precision_loss":0,"resource_caps":{"requests":300,"third_party_cost_usd":0}}
```

Promotion requires identical input/population and reviewed-pool fingerprints,
complete known host separation, complete runtime observations, complete independent publication review, complete input
membership, no material wrong-company claims or additional wrong-company claims,
complete reviewed material evidence, preserved precision, positive declared
coverage gain without target-field regression, explicit resource caps, and reviewed
perfect refresh correctness with no false changes. Missing telemetry blocks its
resource check; missing refresh labels block refresh verification. Caps are local
experiment policy, not organizer budgets. Even passing promotion is insufficient
for release: run the offline evidence audit, inspect per-field regressions and
review scope, test runtime budgets/clean setup, and reserve holdout until strategy
freeze. Runtime p50/p95 uses measured per-envelope runtime; missing runtime
observations are exposed and suppress aggregate percentiles rather than becoming
zero. Existing production envelopes may default absent telemetry to zero; the
comparator cannot distinguish these defaults from measured zeros. Inspect runner
telemetry completeness before interpreting cost/runtime or promoting a strategy. Successful-envelope fraction is
not proof every source crawl succeeded.
Missing envelope availability or incomplete input membership suppresses the
successful-company fraction instead of counting missing results as failures.

Unfinished opportunity rows block promotion even if dropping them would improve
the measured recall. Each declared target field needs one independently reviewed,
complete bounded search-scope row for every development company; missing,
unfinished or duplicate scope rows cannot establish completeness. This includes
companies without successful outputs. Submitted challenger refresh cases must
all be independently reviewed, have unique case IDs, and pass correctness and
false-change checks. An unreviewed refresh failure cannot disappear from the gate.
These are local completeness gates, not new official scoring thresholds.

## Offline human review packet

```sh
.venv/bin/python scripts/prepare_human_review.py \
  --development data/coverage-review-v1/development.jsonl \
  --holdout data/coverage-review-v1/holdout.jsonl \
  --envelopes out/development/envelopes.jsonl \
  --snapshot-root out/development \
  --run challenger --output-dir out/evaluation-review/challenger-packet
```

Use the directory that actually contains the retained files as `--snapshot-root`.
Relative evidence paths resolve against that root; absolute paths must also stay
inside it after symlink resolution. External paths, holdout companies, split
overlap, duplicate/malformed membership, missing development envelopes, dangling
evidence references and asserted values on unavailable claims are refused before
writing output. Membership is checked before reading evidence bytes. Only local
files are read; URLs are metadata and are never fetched. Outputs must use a new
directory to protect earlier packets and evidence.

`packet.json` contains all development companies, available and unavailable
claims, legal identity, values, effective/reporting dates, exact source URLs,
retrieval dates, hashes, locators and spans. Hash-matching retained bytes are
copied to `snapshots/<sha256>.bin`; paths in the packet resolve relative to its
directory. Original snapshot paths are retained as metadata. Missing or corrupt
bytes appear in `evidence_issues`, suppress `retained_bytes_complete`, and are
never copied as verified evidence. No automatic identity, span-support or
materiality judgment is made. Run the existing offline auditor separately on the
original envelopes. Snapshot copies may be large when a claim cites bulk data.

`labels-template.json` is accepted by the comparator without editing and produces
unknown precision and incomplete review. Every available publication has a blank
judgment; unavailable publications have no fabricated negative judgment. Scope
templates cover every company for the default fields `official_website`,
`job_posting` and `company_news` (override with `--fields`). No opportunities,
refresh verdicts, reviewer names or times are generated.

Copy the template to a separate reviewed file. An independent reviewer supplies
`exact_entity`, `correct`, `evidence_valid`, `material`, and their actual review
provenance after inspecting each claim and retained evidence. Leave uncertain
rows unreviewed, including evidence that is missing. Assistant reviews must use
`kind: "assistant"` and remain diagnostic. To compare two runs, generate one
packet per run, combine their judgment rows into one labels document, establish
one shared deduplicated opportunity pool, and supply actual refresh reviews.
Scope rows are shared and must be deduplicated by company and field. Pass that
document to `evaluate_strategy.py --labels ...` using the matching
`--baseline-name` and `--challenger-name`. Do not merge unreviewed templates into
gold labels as if they were completed reviews.

Find opportunities beyond successful outputs by independently reviewing the
same declared development sources for every company-field pair, recording source
boundaries, cutoff, inaccessible pages and unknown ownership in `scope`. Add only
supported exact-company facts to `opportunities`; map matching publication
judgments to those IDs. An unresolved company or a bounded search that found
nothing is not a web-wide negative. This worker does no external research and
does not inspect holdout outcomes. The 12 unknown hosts in each frozen split
remain a separate promotion blocker.

Smallest next human task: reacquire or package the 24 development outputs and have
an independent reviewer inspect every published website identity and evidence,
starting with assistant-accepted positives and rejected ownership conflicts. Then
independently establish website opportunities for unresolved development companies
and dated jobs/news opportunities across the same development set. Labeling only
our successful outputs supports reviewed precision, not discovery recall.

Run dedicated checks:

```sh
.venv/bin/python -m unittest discover -s tests -p test_strategy_evaluation.py -v
.venv/bin/python -m unittest discover -s tests -p test_human_review.py -v
```
