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

    def test_unmanaged_destination_is_preserved(self):
        dest = self.target / 'sample'
        dest.mkdir(parents=True)
        (dest / 'mine').write_text('mine')
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertEqual('mine', (dest / 'mine').read_text())

    def test_local_edits_are_preserved(self):
        self.sync(True)
        payload = self.target / 'sample' / 'SKILL.md'
        payload.write_text('local')
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertEqual('local', payload.read_text())

    def test_missing_managed_payload_is_rejected(self):
        self.sync(True)
        ctl.remove(self.target / 'sample')
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

    def test_invalid_metadata_is_rejected(self):
        self.sync(True)
        meta = self.target / '.agents-managed' / 'sample.json'
        for value in ['{', '[]', '{}', json.dumps({'id': 'other', 'digest': ctl.digest(self.source)}), json.dumps({'id': 'sample', 'digest': 'wrong'})]:
            with self.subTest(value=value):
                meta.write_text(value)
                with self.assertRaises(ctl.SafetyError):
                    self.sync(True)
        meta.unlink()
        meta.mkdir()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

    def test_source_ancestor_symlink_is_rejected(self):
        real = self.repo / 'real'
        self.source.parent.rename(real)
        (self.repo / 'skills').symlink_to(real, target_is_directory=True)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse(self.target.exists())

    def test_source_payload_symlink_and_special_file_are_rejected(self):
        link = self.source / 'link'
        link.symlink_to(self.source / 'SKILL.md')
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        link.unlink()
        os.mkfifo(link)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse(self.target.exists())

    def test_target_ancestor_symlink_is_rejected(self):
        real = self.base / 'real-target'
        real.mkdir()
        self.target.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertEqual([], list(real.iterdir()))

    def test_metadata_symlink_is_rejected(self):
        self.sync(True)
        meta = self.target / '.agents-managed' / 'sample.json'
        real = self.base / 'meta.json'
        meta.rename(real)
        meta.symlink_to(real)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        meta.unlink()
        (self.target / '.agents-managed').rmdir()
        (self.target / '.agents-managed').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

    def test_destination_payload_symlink_is_rejected(self):
        self.sync(True)
        payload = self.target / 'sample' / 'SKILL.md'
        payload.unlink()
        payload.symlink_to(self.source / 'SKILL.md')
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

    def test_all_item_preflight_failure_has_zero_writes(self):
        import copy
        second = copy.deepcopy(self.catalog['items'][0])
        second.update(id='second', name='second', path='missing')
        self.catalog['items'].append(second)
        self.environment['items'].append('second')
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse(self.target.exists())

    def test_existing_lock_rejects_apply_but_not_preview(self):
        lock = self.target / '.agents-sync.lock'
        lock.mkdir(parents=True)
        (lock / 'owner').write_text('other')
        self.assertEqual(['install sample'], self.sync())
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertEqual('other', (lock / 'owner').read_text())
        self.assertFalse((self.target / 'sample').exists())

    def add_plugin(self):
        import copy
        item = copy.deepcopy(self.catalog['items'][0])
        item.update(id='plugin', kind='plugin', name='plugin')
        self.catalog['items'].append(item)
        self.environment['items'].append('plugin')
        other = self.base / 'z-plugins'
        self.environment['targets']['plugin'] = str(other)
        self.save()
        return other

    def test_multi_root_lock_release_on_acquisition_failure(self):
        other = self.add_plugin()
        (other / '.agents-sync.lock').mkdir(parents=True)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse((self.target / '.agents-sync.lock').exists())
        self.assertTrue((other / '.agents-sync.lock').exists())
        self.assertFalse((self.target / 'sample').exists())

    def test_all_roots_locked_and_repreflight_before_apply(self):
        from unittest.mock import patch
        other = self.add_plugin()
        original = ctl.prepare
        calls = []
        def inspect(env, repo):
            calls.append(1)
            if len(calls) == 2:
                self.assertTrue((self.target / '.agents-sync.lock').is_dir())
                self.assertTrue((other / '.agents-sync.lock').is_dir())
                (self.target / 'sample').mkdir()
                (self.target / 'sample' / 'mine').write_text('late')
            return original(env, repo)
        with patch.object(ctl, 'prepare', side_effect=inspect):
            with self.assertRaises(ctl.SafetyError):
                self.sync(True)
        self.assertEqual(2, len(calls))
        self.assertEqual('late', (self.target / 'sample' / 'mine').read_text())
        self.assertFalse((self.target / '.agents-sync.lock').exists())
        self.assertFalse((other / '.agents-sync.lock').exists())

    def test_metadata_replace_failure_rolls_back_payload_and_metadata(self):
        from unittest.mock import patch
        self.sync(True)
        meta = self.target / '.agents-managed' / 'sample.json'
        old_meta = meta.read_bytes()
        (self.source / 'SKILL.md').write_text('new')
        original = os.replace
        def fail(src, dest):
            if Path(dest) == meta:
                raise OSError('injected metadata replacement failure')
            return original(src, dest)
        with patch.object(ctl.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                self.sync(True)
        self.assertEqual('# sample', (self.target / 'sample' / 'SKILL.md').read_text())
        self.assertEqual(old_meta, meta.read_bytes())
        self.assertEqual({'sample', '.agents-managed'}, {p.name for p in self.target.iterdir()})

    def test_install_metadata_failure_removes_new_payload(self):
        from unittest.mock import patch
        original = os.replace
        def fail(src, dest):
            if Path(dest).suffix == '.json':
                raise OSError('injected')
            return original(src, dest)
        with patch.object(ctl.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                self.sync(True)
        self.assertFalse((self.target / 'sample').exists())
        self.assertFalse((self.target / '.agents-managed' / 'sample.json').exists())
        self.assertFalse((self.target / '.agents-sync.lock').exists())

    def test_late_destination_edit_is_preserved(self):
        from unittest.mock import patch
        self.sync(True)
        payload = self.target / 'sample' / 'SKILL.md'
        (self.source / 'SKILL.md').write_text('new')
        original = ctl.shutil.copytree
        def edit(src, dst, **kwargs):
            result = original(src, dst, **kwargs)
            if Path(src) == self.source:
                payload.write_text('late local')
            return result
        with patch.object(ctl.shutil, 'copytree', side_effect=edit):
            with self.assertRaises(ctl.SafetyError):
                self.sync(True)
        self.assertEqual('late local', payload.read_text())
        self.assertFalse((self.target / '.agents-sync.lock').exists())

    def test_late_source_mutation_rejected(self):
        from unittest.mock import patch
        original = ctl.shutil.copytree
        def mutate(src, dst, **kwargs):
            if Path(src) == self.source:
                (self.source / 'SKILL.md').write_text('late source')
            return original(src, dst, **kwargs)
        with patch.object(ctl.shutil, 'copytree', side_effect=mutate):
            with self.assertRaises(ctl.SafetyError):
                self.sync(True)
        self.assertFalse((self.target / 'sample').exists())
        self.assertEqual('late source', (self.source / 'SKILL.md').read_text())

    def test_unchanged_payload_is_rechecked_under_lock(self):
        from unittest.mock import patch
        self.sync(True)
        original = ctl.prepare
        calls = []
        payload = self.target / 'sample' / 'SKILL.md'
        def change(env, repo):
            plans = original(env, repo)
            calls.append(1)
            if len(calls) == 2:
                payload.write_text('late unchanged')
            return plans
        with patch.object(ctl, 'prepare', side_effect=change):
            with self.assertRaises(ctl.SafetyError):
                self.sync(True)
        self.assertEqual('late unchanged', payload.read_text())

    def test_multi_root_locks_released_after_write_failure(self):
        from unittest.mock import patch
        other = self.add_plugin()
        with patch.object(ctl, 'replace_artifact', side_effect=OSError('injected')):
            with self.assertRaises(OSError):
                self.sync(True)
        self.assertFalse((self.target / '.agents-sync.lock').exists())
        self.assertFalse((other / '.agents-sync.lock').exists())

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
