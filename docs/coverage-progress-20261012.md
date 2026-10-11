# Coverage and evidence progress — 12 October 2026

The known four-company retrieval set improved from 1/4 to 3/4 verified websites.
This is a selected development set, not a recall estimate. A separate, newly frozen
24-company stratified development set produced 6 verified websites, no dated jobs,
and no dated news. Winning-score coverage remains unproven.

## Changes

- Decode HTML using declared/detected character encoding and carry the chosen
  encoding into evidence locators so offline audit reads the same characters.
- Follow same-host frames and image-map links within existing crawl budgets.
- After a TLS connection/certificate failure, try public HTTP with its own robots
  policy and full URL checks. Certificate verification stays enabled. Denials do
  not trigger fallback.
- Recognize an older contact-page pattern: complete legal name in a bold paragraph
  label and the registered phone in the same compact block. Partial names and
  phones elsewhere do not establish a match. Conflicting footer owners anywhere
  in the crawled pages reject the site.
- Cite the identity-bearing page for the website claim. Preserve CSS locators for
  nested footer text; privacy/cookie pages no longer become contact-page claims.
- Allow bounded graceful worker shutdown. Both new live runs exited with code 0.
- Fingerprint source files, dependency manifests, strategy and input for resume.
- Reject missing/corrupt prior snapshots during refresh while preserving newly
  acquired facts. Last-known leadership is explicitly qualified in summaries.
- Add offline retained-page re-extraction/export with separate acquisition and
  export source hashes, and a mandatory evidence audit.

## Measurements

| Run | Companies | Verified sites | Requests | Runtime | API cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Targeted development v4 | 4 | 3 | 37 | 63.505 s | $0 |
| Stratified development v1 | 24 | 6 | 230 | 73.097 s | $0 |

Both live runs emitted every envelope and had complete telemetry and no deadline
exhaustion. Requests include redirects; latency observations count outer attempts.

Targeted results: Aas Elektronikk is supported by the exact company name and
registry mobile number on its HTTP contact page. Bærum Eiendomstaksering is
supported by the complete legal name and registered mobile in one contact
paragraph. AIOTA remains verified. APPELX remains rejected because STUDIO X's
footer identifies another legal company.

The 24-company diagnostic set allocates three companies to each combination of:
finance/property versus other sectors, 5+ employees versus small/unknown staff,
and registry website present versus absent. It oversamples website-bearing
companies; **6/24 must not be compared with the old random smoke result of 1/100**.
Missing staff counts remain missing. Sampling excluded the 100 previously used
companies, including the four targeted examples. The separate 24-company holdout
has not been crawled or reviewed.

Six positive matches were inspected by the Codex assistant against retained page
text and registry records: AS Thor Dahl, MittEgetLokale, M3 Utleie, Jon Sæter,
Norvigroup Norsk Dun, and Norsk Farmasøytisk Selskap. This is not independent human
review. The remaining 18 companies are unresolved, not true negatives. Jon Sæter
was discovered through the registry email domain. Results by stratum and explicit
review notes are retained in `out/coverage-development-v1-final/`.

## Evidence artifacts and reproduction

- `out/development-v4-live/`: immutable live acquisition output. Its original
  envelope audit caught one nested-footer locator error; do not use that export.
- `out/development-v4-reviewed/`: corrected offline export; 4 envelopes,
  21 unique snapshots, 136 locators, no audit errors.
- `out/coverage-development-v1/`: live acquisition profiles and resource report.
- `out/coverage-development-v1-final/`: final offline export; 24 envelopes,
  119 unique snapshots, 812 locators, no audit errors. This removes the two
  privacy/cookie contact claims and records the final export source fingerprint.
- `data/coverage-review-v1/`: frozen development and holdout inputs and manifest.

Run all regressions:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests -q
```

Re-export without networking into a **new** directory:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/reexport_competition.py \
  --profiles out/coverage-development-v1/profiles.jsonl \
  --acquisition-report out/coverage-development-v1/report.json \
  --output-dir out/coverage-development-v1-replay
```

Re-export validates retained bytes and re-extracts already accepted sites. It
cannot discover new sites or retry previously rejected candidates. Acquisition
times remain source retrieval times. Reports distinguish the acquisition source
hash from the export source hash; no re-export is claimed as a new live run.

## Next work

1. Improve discovery for companies without registry website/email candidates:
   11/12 of that half of the diagnostic sample remain unresolved. Even recognizable
   businesses such as Storebrand Livsforsikring have no candidate under the current
   strategy. Independently verify every candidate; do not add hardcoded answers.
2. Investigate jobs/news article discovery. Navigation pages were found but no dated
   facts were emitted. A news index is not itself evidence for individual events.
3. Expand independent human labels before interpreting precision or recall, then
   use the untouched holdout once the strategy is stable.
4. Finish portable evidence packaging, remaining official-field regressions and
   a final current-source 100-company smoke before considering larger runs.
5. Ask about organizer-supported search/model credentials and resource budgets
   later; no paid calls or credential collection occurred. No publication,
   repository creation or submission occurred.
