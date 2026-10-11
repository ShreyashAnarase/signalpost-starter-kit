# Working on Signalpost

Read `HANDOFF.md` (latest continuation update first) and
`docs/coverage-progress-20261012.md` before continuing development. Historical
absolute paths and local `out/` artifacts in those documents are not available in
a fresh cloud checkout. Work relative to the repository root.

Keep changes focused on the user's task. The current entry point is
`scripts/run_competition_batch.py`; parts of README and OUTPUT_CONTRACT describe
legacy behavior. Preserve exact legal-company attribution, evidence locators,
snapshot integrity, missing-value semantics, and one terminal envelope per input.
Do not infer facts from model guesses or weaken identity gates for coverage.

## Setup and checks

- Python 3.12+ is required. Run `bash scripts/setup_codex_cloud.sh` to install
  dependencies from `uv.lock` without rewriting it.
- Run `.venv/bin/python -m unittest discover -s tests -v` for regression checks.
- Offline smoke: `.venv/bin/python scripts/run_refresh_replay.py --manifest tests/fixtures/refresh-snapshots.json --output out/refresh-demo.json`.
- No API credentials or bulk registry download are needed for these checks.
- Core modules live in `src/norway_company_agent/`; command wrappers live in
  `scripts/`. The project uses `uv` with `package = false`.

## Data and live work

Large downloaded datasets, environments, caches, and generated `out/` evidence are
intentionally ignored by Git. See README for data download and live-run commands;
do not assume prior local evidence exists. Keep the untouched holdout separate
from development. Live research needs network access to registry and company
sites. No paid API budget or competition submission is authorized by setup alone.
Never commit credentials or fabricate evidence or official scores.
