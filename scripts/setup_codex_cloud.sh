#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# A clean evaluator may have a read-only home. Keep installation caches inside
# the ignored, writable project directory instead of relying on prior user state.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.tools/uv-cache}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.tools/pip-cache}"

# Keep the bootstrap tool inside the already-ignored .tools directory.
if command -v uv >/dev/null 2>&1; then
  uv_bin="$(command -v uv)"
else
  python3 -m venv .tools/codex-uv
  .tools/codex-uv/bin/python -m pip install 'uv==0.12.22'
  uv_bin="$PWD/.tools/codex-uv/bin/uv"
fi

"$uv_bin" sync --locked
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
