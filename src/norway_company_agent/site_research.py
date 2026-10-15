"""Free website discovery and evidence-bearing company-site research."""
from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any

from bs4 import BeautifulSoup

from .acquisition import AcquisitionError, ResearchSession
from .crawl_events import extract_page_event
from .evidence import evidence
from .identity import _tokens
from .html_text import decode_html
from .website import _registered_domain, normalize_homepage, normalize_social_url
from .wikidata_discovery import discover_candidates
from .search_discovery import SearchBudget, discover_candidates as discover_search_candidates
from .tavily_discovery import discover_candidates as discover_tavily_candidates
from .site_events import STRATEGY as EVENT_STRATEGY, dated_events, iso_date, selector as dom_selector

PERSONAL_EMAIL_HOSTS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "hotmail.no", "live.com", "live.no",
    "msn.com", "yahoo.com", "yahoo.no", "icloud.com", "me.com", "aol.com", "online.no", "start.no",
    "frisurf.no", "broadpark.no", "home.no", "getmail.no", "proton.me", "protonmail.com", "mail.com",
}
RESTRICTED_HOSTS = {"linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com", "youtube.com", "glassdoor.com", "indeed.com", "google.com"}
IDENTITY_SELECTOR = 'footer,address,[role="contentinfo"],[id*="footer"],[class*="footer"]'
PAGE_KINDS = {
    "contact": r"kontakt|contact",
    "legal": r"impressum|legal|privacy|personvern|cookie|vilkår|terms|betingelser",
    "about": r"om[-_/ ]oss|about|om[-_/ ]selskap|hvem[-_/ ]er|ledelse|management",
    "careers": r"karriere|career|ledige[-_/ ]stilling|ledig[-_/ ]jobb|vacanc|\b(?:jobs?|jobb(?:er)?|stilling(?:er|sannonser)?)\b|recruit",
    "news": r"nyheter|news|aktuelt|press|media|blog|artikler",
    "locations": r"lokasjon|location|avdeling|kontorer|butikker|offices",
}
ORG_PATTERN = re.compile(r"(?<!\d)(\d{3}[ .-]?\d{3}[ .-]?\d{3})(?!\d)")
ORG_LABEL = re.compile(r"(?:org(?:anisasjons)?[ ._-]*(?:nummer|nr)?|organi[sz]ation(?:\s+number)?|foretaksregister(?:et)?|registration\s+number|vat(?:\s+number)?|mva)[\s:.#-]*(?:NO\s*)?(\d{3}[ .-]?\d{3}[ .-]?\d{3})(?!\d)", re.I)
VAT_NUMBER = re.compile(r"\bNO\s*(\d{3}[ .-]?\d{3}[ .-]?\d{3})\s*MVA\b", re.I)


def legal_org_numbers(text: str) -> set[str]:
    return {re.sub(r"\D", "", number) for number in [*ORG_LABEL.findall(text), *VAT_NUMBER.findall(text)]}


def website_candidates(profile: dict[str, Any]) -> list[dict[str, str]]:
    records = profile.get("evidence", {})
    live = (records.get("registry_live", {}).get("value") or {})
    raw = records.get("registry", {}).get("value") or {}
    values = [(live.get("website"), "registry_live"), (profile.get("website"), "registry")]
    email = live.get("email") or raw.get("epostadresse")
    if isinstance(email, str) and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
        host = email.strip().rsplit("@", 1)[1].lower().strip(".")
        if _registered_domain("https://" + host) not in PERSONAL_EMAIL_HOSTS:
            values.append(("https://" + host, "registry_email_domain"))
    result = []
    seen = set()
    for value, source in values:
        normalized = normalize_homepage(value)
        if normalized and normalized.rstrip("/") not in seen:
            seen.add(normalized.rstrip("/"))
            result.append({"url": normalized, "discovery_method": source})
    return result[:3]


def page_kind(url: str, label: str = "") -> str | None:
    text = urllib.parse.unquote(urllib.parse.urlsplit(url).path) + " " + label
    return next((kind for kind, pattern in PAGE_KINDS.items() if re.search(pattern, text, re.I)), None)


