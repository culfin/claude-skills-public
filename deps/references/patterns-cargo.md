# Rust / Cargo patterns

Read when the project has a `Cargo.toml` (including Tauri and other hybrids). The lockfile-merge
behaviour of cargo is pattern 22 in `patterns-ci.md`; general cargo commands are in `ecosystems.md`.

12 (Rust part). **⚠ Rust / hybrid projects (Tauri, Electron+Rust): `$PM outdated` covers only the npm half.** The cargo side needs its own scan — `cargo outdated --root-deps-only` (install once: `brew install cargo-outdated` or `cargo install cargo-outdated`; `cargo update --dry-run` is NOT a substitute, it only shows in-range updates). Observed in a Tauri workspace: `zip 4.6.1` vs `Latest 8.6.0` — a four-major gap Dependabot will never PR — plus ~10 minor/patch crates in batch lag and an open cargo PR that was already stale (bumped to 2.0.19 while `Latest` was 2.0.20). None of this is visible from the npm scan or the PR queue. See ecosystems.md for hybrid-project and workspace rules.
