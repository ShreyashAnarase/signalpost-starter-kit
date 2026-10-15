# NAV private-token request — sent by entrant; response pending

The official [NAV feed documentation](https://navikt.github.io/pam-stilling-feed/)
says experiments may use a rotating public token. A private token requires
consumer registration, written agreement to the
[NAV API terms](https://arbeidsplassen.nav.no/vilkar-api), an identifier, contact
email, phone and contact person. Documentation was rechecked on 14 October 2026.
The entrant sent the registration request and shared NAV's automatic acknowledgment
on 15 October 2026. NAV says it will respond within two days. No private token
has been supplied. The assistant did not send the message.

The original prepared wording below is retained for reference; no duplicate
request is needed while NAV responds. Fill the three contact fields;
they cannot be inferred safely from the repository. NAV's token is entered only
in the prepared optional `NAV_API_TOKEN` secret in environment settings, scoped
to `pam-stilling-feed.nav.no`. Never paste a token in chat or commit it. After
adding it, review/save and publish the environment; the saved draft alone does
not activate access. The optional secret does not block registry/Tavily work.

---

**To:** nav.team.arbeidsplassen@nav.no

**Subject:** Request to register Signalpost as a job-feed API consumer

Hello NAV team,

Please register our Signalpost company-research application as a consumer of the
official job-advertisement feed and issue a private API token.

Identifier: Signalpost — ShreyashAnarase/signalpost-starter-kit

Contact email: **[fill preferred contact email]**

Contact phone: **[fill contact phone]**

Contact person: **[fill contact name]**

Repository: https://github.com/ShreyashAnarase/signalpost-starter-kit

The application finds job advertisements for Norwegian legal entities. We use a
bounded shared candidate index, re-fetch each published ad to confirm active
status and dates, and match the registered employer to the legal company.
Registered workplaces are resolved through the official Brønnøysund subunit
record, with that relationship labelled and both sources cited. We remove
unconfirmed advertisements from current display and direct applicants to the
originating application link. Contact-person data is not included in our public
company profiles.

**[Include the following confirmation only after reviewing and agreeing to the terms:]**
I confirm that I agree to the terms for use of NAV's job-advertisement API at
https://arbeidsplassen.nav.no/vilkar-api.

Please also confirm how the access should be used in a reproducible, time-limited
competition evaluation that runs our same code with documented server-side
credentials, without publishing the token.

Thank you.
