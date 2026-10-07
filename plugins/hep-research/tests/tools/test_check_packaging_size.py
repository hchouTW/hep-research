"""tools/check_packaging.py size statement: the README's "about N files, X MB uncompressed"
must stay within 10% of the measured package; a drift fails."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_packaging", PLUGIN / "tools" / "check_packaging.py")
cp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cp)


class SizeStatementTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.old = cp.ROOT
        cp.ROOT = self.root
        self.files = []
        for i in range(20):
            p = self.root / f"f{i}.txt"
            p.write_bytes(b"x" * 50_000)  # 20 files, 1.0 MB
            self.files.append(p)

    def tearDown(self):
        cp.ROOT = self.old
        self.td.cleanup()

    def readme(self, text):
        (self.root / "README.md").write_text(text, encoding="utf-8")
        return self.files + [self.root / "README.md"]

    def test_matching_statement_passes(self):
        self.assertEqual(cp.size_drift(self.readme("The plugin (about 21 files, 1.0 MB\n   uncompressed) fits.")), [])

    def test_drift_fails_for_count_and_size(self):
        problems = cp.size_drift(self.readme("The plugin (about 15 files, 0.6 MB uncompressed) fits."))
        self.assertEqual(len(problems), 2, problems)

    def test_missing_statement_fails(self):
        self.assertTrue(cp.size_drift(self.readme("No size here.")))

    def test_the_plugin_readme_is_within_margin(self):
        cp.ROOT = self.old
        self.assertEqual(cp.size_drift(cp.files()), [])


if __name__ == "__main__":
    unittest.main()
