"""Dated events from individual company pages, with auditable field locators."""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

STRATEGY = "company_dated_events_v4"

MONTHS = {name: index for index, name in enumerate(
    ("januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"), 1)}


def publication_date(value):
    """Normalize an explicit publication field; never mine dates from prose."""
    if iso_date(value):
        return value
    if not isinstance(value, str):
        return None
    value = re.sub(r"^(?:publisert|published|publication date|date posted|posted|utlyst|dato)\s*:?\s*", "", value.strip(), flags=re.I)
    if iso_date(value):
        return value
    match = re.fullmatch(r"(\d{1,2})\.\s*(\w+)\s+(\d{4})", value.casefold())
    numeric = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value)
    if not match and not numeric:
        return None
    day, month, year = (match or numeric).groups()
    month = MONTHS.get(month, 0) if match else int(month)
    try:
        return datetime(int(year), month, int(day)).date().isoformat()
    except ValueError:
        return None


def iso_date(value):
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|T)", value):
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError:
        return None


def page_url(value, base):
    if not isinstance(value, str):
        return None
    parts = urlsplit(urljoin(base, value))
    if parts.scheme not in {"https", "http"} or parts.username or parts.password:
        return None
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/") or "/", parts.query, ""))


def selector(node):
    """Absolute CSS position in the retained DOM; IDs need not be unique."""
    parts = []
    while node and node.name != "[document]":
        position = 1 + sum(sibling.name == node.name for sibling in node.previous_siblings if getattr(sibling, "name", None))
        parts.append(f"{node.name}:nth-of-type({position})")
        node = node.parent
    return " > ".join(reversed(parts))


