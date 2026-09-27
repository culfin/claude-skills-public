# Web delivery checks

## Deployment and environments

- Discover actual hosts and environments; verify canonical host and HTTPS behavior where access exists.
- Check public URLs, callbacks, email links, assets, CORS configuration, and metadata for unintended development/preview hosts.
- Verify meaningful separation of production and test services, credentials, datasets, and configuration.
- Missing required configuration produces an actionable startup/build error without exposing values.
- Preview access and indexability match intent. A preview need not redirect to production; use access control for private previews and suitable indexing controls for public ones.

## Public discovery and sharing — conditional

For indexable pages, check useful titles, descriptions, canonical URLs, crawlability, status codes, redirects, and sitemap coverage. Treat description length as editorial guidance rather than a strict validity rule. Private application screens do not need public marketing metadata.

For shareable pages, verify relevant Open Graph/card metadata and accessible absolute image URLs. A shared branded image may be sufficient; dynamic images are not universally required. Test rendering/cropping when tools permit.

- `robots.txt` controls crawling, not access security or reliable deindexing.
- A crawler must be able to retrieve a page to observe its `noindex` directive. Do not combine crawl blocking with an assumption that page-level noindex will be read.
- Protect private resources through access control, independently of indexing policy.
- Sitemaps contain intended public canonical URLs, not authenticated or noncanonical pages.
- Missing routes return an appropriate status where the delivery architecture supports it; report SPA hosting limitations accurately.
- Redirect type and caching should fit the move and method semantics; do not blindly apply one redirect status everywhere.
- Structured data must describe real visible content and fit a supported use case. Do not promise rich results.
- Check meaningful heading structure and semantic HTML; do not treat an arbitrary heading count as proof of SEO failure.

References when needed:
- https://developers.google.com/search/docs/crawling-indexing/block-indexing
- https://developers.google.com/search/docs/crawling-indexing/robots/intro

## Icons and PWA — conditional

Check a recognizable working favicon for browser-facing products. Add platform icon variants according to actual support needs. A manifest, service worker, maskable icons, and installability checks apply to intended PWAs, not every website.

For PWAs, inspect scope/start URL, update behavior, stale caches, offline behavior, and whether sensitive or personalized responses can leak through caching.

## Performance

Measure relevant pages and interactions using repeatable conditions: revision, route, data, device/viewport, network/CPU settings, cache state, and tool version where available. Label individual results as measurements, not general guarantees.

- Separate field data from laboratory measurements. Ordinary Lighthouse navigation runs do not measure INP; do not substitute a lab proxy and label it verified INP.
- Evaluate large client bundles, unnecessary third parties, rendering bottlenecks, over-fetching, N+1 patterns, and hot-path work based on evidence.
- Inspect image sizing, aspect ratios, loading priority, font behavior, layout shifts, and theme flashes.
- Caching, compression, static delivery, and lazy loading must preserve freshness, privacy, and critical content loading. Do not cache authenticated responses publicly or lazy-load the primary image indiscriminately.
- Report missing field data and variability. Run additional measurements when noise prevents a meaningful conclusion; do not repeatedly benchmark without a question to resolve.

Reference: https://web.dev/articles/vitals
