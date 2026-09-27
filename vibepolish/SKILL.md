---
name: vibepolish
description: Audit and improve web apps, especially quickly built or AI-assisted apps, for visible polish, functional quality, and launch readiness. Find unfinished details and evidence-backed risks; implement verified fixes when requested. Use for app audits, pre-launch reviews, and requests to make an app look less unfinished, template-like, vibe-coded, or AI-generated ("AI slop"). Keep requests about one area focused on that area and its direct dependencies.
---

# Vibepolish

Answer in the user's language; keep file paths, identifiers and quoted source text as they are.

Improve the app users actually have. Preserve its intended behavior, brand, architecture, and existing conventions. Cover both visible finish and underlying product risks. Weight them according to the request and observed impact: a visual-polish review emphasizes presentation, while a launch audit prioritizes release-blocking failures and exposure. Appearance alone does not establish whether an app was AI-generated. This skill supports web apps across stacks; native apps require a separate platform-specific checklist and must not receive a web-based readiness verdict.

## 1. Establish mode, scope, and authorization

Infer the mode from the user's request and briefly state the scope. If the request only asks to check, review, or inspect, use an audit-only mode unless the conversation already authorizes fixes. Ask only when missing information materially blocks the work.

- **Focused review:** Inspect the requested area and directly affected dependencies. Do not expand a title fix into a full audit.
- **Launch audit:** Assess applicable launch risks and representative user journeys. Report findings without implementing fixes.
- **Audit and fix:** Inspect first, then implement within the user's existing authorization, using the risk assessment below.

User instructions take precedence over this workflow. Do not interpret an audit request as permission to change the app. Conversely, do not impose an approval round for changes the user has already clearly authorized.

### Authorization and change risk

Assess each change by its fit with the requested outcome, user-visible behavior, potential harm, external effects, and reversibility. File count, a shared component, or a category label alone does not decide whether approval is needed.

- **Proceed within existing authorization:** necessary, proportionate changes that preserve the intended product behavior, including fixes to shared components and meaningful regression tests using existing infrastructure. Keep batches small and verify the affected surface. A broad fix request does not require repeated permission for routine implementation details.
- **Ask for a decision when scope or intent is unresolved:** substantial visual redesign, new product behavior, breaking contracts, new tooling/infrastructure, or consequential changes whose tradeoffs the request does not settle. Prepare a concrete proposal and continue independent authorized work while waiting.
- **Assess consequential operations explicitly:** dependency changes, schema/migrations, auth/authorization, payments/entitlements, indexed URLs, security enforcement, and external effects require closer assessment. Identify the operation, affected environment/data, known consumers and contracts, supporting checks, and recovery path. If a material compatibility or data-loss question remains unresolved after inspecting available evidence, prepare a focused proposal and ask before the dependent change; do not assume missing consumers do not exist. Explain new runtime dependencies through necessity, existing alternatives, and maintenance/bundle implications. Seek a decision when that tradeoff exceeds the request. Patch/minor versions alone do not establish safety. Existing authorization may cover implementation without covering deployment, a production migration, real payments, or messages.

Do not run destructive or consequential external operations without authorization covering the operation and environment. Distinguish preparing and testing a fix in isolation from applying it to production. Never delete files of unclear purpose merely as cleanup; establish their role first.

Record material decisions in the report. Honor authorization already given; do not require the user to waive a generic tier. For broad audit-and-fix work, first record a bounded, prioritized inspection overview as described in section 6; then report progress incrementally. In audit-only mode, deliver findings without implementation.

For broader work, agree or infer a practical coverage boundary: product areas, environments, critical journeys, browser targets, and any time budget. Report limitations; never imply exhaustive coverage from a sample.

## 2. Discover only the context needed

Start with the conversation, memory, and applicable project instructions (e.g. `CLAUDE.md`, `AGENTS.md`, editor rule files), then inspect relevant manifests, lockfiles, configuration, routes, shared components, environment templates, and existing checks. Read docs and recent history only when useful. Avoid loading the whole repository or every reference by default.

Record facts with source and confidence:

- App purpose, principal users, and critical journeys.
- Stack, rendering model, package manager, and existing design conventions.
- Target environment and known production domain.
- Public/indexable, authenticated, and administrative surfaces.
- Auth, data stores, uploads, payments, email, analytics, and AI integrations.
- UI languages and locales; operator location and target markets if known.
- Sensitive data, data flows, and external services.
- Available build, lint, type, test, browser, deployment, and monitoring tools.
- Current revision, working-tree changes, and any relevant deployment identifier.

