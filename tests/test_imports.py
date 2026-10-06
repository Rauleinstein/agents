import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ImportTests(unittest.TestCase):
    def test_maturity_controls_default_selection(self):
        path = ROOT / 'scripts/import_upstreams.py'
        self.assertTrue(path.is_file(), 'reproducible import helper missing')
        spec = importlib.util.spec_from_file_location('import_upstreams', path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.maturity('engineering'), 'stable')
        self.assertEqual(module.maturity('productivity'), 'stable')
        self.assertEqual(module.maturity('misc'), 'optional')
        self.assertEqual(module.maturity('in-progress'), 'experimental')
        with self.assertRaises(ValueError):
            module.maturity('unknown')
