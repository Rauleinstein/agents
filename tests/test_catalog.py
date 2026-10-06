import hashlib
import json
from pathlib import Path
import re
import unittest
import agentsctl

ROOT = Path(__file__).resolve().parents[1]

class CatalogTests(unittest.TestCase):
    def test_complete_pinned_catalog(self):
        self.assertTrue((ROOT / 'catalog.json').is_file(), 'imported catalog missing')
        items = agentsctl.validate_catalog(json.loads((ROOT / 'catalog.json').read_text()))
        self.assertEqual(len(items), 52)
        originals = [i for i in items.values() if i['provenance']['source'] == 'original']
        self.assertEqual({i['id'] for i in originals},
                         {'verify-before-reporting', 'claude-reviewer', 'cursor-reviewer', 'example-bundle'})
        upstream = [i for i in items.values() if i['provenance']['source'] != 'original']
        self.assertEqual(len(upstream), 48)
        self.assertEqual(sum(i['id'].startswith('speckit-') for i in upstream), 10)
        for item in upstream:
            path = ROOT / item['path']
            self.assertTrue((path / 'SKILL.md').is_file())
            self.assertTrue((path / 'LICENSE').is_file())
            self.assertRegex(item['provenance']['revision'], r'^[0-9a-f]{40}$')
            self.assertIn('not a security audit', item['provenance']['review_scope'])
            agentsctl.digest(path)
        matt = [i for i in items.values() if i['id'].startswith('mattpocock-')]
        self.assertEqual(len(matt), 38)
        self.assertEqual(sum(i['provenance']['maturity'] == 'stable' for i in matt), 27)
        self.assertEqual(sum(i['provenance']['maturity'] == 'optional' for i in matt), 4)
        self.assertEqual(sum(i['provenance']['maturity'] == 'experimental' for i in matt), 7)
        self.assertEqual(items['mattpocock-git-guardrails-claude-code']['harnesses'], ['claude'])

    def test_upstream_files_preserved_and_resources_complete(self):
        for vendor in (ROOT / 'vendor').iterdir():
            manifest = json.loads((vendor / 'IMPORT-PROVENANCE.json').read_text())
            for name, expected in manifest['upstream_sha256'].items():
                self.assertEqual(hashlib.sha256((vendor / name).read_bytes()).hexdigest(), expected, name)
            self.assertFalse(any(p.name == 'AGENTS.md' for p in vendor.rglob('*')))
            if vendor.name == 'mattpocock-skills':
                for skill in vendor.glob('skills/*/*/SKILL.md'):
                    self.assertTrue((skill.parent / 'agents/openai.yaml').is_file())
                    for link in re.findall(r'\]\(([^)]+)\)', skill.read_text()):
                        if link.endswith(('.md', '.sh', '.cjs')) and not '://' in link and not link.startswith('./src/'):
                            self.assertTrue((skill.parent / link).is_file(), (skill, link))

    def test_official_generated_skills_resolve_templates_and_scripts(self):
        skills = list((ROOT / 'generated/github-spec-kit/generic').glob('*/SKILL.md'))
        self.assertEqual(len(skills), 10)
        manifest = json.loads((ROOT / 'generated/github-spec-kit/GENERATION.json').read_text())
        self.assertEqual(len(manifest['generated_sha256']), 10)
        for skill in skills:
            self.assertEqual(hashlib.sha256(skill.read_bytes()).hexdigest(), manifest['generated_sha256'][skill.parent.name + '/SKILL.md'])
            body = skill.read_text()
            self.assertRegex(body, r'(?m)^name: "?' + re.escape(skill.parent.name) + r'"?$')
            self.assertNotRegex(body, r'__SPECKIT_[A-Z_]+__|\{SCRIPT\}|\{ARGS\}|\{AGENT\}')
            for script in re.findall(r'\.specify/scripts/bash/([\w-]+\.sh)', body):
                self.assertTrue((ROOT / 'vendor/github-spec-kit/scripts/bash' / script).is_file(), script)
            self.assertNotIn('/home/raulalvarez', body)