An SDK suggests a capability; it does not prove that the capability is active. Language, currency, and TLD suggest markets; they do not establish legal jurisdiction. Distinguish observed, inferred, and unknown facts. Never expose secret values while discovering configuration.

## 3. Activate applicable checks

Load only references relevant to the scope:

| Reference | Read when |
|---|---|
| [Vibe-code tells](references/vibecode-tells.md) | Launch audits and visible-polish work; for focused UI, copy, or metadata requests, read only the relevant sections |
| [Product quality](references/product-quality.md) | Reviewing journeys, states, forms, accessibility, responsiveness, design, or content |
| [Web delivery](references/web-delivery.md) | Reviewing deployment, public discovery, browser performance, or installable web apps |
| [Security and operations](references/security-operations.md) | Assessing security, data integrity, maintenance, or launch reliability |
| [Conditional services](references/conditional-services.md) | Relevant auth, payment, AI, email, upload, localization, or privacy capabilities exist |
| [Reporting and verification](references/reporting-verification.md) | Producing an audit report or implementing findings |

For a launch audit or broad audit-and-fix request, assess applicability across the four check domains and include relevant vibe-code tells. Start with likely high-impact failures and critical journeys; there is no mandatory cosmetic-first order. Always consider functional integrity, accessibility, security exposure, and operational needs at a depth appropriate to the product.

SEO and social previews apply to indexable or shareable content. PWA checks apply only to an existing or intended PWA. Analytics checks apply when tracking exists or is requested. Privacy checks apply whenever personal data is processed, including internal tools. Optional features are not defects merely because they are absent.

Infer scope from the whole request and conversation. An app-wide request to reduce an unfinished or template-like impression includes the brief exposure check unless context limits the work to presentation. A request confined to specific visual elements remains focused. For applicable broad polish requests, include a short, non-mutating exposure check: potentially privileged credentials in client/public surfaces, sensitive debug/admin/test routes, and available rules for direct client database access where present. Respect narrower user scope. Inspect context before classifying a hit: public client keys, route existence, or missing infrastructure access do not prove exposure. Report limits and do not imply a complete security audit. Do not run live probes without the access and authorization they require.

## 4. Inspect safely and collect a baseline

Separate **no source changes** from **no external side effects**. Clicking buttons, signing up, submitting forms, uploading files, and exercising delete flows can mutate systems even during an audit.

- Start with static inspection and non-mutating observation.
- Before state-changing tests, establish environment, test accounts/data, permitted effects, and cleanup. Prefer isolated local or staging fixtures and provider sandboxes.
- Do not send real messages, make real payments, delete real records, deploy, or alter external configuration without authorization covering that action.
- Inspect relevant scripts before running unfamiliar project commands. Builds and test hooks can access services or perform mutations.
- Prefer installed tooling. Temporary package execution is still code execution: choose a trusted tool and version, assess its effects, and do not treat `npx`/`pipx` as an automatic exemption.
- Keep secrets and personal data out of commands, reports, screenshots, and stored logs. Secret scanning should emit redacted locations and types, not matched values.

Before fixing, capture relevant existing check results and representative screenshots or measurements. Use the same conditions for comparisons. Record pre-existing failures separately — but a failure counts as pre-existing only when the same test or check fails for the same cause on the unchanged starting state under comparable conditions, and the changed behavior can still be checked meaningfully. Equal failure counts prove nothing; missing coverage is not a baseline. Compare in a separate checkout or from the recorded starting state — never reset or stash the user's changes to do it. Unclear cause keeps the check open; required CI is not waived, and a limited result is never reported as all green. Do not execute every available check for a trivial focused review.

Map routes/layouts for broad audits. Cover critical journeys and distinct layouts, then sample repeated pages and states based on risk. Expand a sample when a finding suggests a shared defect. Browser unavailability reduces verification coverage; it does not establish a pass.

## 5. Turn observations into defensible findings

Use the finding schema and status model in [Reporting and verification](references/reporting-verification.md).

Every confirmed finding needs evidence, user/system impact, expected versus actual behavior, and a testable acceptance criterion. A missing implementation in the repository does not prove a missing capability at the gateway, hosting provider, or external service. Mark such cases as hypotheses or checks requiring access. Assets have three levels of evidence: *not found in the supplied material* (a build step, CDN or public directory outside your view may still provide it — a hypothesis, not a defect); *broken locally*, shown by a reproducible build, runtime or decoding failure (a confirmed defect of that build — not proof of a production outage); and *broken on the target system*, shown by an observed failed request or render there.

Separate:

