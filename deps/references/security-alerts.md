# /deps audit — Dependabot Security Alerts

Covers the blind spot of every PR-based command in this skill: **security advisories
do NOT always come with an update PR.** `gh pr list --author app/dependabot` can return
`[]` while the repo has dozens of open vulnerabilities — because the vulnerable package
is a **transitive** dependency (in the lockfile, not in `package.json`), so Dependabot
cannot open a version-bump PR for it. The signal lives in a different API.

> Real case that motivated this: 0 open Dependabot PRs, **24 open security alerts**
> (5 high / 13 moderate / 6 low) across 6 transitive packages. `/deps check` reported
> "nothing to do" while the vulns sat there. Alerts are a separate signal — always scan them.

`/deps audit` = read-and-fix. `/deps check` and bare `/deps` (status) scan and **report**
the same alerts read-only. Wire this into both (see SKILL.md).

## 1. Fetch and group alerts

```bash
OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

# Count by severity
gh api repos/$OWNER_REPO/dependabot/alerts --paginate -X GET -f state=open \
  | jq -r 'group_by(.security_advisory.severity)[] | "\(.[0].security_advisory.severity|ascii_upcase): \(length)"'
```

Full detail per alert — write the jq to a file (the `→` / shell-quoting bites inline):

```bash
cat > /tmp/alerts.jq <<'JQ'
sort_by(.security_advisory.severity)[]
| "[\(.security_advisory.severity|ascii_upcase)] \(.dependency.package.name) (\(.dependency.scope // "?"))"
  + "\n   vuln: \(.security_advisory.summary)"
  + "\n   range: \(.security_vulnerability.vulnerable_version_range)  patched: \(.security_vulnerability.first_patched_version.identifier // "NO FIX")"
  + "\n   manifest: \(.dependency.manifest_path)\n"
JQ
gh api repos/$OWNER_REPO/dependabot/alerts --paginate -X GET -f state=open | jq -r -f /tmp/alerts.jq
```

Key fields: `dependency.scope` (`runtime` vs `development`), `dependency.manifest_path`
(`pnpm-lock.yaml` ⇒ transitive; `package.json` ⇒ direct, has a PR path), and
`first_patched_version` (`null` may mean "go above the vulnerable range" — verify, don't
assume unfixable).

### Compare the alert range against your EXISTING override floor, not just the installed version

**An override that was correct when written can be overtaken by a later advisory** whose
`vulnerable_version_range` extends *up to and including* the floor you pinned. The override
then actively holds the package ON the vulnerable version, and the alert can never resolve
itself — while looking like "the override isn't working".

Real case: the block carried `dompurify@<3.4.12: "^3.4.12"`, written against an earlier
advisory. The new alert's range was `<= 3.4.12`, patched in 3.4.13 — so the very pin meant to
protect the package was keeping it vulnerable. Fix was mechanical once seen: raise the
selector and the value together (`dompurify@<3.4.13: "^3.4.13"`).

So for every alert on a package you already override, diff the two:

```bash
grep -E "^\s+<pkg>@" pnpm-workspace.yaml     # the floor you pinned (selector AND value)
# vs the alert's .security_vulnerability.vulnerable_version_range from the scan above
```

If the alert range covers your floor, the floor is the bug. Raise both halves of the entry —
bumping only the value while leaving a `<oldfloor` selector in place makes the rule stop
matching, and the package silently stays put. Note this is invisible to `pnpm outdated`: a
transitive pinned exactly at its override floor is not "outdated", it is doing what you told it.

## 2. Triage — severity label ≠ real exposure

GitHub's severity reflects the CVE in isolation. **Who pulls the package in** decides the
actual production risk. Map every alert to its importer before reporting:

```bash
for p in <pkg1> <pkg2> …; do echo "════ $p ════"; pnpm why $p 2>&1 | head -25; done
# npm:  npm ls <pkg> --all   |  yarn: yarn why <pkg>
```

Re-rank by importer, not just by GitHub severity:

- **Runtime, reachable in prod** (e.g. `dompurify` via `jspdf` in a PDF generator that runs
  on the server) → the ones that actually matter, even at "moderate/low".
- **Test/dev-only** (e.g. `undici` via `jsdom`→`vitest`; `vite`/`esbuild` via the test
  runner) → low practical risk; several "high" alerts often land here.
- **Platform-gated** — many advisories are Windows-only (`server.fs.deny` bypass, NTLM via
  UNC, dev-server file read). If the project deploys Linux/macOS, note that explicitly.

Report this re-ranking. "5 high, but none touch production runtime; the one to care about
is a moderate dompurify via jspdf" is far more useful than echoing GitHub's counts.

## 2b. Before overriding: can the importer simply be DELETED?

Pattern 20 (`patterns-js.md`) asks whether a newer importer already widens its range. Ask the cheaper question
first: **is the importer used at all?**

```bash
pnpm exec knip --dependencies          # or: npx knip / npx depcheck
```

Cross-reference its "Unused dependencies / Unused devDependencies" list against the
importers you mapped in §2. A hit means the alert can be removed at the root instead of
frozen at a patched floor forever.