def page_links(url: str, soup: BeautifulSoup, *, family: str | None = None) -> list[tuple[str, str]]:
    host = urllib.parse.urlsplit(url).hostname
    result = {}
    for link in soup.select("a[href],area[href],frame[src],iframe[src]"):
        target = urllib.parse.urljoin(url, str(link.get("href") or link.get("src") or ""))
        parsed = urllib.parse.urlsplit(target)
        if parsed.scheme not in {"https", "http"} or parsed.hostname != host:
            continue
        if parsed.query or re.search(r"\.(?:pdf|jpg|png|zip|svg|mp4)$", parsed.path, re.I):
            continue
        path = urllib.parse.quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
        clean = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))
        kind = page_kind(clean, link.get_text(" ", strip=True) + " " + str(link.get("alt") or ""))
        if not kind and family in {"news", "careers"} and link.name == "a":
            # Index cards often use opaque slugs and a headline as the link label.
            # Carry the verified source family only for content-card links, never
            # navigation/footer links or arbitrary same-host URLs.
            content = link.find_parent("article") or link.find_parent(["h2", "h3"])
            if content and not link.find_parent(["nav", "footer", "header"]):
                kind = family
        if not kind and link.name in {"frame", "iframe"}:
            kind = "navigation"
        if kind:
            result[clean] = kind
    priority = {kind: index for index, kind in enumerate([*PAGE_KINDS, "navigation"])}
    # Preserve publisher order for detail links from an activity index. Sorting
    # article slugs by length favored old short titles over the featured update.
    return sorted(result.items(), key=lambda item: (priority[item[1]], 0, "") if item[1] == family
                  else (priority[item[1]], len(urllib.parse.urlsplit(item[0]).path), item[0]))


def _structured(soup: BeautifulSoup) -> list[dict[str, Any]]:
    result = []

    def walk(value):
        if isinstance(value, dict):
            if "@type" in value:
                result.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            walk(json.loads(script.string or script.get_text()))
        except (ValueError, TypeError):
            continue
    return result


def next_crawl_page(queue: list[tuple[str, str]], *, verified: bool,
                    visits: Counter, detail_urls: set[str] | None = None) -> tuple[str, str]:
    """Verify identity first, then alternate news/jobs and their detail pages."""
    identity_order = {kind: index for index, kind in enumerate(PAGE_KINDS)}

    def priority(item):
        url, kind = item
        if verified and kind in {"careers", "news"}:
            pagination = bool(re.search(r"/page/\d+(?:/|$)", urllib.parse.urlsplit(url).path))
            return (0 if not pagination else 2, visits[kind], 0 if detail_urls and url in detail_urls else 1, identity_order[kind])
        return (1, identity_order.get(kind, 99), 0, 0)

    index = min(range(len(queue)), key=lambda index: priority(queue[index]))
    return queue.pop(index)


