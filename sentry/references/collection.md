# Scope, counts and evidence

Use for status/check and when selecting event evidence for a fix.

## Environment coverage

Retrieve project environments with hidden ones included where supported. Prefer the environment
inventory over grouped recent events: quiet or hidden environments may have no recent events.
If inventory is unavailable, use observed events as a bounded fallback and label discovery partial.
With the Sentry MCP there is no inventory tool: aggregate error events by environment over the
longest period (`search_events`, dataset `errors`, fields `environment` and `count()`, `90d`). That
lists only environments *with errors* — a configured environment missing from it is "no errors
seen", not "does not exist"; say so.
Missing/untagged environment values must remain visible as an unknown-environment bucket when
returned by an unfiltered query, not disappear during grouping. Attribute an untagged event to an
issue only when its event/group identity establishes that relationship; proximity in a summary
is not evidence of membership.

- `all` (also: no scope given): **first discover the environments** — inventory, or with the Sentry
  MCP the event aggregation above; a failed or read-only-blocked discovery path is no reason to fall
  back to the configured list alone. Then query the configured project's issues without an
  environment filter as a coverage backstop, plus per-environment results for configured and
  discovered environments. Unmapped
  environments remain unclassified; do not automatically treat them as dev or local noise.
- `prod`/`dev`: query each mapped environment in that scope. Show discovered unmapped names as a
  coverage warning; do not inspect their event payloads or silently widen scope. If real production
  errors may be mislabelled outside scope, explain the gap and propose `all` or a mapping correction.
- Empty scope: "no environments configured for this scope", not "zero production errors".
- New assignments require user/project evidence. Reuse explicit assignments already provided.

Use identical project, status and time filters for comparable queries. Quote/encode environment
values with the actual tool/query syntax; a name containing spaces is one value. Default window is
the last 14 days — as `period: "14d"` where the tool only supports relative periods (Sentry MCP),
as explicit UTC start/end where it supports them (REST). Fresh issues use the last 24 hours **within** that window;
regressions need status/history evidence because they may have old first-seen dates.

## Exact versus sampled results

Status totals require complete pagination or an aggregate explicitly matching the same filters.
A top-N list is a sample, never a total. A simple completeness test for list tools with a `limit`:
fewer results than the limit means the list is complete for that query (exact); exactly `limit`
results means "at least N" — raise the limit (Sentry MCP `search_issues`: up to 100) or paginate,
and label the number a lower bound if that is not possible. Triage may sample approximately eight frequent and eight
new issues per environment and include observed regressions/high-impact issues; show the sampling
limits and do not claim all issues were reviewed. Do not rank only by frequency: security, data
loss and critical user flows outrank routine noisy errors even with few reported users.

Deduplicate using stable issue ID and verified project; retain every matching environment. Never
sum issue-wide `count`/`userCount` as environment-specific totals. Request filtered event aggregates
for that environment and window when needed, or mark those metrics unavailable. Distinct users
across issues require a deduplicated aggregate; unknown is not zero. Missing severity values belong
in an unknown bucket rather than being discarded from the breakdown.

Record tool/endpoint, filters, window, retrieval time and pagination/aggregate coverage. A failed
page makes coverage partial even if earlier pages succeeded. Deduplicate moving results and note
that current unresolved status can change during collection; do not promise an atomic snapshot.

## Local noise and representative events

Select event evidence for the relevant environment and release. An issue's latest event can come
from another environment; one local event never makes the entire grouped issue local noise.
Inspect a representative server/production event when available. A release SHA alone is not proof
of production: local builds also have releases. Contradictory/missing tags mean uncertain origin;
keep the issue visible. Explain noise classifications with positive local evidence and retain
nonlocal occurrences as actionable.

[Environment inventory](https://docs.sentry.io/api/environments/list-a-projects-environments/)
includes a visibility selector. [Organization issue search](https://docs.sentry.io/api/events/list-an-organizations-issues/)
supports project/environment and time filters; short-ID lookups may bypass project filters, so
verify returned ownership separately.
