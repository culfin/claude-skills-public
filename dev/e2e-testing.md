# E2E / Integration Tests — Detail

**Step 1: Determine testability.** Not every project type benefits from browser-based E2E tests. Decide based on the technology:

| Technology | Playwright suitable? | Alternative |
|-------------|---------------------|-------------|
| Web app (Next.js, React, Vue, Svelte, etc.) | Yes — preferred | Cypress, Vitest Browser Mode |
| REST/GraphQL API (without UI) | No | Vitest/Jest integration tests, `supertest`, `httpie` |
| CLI tool | No | Shell-based tests, Vitest |
| Native app (iOS/macOS) | No | XCTest, Swift Testing (`xcodebuild test` / `swift test`) |
| Native app (Windows/WinUI) | No | xUnit (`dotnet test`) |
| Library/package | No | The framework's unit tests |
| Hybrid (web app + API) | Yes for UI parts | API parts: integration tests |

**Step 2: Detect existing test infrastructure.** Check for config files in the project root:
- `playwright.config.ts` / `playwright.config.js` → Playwright
- `cypress.config.ts` / `cypress.json` → Cypress
- `vitest.config.ts` with browser mode → Vitest Browser
- `package.json` scripts containing `test:e2e`, `test:integration`, `e2e` → use those
- `.xcodeproj` / `Package.swift` → XCTest / Swift Testing
- `*.csproj` with xUnit → xUnit

**Step 3: Run tests.**

If Playwright is suitable and configured:
1. Look for existing spec files matching the changed feature area (e.g., specs in `e2e/` whose names relate to the phase).
2. Run matching specs first. If they pass, run the full relevant project/suite to catch regressions.
3. Use the `/playwright-cli` skill for execution if available.

If Playwright is NOT suitable or not configured:
1. Run the project's existing test command (`test:e2e`, `test:integration`, or `test`).
2. If no test infrastructure exists at all: **warn and skip**, but log as Blocker in STATE.md ("No test framework configured — phase N had no automated test").

**Step 4: Handle missing specs.**
If the phase introduced new functionality but no matching test spec exists: flag it and **write a basic smoke test** before running — and see it fail once against a deliberately broken implementation, as the spec checker (5c-v) requires. This ensures new features always get at least one automated test.

**Failure handling:**
- Test fails due to phase changes → fix before proceeding.
- Test fails due to pre-existing/flaky issue → document in STATE.md under Blockers & Risks, proceed.
- After fixes: re-run failing tests to confirm green.

Only proceed to post-skills when tests are green (or failures are documented as pre-existing).
