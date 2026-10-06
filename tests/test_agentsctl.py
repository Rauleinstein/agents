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

if __name__ == '__main__':
    unittest.main()