def structured_events(soup: BeautifulSoup, url: str, kind: str):
    result = []

    def walk(value, pointer, script_index):
        if isinstance(value, dict):
            kinds = value.get("@type", [])
            kinds = [kinds] if isinstance(kinds, str) else kinds if isinstance(kinds, list) else []
            kinds = [kind for kind in kinds if isinstance(kind, str)]
            family = "job_posting" if "JobPosting" in kinds else "company_news" if set(kinds) & {"NewsArticle", "Article", "BlogPosting", "PressRelease"} else None
            if family:
                target = value.get("url") or value.get("mainEntityOfPage")
                if isinstance(target, dict):
                    target = target.get("@id")
                # Listing cards belong to their detail pages, never the index.
                headlines = [node.get_text(" ", strip=True) for node in soup.select("h1")]
                headline = value.get("headline") or value.get("name")
                individual = family == "job_posting" or bool(target) or (len(headlines) == 1 and headline == headlines[0])
                if individual and (not target or page_url(target, url) == page_url(url, url)):
                    result.append({"field": family, "item": value,
                                   "claim_span": json.dumps(value, ensure_ascii=False, sort_keys=True),
                                   "source_locator": {"type": "jsonld_pointer", "script_index": script_index, "pointer": pointer}})
            for key, child in value.items():
                walk(child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"), script_index)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, pointer + "/" + str(index), script_index)

    for index, script in enumerate(soup.select('script[type="application/ld+json"]')):
        try:
            walk(json.loads(script.string or script.get_text()), "", index)
        except (ValueError, TypeError):
            continue
    # Multiple unaddressed news cards do not establish an individual article.
    news = [event for event in result if event["field"] == "company_news"]
    if len(news) > 1:
        result = [event for event in result if event["field"] != "company_news"]
    return result


def dom_event(soup: BeautifulSoup, url: str, kind: str):
    if kind not in {"news", "careers"}:
        return None
    canonical = soup.select_one('link[rel="canonical"][href]')
    if canonical and page_url(canonical["href"], url) != page_url(url, url):
        return None
    articles = soup.select("article")
    if len(articles) > 1:
        return None
    scope = articles[0] if articles else soup.select_one("main")
    if scope is None:
        return None
    headings = scope.select("h1")
    if len(headings) != 1 or not headings[0].get_text(" ", strip=True):
        return None
    title = headings[0]
    if kind == "careers" and re.fullmatch(
            r"(?:karriere|careers?|ledige\s+(?:stillinger|jobber)|open\s+(?:positions|roles)|vacancies|"
            r"jobb\s+hos\s+oss|join\s+us|åpen\s+søknad|open\s+application)",
            title.get_text(" ", strip=True), re.I):
        return None
    published_nodes = scope.select('[itemprop="datePublished"], [itemprop="datePosted"], time[datetime]')
    # Prefer explicit publication metadata over arbitrary visible timestamps.
    published = next((node for node in published_nodes if node.get("itemprop") in {"datePublished", "datePosted"}), None)
    if published is None and len(published_nodes) == 1:
        published = published_nodes[0]
    if published is None and kind == "news":
        published = soup.select_one('meta[property="article:published_time"][content]')
    if published is None and kind == "careers":
        labelled = [node for node in scope.select('p,div,span,time')
                    if len(node.get_text(" ", strip=True)) <= 100
                    and re.match(r"^(?:publisert|published|date posted|posted|utlyst)\b", node.get_text(" ", strip=True), re.I)
                    and publication_date(node.get_text(" ", strip=True))]
        if len({publication_date(node.get_text(" ", strip=True)) for node in labelled}) == 1:
            published = min(labelled, key=lambda node: len(node.get_text(" ", strip=True)))
    labelled_publication = False
    if published is None and kind == "news":
        # Some company CMSs expose a labelled publication block rather than
        # time/JSON-LD. Require a detail page with a same-host parent breadcrumb;
        # footer dates, image URLs, and dates in body prose do not qualify.
        here = urlsplit(url)
        parent_breadcrumb = any(
            (target := urlsplit(urljoin(url, str(link["href"]))))
            and target.hostname == here.hostname
            and target.path.rstrip("/") != here.path.rstrip("/")
            and here.path.startswith(target.path.rstrip("/") + "/")
            and re.search(r"/(?:nyheter|news|aktuelt|blog|fagartikler|artikler|articles|press)(?:/|$)", target.path, re.I)
            for link in scope.select('a[href]'))
        if parent_breadcrumb:
            candidates = [node for node in scope.select('p,div,span,time')
                          if len(node.get_text(" ", strip=True)) <= 100
                          and re.match(r"^(?:publisert|published|publication date|dato)\b", node.get_text(" ", strip=True), re.I)
                          and publication_date(node.get_text(" ", strip=True))]
            dates = {publication_date(node.get_text(" ", strip=True)) for node in candidates}
            if len(dates) == 1:
                published = min(candidates, key=lambda node: len(node.get_text(" ", strip=True)))
                labelled_publication = True
    if published is None:
        return None
    attr = "datetime" if published.has_attr("datetime") else "content" if published.has_attr("content") else None
    date = str(published.get(attr)) if attr else published.get_text(" ", strip=True)
    normalized_date = publication_date(date)
    if not normalized_date:
        return None
    fields = {"title": {"selector": selector(title), "value": title.get_text(" ", strip=True)},
              "date": {"selector": selector(published), "value": date}}
    if attr:
        fields["date"]["attribute"] = attr
    item = {"headline" if kind == "news" else "title": fields["title"]["value"],
            "datePublished" if kind == "news" else "datePosted": normalized_date}
    if kind == "careers":
        employer = scope.select_one('[itemprop="hiringOrganization"] [itemprop="legalName"], [itemprop="hiringOrganization"] [itemprop="name"]')
        if employer is None:
            # Plain company-owned advertisements often label the legal employer
            # without schema.org attributes. Do not infer it from page ownership,
            # a logo, application recipient, or the site's footer.
            labelled_employers = [node for node in scope.select('p,div,span,dd')
                                 if len(node.get_text(" ", strip=True)) <= 160
                                 and re.match(r"^(?:arbeidsgiver|employer)\s*:\s*\S", node.get_text(" ", strip=True), re.I)]
            names = {re.sub(r"^(?:arbeidsgiver|employer)\s*:\s*", "", node.get_text(" ", strip=True), flags=re.I)
                     for node in labelled_employers}
            if len(names) != 1:
                return None
            employer = min(labelled_employers, key=lambda node: len(node.get_text(" ", strip=True)))
        employer_attr = "content" if employer.has_attr("content") else None
        name = str(employer.get(employer_attr)) if employer_attr else employer.get_text(" ", strip=True)
        fields["employer"] = {"selector": selector(employer), "value": name}
        if employer_attr:
            fields["employer"]["attribute"] = employer_attr
        item["hiringOrganization"] = {"legalName": re.sub(r"^(?:arbeidsgiver|employer)\s*:\s*", "", name, flags=re.I)}
        expiry = scope.select_one('[itemprop="validThrough"]')
        if expiry is not None:
            expiry_attr = "datetime" if expiry.has_attr("datetime") else "content" if expiry.has_attr("content") else None
            value = str(expiry.get(expiry_attr)) if expiry_attr else expiry.get_text(" ", strip=True)
            if not iso_date(value):
                return None
            item["validThrough"] = value
            fields["expiry"] = {"selector": selector(expiry), "value": value}
            if expiry_attr:
                fields["expiry"]["attribute"] = expiry_attr
        else:
            deadlines = [node for node in scope.select('p,div,span')
                         if len(node.get_text(" ", strip=True)) <= 100
                         and re.match(r"^(?:søknadsfrist|application deadline)\s*:", node.get_text(" ", strip=True), re.I)]
            if deadlines:
                dates = {publication_date(re.sub(r"^[^:]+:\s*", "", node.get_text(" ", strip=True))) for node in deadlines}
                if None in dates or len(dates) != 1:
                    return None
                expiry = min(deadlines, key=lambda node: len(node.get_text(" ", strip=True)))
                item["validThrough"] = dates.pop()
                fields["expiry"] = {"selector": selector(expiry), "value": expiry.get_text(" ", strip=True)}
    elif not articles and not labelled_publication and soup.select_one('meta[property="og:type"][content="article"]') is None:
        return None
    return {"field": "company_news" if kind == "news" else "job_posting", "item": item,
            "source_locator": {"type": "dom_fields", "fields": fields},
            "claim_span": json.dumps({key: spec["value"] for key, spec in fields.items()}, ensure_ascii=False, sort_keys=True)}


def dated_events(soup, url, kind):
    events = structured_events(soup, url, kind)
    dom = dom_event(soup, url, kind)
    if dom and not any(event["field"] == dom["field"] for event in events):
        events.append(dom)
    return events
