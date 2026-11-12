"""detect-stack.py detects $TECH_STACKS from section 1 of stack/INDEX.md (the only list) and prints
the matching lines of tech-stack-triggers.md and stack/INDEX.md section 2 for one step and type."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
SCRIPT = DEV / "scripts" / "detect-stack.py"
INDEX = DEV / "stack" / "INDEX.md"


def run(root, *extra):
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *extra],
                         capture_output=True, text=True)
    return out.returncode, out.stdout, out.stderr


class Fixture:
    def __init__(self, test):
        tmp = tempfile.TemporaryDirectory()
        test.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write(self, rel, content=""):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return self

    def mkdir(self, rel):
        (self.root / rel).mkdir(parents=True, exist_ok=True)
        return self

    def package(self, rel="package.json", deps=(), dev=(), **extra):
        data = {"dependencies": {d: "1.0.0" for d in deps}, "devDependencies": {d: "1.0.0" for d in dev}}
        data.update(extra)
        return self.write(rel, json.dumps(data))


def detected(root, *extra):
    rc, out, err = run(root, "--json", *extra)
    assert rc == 0, err
    return json.loads(out)


class DetectionTests(unittest.TestCase):
    def test_nextjs_with_postgres(self):
        f = Fixture(self).package(deps=["next", "react", "pg"]).write("next.config.mjs")
        rc, out, _ = run(f.root)
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines(), ["stacks: nextjs, postgres", "groups: web"])

    def test_rust(self):
        f = Fixture(self).write("Cargo.toml", "[package]\nname = 'x'\n")
        self.assertEqual(detected(f.root), {"stacks": ["rust"], "groups": []})

    def test_ios_counts_as_apple(self):
        f = Fixture(self).mkdir("App.xcodeproj").write("Package.swift")
        self.assertEqual(detected(f.root), {"stacks": ["ios"], "groups": ["Apple"]})

    def test_empty_project(self):
        f = Fixture(self)
        rc, out, _ = run(f.root)
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines(), ["stacks: none", "groups: none"])

    def test_monorepo_workspace_members(self):
        f = (Fixture(self).package(workspaces=["apps/*"]).write("Dockerfile").write(".github/workflows/ci.yml")
             .package("apps/web/package.json", deps=["next"], dev=["tailwindcss"]).write("apps/web/next.config.js")
             .package("packages/ui/package.json", deps=["svelte"]))
        self.assertEqual(detected(f.root)["stacks"], ["nextjs", "docker", "gha", "tailwind"])

    def test_pnpm_workspace_globs(self):
        f = (Fixture(self).write("pnpm-workspace.yaml", "packages:\n  - 'services/*'\n")
             .package("services/api/package.json", deps=["fastify"]))
        self.assertEqual(detected(f.root)["stacks"], ["fastify"])

    def test_content_indicators(self):
        f = (Fixture(self).write(".env", "DATABASE_URL=postgres://x\n").write("app.json", '{"expo": {}}')
             .write("App/App.csproj", "<UseWinUI>true</UseWinUI>"))
        self.assertEqual(detected(f.root)["stacks"], ["postgres", "winui", "expo"])

    def test_content_indicator_without_content_does_not_match(self):
        f = Fixture(self).write(".env", "PORT=3000\n").write("app.json", "{}").write("App/App.csproj", "<Project/>")
        self.assertEqual(detected(f.root)["stacks"], [])

    def test_migrations_directory_anywhere_shallow(self):
        f = Fixture(self).mkdir("src/db/migrations")
        self.assertEqual(detected(f.root)["stacks"], ["postgres"])

    def test_tauri_implies_rust(self):
        f = Fixture(self).mkdir("src-tauri")
        self.assertEqual(detected(f.root)["stacks"], ["rust", "tauri"])

    def test_plain_web_only_without_a_web_stack(self):
        f = Fixture(self).write("index.html").write("vite.config.ts")
        self.assertEqual(detected(f.root), {"stacks": ["web"], "groups": ["web"]})
        f.package(deps=["svelte"])
        self.assertEqual(detected(f.root), {"stacks": ["svelte"], "groups": ["web"]})

    def test_wordpress_plugin_header(self):
        f = Fixture(self).write("my-plugin.php", "<?php\n/*\n * Plugin Name: Demo\n */\n")
        self.assertEqual(detected(f.root)["stacks"], ["wordpress"])

    def test_every_quoted_token_is_a_dependency(self):
        # `"@playwright/test"` or `"playwright"` in dependencies: both names count, not only the last
        f = Fixture(self).package(dev=["@playwright/test"])
        self.assertEqual(detected(f.root)["stacks"], ["playwright"])

    def test_ignored_directories_are_not_scanned(self):
        f = Fixture(self).write("node_modules/x/Cargo.toml").write("node_modules/y/next.config.js")
        self.assertEqual(detected(f.root)["stacks"], [])

    def test_index_is_the_only_list(self):
        index = Fixture(self).write("INDEX.md", INDEX.read_text().replace(
            "| `Cargo.toml` | `rust` |", "| `deno.json` | `deno` | — |\n| `Cargo.toml` | `rust` |"))
        f = Fixture(self).write("deno.json", "{}")
        self.assertEqual(detected(f.root, "--index", str(index.root / "INDEX.md"))["stacks"], ["deno"])

    def test_broken_index_row_exits_2(self):
        for broken in ("| `Cargo.toml` | rust | x |", "| Cargo.toml | `rust` | x |", "| `Cargo.toml` | `rust` |"):
            index = Fixture(self).write("INDEX.md", INDEX.read_text().replace(
                "| `Cargo.toml` | `rust` | `rust-best-practices`, `rust-testing` |", broken))
            rc, out, err = run(Fixture(self).root, "--index", str(index.root / "INDEX.md"))
            self.assertEqual(rc, 2, broken)
            self.assertIn("INDEX.md", err)
            self.assertIn("Cargo.toml", err)
            self.assertEqual(out, "")



TRIGGERS = DEV / "tech-stack-triggers.md"
STACK_COND = re.compile(r"`([a-z0-9-]+)` (?:is )?in `\$TECH_STACKS`")


def source_lines():
    return set(TRIGGERS.read_text().splitlines()) | set(INDEX.read_text().splitlines())


def trigger_output(test, root, step, type_=None):
    args = ["--triggers", "--step", step] + (["--type", type_] if type_ else [])
    rc, out, err = run(root, *args)
    test.assertEqual(rc, 0, err)
    return [l for l in out.splitlines() if l.strip() and not l.startswith("# ")]


def block(start, path=TRIGGERS):
    """The lines of the paragraph in `path` that starts with `start`."""
    lines = path.read_text().splitlines()
    i = next(i for i, l in enumerate(lines) if l.startswith(start))
    j = i
    while j < len(lines) and lines[j].strip():
        j += 1
    return lines[i:j]


def line(text, path=TRIGGERS):
    return next(l for l in path.read_text().splitlines() if text in l)


class TriggerTests(unittest.TestCase):
    def nextjs_postgres(self):
        return Fixture(self).package(deps=["next", "pg"]).write("next.config.mjs").root

    def test_backend_brainstorming_gets_exactly_its_lines(self):
        out = trigger_output(self, self.nextjs_postgres(), "4a", "backend")
        expected = (block("**Stack sources") + block("**Next.js — where")
                    + ["**During Brainstorming (step 4a):**",
                       line("If phase `@type:` is `backend` and `postgres`"),
                       line("If phase involves new pages/routes and `nextjs`")]
                    + ["| Trigger | Load | How |", "|---|---|---|",
                       line("| `postgres` 4a/5c:", INDEX), line("| `nextjs` 4a/5c:", INDEX)]
                    + block("**How.**", INDEX) + block("**Limits.**", INDEX))
        self.assertEqual(out, expected)

    def test_every_line_is_verbatim_and_of_a_detected_stack(self):
        stacks = {"rust"}
        root = Fixture(self).write("Cargo.toml").root
        for step in ("4a", "4c", "gate"):
            for type_ in ("ui", "landing", "backend", None):
                out = trigger_output(self, root, step, type_)
                for l in out:
                    self.assertIn(l, source_lines(), l)
                    for s in STACK_COND.findall(l):
                        self.assertIn(s, stacks, f"{step}/{type_}: foreign stack line {l}")
                    self.assertFalse(re.match(r"\| `(?!rust)[a-z0-9-]+` (4a|4c|5c|5g|debug)", l), l)
        gate = trigger_output(self, root, "gate", "backend")
        self.assertIn(line("| `**/*.rs` |"), gate)
        self.assertIn(line("| Rust tests ("), gate)
        self.assertIn(line("| `**/auth*`,"), gate)
        self.assertNotIn(line("If phase `@type:` is `backend`"), gate)

    def test_preamble_before_the_first_section_heading_is_never_printed(self):
        root = Fixture(self).write("Cargo.toml").root
        for step in ("4a", "4c", "gate"):
            self.assertNotIn(block("`5c` in the index files")[0], trigger_output(self, root, step))

    def test_unknown_type_keeps_only_type_independent_lines(self):
        root = Fixture(self).package(deps=["next"]).write("components.json").root
        out = trigger_output(self, root, "4a", "weird")
        self.assertFalse([l for l in out if "`@type:` is" in l], out)
        self.assertIn(line("If phase involves new pages/routes and `nextjs`"), out)
        self.assertEqual(out, trigger_output(self, root, "4a"))

    def test_ui_phase_gets_design_and_motion_rules(self):
        root = Fixture(self).package(deps=["next"]).write("components.json").root
        out = trigger_output(self, root, "4a", "ui")
        for text in ("If phase `@type:` is `ui` and `shadcn`", "If phase `@type:` is `ui` →",
                     "**Motion — which source wins.**", "`ux-ui-design` available → the rows",
                     "If phase `@type:` is `ui` or `landing` and `ux-ui-design`"):
            self.assertIn(line(text), out, text)
        self.assertNotIn(line("If phase `@type:` is `landing` →"), out)
        self.assertNotIn(line("Svelte tasks"), out)

    def test_execution_step(self):
        root = Fixture(self).package(deps=["svelte"]).root
        out = trigger_output(self, root, "4c", "ui")
        self.assertIn(line("Svelte tasks and `svelte`"), out)
        self.assertIn(line("- UI tasks in the plan"), out)
        self.assertIn(line("**Motion — which source wins.**"), out)
        self.assertNotIn(line("| `**/*.rs` |"), out)
        self.assertNotIn(line("If phase `@type:` is `ui` →"), out)

    def test_stack_without_index_rows(self):
        out = trigger_output(self, Fixture(self).root, "gate", "backend")
        self.assertFalse([l for l in out if re.match(r"\| `[a-z0-9-]+` (4a|4c|5c|5g)", l)])
        self.assertNotIn(block("**How.**", INDEX)[0], out)

    def test_gate_takes_5c_and_5g_rows(self):
        root = Fixture(self).package(dev=["@playwright/test"]).root
        out = trigger_output(self, root, "gate")
        self.assertIn(line("| `playwright` 5g/debug:", INDEX), out)

    def test_bad_step_exits_2(self):
        rc, out, _ = run(Fixture(self).root, "--triggers", "--step", "5x")
        self.assertEqual((rc, out), (2, ""))


if __name__ == "__main__":
    unittest.main()
