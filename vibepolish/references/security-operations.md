# Security, data integrity, and operations

Scale depth to exposure and consequences. Static inspection is not a penetration test or security certification. Active negative tests require an appropriate isolated environment and authorization.

## Trust boundaries

- Classify endpoints as public, authenticated, privileged, or machine-to-machine. Each must enforce the policy appropriate to its purpose; public endpoints do not universally require login.
- Trace authentication and authorization through handlers, services, data access, and infrastructure. Verify ownership, role, and tenant boundaries where relevant.
- Test cross-user and cross-tenant denial with controlled fixtures when authorized. Hidden UI controls are not access control.
- Inspect trusted server-side validation, output encoding, user/AI HTML rendering, injection risks, unsafe URL fetching, and redirects.
- Evaluate session storage, cookie flags, CSRF protection, and CORS in the actual architecture. CORS is not a substitute for authorization; a public API may intentionally allow broad origins.
- Inspect abuse controls for costly or sensitive operations, including quotas and limits where upstream infrastructure may implement them.
- Security headers should suit the app and deployment. Evaluate CSP compatibility before changing enforcement; do not blindly break necessary embeds or integrations.

## Secrets and exposure

Use redacted scanning output. Report secret type and location only. Inspect source, relevant history, generated bundles, and deployment surfaces when within scope. If exposed credentials are confirmed, identify rotation/revocation and history-remediation needs; deleting the current literal alone is not remediation. Do not rewrite Git history or rotate live credentials without authorization.

Review storage access, debug artifacts, administrative surfaces, verbose errors, and unintentional source exposure. Public source maps are a context-dependent exposure decision, not automatically a vulnerability. Private upload to monitoring may be appropriate.

Dependency audit results need version, affected path, exposure/reachability where assessable, and remediation risk. Do not apply forced upgrades simply to clear a scanner. License concerns require relevant evidence about intended use.

## Data integrity

Check transactions and invariants for consequential multi-step writes, uniqueness constraints, concurrency, idempotency, cache invalidation, and rollback behavior. Examine migrations and compatibility with rollout/rollback when database changes are in scope.

Represent instants, dates, local times, currencies, and recurring schedules according to their semantics. Do not convert every date-like value to UTC: birthdays and local recurring schedules require different treatment.

## Maintainability

Prioritize code issues that affect correctness, exposure, performance, or change safety. Unused code and duplicate components are recommendations unless concrete impact is shown. Logging can be intentional; remove debug noise without disabling operational diagnostics. Do not require a broad architectural refactor or a single data-fetching style solely for uniformity.

## Operations

According to the app's operational needs, inspect:

- Reproducible setup/build/deployment, relevant CI checks, and configuration documentation.
- Useful redacted logs, error visibility, and an actionable alert destination.
- Health checks and monitoring appropriate to the service.
- Backup coverage and evidence of a successful restore, including file storage when needed. Backup configuration alone does not verify recoverability. Restore tests use isolated targets.
- Deployment rollback or roll-forward strategy and migration compatibility.
- Background jobs, retries, duplicate processing, and failed-job recovery when present.
- Resource/cost limits and degraded behavior when a dependency is unavailable.

Missing access to infrastructure is an unknown, not proof that monitoring or backups do not exist. Avoid imposing enterprise infrastructure on a small static site.
