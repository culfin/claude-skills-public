import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('check_superpowers', Path(__file__).resolve().parents[1] / 'scripts/check-superpowers.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SuperpowersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for role in m.REQUIRED:
            p = self.root / 'skills' / role / 'SKILL.md'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('fixture')
        p = self.root / 'skills/brainstorming/scripts'
        p.mkdir()
        for name in ['start-server.sh', 'stop-server.sh']: (p/name).write_text('exit 0')
    def tearDown(self): self.temp.cleanup()
    def manifest(self, name, value):
        p=self.root / name
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(value))
    def test_files_are_not_runtime_proof(self):
        result=m.inspect(self.root)
        self.assertEqual(result['status'], 'files-present')
        self.assertEqual(result['runtimeCompatibility'], 'not-tested')
        self.assertEqual(result['freshness'], 'not-checked')
    def test_missing_review_blocks(self):
        (self.root/'skills/requesting-code-review/SKILL.md').unlink()
        self.assertEqual(m.inspect(self.root)['status'], 'blocked')
    def test_missing_stop_blocks(self):
        (self.root/'skills/brainstorming/scripts/stop-server.sh').unlink()
        self.assertEqual(m.inspect(self.root)['status'], 'blocked')
    def test_versions_match(self):
        for p in ['.claude-plugin/plugin.json','.codex-plugin/plugin.json']: self.manifest(p, {'version':'6.4.1'})
        self.assertEqual(m.inspect(self.root)['status'],'files-present')
    def test_versions_disagree(self):
        self.manifest('.claude-plugin/plugin.json', {'version':'6.4.1'})
        self.manifest('.codex-plugin/plugin.json', {'version':'6.3.0'})
        self.assertEqual(m.inspect(self.root)['status'],'blocked')
    def test_bad_manifest_blocks(self):
        self.manifest('plugin.json', [])
        self.assertEqual(m.inspect(self.root)['status'],'blocked')
