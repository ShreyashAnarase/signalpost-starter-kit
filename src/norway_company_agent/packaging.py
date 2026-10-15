"""Audited, relocatable evidence packages; acquisition artifacts remain untouched."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .audit import audit_envelopes, resolve_snapshot_path


def _digest(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def package_submission(envelopes: list[dict], organisations: list[str], output_dir: str | Path,
                       *, snapshot_root: str | Path | None = None) -> dict:
    """Copy all cited bytes, including refresh history, then audit before publishing.

    The output must be new. Relative input references resolve against snapshot_root
    when supplied, otherwise the caller's working directory. No source bytes,
    evidence IDs, dates, locators, or claim values are rewritten.
    """
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(f'Package directory already exists: {output}')
    initial = audit_envelopes(envelopes, organisations, snapshot_root=snapshot_root)
    if not initial['passed']:
        raise ValueError(f'Input evidence audit failed: {initial}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.signalpost-package-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'package'
        (staging / 'snapshots').mkdir(parents=True)
        portable = copy.deepcopy(envelopes)
        snapshots = {}
        for envelope in portable:
            for source in envelope['evidence']:
                original = resolve_snapshot_path(source['snapshot_path'], snapshot_root)
                digest = source['content_sha256']
                # Fixed names preserve gzip/plain CSV autodetection by iter_bulk,
                # which reads magic bytes rather than trusting extensions.
                relative = f'snapshots/{digest}.bin'
                destination = staging / relative
                if not destination.exists():
                    shutil.copyfile(original, destination)
                if _digest(destination) != digest:
                    raise ValueError('Snapshot changed during packaging or copied bytes are corrupt')
                source['snapshot_path'] = relative
                snapshots[relative] = {'content_sha256': digest, 'bytes': destination.stat().st_size}
        final = audit_envelopes(portable, organisations, snapshot_root=staging)
        if not final['passed']:
            raise ValueError(f'Packaged evidence audit failed: {final}')
        envelope_path = staging / 'envelopes.jsonl'
        envelope_path.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n'
                                       for row in portable), encoding='utf-8')
        batch_path = staging / 'organisations.jsonl'
        batch_path.write_text(''.join(json.dumps({'organisation_number': org}) + '\n' for org in organisations), encoding='utf-8')
        manifest = {'format': 'signalpost-evidence-package-v1',
                    'snapshot_path_base': 'package_directory', 'envelopes': len(portable),
                    'envelopes_sha256': _digest(envelope_path), 'organisations_sha256': _digest(batch_path),
                    'snapshots': snapshots, 'audit': final,
                    'boundary': 'Portable retained evidence; not an official score or independent identity review.'}
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Rename only a complete, audited package. Never merge into existing output.
        if output.exists():
            raise FileExistsError(f'Package directory already exists: {output}')
        staging.rename(output)
    return manifest
