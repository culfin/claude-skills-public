# E2E / Integration Tests — Detail

No flow touched → the `E2E Tests` item is left out of the checklist, not ticked.

**What this step must prove:** the user flows this phase touched work end to end on the candidate —
through the real UI or the real public interface, with the assertions that matter to a user. The
tool is secondary; what counts is which flows and assertions actually ran.

**Step 1: Name the flows and assertions.** From the spec (or the acceptance criteria in STATE.md), list the
user flows the phase changed or added and, per flow, the assertions that prove it works (e.g.
"valid checkout completes", "invalid field shows its message", "form submits with the keyboard").
This list is what the step is measured against.

**Step 2: Pick the level that can actually exercise them.**

| Technology | Proves UI flows | Does **not** prove UI flows on its own |
|---|---|---|
| Web app (Next.js, React, Vue, Svelte, …) | Playwright (preferred), Cypress, Vitest Browser Mode | unit tests, component tests without a browser |
| REST/GraphQL API (no UI) | integration tests against a running server (`supertest`, HTTP calls) | unit tests of handlers |
| CLI tool | tests that run the built binary with real arguments | unit tests of internal functions |
| Native app (iOS/macOS) | XCUITest (UI tests in `xcodebuild test`) | XCTest/Swift Testing unit tests |
| Native app (Windows/WinUI) | UI automation (WinAppDriver, FlaUI, Appium) | xUnit unit tests |
| Library/package | the public API tested as a consumer would call it | — |
| Hybrid (web app + API) | browser tests for UI parts, integration tests for API parts | — |

A **substitute** for the preferred tool counts only if it runs the same flows with the same
assertions against the same candidate (e.g. Cypress instead of Playwright, a Playwright CLI run instead
of the Playwright MCP). Record which substitute ran and which flows/assertions it covered. A unit
suite, a build or a screenshot is never a substitute for a UI flow.

**Step 3: Find the project's infrastructure.**
- `playwright.config.*` → Playwright; `cypress.config.*` → Cypress; `vitest.config.*` with browser
  mode → Vitest Browser
- `package.json` scripts `test:e2e`, `test:integration`, `e2e` → use those
- `.xcodeproj` with a UI test target → XCUITest; `*.csproj` with a UI automation project → that

**Step 4: Run.** Matching specs for the changed area first, then the full relevant suite to catch
regressions. For every flow from step 1: which test covered it, and its result.

**Step 5: Missing coverage.** A changed flow without a test gets one now — written from the
requirement, seen failing once against a deliberately broken implementation, then green (as the
Spec checker requires).

**No infrastructure for the needed level** (no browser runner, no UI test target): that is not a
pass and not a skip. Either set up the smallest runner that can cover the flows (with the user's
agreement if it adds dependencies), or the E2E checkbox stays open and the phase stays `[!]` —
record in STATE.md which flows are unverified and why.

**Failures:**
- Caused by the phase → fix, rerun.
- Believed to be pre-existing → only with the proof from `gate.md` ("The error was already there
  before"): the same failure, same cause, reproduced on the unchanged base; the change causes and
  hides nothing; the tests covering this phase's flows still run and pass. Then the phase completes
  *with a known pre-existing failure*, named as such — never "all green". Flaky without proof is not
  pre-existing. None of this excuses a failing required CI run.
- After fixes: rerun the failing tests on the new candidate.
- A failed Playwright run (local or CI artifact) that left a trace `.zip` → `stack/INDEX.md`, row
  `playwright`, before guessing from the error text; the skill missing → say so and read the report instead.
