# DNS/proxy compatibility — 13 October 2026

The URL-validation implementation and offline regressions are complete. **Live
research remains blocked by platform networking.** Local DNS fails for all three
research hosts, while an ordinary registry HTTPS request through the inherited
proxy succeeds. The implemented HTTPS DNS fallback is also denied by that proxy.
The bounded application run produced audited failure envelopes, not acquired
research evidence.

## Snapshot and ownership

Read `AGENTS.md`, the latest `HANDOFF.md` update,
`docs/integration-review-20261012.md`, and the required
`docs/coverage-progress-20261012.md`. `docs/network-diagnosis-20261013.md` was absent.
The integrated evaluator timeout, portable human-review packet generator, and
development live runner were present. Before editing, the standard regression
command passed **205 tests in 19.330 seconds**:

```sh
.venv/bin/python -B -m unittest discover -s tests -q
```

Initial HEAD was `a7c24ef`. The initial checkout included the coordinator's
uncommitted integrated work. An exact copy and SHA-256 manifest of all 125 initial
tracked/untracked project files were retained under
`/workspace/work/network-compatibility/network-initial/`. Only the following
initial files changed; all other 123 initial files retain their original hashes:

- `src/norway_company_agent/website.py`: re-export the shared URL validator.
- `src/norway_company_agent/acquisition.py`: bounded validation, operational DNS
  errors, DNS-request telemetry/budgets, redirects, and unexpected final URLs.

New integration files:

- `src/norway_company_agent/network.py`: public-address validation and optional
  proxied HTTPS DNS.
- `tests/test_network_compatibility.py`: dedicated offline security regressions.
- `docs/task-results/network-compatibility.md`: this report.

These intended files were reported in chat before edits. No extraction,
evaluation, packaging, dependency, strategy-version, or frozen-dataset changes
were made. No commits, configuration publication, paid calls, secrets, holdout
research, competition submission, or publication occurred.

## Runtime and reproduction

Read the cloud-environment-runtime skill and its networking reference. Current
runtime observations are current; phase is `running`, connectivity is `connected`,
HTTP policy is `restricted`, and enforcement state remains **`unknown`**. There
are no configured secrets or outbound identities. The startup policy snapshot
`/etc/codex/network-policy.json` is version 1, records the inherited
`http://proxy:8080`, has `vpn_configured: false`, and has no TCP destination grants.
The configured research hosts are `data.brreg.no`, `www.nf.no`, and `www.nfs.no`.
The executor resolver configuration points at `172.31.4.45`; it was inspected,
never changed.

The initial command sandbox prohibited outgoing sockets. Repeating the diagnostic
with the tool's authorized command-level network capability separated that
sandbox restriction from the managed executor's actual behavior:

| Probe | Observed result |
| --- | --- |
| Local `socket.getaddrinfo` for each research host | `gaierror: [Errno -3] Temporary failure in name resolution` |
| Ordinary inherited-proxy HTTPS GET to registry organisation 984589344 | HTTP 200; exact organisation number `984589344`, name `NORSK FARMASØYTISK SELSKAP`; 2,047 response bytes; default TLS verification enabled |
| Original application `ResearchSession.get` | `AcquisitionError: Hostname did not resolve`, zero source requests/captures |
| `https://dns.google/resolve?name=data.brreg.no&type=A` through inherited proxy | `URLError: Tunnel connection failed: 403 Forbidden`; resolver does not match `NO_PROXY` |

The registry diagnostic response was not inserted into any claim or application
snapshot. It establishes reachable proxied acquisition for that diagnostic only.
The resolver failure is an explicit proxy CONNECT denial, not a DNS API negative
answer, bad company identity, missing registry record, or robots denial.

The cloud resolver problem is real and independent of the application. The
application assumption is that its local resolver must succeed even when the
forward proxy resolves the destination remotely. Neither proxy presence nor an
allowlisted hostname supplies a documented public-IP attestation. No supported
sidecar DNS-answer API was exposed by the inspected runtime guidance.

## Implementation and security behavior

