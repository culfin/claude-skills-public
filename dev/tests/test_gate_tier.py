"""gate-tier.py decides the gate tier from phase size, type and touched files."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gate-tier.py"


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


class GateTierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        (self.root / "app.py").write_text("x = 1\n")
        git(self.root, "add", "app.py")
        git(self.root, "commit", "-qm", "base")
        self.base = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def run_tier(self, *extra):
        out = subprocess.run([sys.executable, str(SCRIPT), "--base", self.base, "--root", str(self.root), *extra],
                             capture_output=True, text=True)
        return out.returncode, out.stdout.splitlines(), out.stderr

    def write(self, rel, lines):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(f"line {i}\n" for i in range(lines)))

    def test_test_files_are_not_sensitive(self):
        self.write("tests/api/users.test.ts", 20)
        self.write("src/lib/auth/__tests__/session.test.ts", 20)
        rc, out, _ = self.run_tier("--tasks", "1", "--type", "feature")
        self.assertEqual(out[0], "small", out)

    def test_auth_code_stays_sensitive(self):
        self.write("src/lib/auth/session.ts", 20)
        rc, out, _ = self.run_tier("--tasks", "1", "--type", "feature")
        self.assertEqual(out[0], "large", out)

    def test_small_change_is_small(self):
        self.write("app.py", 20)
        rc, out, _ = self.run_tier("--tasks", "2", "--type", "ui")
        self.assertEqual(rc, 0)
        self.assertEqual(out[0], "small")

    def test_too_many_lines_is_large(self):
        self.write("big.py", 401)          # untracked file counts
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual(out[0], "large")
        self.assertTrue(any("lines" in r for r in out[1:]))

    def test_exactly_400_lines_is_small(self):
        self.write("big.py", 400)
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual(out[0], "small")

    def test_too_many_tasks_is_large(self):
        self.write("app.py", 3)
        rc, out, _ = self.run_tier("--tasks", "4")
        self.assertEqual(out[0], "large")

    def test_risk_type_is_large(self):
        for t in ("auth", "security", "migration", "data"):
            with self.subTest(t=t):
                rc, out, _ = self.run_tier("--tasks", "1", "--type", t)
                self.assertEqual(out[0], "large")

    def test_backend_only_large_with_db_change(self):
        self.write("svc/handler.py", 5)
        self.assertEqual(self.run_tier("--tasks", "1", "--type", "backend")[1][0], "small")
        self.write("migrations/0002_add.sql", 5)
        self.assertEqual(self.run_tier("--tasks", "1", "--type", "backend")[1][0], "large")

    def test_workflow_change_is_large_without_type(self):
        self.write(".github/workflows/ci.yml", 3)
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual(out[0], "large")
        self.assertTrue(any(r.startswith("- ops files:") for r in out[1:]), out)

    def test_dockerfile_change_is_large(self):
        for rel in ("Dockerfile", "svc/Dockerfile.prod", "docker-compose.yml", "deploy/run.sh", "infra/main.tf"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1", "--type", "ui")
                self.assertEqual(out[0], "large")
                (self.root / rel).unlink()

    def test_lockfile_change_is_large(self):
        for rel in ("pnpm-lock.yaml", "apps/web/package.json", "Cargo.lock", "app/build.gradle.kts"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1")
                self.assertEqual(out[0], "large")
                self.assertTrue(any(r.startswith("- dependency manifest:") for r in out[1:]), out)
                (self.root / rel).unlink()

    def test_db_change_is_large_for_any_type(self):
        self.write("migrations/1.sql", 2)
        for t in ("ui", "backend", ""):
            with self.subTest(t=t):
                args = ("--tasks", "1") + (("--type", t) if t else ())
                rc, out, _ = self.run_tier(*args)
                self.assertEqual(out[0], "large")
                self.assertTrue(any(r.startswith("- DB change:") for r in out[1:]), out)

    def test_rails_and_alembic_migrations_are_db_change(self):
        for rel in ("db/migrate/20261111_add_users.rb", "alembic/versions/abc123_add_users.py"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1")
                self.assertEqual(out[0], "large")
                self.assertTrue(any(r.startswith("- DB change:") and rel in r for r in out[1:]), out)
                (self.root / rel).unlink()

    def test_unknown_type_cannot_weaken(self):
        self.write("src/auth/session.ts", 2)
        rc, out, _ = self.run_tier("--tasks", "1", "--type", "fullstack")
        self.assertEqual(out[0], "large")

    def test_infrastructure_dir_is_large(self):
        self.write("infrastructure/main.yaml", 2)
        self.assertEqual(self.run_tier("--tasks", "1")[1][0], "large")

    def test_deploy_script_is_large(self):
        for rel in ("scripts/deploy.sh", "bin/predeploy.sh", "deploy-prod.sh"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1")
                self.assertEqual(out[0], "large")
                self.assertTrue(any(r.startswith("- ops files:") for r in out[1:]), out)
                (self.root / rel).unlink()

    def test_nginx_dir_is_large(self):
        self.write("nginx/site.conf", 2)
        self.assertEqual(self.run_tier("--tasks", "1")[1][0], "large")

    def test_dockerfile_case_insensitive(self):
        for rel in ("svc/dockerfile", "svc/Dockerfile.prod"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                self.assertEqual(self.run_tier("--tasks", "1")[1][0], "large")
                (self.root / rel).unlink()

    def test_more_dependency_manifests_are_large(self):
        for rel in ("pom.xml", "Pipfile.lock", "uv.lock", "composer.json", "composer.lock", "bun.lockb",
                    "pnpm-workspace.yaml", "Package.resolved", "src/App/App.csproj"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1")
                self.assertEqual(out[0], "large")
                self.assertTrue(any(r.startswith("- dependency manifest:") for r in out[1:]), out)
                (self.root / rel).unlink()

    def test_docs_deploy_md_stays_small(self):
        self.write("docs/deploy.md", 20)
        self.assertEqual(self.run_tier("--tasks", "1")[1][0], "small")

    def test_docs_only_stays_small(self):
        self.write("README.md", 50)
        self.write("docs/deploy/notes.md", 50)
        self.write("docs/package.json.md", 5)
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual((rc, out[0]), (0, "small"), out)

    def test_sensitive_file_forces_large(self):
        for rel in ("src/auth/session.ts", "app/api/orders/route.ts", "db/migrations/1.sql",
                    "src/middleware.ts", "server/routes/login.py"):
            with self.subTest(rel=rel):
                self.write(rel, 2)
                rc, out, _ = self.run_tier("--tasks", "1", "--type", "ui")
                self.assertEqual(out[0], "large")
                (self.root / rel).unlink()

    def test_markdown_does_not_count_towards_size(self):
        # A planned phase carries its spec and plan (often 500+ lines); they must not make it large.
        self.write("docs/plans/phase-5.md", 900)
        self.write("STATE.md", 120)
        self.write("app.py", 50)
        rc, out, _ = self.run_tier("--tasks", "2")
        self.assertEqual((rc, out[0]), (0, "small"), out)
        self.assertIn("51 changed lines", out[1])          # app.py: 1 removed + 50 added

    def test_markdown_still_counts_as_sensitive_path(self):
        self.write("src/auth/notes.md", 3)
        rc, out, _ = self.run_tier("--tasks", "1")
        self.assertEqual(out[0], "large")
        self.assertTrue(any("sensitive files" in r for r in out[1:]))

    def test_gate_full_forces_large(self):
        rc, out, _ = self.run_tier("--tasks", "1", "--gate", "full")
        self.assertEqual(out[0], "large")

    def slim(self, *extra):
        rc, out, _ = self.run_tier("--slim", *extra)
        self.assertEqual(rc, 0)
        return [l for l in out if l.startswith("+ ")]

    def test_slim_triggers_none_for_plain_code(self):
        self.write("app.py", 20)
        self.assertEqual(self.slim(), ["+ none"])

    def test_slim_triggers_security_by_path_and_type(self):
        self.write("src/lib/auth/session.ts", 5)
        self.assertTrue(self.slim()[0].startswith("+ security: "), self.slim())
        self.assertTrue(any(l.startswith("+ codex: security") for l in self.slim()))
        self.assertTrue(self.slim()[0].endswith("→ Security review"), self.slim())

    def test_slim_security_ignores_tests_and_covers_secrets_and_types(self):
        self.write("tests/auth/session.test.ts", 5)
        self.assertEqual(self.slim(), ["+ none"])
        self.write("config/secrets.py", 5)
        self.assertTrue(self.slim()[0].startswith("+ security: "), self.slim())

    def test_slim_security_by_risk_type(self):
        self.write("app.py", 5)
        self.assertTrue(self.slim("--type", "data")[0].startswith("+ security: "))

    def test_slim_triggers_ui_and_codex_by_size(self):
        self.write("src/components/Button.tsx", 10)
        self.assertEqual([l.split(":")[0] for l in self.slim()], ["+ ui"])
        self.assertTrue(self.slim()[0].endswith("→ UX review, Accessibility review, Polish review"), self.slim())
        self.write("big.py", 301)
        self.assertEqual([l.split(":")[0] for l in self.slim()], ["+ ui", "+ codex"])

    def test_slim_review_findings_auth_basenames_native_tests_styles_test_lines(self):
        # /code-review high on v4.19.0: matrix basenames missed, Swift tests and CSS tokens triggered, test lines counted.
        for f in ("src/lib/auth-options.ts", "src/components/LoginForm.ts", "src/lib/sessionStore.ts",
                  "src/app/webhooks/stripe/route.ts"):
            with self.subTest(f):
                self.setUp()
                self.write(f, 3)
                self.assertTrue(self.slim()[0].startswith("+ security: "), self.slim())
        self.setUp()
        self.write("AppTests/TokenRefreshTests.swift", 3)
        self.write("src/styles/reset.css", 3)
        self.write("src/styles/tokens.css", 3)
        self.assertEqual([l.split(":")[0] for l in self.slim()], ["+ ui"])
        self.setUp()
        self.write("tests/test_big.py", 350)
        self.write("app.py", 2)
        self.assertEqual(self.slim(), ["+ none"])

    def test_without_slim_no_trigger_lines(self):
        self.write("src/lib/auth/session.ts", 5)
        rc, out, _ = self.run_tier()
        self.assertFalse(any(l.startswith("+ ") for l in out), out)

    def test_bad_base_exits_2(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "--base", "nope", "--root", str(self.root)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertEqual(out.stdout, "")


if __name__ == "__main__":
    unittest.main()
