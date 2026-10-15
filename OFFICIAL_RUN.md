# Official evaluator entry point

This describes the current Python implementation. It does not depend on a
precomputed company list, profile export, developer virtual environment, or
credential embedded in the repository. The intended configuration uses Tavily
for candidate discovery through a runtime `TAVILY_API_KEY`. A published exact Git commit is still required
before submission; the development checkout is not an official frozen version.

## Declared installation

Prerequisites: Linux/POSIX, Git and Python 3.12+. From the pinned checkout:

```sh
bash scripts/setup_codex_cloud.sh
```

The script creates a local uv bootstrap if needed, installs through `uv.lock`
with `uv sync --locked`, runs regressions and checks offline refresh.
Installation caches default to the ignored project-local `.tools/` directory;
a writable home directory or pre-existing uv cache is not required. No API key,
registry bulk download or company sampling is part of installation. Optional
Scrapy, browser automation and model packages are not required by this entry point.

## One run command

`BATCH_FILE`, `REGISTRY_CSV`, `OUTPUT_DIR` and `RUN_ID` below name the supplied
input/output paths and run ID; map them to the actual official instructions.
`OUTPUT_DIR` must be new. The registry is a frozen
BRREG-format CSV, optionally gzip-compressed, not a developer's saved profile file.

```sh
.venv/bin/python scripts/evaluate_signalpost.py --organisations "$BATCH_FILE" --bulk "$REGISTRY_CSV" --output-dir "$OUTPUT_DIR" --run-id "$RUN_ID" --workers 8 --deadline-seconds 1500 --company-timeout 150 --request-timeout 15 --max-pages 6 --max-requests 60 --evaluator-timeout-seconds 1800 --search-provider tavily --search-max-queries 1100 --search-price-per-1000 8 --search-budget-usd 8.80
```

This is the intended **search-enabled configuration**, pending the common official
resource/API budget and credential delivery. It allows at most 1,100 Basic search
queries and reserves at most $8.80 at the checked $0.008/query paid rate. This is a
conservative cap, not authorization to spend or an assumed official allowance.
The paid-rate command was not executed locally; bounded local tests use their
verified free allowance with explicit zero price/cap. See
[the API declaration](docs/submission-apis-and-cost.md).

The program derives the company count and preserves input order. There is no
100-company limit and the official command has no `--expected-count 100` flag.
The batch may be JSONL objects with `organisation_number`, a JSON array of IDs or
such objects, or newline-separated IDs. Duplicate/malformed IDs are explicit
input errors. Missing companies and failed acquisition still receive envelopes.
Names and financial values are anchored in registry/source evidence, not trusted
input annotations. Confirm the organizer's actual file formats before freezing.

The default uses eight workers and a 900-second batch budget. The organizer must
supply its actual constraints; supported command options include `--workers`,
`--deadline-seconds`, `--company-timeout`, `--request-timeout`, `--max-pages`,
`--max-requests` and `--evaluator-timeout-seconds`. A large batch producing failed
deadline envelopes does not demonstrate completion within an official budget.

Outputs include `envelopes.jsonl`, `profiles.jsonl`, telemetry `report.json`,
`evaluator-status.json` and an audited portable `package/`. A successful package
audit checks bytes, locators and membership, not an official competition score.
The public product sample remains a separate 100-profile `/signalpost` artifact;
its display limit does not constrain the evaluator batch.

## Credentials and optional sources

The intended command requires `TAVILY_API_KEY` for Tavily Basic website discovery.
The key is supplied securely at runtime and is never part of the repository or
submission email. No model, Brave or NAV credential is required. Omitting all four
search options gives the public-source fallback; its coverage is a separate
configuration and must not be represented by the search-enabled smoke results. TLS verification, proxy trust, DNS/public-address
checks, redirect checks and website robots rules remain enabled. In this managed
cloud environment, `SIGNALPOST_DNS_OVER_HTTPS=1` is the documented resolver fallback;
ordinary working DNS is sufficient elsewhere.

