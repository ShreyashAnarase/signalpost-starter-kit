"""Declared official-feed candidate hints; never reusable published job facts."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from .evidence import utc_now

SCHEMA = "signalpost-nav-candidates-v1"
FEED = "https://pam-stilling-feed.nav.no/api/v1/feed"
MAX_BYTES = 32_000_000
MAX_ENTRIES = 50_000
UUID = re.compile(r"^[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$")


def valid_time(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False


def entry(uid, name, capture, *, org=None, modified=None):
    return {"job_id": uid, "business_name": name, "employer_organisation_number": org,
            "modified_at": modified if valid_time(modified) else capture.retrieved_at,
            "source_url": capture.final_url, "retrieved_at": capture.retrieved_at,
            "content_sha256": capture.content_sha256}


def validate(row):
    fields = {'job_id', 'business_name', 'employer_organisation_number', 'modified_at',
              'source_url', 'retrieved_at', 'content_sha256'}
    if not isinstance(row, dict) or set(row) != fields:
        raise ValueError("Invalid NAV candidate cache row")
    org = row['employer_organisation_number']
    if (not isinstance(row['job_id'], str) or not UUID.fullmatch(row['job_id'])
            or not isinstance(row['business_name'], str) or len(row['business_name']) > 300
            or (org is not None and (not isinstance(org, str) or not re.fullmatch(r'\d{9}', org)))
            or not valid_time(row['retrieved_at']) or not valid_time(row['modified_at'])
            or not isinstance(row['content_sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', row['content_sha256'])
            or not isinstance(row['source_url'], str)
            or urlsplit(row['source_url']).scheme != 'https'
            or urlsplit(row['source_url']).netloc != 'pam-stilling-feed.nav.no'
            or not urlsplit(row['source_url']).path.startswith('/api/v1/feed')):
        raise ValueError("Invalid NAV candidate cache provenance")
    return row


def load(path):
    source = Path(path)
    with source.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("NAV candidate cache exceeds byte limit")
    payload = json.loads(raw)
    if (not isinstance(payload, dict) or payload.get('schema') != SCHEMA
            or payload.get('source_feed') != FEED or not valid_time(payload.get('created_at'))
            or not isinstance(payload.get('entries'), list) or len(payload['entries']) > MAX_ENTRIES):
        raise ValueError("Invalid NAV candidate cache schema")
    rows = [validate(row) for row in payload['entries']]
    if len({row['job_id'] for row in rows}) != len(rows):
        raise ValueError("Duplicate NAV cache job IDs")
    declaration = {"schema": SCHEMA, "sha256": hashlib.sha256(raw).hexdigest(),
                   "entries": len(rows), "created_at": payload['created_at'],
                   "source_feed": FEED, "role": "candidate_hints_only",
                   "live_verification_required": True,
                   "oldest_source_retrieval": min((r['retrieved_at'] for r in rows), default=None),
                   "newest_source_retrieval": max((r['retrieved_at'] for r in rows), default=None)}
    return {row['job_id']: row for row in rows}, declaration


def save(path, rows):
    ordered = sorted((validate(row) for row in rows.values()),
                     key=lambda r: (datetime.fromisoformat(r['modified_at'].replace('Z', '+00:00')).timestamp(), r['job_id']), reverse=True)
    truncated = len(ordered) > MAX_ENTRIES
    payload = {"schema": SCHEMA, "source_feed": FEED, "created_at": utc_now(),
               "role": "candidate_hints_only", "entries": ordered[:MAX_ENTRIES]}
    raw = (json.dumps(payload, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    if len(raw) > MAX_BYTES:
        raise ValueError("NAV candidate cache exceeds byte limit")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        handle.write(raw)
    return {"schema": SCHEMA, "sha256": hashlib.sha256(raw).hexdigest(),
            "entries": len(payload['entries']), "truncated": truncated,
            "role": "candidate_hints_only", "live_verification_required": True}
