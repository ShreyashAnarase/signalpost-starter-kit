# Builderr runtime access request — held, not sent

User asked to hold the access question while improving the submission. Tavily
remains in the intended search-enabled configuration; see
`submission-apis-and-cost.md`. No outreach is required for development.

Updated after the organizer's Discord clarification, 14 October 2026. Provider,
model, key, limits and the common resource budget will arrive in the official-run
instructions. These are deferred configuration details, not blockers to building
or testing. No personal third-party credential is an official-run dependency.

**Subject:** Signalpost — official-run instructions and optional NAV access

Hello Builderr team,

I am preparing https://github.com/ShreyashAnarase/signalpost-starter-kit.
Thank you for clarifying that the shared batch currently has 1,000 companies and
may grow to 1,100, that you supply the frozen registry snapshot, and that the
provider, model, credentials and limits will be documented in the official-run
instructions. Please include this entry when those instructions are distributed.

Our entry reads the supplied batch and has a pinned install and one run command.
It runs without model/search credentials. Optional search uses candidates only;
published claims come from independently fetched, permitted, exact-company sources.

We also support an explicitly declared NAV feed candidate cache: IDs, source
hashes and timestamps only. Every published ad is freshly verified through NAV's
official detail endpoint and matched to the legal employer. Stale ads disappear
from display while evidence history is retained. If evaluator-owned NAV access is
available, please specify its credential mapping and the permitted cache mounting
arrangement in the official instructions. The documented optional variable is
`NAV_API_TOKEN`; our production command does not fetch public experiment tokens.

We will adapt configuration to the supplied common budget rather than depend on
personal account keys or precomputed profile outputs.

Thank you.
