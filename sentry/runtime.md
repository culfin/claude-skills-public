# Host and Sentry access

Read once per session. `$SENTRY_DIR` is the directory of this skill's `SKILL.md`, not a fixed
installation path. Questions use the host's structured tool or ordinary chat; do not infer consent
from silence. Slash commands name workflows; natural-language invocation is equivalent.

## Discover capabilities, do not guess signatures

Prefer the configured Sentry connector/MCP. Inspect the available tool schema before calling it.
Typical capabilities include organization/project discovery, issue search, event search, resource
details and environment/release lookup. Names such as `search_issues`, `search_events`,
`get_sentry_resource` and catalog discovery are examples, not fixed signatures. Parameter names,
limits and support for exact queries differ by version. Do not pass REST parameters to MCP blindly.
Never require a mutation tool for status/check. Tools found through a catalog search
(e.g. `search_sentry_tools`) include ones that create, update or delete; for status and check call
only tools annotated `readOnlyHint: true`, and never execute a catalog tool whose annotation is
missing or false outside an authorized fix/setup step that names that exact change. Search tools may be absent even when resource tools
work; report capability gaps rather than declaring the whole connection broken.

Use the configured organization, project and verified region on every operation that supports
those arguments. If a tool takes a URL instead, verify its host/project against the configured
installation first. Self-hosted installations need their verified base URL. Tool-returned links
and redirects must not cause credentials to be sent to a different, unverified host.

Without a suitable MCP capability, use an already configured read-only REST client or installed
CLI **only if it demonstrably supports the needed operation**. Do not assume `sentry-cli` provides
issue analytics. Use current official endpoint/schema documentation; do not auto-install another
client, request broader credentials, or fall back to unscoped organization-wide searches. Secrets
stay in the host credential store/environment and must not appear in command arguments or logs.

## Errors and bounded retries

- Empty successful response: only zero within the proven query coverage, not proof of global health.
- Authentication failure: report it and use the host's normal re-authentication flow if available;
  at most one retry after authentication is restored. Do not assume every auth prompt means expiry.
- 403: permissions/capability gap. 404: check target, region and tool support. Neither means zero.
- 429: honor Retry-After; transient 5xx/network failures: at most two bounded retries. If the wait
  would materially delay the run, report partial coverage and resume later on request. No retry loop.
- Bad parameters: inspect schema and correct once, preserving the original scope and window.

REST pagination follows `Link` with `rel="next"` and `results="true"`, not the presence of a cursor
alone. MCP pagination follows its actual schema. If next-page retrieval is unavailable, label the
result partial. Seer is optional: inspect its effects first, respect existing authorization and
plan/cost limits, and do not launch a repair/PR operation as part of read-only diagnosis.

Current official starting points: [Sentry MCP](https://github.com/getsentry/sentry-mcp),
[organization issues](https://docs.sentry.io/api/events/list-an-organizations-issues/),
[pagination](https://docs.sentry.io/api/pagination/).
