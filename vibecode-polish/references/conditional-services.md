# Conditional services and privacy

Read and apply only sections activated by actual capabilities. Test external effects using approved test environments.

## Authentication and accounts

Check implemented flows and their invalid/expired paths: login/logout, registration, recovery, verification, and provider callbacks as applicable. Do not demand password reset for a passwordless-only product.

Verify session expiry/revocation, server-side access checks, safe return URLs, and account lifecycle behavior. Prefer established provider patterns; assess cookie/token storage in context. Check export/deletion where applicable to product requirements and confirmed obligations, including downstream data stores and backups under the retention policy.

## Payments

Verify server-trusted price/product selection and entitlements, webhook signature validation, idempotency, retry and out-of-order event handling, and reconciliation after missed events. Cover implemented pending, failed, cancelled, refunded, and subscription lifecycle paths. Keep test/live resources separated. Use test mode for purchases; never infer success from a browser redirect alone.

## AI and agent features

Check server-side credentials, per-user cost/rate limits, bounded requests/tool loops, timeouts, cancellation, streaming failures, and provider outages. Treat retrieved content and model output as untrusted. Constrain tools and permissions independently of prompts, and verify authorization before consequential actions. Check rendered output safety, sensitive-data flow, and tenant isolation in retrieval/caches. Evaluate quality against task-specific examples if the product depends on output accuracy; do not treat successful API calls as quality verification.

## Email

Verify sending-domain authentication and actual provider configuration where accessible; do not infer configuration solely from code. Inspect template links, readability, text fallback, and intended sender identity. Check bounce/unsubscribe/suppression behavior as applicable. Use test recipients or provider sandboxes before sending; distinguish transactional and marketing requirements.

## Uploads

Inspect server-side size/content/type checks, access control, storage naming, retrieval headers, quotas, and dangerous active content. Consider image-processing failures, archive expansion, and malware controls according to risk. Private uploads must remain private when served, transformed, or cached. Use harmless fixtures.

## Localization

Check implemented locales for completeness, pluralization, locale-aware formatting, fallback behavior, and language-switch continuity. Include text expansion and RTL layout when relevant. Indexable localized content may require hreflang; internal translated screens do not automatically require SEO work. Hardcoded language-neutral identifiers are not localization defects.

## Privacy and sensitive data

Activate whenever personal data is processed, even in internal products. Map collection, purpose, recipients/processors, storage, retention/deletion, and transfers using observed evidence. Include logs, analytics, error monitoring, uploads, and AI providers.

Do not establish jurisdiction from language or TLD. Record confirmed operator location, target markets, business model, user groups, and relevant thresholds when available. Treat unconfirmed applicability as a question requiring evidence. Check current authoritative sources for legal claims and record source/date; do not use this reference as a legal rulebook or certify compliance.

Assess whether notices and implemented choices match actual data flows. Where consent is required, inspect behavior before consent, after rejection, and after withdrawal. Do not generate binding legal text or invent business facts. Distinguish a technical observation (a request transmitted an identifier) from a legal conclusion (that transfer is unlawful).

Once operator location and target markets are confirmed, use these as prompts for what to verify against current authoritative sources, not as conclusions. Establish applicability, exceptions, and thresholds before reporting a legal gap:

- EU/EEA: privacy notice, legal basis per data flow, consent before non-essential cookies or tracking, processor agreements, data export and deletion, third-party resources loaded from external servers (fonts, maps, videos, analytics), European Accessibility Act for consumer-facing services.
- Germany/Austria: a legal notice (Impressum) reachable from every page, national telecom/cookie rules on top of GDPR.
- United States: privacy policy, state privacy laws where thresholds are met, COPPA where children are an audience.
- Commerce anywhere: terms, withdrawal/refund information, and price display rules of the target market.

For sensitive data, deepen minimization, access control, auditability, retention, encryption, and provider review. Severity still depends on impact and evidence; not every finding is automatically High.

## Analytics

Activate only when tracking exists or is requested. Check event meaning, duplication, data minimization, consent behavior where applicable, and separation of test/production traffic. Absence of analytics is not automatically a defect.