- **Confirmed defects:** Behavior or configuration demonstrably violates a relevant requirement.
- **Suspected risks:** Plausible concerns whose decisive evidence is unavailable.
- **Recommendations:** Optional improvements or design judgments, with rationale.

Rank confirmed defects by impact, reach, likelihood, and reversibility. Use effort and dependencies to sequence comparable risks. An inaccessible checkout can outrank metadata; visual taste does not become a security-level incident.

Guard against errors in both directions. Do not manufacture findings from search hits, and do not dismiss evidenced problems merely because each looks small. For requests specifically about unfinished or template-like appearance, report relevant, concrete presentation observations with their likely effect and an actionable alternative. Keep subjective choices separate from defects; if none warrant change, say so. For other requests, listing a few relevant design choices is optional. Unknown intent alone neither proves a defect nor forces omission. Ask for an answer only when a pending implementation needs that decision; omit ungrounded preferences. Several concrete inconsistencies on a key page may justify one grouped finding about clarity, trust, or finish. Explain the combined effect without inflating severity by counting duplicate symptoms. Respect the agreed scope; report an incidental serious risk briefly without automatically expanding the audit.

## 6. Report or fix according to the mode

For a substantial audit, write `AUDIT.md` in the project's documentation location, or another user-requested location. Preserve prior reports and stable finding IDs; do not overwrite unrelated content. For a small focused review, an inline result may be sufficient. Report creation is the permitted artifact write in an otherwise non-implementation audit.

In audit-only modes, stop after delivering findings and proposed next steps. In audit-and-fix mode, implement changes covered by existing authorization. Pause only the work that needs an unresolved decision or additional authorization, and continue independent authorized work.

For broad audit-and-fix requests, complete a bounded first inspection across applicable areas and critical journeys, then save a prioritized finding list and uninspected areas before the first product change. This is not an exhaustive audit or an approval gate. Fix in risk/dependency order and keep statuses current so interruption leaves a useful record. Narrow fixes do not need this extra artifact.

Before a fix, identify the acceptance criterion and check baseline. Make small, reversible batches tied to a coherent defect or behavior. Avoid unrelated refactors and preserve uncommitted user work. Cross-file fixes are acceptable when needed for one behavior.

Record the starting working-tree state and preserve existing user changes. For substantial or risky batches, keep a practical recovery checkpoint: commits if authorized by user/project conventions, reviewed patches, or targeted snapshots. Ensure the checkpoint distinguishes your changes from pre-existing work and includes relevant untracked files without capturing secrets. Use isolation only when it preserves the necessary starting state: a branch alone does not isolate a dirty working tree, and a fresh worktree does not automatically include uncommitted changes. Do not automatically commit, push, or deploy; follow the user's request and project conventions.

**Projects that use `/dev`.** During an active phase (`[~]` or `[!]` in `ROADMAP.md`) the fixes belong to that phase: record them there and leave verification to its quality gate — `/dev check` refuses to start during a phase. Outside a phase `/dev check` is the gate, but it ends with a commit: use it only when commits are already authorized (by the user or project conventions); otherwise run the equivalent checks without committing and name the gate steps still open. Calling another skill never grants a permission this one lacks. Reuse earlier gate results only while code, scope and acceptance criteria are unchanged; never run a second gate or create a second closing commit for the same change.

Verify changed behavior and relevant regressions. A visual change without browser access stays *visually unverified* — say so, and support it with what can be measured (contrast ratio, sizes) instead. Add tests where they meaningfully protect behavior or risk; do not add tests solely to mirror a cosmetic edit. Run broader checks once at integration boundaries unless a failure or new change warrants repetition.

When a fix becomes materially larger or riskier than assessed, pause that fix, explain the new information, and continue independent authorized work where possible.

## 7. Close with a bounded result

Report what was inspected, what changed, how it was verified, and remaining blockers or unknowns. Even a one-line fix ends with that line: which checks ran, which did not (for example "no browser available — visual result not verified"), and, in a `/dev` project, where the change stands with respect to its gate (the active phase's gate, or open). Distinguish audit completion, implementation completion, verified fixes, and release readiness. Passing builds alone do not establish production readiness.

For follow-up runs, retain finding IDs, record the new revision/deployment, recheck open findings and changed dependencies, and broaden coverage only when justified. Never reuse a prior pass as current evidence without assessing relevant changes.

## Skill maintenance

Behavioral evaluation scenarios live in `evals/evals.json`; they are not part of routine app audits. Some cases include small fixtures, while environment-dependent cases remain scenario specifications. Read `evals/README.md` only when evaluating or changing this skill. Do not claim an evaluation passed unless it was executed and its observed result was assessed.
