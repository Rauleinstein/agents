import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'agentsctl.py'

class DigestTests(unittest.TestCase):
    def test_digest_is_stable_and_tracks_paths_and_bytes(self):
        self.assertTrue(MODULE.exists(), 'installer module must exist')
        spec = importlib.util.spec_from_file_location('agentsctl', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as root:
            p = Path(root)
            (p / 'a').write_bytes(b'one')
            first = module.digest(p)
            (p / 'empty').mkdir()
            self.assertEqual(first, module.digest(p))
            (p / 'a').write_bytes(b'two')
            self.assertNotEqual(first, module.digest(p))
            (p / 'a').write_bytes(b'one')
            (p / 'a').rename(p / 'b')
            self.assertNotEqual(first, module.digest(p))

import json
import sys
sys.path.insert(0, str(MODULE.parent))
import agentsctl as ctl


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.source = self.repo / 'skills' / 'sample'
        self.source.mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('# sample')
        self.target = self.base / 'target'
        self.catalog = {'version': 1, 'items': [dict(id='sample', kind='skill', path='skills/sample', name='sample', harnesses=['hermes', 'claude', 'cursor', 'codex'], provenance=dict(source='https://example.test', revision='abc', license='MIT', reviewed=True))]}
        self.environment = dict(harness='hermes', targets={'skill': str(self.target)}, items=['sample'])
        self.env = self.base / 'env.json'
        self.save()

    def save(self):
        (self.repo / 'catalog.json').write_text(json.dumps(self.catalog))
        self.env.write_text(json.dumps(self.environment))

    def sync(self, apply=False):
        return ctl.sync(self.env, self.repo, apply=apply)

    def test_preview_is_read_only(self):
        before = sorted(str(p) for p in self.base.rglob('*'))
        self.assertTrue(hasattr(ctl, 'sync'), 'sync entry point is required')
        self.assertEqual(['install sample'], self.sync())
        self.assertEqual(before, sorted(str(p) for p in self.base.rglob('*')))

    def test_install_repeat_update(self):
        self.assertTrue(hasattr(ctl, 'sync'), 'sync entry point is required')
        self.assertEqual(['install sample'], self.sync(True))
        self.assertEqual('# sample', (self.target / 'sample' / 'SKILL.md').read_text())
        self.assertEqual(['unchanged sample'], self.sync(True))
        (self.source / 'SKILL.md').write_text('# changed')
        self.assertEqual(['update sample'], self.sync(True))
        self.assertEqual('# changed', (self.target / 'sample' / 'SKILL.md').read_text())


if __name__ == '__main__':
    unittest.main()
