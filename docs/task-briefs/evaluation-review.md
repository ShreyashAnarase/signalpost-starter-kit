# Chat assignment: evaluation and human review preparation

Follow ../parallel-chat-plan.md, including its exact file ownership. This task
can finish offline and does not depend on the live worker succeeding.

Read ../strategy-evaluation.md. Human labels are currently missing. Known-domain
separation passes, but 12 companies in each split lack known hosts. Do not label
unresolved companies as negatives or inspect holdout research outcomes.

1. Review the comparator for missing-data, population/pool consistency, review
   completeness and promotion-gate correctness. Fix demonstrated bugs in owned
   files and add focused regression checks. Local reviewed-pool recall is not
   the official cumulative-pool score.
2. Build scripts/prepare_human_review.py to turn development envelopes plus
   retained evidence into a small review packet and unfilled label template.
   Include company, claim ID/value, source URL/date, snapshot hash/path and exact
   locator/span. Verify paths safely and refuse holdout organisations. Use only
   local bytes; do not make network requests or modify the evidence auditor.
3. Leave exact identity, claim support and material-evidence judgments unknown
   until a reviewer supplies them. Never manufacture reviewer names/times or mark
   assistant labels as independent human labels. Document how to import reviews
   into the comparator and how to find opportunities beyond successful outputs.
4. Test using explicitly synthetic fixtures, including unavailable claims,
   missing snapshots, malformed membership and an assistant-only review.

Acceptance: safe reproducible packet generation, unfilled human-review template,
focused checks pass, incomplete review cannot promote a strategy. Clearly expose
the remaining human review and unknown-host dependencies.

Use out/evaluation-review/ for artifacts. Save
docs/task-results/evaluation-review.md with the smallest concrete human review
step. Do not change frozen splits or invent a new official scoring threshold.