def read_page(session: ResearchSession, url: str, kind: str) -> tuple[dict[str, Any], BeautifulSoup]:
    capture = session.get(url, robots=True)
    if capture.status in {401, 403, 429}:
        raise AcquisitionError(f"HTTP {capture.status}", "blocked")
    if capture.status != 200:
        raise AcquisitionError(f"HTTP {capture.status}", "not_available" if capture.status in {404, 410} else "failed")
    if "html" not in capture.content_type.lower():
        raise AcquisitionError("Source is not an HTML page")
    try:
        page = extract_page_event(organisation_number="", requested_url=url, final_url=capture.final_url,
                                  status_code=200, content_type=capture.content_type, body=capture.body,
                                  page_kind="homepage" if kind == "homepage" else kind, retrieved_at=capture.retrieved_at)
    except ValueError as exc:
        raise AcquisitionError("HTML content could not be decoded within its byte limit") from exc
    page.update(capture.metadata())
    page["url"] = capture.final_url
    page["kind"] = kind
    soup = BeautifulSoup(decode_html(capture.body, capture.content_type)[0], "lxml")
    page["structured_items"] = _structured(soup)
    page["dated_events"] = dated_events(soup, capture.final_url, kind)
    page["full_text"] = soup.get_text(" ", strip=True)[:50000]
    # This text includes legal footers; article extraction often removes them.
    page["identity_text_excerpt"] = " ".join(node.get_text(" ", strip=True) for node in soup.select(IDENTITY_SELECTOR))[:12000]
    page["headings"] = [node.get_text(" ", strip=True) for node in soup.select('h1,h2,[itemprop="legalName"]')]
    page["identity_heading_nodes"] = [{"text": node.get_text(" ", strip=True), "selector": dom_selector(node)}
                                      for node in soup.select('title,h1,h2,[itemprop="legalName"]')
                                      if node.get_text(" ", strip=True)]
    page["identity_contact_nodes"] = [{"text": node.get_text(" ", strip=True), "selector": dom_selector(node)}
                                      for node in soup.select('p,address,a,span,div')
                                      if 0 < len(node.get_text(" ", strip=True)) <= 1000]
    page["contact_blocks"] = [{"text": node.get_text(" ", strip=True),
                               "names": [name.get_text(" ", strip=True) for name in node.select("strong,b")]} 
                              for node in soup.select("p,address") if len(node.get_text(" ", strip=True)) <= 1000] if kind == "contact" else []
    # A property can have the registered address of its manager. A legal
    # company named in a footer contact/address block is ownership evidence,
    # not just a contact match for every property listed on that site.
    page["footer_contact_owners"] = []
    for node in soup.select('footer address,[role="contentinfo"] address,[id*="footer"] address,[class*="footer"] address'):
        text = node.get_text(" ", strip=True)
        match = re.match(r"^([\w .,&'()/-]{2,100}?\s+(?:ASA|AS|ANS|DA|SA|NUF|LTD|LLC))\b", text, re.I)
        if match:
            page["footer_contact_owners"].append(match.group(1).strip())
    page["legal_identity_blocks"] = [
        {"text": node.get_text(" ", strip=True), "selector": dom_selector(node)}
        for node in soup.select('main p,main address,article p,article address')
        if kind in {"contact", "legal"} and 0 < len(node.get_text(" ", strip=True)) <= 700
        and legal_org_numbers(node.get_text(" ", strip=True))]
    if kind in {"contact", "legal"}:
        # Some legal notices put the number, legal name and registered address
        # in adjacent paragraphs. Keep that narrow local block, with an exact
        # multi-node locator; never join arbitrary page-wide mentions.
        for node in soup.select('main p,main address,article p,article address'):
            if not legal_org_numbers(node.get_text(" ", strip=True)):
                continue
            nodes = [node]
            for sibling in node.find_next_siblings(limit=5):
                if sibling.name not in {"p", "address"}:
                    break
                nodes.append(sibling)
            text = ' '.join(n.get_text(' ', strip=True) for n in nodes)
            if len(nodes) > 1 and 0 < len(text) <= 700:
                page["legal_identity_blocks"].append({"text": text,
                    "selector": ','.join(dom_selector(n) for n in nodes), "requires_registered_address": True})
    return page, soup


