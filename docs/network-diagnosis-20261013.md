# Network diagnosis after publication — 13 October 2026

Runtime observations are current; configured destination policy now reports
`enforced` for data.brreg.no, www.nf.no and www.nfs.no. The instance is running.
There are no configured secret bindings or VPN. Publication is confirmed by the
user; network status alone does not prove a particular DNS service is reachable.

Fresh checks in the selected executor:

- The proxy hostname resolves locally.
- Local getaddrinfo fails with temporary name-resolution errors for the official
  registry and both company hosts.
- An inherited-proxy HTTPS registry request succeeds with TLS verification enabled
  and returns organisation 984589344 exactly.

The failure is specifically the crawler's assumption that local origin-host DNS
resolution is available before a proxied HTTP request. Managed networking supports
HTTP through a sidecar; functioning proxy HTTPS does not establish local DNS health.
The exact cause of origin-DNS failure remains unproven: resolver reachability,
network design and executor configuration need distinction. Do not report missing
credentials, an unapplied allowlist, or universal Internet failure.

Earlier advice to restart was a troubleshooting proposal, not a demonstrated
remedy. Starting a fresh task from the published environment can provide a fresh
executor but may reproduce the same behavior. No verified restart UI control or
restart tool is available to this coordinator. Repeated publication/restarts are
not a justified next diagnostic step.

Next technical work: investigate a supported way to validate destination DNS
through the managed proxy or restore configured DNS reachability, while retaining
private-address rejection, redirect checks and TLS verification. Do not disable
the existing public-URL gate merely to make acquisition run. No code/network
configuration was changed by this diagnostic step.
