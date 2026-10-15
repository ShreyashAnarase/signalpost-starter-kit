# Separate chat ownership plan

Use three fresh chats, each assigned exactly one brief below. This chat remains
the coordinator. New UI chats are opened by the user; internal subagents do not
provide the same separate conversation context.

Before launching, publish the prepared cloud environment through its settings so
future tasks can restore the current code and these briefs. The current changes
are uncommitted and cannot be assumed to exist in a fresh clone of GitHub main.
Every worker must verify the latest handoff and its brief are present. If missing,
stop and report that the task has the wrong snapshot; do not rebuild from old main.
Selecting the same named environment does not prove chats share a live filesystem.

## Common worker instructions

Read AGENTS.md, the latest HANDOFF.md continuation, this plan, and your assigned
brief. Use repository-relative paths: the current checkout is
`/workspace/signalpost-starter-kit`. Read relevant task documentation only; do not
request the full conversation. Use the existing checkout, not a new worktree.

Inspect initial status and diffs. Previous uncommitted work is intentional:
packaging/evaluation/discovery and dated events were implemented and 163 tests
passed. Preserve that work. Announce your exact owned file list, then proceed
within the assignment. Do not require another user confirmation for assigned work.
If another file is needed, stop before editing it and name the dependency.

Do not edit another worker's files, AGENTS.md, HANDOFF.md, this plan, dependency
declarations, lockfiles, strategy versioning, frozen data splits, or other briefs.
No reset, stash, branch switch, commit, push, submission, publication, paid calls,
secret collection, or holdout crawl. Do not spawn additional workers.

If filesystem is shared, file ownership prevents simultaneous writes. If separate
checkouts are restored, return a patch as well as your report for integration.
Keep generated artifacts in your assigned ignored output directory. Only the live
validation worker makes external research requests or saves network requirements.
Other workers can complete their offline assignments even if live access fails.

Run focused meaningful checks. One full regression run after integration belongs
to the coordinator. Save a concise result report in your assigned task-results
file: changed files, commands and outcomes, artifact paths, failures, limitations,
next dependencies, and whether your filesystem was shared or isolated (unknown
if not established). Report only your changes. Do not claim an official score.

## Ownership

| Chat | Brief | Existing files it may edit | New files it may create |
| --- | --- | --- | --- |
| Live validation | task-briefs/live-validation.md | None | scripts/run_development_review.py, tests/test_development_review.py, docs/live-development-review.md, docs/task-results/live-validation.md |
| Evaluation and review | task-briefs/evaluation-review.md | scripts/evaluate_strategy.py, tests/test_strategy_evaluation.py, tests/fixtures/strategy-evaluation.json, docs/strategy-evaluation.md | scripts/prepare_human_review.py, tests/test_human_review.py, docs/task-results/evaluation-review.md |
| Packaging and reliability | task-briefs/packaging-reliability.md | src/norway_company_agent/packaging.py, src/norway_company_agent/audit.py, scripts/package_submission.py, scripts/audit_submission.py, scripts/evaluate_signalpost.py, tests/test_packaging.py, docs/submission-packaging.md | tests/test_evaluator_reliability.py, docs/task-results/packaging-reliability.md |

Production discovery/site extraction/pipeline/runner changes remain with the
coordinator until concrete review findings justify the next bounded assignment.

## Integration sequence

1. Workers perform the three assignments concurrently.
2. Bring their reports and, for isolated checkouts, patches to the coordinator.
3. Coordinator reviews/integrates changes, runs the full suite and evidence audit,
   and records one handoff. Do not combine scores from different input snapshots.
4. Human review and observed live failures guide the next discovery/extraction
   changes; then validation, frozen holdout, and fresh 100-company smoke follow.