Local DNS remains the default. `SIGNALPOST_DNS_OVER_HTTPS=1` explicitly permits the
[Google Public DNS JSON API](https://developers.google.com/speed/public-dns/docs/doh/json)
at `https://dns.google/resolve` when local resolution raises `socket.gaierror`.
Both the source URL and resolver must select the inherited HTTP(S) proxy;
missing/incompatible proxies or `NO_PROXY` bypass fail closed. The resolver host
has no hardcoded IP, uses standard-library HTTP, and keeps the default CA trust
and hostname/certificate verification. Resolver redirects are prohibited.

The fallback validates both A and AAAA questions, successful/non-truncated
responses, record ownership and CNAME chains, address-family consistency, and
every returned address. Empty resolution, malformed/oversized responses, NXDOMAIN,
SERVFAIL, partial resolution failure, unsafe answers, or network/TLS denial never
authorize a source request. An unsafe local answer never triggers fallback.

URL syntax, embedded credentials, local names, ambiguous numeric host spellings,
private/loopback/link-local/shared/reserved/multicast addresses, and unsafe IPv6
embedded destinations are rejected before transport. Every redirect receives the
same validation. Initial and redirected company pages still require the existing
robots policy; an unexpected final response URL is validated before reading or
retaining its bytes. Existing site TLS-error handling is preserved.

DNS HTTPS calls share a single validation timeout and consume the session's
existing request/deadline budget. Their bytes, latency, success/error state, and
attempts enter telemetry without becoming company evidence. No DNS-answer cache
or unsafe-answer retry was added. The synchronous system resolver itself cannot
be interrupted by this helper; existing worker process supervision still supplies
the hard company/batch bound.

As with the original DNS preflight, validated DNS answers are not pinned to the
proxy's actual connection. The proxy chooses its own DNS view. This change
preserves address preflight rejection; it does not claim to eliminate DNS rebinding
or provide a new proxy destination attestation. A guarantee about actual upstream
connection addresses requires documented/enforced proxy protection or a platform
attestation interface.

## Offline validation

Run each focused suite through the normal `unittest` entry point:

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_network_compatibility.py -v
.venv/bin/python -B -m unittest discover -s tests -p test_competitive.py -q
.venv/bin/python -B -m unittest discover -s tests -p test_development_review.py -q
.venv/bin/python -B -m unittest discover -s tests -p test_poc.py -q
.venv/bin/python -B -m unittest discover -s tests -p test_retrieval_v2.py -q
```

All pass: **37 dedicated tests + 141 existing focused tests = 178 focused tests**.
They cover direct and DNS-derived private targets, mixed public/private answers,
both address families, CNAME/question/response corruption, default opt-out,
proxy bypass, resolver denial, verified TLS handlers and certificate errors,
initial/redirected robots denials, private and public proxied-DNS redirects,
unexpected final URLs, deadlines, and exhausted request budgets. Dedicated
security tests mock DNS and HTTP; no live sockets or company data are used.

An initial combined focused invocation via a Python stdin script produced three
multiprocessing fixture failures because spawned workers could not reopen
`<stdin>`. The standard invocations above resolve that harness problem; all
affected tests pass. The full combined suite was not rerun after implementation;
the coordinator owns that check. `git diff --check` and patch whitespace checks
pass.

## Bounded live check

With command-level network capability enabled, ran the existing supervised runner:

```sh
SIGNALPOST_DNS_OVER_HTTPS=1 .venv/bin/python -B scripts/run_development_review.py \
  --organisations 985215294 984589344 \
  --output-dir out/live-development-review/network-compatibility-20261013
```

Only these two frozen development companies were selected. Limits stayed at one
worker, four pages, 20 requests per company (including resolver HTTPS attempts),
eight seconds per request, 40 seconds per company, and 180 seconds overall.
Wikidata and paid sources stayed disabled.

Results: **11.563 seconds**, four denied DNS-validation HTTPS attempts, zero
response bytes, **zero source captures**, zero cited evidence locators, complete
telemetry, $0 third-party cost. Both workers exited 0 with no unfinished companies
or deadline exhaustion. Both companies have `source_error` registry/website
results. Two terminal envelopes pass the schema/membership/evidence audit with
zero snapshots and zero locators. Runner exit 0 reflects that audit and must not
be reported as successful live research.

Live source fingerprint:
`f4e78005d087b7935392e70adeb04332c5083df663889b4c14952d879520dbce`.
Frozen development input fingerprint:
`537e8659bc16de3ebf2ee319d153a5df763d43dc4b0fff4232f9f4b9cf676b1c`.
Retained application artifacts are under the run directory above: inputs,
profiles, envelopes, report, audit, and per-company telemetry. Sanitized diagnostic
JSON and focused-test logs are under
`/workspace/work/network-compatibility/network/` and in the evidence archive.

## Required external action and integration

Two supported platform actions can unblock validation:

1. Restore functioning DNS for the managed executor through the platform support
   or environment lifecycle workflow. The default local-resolution path then
   needs no application opt-in. Preserve this integrated checkout before a restart
   that replaces its filesystem.
2. Alternatively, allow **`dns.google`** in the managed environment's HTTP policy
   using its supported configuration/review workflow, preserving existing rules,
   and apply the configuration. Verify actual proxied resolver access and current
   enforcement observations, then set `SIGNALPOST_DNS_OVER_HTTPS=1` for the runner.

After either action, rerun only the same two-company development check in a fresh
output directory. Successful resolver access alone does not establish company
page acquisition, robots permission, legal identity, evidence validity, or live
coverage; assess the captured application results separately. No configuration
changes, duplicate company-domain allowlist saves, system DNS/route overrides,
proxy bypass, or TLS-disablement were attempted here.

The integration patch is `docs/task-results/network-compatibility.patch`. It
contains exactly the five implementation/test/report files listed above, with
new files included and diffs computed against the retained **initial working
snapshot**, not against HEAD. Applying it to a copy of that snapshot reproduces
the current owned files byte for byte; all pre-existing integrated changes remain
untouched. The companion SHA-256 manifest and evidence archive are in
`out/network-compatibility/`.

The projectless UI output directory could not be created in this managed executor:
`mkdir /codex/.../output` returned `Read-only file system`. Deliverables are saved
in the repository paths above instead.
