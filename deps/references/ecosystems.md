# Ecosystem Detection & Tooling Reference

## Project Type Detection

Detect by checking for indicator files in project root (check all — monorepos have multiple):

| Indicator File | Ecosystem | Package Manager |
|----------------|-----------|----------------|
| `package.json` | Node | Detect: `pnpm-lock.yaml` → pnpm, `bun.lockb`/`bun.lock` → bun, `yarn.lock` → yarn, `package-lock.json` → npm |
| `Cargo.toml` | Rust | cargo |
| `pubspec.yaml` | Flutter/Dart | pub (`flutter pub`) |
| `Package.swift` | Swift | SPM (`swift package`) |
| `build.gradle` / `build.gradle.kts` | Android/Kotlin | Gradle (`./gradlew`) |

If none found → warn: "Unknown project type. /deps setup required for test framework installation."

**Hybrid projects (Tauri, Electron+Rust, wasm):** `package.json` AND `Cargo.toml` both present
→ run BOTH ecosystems through every step (outdated scan, lockfile fix, validation). An
npm-only pass silently covers half the project — Dependabot opens `cargo`-ecosystem PRs too.

**Rust workspaces:** dependencies are declared per-member (`members = [...]` in the root
`Cargo.toml`), but there is ONE root `Cargo.lock`. A Dependabot bump PR may touch several
member `Cargo.toml`s at once. Scan/validate with `--workspace`, not a single member's
`--manifest-path` (which silently skips the other members).

## Lockfile Resolution (after each merge)

| Ecosystem | Command | Commit if changed |
|-----------|---------|-------------------|
| Node (pnpm) | `pnpm install` | `pnpm-lock.yaml` |
| Node (npm) | `npm install` | `package-lock.json` |
| Node (yarn) | `yarn install` | `yarn.lock` |
| Node (bun) | `bun install` | `bun.lockb` |
| Rust | `cargo check --workspace` (re-resolves lock) | `Cargo.lock` |
| Flutter | `flutter pub get` | `pubspec.lock` |
| Swift | `swift package resolve` | `Package.resolved` |
| Android | `./gradlew dependencies` | `gradle.lock` (if exists) |

## Test Frameworks

### Detection

| Ecosystem | Check for | Framework |
|-----------|-----------|-----------|
| Node | `playwright.config.*` | Playwright |
| Node | `vitest.config.*` or `vitest` in devDeps | Vitest |
| Node | `jest.config.*` or `jest` in devDeps | Jest |
| Rust | built-in (`#[test]`, `tests/`) | cargo test |
| Flutter | `flutter_test` in dev_dependencies | flutter_test |
| Swift | `Tests/` directory or test targets in Package.swift | XCTest / swift-testing |
| Android | `src/test/` or `src/androidTest/` | JUnit / Espresso |

### Recommended Installs (when missing)

| Ecosystem | Install Command | Config |
|-----------|----------------|--------|
| Node | `$PM add -D @playwright/test && npx playwright install` | Creates `playwright.config.ts` |
| Flutter | Already included via `flutter_test` in SDK | N/A |
| Swift | Add test target to `Package.swift` | N/A |
| Android | Already included via Gradle test plugin | N/A |

### Local Validation Commands

| Ecosystem | Type Check | Lint | Unit Tests | E2E/Integration |
|-----------|-----------|------|------------|-----------------|
| Node | `$PM tsc --noEmit` or `$PM typecheck` | `$PM lint` | `$PM test` or `$PM vitest run` | `$PM playwright test` |
| Rust | `cargo check --workspace` | `cargo clippy --workspace` | `cargo test --workspace` | project-specific (check CLAUDE.md for required `--features`) |
| Flutter | `dart analyze` | `dart analyze` | `flutter test` | `flutter test integration_test/` |
| Swift | `swift build` | `swiftlint` (if installed) | `swift test` | N/A |
| Android | `./gradlew compileDebugKotlin` | `./gradlew lint` | `./gradlew test` | `./gradlew connectedAndroidTest` |

## Dependabot Ecosystem Mapping

| Dependabot Ecosystem | Impact Analysis Source | Files to Check |
|---------------------|----------------------|----------------|
| npm | npm registry changelog, GitHub releases | `package.json`, source files with imports |
| cargo | GitHub releases; many crates use `CHANGELOG.md`/`RELEASE-NOTES.md` in-repo instead of GitHub Releases (fetch via `gh api repos/{owner}/{repo}/contents/CHANGELOG.md`) | workspace-member `Cargo.toml`s, `use`-sites (`grep -rn '<crate>::' */src`) |
| github-actions | Action repo releases | `.github/workflows/*.yml` |
| docker | Docker Hub / image release notes | `Dockerfile`, `docker-compose*.yml` |
