import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("branch_config", Path(__file__).resolve().parents[1] / "scripts/branch_config.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "config.json"
    def tearDown(self):
        self.temp.cleanup()
    def write(self, data):
        self.path.write_text(json.dumps(data))
        return module.read_config(self.path)
    def test_missing_file_defaults(self):
        self.assertEqual(module.read_config(self.path), {"devBranch": "main", "prodBranch": "prod"})
    def test_missing_key_defaults(self):
        self.assertEqual(self.write({"devBranch": "develop"})["prodBranch"], "prod")
    def test_explicit_null_disables_prod(self):
        self.assertIsNone(self.write({"prodBranch": None})["prodBranch"])
    def test_custom_branches(self):
        self.assertEqual(self.write({"devBranch": "release/dev", "prodBranch": "release/prod"})["devBranch"], "release/dev")
    def test_null_dev_rejected(self):
        with self.assertRaises(ValueError): self.write({"devBranch": None})
    def test_empty_branch_rejected(self):
        with self.assertRaises(ValueError): self.write({"prodBranch": ""})
    def test_option_rejected(self):
        with self.assertRaises(ValueError): self.write({"devBranch": "--help"})
    def test_ref_expression_rejected(self):
        with self.assertRaises(ValueError): self.write({"devBranch": "main~1"})
    def test_equal_branches_rejected(self):
        with self.assertRaises(ValueError): self.write({"prodBranch": "main"})
    def test_malformed_rejected(self):
        self.path.write_text("{")
        with self.assertRaises(ValueError): module.read_config(self.path)
    def test_nonobject_rejected(self):
        with self.assertRaises(ValueError): self.write([])