Tavily is our chosen discovery API, not a requirement for the entrant's personal
account. Declare compatible runtime credentials, query/pricing/spending caps and
terms/licences in the submission. Their delivery must follow Builderr's official
instructions. A local free allowance does not establish official-run pricing or
quota. The access clarification is held while development continues, per the user.

NAV jobs are optional: append `--nav-jobs` only when evaluator-provisioned
`NAV_API_TOKEN` access is agreed. The production CLI never obtains or relies on
NAV's rotating public experiment token. Missing/denied NAV access is explicit and
does not drop companies or prevent registry research. The feed scan is shared
once across the batch, bounded by `--nav-max-pages`, `--nav-max-details`,
`--nav-max-requests`, `--nav-timeout` and `--nav-lookback-days`. Defaults prioritize
the last seven days of updates and explicitly report partial coverage; they do
not establish absence of older active jobs. Source timestamps and cache use are
declared in the report.

Builderr's Discord clarification permits a declared official NAV feed cache when
access is permitted and every published ad is live-verified and company-matched.
Append `--nav-cache-input /path/to/candidates.json` to use this optional index and
`--nav-cache-output /path/to/new-candidates.json` to export a new one. Both require
`--nav-jobs`; the output must differ from the input and is never overwritten.
Rows contain candidate IDs/names, optional employer IDs and source hash/times,
not ad bodies or reusable claims. Cache schema, input hash, source retrieval range,
matching/rechecked counts and output status are reported. Every published fact
comes from a fresh detail response with its own evidence; missing credentials
cannot publish cached ads. Missing, invalid or changed caches fall back to live
discovery and are explicitly reported. No cache is required for a clean run.
The index is bounded to 50,000 rows/32 MB; evictions/truncation are declared.

NAV detail extraction supports the live `ad_content` envelope. Some ads identify
registered workplaces rather than the input legal company. The adapter verifies
BRREG's direct workplace-parent record, labels that relationship, and attaches
both source snapshots to the job claim. It never treats a corporate subsidiary
or group parent as an interchangeable legal entity. See
[the real jobs validation](docs/jobs-improvement-20261014.md).

To prepare a declared index with permitted stable credentials, run
`.venv/bin/python scripts/build_nav_candidate_cache.py --output-dir out/nav-bootstrap`.
This is optional source preparation, not installation or a hidden prerequisite.
It publishes no company claims and explicitly reports incomplete coverage.
The evaluator can run cold. Each published ad and workplace relationship is still
freshly fetched; align bootstrap/runtime caps with the common official limits.

For refresh, the evaluator wrapper accepts `--previous-output` with prior raw
envelopes and their retained snapshots. NAV IDs from those input companies are
freshly checked before discovery, even when their publication is outside the
lookback window. NAV resume checkpoints are not reused as active-job evidence.
Unconfirmed NAV ads disappear from current display; prior evidence remains private
audit history. Generic source failures retain qualified last-known non-NAV facts.
Direct refresh from a relocated portable package remains unsupported.

LLMs are allowed by the competition, but none is mandatory or enabled in this
implementation. Builderr says the provider, model, key and limits will be supplied
in the official-run instructions. Work can continue before those arrive. The revised unsent request is
[docs/builderr-runtime-access-request.md](docs/builderr-runtime-access-request.md).
It has not been sent; no unsupported model API or personal key is assumed.

The current official batch is 1,000 companies and may grow to 1,100. There is no
closed external field-family list. Every external claim still needs its source
URL/ID, retrieval time, applicable reporting/effective date, content hash and
extraction method. Search results remain candidate discovery only.

## Clean verification boundary

Release verification must clone the final published repository at its exact
submitted commit, start without `.venv`, `.tools` or generated `out` files, run
only the declared installation and then the evaluator command against newly
supplied inputs. A local isolated candidate commit/clone is useful evidence but
does not replace checking the eventual published GitHub commit.
