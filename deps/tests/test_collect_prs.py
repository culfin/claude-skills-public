import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('collect_prs', Path(__file__).parents[1] / 'scripts/collect_prs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def pr(n, base='main', author='dependabot[bot]', sha=None):
    return dict(number=n, state='open', base=dict(ref=base), user=dict(login=author), head=dict(sha=sha or str(n)))


class CollectionTests(unittest.TestCase):
    def invoke(self, pages):
        def run(args, **kwargs):
            self.assertIn('--paginate', args)
            self.assertIn('--slurp', args)
            self.assertIn('base=main', args)
            return SimpleNamespace(stdout=json.dumps(pages))
        return module.collect('owner/repo', 'main', run)

    def test_collects_beyond_one_page(self):
        self.assertEqual(len(self.invoke([[pr(n) for n in range(1, 101)], [pr(101)]])), 101)

    def test_filters_target_and_author(self):
        self.assertEqual([p['number'] for p in self.invoke([[pr(1), pr(2, 'prod'), pr(3, author='human')]])], [1])

    def test_deduplicates_same_snapshot(self):
        self.assertEqual(len(self.invoke([[pr(1)], [pr(1)]])), 1)

    def test_changed_head_blocks(self):
        with self.assertRaises(ValueError):
            self.invoke([[pr(1)], [pr(1, sha='changed')]])

    def test_bad_shape_blocks(self):
        with self.assertRaises(ValueError):
            self.invoke({'message': 'denied'})

    def test_api_error_is_not_empty(self):
        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(1, 'gh')
        with self.assertRaises(subprocess.CalledProcessError):
            module.collect('owner/repo', 'main', fail)

    def test_empty_base_rejected(self):
        with self.assertRaises(ValueError):
            module.collect('owner/repo', '')


if __name__ == '__main__':
    unittest.main()
