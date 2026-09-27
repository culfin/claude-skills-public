# Workflow patterns — merge order, promote, security alerts

Apply to every ecosystem. Numbers are stable across files — other references cite them as "pattern N".

5. **Dev-deps have 100% pass rate** — Across 8+ merges, zero dev-dependency updates broke anything. Batch them (Wave 1) and validate once at the end.

6. **Runtime deps need individual validation** — Merge one at a time with `typecheck + lint + test` after each. This catches the exact culprit on failure.

9. **Impact analysis is the core value** — NEVER skip it. The user MUST see changelog summaries, code suggestions, and breaking changes for every PR before it's merged. This is what makes /deps better than manual Dependabot merging.

10. **Auto-promote after merge** — After all merges + CI green + code suggestions handled, automatically create the promote PR. Don't wait for a separate `/deps promote` command. The only manual step is the PR merge on GitHub.

11. **Promote PR: always "Create a merge commit"** — NEVER use "Rebase and merge" for promote PRs. Rebase creates new commit SHAs on prod, causing main and prod to diverge. Merge commit keeps branches in sync.

13. **Major updates are NOT skipped** — Wave 3 handles all major version bumps. Deep changelog analysis, usage scan, risk assessment (low/medium/high), and automatic migration for medium-risk updates. Only truly high-risk updates (unclear migration, infrastructure mismatch) are skipped with detailed explanation. See merge.md "Wave 3: Major Updates".

14. **Sync back after a promote merge — in the same session** — After the promote PR is merged on GitHub, prod has a merge commit that main doesn't. Merge prod back into main in the same session (promote.md Step 5) so `main..prod` stays at zero. If it is skipped, nothing detects it later — and nothing has to: a promote merge node is merge-only divergence, not drift (Safety Rule 12).

15. **NEVER resolve promote PR conflicts on prod** — If a promote PR has conflicts, close the PR, merge prod into main (resolve conflicts there), then recreate the PR. Pushing directly to prod violates Safety Rule #2 and causes divergence. See promote.md "Handle PR conflicts".

16. **Security alerts are a SEPARATE signal from update PRs** — `gh pr list --author app/dependabot` can be empty while `gh api .../dependabot/alerts` has dozens of open vulns. Transitive packages (in the lockfile, not `package.json`) get an alert but NO version-bump PR — so a PR-only skill silently misses them. Always scan `dependabot/alerts` in status, `check`, and `audit`. (Observed: 0 PRs, 24 alerts.) See `references/security-alerts.md`.

17. **Severity label ≠ real exposure — re-rank by importer** — GitHub rates the CVE in isolation; `pnpm why <pkg>` reveals who pulls it. A "high" in a test-only chain (undici→jsdom→vitest) or a Windows-only advisory on a Linux deploy is near-zero practical risk; a "moderate" on a prod runtime path (dompurify→jspdf in a server PDF generator) is the one that matters. Report the importer-reranked view, not GitHub's raw counts.

21. **Supersede instead of another rebase round** — When remaining PRs keep flipping to CONFLICTING after each merge AND the beyond-Dependabot pass (`$PM update`/`cargo update`) reaches the SAME dep at an equal-or-newer in-range version, skip further rebase+CI rounds: run the beyond-pass, validate, push, then close those PRs with a comment naming the superseding commit ("Superseded: vite 8.2.1 via <sha>"). Condition to check first: PR target version ≤ what the update command reaches in-range. Observed: 2 PRs × ~8 min rebase+CI saved, and the result was NEWER than the stale PRs (vite 8.2.1 > 8.2.0, thiserror 2.0.20 > 2.0.19). pnpm v10 `pnpm update` also bumps the package.json ranges, so manifest + lockfile both end up current — the close-as-superseded is honest. This beats Pattern 2's "wait for next session" whenever the beyond-pass covers the dep anyway.

25. **`prodBranch: null` = single-trunk repo — and jq's `//` eats the null** — Projects whose dev branch is the ONLY branch set `"prodBranch": null` in `.deps/config.json`. Then: skip promote entirely (no promote PR, no main↔prod diff in status; the merge report is the final artifact). ⚠ `jq -r '.prodBranch // "prod"'` maps an explicit `null` to `"prod"` — the alternative operator treats null as absent — so auto-promote would open a PR against a branch that doesn't exist. Guard first: `jq -e '.prodBranch != null'` before any promote step.