Real case: 3 of 4 open alerts were `hono`, reached only via
`shadcn → @modelcontextprotocol/sdk → @hono/node-server`. `shadcn` sat in
`devDependencies` while the CLI is normally invoked through `pnpm dlx` — knip flagged it as
unused, and dropping it retires all three advisories along with the dependency.

**Two guard rails:**

- **knip names its own blind spots.** Its "Configuration hints" section says what it does not
  follow — `.css` is the common one, so packages consumed only from a stylesheet
  (`tailwindcss`, `tw-animate-css`) appear as unused and are false positives. Confirm every
  candidate with a grep that includes stylesheets and config files:
  `grep -rl "<pkg>" src app --include="*.css" . | grep -v node_modules`
- **Never fold a dependency removal into a bump commit.** It is a separate, reversible change
  with a different blast radius. Report it; let the user decide.

## 3. Fix — transitive vulns are fixed by an override, not a PR

A transitive package has no `package.json` entry to bump, so there is no Dependabot PR to
merge. Force the patched version with the package manager's override mechanism:

| Manager | Mechanism | Where |
|---------|-----------|-------|
| pnpm    | `overrides:` | **`pnpm-workspace.yaml`** (pnpm v9+/v11) — NOT `package.json`, see §4 |
| npm     | `overrides` | `package.json` |
| yarn    | `resolutions` | `package.json` |

First try a plain `pnpm update <pkg> -r` — if the parent's semver range already permits the
patched version, the update reaches it and no override is needed. Only the packages the
update can't reach (parent caps below the patch) need an override entry. But for a security
fix, **pin a floor anyway** so a later lockfile reshuffle can't silently regress below the
patched version — that is the whole point of the override block.

pnpm keyed-range form (matches house style, surgical — only rewrites sub-floor versions):

```yaml
overrides:
  undici@<7.28.0: "^7.28.0"     # selector: only fires when natural resolution < floor
  dompurify@<3.4.11: "^3.4.11"
```

## 4. pnpm gotcha — overrides live in `pnpm-workspace.yaml`, not `package.json`

pnpm v9+ reads `overrides` from **`pnpm-workspace.yaml`**. A `pnpm.overrides` block in
`package.json` is **silently ignored** (it may still exist as dead config — leave it, don't
"fix" it; that's out of scope). Confirm where the *active* overrides are:

```bash
grep -A20 "^overrides:" pnpm-workspace.yaml   # active block for pnpm v9+
grep -A3  '"overrides"' package.json          # if present here too, it's dead for pnpm v9+
# Truth check: the lockfile's own overrides block is what's actually applied:
grep -A15 "^overrides:" pnpm-lock.yaml
```

If you edit the wrong file, the version won't move and `pnpm why` keeps showing the old one.

## 5. Caret-cap the replacement value — never `>=` open-ended

An override value of `">=7.28.0"` resolves to the **highest** matching version — which can
be a **major bump**. Real example: `undici@<7.28.0: ">=7.28.0"` pulled **undici 8.5.0**,
breaking `jsdom`'s declared `undici@^7.25.0`. Always cap to the current major with a caret:

```yaml
undici@<7.28.0: "^7.28.0"     # ✅ stays in 7.x  (NOT ">=7.28.0" → would grab 8.x)
js-yaml@<4.2.0: "^4.2.0"      # ✅ js-yaml 5.0.0 exists; ^ caps it out
```

Before writing each value, check whether a higher major exists (`npm view <pkg> version`)
and whether the importer constrains the major (`npm view <importer> dependencies.<pkg>`).

## 6. pnpm won't re-resolve already-locked transitives on a plain install

Adding/changing an override and running `pnpm install` (even `--force`) often reports
"Already up to date" in ~100ms and leaves the old pinned version in place — pnpm writes the
new `overrides:` block into the lockfile but does **not** recompute the already-locked
transitive. Force a real resolver run:

```bash
rm -f pnpm-lock.yaml
rm -rf node_modules/.pnpm/<pkg>@*   # drop the stale virtual-store entries for the pinned pkgs
pnpm install                        # a genuine resolve takes seconds (global store), not 100ms
```

A sub-second "Already up to date" = it did NOT re-resolve. A multi-second run with
`resolved … added …` = it did. Verify with `pnpm why <pkg>`.

## 7. Verify

```bash
for p in <pkgs>; do printf "%-12s " "$p:"; pnpm why $p 2>/dev/null | grep -oE "$p@[0-9.]+" | sort -u | tr '\n' ' '; echo; done
```

Each must be ≥ its `first_patched_version` AND within the intended major. Then run the full
local validation (typecheck + lint + unit tests + build — script names from `package.json`,
see merge.md). The dependency bumps often touch the test stack itself (vite/vitest/jsdom),
so a green unit-test run is the real proof.

Commit only the override file + lockfile (e.g. `pnpm-workspace.yaml` + `pnpm-lock.yaml`) —
scope must be exactly those. Document each pin with a one-line comment: package, patched
version, who pins the vulnerable one, and the CVE class.

## Read-only mode (`/deps check` and status)

For `/deps check` and bare `/deps`: do steps 1–2 only (fetch, group, triage-by-importer)
and report. Do NOT edit overrides, install, or commit. Surface the count and the
importer-reranked summary so the user sees vulnerabilities that have no PR.
