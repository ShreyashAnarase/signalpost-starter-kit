"""Generate a standalone public profile sample from audited envelopes."""
from __future__ import annotations

import json
from pathlib import Path

from .audit import audit_envelopes


def public_profiles(envelopes: list[dict]) -> list[dict]:
    """Keep published facts and short attributed spans; omit private snapshots."""
    return [{"org": row["organisation_number"], "identity": row["legal_identity"],
             "updated": row["run"]["completed_at"],
             "claims": [{key: claim.get(key) for key in
                         ("id", "field", "value", "availability", "evidence_ids", "reporting_period", "account_scope", "effective_at", "relationship", "freshness")}
                        for claim in row["claims"]],
             "summary": row["summary"], "changes": [
                 {key: value for key, value in change.items() if key not in {"old_value", "new_value"}}
                 if change.get("source_policy") == "nav_remove_from_display" else change
                 for change in row.get("changes", [])],
             "sources": [{key: source.get(key) for key in
                          ("id", "source_url", "source_class", "retrieved_at", "content_sha256", "reporting_period")}
                         | {"excerpt": source["claim_span"][:300] if source["source_class"] == "company_owned" else ""}
                         for source in row["evidence"]]}
            for row in envelopes]


def build_showcase(envelopes: list[dict], output: Path, *, expected_count: int = 100, snapshot_root=None) -> dict:
    if len(envelopes) != expected_count:
        raise ValueError(f"Expected {expected_count} public profiles, received {len(envelopes)}")
    audit = audit_envelopes(envelopes, [row["organisation_number"] for row in envelopes], snapshot_root=snapshot_root)
    if not audit["passed"]:
        raise ValueError("Public sample requires passing evidence and input-membership audit")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    profiles = public_profiles(envelopes)
    # An HTML parser must never interpret company-provided strings as tags or
    # terminate the data script. All rendering below uses DOM textContent.
    payload = json.dumps(profiles, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    html = TEMPLATE.replace('__PROFILE_DATA__', payload)
    (output / 'index.html').write_text(html, encoding='utf-8')
    report = {"profiles": len(profiles), "audit_passed": True, "route": "/signalpost/",
              "hosting_status": "local artifact; not deployed", "raw_snapshots_exported": False}
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signalpost · Company research</title>
<style>
:root{color-scheme:light;--ink:#182d2a;--muted:#62736f;--line:#d9e3df;--green:#17624d;--wash:#f4f7f4}
*{box-sizing:border-box}body{margin:0;background:var(--wash);color:var(--ink);font:15px/1.55 system-ui,sans-serif}
header{padding:22px 5vw;border-bottom:1px solid var(--line);background:#fff;display:flex;justify-content:space-between;gap:18px;align-items:center}
.brand{font-size:23px;font-weight:750;letter-spacing:-.7px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:1.2px;color:var(--green)}
.muted{color:var(--muted)}.shell{display:grid;grid-template-columns:300px minmax(0,1fr);max-width:1400px;margin:auto;min-height:85vh}
aside{padding:24px 18px;border-right:1px solid var(--line)}input{width:100%;padding:12px;border:1px solid var(--line);border-radius:8px;background:#fff;font:inherit}
#results{margin-top:14px;max-height:72vh;overflow:auto}.company{display:block;width:100%;text-align:left;background:transparent;border:0;border-bottom:1px solid var(--line);padding:14px 10px;cursor:pointer;color:var(--ink);font:inherit}
.company:hover,.company[aria-current=true]{background:#e0ece5;border-radius:6px}.company strong{display:block;font-size:14px}.company small{color:var(--muted)}
main{padding:35px 40px;min-width:0}h1{font-size:30px;line-height:1.2;letter-spacing:-.6px;margin:10px 0}h2{font-size:17px;margin:0 0 14px}h3{font-size:15px;margin:0 0 6px}
.meta{display:flex;flex-wrap:wrap;gap:10px 22px}.tabs{display:flex;gap:5px;margin:26px 0 20px;border-bottom:1px solid var(--line);overflow:auto}
.tabs button{border:0;background:transparent;padding:12px 14px;color:var(--muted);font:inherit;cursor:pointer;white-space:nowrap}.tabs button[aria-selected=true]{color:var(--green);border-bottom:3px solid var(--green);font-weight:650}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px;margin-bottom:14px;overflow-wrap:anywhere}.card p{margin:6px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.value{font-size:24px;font-weight:700;letter-spacing:-.4px}.tag{display:inline-block;background:#edf2ef;color:var(--muted);padding:2px 8px;border-radius:20px;font-size:12px;margin:3px 6px 3px 0}.tag.available{color:var(--green);background:#dff0e6}
.citation{background:none;border:0;color:var(--green);text-decoration:underline;cursor:pointer;padding:0;font:inherit;font-size:12px}.card>.citation{display:block;margin-top:8px}.notice{padding:12px 16px;border-left:3px solid var(--green);background:#e9f0eb;margin-bottom:18px}
a{color:var(--green)}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}code{font-size:11px;overflow-wrap:anywhere}details{margin-top:10px}footer{font-size:12px;color:var(--muted);padding:20px 5vw;border-top:1px solid var(--line)}
@media(max-width:760px){header{align-items:flex-start}.shell{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line);padding:16px}#results{max-height:180px}main{padding:22px 16px}h1{font-size:24px}.tabs button{padding:10px}.meta{font-size:13px}}
</style></head><body><header><div><div class="brand">Signalpost<span style="color:#45826b">.</span></div><div class="muted">Company research, with sources.</div></div><div><div class="eyebrow">Norway · public sample</div><div id="count" class="muted"></div></div></header>
<div class="shell"><aside><label for="search">Find a company</label><input id="search" type="search" placeholder="Name or organisation number"><div id="results" aria-label="Companies"></div></aside><main id="profile" aria-live="polite"></main></div>
<footer>Registry records anchor legal identity. Company-authored articles describe company publications; they do not provide independent sentiment. Unavailable information remains explicit.</footer>
<script type="application/json" id="data">__PROFILE_DATA__</script>
<script>
'use strict';
const profiles=JSON.parse(document.getElementById('data').textContent), root=document.getElementById('profile');
let selected=profiles[0], tab='Overview', focusEvidence=null;
const states={available:'Available',not_available:'Not found in this search',blocked:'Access blocked',not_applicable:'Not applicable',ambiguous:'Identity unresolved',failed:'Could not retrieve'};
const labels={legal_name:'Registered name',employee_count:'Registered employees',official_website:'Verified website',business_description:'Company description',company_news:'Company-authored article',job_posting:'Job posting',company_declared_profile:'Profile linked by company',roles:'Registered roles',locations:'Registered workplaces'};
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function add(parent,...children){children.forEach(c=>parent.append(c));return parent}
function text(value){return value===null||value===undefined?'Not available':typeof value==='object'?JSON.stringify(value):String(value)}
function safeURL(value){try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:null}catch{return null}}
function link(value,label){const href=safeURL(value);if(!href)return node('span',label||text(value));const a=node('a',label||value);a.href=href;a.target='_blank';a.rel='noopener noreferrer';return a}
function currencyFor(c){return selected.claims.find(x=>x.field==='financials.currency'&&x.availability==='available'&&x.account_scope===c.account_scope&&JSON.stringify(x.reporting_period)===JSON.stringify(c.reporting_period))?.value||''}
function refs(claims){const ids=[...new Set(claims.flatMap(c=>c.evidence_ids||[]))], b=node('button',ids.length?'View sources':'No source available','citation');b.type='button';b.disabled=!ids.length;b.onclick=()=>{focusEvidence=ids;tab='Sources';render()};return b}
function badge(c){return node('span',(c.freshness==='last_known'?'Last known · ':'')+(states[c.availability]||c.availability),'tag '+c.availability)}
function title(field){return labels[field]||field.replace('financials.','Filed ').replaceAll('_',' ')}
function readableSummary(value){return value.replaceAll('official_website','verified website').replaceAll('job_posting','job postings').replaceAll('company_news','company articles').replaceAll('not_available','not found').replaceAll('not_applicable','not applicable').replaceAll('ambiguous','identity unresolved').replaceAll('failed','could not retrieve').replaceAll('scope: SELSKAP','scope: company accounts').replaceAll('scope: KONSERN','scope: group accounts')}
function card(c){const box=node('section',undefined,'card');add(box,node('h3',title(c.field)),badge(c));if(c.availability==='available'){
 if(c.field==='official_website'||c.field.endsWith('_page'))box.append(link(c.value));
 else if(c.field==='company_news'||c.field==='job_posting'){const v=c.value;add(box,node('p',v.headline||v.title),node('p',(v.date_published||v.date_posted||'Publication date unavailable').slice(0,10),'muted'),link(v.url,'Read original'));}
 else if(c.field==='company_declared_profile'){add(box,link(c.value.url,c.value.platform||'Company-linked profile'),node('p','Linked by the verified company website.','muted'));}
 else box.append(node('p',text(c.value)));
 if(c.reporting_period)box.append(node('p',text(c.reporting_period.fraDato)+' – '+text(c.reporting_period.tilDato)+' · '+(c.account_scope||'Scope unavailable'),'muted'));
 }box.append(refs([c]));return box}
function overview(){const stats=node('div',undefined,'grid');['employee_count','official_website'].forEach(field=>{const c=selected.claims.find(x=>x.field===field);if(c)stats.append(card(c))});root.append(stats);
 const summary=node('section',undefined,'card');summary.append(node('h2','What we found'));selected.summary.forEach(s=>{const p=node('p',readableSummary(s.text));p.append(document.createTextNode(' '),refs(selected.claims.filter(c=>(s.claim_ids||[]).includes(c.id))));summary.append(p)});root.append(summary);
 const activity=selected.claims.filter(c=>['company_news','job_posting'].includes(c.field)&&c.availability==='available').sort((a,b)=>(b.effective_at||'').localeCompare(a.effective_at||''));if(activity.length){root.append(node('h2','Latest captured activity'));activity.slice(0,3).forEach(c=>root.append(card(c)))}
 root.append(node('p','This sample shows findings from a bounded search. Missing results are not proof that information does not exist.','muted'))}
function financials(){const claims=selected.claims.filter(c=>c.field.startsWith('financials.')&&c.availability==='available'), table=node('table');const head=node('tr');['Period / scope','Measure','Filed value','Source'].forEach(t=>head.append(node('th',t)));table.append(add(node('thead'),head));const body=node('tbody');claims.filter(c=>c.field!=='financials.currency').sort((a,b)=>text(b.reporting_period?.tilDato).localeCompare(text(a.reporting_period?.tilDato))).forEach(c=>{const row=node('tr');add(row,node('td',text(c.reporting_period?.tilDato)+' / '+text(c.account_scope)),node('td',title(c.field)),node('td',text(c.value)+' '+currencyFor(c)),add(node('td'),refs([c])));body.append(row)});table.append(body);root.append(add(node('section',undefined,'card'),node('h2','Filed accounts'),table));if(!claims.length)root.append(node('p','No filed financial values were available.','notice'));root.append(node('p','Different account scopes are shown separately. Missing values are never displayed as zero.','muted'));selected.claims.filter(c=>c.field.startsWith('financials.')&&c.availability!=='available').forEach(c=>root.append(card(c)))}
function people(){selected.claims.filter(c=>c.field==='roles').forEach(c=>{if(c.availability!=='available'||!Array.isArray(c.value)){root.append(card(c));return}const box=node('section',undefined,'card');add(box,node('h2','Registered management and board roles'),badge(c));c.value.forEach(person=>box.append(node('p',text(person.name)+' · '+text(person.role)+(person.inactive?' · Inactive':''))));box.append(refs([c]));root.append(box)})}
function locations(){selected.claims.filter(c=>c.field==='locations').forEach(c=>{if(c.availability!=='available'||!Array.isArray(c.value)){root.append(card(c));return}c.value.forEach(place=>{const box=node('section',undefined,'card');add(box,node('h3',text(place.name)),node('p','Registered workplace '+text(place.organisation_number),'muted'));const a=place.address;if(a)add(box,node('p',text((a.adresse||[]).join(', '))+' · '+text(a.postnummer)+' '+text(a.poststed)));box.append(refs([c]));root.append(box)});if(!c.value.length)root.append(node('p','No registered workplaces were returned.','notice'))})}
function sources(){if(focusEvidence){const b=node('button','Show all sources','citation');b.onclick=()=>{focusEvidence=null;render()};root.append(b)}selected.sources.filter(s=>!focusEvidence||focusEvidence.includes(s.id)).forEach(s=>{const box=node('section',undefined,'card');add(box,link(s.source_url),node('p','Retrieved '+s.retrieved_at,'muted'));const details=node('details');add(details,node('summary','Evidence details'),node('p',s.excerpt),node('p','Content SHA-256'),node('code',s.content_sha256));box.append(details);root.append(box)});root.append(node('p','Original page snapshots are retained for verification. This public sample includes short attributed spans and links.','muted'))}
function render(){root.replaceChildren();add(root,node('div','Legal company profile','eyebrow'),node('h1',selected.identity.name||selected.org));const meta=node('div',undefined,'meta muted');add(meta,node('span','Organisation '+selected.org),node('span','Updated '+selected.updated.slice(0,10)));root.append(meta);
 const tabs=node('div',undefined,'tabs');tabs.setAttribute('role','tablist');['Overview','Financials','Activity','People','Locations','Sources'].forEach(name=>{const b=node('button',name);b.setAttribute('role','tab');b.setAttribute('aria-selected',String(tab===name));b.onclick=()=>{tab=name;focusEvidence=null;render()};tabs.append(b)});root.append(tabs);
 if(tab==='Overview')overview();else if(tab==='Financials')financials();else if(tab==='People')people();else if(tab==='Locations')locations();else if(tab==='Sources')sources();else selected.claims.filter(c=>['company_news','job_posting','company_declared_profile','careers_page','news_page'].includes(c.field)).forEach(c=>root.append(card(c)));
 document.querySelectorAll('.company').forEach(b=>b.setAttribute('aria-current',String(b.dataset.org===selected.org)))}
function list(){const query=document.getElementById('search').value.toLocaleLowerCase(), results=document.getElementById('results');results.replaceChildren();const filtered=profiles.filter(p=>(p.org+' '+text(p.identity.name)).toLocaleLowerCase().includes(query));filtered.forEach(p=>{const b=node('button',undefined,'company');b.dataset.org=p.org;add(b,node('strong',p.identity.name||p.org),node('small',p.org));b.onclick=()=>{selected=p;tab='Overview';focusEvidence=null;render()};results.append(b)});if(!filtered.length)results.append(node('p','No matching companies.','muted'));document.getElementById('count').textContent=profiles.length+' researched companies';}
document.getElementById('search').addEventListener('input',list);list();render();
</script></body></html>'''
