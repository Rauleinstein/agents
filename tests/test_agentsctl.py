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

    def test_schema_and_compatibility_rejections_are_read_only(self):
        import copy
        cases = [
            ('catalog version', lambda c, e: c.update(version=True)),
            ('catalog list', lambda c, e: c.update(items={})),
            ('duplicate catalog', lambda c, e: c['items'].append(copy.deepcopy(c['items'][0]))),
            ('bad id', lambda c, e: c['items'][0].update(id='../bad')),
            ('bad name', lambda c, e: c['items'][0].update(name='UPPER')),
            ('reserved name', lambda c, e: c['items'][0].update(name='.agents-managed')),
            ('path traversal', lambda c, e: c['items'][0].update(path='skills/../skills/sample')),
            ('absolute source', lambda c, e: c['items'][0].update(path=str(self.source))),
            ('unreviewed', lambda c, e: c['items'][0]['provenance'].update(reviewed=False)),
            ('no revision', lambda c, e: c['items'][0]['provenance'].pop('revision')),
            ('bad harnesses', lambda c, e: c['items'][0].update(harnesses='hermes')),
            ('incompatible', lambda c, e: c['items'][0].update(harnesses=['claude'])),
            ('bad kind', lambda c, e: c['items'][0].update(kind='other')),
            ('unknown harness', lambda c, e: e.update(harness='other')),
            ('empty selection', lambda c, e: e.update(items=[])),
            ('duplicate selection', lambda c, e: e.update(items=['sample', 'sample'])),
            ('unknown selection', lambda c, e: e.update(items=['missing'])),
            ('relative target', lambda c, e: e.update(targets={'skill': 'relative'})),
            ('noncanonical target', lambda c, e: e.update(targets={'skill': str(self.target) + '/../target'})),
            ('overlap repo', lambda c, e: e.update(targets={'skill': str(self.repo / 'output')})),
            ('ancestor repo', lambda c, e: e.update(targets={'skill': str(self.base)})),
            ('overlap roots', lambda c, e: e.update(targets={'skill': str(self.target), 'plugin': str(self.target / 'plugins')})),
            ('same roots', lambda c, e: e.update(targets={'skill': str(self.target), 'plugin': str(self.target)})),
            ('malformed target map', lambda c, e: e.update(targets=[])),
        ]
        original_c, original_e = copy.deepcopy(self.catalog), copy.deepcopy(self.environment)
        for label, mutate in cases:
            with self.subTest(label=label):
                self.catalog, self.environment = copy.deepcopy(original_c), copy.deepcopy(original_e)
                mutate(self.catalog, self.environment)
                self.save()
                with self.assertRaises(ctl.SafetyError):
                    self.sync(True)
                self.assertFalse(self.target.exists())

    def test_duplicate_destinations_rejected(self):
        import copy
        second = copy.deepcopy(self.catalog['items'][0])
        second['id'] = 'second'
        self.catalog['items'].append(second)
        self.environment['items'].append('second')
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse(self.target.exists())

    def test_native_agent_and_plugin_shapes_rejected(self):
        item = self.catalog['items'][0]
        item['kind'] = 'agent'
        self.environment['targets'] = {'agent': str(self.target)}
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        item['kind'] = 'plugin'
        item['path'] = 'skills/sample/SKILL.md'
        self.environment['targets'] = {'plugin': str(self.target)}
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

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
