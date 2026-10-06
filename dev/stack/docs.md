# Live docs per technology

Read only the row you need. The order is fixed — take the first source that exists and stop:

1. **Bundled** — docs or skills shipped inside the project's own packages (version-matched).
2. **Official access** — the vendor's docs MCP server, plugin or CLI, if the host has it.
3. **`llms.txt`** — fetch the index, then single pages; never `llms-full.txt`.
4. **Context7** — with the version the project resolves (lockfile), not "latest".

A framework or library decision quotes the doc it relies on (path or URL + line) or is marked `UNVERIFIED`.
A subagent does the reading and returns findings or a ≤ 40-line digest. Nothing reachable →
say so (`skipped: <reason>` on a gate item); never answer from memory as if it were the docs.
"—" = that step does not exist for the technology. Context7 ids are given where one is known to
resolve; otherwise resolve the id by name.

| Technology | 1 Bundled | 2 Official access | 3 `llms.txt` / official site | 4 Context7 |
|---|---|---|---|---|
| Next.js | `node_modules/next/dist/docs/` | — | https://nextjs.org/docs/llms.txt | by name |
| React | — | — | https://react.dev/llms.txt (pages as `.md`) | by name |
| FullCalendar | — | — | https://fullcalendar.io/docs/llms.txt (v7; pages as `.md`; read `upgrading-from-v6.md` first — most examples online are v6) | by name |
| Tailwind CSS | — | — | — | `/tailwindlabs/tailwindcss.com` |
| shadcn/ui | — | `npx shadcn@latest docs <component>`, skill `shadcn` | https://ui.shadcn.com/llms.txt | by name |
| Base UI | — | — | https://base-ui.com/llms.txt | by name |
| Radix | — | — | — | `/websites/radix-ui_primitives` |
| PostgreSQL | — | pg plugin `search_docs` | https://www.postgresql.org/docs/current/ | `/websites/node-postgres`, `/salsita/node-pg-migrate` (drivers, migrations) |
| better-auth | — | — | https://better-auth.com/llms.txt | by name |
| Zod | — | — | https://zod.dev/llms.txt | by name |
| Vitest | — | — | https://vitest.dev/llms.txt | by name |
| Playwright | `node_modules/playwright-core/lib/tools/skills/` | — | — | `/microsoft/playwright` |
| Docker | — | — | https://docs.docker.com/llms.txt | by name |
| GitHub Actions | — | — | https://docs.github.com/llms.txt | by name |
| Tauri | — | — | https://tauri.app/llms.txt | by name |
| Rust | `cargo doc` for the resolved crates | — | docs.rs page of the crate version | by name |
| Svelte / SvelteKit | — | Svelte MCP (official plugin) | https://svelte.dev/llms.txt | by name |
| next-intl | — | — | — | `/amannn/next-intl` |
| TanStack | `node_modules/@tanstack/*/skills/` (where shipped) | — | https://tanstack.com/llms.txt | by name |
| Biome | `biome explain <rule>` | — | — | `/biomejs/website` |
| TypeScript | — | — | https://www.typescriptlang.org/docs/ | by name |
| Stripe | — | — | https://docs.stripe.com/llms.txt (pages as `.md`) | by name |
| Sentry | — | Sentry MCP | https://docs.sentry.io/llms.txt | by name |
| AI SDK | `node_modules/ai/docs/` | — | https://ai-sdk.dev/llms.txt (very large: single pages only) | by name |
| Astro | — | Astro docs MCP (https://mcp.docs.astro.build/mcp) | — | by name |
| Fastify | `node_modules/fastify/docs/` | — | https://fastify.dev/llms.txt | by name |
| Kotlin / KMP / Ktor | — | — | https://kotlinlang.org/llms.txt, https://ktor.io/docs/llms.txt | by name |
| Swift / SwiftUI | — | — | — | by name |
| WordPress | — | — | https://wordpress.org/llms.txt, https://developer.wordpress.org/ | by name |
| pnpm | `pnpm help <command>` | — | — | `/pnpm/pnpm.io` |

Official access is used for reading docs only: no vendor MCP server or plugin is installed for
this, and a hosted product a doc page recommends is not a recommendation of `/dev`.
