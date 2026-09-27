# Reporting and verification

## Audit artifact

For a substantial audit use this structure, adapting length to scope:

```markdown
# Audit — <app> — <date>

## Scope and project profile
Mode, requested scope, relevant facts with sources/confidence, revision/deployment,
and activated/excluded modules with reasons.

## Coverage and baseline
Routes/layouts, journeys/roles, environments, browsers/devices, checks performed,
sampling rationale, existing failures, and unavailable evidence.

## Outcome
Most consequential confirmed findings, release blockers within the inspected scope,
quick wins, and material unknowns. Avoid an unqualified production-ready verdict.

## Findings
| ID | Type | Severity | Area/location | Finding and impact | Evidence | Fix / acceptance criterion | Effort | Status |
|---|---|---|---|---|---|---|---|---|

## Decisions and manual checks
Only decisions or access needed to resolve remaining questions, with their impact.

## Changes and verification
Finding IDs, changes, checks/results, comparison conditions, and remaining limitations.
```

Use short table entries with expanded finding blocks when needed. Do not compress evidence into unreadable cells.

Each actionable finding records:

- Stable ID and classification: confirmed defect, suspected risk, or recommendation.
- Severity and rationale; suspected severity remains provisional.
- Specific location and revision/environment.
- Expected and actual behavior; relevant requirement or product expectation.
- Redacted evidence and reproducible steps when applicable.
- Verification method: static, reproduced, externally verified, or unverified.
- Minimal proposed fix, dependencies, rough effort, and acceptance criterion.
- Current status and fix-verification evidence.

For example, a confirmed ownership bug names the endpoint/check location, describes a controlled user-A/user-B test without real personal data, and requires both cross-user denial and successful owner access after correction. A missing gateway configuration is instead an unknown until inspected.

## Severity

- **Critical:** Confirmed severe exposure, destructive data failure, or a blocker making the core product unusable, with impact sufficient to block release.
- **High:** Major functional failure or barrier affecting important journeys, or substantial evidenced security/reliability risk.
- **Medium:** Limited functional defects or meaningful usability/maintainability issues without major impact.
- **Low:** Minor inconsistencies or cleanup.
- **Recommendation:** Optional improvement; keep separate from mandatory defect severity where clearer.

Consider affected users, likelihood/exploitability, data sensitivity, and recovery. Legal uncertainty alone is not Critical, and aesthetic preferences are not High by default. Sequence dependencies and low-effort fixes after risk ranking; do not enforce a fixed category order.

## Check and finding statuses

Keep coverage separate from remediation:

- Check: passed, failed, not applicable, not checked, or blocked.
- Finding: open, in progress, implemented/unverified, verified fixed, deferred, or accepted risk.

A pass requires a performed check. Record reasons for skipped/blocked checks and evidence for accepted risk; do not claim the owner accepted a risk without their decision. Preserve stable IDs across reruns and identify obsolete findings explicitly.

## Verification and completion

Capture relevant pre-change failures so new regressions remain distinguishable. Verify a fix against its acceptance criterion and important neighboring behavior. Use existing test/build/lint/type tools where applicable and inspect actual results. Commands that did not run or do not exist cannot pass.

Use targeted checks per batch, then broader applicable checks at integration boundaries. For low-impact cosmetic changes a visual check may suffice; sensitive behavior requires stronger evidence. If checks are unavailable, perform meaningful alternatives and label the remaining limitation.

Separate four outcomes:

1. **Audit complete:** Agreed scope assessed, with sampled/blocked areas disclosed.
2. **Implementation complete:** Authorized changes made; pending verification identified.
3. **Fix verified:** Acceptance criterion supported by current evidence.
4. **Release readiness:** Remaining blockers and unknowns assessed within stated coverage; not inferred solely from green tooling.
