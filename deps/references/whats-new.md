# What's new — report for minor and major jumps of listed technologies

Runs in `/deps check` and `/deps merge`, after the impact analysis of the wave, for every update
(Dependabot PR or "beyond Dependabot") that lifts a technology from the table across a **minor or
major** version. Patch jumps: no report. It complements the per-PR impact analysis: that one
decides whether the update is safe to merge, this one tells the user what the skipped range offers.

## Procedure

1. **Match.** Package (or tool) name against the "Package" column; old → new version from the PR
   or the lockfile diff. Several packages of one technology in one run → one report.
2. **Read — one subagent per technology** (cheap tier, read-only; no subagents on the host → one
   after another). It fetches the release notes / upgrade guide below for the **skipped range
   only** (every version after old, up to and including new) and greps the project for the APIs
   those notes name. A page that fails to load → try the next URL of the row.
3. **Report**, ≤ 25 lines per technology, appended to the merge/check report under
   "What's new":
   ```
   ### <Technology> <old> → <new>
   New:            <features worth knowing, one line each>
   Affects us:     <change> — <file:line> (every claim with a location, or "nothing found")
   Deprecated/removed: <API> — <file:line where we still use it, or "not used">
   Source:         <URL(s) actually read>
   ```
4. **Report only.** No automatic rewrites, no codemods, no follow-up commits. Adopting something
   is the user's decision after reading; a deprecated API still in use becomes a code suggestion
   in the report, like any other.
5. **Unreachable** (no network, every URL of the row fails, rate limit) → the section reads
   `What's new: <Technology> — skipped: <reason>`. Never write a summary from memory and never
   leave the section out silently.

## Release notes and upgrade guides

| Technology | Package | Read |
|---|---|---|
| Next.js | `next` | https://nextjs.org/docs/app/guides/upgrading · https://github.com/vercel/next.js/releases |
| React | `react`, `react-dom` | https://react.dev/blog · https://github.com/facebook/react/releases |
| Tailwind CSS | `tailwindcss` | https://tailwindcss.com/docs/upgrade-guide · https://github.com/tailwindlabs/tailwindcss/releases |
| shadcn/ui | `shadcn` | https://ui.shadcn.com/docs/changelog |
| Base UI | `@base-ui/*`, `@base-ui-components/*` | https://base-ui.com/react/overview/releases |
| Radix | `@radix-ui/*`, `radix-ui` | https://www.radix-ui.com/primitives/docs/overview/releases |
| PostgreSQL | server image `postgres`, `node-pg-migrate` | https://www.postgresql.org/docs/release/ · https://github.com/salsita/node-pg-migrate/releases |
| better-auth | `better-auth` | https://www.better-auth.com/changelog · https://github.com/better-auth/better-auth/releases |
| Zod | `zod` | https://zod.dev/v4/changelog · https://github.com/colinhacks/zod/releases |
| Vitest | `vitest` | https://vitest.dev/guide/migration · https://github.com/vitest-dev/vitest/releases |
| Playwright | `@playwright/test`, `playwright` | https://playwright.dev/docs/release-notes |
| Docker | Compose, Engine (CI images, base images) | https://docs.docker.com/compose/releases/release-notes/ · https://docs.docker.com/engine/release-notes/ |
| GitHub Actions | runner features, `actions/*` | https://github.blog/changelog/label/actions/ |
| Tauri | `@tauri-apps/*`, crate `tauri` | https://v2.tauri.app/release/ · https://github.com/tauri-apps/tauri/releases |
| Rust | toolchain (`rust-toolchain`, CI) | https://blog.rust-lang.org/ · https://releases.rs/ |
| Svelte / SvelteKit | `svelte`, `@sveltejs/kit` | https://svelte.dev/docs/svelte/v5-migration-guide · https://github.com/sveltejs/svelte/releases |
| next-intl | `next-intl` | https://next-intl.dev/blog · https://github.com/amannn/next-intl/releases |
| TanStack | `@tanstack/*` | https://github.com/TanStack/table/releases · https://github.com/TanStack/query/releases · https://github.com/TanStack/virtual/releases |
| Biome | `@biomejs/biome` | https://biomejs.dev/internals/changelog/ |
| TypeScript | `typescript` | https://www.typescriptlang.org/docs/handbook/release-notes/overview.html |
| Stripe | `stripe`, `@stripe/*` | https://docs.stripe.com/changelog |
| Sentry | `@sentry/*` | https://github.com/getsentry/sentry-javascript/blob/develop/CHANGELOG.md |
| AI SDK | `ai`, `@ai-sdk/*` | https://ai-sdk.dev/docs/migration-guides · https://github.com/vercel/ai/releases |
| Astro | `astro` | https://docs.astro.build/en/upgrade-astro/ |
| Fastify | `fastify` | https://github.com/fastify/fastify/releases |
| Kotlin / KMP / Ktor | Kotlin plugin, `io.ktor:*` | https://kotlinlang.org/docs/releases.html · https://ktor.io/docs/releases.html |
| Swift / SwiftUI | toolchain, Xcode | https://www.swift.org/blog/ · https://developer.apple.com/documentation/updates/swiftui |
| WordPress | `roots/wordpress`, `johnpbloch/wordpress` (Composer-managed core only) | https://wordpress.org/documentation/wordpress-version/ · https://make.wordpress.org/core/tag/dev-notes/ |
| pnpm | `packageManager` pin | https://github.com/pnpm/pnpm/releases |

A technology not listed gets no "What's new" section — its changelog is already read in the
impact analysis. Hosted products these pages advertise are not recommendations of this skill.
