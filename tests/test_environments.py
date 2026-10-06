import json
import os
from pathlib import Path
import tempfile
import unittest
import agentsctl

ROOT = Path(__file__).resolve().parents[1]

class EnvironmentTests(unittest.TestCase):
    def test_default_selection_and_target_paths(self):
        targets = {'hermes': '~/.hermes/skills', 'claude': '~/.claude/skills', 'codex': '~/.agents/skills', 'cursor': '~/.agents/skills'}
        for harness, target in targets.items():
            config = json.loads((ROOT / 'environments' / (harness + '.json')).read_text())
            self.assertEqual(config['harness'], harness)
            self.assertEqual(config['targets'], {'skill': target})
            self.assertEqual(len(config['items']), 37)
            self.assertEqual(len(set(config['items'])), 37)
            self.assertEqual(sum(i.startswith('mattpocock-') for i in config['items']), 27)
            self.assertEqual(sum(i.startswith('speckit-') for i in config['items']), 10)

    def test_all_harnesses_preview_apply_and_idempotent_readback(self):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as temp:
            temp = Path(temp)
            for harness in ('hermes', 'claude', 'codex', 'cursor'):
                config = json.loads((ROOT / 'environments' / (harness + '.json')).read_text())
                config['targets'] = {'skill': str(temp / ('shared' if harness in {'codex', 'cursor'} else harness))}
                env = temp / (harness + '.json')
                env.write_text(json.dumps(config))
                preview = agentsctl.sync(env, ROOT)
                action = 'unchanged' if harness == 'cursor' else 'install'
                self.assertEqual(preview, [action + ' ' + i for i in config['items']])
                if action == 'install':
                    self.assertFalse(Path(config['targets']['skill']).exists())
                self.assertEqual(agentsctl.sync(env, ROOT, apply=True), preview)
                self.assertEqual(agentsctl.sync(env, ROOT), ['unchanged ' + i for i in config['items']])
                plans, _ = agentsctl.prepare(env, ROOT)
                for plan in plans:
                    self.assertEqual(agentsctl.digest(plan['dest']), agentsctl.digest(plan['source']))
                    self.assertEqual(json.loads(plan['meta'].read_text()), {'id': plan['id'], 'digest': plan['wanted']})

    def test_real_catalog_unmanaged_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as temp:
            temp = Path(temp)
            config = json.loads((ROOT / 'environments/codex.json').read_text())
            config['targets'] = {'skill': str(temp / 'skills')}
            destination = temp / 'skills/ask-matt'
            destination.mkdir(parents=True)
            (destination / 'SKILL.md').write_text('my skill')
            env = temp / 'env.json'
            env.write_text(json.dumps(config))
            with self.assertRaisesRegex(agentsctl.SafetyError, 'unmanaged destination'):
                agentsctl.sync(env, ROOT, apply=True)
            self.assertEqual((destination / 'SKILL.md').read_text(), 'my skill')
