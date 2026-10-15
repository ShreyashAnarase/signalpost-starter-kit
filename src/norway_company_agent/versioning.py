"""Content fingerprints independent of checkout location and file timestamps."""
from __future__ import annotations

import hashlib
from pathlib import Path

STRATEGY_VERSION = "sources_v9_live_nav_ad_content_and_candidates"


def source_fingerprint(root: Path) -> str:
    paths = sorted({*root.glob("src/**/*.py"), *root.glob("scripts/**/*.py"),
                    root / "pyproject.toml", root / "uv.lock"})
    digest = hashlib.sha256()
    for path in paths:
        if path.is_file():
            name = path.relative_to(root).as_posix().encode()
            body = path.read_bytes()
            digest.update(len(name).to_bytes(8, "big") + name)
            digest.update(len(body).to_bytes(8, "big") + body)
    return digest.hexdigest()
