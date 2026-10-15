# First submission draft — not sent

Organizer-confirmed route (Discord, supplied by entrant on 14 October 2026):
email the completed template to **submit@builderr.ai**. The board updates after
official evaluation, not immediately. If there is no reply after one day, email
**inquiries@builderr.ai** with the same details. Record the actual send time to
calculate that follow-up; no message has been sent.

Before sending, fill the exact published commit and contact, verify that commit
from a clean clone, attach/link its 100-company smoke report, and reconcile the
run command with the official resource/credential instructions. This draft does
not freeze an entry and must not be sent with the old import commit.

**Subject:** Signalpost Round 1 entry — reproducible company research agent

**Repository:** https://github.com/ShreyashAnarase/signalpost-starter-kit

**Exact commit:** PENDING — reviewed implementation has not been published.

**100-company smoke-test result:** `docs/submission-smoke-report.md` and
`docs/submission-smoke-report.json`: 100/100 envelopes, 14 verified websites,
seven company-authored articles across three companies and zero jobs. Whole
runtime 173.707 seconds; 1,190 operations; 94 search queries; $0 estimated local
paid fees under the observed free allowance. Package audit: 448 snapshots,
3,164 locators, zero errors. 334 regressions pass.
These results do not establish official precision/recall or a competition score.
The final published commit still needs its own clean-clone verification.

**Install:** `bash scripts/setup_codex_cloud.sh` (Python 3.12+, Linux/POSIX).

**One run command:**

```sh
.venv/bin/python scripts/evaluate_signalpost.py --organisations "$BATCH_FILE" --bulk "$REGISTRY_CSV" --output-dir "$OUTPUT_DIR" --run-id "$RUN_ID" --workers 8 --deadline-seconds 1500 --company-timeout 150 --request-timeout 15 --max-pages 6 --max-requests 60 --evaluator-timeout-seconds 1800 --search-provider tavily --search-max-queries 1100 --search-price-per-1000 8 --search-budget-usd 8.80
```

The official harness supplies batch, registry and output paths. Company count
comes from that batch (currently 1,000, potentially 1,100), never our local sample.
Match supported timeout/request/worker options to the forthcoming shared budget.
See `OFFICIAL_RUN.md` for formats, secrets and optional source configuration.

**Models/APIs/licences:** intended configuration uses Tavily Basic Search to find
candidate websites, public BRREG endpoints and permitted company-owned pages.
Published facts are independently fetched and exact-company matched; search
snippets are never claim evidence. `TAVILY_API_KEY` is supplied securely at runtime,
not in this email/repository. No LLM is currently used. Google Public DNS is an
optional resolver fallback; NAV's free official feed is optional and excluded from
this intended command until permitted production access is configured. Details,
source terms and dependencies: `docs/submission-apis-and-cost.md`.

**Expected cost:** measured 94 queries/100 companies imply $0.752 at the paid
reference rate, or approximately $7.52/1,000 and $8.272/1,100 companies. Details
and limits are in `docs/submission-apis-and-cost.md`. At the checked paid price of $0.008 per Basic
query, the command caps search fees at **$8.80 for up to 1,100 queries**, before
free allowances. This is a declared maximum, not an assumed official budget or
authorization to spend. Compute/storage/hosting/transfer are excluded. Update the
measured estimate from the final smoke before sending, and align limits to the
common official budget. Local tests use a verified free allowance, not this paid
command. No personal-account credential is embedded or assumed for evaluation.

**Caches:** frozen registry snapshot and retained immutable HTTP evidence are
declared. An optional NAV candidate index has an explicit input hash, source
retrieval times and live-verification requirement. It is not reusable published
job evidence. No precomputed profile corpus substitutes for official execution.

**Known limits:** live external coverage remains narrow; no independent human
precision/recall or official score yet. Clean local structural tests on 1,511
supplied inputs demonstrate envelope handling, not live research at that scale.
Refresh from a relocated portable package remains unsupported.

**Contact:** PENDING — entrant's preferred contact details.