def assess_site(profile: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    org = profile["organisation_number"]
    core = set(_tokens(profile.get("name")))
    raw = profile.get("evidence", {}).get("registry", {}).get("value") or {}
    live = profile.get("evidence", {}).get("registry_live", {}).get("value") or {}
    address = live.get("business_address") or {}
    streets = address.get("adresse") or [raw.get("forretningsadresse.adresse", "")]
    postal = str(address.get("postnummer") or raw.get("forretningsadresse.postnummer") or "")
    phone = re.sub(r"\D", "", str(live.get("phone") or raw.get("telefon") or raw.get("mobil") or ""))[-8:]
    proofs = []
    footer_ids = [legal_org_numbers(str(page.get("identity_text_excerpt") or "")) for page in pages]
    if any(ids and org not in ids for ids in footer_ids):
        return {"publishable": False, "status": "ambiguous", "method": "legal_identity_and_contact_v3", "proofs": [], "reasons": ["The website's legal footer identifies another organisation"]}
    target_name = set(_tokens(profile.get("name")))
    if any(set(_tokens(name)) != target_name for page in pages for name in page.get("footer_contact_owners", [])):
        return {"publishable": False, "status": "ambiguous", "method": "legal_identity_and_contact_v3", "proofs": [],
                "reasons": ["The website's legal contact block names another company"]}
    for page in pages:
        identity_text = str(page.get("identity_text_excerpt") or "")
        text = str(page.get("full_text") or page.get("main_text_excerpt") or "")
        ids = legal_org_numbers(identity_text)
        if ids == {org}:
            proofs.append({"type": "organisation_number_in_legal_footer", "value": org, "source_url": page["url"]})
        full_legal_name = " ".join(str(profile.get("name") or "").casefold().split())
        for block in page.get("legal_identity_blocks", []):
            # A compact legal/contact paragraph must name the complete legal
            # company and its sole labelled ID. Directory mentions and broad
            # page text cannot become ownership proof.
            block_text = ' '.join(_tokens(block["text"]))
            block_address = bool(postal and re.search(rf"(?<!\d){re.escape(postal)}(?!\d)", block["text"])
                                 and any(street and ' '.join(_tokens(street)) in block_text for street in streets))
            if (full_legal_name and legal_org_numbers(block["text"]) == {org}
                    and (not block.get("requires_registered_address") or block_address)
                    and re.search(r"(?<!\w)" + re.escape(full_legal_name) + r"(?!\w)",
                                  " ".join(block["text"].casefold().split()))):
                proofs.append({"type": "legal_name_and_number_in_contact_block", "value": org,
                               "source_url": page["url"], "claim_span": block["text"],
                               "source_locator": {"type": "css_text", "selector": block["selector"]}})
        for item in page.get("structured_items", []):
            name = item.get("legalName") or item.get("name") or ""
            number = re.sub(r"\D", "", str(item.get("taxID") or item.get("vatID") or ""))
            if number == org and core and core.issubset(set(_tokens(name))):
                proofs.append({"type": "structured_legal_identity", "value": org, "source_url": page["url"]})
        title_names = [page.get("title"), *page.get("headings", []), *[item.get("legalName") or item.get("name") for item in page.get("structured_items", []) if isinstance(item.get("@type"), str) and item.get("@type") in {"Organization", "Corporation", "LocalBusiness"}]]
        name_matches = bool(core and any(core.issubset(set(_tokens(name))) for name in title_names if isinstance(name, str)))
        normalized = " ".join(_tokens(text))
        address_matches = bool(postal and re.search(rf"(?<!\d){re.escape(postal)}(?!\d)", text) and any(
            street and " ".join(_tokens(street)) in normalized for street in streets))
        phone_matches = bool(len(phone) == 8 and re.search(r"(?<!\d)" + r"[\s().+-]*".join(phone) + r"(?!\d)", text))
        page_ids = legal_org_numbers(text)
        for block in page.get("contact_blocks", []):
            exact_name = " ".join(str(profile.get("name") or "").casefold().split())
            block_ids = legal_org_numbers(block["text"])
            # Older sites use bold paragraph labels instead of semantic headings.
            # Require the complete legal name and registered phone in that same
            # compact contact block, not mentions scattered across the page.
            if (exact_name and exact_name in {" ".join(name.casefold().split()) for name in block["names"]}
                    and (not block_ids or block_ids == {org}) and len(phone) == 8
                    and re.search(r"(?<!\d)" + r"[\s().+-]*".join(phone) + r"(?!\d)", block["text"])):
                proofs.append({"type": "legal_contact_block_with_registered_phone", "value": profile["name"],
                               "source_url": page["url"], "claim_span": block["text"]})
        full_name = " ".join(str(profile.get("name") or "").casefold().split())
        full_heading = bool(full_name and any(re.search(r"(?<!\w)" + re.escape(full_name) + r"(?!\w)", " ".join(str(name).casefold().split())) for name in title_names if name))
        # A one-word brand plus a phone listed among several clinics does not
        # resolve the whole shared site to an incorporated legal company.
        if name_matches and (len(core) > 1 or full_heading) and (address_matches or phone_matches or page_ids == {org}):
            proof = {"type": "legal_name_with_registered_contact", "value": profile.get("name"), "source_url": page["url"]}
            heading = next((node for node in page.get("identity_heading_nodes", []) if core.issubset(set(_tokens(node["text"])))), None)
            contacts = [node for node in page.get("identity_contact_nodes", []) if
                        (len(phone) == 8 and re.search(r"(?<!\d)" + r"[\s().+-]*".join(phone) + r"(?!\d)", node["text"]))
                        or (postal and re.search(rf"(?<!\d){re.escape(postal)}(?!\d)", node["text"])
                            and any(street and " ".join(_tokens(street)) in " ".join(_tokens(node["text"])) for street in streets))]
            if heading and contacts:
                contact = min(contacts, key=lambda node: len(node["text"]))
                fields = {"name": {"selector": heading["selector"], "value": heading["text"]},
                          "registered_contact": {"selector": contact["selector"], "value": contact["text"]}}
                proof["source_locator"] = {"type": "dom_fields", "fields": fields}
                proof["claim_span"] = json.dumps({key: field["value"] for key, field in fields.items()}, ensure_ascii=False, sort_keys=True)
            elif page.get("identity_heading_nodes"):
                # Fresh HTML must cite the corroborating nodes, not an unrelated
                # web designer/copyright footer. Missing nodes remain unresolved.
                continue
            proofs.append(proof)
    # An organisation mentioned in a directory or a parent portfolio is not proof
    # of ownership. Require a sole footer identity or corroborated company heading.
    return {"publishable": bool(proofs), "status": "exact" if proofs else "ambiguous",
            "method": "legal_identity_and_contact_v3", "proofs": proofs,
            "reasons": [] if proofs else ["No exact legal identity or corroborated registered contact found"]}


def _dated(value: Any) -> str | None:
    return iso_date(value)


def extract_site_facts(profile: dict[str, Any], pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []
    seen = set()

    def add(field: str, value: Any, page: dict, span: str, **extra):
        key = (field, json.dumps(value, sort_keys=True, ensure_ascii=False))
        if value in (None, "", []) or key in seen:
            return
        seen.add(key)
        facts.append({"field": field, "value": value, "source_url": page["url"],
                      "retrieved_at": page["retrieved_at"], "content_sha256": page["content_sha256"],
                      "snapshot_path": page["snapshot_path"], "claim_span": span,
                      "extraction_method": "company_site_structured_and_dom_v1", **extra})
        if page.get("text_encoding"):
            facts[-1].setdefault("source_locator", {"type": "extracted_text", "text": span})["encoding"] = page["text_encoding"]

    homepage = pages[0]
    proofs = assess_site(profile, pages).get("proofs", [])
    proof = proofs[0] if proofs else {}
    identity_page = next((page for page in pages if page["url"] == proof.get("source_url")), homepage)
    identity_span = proof.get("claim_span") or identity_page.get("identity_text_excerpt") or identity_page.get("full_text") or identity_page.get("title", "")
    locator = proof.get("source_locator") or ({"type": "css_text", "selector": IDENTITY_SELECTOR} if not proof.get("claim_span") and identity_page.get("identity_text_excerpt") else {"type": "extracted_text", "text": identity_span})
    add("official_website", homepage["url"], identity_page, identity_span, source_locator=locator)
    if homepage.get("description"):
        add("business_description", homepage["description"], homepage, homepage["description"])
    legal_tokens = set(_tokens(profile.get("name")))
    for page in pages:
        if (page["kind"] in {"careers", "news", "contact", "locations"}
                and page_kind(page["url"], page.get("title") or "") == page["kind"]):
            page_span = page.get("title") or next(iter(page.get("headings", [])), None)
            if page_span:
                add(page["kind"] + "_page", page["url"], page, page_span)
        for link in page.get("social_links", []):
            # This claim records the company's outbound link; it does not assert
            # exclusive ownership of a platform account shared by a group.
            add("company_declared_profile", link, page, link["url"], relationship="linked_by_company", source_locator={"type": "normalized_outbound_link", "url": link["url"]})
        events = page.get("dated_events")
        if events is None:
            # Compatibility for old in-memory fixtures. Retained HTML re-export
            # goes through read_page and always uses the new precise locators.
            events = [{"item": item} for item in page.get("structured_items", [])]
        for event in events:
            item = event["item"]
            kinds = item.get("@type") or []
            kinds = {kinds} if isinstance(kinds, str) else set(kinds)
            observed = _dated(page.get("retrieved_at"))
            extra = {"source_locator": event["source_locator"], "extraction_method": EVENT_STRATEGY} if event.get("source_locator") else {}
            if "JobPosting" in kinds or event.get("field") == "job_posting":
                employer = item.get("hiringOrganization") or {}
                employer = employer if isinstance(employer, dict) else {}
                employer_name = str(employer.get("legalName") or employer.get("name") or "")
                employer_url = employer.get("url") or employer.get("sameAs") or ""
                if isinstance(employer_url, list):
                    employer_url = next((u for u in employer_url if isinstance(u, str)), "")
                exact_name = bool(legal_tokens and _tokens(profile.get("name")) == _tokens(employer_name))
                exact_domain = bool(isinstance(employer_url, str) and employer_url.startswith(("https://", "http://")) and _registered_domain(employer_url) == _registered_domain(homepage["url"]))
                if not exact_name and (employer.get("legalName") or re.search(r"\b(?:AS|ASA|Ltd|LLC)\s*$", employer_name)):
                    continue
                if not (exact_name or exact_domain):
                    continue
                posted = _dated(item.get("datePosted"))
                title = item.get("title")
                if not isinstance(title, str) or not title.strip() or not posted or not observed or posted[:10] > observed[:10]:
                    continue
                expiry = _dated(item.get("validThrough"))
                if item.get("validThrough") and not expiry:
                    continue
                if expiry and expiry[:10] < observed[:10]:
                    continue
                job = {"title": title, "url": page["url"], "date_posted": posted, "valid_through": expiry,
                       "location": item.get("jobLocation"), "employment_type": item.get("employmentType")}
                add("job_posting", job, page, event.get("claim_span") or title, effective_at=posted, **extra)
            elif kinds.intersection({"NewsArticle", "Article", "BlogPosting", "PressRelease"}) or event.get("field") == "company_news":
                published = _dated(item.get("datePublished"))
                headline = item.get("headline") or item.get("name")
                if published and observed and published[:10] <= observed[:10] and isinstance(headline, str) and headline.strip():
                    add("company_news", {"headline": headline, "url": page["url"], "date_published": published}, page, event.get("claim_span") or headline, effective_at=published, **extra)
    return facts


def research_site(profile: dict[str, Any], session: ResearchSession, *, max_pages: int = 10,
                  wikidata_discovery: bool = False, search_budget: SearchBudget | None = None,
                  search_provider: str = "brave",
                  discovery_candidates: list[dict[str, str]] | None = None) -> dict[str, Any]:
    # Explicit provider candidates support a bounded development experiment
    # without falsely relabelling them as registry-supplied websites. Ownership
    # and publication checks are identical to the ordinary production crawl.
    candidates = website_candidates(profile) if discovery_candidates is None else discovery_candidates[:3]
    diagnostic = None
    if wikidata_discovery and not candidates:
        candidates, diagnostic = discover_candidates(profile["organisation_number"], session)
    if search_budget is not None and not candidates:
        if search_provider == "tavily":
            candidates, search_diagnostic = discover_tavily_candidates(profile, session, search_budget)
        elif search_provider == "brave":
            candidates, search_diagnostic = discover_search_candidates(profile, session, search_budget)
        else:
            raise ValueError("Unsupported search provider")
        if diagnostic is not None:
            search_diagnostic["prior_discovery"] = diagnostic
        diagnostic = search_diagnostic
    attempts = []
    if not candidates:
        record = evidence("website", "not_found", "company_owned", "https://data.brreg.no/enhetsregisteret/api/enheter/" + profile["organisation_number"], note="No website candidate in the official website or business-email fields")
        if diagnostic is not None:
            record["candidate_discovery"] = diagnostic
            if diagnostic["status"] in {"blocked", "failed", "ambiguous"}:
                record["status"] = "source_error" if diagnostic["status"] == "failed" else diagnostic["status"]
        return record
    for candidate in candidates:
        pages = []
        errors = []
        try:
            if _registered_domain(candidate["url"]) in RESTRICTED_HOSTS:
                raise AcquisitionError("Platform requires a permitted connector; direct collection disabled", "blocked")
            try:
                homepage, soup = read_page(session, candidate["url"], "homepage")
            except AcquisitionError as exc:
                if not exc.tls_failure or not candidate["url"].startswith("https://"):
                    raise
                # A separate public HTTP request with its own robots policy;
                # never bypass certificate verification or access denials.
                errors.append({"url": candidate["url"], "error": str(exc), "fallback": "http"})
                homepage, soup = read_page(session, "http://" + candidate["url"][8:], "homepage")
            pages.append(homepage)
            owner = assess_site(profile, pages)
            if owner.get("reasons") == ["The website's legal footer identifies another organisation"]:
                attempts.append({**candidate, "identity": owner, "pages": 1, "errors": []})
                continue
            queue = page_links(homepage["url"], soup)
            visited = {homepage["url"].rstrip("/")}
            visits = Counter()
            detail_urls: set[str] = set()
            if not queue and len(pages) < max_pages:
                origin = urllib.parse.urlsplit(homepage["url"])
                sitemap_url = urllib.parse.urlunsplit((origin.scheme, origin.netloc, "/sitemap.xml", "", ""))
                try:
                    sitemap = session.get(sitemap_url, robots=True, max_bytes=1_000_000, attempts=1)
                    if sitemap.status == 200:
                        root = ET.fromstring(sitemap.body)
                        for node in root.iter():
                            target = (node.text or "").strip()
                            if node.tag.rsplit("}", 1)[-1] == "loc" and urllib.parse.urlsplit(target).netloc == origin.netloc:
                                kind = page_kind(target)
                                if kind:
                                    queue.append((target, kind))
                except (AcquisitionError, ET.ParseError) as exc:
                    errors.append({"url": sitemap_url, "error": str(exc)[:180]})
            while queue and len(pages) < max_pages:
                url, kind = next_crawl_page(queue, verified=owner["publishable"], visits=visits, detail_urls=detail_urls)
                if url.rstrip("/") in visited:
                    continue
                visited.add(url.rstrip("/"))
                try:
                    page, page_soup = read_page(session, url, kind)
                    if _registered_domain(page["url"]) != _registered_domain(homepage["url"]):
                        errors.append({"url": url, "error": "Page redirects outside the candidate site"})
                        continue
                    pages.append(page)
                    visits[kind] += 1
                    owner = assess_site(profile, pages)
                    if owner.get("reasons") == ["The website's legal footer identifies another organisation"]:
                        break
                    if kind in {"careers", "news", "navigation", "contact", "legal", "about"}:
                        pending = {target for target, _ in queue}
                        found = [(target, family) for target, family in page_links(page["url"], page_soup, family=kind)
                                 if (kind == "navigation" or family == kind
                                     or kind in {"contact", "legal", "about"} and family in {"contact", "legal"})
                                 and target.rstrip("/") not in visited and target not in pending]
                        if kind in {"careers", "news"}:
                            detail_urls.update(target for target, _ in found if target not in pending)
                        queue.extend(found)
                except AcquisitionError as exc:
                    errors.append({"url": url, "error": str(exc), "availability": exc.availability})
                    if "budget" in str(exc).lower() or "deadline" in str(exc).lower():
                        break
            identity = assess_site(profile, pages)
            attempt = {**candidate, "identity": identity, "pages": len(pages), "errors": errors}
            attempts.append(attempt)
            if not identity["publishable"]:
                continue
            facts = extract_site_facts(profile, pages)
            for page in pages:
                page.pop("full_text", None)
                page.pop("structured_items", None)
                page.pop("dated_events", None)
                page.pop("identity_heading_nodes", None)
                page.pop("identity_contact_nodes", None)
                page.pop("footer_contact_owners", None)
                page.pop("legal_identity_blocks", None)
            value = {**homepage, "pages": pages, "identity_assessment": identity,
                     "facts": facts, "discovery_attempts": attempts, "crawl_errors": errors,
                     "social_links": [], "discovered_social_links": [item["value"] for item in facts if item["field"] == "company_declared_profile"]}
            record = evidence("website", "available", "company_owned", homepage["url"], value=value,
                              content_sha256=homepage["content_sha256"], retrieved_at=homepage["retrieved_at"])
            record["snapshot_path"] = homepage["snapshot_path"]
            if diagnostic is not None:
                record["candidate_discovery"] = diagnostic
            return record
        except AcquisitionError as exc:
            attempts.append({**candidate, "availability": exc.availability, "error": str(exc)})
    if search_budget is not None and diagnostic is None and discovery_candidates is None:
        # Existing registry/email candidates are hints, not a reason to suppress
        # discovery forever when all of them fail. One bounded search shares the
        # original session's time/request budgets and the batch spending cap.
        discover = discover_tavily_candidates if search_provider == "tavily" else discover_search_candidates
        alternatives, diagnostic = discover(profile, session, search_budget)
        attempted = {_registered_domain(row["url"]) for row in attempts}
        alternatives = [row for row in alternatives if _registered_domain(row["url"]) not in attempted]
        if alternatives:
            record = research_site(profile, session, max_pages=max_pages,
                                   discovery_candidates=alternatives)
            record["candidate_discovery"] = diagnostic
            value = record.get("value")
            if isinstance(value, dict):
                value["discovery_attempts"] = attempts + value.get("discovery_attempts", [])
            else:
                record["discovery_attempts"] = attempts + record.get("discovery_attempts", [])
            return record
    status = "ambiguous" if any(item.get("identity") for item in attempts) else "blocked" if attempts and all(item.get("availability") == "blocked" for item in attempts) else "not_found" if attempts and all(item.get("availability") == "not_available" for item in attempts) else "source_error"
    record = evidence("website", status, "company_owned", candidates[0]["url"], note="No candidate passed exact-company verification")
    record["discovery_attempts"] = attempts
    if diagnostic is not None:
        record["candidate_discovery"] = diagnostic
    return record
