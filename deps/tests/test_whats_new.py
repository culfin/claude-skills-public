import re
import unittest
from pathlib import Path

DEPS = Path(__file__).resolve().parents[1]
REF = DEPS / 'references/whats-new.md'
TECHNOLOGIES = ['Next.js', 'React', 'Tailwind', 'shadcn', 'Base UI', 'Radix', 'PostgreSQL', 'better-auth',
                'Zod', 'Vitest', 'Playwright', 'Docker', 'GitHub Actions', 'Tauri', 'Rust', 'Svelte',
                'next-intl', 'TanStack', 'Biome', 'TypeScript', 'Stripe', 'Sentry', 'AI SDK', 'Astro',
                'Fastify', 'Kotlin', 'Swift', 'pnpm']


class WhatsNewTests(unittest.TestCase):
    def rows(self):
        rows = [[c.strip() for c in l.strip().strip('|').split('|')]
                for l in REF.read_text().splitlines() if l.startswith('|') and not l.startswith('|---')]
        return rows[1:]

    def test_every_technology_has_a_package_and_an_https_url(self):
        rows = self.rows()
        for tech in TECHNOLOGIES:
            self.assertTrue(any(tech in r[0] for r in rows), tech)
        for tech, package, read in rows:
            self.assertTrue(package, tech)
            urls = re.findall(r'https://\S+', read)
            self.assertTrue(urls, tech)
            self.assertEqual(len(urls), len(read.split(' · ')), tech)

    def test_rules(self):
        text = ' '.join(REF.read_text().split())
        for phrase in ('minor or major', 'Patch jumps: no report', 'Report only', 'No automatic rewrites',
                       'skipped: <reason>', 'skipped range'):
            self.assertIn(phrase, text, phrase)

    def test_skill_points_to_the_reference_and_stays_small(self):
        skill = (DEPS / 'SKILL.md').read_text()
        self.assertIn('references/whats-new.md', skill)
        self.assertLessEqual(len(skill.splitlines()), 180)
        self.assertNotIn('https://', skill.split('references/whats-new.md', 1)[1].splitlines()[0])
        self.assertIn('references/whats-new.md', (DEPS / 'references/merge.md').read_text())

    def test_no_private_data(self):
        text = REF.read_text()
        for needle in ('/Users/', '/home/', '.ts.net'):
            self.assertNotIn(needle, text)
        self.assertIsNone(re.search(r'\b\d{1,3}(\.\d{1,3}){3}\b', text))


if __name__ == '__main__':
    unittest.main()
