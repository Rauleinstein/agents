import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import agentsctl

ROOT = Path(__file__).resolve().parents[1]


class ExampleTests(unittest.TestCase):
    def setUp(self):
        self.items = agentsctl.validate_catalog(json.loads((ROOT / 'catalog.json').read_text()))

    def example(self, identifier, kind, path, harnesses):
        self.assertIn(identifier, self.items, 'optional original example missing')
        item = self.items[identifier]
        self.assertEqual((kind, path, harnesses), (item['kind'], item['path'], item['harnesses']))
        self.assertTrue((ROOT / path).exists())
        provenance = item['provenance']
        self.assertEqual(('original', 'v1', 'All rights reserved', True, 'optional'),
                         tuple(provenance[k] for k in ('source', 'revision', 'license', 'reviewed', 'maturity')))
        self.assertIn('not a security audit', provenance['review_scope'])
        return item

    def test_inert_plugin_fixture(self):
        item = self.example('example-bundle', 'plugin', 'plugins/example-bundle',
                            ['hermes', 'claude', 'codex', 'cursor'])
        body = (ROOT / item['path'] / 'README.md').read_text()
        self.assertIn('INERT', body)
        self.assertIn('not a runnable plugin', body)
        self.assertIn('hooks', body)
        self.assertEqual(['README.md'], sorted(p.name for p in (ROOT / item['path']).iterdir()))

    def test_cursor_native_reviewer(self):
        self.native_reviewer('cursor')

    def test_claude_native_reviewer(self):
        self.native_reviewer('claude')

    def native_reviewer(self, harness):
        item = self.example(harness + '-reviewer', 'agent',
                            'agents/' + harness + '/reviewer.md', [harness])
        self.assertEqual('reviewer.md', item['name'])
        body = (ROOT / item['path']).read_text()
        self.assertTrue(body.startswith('---\nname: reviewer\ndescription:'))
        self.assertIn('read-only', body)
        self.assertIn('exact paths', body)
        self.assertIn('unverified', body)
        if harness == 'claude':
            self.assertIn('tools: Read, Glob, Grep', body.split('---')[1])
        else:
            self.assertNotIn('tools:', body.split('---')[1])

    def test_portable_verification_skill(self):
        item = self.example('verify-before-reporting', 'skill', 'skills/verify-before-reporting',
                            ['hermes', 'claude', 'codex', 'cursor'])
        body = (ROOT / item['path'] / 'SKILL.md').read_text()
        self.assertTrue(body.startswith('---\nname: verify-before-reporting\n'))
        self.assertIn('description: Use when reporting completion. Require observable evidence.', body)
        self.assertIn('acceptance', body)
        self.assertIn('Never fabricate', body)
        self.assertIn('read back', body)


class ExampleCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.local = json.loads((ROOT / 'local-examples.json').read_text())
        (self.repo / 'catalog.json').write_text(json.dumps({'version': 1, 'items': self.local}))
        for item in self.local:
            src, dest = ROOT / item['path'], self.repo / item['path']
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copyfile(src, dest)

    def cli(self, harness, identifiers, targets, apply=False):
        env = self.base / 'env.json'
        env.write_text(json.dumps(dict(harness=harness, items=identifiers,
                                       targets={k: str(v) for k, v in targets.items()})))
        command = [sys.executable, str(ROOT / 'agentsctl.py'), 'sync', '--repo',
                   str(self.repo), '--env', str(env)]
        return subprocess.run(command + (['--apply'] if apply else []),
                              capture_output=True, text=True, cwd=self.base)

    def test_optional_payloads_preview_apply_and_unchanged_readback(self):
        for harness in ['hermes', 'claude', 'codex', 'cursor']:
            with self.subTest(harness=harness):
                home = self.base / harness
                targets = {'skill': home / '.agents/skills', 'plugin': home / 'staged/plugins'}
                ids = ['verify-before-reporting', 'example-bundle']
                if harness in {'claude', 'cursor'}:
                    targets['agent'] = home / '.agents/agents'
                    ids.append(harness + '-reviewer')
                result = self.cli(harness, ids, targets)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(''.join('install ' + i + '\n' for i in ids), result.stdout)
                self.assertFalse(home.exists())
                result = self.cli(harness, ids, targets, True)
                self.assertEqual(0, result.returncode, result.stderr)
                for item in self.local:
                    if item['id'] not in ids:
                        continue
                    dest = targets[item['kind']] / item['name']
                    wanted = agentsctl.digest(self.repo / item['path'])
                    self.assertEqual(wanted, agentsctl.digest(dest))
                    meta = targets[item['kind']] / '.agents-managed' / (item['name'] + '.json')
                    self.assertEqual(dict(id=item['id'], digest=wanted), json.loads(meta.read_text()))
                result = self.cli(harness, ids, targets, True)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(''.join('unchanged ' + i + '\n' for i in ids), result.stdout)

    def test_foreign_native_agent_rejected_before_any_target_writes(self):
        for harness, foreign in [('claude', 'cursor-reviewer'), ('cursor', 'claude-reviewer'),
                                 ('hermes', 'claude-reviewer'), ('codex', 'cursor-reviewer')]:
            with self.subTest(harness=harness):
                targets = {'skill': self.base / harness / 'skills', 'agent': self.base / harness / 'agents'}
                result = self.cli(harness, ['verify-before-reporting', foreign], targets, True)
                self.assertEqual(2, result.returncode)
                self.assertIn('incompatible harness', result.stderr)
                self.assertEqual('', result.stdout)
                self.assertFalse((self.base / harness).exists())

    def test_plugin_sentinel_script_is_staged_never_executed(self):
        sentinel = self.base / 'executed'
        source = self.repo / 'plugins/example-bundle/install.sh'
        source.write_text('#!/bin/sh\ntouch ' + str(sentinel) + '\n')
        source.chmod(0o755)
        target = self.base / 'staged'
        result = self.cli('codex', ['example-bundle'], {'plugin': target}, True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(source.read_bytes(), (target / 'example-bundle/install.sh').read_bytes())
        self.assertFalse(sentinel.exists())


class ImportMergeTests(unittest.TestCase):
    def test_invalid_local_ids_are_rejected(self):
        from scripts import import_upstreams
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            repo = Path(tmp)
            (repo / 'local-examples.json').write_text(json.dumps([{'id': '../escape'}]))
            with self.assertRaises(ValueError):
                import_upstreams.merge_local_examples([], repo)

    def test_duplicate_local_ids_and_upstream_conflicts_are_rejected(self):
        from scripts import import_upstreams
        item = json.loads((ROOT / 'local-examples.json').read_text())[0]
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
            repo = Path(tmp)
            for local, upstream in [([item, item], []), ([item], [item])]:
                with self.subTest(local_count=len(local)):
                    (repo / 'local-examples.json').write_text(json.dumps(local))
                    with self.assertRaisesRegex(ValueError, 'duplicate catalog id'):
                        import_upstreams.merge_local_examples(upstream, repo)

    def test_reimport_merges_sidecar_without_changing_upstreams(self):
        from scripts import import_upstreams
        self.assertTrue(hasattr(import_upstreams, 'merge_local_examples'), 'sidecar merge API missing')
        upstream = [i for i in json.loads((ROOT / 'catalog.json').read_text())['items']
                    if i['provenance']['source'] != 'original']
        before = json.dumps(upstream)
        result = import_upstreams.merge_local_examples(upstream, ROOT)
        local = json.loads((ROOT / 'local-examples.json').read_text())
        self.assertEqual(upstream + local, result)
        self.assertEqual(result, import_upstreams.merge_local_examples(upstream, ROOT))
        self.assertEqual(before, json.dumps(upstream))
        self.assertEqual(52, len(result))
