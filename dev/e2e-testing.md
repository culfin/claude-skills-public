# E2E / Integration Tests — Detail

**Step 1: Determine testability.** Not every project type benefits from browser-based E2E tests. Decide based on the technology:

| Technologie | Playwright geeignet? | Alternative |
|-------------|---------------------|-------------|
| Web-App (Next.js, React, Vue, Svelte, etc.) | Ja — bevorzugt | Cypress, Vitest Browser Mode |
| REST/GraphQL API (ohne UI) | Nein | Vitest/Jest Integration Tests, `supertest`, `httpie` |
| CLI Tool | Nein | Shell-basierte Tests, Vitest |
| Native App (iOS/macOS) | Nein | XCTest, Swift Testing (`/run-tests`) |
| Native App (Windows/WinUI) | Nein | xUnit (`/run-tests`) |
| Library/Package | Nein | Unit Tests des Frameworks |
| Hybrid (Web-App + API) | Ja für UI-Teile | API-Teile: Integration Tests |

**Step 2: Detect existing test infrastructure.** Check for config files in the project root:
- `playwright.config.ts` / `playwright.config.js` → Playwright
- `cypress.config.ts` / `cypress.json` → Cypress
- `vitest.config.ts` mit browser mode → Vitest Browser
- `package.json` scripts containing `test:e2e`, `test:integration`, `e2e` → use those
- `.xcodeproj` / `Package.swift` → XCTest / Swift Testing
- `*.csproj` mit xUnit → xUnit

**Step 3: Run tests.**

If Playwright is suitable and configured:
1. Look for existing spec files matching the changed feature area (e.g., specs in `e2e/` whose names relate to the phase).
2. Run matching specs first. If they pass, run the full relevant project/suite to catch regressions.
3. Use the `/playwright-cli` skill for execution if available.

If Playwright is NOT suitable or not configured:
1. Run the project's existing test command (`test:e2e`, `test:integration`, or `test`).
2. If no test infrastructure exists at all: **warn and skip**, but log as Blocker in STATE.md ("Kein Test-Framework konfiguriert — Phase N hatte keinen automatisierten Test").

**Step 4: Handle missing specs.**
If the phase introduced new functionality but no matching test spec exists: flag it and **generate a basic smoke test** using `/generate-tests` before running. This ensures new features always get at least one automated test.

**Failure handling:**
- Test fails due to phase changes → fix before proceeding.
- Test fails due to pre-existing/flaky issue → document in STATE.md under Blockers & Risks, proceed.
- After fixes: re-run failing tests to confirm green.

Only proceed to post-skills when tests are green (or failures are documented as pre-existing).
