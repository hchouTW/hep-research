"""F-10: running a script leaves no __pycache__ in the plugin. Every script that imports a sibling module or a plugin
package (core, contracts, another file of its skill) sets sys.dont_write_bytecode = True before that import.

The scripts run from a copy of the plugin in a temporary folder, with PYTHONDONTWRITEBYTECODE unset and without -B
(the interpreter writes bytecode by default), once with --help and once pointed at a missing input; after each run the
copy must hold no __pycache__. With the variable exported the test would pass on any commit and prove nothing."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.skills.test_cli_contract import TOOLS  # noqa: E402
from tests.skills.test_cli_robustness import MISSING_FILE_ARGS, argv_sets  # noqa: E402

COPY = ("skills", "core", "contracts", "adapters", "profiles", ".claude-plugin")


def _caches(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("__pycache__"))


class NoBytecode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "plugin"
        cls.root.mkdir()
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "output", "*.root", "*.pt")
        for name in COPY:
            src = ROOT / name
            if src.is_dir():
                shutil.copytree(src, cls.root / name, ignore=ignore)
        cls.env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_scripts_write_no_bytecode(self):
        self.assertEqual(_caches(self.root), [])
        offenders = {}
        for script in TOOLS:
            runs = [["--help"]] + (argv_sets(MISSING_FILE_ARGS[script]) if script in MISSING_FILE_ARGS else [])
            for args in runs:
                with tempfile.TemporaryDirectory() as cwd:
                    subprocess.run([sys.executable, str(self.root / script), *args], capture_output=True, text=True,
                                   timeout=180, cwd=cwd, env=self.env)
                made = _caches(self.root)
                if made:
                    offenders[script] = made
                    for d in made:
                        shutil.rmtree(self.root / d, ignore_errors=True)
        self.maxDiff = None
        self.assertEqual(sorted(offenders), [], "set sys.dont_write_bytecode = True before importing siblings or plugin packages")


if __name__ == "__main__":
    unittest.main()
