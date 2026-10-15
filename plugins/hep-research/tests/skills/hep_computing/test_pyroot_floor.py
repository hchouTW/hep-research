"""PyROOT tests count only on a supported interpreter: a $HEP_ROOT_PYTHON (or other PyROOT candidate) older than the
Python 3.13 floor is not used, so a run under it cannot pass as ROOT evidence (review of the 3.13 floor, item 3)."""
import importlib
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def fake_python(folder: Path, name: str, major_minor: str) -> Path:
    """Answers every `-c` probe with exit 0 and prints `major_minor` ("3 12"): it 'imports ROOT' and reports that
    version."""
    path = folder / name
    path.write_text(f"#!/bin/sh\necho '{major_minor}'\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@unittest.skipUnless(os.name == "posix", "fake interpreters are shell scripts")
class PyrootFloorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_floor_helper(self):
        from tests.skills.hep_computing import pyroot_floor
        self.assertFalse(pyroot_floor.meets_floor(str(fake_python(self.dir, "py312", "3 12"))))
        self.assertFalse(pyroot_floor.meets_floor(str(fake_python(self.dir, "py39", "3 9"))))
        self.assertTrue(pyroot_floor.meets_floor(str(fake_python(self.dir, "py314", "3 14"))))
        self.assertEqual(pyroot_floor.meets_floor(sys.executable), sys.version_info[:2] >= (3, 13))
        self.assertFalse(pyroot_floor.meets_floor(str(self.dir / "missing")))

    def test_integration_tests_refuse_an_old_pyroot_interpreter(self):
        old = fake_python(self.dir, "py312", "3 12")
        with mock.patch.dict(os.environ, {"HEP_ROOT_PYTHON": str(old)}):
            mod = importlib.reload(importlib.import_module("tests.skills.hep_computing.test_root_integration"))
            self.assertFalse(mod._has_pyroot())
        importlib.reload(mod)

    def test_cpp_asset_tests_skip_an_old_pyroot_candidate(self):
        old = fake_python(self.dir, "py312", "3 12")
        with mock.patch.dict(os.environ, {"HEP_ROOT_PYTHON": str(old)}):
            mod = importlib.reload(importlib.import_module("tests.adapters.test_root_cpp_assets"))
            self.assertNotEqual(mod._pyroot_python(), str(old))
        importlib.reload(mod)


if __name__ == "__main__":
    unittest.main()
