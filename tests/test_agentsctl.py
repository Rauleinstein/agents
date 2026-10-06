import os
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'agentsctl.py'

class DigestTests(unittest.TestCase):
    def test_digest_is_stable_and_tracks_paths_and_bytes(self):
        self.assertTrue(MODULE.exists(), 'installer module must exist')
        module = ctl
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
        # Keep even a failing relative-path implementation inside scratch.
        previous_cwd = Path.cwd()
        os.chdir(self.base)
        self.addCleanup(os.chdir, previous_cwd)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.source = self.repo / 'skills' / 'sample'
        self.source.mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('# sample')
        self.target = self.base / 'target'
        self.catalog: dict = {'version': 1, 'items': [dict(id='sample', kind='skill', path='skills/sample', name='sample', harnesses=['hermes', 'claude', 'cursor', 'codex'], provenance=dict(source='https://example.test', revision='abc', license='MIT', reviewed=True))]}
        self.environment: dict = dict(harness='hermes', targets={'skill': str(self.target)}, items=['sample'])
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

    def test_cli_preview_apply_and_errors(self):
        import subprocess
        command = [sys.executable, str(MODULE), 'sync', '--env', str(self.env), '--repo', str(self.repo)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertEqual('install sample\n', result.stdout)
        self.assertFalse(self.target.exists())
        result = subprocess.run(command + ['--apply'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('install sample\n', result.stdout)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual('unchanged sample\n', result.stdout)
        self.env.write_text('{broken')
        result = subprocess.run(command + ['--apply'], capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertEqual('', result.stdout)
        self.assertIn('error:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_native_markdown_agent_deploys_to_claude_and_cursor(self):
        source = self.repo / 'agent.md'
        source.write_text('# agent')
        item = self.catalog['items'][0]
        item.update(kind='agent', path='agent.md', name='sample.md', harnesses=['claude', 'cursor'])
        self.environment['targets'] = {'agent': str(self.target)}
        for harness in ['claude', 'cursor']:
            with self.subTest(harness=harness):
                self.environment['harness'] = harness
                self.save()
                result = self.sync(True)
                self.assertEqual('# agent', (self.target / 'sample.md').read_text())
                self.assertEqual(['install sample'] if harness == 'claude' else ['unchanged sample'], result)
        self.environment['harness'] = 'codex'
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

    def test_cursor_codex_shared_skill_root_is_idempotent(self):
        for harness in ['cursor', 'codex']:
            self.environment['harness'] = harness
            self.save()
            self.assertEqual(['install sample'] if harness == 'cursor' else ['unchanged sample'], self.sync(True))

    def test_plugin_script_is_copied_never_executed(self):
        sentinel = self.base / 'executed'
        script = self.source / 'install.sh'
        script.write_text(f'#!/bin/sh\ntouch {sentinel}\n')
        script.chmod(0o755)
        self.catalog['items'][0]['kind'] = 'plugin'
        self.environment['targets'] = {'plugin': str(self.target)}
        self.save()
        self.sync(True)
        self.assertEqual(script.read_bytes(), (self.target / 'sample' / 'install.sh').read_bytes())
        self.assertFalse(sentinel.exists())

    def test_unused_declared_target_symlink_is_rejected(self):
        other = self.base / 'unused'
        other.symlink_to(self.base / 'nonexistent', target_is_directory=True)
        self.environment['targets']['plugin'] = str(other)
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse(self.target.exists())

    def test_unused_declared_target_is_locked(self):
        other = self.base / 'unused'
        self.environment['targets']['plugin'] = str(other)
        self.save()
        (other / '.agents-sync.lock').mkdir(parents=True)
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertTrue((other / '.agents-sync.lock').exists())
        self.assertFalse((self.target / 'sample').exists())

    def test_duplicate_json_keys_are_rejected(self):
        self.env.write_text('{"harness":"codex","harness":"hermes","targets":' + json.dumps(self.environment['targets']) + ',"items":["sample"]}')
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)
        self.assertFalse(self.target.exists())

    def test_unknown_tilde_user_is_rejected_cleanly(self):
        self.environment['targets']['skill'] = '~agentsctl-user-that-does-not-exist/skills'
        self.save()
        with self.assertRaises(ctl.SafetyError):
            self.sync(True)

    def test_payload_swap_failure_restores_original(self):
        from unittest.mock import patch
        self.sync(True)
        meta = self.target / '.agents-managed' / 'sample.json'
        old_meta = meta.read_bytes()
        (self.source / 'SKILL.md').write_text('new')
        original = os.replace
        def fail(src, dst):
            if Path(src).name.startswith('.agents-stage-'):
                raise OSError('injected payload swap failure')
            return original(src, dst)
        with patch.object(ctl.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                self.sync(True)
        self.assertEqual('# sample', (self.target / 'sample' / 'SKILL.md').read_text())
        self.assertEqual(old_meta, meta.read_bytes())
        self.assertEqual({'sample', '.agents-managed'}, {p.name for p in self.target.iterdir()})

    def test_source_mutation_after_copy_is_rejected(self):
        from unittest.mock import patch
        original = ctl.shutil.copytree
        def mutate(src, dst, **kwargs):
            result = original(src, dst, **kwargs)
            if Path(src) == self.source:
                (self.source / 'SKILL.md').write_text('after copy')
            return result
        with patch.object(ctl.shutil, 'copytree', side_effect=mutate):
            with self.assertRaises(ctl.SafetyError):
                self.sync(True)
        self.assertFalse((self.target / 'sample').exists())

    def test_late_metadata_edit_is_preserved(self):
        from unittest.mock import patch
        self.sync(True)
        meta = self.target / '.agents-managed' / 'sample.json'
        (self.source / 'SKILL.md').write_text('new')
        original = ctl.shutil.copytree
        def edit(src, dst, **kwargs):
            result = original(src, dst, **kwargs)
            if Path(src) == self.source:
                meta.write_text('local metadata')
            return result
        with patch.object(ctl.shutil, 'copytree', side_effect=edit):
            with self.assertRaises(ctl.SafetyError):
                self.sync(True)
        self.assertEqual('local metadata', meta.read_text())
        self.assertEqual('# sample', (self.target / 'sample' / 'SKILL.md').read_text())

    def test_tilde_target_expands_without_real_profile_writes(self):
        from unittest.mock import patch
        self.environment['targets']['skill'] = '~/target'
        self.save()
        with patch.dict(os.environ, {'HOME': str(self.base)}):
            self.sync(True)
        self.assertTrue((self.target / 'sample' / 'SKILL.md').is_file())

    def test_lock_replacement_is_not_removed(self):
        from unittest.mock import patch
        lock = self.target / '.agents-sync.lock'
        original = ctl.replace_artifact
        def replace_lock(plan):
            lock.rename(self.base / 'original-lock')
            lock.mkdir()
            (lock / 'owner').write_text('another process')
            return original(plan)
        with patch.object(ctl, 'replace_artifact', side_effect=replace_lock):
            self.sync(True)
        self.assertEqual('another process', (lock / 'owner').read_text())

    def test_lock_acquisition_is_sorted(self):
        from unittest.mock import patch
        other = self.add_plugin()
        original = Path.mkdir
        acquired = []
        def record(path, *args, **kwargs):
            if path.name == '.agents-sync.lock':
                acquired.append(path.parent)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', record):
            self.sync(True)
        self.assertEqual(sorted([self.target, other]), acquired)

    def test_existing_preview_changes_no_payload_or_metadata(self):
        self.sync(True)
        before = {str(p): p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(['unchanged sample'], self.sync())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.target.rglob('*') if p.is_file()})
        self.assertFalse((self.target / '.agents-sync.lock').exists())

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
