# dev/hooks/test_gate_check.py
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("gate_check", os.path.join(_HERE, "gate-check.py"))
gate_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate_check)

T_EDIT = "2026-09-25T10:00:00.460Z"


def edit(path, ts=T_EDIT):
    ev = {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}]}}
    if ts is not None:
        ev["timestamp"] = ts
    return ev


def typed(command, args=""):
    text = "<command-message>%s</command-message>\n<command-name>/%s</command-name>\n<command-args>%s</command-args>" % (command, command, args)
    return {"type": "user", "message": {"role": "user", "content": text}}


def skill(name):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": name}}]}}


def git(root, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_COMMITTER_DATE"] = date
        env["GIT_AUTHOR_DATE"] = date
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True, env=env)


def init_repo(root):
    os.makedirs(root, exist_ok=True)
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "commit", "-q", "--allow-empty", "-m", "init", date="2026-09-25T09:00:00Z")



def hinted(result):
    """Der Hook meldet sich als Hinweis an den Nutzer (systemMessage), nicht als Block."""
    return bool(result) and str(result.get("systemMessage", "")).startswith("DEV-GATE")

class DevGateCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "proj")
        os.makedirs(os.path.join(self.root, "src", "lib"))
        init_repo(self.root)
        self.state = os.path.join(self.tmp.name, "state")
        os.makedirs(self.state)
        self.roadmap("- [x] Phase 1: Fertig\n- [ ] Phase 2: Offen\n")

    def tearDown(self):
        self.tmp.cleanup()

    def roadmap(self, text):
        with open(os.path.join(self.root, "ROADMAP.md"), "w") as fh:
            fh.write("# Roadmap\n\n" + text)

    def src(self, rel):
        return os.path.join(self.root, rel)

    def gate_commit(self, date, root=None, message="chore: quality gate — Phase 3 [gate-pass]"):
        git(root or self.root, "commit", "-q", "--allow-empty", "-m", message, date=date)

    def run_with(self, events, session="s1", cwd=None, raw_lines=(), env=None):
        path = os.path.join(self.tmp.name, "t.jsonl")
        with open(path, "w") as fh:
            for line in raw_lines:
                fh.write(line + "\n")
            for ev in events:
                fh.write(json.dumps(ev) + "\n")
        payload = {"transcript_path": path, "session_id": session}
        if cwd is not False:
            payload["cwd"] = cwd or self.root
        return gate_check.decide(payload, self.state, env={} if env is None else env)

    # Gate-Signal
    def test_edit_without_gate_hints(self):
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_reason_names_dev_check(self):
        self.assertIn("/dev check", self.run_with([edit(self.src("src/a.ts"))])["systemMessage"])

    def test_gate_commit_after_edit_allows(self):
        self.gate_commit("2026-09-25T10:05:00Z")
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"))]))

    def test_gate_commit_same_second_allows(self):
        self.gate_commit("2026-09-25T10:00:00Z")
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"), ts="2026-09-25T10:00:00.900Z")]))

    def test_gate_commit_before_edit_hints(self):
        self.gate_commit("2026-09-25T09:55:00Z")
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_gate_commit_from_message_file_counts(self):
        msg = os.path.join(self.tmp.name, "msg.txt")
        with open(msg, "w") as fh:
            fh.write("chore: dev check [gate-pass]\n\nlang\n")
        git(self.root, "commit", "-q", "--allow-empty", "-F", msg, date="2026-09-25T10:05:00Z")
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"))]))

    def test_gate_commit_in_other_repo_does_not_count(self):
        other = os.path.join(self.tmp.name, "other")
        init_repo(other)
        self.gate_commit("2026-09-25T10:05:00Z", root=other)
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_gate_commit_on_other_local_branch_counts(self):
        git(self.root, "checkout", "-q", "-b", "feature")
        self.gate_commit("2026-09-25T10:05:00Z")
        git(self.root, "checkout", "-q", "-")
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"))]))

    def test_edits_in_nested_worktrees_dir_are_ignored(self):
        self.assertIsNone(self.run_with([edit(self.src(".worktrees/feature/src/a.ts"))]))

    def test_brainstorm_mockups_in_superpowers_dir_are_ignored(self):
        # Entwuerfe des Brainstorming-Begleiters (HTML) sind kein Projektcode.
        self.assertIsNone(self.run_with([edit(self.src(".superpowers/brainstorm/1-2/content/layout.html"))]))

    def test_rebased_old_gate_does_not_count(self):
        env = dict(os.environ, GIT_AUTHOR_DATE="2026-09-25T09:55:00Z", GIT_COMMITTER_DATE="2026-09-25T10:05:00Z")
        subprocess.run(["git", "-C", self.root, "commit", "-q", "--allow-empty", "-m",
                        "chore: quality gate — Phase 2 [gate-pass]"], check=True, capture_output=True, env=env)
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_marker_only_in_body_does_not_count(self):
        self.gate_commit("2026-09-25T10:05:00Z", message="feat: Hook\n\nerkennt jetzt [gate-pass] im Betreff")
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_older_body_mention_does_not_hide_real_gate(self):
        self.gate_commit("2026-09-25T10:04:00Z", message="chore: dev check [gate-pass]")
        self.gate_commit("2026-09-25T10:06:00Z", message="docs: Notiz\n\nsiehe [gate-pass] oben")
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"))]))

    def test_commit_without_marker_does_not_count(self):
        self.gate_commit("2026-09-25T10:05:00Z", message="feat: irgendwas")
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_not_a_git_repo_allows(self):
        shutil.rmtree(os.path.join(self.root, ".git"))
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"))]))

    def test_edit_without_timestamp_allows(self):
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"), ts=None)]))

    # Aktivierung
    def test_no_roadmap_allows(self):
        os.remove(os.path.join(self.root, "ROADMAP.md"))
        self.assertIsNone(self.run_with([edit(self.src("src/a.ts"))]))

    def test_stale_active_phase_without_dev_session_hints(self):
        self.roadmap("- [x] Phase 1: Fertig\n- [~] Phase 2: seit Wochen liegengeblieben\n")
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))])))

    def test_typed_dev_command_allows(self):
        self.assertIsNone(self.run_with([typed("dev", "next"), edit(self.src("src/a.ts"))]))

    def test_dev_skill_call_allows(self):
        self.assertIsNone(self.run_with([skill("dev"), edit(self.src("src/a.ts"))]))

    def test_other_typed_command_does_not_count_as_dev(self):
        self.assertTrue(hinted(self.run_with([typed("deploy"), edit(self.src("src/a.ts"))])))

    def test_meta_message_does_not_count_as_dev(self):
        meta = typed("dev", "next")
        meta["isMeta"] = True
        self.assertTrue(hinted(self.run_with([meta, edit(self.src("src/a.ts"))])))

    def test_roadmap_found_from_subdirectory(self):
        result = self.run_with([edit(self.src("src/lib/b.ts"))], cwd=self.src("src/lib"))
        self.assertTrue(hinted(result))

    def test_search_stops_at_git_root_without_roadmap(self):
        other = os.path.join(self.root, "vendor", "repo")
        os.makedirs(os.path.join(other, ".git"))
        self.assertIsNone(self.run_with([edit(os.path.join(other, "x.ts"))], cwd=other))

    # Was als Code zaehlt
    def test_edit_outside_project_allows(self):
        self.assertIsNone(self.run_with([edit(os.path.join(self.tmp.name, "other-repo", "x.py"))]))

    def test_non_code_edits_allow(self):
        events = [edit(self.src("README.md")), edit(self.src("docs/x.ts")), edit(self.src(".scratch/y.ts")),
                  edit(self.src(".claude/settings.json")), edit(self.src("CHANGELOG.md"))]
        self.assertIsNone(self.run_with(events))

    def test_nested_docs_dir_counts_as_code(self):
        self.assertTrue(hinted(self.run_with([edit(self.src("app/docs/page.tsx"))])))

    def test_node_modules_anywhere_is_ignored(self):
        self.assertIsNone(self.run_with([edit(self.src("packages/x/node_modules/y.js"))]))

    def test_drupal_and_shell_files_count(self):
        for rel in ("web/modules/custom/x/x.module", "web/themes/t/templates/page.html.twig",
                    "web/modules/custom/x/src/Foo.php", "scripts/deploy.sh", "static/index.html"):
            with self.subTest(rel=rel):
                self.assertTrue(hinted(self.run_with([edit(self.src(rel))], session=rel)))

    # Einmal je Sitzung
    def test_second_stop_without_new_edit_allows(self):
        events = [edit(self.src("src/a.ts"))]
        self.assertTrue(hinted(self.run_with(events)))
        self.assertIsNone(self.run_with(events))

    # Seit 27.09.2026: hoechstens ein Hinweis je Sitzung, auch nach neuen Aenderungen.
    def test_new_edit_after_hint_stays_quiet(self):
        self.run_with([edit(self.src("src/a.ts"))])
        events = [edit(self.src("src/a.ts")), edit(self.src("src/b.ts"), ts="2026-09-25T10:01:00.000Z")]
        self.assertIsNone(self.run_with(events))

    def test_hint_does_not_block(self):
        self.assertNotIn("decision", self.run_with([edit(self.src("src/a.ts"))]))

    def test_state_is_per_session(self):
        self.run_with([edit(self.src("src/a.ts"))], session="one")
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))], session="two")))

    # Robustheit
    def test_cwd_falls_back_to_env(self):
        result = self.run_with([edit(self.src("src/a.ts"))], cwd=False, env={"CLAUDE_PROJECT_DIR": self.root})
        self.assertTrue(hinted(result))

    def test_missing_transcript_allows(self):
        self.assertIsNone(gate_check.decide({"cwd": self.root, "session_id": "x"}, self.state, env={}))

    def test_malformed_lines_are_ignored(self):
        raw = ["not json", "[]", json.dumps({"type": "user"}), json.dumps({"message": "text"}),
               json.dumps({"message": {"content": [{"type": "tool_use", "name": "Edit", "input": "kaputt"}]}})]
        self.assertTrue(hinted(self.run_with([edit(self.src("src/a.ts"))], raw_lines=raw)))


if __name__ == "__main__":
    unittest.main()
