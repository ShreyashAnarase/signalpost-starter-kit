"""Bounded official NAV feed scan shared by one evaluator-supplied batch.

Header names select candidates only. Every publication requires a fresh detail
response with the exact legal employer number and active, unexpired status.
Production never obtains a public experimental token automatically.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import urljoin, urlsplit

from .acquisition import AcquisitionError
from .evidence import evidence, utc_now
from .identity import _tokens
from . import nav_cache

BASE = "https://pam-stilling-feed.nav.no"
FEED = BASE + "/api/v1/feed"
STRATEGY = "nav_feed_exact_employer_v1"
UUID = re.compile(r"^[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}$")


def candidate_employers(name, names):
    """Names are hints only; workplace suffixes must not hide legal employers."""
    tokens = frozenset(_tokens(name))
    matched = set(names.get(tokens, ()))
    for legal_tokens, organisations in names.items():
        # A whole distinctive legal name followed by e.g. 'avdeling Oslo' is
        # useful discovery. Actual employer.orgnr still controls publication.
        if (legal_tokens and legal_tokens <= tokens
                and (len(legal_tokens) > 1 or len(next(iter(legal_tokens))) >= 5)):
            matched.update(organisations)
    return matched


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError:
        return None


def feed_url(value, *, detail=False):
    if not isinstance(value, str) or not value:
        raise ValueError("Missing NAV URL")
    url = urljoin(BASE + "/", value)
    parts = urlsplit(url)
    prefix = "/api/v1/feedentry/" if detail else "/api/v1/feed"
    if (parts.scheme != "https" or parts.netloc != "pam-stilling-feed.nav.no"
            or parts.username or parts.password or parts.fragment or not parts.path.startswith(prefix)):
        raise ValueError("NAV pagination/detail URL escapes its authenticated origin")
    return url


def ad_content(payload):
    """Current NAV feed entries use ad_content; support the legacy JSON shape.

    Conflicting envelopes cannot choose an employer by field preference.
    The original response remains the evidence, without rewriting either shape.
    """
    if not isinstance(payload, dict):
        return None
    fields = [payload[key] for key in ('ad_content', 'json') if key in payload]
    if len(fields) != 1 or not isinstance(fields[0], dict):
        return None
    return fields[0]


def job_fact(payload, capture, expected_uuid, organisations):
    if not isinstance(payload, dict) or payload.get("status") != "ACTIVE" or payload.get("uuid") != expected_uuid:
        return None
    data = ad_content(payload)
    if not isinstance(data, dict) or data.get("uuid") not in {None, expected_uuid}:
        return None
    employer = data.get("employer")
    org = employer.get("orgnr") if isinstance(employer, dict) else None
    if not isinstance(org, str) or org not in organisations:
        return None
    published, expiry, observed = timestamp(data.get("published")), timestamp(data.get("expires")), timestamp(capture.retrieved_at)
    title = data.get("title")
    if (not all([published, expiry, observed]) or published > observed or expiry < observed
            or not isinstance(title, str) or not title.strip() or len(title) > 500):
        return None
    value = {"title": title.strip(), "url": "https://arbeidsplassen.nav.no/stillinger/stilling/" + expected_uuid,
             "date_posted": data["published"], "valid_through": data["expires"],
             "application_url": data.get("applicationUrl") or None,
             "nav_job_id": expected_uuid, "employer_organisation_number": org,
             "location": data.get("workLocations"), "employment_type": data.get("engagementtype")}
    return org, {"field": "job_posting", "value": value, "source_class": "official_job_feed",
                 "source_url": capture.final_url, "retrieved_at": capture.retrieved_at,
                 "content_sha256": capture.content_sha256, "snapshot_path": capture.snapshot_path,
                 "claim_span": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                 "source_locator": {"type": "json_pointer", "pointer": ""},
                 "effective_at": data["published"], "extraction_method": STRATEGY}


def collect_jobs(profiles, session, *, token=None, max_pages=20, max_details=100,
                 lookback_days=7, since=None, prior_job_ids=(), cache_input=None,
                 cache_output=None, expected_cache_sha256=None):
    """Return records for every input, including blocked/incomplete scans.

    An optional declared index contains only candidates. The caller bounds session time/requests and
    accounts its metrics once per batch. Name filtering may miss public brands;
    a partial scan or a name-filter miss is never proof of no jobs.
    """
    if min(max_pages, max_details, lookback_days) <= 0:
        raise ValueError("NAV limits must be positive")
    organisations = {p["organisation_number"] for p in profiles}
    names = defaultdict(set)
    for profile in profiles:
        key = frozenset(_tokens(profile.get("name")))
        if key:
            names[key].add(profile["organisation_number"])
    report = {"strategy": STRATEGY, "pages": 0, "entries": 0, "candidate_details": 0,
              "scan_complete": False, "lookback_days": lookback_days,
              "name_filter_is_candidate_only": True, "cross_run_cache": False,
              "max_pages": max_pages, "max_details": max_details, "errors": []}
    report.update(scan_scope="updates_since_timestamp", full_active_window_covered=False,
                  prior_jobs_rechecked=0, cached_jobs_rechecked=0)
    cached = {}
    workplaces = {}
    report.update(subunit_lookups=0, subunit_matched_jobs=0)
    cache_enabled = bool(cache_input or cache_output)
    def remember(uid, row):
        if not cache_enabled:
            return
        cached.pop(uid, None)
        cached[uid] = row
        if len(cached) > nav_cache.MAX_ENTRIES:
            cached.pop(next(iter(cached)))
            report['cache_evictions'] = report.get('cache_evictions', 0) + 1
    if cache_input:
        try:
            cached, declaration = nav_cache.load(cache_input)
            if expected_cache_sha256 and declaration["sha256"] != expected_cache_sha256:
                raise ValueError("Declared NAV cache changed before acquisition")
            report["cache_input"] = {**declaration, "status": "accepted"}
            report["cross_run_cache"] = True
        except (OSError, ValueError, TypeError):
            cached = {}
            report["cache_input"] = {"status": "rejected", "role": "candidate_hints_only"}
            report["errors"].append("Declared NAV cache unavailable or invalid; live discovery continues")
    token = os.environ.get("NAV_API_TOKEN", "").strip() if token is None else token.strip()
    jobs, seen_pages, seen_jobs = {}, set(), set()
    def workplace_parent(org):
        if org in workplaces:
            return workplaces[org]
        workplaces[org] = None
        report['subunit_lookups'] += 1
        try:
            # A registered workplace is not a corporate subsidiary or group
            # parent. Verify the direct official relationship, never a name.
            capture = session.get('https://data.brreg.no/enhetsregisteret/api/underenheter/' + org,
                                  allow_redirects=False, attempts=1, max_bytes=200_000)
            if capture.status == 404:
                return None
            if capture.status != 200:
                raise ValueError('Workplace registry unavailable')
            body = json.loads(capture.body)
            parent = body.get('overordnetEnhet') if isinstance(body, dict) else None
            if (not isinstance(body, dict) or body.get('organisasjonsnummer') != org
                    or (body.get('organisasjonsform') or {}).get('kode') != 'BEDR'
                    or body.get('slettedato') or not isinstance(parent, str)
                    or not re.fullmatch(r'\d{9}', parent) or parent == org):
                return None
            proof = {'source_url': capture.final_url, 'source_class': 'official_registry',
                     'retrieved_at': capture.retrieved_at, 'content_sha256': capture.content_sha256,
                     'snapshot_path': capture.snapshot_path,
                     'source_locator': {'type': 'json_pointer', 'pointer': ''},
                     'claim_span': json.dumps(body, ensure_ascii=False, separators=(',', ':')),
                     'extraction_method': 'brreg_registered_workplace_parent_v1'}
            workplaces[org] = parent, proof
            return workplaces[org]
        except (AcquisitionError, ValueError, TypeError, AttributeError):
            report['errors'].append('A registered workplace relationship could not be verified')
            return None
    failure_state = "source_error"
    if not token:
        report["errors"].append("Evaluator-supplied NAV_API_TOKEN is missing")
    else:
        headers = {"Authorization": token if token.lower().startswith("bearer ") else "Bearer " + token,
                   "Accept": "application/json"}
        start = since or datetime.now(timezone.utc) - timedelta(days=lookback_days)
        report["since"] = start.isoformat()
        url, details_exhausted = FEED, False
        def fetch_detail(uid):
            nonlocal details_exhausted
            if report["candidate_details"] >= max_details:
                details_exhausted = True
                return None
            seen_jobs.add(uid)
            report["candidate_details"] += 1
            detail = session.get(BASE + "/api/v1/feedentry/" + uid, request_headers=headers,
                                 allow_redirects=False, attempts=1, max_bytes=2_000_000)
            if detail.status != 200:
                report["errors"].append("A candidate detail could not be checked")
                return None
            payload = json.loads(detail.body)
            data = ad_content(payload)
            employer = data.get("employer") if isinstance(data, dict) else None
            actual_org = employer.get("orgnr") if isinstance(employer, dict) else None
            cache_fact = job_fact(payload, detail, uid, {actual_org}) if isinstance(actual_org, str) and re.fullmatch(r"\d{9}", actual_org) else None
            if cache_fact:
                name = employer.get("name")
                remember(uid, nav_cache.entry(uid, name if isinstance(name, str) and len(name) <= 300 else "",
                    detail, org=actual_org, modified=data.get("updated")))
            else:
                cached.pop(uid, None)
            fact = job_fact(payload, detail, uid, organisations)
            if fact is None and cache_fact:
                resolved = workplace_parent(actual_org)
                if resolved and resolved[0] in organisations:
                    parent, proof = resolved
                    _, derived = cache_fact
                    derived['value'].update(employer_organisation_number=parent,
                        registered_employer_organisation_number=actual_org,
                        employer_relationship='registered_workplace_of')
                    derived['relationship'] = 'registered_workplace_of'
                    derived['supporting_evidence'] = [proof]
                    fact = parent, derived
            if fact and fact[1]["value"]["application_url"]:
                try:
                    session._validate_url(fact[1]["value"]["application_url"])
                except (AcquisitionError, ValueError):
                    report["errors"].append("An application URL failed the public URL policy")
                    return None
            if fact and fact[1].get('relationship') == 'registered_workplace_of':
                report['subunit_matched_jobs'] += 1
            return fact
        try:
            # Previously published IDs are hints only and are re-fetched before
            # scanning new updates. An unchanged active job must not disappear
            # merely because its publication moved outside the discovery window.
            for uid in sorted(set(prior_job_ids)):
                if not isinstance(uid, str) or not UUID.fullmatch(uid):
                    continue
                before = report["candidate_details"]
                fact = fetch_detail(uid)
                report["prior_jobs_rechecked"] += report["candidate_details"] - before
                if fact:
                    jobs[uid] = fact
            matching_cache = [row for row in cached.values()
                              if row["employer_organisation_number"] in organisations
                              or candidate_employers(row["business_name"], names)]
            report["cache_matching_candidates"] = len(matching_cache)
            for row in sorted(matching_cache, key=lambda r: (r["modified_at"], r["job_id"]), reverse=True):
                uid = row["job_id"]
                if uid in seen_jobs:
                    continue
                before = report["candidate_details"]
                fact = fetch_detail(uid)
                report["cached_jobs_rechecked"] += report["candidate_details"] - before
                if fact:
                    jobs[uid] = fact
            for _ in range(max_pages):
                if url in seen_pages:
                    raise ValueError("Repeated NAV page")
                seen_pages.add(url)
                capture = session.get(url, request_headers={**headers, "If-Modified-Since": format_datetime(start)},
                                      allow_redirects=False, attempts=1, max_bytes=2_000_000)
                if capture.status != 200:
                    failure_state = "blocked" if capture.status in {401, 403, 429} else "source_error"
                    raise ValueError("NAV feed access failed")
                page = json.loads(capture.body)
                items = page.get("items") if isinstance(page, dict) else None
                if not isinstance(items, list) or len(items) > 2000:
                    raise ValueError("Invalid NAV page")
                report["pages"] += 1
                report["entries"] += len(items)
                for row in items:
                    if not isinstance(row, dict) or not isinstance(row.get("_feed_entry"), dict):
                        raise ValueError("Invalid NAV entry")
                    entry = row["_feed_entry"]
                    uid = entry.get("uuid")
                    if not isinstance(uid, str) or not UUID.fullmatch(uid):
                        continue
                    if entry.get("status") == "INACTIVE":
                        # A fresh detail is the latest state. An older inactive
                        # event cannot undo a subsequently reactivated vacancy.
                        modified = timestamp(entry.get("sistEndret") or row.get("date_modified"))
                        if uid in jobs and modified and modified <= timestamp(jobs[uid][1]["retrieved_at"]):
                            continue
                        jobs.pop(uid, None)
                        cached.pop(uid, None)
                        seen_jobs.discard(uid)
                        continue
                    if entry.get("status") != "ACTIVE":
                        continue
                    # Index all permitted feed candidates, not just this batch's
                    # companies. Cache rows never contain ad bodies or claims.
                    name = entry.get("businessName")
                    if isinstance(name, str) and len(name) <= 300 and uid not in seen_jobs:
                        prior_org = (cached.get(uid) or {}).get("employer_organisation_number")
                        remember(uid, nav_cache.entry(uid, name, capture, org=prior_org,
                                                     modified=entry.get("sistEndret") or row.get("date_modified")))
                    if uid in seen_jobs:
                        continue
                    candidates = candidate_employers(entry.get("businessName"), names)
                    if not candidates:
                        continue
                    detail_url = feed_url(row.get("url"), detail=True)
                    if urlsplit(detail_url).path.rstrip("/").rsplit("/", 1)[-1] != uid or urlsplit(detail_url).query:
                        raise ValueError("NAV detail URL does not match its job UUID")
                    fact = fetch_detail(uid)
                    if fact:
                        jobs[uid] = fact
                next_page = page.get("next_url")
                if not next_page:
                    report["scan_complete"] = not details_exhausted and not report["errors"]
                    break
                url = feed_url(next_page)
        except (AcquisitionError, ValueError, TypeError):
            # Never retain authenticated headers, exception text, or provider
            # bodies in errors. Detail snapshots remain immutable evidence.
            report["errors"].append("NAV scan did not complete within access/schema/resource limits")
    by_org = defaultdict(list)
    report["full_active_window_covered"] = report["scan_complete"] and lookback_days >= 184 and since is None
    for org, fact in jobs.values():
        by_org[org].append(fact)
    records = {}
    for org in organisations:
        facts = sorted(by_org[org], key=lambda f: f["value"]["nav_job_id"])
        status = "available" if facts else "not_found" if report["scan_complete"] else failure_state
        note = "Only freshly confirmed active jobs are displayed; bounded name-filtered scan is not proof of absence"
        records[org] = evidence("nav_jobs", status, "official_job_feed", FEED,
                                value={"facts": facts} if facts else None, note=note)
        records[org]["scan_complete"] = report["scan_complete"]
    report["confirmed_jobs"] = len(jobs)
    report["companies"] = sum(bool(facts) for facts in by_org.values())
    report["metrics"] = session.metrics()
    if cache_output:
        try:
            report["cache_output"] = {**nav_cache.save(cache_output, cached), "status": "saved"}
        except (OSError, ValueError, TypeError):
            report["cache_output"] = {"status": "failed", "role": "candidate_hints_only"}
    return records, report
